# Operator Checklist — First Deploy to Production

Work through these sections top-to-bottom. Each section has a verification step.

---

## Phase 1: Supabase project setup

- [ ] Create new Supabase project at https://supabase.com
- [ ] Note: `Project URL`, `anon key`, `service_role key`, `JWT secret` (Settings → API)
- [ ] Apply migrations:
  ```bash
  # Option A: Supabase CLI
  supabase link --project-ref <project-ref>
  supabase db push

  # Option B: Dashboard SQL editor
  # Paste 001_initial_schema.sql → Run
  # Paste 002_rls_policies.sql → Run
  # Paste 003_indexes.sql → Run
  ```
- [ ] Create storage bucket:
  ```sql
  -- If 002_rls_policies.sql didn't create it automatically:
  INSERT INTO storage.buckets (id, name, public) VALUES ('exports', 'exports', false);
  ```
- [ ] Verify: visit Supabase Table Editor — all 8 tables should exist
- [ ] Verify: visit Storage — `exports` bucket should exist and be private

---

## Phase 2: Groq API key

- [ ] Log in to https://console.groq.com
- [ ] Create API key for production (name: `pm-sidekick-prod`)
- [ ] Copy key — you won't see it again

---

## Phase 3: Render services

### Create Postgres database
- [ ] Render Dashboard → New → PostgreSQL
- [ ] Name: `pm-sidekick-db`
- [ ] Copy `Internal Database URL`

### Create API web service
- [ ] Render Dashboard → New → Web Service → Connect GitHub repo
- [ ] Name: `pm-sidekick-api`
- [ ] Root directory: `backend`
- [ ] Docker file path: `backend/Dockerfile`
- [ ] Health check path: `/healthz`
- [ ] Set environment variables:
  ```
  SUPABASE_URL=<from Supabase>
  SUPABASE_SERVICE_ROLE_KEY=<from Supabase>
  SUPABASE_JWT_SECRET=<from Supabase>
  DATABASE_URL=<Internal DB URL from Render Postgres>
  GROQ_API_KEY=<from Groq>
  APP_ENV=production
  GROQ_MODEL_FAST=llama-3.1-8b-instant
  GROQ_MODEL_STRUCTURED=llama-3.3-70b-versatile
  GROQ_MODEL_SYNTHESIS=llama-3.3-70b-versatile
  GROQ_MODEL_AUDIO=whisper-large-v3-turbo
  WORKER_CONCURRENCY=3
  EXPORT_STORAGE_BUCKET=exports
  LOG_LEVEL=INFO
  ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app
  ```
- [ ] Deploy
- [ ] Verify: `curl https://pm-sidekick-api.onrender.com/healthz` → `{"status": "ok"}`
- [ ] Verify: `curl https://pm-sidekick-api.onrender.com/readyz` → `{"status": "ok"}`

### Create worker service
- [ ] Render Dashboard → New → Background Worker → same repo
- [ ] Name: `pm-sidekick-worker`
- [ ] Docker file path: `backend/Dockerfile.worker`
- [ ] Same environment variables as API service (copy them)
- [ ] Deploy
- [ ] Verify: worker logs show `Worker started. Polling for jobs...`

---

## Phase 4: Vercel frontend

- [ ] `vercel link` (or connect via Vercel Dashboard → Import Project)
- [ ] Set environment variables in Vercel Dashboard:
  ```
  VITE_SUPABASE_URL=<from Supabase>
  VITE_SUPABASE_ANON_KEY=<from Supabase>
  VITE_API_BASE_URL=https://pm-sidekick-api.onrender.com
  ```
- [ ] Deploy: `vercel --prod`
- [ ] Note the production URL (e.g., `https://pm-sidekick.vercel.app`)
- [ ] Update `ALLOWED_ORIGINS` in Render API to match this URL

---

## Phase 5: CI/CD secrets

Add these secrets to GitHub repository (Settings → Secrets → Actions):

```
VERCEL_TOKEN=<vercel token from vercel.com/account/tokens>
VERCEL_ORG_ID=<from .vercel/project.json after linking>
VERCEL_PROJECT_ID=<from .vercel/project.json>
RENDER_API_KEY=<from render.com/u/settings → API keys>
RENDER_API_SERVICE_ID=<from Render API service URL>
RENDER_WORKER_SERVICE_ID=<from Render worker service URL>
API_BASE_URL=https://pm-sidekick-api.onrender.com
VITE_SUPABASE_URL=<same as above>
VITE_SUPABASE_ANON_KEY=<same as above>
VITE_API_BASE_URL=https://pm-sidekick-api.onrender.com
```

---

## Phase 6: End-to-end smoke test

- [ ] Visit production Vercel URL
- [ ] Sign up with a real email address
- [ ] Submit a test intake: "We need a Slack bot to remind engineers about PR reviews"
- [ ] Watch run progress through processing stages
- [ ] Verify QA report appears (should take 60-120s with mocked Groq)
- [ ] Approve the run
- [ ] Download markdown export
- [ ] Verify export file downloads and contains content

---

## Phase 7: Monitoring setup (optional but recommended)

- [ ] Set up Render alerts: service → Alerts → Add alert for crash loop + high memory
- [ ] If using LangSmith: set `LANGSMITH_ENABLED=true` and `LANGSMITH_API_KEY` in Render
- [ ] If using OTEL: set `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME`

---

## Secret rotation procedure

When rotating a secret (e.g., GROQ_API_KEY):
1. Generate new key
2. In Render: Add `GROQ_API_KEY_NEW=<new key>` 
3. Update code to read `GROQ_API_KEY_NEW` (or just swap — Groq keys are stateless)
4. Redeploy
5. Verify health check passes
6. Remove `GROQ_API_KEY_NEW` and rename to `GROQ_API_KEY`
7. Never commit old or new keys to git
