---
name: groq-model-routing
description: Choose Groq models for fast extraction, strict JSON, deep synthesis, QA, and optional research while keeping cost low.
user-invocable: false
---

Use Groq through a provider adapter. Prefer the cheapest model that satisfies the task.

## Routing rules
- Prefer strict structured outputs for canonical JSON artifacts.
- Prefer smaller fast models for cleanup, tagging, and extraction.
- Use stronger models only for nuanced synthesis, architecture tradeoffs, or QA.
- Avoid preview models in production unless explicitly approved.
- Verify active model availability at runtime if a model call fails or is unavailable.

## Defaults
- Fast transforms -> `llama-3.1-8b-instant`
- Strict JSON artifacts -> `openai/gpt-oss-20b`
- Higher-quality synthesis -> `llama-3.3-70b-versatile`
- Hardest evaluation/remediation -> `openai/gpt-oss-120b`
- Optional tool-augmented research -> `groq/compound-mini`

## Structured output policy
For canonical app artifacts, prefer schema-validated output. Use strict mode where supported. Keep all fields required and set `additionalProperties: false`.

## Routing table
Load `model-routing.md` when choosing or changing model assignments.
