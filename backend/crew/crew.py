"""
Crew assembly — brings agents and tasks together into a sequential crew.
This file is the main entry point for running the crew standalone (Phase 3 testing).
"""

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


# ── Standalone test runner ───────────────────────────────────────
if __name__ == "__main__":
    crew = build_crew()
    result = crew.kickoff(inputs={"topic": "Impact of AI on Healthcare in 2025"})
    print("\n" + "=" * 60)
    print("FINAL OUTPUT:")
    print("=" * 60)
    print(result.raw)
