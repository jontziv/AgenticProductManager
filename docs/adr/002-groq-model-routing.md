# ADR-002: Groq as sole LLM provider with explicit model routing

**Status:** Accepted  
**Date:** 2026-04-10

## Context

The system requires LLM calls for ~10 pipeline nodes. Choices:

1. **OpenAI GPT-4o / GPT-4o-mini** — industry standard, wide tooling. Cost: ~$0.01-0.15 per 1K tokens. Rate limits require careful management.
2. **Anthropic Claude (via API)** — strong reasoning. Cost similar to OpenAI. No open-weights fallback.
3. **Groq (hosted inference)** — extremely fast inference on llama open-weights models. Free tier generous. Two relevant models available.
4. **Self-hosted Llama** — zero variable cost, but requires GPU infra ($600+/month) — ruled out for MVP.
5. **Multi-provider with fallback** — adds complexity, different output formats, harder to test deterministically.

## Decision

Use **Groq exclusively** as the LLM provider, with two models behind a `ModelRole` enum:

- `ModelRole.FAST` → `llama-3.1-8b-instant`: classify, detect_missing, choose_pattern
- `ModelRole.STRUCTURED` / `ModelRole.SYNTHESIS` → `llama-3.3-70b-versatile`: all artifact generators
- `ModelRole.AUDIO` → `whisper-large-v3-turbo`: audio transcription

Model names are env-var overridable. A single `generate_structured()` function wraps Groq via `instructor` for Pydantic-validated structured output.

## Consequences

**Positive:**
- Groq free tier covers development + low-volume production
- `llama-3.1-8b-instant` fast enough for classify/detect steps (<1s)
- `instructor` + Pydantic ensures all LLM outputs are typed and validated
- Single provider = simpler config, single retry strategy, easier testing (one mock point)
- Open-weights models: can switch to self-hosted later without prompt changes

**Negative:**
- Groq rate limits (free tier: 30 req/min per model) may throttle at scale
- If Groq is down, entire pipeline is blocked (no fallback)
- `llama-3.3-70b-versatile` output quality is below GPT-4o for complex synthesis tasks

**Mitigation:**
- `generate_structured()` retries 3x with exponential backoff on `RateLimitError`
- Worker `WORKER_CONCURRENCY` defaults to 3 — limiting simultaneous Groq calls
- Swap to another provider by implementing a new `generate_structured` adapter — the rest of the codebase only sees `ModelRole` enums and Pydantic models
