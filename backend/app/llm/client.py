"""
Groq client with instructor for schema-validated structured outputs.
Every generation call goes through this module.
"""

import asyncio
import re
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

# Retry config for transient 5xx server errors only.
# TPM (per-minute) rate limits are caught separately and retried after the
# reported cooldown. TPD (daily) rate limits fail immediately — never retry.
# instructor has its own internal retry loop for schema validation; we cap it at
# 1 to prevent silent token multiplication when the model produces invalid JSON.
MAX_SERVER_RETRIES = 2
SERVER_RETRY_BACKOFF = 1.5  # seconds
INSTRUCTOR_MAX_RETRIES = 1

# Maximum seconds to wait on a TPM retry. The API reports the exact wait time;
# we cap it so a single call cannot stall a job indefinitely.
TPM_RETRY_MAX_WAIT = 65  # seconds
TPM_MAX_ATTEMPTS = 5


def _parse_retry_after(error_message: str) -> float | None:
    """Extract the retry-after seconds from a Groq 429 error message.

    Groq returns several formats:
      'Please try again in 35.91s'   → 35.91s
      'Please try again in 1m2.3s'   → 62.3s
      'Please try again in 280ms'    → 0.28s
    Returns seconds as a float, or None if the format is not recognised.
    """
    # Milliseconds: e.g. "280ms"
    ms = re.search(r"try again in (\d+(?:\.\d+)?)ms", error_message)
    if ms:
        return float(ms.group(1)) / 1000

    # Seconds with optional minutes prefix: e.g. "35.91s" or "1m2.3s"
    m = re.search(r"try again in (?:(\d+)m)?(\d+(?:\.\d+)?)s", error_message)
    if m:
        minutes = float(m.group(1) or 0)
        seconds = float(m.group(2))
        return minutes * 60 + seconds

    return None


def _is_tpm_error(exc: RateLimitError) -> bool:
    """Return True if this is a per-minute quota error (retryable)."""
    return "tokens per minute" in str(exc).lower()


def _is_tpd_error(exc: RateLimitError) -> bool:
    """Return True if this is the daily quota error (not retryable)."""
    return "tokens per day" in str(exc).lower()


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
    max_tokens: int = 2048,
    run_id: str | None = None,
    node_name: str | None = None,
) -> T:
    """
    Generate a structured output validated against response_model.

    Retry policy:
    - TPD (tokens per day): fail immediately — daily quota cannot be recovered by waiting.
    - TPM (tokens per minute): wait the reported cooldown, retry up to TPM_MAX_ATTEMPTS.
    - 5xx server errors: exponential backoff, up to MAX_SERVER_RETRIES.
    """
    model = get_model(role)
    log = logger.bind(model=model, node=node_name, run_id=run_id)

    tpm_attempt = 0

    while True:
        for server_attempt in range(MAX_SERVER_RETRIES):
            try:
                t0 = time.perf_counter()

                # instructor runs synchronously — run in thread pool.
                # max_retries=1 caps instructor's internal schema-validation retry loop.
                client = _get_instructor_client()
                result = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    response_model=response_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    max_retries=INSTRUCTOR_MAX_RETRIES,
                )

                duration_ms = (time.perf_counter() - t0) * 1000
                log.info(
                    "llm_call_success",
                    attempt=server_attempt + 1,
                    tpm_attempt=tpm_attempt,
                    duration_ms=round(duration_ms, 1),
                )
                return result

            except RateLimitError as exc:
                error_str = str(exc)

                if _is_tpd_error(exc):
                    # Daily quota exhausted — retrying wastes the remaining tokens.
                    # The job processor catches this and fails the job immediately.
                    log.error("tpd_limit_exceeded", node=node_name, run_id=run_id)
                    raise

                if _is_tpm_error(exc):
                    # Per-minute quota — temporary. Wait the reported cooldown.
                    tpm_attempt += 1
                    if tpm_attempt >= TPM_MAX_ATTEMPTS:
                        log.error(
                            "tpm_limit_exhausted",
                            node=node_name,
                            run_id=run_id,
                            attempts=tpm_attempt,
                        )
                        raise

                    parsed = _parse_retry_after(error_str)
                    # Floor at 1s so sub-second waits (e.g. "280ms") still give
                    # the sliding window time to tick over before retry.
                    wait = max(parsed + 1.0 if parsed is not None else 60.0, 1.0)
                    wait = min(wait, TPM_RETRY_MAX_WAIT)
                    log.warning(
                        "tpm_limit_hit_retrying",
                        node=node_name,
                        wait_s=wait,
                        attempt=tpm_attempt,
                    )
                    await asyncio.sleep(wait)
                    break  # exit inner server-retry loop → re-enter outer TPM loop

                # Unknown 429 flavour — fail immediately
                log.error("rate_limit_exceeded_unknown", node=node_name, run_id=run_id)
                raise

            except APIError as exc:
                if exc.status_code and exc.status_code >= 500:
                    backoff = SERVER_RETRY_BACKOFF ** (server_attempt + 1)
                    log.warning(
                        "groq_server_error",
                        attempt=server_attempt + 1,
                        backoff_s=backoff,
                    )
                    if server_attempt < MAX_SERVER_RETRIES - 1:
                        await asyncio.sleep(backoff)
                        continue
                log.error("llm_call_failed", attempt=server_attempt + 1, error=str(exc))
                raise

        else:
            # Server retry loop exhausted without TPM break
            raise RuntimeError(f"LLM call failed after {MAX_SERVER_RETRIES} server retries")


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
