"""
JWT verification middleware.
Validates the Supabase access token from the Authorization header
(or ?token= for browser EventSource, which cannot set headers).
Returns the authenticated user_id for use in endpoint handlers.
"""

import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")

JWT_SECRET = os.getenv("JWT_SECRET")

security = HTTPBearer()
optional_scheme = HTTPBearer(auto_error=False)


def _decode_user(token: str) -> str:
    if not JWT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: JWT_SECRET is not set",
        )
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no sub claim")
        return str(user_id)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(security)
    ],
) -> str:
    """Dependency — JWT from ``Authorization: Bearer``."""
    return _decode_user(credentials.credentials)


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
    return _decode_user(token)
