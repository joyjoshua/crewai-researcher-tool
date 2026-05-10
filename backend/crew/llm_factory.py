"""
LLM Factory — creates LLM instances for each agent using Paytm Inference.
Each agent gets a model matched to its task complexity (see Tech Stack doc, Section 6).

IMPORTANT: This returns a factory function, NOT module-level singletons.
Each crew run gets fresh LLM instances to avoid cross-request state leaks.
"""

import os

from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

PAYTM_BASE_URL = os.getenv("PAYTM_BASE_URL")
PAYTM_API_KEY = os.getenv("PAYTM_API_KEY")


def make_llm(model: str, temperature: float = 0.7) -> LLM:
    """Create an LLM instance pointing at Paytm Inference."""
    return LLM(
        model=model,
        base_url=PAYTM_BASE_URL,
        api_key=PAYTM_API_KEY,
        temperature=temperature,
    )


def create_llms() -> dict:
    """
    Creates a fresh set of LLM instances for one crew run.
    Called inside create_agents() — never cached at module level.

    Model IDs use the ``openai/...`` prefix so CrewAI/LiteLLM targets the
    OpenAI-compatible API at PAYTM_BASE_URL (avoids Bedrock routing for
    anthropic.* names). Adjust if your gateway uses different aliases.
    """
    return {
        "planner": make_llm("openai/qwen/qwen3-32b", temperature=0.3),
        "researcher": make_llm("openai/llama-3.3-70b-versatile", temperature=0.5),
        "analyst": make_llm("openai/moonshotai.kimi-k2-thinking", temperature=0.2),
        "writer": make_llm("openai/gpt-oss-120b", temperature=0.7),
        "editor": make_llm(
            "openai/anthropic.claude-3-haiku-20240307-v1:0",
            temperature=0.3,
        ),
    }
