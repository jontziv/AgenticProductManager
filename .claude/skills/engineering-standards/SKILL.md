---
name: engineering-standards
description: Coding standards, file organization conventions, error handling patterns, and PR review checklist for the PM Sidekick codebase.
triggers:
  - "code style"
  - "conventions"
  - "how should I structure"
  - "engineering standards"
  - "code review"
  - "pr checklist"
---

# Engineering Standards

## Python (backend)

### Style
- Python 3.12+, type hints everywhere
- `ruff` for linting + import sorting (line length 100)
- `mypy` non-strict (ignore_missing_imports = true)
- No `print()` — use `structlog.get_logger()` 

### Patterns
```python
# ✅ DO: typed function signatures
async def get_run(run_id: UUID, user_id: UUID) -> IntakeRun | None:
    ...

# ✅ DO: structlog for all logging
logger = structlog.get_logger()
logger.info("job.started", job_id=job_id, run_id=run_id)

# ✅ DO: Pydantic models at all API boundaries
class CreateRunPayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    raw_input: str = Field(..., min_length=10)

# ❌ DON'T: hardcode secrets or model names
model = "llama-3.1-8b-instant"  # use get_model(ModelRole.FAST) instead

# ❌ DON'T: bare except
try:
    ...
except Exception:  # too broad — catch specific exceptions
    ...
```

### File organization
```
backend/
├── app/
│   ├── config.py           # Settings (pydantic-settings)
│   ├── deps.py             # FastAPI dependencies (auth, db)
│   ├── main.py             # FastAPI app, lifespan, middleware
│   ├── db/
│   │   ├── pool.py         # asyncpg pool
│   │   └── queries.py      # DB query classes (RunsDB, ArtifactsDB, etc.)
│   ├── evaluators/
│   │   ├── harness.py      # run_qa_evaluation()
│   │   └── rubric.py       # CheckDef, HARD_FAIL_IDS
│   ├── graph/
│   │   ├── graph.py        # build_graph(), get_graph() singleton
│   │   ├── state.py        # WorkflowState TypedDict
│   │   └── nodes/
│   │       ├── ingest.py   # sanitize, extract, classify, detect_missing, choose_pattern
│   │       ├── generate.py # all 10 artifact generators
│   │       └── qa.py       # qa_evaluation, remediation_router, human_review_gate, export_pack
│   ├── llm/
│   │   ├── client.py       # generate_structured(), transcribe_audio()
│   │   └── routing.py      # ModelRole enum, get_model(), get_model_routing()
│   ├── prompts/
│   │   └── registry.py     # PromptTemplate instances, get_prompt()
│   ├── routers/
│   │   ├── runs.py         # /api/v1/runs
│   │   ├── jobs.py         # /api/v1/runs/{id}/jobs
│   │   └── exports.py      # /api/v1/runs/{id}/exports
│   ├── schemas/            # Pydantic output models (one per artifact type)
│   └── services/
│       └── export_service.py  # _artifacts_to_markdown, _artifacts_to_jira_csv, generate_export_pack
└── worker/
    ├── main.py             # asyncio polling loop, signal handlers
    └── processor.py        # process_job(), _orchestrate_run(), _regenerate_artifact()
```

## TypeScript (frontend)

### Style
- TypeScript strict mode off (strictNullChecks on)
- All API response shapes typed in `src/app/types/api.ts`
- Prefer `const` over `let`; avoid `any`
- Use Tailwind for all styling — no inline style objects

### Patterns
```typescript
// ✅ DO: typed API calls with error handling
try {
  const run = await runsApi.create(payload);
  navigate(`/runs/${run.id}`);
} catch (err) {
  if (err instanceof ApiClientError) toast.error(err.message);
}

// ✅ DO: explicit loading and error states
const [isLoading, setIsLoading] = useState(false);
const [error, setError] = useState<string | null>(null);

// ❌ DON'T: mutate context state directly
state.run = updatedRun;  // use setRun() from context instead

// ❌ DON'T: fetch in render
function Component() {
  const data = await fetch(...);  // use useEffect or React Query
}
```

## API design

- All routes under `/api/v1/`
- Resource naming: plural nouns (`/runs`, `/artifacts`, `/jobs`)
- Return 201 on create, 200 on update, 204 on delete with no body
- Return 404 (not 403) when a user lacks access to a resource — don't leak existence
- Return 409 when business logic prevents an action (export on unapproved run)
- Return 422 for schema validation failures (FastAPI default)
- All list endpoints return `{"items": [...], "total": N}`

## PR review checklist

Before merging any PR:
- [ ] No hardcoded secrets, API keys, or model names
- [ ] New DB queries use parameterized values (no string interpolation)
- [ ] New endpoints have auth dependency (`CurrentUser`)
- [ ] New artifacts have QA rubric coverage
- [ ] New config fields are in `.env.example` with placeholders
- [ ] Unit tests cover new logic
- [ ] `ruff check` + `mypy` pass
- [ ] `tsc --noEmit` passes
- [ ] `CLAUDE.md` updated if architecture changed
