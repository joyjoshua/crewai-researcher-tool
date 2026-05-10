"""
LLM Factory — creates LLM instances for each agent using Paytm Inference.
Each agent gets a model matched to its task complexity (see Tech Stack doc, Section 6).

IMPORTANT: This returns a factory function, NOT module-level singletons.
Each crew run gets fresh LLM instances to avoid cross-request state leaks.
"""

import json
import os
import socket
from pathlib import Path
from urllib.parse import urlparse, urlunsplit

from crewai import LLM
from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")


def _sanitize_secret(value: str) -> str:
    """Strip .env quirks: quotes, pasted newlines/carriage returns."""
    s = value.strip().strip('"').strip("'")
    return s.replace("\r", "").replace("\n", "").strip()


def _effective_paytm_api_key() -> str:
    return _sanitize_secret(os.getenv("PAYTM_API_KEY") or "")


def _raw_paytm_base_url() -> str:
    return _sanitize_secret(os.getenv("PAYTM_BASE_URL") or "")


def _normalize_openai_api_base(raw: str, *, skip: bool) -> str:
    """
    LiteLLM/OpenAI-compatible clients POST to ``{base}/chat/completions``.
    Gateways often answer with an HTML ``Access Denied`` page when ``/v1`` is missing.
    Default: append ``/v1`` only when path is empty (``https://host`` or ``https://host/``).
    Set PAYTM_SKIP_BASE_URL_NORMALIZE=1 only if your base URL intentionally has no ``/v1``.
    """
    if skip:
        return raw.rstrip("/")
    full = raw if raw.startswith(("http://", "https://")) else f"https://{raw}"
    p = urlparse(full)
    if not p.netloc:
        return raw.rstrip("/")
    path = (p.path or "").strip()
    trail = path.rstrip("/") if path else ""
    new_path = "/v1" if trail == "" else "/" + trail.lstrip("/")
    return urlunsplit((p.scheme, p.netloc, new_path, "", "")).rstrip("/")


_PAYTM_SKIP_BASE_NORMALIZE = (os.getenv("PAYTM_SKIP_BASE_URL_NORMALIZE") or "").strip().lower() in (
    "1",
    "true",
    "yes",
)


def _effective_paytm_api_base() -> str:
    return _normalize_openai_api_base(
        _raw_paytm_base_url(),
        skip=_PAYTM_SKIP_BASE_NORMALIZE,
    )


_PAYTM_EXTRA_HEADERS_JSON = (os.getenv("PAYTM_EXTRA_HEADERS_JSON") or "").strip()


def _completion_extra_headers() -> dict[str, str]:
    """
    Some CDN/WAFs block default Python/httpx user agents with HTML Access Denied.
    Paytm gateways may require extra headers — use PAYTM_EXTRA_HEADERS_JSON if documented.
    """
    headers: dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": os.getenv(
            "PAYTM_HTTP_USER_AGENT",
            "OpenAI/Python 1.0 (crewai-litellm; compatible)",
        ),
    }
    if _PAYTM_EXTRA_HEADERS_JSON:
        try:
            extra = json.loads(_PAYTM_EXTRA_HEADERS_JSON)
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if isinstance(k, str) and isinstance(v, str):
                        headers[k] = v
        except json.JSONDecodeError:
            raise RuntimeError(
                "PAYTM_EXTRA_HEADERS_JSON must be valid JSON object, "
                'e.g. {"X-Custom-Header": "value"}'
            ) from None
    return headers


def _validate_inference_env() -> None:
    """
    Fail fast with a clearer message than LiteLLM's generic "Connection error".
    Mirrors Windows error WinError 10051 / POSIX EAI_*: bad hostname → getaddrinfo.
    """
    key = _effective_paytm_api_key()
    raw_base = _raw_paytm_base_url()
    api_base = _effective_paytm_api_base()

    if not key:
        raise RuntimeError(
            "PAYTM_API_KEY is missing or empty in backend/.env. "
            "Set it to your inference gateway API key."
        )
    if "your_paytm" in key.lower() or "your-paytm" in key.lower():
        raise RuntimeError(
            "PAYTM_API_KEY still looks like a placeholder. Replace it with a real key."
        )

    if not raw_base:
        raise RuntimeError(
            "PAYTM_BASE_URL is missing or empty in backend/.env. Example: "
            "https://api.inference.paytm.com/v1 (exact path depends on your gateway)."
        )

    parsed = urlparse(
        api_base if api_base.startswith("http") else f"https://{api_base}"
    )
    host = parsed.hostname
    if not host:
        raise RuntimeError(
            f"PAYTM_BASE_URL is invalid: {raw_base!r}. Use a full URL with a hostname "
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

    _completion_extra_headers()


def make_llm(model: str, temperature: float = 0.7) -> LLM:
    """Create an LLM instance pointing at Paytm Inference."""
    return LLM(
        model=model,
        base_url=_effective_paytm_api_base(),
        api_base=_effective_paytm_api_base(),
        api_key=_effective_paytm_api_key(),
        temperature=temperature,
        extra_headers=_completion_extra_headers(),
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
    OpenAI-compatible API at PAYTM_BASE_URL. Override per-role with
    PAYTM_MODEL_PLANNER, PAYTM_MODEL_WRITER, PAYTM_MODEL_EDITOR, etc.;
    ids must be models assigned to your Paytm account or calls fail (403 / not available).

    HTML "Access Denied" from the gateway usually means wrong path (missing ``/v1``),
    bad API key formatting, blocked User-Agent — see PAYTM_SKIP_BASE_URL_NORMALIZE,
    PAYTM_HTTP_USER_AGENT, PAYTM_EXTRA_HEADERS_JSON in backend/.env.
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
                # Haiku/Bedrock-style ids often return "not assigned" on Paytm; override with PAYTM_MODEL_EDITOR.
                "editor",
                "openai/llama-3.3-70b-versatile",
            ),
            temperature=0.3,
        ),
    }
