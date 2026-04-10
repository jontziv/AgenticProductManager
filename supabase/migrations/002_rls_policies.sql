-- ============================================================================
-- Migration 002: Row-Level Security policies
-- Every table is user-scoped: users can only see/modify their own rows.
-- Service role (used by backend) bypasses RLS automatically.
-- ============================================================================

-- ── Enable RLS on all tables ─────────────────────────────────────────────────
ALTER TABLE public.user_profiles    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intake_runs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.artifacts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approvals        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.qa_reports       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.queued_jobs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.export_records   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stale_markers    ENABLE ROW LEVEL SECURITY;


-- ── user_profiles ─────────────────────────────────────────────────────────────
CREATE POLICY "user_profiles_own_row" ON public.user_profiles
    FOR ALL USING (auth.uid() = id);


-- ── intake_runs ───────────────────────────────────────────────────────────────
CREATE POLICY "intake_runs_select_own" ON public.intake_runs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "intake_runs_insert_own" ON public.intake_runs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "intake_runs_update_own" ON public.intake_runs
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "intake_runs_delete_own" ON public.intake_runs
    FOR DELETE USING (auth.uid() = user_id);


-- ── artifacts ─────────────────────────────────────────────────────────────────
CREATE POLICY "artifacts_select_own" ON public.artifacts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "artifacts_insert_own" ON public.artifacts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "artifacts_update_own" ON public.artifacts
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "artifacts_delete_own" ON public.artifacts
    FOR DELETE USING (auth.uid() = user_id);


-- ── approvals ─────────────────────────────────────────────────────────────────
CREATE POLICY "approvals_select_own" ON public.approvals
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "approvals_insert_own" ON public.approvals
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "approvals_update_own" ON public.approvals
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ── qa_reports ────────────────────────────────────────────────────────────────
CREATE POLICY "qa_reports_select_own" ON public.qa_reports
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "qa_reports_insert_own" ON public.qa_reports
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "qa_reports_update_own" ON public.qa_reports
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ── queued_jobs ───────────────────────────────────────────────────────────────
-- Users can read their own jobs but cannot insert/update directly.
-- Only the service role (backend API and worker) writes jobs.
CREATE POLICY "queued_jobs_select_own" ON public.queued_jobs
    FOR SELECT USING (auth.uid() = user_id);


-- ── export_records ────────────────────────────────────────────────────────────
CREATE POLICY "export_records_select_own" ON public.export_records
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "export_records_insert_own" ON public.export_records
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "export_records_update_own" ON public.export_records
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ── stale_markers ─────────────────────────────────────────────────────────────
-- Internal housekeeping; only service role writes.
CREATE POLICY "stale_markers_select_own" ON public.stale_markers
    FOR SELECT USING (
        auth.uid() IN (
            SELECT user_id FROM public.intake_runs WHERE id = run_id
        )
    );


-- ── Storage bucket RLS ───────────────────────────────────────────────────────
-- Bucket: "exports" — users can only read their own objects.
-- Objects are stored under {user_id}/{run_id}/{filename}.

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'exports',
    'exports',
    false,
    52428800,  -- 50 MB
    ARRAY['text/markdown', 'application/json', 'text/html', 'text/csv']
)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "exports_object_select_own" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'exports'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "exports_object_insert_service" ON storage.objects
    FOR INSERT TO service_role
    WITH CHECK (bucket_id = 'exports');

CREATE POLICY "exports_object_delete_own" ON storage.objects
    FOR DELETE TO authenticated
    USING (
        bucket_id = 'exports'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );
