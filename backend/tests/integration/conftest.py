"""
Integration test fixtures.
Provides an AsyncClient wired to the real FastAPI app and two sets of auth headers
(representing two distinct users) for isolation tests.
"""

import os
import pytest
import pytest_asyncio
import jwt
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# App import (env must be set before this)
# ---------------------------------------------------------------------------

def _make_jwt(user_id: str) -> str:
    """Mint a Supabase-shaped JWT signed with the test secret."""
    secret = os.environ["SUPABASE_JWT_SECRET"]
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "email": f"{user_id[:8]}@test.example",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest_asyncio.fixture(scope="session")
async def test_client():
    """Single AsyncClient for the whole integration test session."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture(scope="session")
def _user_a_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture(scope="session")
def _user_b_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture(scope="session")
def auth_headers(_user_a_id: str) -> dict:
    token = _make_jwt(_user_a_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def other_auth_headers(_user_b_id: str) -> dict:
    token = _make_jwt(_user_b_id)
    return {"Authorization": f"Bearer {token}"}
