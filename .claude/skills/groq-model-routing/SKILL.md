---
name: groq-model-routing
description: Selects the right Groq model for a given task type using the ModelRole enum and lru_cached routing table. Covers FAST, STRUCTURED, SYNTHESIS, EVAL, and AUDIO roles.
triggers:
  - "which model should I use"
  - "model routing"
  - "groq model"
  - "choose model"
  - "llm routing"
---

# Groq Model Routing

## What this skill does
Picks the correct Groq model for each step in the pipeline. One `get_model()` call is all you need.

## Quick reference

| ModelRole    | Default model                  | Use for                                          |
|--------------|-------------------------------|--------------------------------------------------|
| FAST         | llama-3.1-8b-instant          | classify, detect_missing, choose_pattern         |
| STRUCTURED   | llama-3.3-70b-versatile       | extract_structured_intake, generate_personas     |
| SYNTHESIS    | llama-3.3-70b-versatile       | problem_frame, mvp_scope, consistency_check      |
| EVAL         | llama-3.3-70b-versatile       | (reserved for LLM-based QA; currently deterministic) |
| AUDIO        | whisper-large-v3-turbo        | transcribe_audio                                 |

## Usage

```python
from app.llm.routing import get_model, ModelRole

model = get_model(ModelRole.FAST)       # "llama-3.1-8b-instant"
model = get_model(ModelRole.SYNTHESIS)  # "llama-3.3-70b-versatile"
```

## Override via env vars

```bash
GROQ_MODEL_FAST=llama-3.1-8b-instant
GROQ_MODEL_STRUCTURED=llama-3.3-70b-versatile
GROQ_MODEL_SYNTHESIS=llama-3.3-70b-versatile
GROQ_MODEL_EVAL=llama-3.3-70b-versatile
GROQ_MODEL_AUDIO=whisper-large-v3-turbo
```

Set in `.env` or platform environment. Changes require app restart (lru_cache cleared at startup).

## Task → ModelRole mapping

```python
TASK_MODEL_GUIDE = {
    "classify":              ModelRole.FAST,
    "detect_missing":        ModelRole.FAST,
    "choose_pattern":        ModelRole.FAST,
    "extract_intake":        ModelRole.STRUCTURED,
    "generate_personas":     ModelRole.STRUCTURED,
    "generate_stories":      ModelRole.STRUCTURED,
    "generate_tests":        ModelRole.STRUCTURED,
    "generate_risks":        ModelRole.STRUCTURED,
    "problem_frame":         ModelRole.SYNTHESIS,
    "mvp_scope":             ModelRole.SYNTHESIS,
    "success_metrics":       ModelRole.SYNTHESIS,
    "architecture":          ModelRole.SYNTHESIS,
    "consistency_check":     ModelRole.SYNTHESIS,
    "transcribe_audio":      ModelRole.AUDIO,
}
```

## Calling generate_structured

```python
from app.llm.client import generate_structured
from app.llm.routing import get_model, ModelRole
from app.prompts.registry import get_prompt
from app.schemas.personas import PersonasOutput

result: PersonasOutput = await generate_structured(
    model=get_model(ModelRole.STRUCTURED),
    prompt_name="personas",
    response_model=PersonasOutput,
    variables={"intake": state["intake"], "problem_framing": state["problem_framing"]},
)
```

## Retry behaviour
`generate_structured` retries up to 3 times with exponential backoff (`1.5^attempt` seconds) on:
- Groq `RateLimitError`
- HTTP 5xx responses

After 3 failures, raises the original exception — the worker marks the job as failed and increments retry_count.

## Adding a new model
1. Add a new `ModelRole` enum value in `app/llm/routing.py`
2. Add a corresponding `groq_model_<role>` field to `app/config.py` Settings
3. Add the env var to `.env.example`
4. Update `TASK_MODEL_GUIDE` with the new task mappings
5. Update this skill file
