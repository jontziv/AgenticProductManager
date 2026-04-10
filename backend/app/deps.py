"""
FastAPI dependency injection: auth, DB, settings.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.db.client import get_supabase_client

bearer_scheme = HTTPBearer()


class AuthenticatedUser:
    def __init__(self, user_id: str, email: str | None = None):
        self.user_id = user_id
        self.email = email


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    token = credentials.credentials
    try:
        # Use Supabase admin client to validate the token — works for both
        # HS256 (legacy) and ES256 (current default) JWT algorithms.
        supabase = get_supabase_client()
        response = supabase.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = response.user
        return AuthenticatedUser(user_id=str(user.id), email=user.email)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
