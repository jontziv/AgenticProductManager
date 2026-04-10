# Agentic Intake-to-Backlog Workbench

A workflow application for product managers. Submit meeting notes, requirements, and ideas — get back structured PM artifacts, QA-reviewed, approved, and export-ready.

This is not a chat app. It is a staged workflow product with forms, orchestration, approvals, and exportable deliverables backed by a real LangGraph state machine calling Groq.

## What it produces

From raw input it generates:

1. Problem framing (statement, opportunity, hypothesis)
2. User personas (goals, pain points, behaviors)
3. MVP scope (in/out of scope, core features)
4. Success metrics (leading + lagging, with targets)
5. User stories + acceptance criteria
6. Backlog items (epic-organized)
7. Test cases
8. Risk checklist + mitigations
9. Architecture recommendation (2 options, 1 recommended)
10. QA/evaluation report (scored, with hard-fail gating)
11. Export pack (Markdown, JSON, PDF-ready HTML)

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + React Router v7 |
| UI | Tailwind CSS v4 + shadcn/ui + Radix UI |
| Backend API | Python 3.12 + FastAPI |
| Orchestration | LangGraph 0.2 |
| LLM | Groq (llama-3.1-8b-instant, llama-3.3-70b-versatile) |
| Auth + DB + Storage | Supabase |
| Background jobs | DB-backed queue + Render worker |
| Deployment | Vercel (frontend) + Render (API + worker) |

## Local development

See [docs/runbooks/local-dev.md](docs/runbooks/local-dev.md) for full setup.

**Quick start:**

```bash
# 1. Copy environment template
cp .env.example .env
# Fill in VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, GROQ_API_KEY, etc.

# 2. Install frontend dependencies
pnpm install

# 3. Start frontend dev server
pnpm dev

# 4. In a separate terminal — start backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 5. In a separate terminal — start worker
cd backend
source .venv/bin/activate
python -m worker.main

# 6. Run Supabase migrations (requires supabase CLI)
supabase db push
```

## Project structure

```
.
├── src/                    # React + TypeScript frontend (Vite)
│   └── app/
│       ├── api/            # Typed API client
│       ├── components/     # Auth, Dashboard, Workflow steps, UI primitives
│       ├── context/        # AuthContext, WorkflowContext
│       └── hooks/          # useJobPolling, useAutosave
├── backend/
│   ├── app/
│   │   ├── api/v1/         # FastAPI routes
│   │   ├── graph/          # LangGraph state machine
│   │   ├── llm/            # Groq client + model routing
│   │   ├── prompts/        # Prompt registry + templates
│   │   ├── evaluators/     # QA harness + rubric
│   │   ├── models/         # Pydantic schemas
│   │   ├── db/             # Supabase client + queries
│   │   └── services/       # Business logic
│   ├── worker/             # Background job processor
│   └── tests/
├── supabase/
│   ├── migrations/         # SQL migrations with RLS
│   └── seed.sql
├── skills/                 # Claude Code skills
├── docs/                   # Architecture, ADRs, standards, runbooks
└── .github/workflows/      # CI/CD
```

## Testing

```bash
# Backend unit + integration tests
cd backend && pytest

# Frontend type check
pnpm typecheck

# E2E tests (requires running stack)
pnpm test:e2e
```

## Deployment

See [docs/runbooks/deploy.md](docs/runbooks/deploy.md) for Vercel + Render deployment.

## Documentation

- [Architecture](docs/architecture.md)
- [ADRs](docs/adr/)
- [Standards](docs/standards/)
- [Local dev guide](docs/runbooks/local-dev.md)
- [Deploy guide](docs/runbooks/deploy.md)
- [Troubleshooting](docs/runbooks/troubleshooting.md)
