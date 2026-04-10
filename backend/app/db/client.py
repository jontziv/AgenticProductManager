"""
Supabase client factory — uses the service role key (server-only).
Never expose service role key to the browser.
"""

from functools import lru_cache

import asyncpg
from supabase import create_client, Client

from app.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


_pool: asyncpg.Pool | None = None


async def get_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def close_db_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
