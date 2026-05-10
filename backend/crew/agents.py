"""
Agent definitions — each agent gets a role-specific LLM and tools.
Config is loaded from config/agents.yaml for role, goal, backstory.

IMPORTANT: create_agents() must be called per crew run, not at module level.
This ensures each run gets fresh agent + LLM instances (no cross-request leaks).
"""

import logging
from pathlib import Path

import yaml
from crewai import Agent
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

from crew.llm_factory import create_llms

logger = logging.getLogger(__name__)

# ── Load YAML config ────────────────────────────────────────────
CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_agents_config():
    """Load agents YAML with error handling."""
    config_path = CONFIG_DIR / "agents.yaml"
    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error("Failed to load agents config from %s: %s", config_path, e)
        raise


def create_agents():
    """
    Creates and returns all 5 agents with fresh LLM instances.
    Returns a dict keyed by agent name for easy reference in tasks.
    """
    agents_config = _load_agents_config()
    llms = create_llms()

    # Tools — created per run (cheap to instantiate)
    search_tool = SerperDevTool()
    scrape_tool = ScrapeWebsiteTool()

    planner = Agent(
        role=agents_config["planner"]["role"],
        goal=agents_config["planner"]["goal"],
        backstory=agents_config["planner"]["backstory"],
        llm=llms["planner"],
        verbose=True,
        allow_delegation=False,
        max_execution_time=300,  # 5 min timeout
    )

    researcher = Agent(
        role=agents_config["researcher"]["role"],
        goal=agents_config["researcher"]["goal"],
        backstory=agents_config["researcher"]["backstory"],
        llm=llms["researcher"],
        tools=[search_tool, scrape_tool],
        verbose=True,
        allow_delegation=False,
        max_iter=15,  # More iterations — tool loops can be long
        max_execution_time=600,  # 10 min timeout
    )

    analyst = Agent(
        role=agents_config["analyst"]["role"],
        goal=agents_config["analyst"]["goal"],
        backstory=agents_config["analyst"]["backstory"],
        llm=llms["analyst"],
        verbose=True,
        allow_delegation=False,
        max_execution_time=300,
    )

    writer = Agent(
        role=agents_config["writer"]["role"],
        goal=agents_config["writer"]["goal"],
        backstory=agents_config["writer"]["backstory"],
        llm=llms["writer"],
        verbose=True,
        allow_delegation=False,
        max_execution_time=600,
    )

    editor = Agent(
        role=agents_config["editor"]["role"],
        goal=agents_config["editor"]["goal"],
        backstory=agents_config["editor"]["backstory"],
        llm=llms["editor"],
        verbose=True,
        allow_delegation=False,
        max_execution_time=300,
    )

    return {
        "planner": planner,
        "researcher": researcher,
        "analyst": analyst,
        "writer": writer,
        "editor": editor,
    }
