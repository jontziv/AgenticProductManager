# Local Development Setup

## Prerequisites

- Node.js 22+
- Python 3.12+
- Docker Desktop (for Supabase local)
- Supabase CLI: `brew install supabase/tap/supabase`
- Groq API key: https://console.groq.com

## First-time setup

### 1. Clone and install

```bash
git clone <repo>
cd AgenticProductManager

# Frontend dependencies
npm install

# Backend dependencies
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cd ..
```

### 2. Start Supabase locally

```bash
supabase start
# Outputs: API URL, anon key, service_role key, JWT secret
```

### 3. Apply migrations and seed

```bash
supabase db reset
# OR manually:
psql postgresql://postgres:postgres@localhost:54322/postgres \
  -f supabase/migrations/001_initial_schema.sql \
  -f supabase/migrations/002_rls_policies.sql \
  -f supabase/migrations/003_indexes.sql \
  -f supabase/seed.sql
```

### 4. Configure environment

```bash
# Copy example env
cp .env.example .env
cp backend/.env.example backend/.env

# Edit .env with values from `supabase start` output:
VITE_SUPABASE_URL=http://localhost:54321
VITE_SUPABASE_ANON_KEY=<anon key from supabase start>
VITE_API_BASE_URL=http://localhost:8000

# Edit backend/.env:
SUPABASE_URL=http://localhost:54321
SUPABASE_SERVICE_ROLE_KEY=<service_role key from supabase start>
SUPABASE_JWT_SECRET=<JWT secret from supabase start>
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
GROQ_API_KEY=gsk_<your real key>
APP_ENV=local
```

### 5. Start all services

Open 3 terminal tabs:

**Tab 1 — Frontend**
```bash
npm run dev
# → http://localhost:5173
```

**Tab 2 — API**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000
# → Docs: http://localhost:8000/docs
```

**Tab 3 — Worker**
```bash
cd backend
source .venv/bin/activate
python -m worker.main
```

## Daily workflow

```bash
# Reset DB to clean state
supabase db reset

# Apply new migration
psql $DATABASE_URL -f supabase/migrations/NNN_new_migration.sql

# Run unit tests (fast, no DB)
cd backend && pytest tests/unit/ -v

# Run integration tests (needs DB running)
cd backend && pytest tests/integration/ -v

# Type check frontend
npm run typecheck
```

## Troubleshooting

### Supabase won't start
```bash
supabase stop --no-backup
supabase start
```

### Port 5432 already in use
```bash
# Check what's using it
lsof -i :5432
# Or use a different local port in DATABASE_URL: ...@localhost:54322/...
```

### Worker not picking up jobs
1. Check worker logs for DB connection errors
2. Verify `DATABASE_URL` in `backend/.env` matches running Supabase
3. Check `queued_jobs` table: `SELECT * FROM queued_jobs ORDER BY created_at DESC LIMIT 5;`

### LLM calls failing
1. Verify `GROQ_API_KEY` is set and not a placeholder
2. Check Groq dashboard for rate limit status
3. Worker logs will show `RateLimitError` with retry count
