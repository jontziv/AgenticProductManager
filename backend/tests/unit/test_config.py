"""
Unit tests for config validation.
Ensures startup fails fast on missing/invalid env vars.
"""

import os
import pytest
from pydantic import ValidationError


def test_missing_groq_key_raises():
    """GROQ_API_KEY placeholder should raise at Settings init."""
    from app.config import Settings
    with pytest.raises((ValidationError, ValueError)):
        Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="real-key-here",
            supabase_jwt_secret="secret",
            database_url="postgresql://localhost/test",
            groq_api_key="gsk_replace_me",  # placeholder
        )


def test_placeholder_supabase_key_raises():
    """Supabase placeholder key should raise."""
    from app.config import Settings
    with pytest.raises((ValidationError, ValueError)):
        Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="replace_me",
            supabase_jwt_secret="secret",
            database_url="postgresql://localhost/test",
            groq_api_key="gsk_real_key",
        )


def test_langsmith_enabled_without_key_raises():
    """Enabling LangSmith without API key should raise."""
    from app.config import Settings
    with pytest.raises((ValidationError, ValueError)):
        Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="real-key",
            supabase_jwt_secret="secret",
            database_url="postgresql://localhost/test",
            groq_api_key="gsk_real_key",
            langsmith_enabled=True,
            langsmith_api_key="",  # empty
        )


def test_model_routing_defaults_from_settings():
    """Model routing should use env var overrides."""
    from app.config import get_settings
    from app.llm.routing import get_model, ModelRole, get_model_routing
    import functools
    # Clear lru_cache to pick up any env changes
    get_model_routing.cache_clear()
    routing = get_model_routing()
    assert routing[ModelRole.FAST] == get_settings().groq_model_fast
    assert routing[ModelRole.SYNTHESIS] == get_settings().groq_model_synthesis
