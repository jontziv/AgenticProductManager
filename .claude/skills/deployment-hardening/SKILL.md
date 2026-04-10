---
name: deployment-hardening
description: Deployment configuration, secrets management, health checks, and production readiness checklist for PM Sidekick on Vercel (frontend) and Render (API + worker + Postgres).
triggers:
  - "deploy"
  - "production"
  - "environment variables"
  - "health check"
  - "render"
  - "vercel"
  - "secrets"
---

# Deployment Hardening

## Infrastructure topology

```
Vercel (frontend)
  └── React SPA → /api/* proxied to Render API

Render (backend)
  ├── pm-sidekick-api   (web service, Docker, port 8000)
  ├── pm-sidekick-worker (background worker, Docker)
  └── Postgres           (managed, pm_sidekick DB)

Supabase
  ├── Auth
  ├── Storage (exports bucket)
  └── Postgres (same DB as Render or separate — see ADR-003)
```

## Health check endpoints

| Endpoint | Service | What it checks |
|----------|---------|----------------|
| `GET /healthz` | API | Process alive (returns 200 immediately) |
| `GET /readyz` | API | DB connection pool reachable |

Render health check path: `/healthz`
Render health check timeout: 5s

## Required environment variables

### API + Worker (Render)
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret
DATABASE_URL=postgresql://user:pass@host:5432/pm_sidekick
GROQ_API_KEY=gsk_...
APP_ENV=production
GROQ_MODEL_FAST=llama-3.1-8b-instant
GROQ_MODEL_STRUCTURED=llama-3.3-70b-versatile
GROQ_MODEL_SYNTHESIS=llama-3.3-70b-versatile
GROQ_MODEL_AUDIO=whisper-large-v3-turbo
WORKER_CONCURRENCY=3
WORKER_POLL_INTERVAL=2
EXPORT_STORAGE_BUCKET=exports
LOG_LEVEL=INFO
```

### Frontend (Vercel)
```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_API_BASE_URL=https://pm-sidekick-api.onrender.com
```

## Secret rotation procedure

1. Generate new key (Groq dashboard / Supabase dashboard)
2. Add new key to Render/Vercel with a temporary `_NEW` suffix
3. Deploy with code that reads both old + new (or just swap if service is stateless)
4. Verify health checks pass
5. Remove old key env var
6. Never commit keys to git — verify with: `git grep -r "gsk_" --` should return nothing

## Docker build (Render auto-builds from Dockerfile)

```bash
# Build API image locally
docker build -t pm-sidekick-api -f backend/Dockerfile backend/

# Build worker image
docker build -t pm-sidekick-worker -f backend/Dockerfile.worker backend/

# Test locally
docker run --env-file backend/.env -p 8000:8000 pm-sidekick-api
```

## Render deploy configuration (`render.yaml`)

```yaml
services:
  - type: web
    name: pm-sidekick-api
    runtime: docker
    dockerfilePath: backend/Dockerfile
    healthCheckPath: /healthz
    envVars: [...]

  - type: worker
    name: pm-sidekick-worker
    runtime: docker
    dockerfilePath: backend/Dockerfile.worker
```

## Vercel deploy configuration (`vercel.json`)

```json
{
  "rewrites": [{"source": "/(.*)", "destination": "/index.html"}],
  "headers": [
    {"source": "/assets/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]},
    {"source": "/(.*)", "headers": [{"key": "X-Frame-Options", "value": "DENY"}]}
  ]
}
```

## Production deploy gate (CI enforces)

Before any production deploy, CI must pass:
1. `ruff check` — Python linting
2. `mypy` — Python type check
3. `pytest tests/unit/` — unit tests
4. `tsc --noEmit` — TypeScript type check
5. `vite build` — frontend build succeeds
6. Smoke check: `curl /healthz` returns 200

## Rollback procedure

1. Render: go to service → Deploys → click previous deploy → "Rollback"
2. Vercel: go to project → Deployments → promote previous to production
3. DB migrations: write a `NNN_rollback_*.sql` and apply — never drop data in a rollback

## Monitoring

- Render logs: service → Logs tab
- Structured JSON logs include `run_id`, `job_id`, `user_id` (hashed), `duration_ms`
- Set up Render alerts for: crash loops, high memory, 5xx rate > 1%
- Optional: OpenTelemetry export via `OTEL_EXPORTER_OTLP_ENDPOINT`
