"""
Supabase client — singleton created on first use (lazy).
Uses the service_role key so the backend bypasses RLS.

Lazy init lets ``uvicorn main:app`` start so ``/api/health`` works while you
fix credentials; any route that touches DB will raise until keys are valid.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

_BACKEND_ROOT = Path(__file__).resolve().parent
load_dotenv(_BACKEND_ROOT / ".env")


def _strip_env(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().strip('"').strip("'")


def _build_client() -> Client:
    url = _strip_env(os.getenv("SUPABASE_URL"))
    key = _strip_env(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    if not url or not key:
        raise RuntimeError(
            "Missing Supabase config: set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY in backend/.env (Settings → API)."
        )
    try:
        return create_client(url, key)
    except Exception as e:
        raise RuntimeError(
            f"Supabase init failed ({e!s}). Use the project URL and the "
            "**service_role** secret (not anon), with no extra quotes or spaces."
        ) from e


class _SupabaseProxy:
    """Forwards to sync Client; connects on first attribute use."""

    __slots__ = ("_client",)

    def __init__(self) -> None:
        self._client: Client | None = None

    def _get(self) -> Client:
        if self._client is None:
            self._client = _build_client()
        return self._client

    def __getattr__(self, name: str):
        return getattr(self._get(), name)


supabase: Client = _SupabaseProxy()  # type: ignore[assignment]
