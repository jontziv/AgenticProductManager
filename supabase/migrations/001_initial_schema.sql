-- ============================================================================
-- Migration 001: Initial schema
-- PM Sidekick — Agentic Intake-to-Backlog Workbench
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- fuzzy search on titles


-- ── Users mirror (kept in sync with Supabase Auth) ──────────────────────────
-- auth.users is managed by Supabase; we store app-level profile data here.
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id          UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT        NOT NULL,
    full_name   TEXT,
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.user_profiles IS 'App-level user data mirroring Supabase Auth users.';


-- ── Intake runs ──────────────────────────────────────────────────────────────
CREATE TYPE run_status AS ENUM (
    'queued',
    'processing',
    'needs_review',
    'qa_failed',
    'qa_passed',
    'approved',
    'exported',
    'cancelled',
    'failed'
);

CREATE TABLE IF NOT EXISTS public.intake_runs (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title               TEXT        NOT NULL CHECK (char_length(title) BETWEEN 1 AND 255),
    status              run_status  NOT NULL DEFAULT 'queued',

    -- Raw intake fields
    raw_input           TEXT        NOT NULL,
    input_type          TEXT        NOT NULL DEFAULT 'text' CHECK (input_type IN ('text','audio','file')),
    target_users        TEXT,
    business_context    TEXT,
    constraints         TEXT,

    -- Processing metadata
    idea_type           TEXT,       -- classified by LLM: feature|product|process|research
    langgraph_thread_id TEXT,       -- MemorySaver checkpoint key

    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    cancelled_at        TIMESTAMPTZ
);

COMMENT ON TABLE public.intake_runs IS 'One row per product idea submitted by a user.';
COMMENT ON COLUMN public.intake_runs.langgraph_thread_id IS 'Thread ID used for LangGraph MemorySaver checkpoints.';


-- ── Artifacts ─────────────────────────────────────────────────────────────────
CREATE TYPE artifact_status AS ENUM (
    'generating',
    'ready',
    'stale',
    'failed'
);

CREATE TABLE IF NOT EXISTS public.artifacts (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID            NOT NULL REFERENCES public.intake_runs(id) ON DELETE CASCADE,
    user_id         UUID            NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    artifact_type   TEXT            NOT NULL,
    status          artifact_status NOT NULL DEFAULT 'generating',
    content         JSONB           NOT NULL DEFAULT '{}',
    version         INTEGER         NOT NULL DEFAULT 1,
    schema_version  TEXT            NOT NULL DEFAULT '1.0',
    stale_reason    TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT artifacts_type_check CHECK (artifact_type IN (
        'problem_framing', 'personas', 'mvp_scope', 'success_metrics',
        'user_stories', 'backlog_items', 'test_cases', 'risks', 'architecture'
    ))
);

COMMENT ON TABLE public.artifacts IS 'Versioned PM artifacts generated per run. Use DISTINCT ON for latest.';
COMMENT ON COLUMN public.artifacts.version IS 'Increments on every regeneration; queries should use ORDER BY version DESC.';


-- ── Approvals ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.approvals (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id      UUID        NOT NULL REFERENCES public.intake_runs(id) ON DELETE CASCADE,
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    approved    BOOLEAN     NOT NULL,
    comment     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT approvals_one_per_run UNIQUE (run_id)
);

COMMENT ON TABLE public.approvals IS 'Human approval decision per run. One row per run.';


-- ── QA reports ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.qa_reports (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id              UUID        NOT NULL REFERENCES public.intake_runs(id) ON DELETE CASCADE UNIQUE,
    user_id             UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    overall_score       INTEGER     NOT NULL DEFAULT 0,
    max_score           INTEGER     NOT NULL DEFAULT 100,
    pass_rate           NUMERIC(5,2) NOT NULL DEFAULT 0,
    critical_issues     INTEGER     NOT NULL DEFAULT 0,
    export_ready        BOOLEAN     NOT NULL DEFAULT FALSE,
    checks              JSONB       NOT NULL DEFAULT '[]',
    remediation_tasks   JSONB       NOT NULL DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.qa_reports IS 'One QA report per run; upserted after every evaluation pass.';


-- ── Job queue ─────────────────────────────────────────────────────────────────
CREATE TYPE job_status AS ENUM (
    'queued',
    'running',
    'completed',
    'failed',
    'cancelled'
);

CREATE TABLE IF NOT EXISTS public.queued_jobs (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID        NOT NULL REFERENCES public.intake_runs(id) ON DELETE CASCADE,
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_type        TEXT        NOT NULL,  -- 'orchestrate_run' | 'regenerate_artifact' | 'generate_export'
    status          job_status  NOT NULL DEFAULT 'queued',
    payload         JSONB       NOT NULL DEFAULT '{}',
    result          JSONB,
    error_message   TEXT,
    retry_count     INTEGER     NOT NULL DEFAULT 0,
    max_retries     INTEGER     NOT NULL DEFAULT 3,
    priority        INTEGER     NOT NULL DEFAULT 5,  -- lower = higher priority
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    worker_id       TEXT        -- identifies which worker instance claimed the job
);

COMMENT ON TABLE public.queued_jobs IS 'DB-backed async job queue. Worker uses SELECT FOR UPDATE SKIP LOCKED.';


-- ── Exports ───────────────────────────────────────────────────────────────────
CREATE TYPE export_format AS ENUM (
    'markdown', 'json', 'html', 'jira_csv', 'linear_csv'
);

CREATE TABLE IF NOT EXISTS public.export_records (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID            NOT NULL REFERENCES public.intake_runs(id) ON DELETE CASCADE,
    user_id         UUID            NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    format          export_format   NOT NULL,
    status          job_status      NOT NULL DEFAULT 'queued',
    storage_path    TEXT,           -- Supabase Storage object key
    download_url    TEXT,           -- pre-signed URL (ephemeral)
    file_size_bytes INTEGER,
    error_message   TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.export_records IS 'One row per export format request. Links to Supabase Storage.';


-- ── Stale artifact tracking ───────────────────────────────────────────────────
-- When an upstream artifact changes, downstream artifacts are marked stale here
-- before regeneration is queued.
CREATE TABLE IF NOT EXISTS public.stale_markers (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id              UUID        NOT NULL REFERENCES public.intake_runs(id) ON DELETE CASCADE,
    artifact_type       TEXT        NOT NULL,
    upstream_artifact   TEXT        NOT NULL,
    marked_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT stale_markers_unique UNIQUE (run_id, artifact_type, upstream_artifact)
);


-- ── Automatic updated_at triggers ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'user_profiles', 'intake_runs', 'artifacts',
        'qa_reports', 'queued_jobs', 'export_records'
    ]
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at
             BEFORE UPDATE ON public.%s
             FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()',
            tbl, tbl
        );
    END LOOP;
END;
$$;
