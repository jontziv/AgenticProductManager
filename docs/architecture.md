# Architecture — PM Sidekick

## System overview

PM Sidekick converts raw stakeholder input into a reviewed, exportable PM artifact set. The system is workflow-first: deterministic staged execution, human-in-the-loop approval, QA gating before export.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Vercel (Frontend)                        │
│  React + TypeScript + Vite                                      │
│  Radix UI / shadcn / Tailwind                                   │
│  Supabase JS Auth client                                        │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTPS + Bearer JWT
┌────────────────────▼────────────────────────────────────────────┐
│                   Render (API service)                           │
│  FastAPI + uvicorn (2 workers)                                  │
│  JWT verification (HS256, supabase_jwt_secret)                  │
│  asyncpg connection pool → Postgres                             │
│  Enqueues jobs into queued_jobs table                           │
└──────────────┬──────────────────────────────────────────────────┘
               │ shared Postgres DB
┌──────────────▼──────────────────────────────────────────────────┐
│                  Render (Worker service)                         │
│  Python asyncio polling loop                                    │
│  SELECT FOR UPDATE SKIP LOCKED                                  │
│  Runs LangGraph pipeline per job                                │
│  Calls Groq API for LLM steps                                   │
│  Writes artifacts + QA report back to DB                        │
└──────────────┬──────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────┐
│  Supabase                                                        │
│  ├── Auth (JWT issuance, magic link)                            │
│  ├── Postgres (app data, all tables)                            │
│  └── Storage (exports bucket, private, pre-signed URLs)         │
└─────────────────────────────────────────────────────────────────┘
               │ GROQ_API_KEY
┌──────────────▼──────────────────────────────────────────────────┐
│  Groq API                                                        │
│  llama-3.1-8b-instant     (FAST: classify, detect_missing)      │
│  llama-3.3-70b-versatile  (STRUCTURED/SYNTHESIS: all generators)│
│  whisper-large-v3-turbo   (AUDIO: transcription)                │
└─────────────────────────────────────────────────────────────────┘
```

## LangGraph pipeline

The worker executes a 14-node LangGraph state machine per run. The graph is compiled once at startup and reused (singleton via `get_graph()`).

```
sanitize_input
    │
extract_structured_intake
    │
classify_idea_type ──────── FAST model
    │
detect_missing_data ──────── FAST model
    │                │
    │         [critical missing]
    │                │
    │         request_human_input ←── STOPS graph (stores partial state)
    │
generate_problem_frame ──── SYNTHESIS
    │
generate_personas ────────── STRUCTURED
    │
generate_mvp_scope ────────── SYNTHESIS
    │
generate_success_metrics ─── SYNTHESIS
    │
generate_stories_and_backlog  STRUCTURED
    │
generate_test_cases ────────── STRUCTURED
    │
generate_risks ────────────── STRUCTURED
    │
generate_architecture_options  SYNTHESIS
    │
run_qa_evaluation ─────────── (deterministic, no LLM)
    │               │
    │         [hard fails]
    │               │
    │         create_remediation_tasks_if_needed
    │               │ (max 3 attempts, then force to human review)
    │               └──────────────────────┐
    │                                      │
    └──────────────────────────────────────▼
                        human_review_gate ←── interrupt_before (waits for UI approval)
                                │
                        export_pack_node ─── generates all 5 formats, uploads to Storage
```

### State keys
`run_id, user_id, intake, classification, assumptions, brief, personas, scope, metrics, backlog, test_cases, risks, architecture, qa_report, approvals, export_pack, remediation_attempts, missing_fields`

### Checkpointing
Uses `MemorySaver` for MVP (in-process). Thread ID = `run_id`. Resume is supported across HTTP requests via `astream(None, config)` after `aupdate_state()`.

Production upgrade path: swap `MemorySaver` for `langgraph.checkpoint.postgres.AsyncPostgresSaver` with the same `DATABASE_URL`.

## Database schema

8 tables, all with `user_id` FK and RLS enabled:

| Table | Purpose |
|-------|---------|
| `intake_runs` | One row per submitted idea; tracks status lifecycle |
| `artifacts` | Versioned PM artifact content (JSONB); append-only |
| `approvals` | Human approval decision (one per run) |
| `qa_reports` | Latest QA evaluation result (one per run, upserted) |
| `queued_jobs` | DB-backed async job queue |
| `export_records` | Export job tracking + Storage path |
| `stale_markers` | Tracks which artifacts need regeneration |
| `user_profiles` | App-level user metadata |

See `supabase/migrations/` for full DDL.

## Artifact versioning

Artifacts are **append-only** — each regeneration inserts a new row with `version + 1`. Queries for "current" artifacts use:

```sql
SELECT DISTINCT ON (artifact_type) *
FROM artifacts WHERE run_id = $1
ORDER BY artifact_type, version DESC;
```

When an upstream artifact changes, downstream artifacts are marked stale via `stale_markers` and a `regenerate_artifact` job is enqueued for each.

## Job queue

The worker polls `queued_jobs` every 2 seconds using `SELECT FOR UPDATE SKIP LOCKED`. This ensures exactly-once processing across multiple worker instances without Redis or a separate queue service.

Job types: `orchestrate_run | regenerate_artifact | generate_export`

Retry logic: up to `worker_max_retries` (default 3) on transient failures. After max retries, the run status is set to `failed`.

## Export formats

| Format | Content type | Notes |
|--------|-------------|-------|
| markdown | `text/markdown` | Human-readable summary |
| json | `application/json` | Full artifact set as structured JSON |
| html | `text/html` | CSS-print-ready for PDF conversion |
| jira_csv | `text/csv` | One row per user story, Jira import format |
| linear_csv | `text/csv` | Linear import format |

Files are uploaded to Supabase Storage bucket `exports` under `{user_id}/{run_id}/{format}.{ext}`. Download URLs are pre-signed (1-hour TTL).

## Security

- All secrets in environment variables only — never committed
- JWT verification: `python-jose` HS256 with `SUPABASE_JWT_SECRET`
- RLS on all tables — service role for server, anon/authenticated for client
- No user-controlled SQL or template injection points
- Structured logging — no raw tokens or sensitive payloads logged
- CORS restricted to `ALLOWED_ORIGINS` env var (defaults to `localhost:5173` in local)
