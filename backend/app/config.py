"""
Application configuration with startup validation.
All values come from environment variables — never hardcoded.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: Literal["local", "preview", "staging", "production"] = "local"
    log_level: str = "INFO"

    # ── Supabase ──────────────────────────────────────────────────────────────
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    database_url: str

    # ── Groq ──────────────────────────────────────────────────────────────────
    groq_api_key: str
    # The Groq SDK appends /openai/v1 internally — base_url must be the root only.
    groq_base_url: str = "https://api.groq.com"

    # Model routing defaults
    groq_model_fast: str = "llama-3.1-8b-instant"
    groq_model_structured: str = "llama-3.1-8b-instant"
    groq_model_synthesis: str = "llama-3.1-8b-instant"
    groq_model_eval: str = "llama-3.1-8b-instant"
    groq_model_audio: str = "whisper-large-v3-turbo"
    groq_model_audio_fallback: str = "whisper-large-v3"

    # ── LangSmith (optional) ──────────────────────────────────────────────────
    langsmith_enabled: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "pm-sidekick"

    # ── OpenTelemetry (optional) ──────────────────────────────────────────────
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "pm-sidekick-api"

    # ── Worker ────────────────────────────────────────────────────────────────
    worker_poll_interval_seconds: int = 5
    worker_max_retries: int = 3
    worker_concurrency: int = 2
    # Runs the worker loop inside the API process (single-instance deployment).
    # Set EMBEDDED_WORKER=false only when deploying a separate worker service.
    embedded_worker: bool = True

    # ── Export ────────────────────────────────────────────────────────────────
    export_storage_bucket: str = "exports"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins, e.g.
    # "https://pm-sidekick.vercel.app,https://pm-sidekick-preview.vercel.app"
    # Defaults to "*" (all origins). Auth is Bearer token — no cookies used.
    allowed_origins: str = "*"

    # ── Rate limiting ─────────────────────────────────────────────────────────
    api_rate_limit_per_minute: int = 60

    @field_validator("groq_api_key")
    @classmethod
    def groq_key_not_placeholder(cls, v: str) -> str:
        if v == "gsk_replace_me" or not v.strip():
            raise ValueError("GROQ_API_KEY must be set to a real key")
        return v

    @field_validator("supabase_service_role_key")
    @classmethod
    def supabase_key_not_placeholder(cls, v: str) -> str:
        if "replace_me" in v or not v.strip():
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY must be set")
        return v

    @model_validator(mode="after")
    def langsmith_key_required_when_enabled(self) -> "Settings":
        if self.langsmith_enabled and not self.langsmith_api_key:
            raise ValueError("LANGSMITH_API_KEY required when LANGSMITH_ENABLED=true")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
