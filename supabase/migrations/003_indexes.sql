-- ============================================================================
-- Migration 003: Performance indexes
-- ============================================================================

-- ── intake_runs ───────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_intake_runs_user_id
    ON public.intake_runs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_intake_runs_status
    ON public.intake_runs (status)
    WHERE status NOT IN ('exported', 'cancelled', 'failed');

CREATE INDEX IF NOT EXISTS idx_intake_runs_title_trgm
    ON public.intake_runs USING gin (title gin_trgm_ops);


-- ── artifacts ─────────────────────────────────────────────────────────────────
-- Primary lookup: latest artifact per type for a run
CREATE INDEX IF NOT EXISTS idx_artifacts_run_type_version
    ON public.artifacts (run_id, artifact_type, version DESC);

CREATE INDEX IF NOT EXISTS idx_artifacts_user_id
    ON public.artifacts (user_id);

CREATE INDEX IF NOT EXISTS idx_artifacts_status
    ON public.artifacts (status)
    WHERE status = 'stale';


-- ── queued_jobs ───────────────────────────────────────────────────────────────
-- Worker claim query: SELECT FOR UPDATE SKIP LOCKED WHERE status='queued' ORDER BY priority, created_at
CREATE INDEX IF NOT EXISTS idx_queued_jobs_claim
    ON public.queued_jobs (priority ASC, created_at ASC)
    WHERE status = 'queued';

CREATE INDEX IF NOT EXISTS idx_queued_jobs_run_id
    ON public.queued_jobs (run_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_queued_jobs_user_status
    ON public.queued_jobs (user_id, status);


-- ── qa_reports ────────────────────────────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS idx_qa_reports_run_id
    ON public.qa_reports (run_id);


-- ── export_records ────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_export_records_run_id
    ON public.export_records (run_id, format);

CREATE INDEX IF NOT EXISTS idx_export_records_user_status
    ON public.export_records (user_id, status);


-- ── approvals ─────────────────────────────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS idx_approvals_run_id
    ON public.approvals (run_id);


-- ── stale_markers ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_stale_markers_run_id
    ON public.stale_markers (run_id);
