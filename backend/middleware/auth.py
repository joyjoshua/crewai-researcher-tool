"""
JWT verification middleware.
Validates Supabase access tokens from ``Authorization: Bearer`` (or ``?token=`` for SSE).

Primary path: Supabase Auth ``GET /auth/v1/user`` — no need to copy JWT Secret into this app.
Fallback: local HS256 decode with ``JWT_SECRET`` (must match Supabase JWT Secret in dashboard).
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Annotated

import httpx
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")

logger = logging.getLogger(__name__)

security = HTTPBearer()
optional_scheme = HTTPBearer(auto_error=False)


def _canonical_user_uuid(uid: str) -> str:
    """Normalise UUID for PostgreSQL FK (``auth.users.id`` matches string form)."""
    try:
        return str(uuid.UUID(str(uid).strip()))
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid user id format") from e


def _strip_env(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().strip('"').strip("'")


async def _user_id_via_supabase_auth_api(token: str) -> str | None:
    """Ask Supabase Auth if the access token is valid; return user id or None."""
    url_base = _strip_env(os.getenv("SUPABASE_URL"))
    api_key = _strip_env(os.getenv("SUPABASE_ANON_KEY")) or _strip_env(
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    if not url_base or not api_key:
        return None

    verify_url = f"{url_base.rstrip('/')}/auth/v1/user"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                verify_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": api_key,
                },
                timeout=15.0,
            )
        if r.status_code != 200:
            return None
        data = r.json()
        uid = data.get("id")
        return str(uid) if uid else None
    except httpx.HTTPError as e:
        logger.warning("Supabase token verify request failed: %s", e)
        return None


def _user_id_via_local_jwt_hs256(token: str) -> str:
    secret = _strip_env(os.getenv("JWT_SECRET"))
    if not secret:
        raise HTTPException(
            status_code=500,
            detail=(
                "Auth misconfiguration: set JWT_SECRET to your Supabase JWT Secret, "
                "or configure SUPABASE_URL with SUPABASE_ANON_KEY or "
                "SUPABASE_SERVICE_ROLE_KEY for token verification."
            ),
        )
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no sub claim")
        return str(user_id)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}") from e


async def _resolve_user_id(token: str) -> str:
    remote = await _user_id_via_supabase_auth_api(token)
    if remote:
        return _canonical_user_uuid(remote)
    if _strip_env(os.getenv("JWT_SECRET")):
        return _canonical_user_uuid(_user_id_via_local_jwt_hs256(token))
    raise HTTPException(
        status_code=401,
        detail=(
            "Invalid or expired session (or auth not configured). "
            "Sign out and sign in again. For the backend, set SUPABASE_URL and "
            "SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY, or set JWT_SECRET "
            "to match Supabase Dashboard → Settings → API → JWT Secret."
        ),
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(security)
    ],
) -> str:
    """Dependency — JWT from ``Authorization: Bearer``."""
    return await _resolve_user_id(credentials.credentials)


async def get_current_user_sse(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(optional_scheme)
    ] = None,
) -> str:
    """SSE friendly: Bearer header or ``token`` query parameter (EventSource)."""
    token = credentials.credentials if credentials else None
    if not token:
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await _resolve_user_id(token)
