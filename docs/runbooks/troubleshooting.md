# Troubleshooting Runbook

## Failed jobs

### Symptom
Run stays in `processing` or transitions to `failed`. Export button stays disabled.

### Diagnosis
```sql
-- Find failed jobs
SELECT id, job_type, status, retry_count, error_message, created_at
FROM queued_jobs
WHERE run_id = '<run_id>'
ORDER BY created_at DESC;

-- Check current run status
SELECT id, status, updated_at FROM intake_runs WHERE id = '<run_id>';
```

### Common causes and fixes

**"GROQ_API_KEY must be set to a real key"**
- Worker process has wrong env var
- Fix: update `GROQ_API_KEY` in Render environment, redeploy worker

**"RateLimitError" repeated 3 times**
- Groq rate limit hit
- Fix: reduce `WORKER_CONCURRENCY` (e.g., set to 1). Wait for rate limit window to reset.
- Long-term: upgrade Groq plan or implement per-user rate limiting

**"asyncpg: connection refused"**
- DB connection failure
- Fix: check `DATABASE_URL` env var. Check Render Postgres service status.

**"ValidationError: ...field required"**
- LLM returned malformed output that failed Pydantic validation
- `instructor` will retry up to 3 times; if all fail, job fails
- Fix: check `error_message` in `queued_jobs` for the specific field.
  Prompt improvement may be needed.

### Manual retry
```sql
-- Reset a failed job to allow retry
UPDATE queued_jobs
SET status = 'queued', retry_count = 0, error_message = NULL
WHERE id = '<job_id>';
```

---

## Bad artifact generation

### Symptom
QA report shows hard fails. Artifacts contain obviously wrong content.

### Diagnosis
```sql
-- View latest artifact content
SELECT artifact_type, version, content, created_at
FROM artifacts
WHERE run_id = '<run_id>'
ORDER BY artifact_type, version DESC;
```

### Fix: trigger selective regeneration
Use the regenerate endpoint (UI: "Regenerate" button on artifact card):
```bash
curl -X POST https://api.pm-sidekick.com/api/v1/runs/<run_id>/artifacts/<type>/regenerate \
  -H "Authorization: Bearer <token>"
```

Or reset the entire run:
```sql
UPDATE intake_runs SET status = 'queued' WHERE id = '<run_id>';
INSERT INTO queued_jobs (run_id, user_id, job_type, payload)
SELECT id, user_id, 'orchestrate_run', jsonb_build_object('run_id', id::text)
FROM intake_runs WHERE id = '<run_id>';
```

---

## Export not generating

### Symptom
Export button shows spinner that never resolves, or export record stays in `queued` status.

### Diagnosis
```sql
SELECT * FROM export_records WHERE run_id = '<run_id>' ORDER BY created_at DESC;
SELECT * FROM queued_jobs WHERE run_id = '<run_id>' AND job_type = 'generate_export' ORDER BY created_at DESC;
```

### Common causes
1. **Run not approved** — `intake_runs.status` must be `approved`. Check approval record:
   ```sql
   SELECT * FROM approvals WHERE run_id = '<run_id>';
   ```
2. **Storage upload failed** — Check `error_message` in `export_records`.
   Common: `EXPORT_STORAGE_BUCKET` env var not set, or Supabase Storage bucket doesn't exist.
3. **Worker down** — Check Render worker service logs.

---

## Auth failures (401/403)

### Symptom
API returns 401 or 403 unexpectedly.

### Diagnosis
1. Check token expiry: JWT `exp` claim should be in the future
2. Check `SUPABASE_JWT_SECRET` matches between Supabase project and Render env var
3. Check that `aud` claim is `authenticated` (Supabase default)

### Fix
```bash
# Verify JWT secret matches
# In Supabase Dashboard: Settings → API → JWT Secret
# In Render: Environment → SUPABASE_JWT_SECRET

# Decode a token to check claims (dev only — never log tokens in production)
python -c "import jwt; print(jwt.decode('<token>', options={'verify_signature': False}))"
```

---

## DB connection pool exhaustion

### Symptom
`asyncpg: too many connections` errors in API or worker logs.

### Fix
1. Reduce `WORKER_CONCURRENCY` (default 3)
2. Add `pgbouncer` connection pooler between Render and Supabase Postgres
3. Check for connection leaks: long-running transactions that aren't closed

```sql
-- Check active connections
SELECT count(*), state FROM pg_stat_activity GROUP BY state;

-- Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle' AND query_start < NOW() - interval '5 minutes';
```
