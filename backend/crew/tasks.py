"""
Task definitions — each task is assigned to an agent and optionally
receives context from prior tasks.
Config is loaded from config/tasks.yaml.

IMPORTANT: No output_file on any task. Intermediate results pass through
CrewAI's context system; the final report is captured from the crew result.
This avoids file collisions when multiple jobs run concurrently.
"""

import logging
from pathlib import Path

import yaml
from crewai import Task

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_tasks_config():
    """Load tasks YAML with error handling."""
    config_path = CONFIG_DIR / "tasks.yaml"
    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error("Failed to load tasks config from %s: %s", config_path, e)
        raise


def create_tasks(agents: dict) -> dict:
    """
    Creates all 5 tasks and wires context dependencies.
    agents: dict from create_agents()
    Returns a dict keyed by task name.
    """
    tasks_config = _load_tasks_config()

    planning_task = Task(
        description=tasks_config["planning_task"]["description"],
        expected_output=tasks_config["planning_task"]["expected_output"],
        agent=agents["planner"],
    )

    research_task = Task(
        description=tasks_config["research_task"]["description"],
        expected_output=tasks_config["research_task"]["expected_output"],
        agent=agents["researcher"],
        context=[planning_task],
    )

    analysis_task = Task(
        description=tasks_config["analysis_task"]["description"],
        expected_output=tasks_config["analysis_task"]["expected_output"],
        agent=agents["analyst"],
        context=[research_task],
    )

    writing_task = Task(
        description=tasks_config["writing_task"]["description"],
        expected_output=tasks_config["writing_task"]["expected_output"],
        agent=agents["writer"],
        context=[analysis_task],
    )

    editing_task = Task(
        description=tasks_config["editing_task"]["description"],
        expected_output=tasks_config["editing_task"]["expected_output"],
        agent=agents["editor"],
        context=[writing_task],
    )

    return {
        "planning_task": planning_task,
        "research_task": research_task,
        "analysis_task": analysis_task,
        "writing_task": writing_task,
        "editing_task": editing_task,
    }
