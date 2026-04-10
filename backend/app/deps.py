"""
FastAPI dependency injection: auth, DB, settings.
"""

from typing import Annotated

import jwt
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
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return AuthenticatedUser(user_id=user_id, email=payload.get("email"))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
