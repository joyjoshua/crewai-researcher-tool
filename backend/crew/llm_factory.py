"""
LLM Factory — creates LLM instances for each agent using Paytm Inference.
Each agent gets a model matched to its task complexity (see Tech Stack doc, Section 6).

IMPORTANT: This returns a factory function, NOT module-level singletons.
Each crew run gets fresh LLM instances to avoid cross-request state leaks.
"""

import os
import socket
from pathlib import Path
from urllib.parse import urlparse

from crewai import LLM
from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")

PAYTM_BASE_URL = (os.getenv("PAYTM_BASE_URL") or "").strip().rstrip("/")
PAYTM_API_KEY = (os.getenv("PAYTM_API_KEY") or "").strip()


def _validate_inference_env() -> None:
    """
    Fail fast with a clearer message than LiteLLM's generic "Connection error".
    Mirrors Windows error WinError 10051 / POSIX EAI_*: bad hostname → getaddrinfo.
    """
    if not PAYTM_API_KEY:
        raise RuntimeError(
            "PAYTM_API_KEY is missing or empty in backend/.env. "
            "Set it to your inference gateway API key."
        )
    if "your_paytm" in PAYTM_API_KEY.lower() or "your-paytm" in PAYTM_API_KEY.lower():
        raise RuntimeError(
            "PAYTM_API_KEY still looks like a placeholder. Replace it with a real key."
        )

    if not PAYTM_BASE_URL:
        raise RuntimeError(
            "PAYTM_BASE_URL is missing or empty in backend/.env. Example: "
            "https://api.inference.paytm.com/v1 (exact path depends on your gateway)."
        )

    parsed = urlparse(PAYTM_BASE_URL if PAYTM_BASE_URL.startswith("http") else f"https://{PAYTM_BASE_URL}")
    host = parsed.hostname
    if not host:
        raise RuntimeError(
            f"PAYTM_BASE_URL is invalid: {PAYTM_BASE_URL!r}. Use a full URL with a hostname "
            "(e.g. https://host.example/v1)."
        )

    try:
        socket.getaddrinfo(host, None)
    except OSError as e:
        tip = ""
        bogus = ("your-", "your_", "fake", "example", "placeholder")
        if any(b in host.lower() for b in bogus):
            tip = (
                " The hostname looks like a template — copy the exact base URL from your "
                "inference dashboard."
            )
        raise RuntimeError(
            f'Cannot resolve inference host "{host}" from PAYTM_BASE_URL ({e}). Check the URL, '
            f"DNS/VPN, and firewall.{tip}"
        ) from e


def make_llm(model: str, temperature: float = 0.7) -> LLM:
    """Create an LLM instance pointing at Paytm Inference."""
    return LLM(
        model=model,
        base_url=PAYTM_BASE_URL,
        api_key=PAYTM_API_KEY,
        temperature=temperature,
    )


def _model_for_agent(role: str, default: str) -> str:
    """Optional override: PAYTM_MODEL_PLANNER, PAYTM_MODEL_WRITER, … (same id the gateway expects)."""
    key = f"PAYTM_MODEL_{role.upper()}"
    custom = (os.getenv(key) or "").strip()
    return custom or default


def create_llms() -> dict:
    """
    Creates a fresh set of LLM instances for one crew run.
    Called inside create_agents() — never cached at module level.

    Model IDs use the ``openai/...`` prefix so CrewAI/LiteLLM targets the
    OpenAI-compatible API at PAYTM_BASE_URL (avoids Bedrock routing for
    anthropic.* names). Adjust if your gateway uses different aliases.

    Override any role with ``PAYTM_MODEL_<ROLE>`` (e.g. PAYTM_MODEL_WRITER);
    values must be models **assigned to your Paytm account**, or the API
    returns 403 (``insufficient_permissions``).
    """
    _validate_inference_env()
    # Defaults avoid models that are often unassigned (e.g. gpt-oss-120b); use env to tune.
    return {
        "planner": make_llm(_model_for_agent("planner", "openai/qwen/qwen3-32b"), temperature=0.3),
        "researcher": make_llm(
            _model_for_agent("researcher", "openai/llama-3.3-70b-versatile"),
            temperature=0.5,
        ),
        "analyst": make_llm(
            _model_for_agent("analyst", "openai/moonshotai.kimi-k2-thinking"),
            temperature=0.2,
        ),
        "writer": make_llm(
            _model_for_agent("writer", "openai/llama-3.3-70b-versatile"),
            temperature=0.7,
        ),
        "editor": make_llm(
            _model_for_agent(
                "editor", "openai/anthropic.claude-3-haiku-20240307-v1:0"
            ),
            temperature=0.3,
        ),
    }
