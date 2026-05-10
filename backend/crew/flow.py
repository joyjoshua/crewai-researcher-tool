"""
ResearchReportFlow — wraps the crew in a Flow for state management
and event-driven orchestration.

Production: set ``flow.state.topic`` from the API (Phase 7) using the topic the user
entered in the UI before calling ``flow.kickoff()``. Do not bake a topic into lib code.
"""

import logging
import os
import sys

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

from crew.crew import build_crew

logger = logging.getLogger(__name__)


class ReportState(BaseModel):
    """Shared state persisted throughout the flow execution."""

    topic: str = ""
    final_report: str = ""
    status: str = "idle"  # idle | running | done | error


class ResearchReportFlow(Flow[ReportState]):
    """
    Main flow: receives a topic, runs the crew, stores results in state.
    """

    def __init__(self, step_callback=None, task_callback=None):
        super().__init__()
        self._step_callback = step_callback
        self._task_callback = task_callback

    @start()
    def begin_research(self):
        """Entry point — topic is already set on state before kickoff."""
        self.state.status = "running"
        logger.info("Starting research on: %s", self.state.topic)
        return self.state.topic

    @listen(begin_research)
    def run_crew(self, topic):
        """Run the full research crew."""
        try:
            crew = build_crew(
                step_callback=self._step_callback,
                task_callback=self._task_callback,
            )
            result = crew.kickoff(inputs={"topic": topic})
            self.state.final_report = result.raw
            self.state.status = "done"
            logger.info(
                "Research complete. Report: %s chars", len(self.state.final_report)
            )
        except Exception as e:
            self.state.status = "error"
            self.state.final_report = f"Error: {str(e)}"
            logger.error("Crew failed: %s", e, exc_info=True)
            raise


# ── Standalone test runner (dev only — not used by FastAPI/UI) ───
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_topic = (
        (sys.argv[1].strip() if len(sys.argv) > 1 else "") or (
            os.environ.get("CREW_DEMO_TOPIC") or ""
        ).strip()
        or "Impact of AI on Healthcare in 2025"
    )
    flow = ResearchReportFlow()
    flow.state.topic = demo_topic
    flow.kickoff()

    print("\n" + "=" * 60)
    print(f"Status: {flow.state.status}")
    print(f"Report length: {len(flow.state.final_report)} chars")
    print("=" * 60)
    print(flow.state.final_report[:500])
