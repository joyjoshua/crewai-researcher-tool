"""
Supabase client — singleton created on first use (lazy).
Uses the service_role key so the backend bypasses RLS.

Lazy init lets ``uvicorn main:app`` start so ``/api/health`` works while you
fix credentials; any route that touches DB will raise until keys are valid.
"""

import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

_BACKEND_ROOT = Path(__file__).resolve().parent
load_dotenv(_BACKEND_ROOT / ".env")


class SupabaseConfigError(RuntimeError):
    """Invalid or missing Supabase configuration for the backend."""


def _strip_env(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().strip('"').strip("'")


def _jwt_payload_unverified(token: str) -> dict | None:
    """Decode Supabase JWT payload without verifying (role check only)."""
    parts = token.split(".")
    if len(parts) < 2:
        return None
    segment = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        raw = base64.urlsafe_b64decode(segment.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _assert_service_role_key(key: str) -> None:
    """
    PostgREST uses the key JWT role when using legacy anon/service_role JWTs.
    The anon key hits RLS; our ``jobs`` table needs the real service secret.

    Supabase newer **secret keys** (`sb_secret_…`) are not JWTs — skip role decode.
    Reject mistakenly using **publishable** keys in this env slot.
    """
    if key.startswith("sb_publishable_"):
        raise SupabaseConfigError(
            "SUPABASE_SERVICE_ROLE_KEY must be your **secret** API key (`sb_secret_…`), "
            "not the publishable key (`sb_publishable_…`). "
            "See Supabase → Project Settings → API."
        )
    if key.startswith("sb_secret_"):
        return

    payload = _jwt_payload_unverified(key)
    if not payload:
        return
    role = payload.get("role")
    if role == "anon":
        raise SupabaseConfigError(
            "SUPABASE_SERVICE_ROLE_KEY is set to the anon (legacy JWT) key. "
            "Use the service_role JWT or the sb_secret_… secret from Settings → API."
        )
    if role is not None and role != "service_role":
        raise SupabaseConfigError(
            f"SUPABASE_SERVICE_ROLE_KEY JWT has role={role!r}; expected 'service_role'."
        )


def _build_client() -> Client:
    url = _strip_env(os.getenv("SUPABASE_URL"))
    key = _strip_env(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    if not url or not key:
        raise SupabaseConfigError(
            "Missing Supabase config: set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY in backend/.env (Settings → API)."
        )
    _assert_service_role_key(key)
    try:
        return create_client(url, key)
    except Exception as e:
        raise SupabaseConfigError(
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
