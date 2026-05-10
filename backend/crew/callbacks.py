"""
Callback functions that CrewAI calls at each step and task completion.
They push structured AgentEvent objects into an asyncio.Queue.

IMPORTANT: CrewAI callbacks run in the crew's thread, but the Queue
is consumed by FastAPI's async SSE generator. We use a thread-safe
approach by calling loop.call_soon_threadsafe().

KNOWN ISSUE: step_callback is unreliable in some CrewAI versions
(may not fire, or fire inconsistently). The task_callback is more
reliable. The frontend should treat step events as best-effort and
not depend on them for correctness.
"""

import asyncio
import json
import logging

from crew.events import AgentEvent, EventType

logger = logging.getLogger(__name__)

# Maximum queue size to prevent memory leaks if SSE consumer disconnects
MAX_QUEUE_SIZE = 500


def create_event_queue() -> asyncio.Queue:
    """Bounded queue so put_nowait can raise QueueFull if the consumer stalls."""
    return asyncio.Queue(maxsize=MAX_QUEUE_SIZE)


def _event_json(event: AgentEvent) -> str:
    """JSON string safe for sse-starlette / browser (Enum → plain strings)."""
    return json.dumps(event.model_dump(mode="json"))


def make_step_callback(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """
    Returns a step_callback compatible with CrewAI Crew(step_callback=...).
    CrewAI calls this after each agent reasoning step.
    """

    def step_callback(output):
        log_text = getattr(output, "log", "") or ""

        if "Action:" in log_text or "tool" in log_text.lower():
            event_type = EventType.TOOL_CALL
        elif "Observation:" in log_text:
            event_type = EventType.TOOL_RESULT
        else:
            event_type = EventType.AGENT_THOUGHT

        agent_name = ""
        if hasattr(output, "agent") and output.agent:
            agent_name = getattr(output.agent, "role", "Unknown")

        event = AgentEvent(
            type=event_type,
            agent=agent_name or "",
            message=log_text[:500],
        )

        try:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                _event_json(event),
            )
        except asyncio.QueueFull:
            logger.warning(
                "Event queue full (max %s), dropping step event", MAX_QUEUE_SIZE
            )
        except RuntimeError:
            pass

    return step_callback


def make_task_callback(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """
    Returns a task_callback compatible with CrewAI Crew(task_callback=...).
    CrewAI calls this after each task completes.
    """

    def task_callback(output):
        agent_raw = getattr(output, "agent", None)
        if agent_raw is None:
            agent_name = "Unknown"
        elif hasattr(agent_raw, "role"):
            agent_name = getattr(agent_raw, "role", "Unknown") or "Unknown"
        else:
            agent_name = str(agent_raw)

        description = getattr(output, "description", "") or ""
        raw = getattr(output, "raw", "") or ""

        event = AgentEvent(
            type=EventType.TASK_COMPLETE,
            agent=agent_name,
            task=description[:200],
            message=f"Task completed. Output: {raw[:300]}...",
        )

        try:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                _event_json(event),
            )
        except asyncio.QueueFull:
            logger.warning(
                "Event queue full (max %s), dropping task_complete event",
                MAX_QUEUE_SIZE,
            )
        except RuntimeError:
            pass

    return task_callback
