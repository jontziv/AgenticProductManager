"""
Groq client with instructor for schema-validated structured outputs.
Every generation call goes through this module.
"""

import asyncio
import time
from typing import TypeVar, Type
from functools import lru_cache

import instructor
import structlog
from groq import Groq, APIError, RateLimitError
from pydantic import BaseModel

from app.config import get_settings
from app.llm.routing import ModelRole, get_model

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# Retry config
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds


@lru_cache(maxsize=1)
def _get_groq_client() -> Groq:
    settings = get_settings()
    return Groq(api_key=settings.groq_api_key, base_url=settings.groq_base_url)


@lru_cache(maxsize=1)
def _get_instructor_client() -> instructor.Instructor:
    return instructor.from_groq(_get_groq_client(), mode=instructor.Mode.JSON)


async def generate_structured(
    messages: list[dict],
    response_model: Type[T],
    role: ModelRole = ModelRole.STRUCTURED,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    run_id: str | None = None,
    node_name: str | None = None,
) -> T:
    """
    Generate a structured output validated against response_model.
    Retries on transient errors with exponential backoff.
    """
    model = get_model(role)
    log = logger.bind(model=model, node=node_name, run_id=run_id)

    for attempt in range(MAX_RETRIES):
        try:
            t0 = time.perf_counter()

            # instructor runs synchronously — run in thread pool
            client = _get_instructor_client()
            result = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                response_model=response_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            duration_ms = (time.perf_counter() - t0) * 1000
            log.info(
                "llm_call_success",
                attempt=attempt + 1,
                duration_ms=round(duration_ms, 1),
            )
            return result

        except RateLimitError:
            backoff = RETRY_BACKOFF_BASE ** (attempt + 1)
            log.warning("rate_limited", attempt=attempt + 1, backoff_s=backoff)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
            else:
                raise

        except APIError as exc:
            if exc.status_code and exc.status_code >= 500:
                backoff = RETRY_BACKOFF_BASE ** (attempt + 1)
                log.warning("groq_server_error", attempt=attempt + 1, backoff_s=backoff)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(backoff)
                    continue
            log.error("llm_call_failed", attempt=attempt + 1, error=str(exc))
            raise

    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts")


async def transcribe_audio(audio_bytes: bytes, filename: str, run_id: str | None = None) -> str:
    """Transcribe audio using Whisper via Groq. Falls back to higher-fidelity model on failure."""
    import io

    settings = get_settings()
    client = _get_groq_client()
    log = logger.bind(run_id=run_id, filename=filename)

    for model in [settings.groq_model_audio, settings.groq_model_audio_fallback]:
        try:
            result = await asyncio.to_thread(
                client.audio.transcriptions.create,
                file=(filename, io.BytesIO(audio_bytes)),
                model=model,
                response_format="text",
            )
            log.info("transcription_success", model=model)
            return result  # type: ignore[return-value]
        except APIError as exc:
            log.warning("transcription_failed", model=model, error=str(exc))
            if model == settings.groq_model_audio_fallback:
                raise

    raise RuntimeError("Audio transcription failed on all models")
