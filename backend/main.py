"""
FastAPI backend — API endpoints + SSE streaming for live agent execution.

Uses ThreadPoolExecutor for crew jobs, Supabase persistence, slowapi limits,
JWT auth (Bearer or ?token= for SSE), and bounded asyncio queues for events.
"""

import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sse_starlette.sse import EventSourceResponse
from starlette.responses import JSONResponse

from crew.callbacks import create_event_queue, make_step_callback, make_task_callback
from crew.events import AgentEvent, EventType
from crew.flow import ResearchReportFlow
from db import supabase
from middleware.auth import get_current_user, get_current_user_sse

_BACKEND_ROOT = Path(__file__).resolve().parent
load_dotenv(_BACKEND_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "3"))
MAX_TOPIC_LENGTH = 500

executor = ThreadPoolExecutor(
    max_workers=MAX_CONCURRENT_JOBS, thread_name_prefix="crew"
)

event_queues: dict[str, asyncio.Queue] = {}
running_futures: dict[str, asyncio.Future] = {}

limiter = Limiter(key_func=get_remote_address)


def _agent_event_json(event: AgentEvent) -> str:
    return json.dumps(event.model_dump(mode="json"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Research Report Generator API started")
    yield
    if running_futures:
        logger.info(
            "Shutting down — waiting for %s running jobs...",
            len(running_futures),
        )
        for job_id, fut in list(running_futures.items()):
            try:
                await asyncio.wait_for(fut, timeout=60)
            except Exception:
                logger.warning(
                    "Job %s did not finish cleanly during shutdown", job_id
                )
    executor.shutdown(wait=False)
    logger.info("API shut down")


app = FastAPI(title="Research Report Generator", lifespan=lifespan)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def ratelimit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        {"detail": "Too many requests. Try again in a minute."},
        status_code=429,
    )


app.add_middleware(SlowAPIMiddleware)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=MAX_TOPIC_LENGTH)


class GenerateResponse(BaseModel):
    job_id: str
    topic: str


class ReportResponse(BaseModel):
    job_id: str
    topic: str
    status: str
    report: str | None = None


def _enqueue_sse(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, payload: str) -> None:
    """Enqueue on the asyncio loop thread; drop if bounded queue is full."""

    def _put():
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("SSE queue full; dropping event")

    loop.call_soon_threadsafe(_put)


def run_crew_job(job_id: str, topic: str, loop: asyncio.AbstractEventLoop):
    """
    Runs the CrewAI flow in a background thread via ThreadPoolExecutor.
    Push events into the job's asyncio.Queue via callbacks.
    Persist final result to Supabase.
    """
    queue = event_queues.get(job_id)
    if not queue:
        return

    try:
        step_cb = make_step_callback(queue, loop)
        task_cb = make_task_callback(queue, loop)

        flow = ResearchReportFlow(step_callback=step_cb, task_callback=task_cb)
        flow.state.topic = topic
        flow.kickoff()

        supabase.table("jobs").update(
            {
                "status": "done",
                "final_report": flow.state.final_report,
            }
        ).eq("id", job_id).execute()

        done_event = AgentEvent(
            type=EventType.FLOW_COMPLETE,
            message="Research report complete",
        )
        _enqueue_sse(loop, queue, _agent_event_json(done_event))

    except Exception as e:
        logger.error("Job %s failed: %s", job_id, e, exc_info=True)

        supabase.table("jobs").update(
            {
                "status": "error",
                "error_message": str(e)[:2000],
            }
        ).eq("id", job_id).execute()

        error_event = AgentEvent(
            type=EventType.ERROR,
            message=f"Crew failed: {str(e)[:500]}",
        )
        _enqueue_sse(loop, queue, _agent_event_json(error_event))

    finally:
        running_futures.pop(job_id, None)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/report/generate", response_model=GenerateResponse)
@limiter.limit("5/minute")
async def generate_report(
    request: Request,
    body: GenerateRequest,
    user_id: str = Depends(get_current_user),
):
    if len(running_futures) >= MAX_CONCURRENT_JOBS:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Server is busy ({MAX_CONCURRENT_JOBS} concurrent jobs limit). "
                "Try again shortly."
            ),
        )

    insert = (
        supabase.table("jobs")
        .insert(
            {
                "user_id": user_id,
                "topic": body.topic,
                "status": "running",
            }
        )
        .execute()
    )

    if not insert.data:
        raise HTTPException(status_code=500, detail="Failed to create job")

    job_id = insert.data[0]["id"]
    event_queues[job_id] = create_event_queue()

    loop = asyncio.get_running_loop()
    fut = loop.run_in_executor(executor, run_crew_job, job_id, body.topic, loop)
    running_futures[job_id] = fut

    return GenerateResponse(job_id=job_id, topic=body.topic)


@app.get("/api/report/stream/{job_id}")
async def stream_report(
    job_id: str,
    user_id: str = Depends(get_current_user_sse),
):
    result = supabase.table("jobs").select("user_id").eq("id", job_id).execute()
    if not result.data or str(result.data[0]["user_id"]) != user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    queue = event_queues.get(job_id)
    if not queue:
        raise HTTPException(
            status_code=404,
            detail="Job not streaming (may have finished before connect)",
        )

    jid = job_id

    async def event_generator():
        try:
            while True:
                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {"data": event_data}
                    parsed = json.loads(event_data)
                    et = parsed.get("type")
                    if et in ("flow_complete", "error"):
                        break
                except asyncio.TimeoutError:
                    yield {"comment": "keepalive"}
        finally:
            event_queues.pop(jid, None)

    return EventSourceResponse(event_generator())


@app.get("/api/report/{job_id}", response_model=ReportResponse)
async def get_report(job_id: str, user_id: str = Depends(get_current_user)):
    result = (
        supabase.table("jobs")
        .select("id, topic, status, final_report")
        .eq("id", job_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = result.data[0]
    return ReportResponse(
        job_id=str(job["id"]),
        topic=job["topic"],
        status=job["status"],
        report=job.get("final_report"),
    )


@app.get("/api/reports/history")
async def report_history(user_id: str = Depends(get_current_user)):
    result = (
        supabase.table("jobs")
        .select("id, topic, status, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    rows = result.data or []
    return [
        {
            "job_id": str(job["id"]),
            "topic": job["topic"],
            "status": job["status"],
            "created_at": job["created_at"],
        }
        for job in rows
    ]
