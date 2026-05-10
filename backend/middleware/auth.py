"""
JWT verification middleware.
Validates the Supabase access token from the Authorization header.
Returns the authenticated user_id for use in endpoint handlers.
"""

import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Dependency that extracts and validates the JWT from the Authorization header.
    Returns the user_id (sub claim) as a string.
    """
    if not JWT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: JWT_SECRET is not set",
        )
    token = credentials.credentials
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
        return user_id
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
