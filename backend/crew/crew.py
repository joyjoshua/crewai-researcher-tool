"""
Crew assembly — brings agents and tasks together into a sequential crew.
This module is imported by FastAPI flows; CLI ``__main__`` is for manual testing only.

Production topics come from ``crew.kickoff(inputs={"topic": ...})``, where ``topic``
is supplied by Phase 7 (API body from the React UI).
"""

import logging
import os
import sys
from crewai import Crew, Process

from crew.agents import create_agents
from crew.tasks import create_tasks


def build_crew(
    step_callback=None,
    task_callback=None,
) -> Crew:
    """
    Assemble the full research crew.
    Optionally accepts callback functions for SSE streaming (Phase 6+).

    Every call creates fresh agents/tasks/LLMs — safe for concurrent use.
    Memory is OFF by default; enabled in Phase 10 once embedder is verified.
    """
    agents = create_agents()
    tasks = create_tasks(agents)

    crew = Crew(
        agents=list(agents.values()),
        tasks=list(tasks.values()),
        process=Process.sequential,
        memory=False,  # Enabled in Phase 10 with verified embedder
        verbose=True,
        step_callback=step_callback,
        task_callback=task_callback,
    )

    return crew


# ── Standalone test runner (dev only — not used by FastAPI/UI) ───
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_topic = (
        (sys.argv[1].strip() if len(sys.argv) > 1 else "") or (
            os.environ.get("CREW_DEMO_TOPIC") or ""
        ).strip()
        or "Impact of AI on Healthcare in 2025"
    )
    crew = build_crew()
    result = crew.kickoff(inputs={"topic": demo_topic})
    print("\n" + "=" * 60)
    print("FINAL OUTPUT:")
    print("=" * 60)
    print(result.raw)
