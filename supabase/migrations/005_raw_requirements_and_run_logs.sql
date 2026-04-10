-- ============================================================================
-- Migration 005: Add raw_requirements column + run_logs JSONB for agent traces
-- ============================================================================

-- Store the user's raw requirements separately from meeting_notes so prompts
-- can reference them explicitly.
ALTER TABLE public.intake_runs
    ADD COLUMN IF NOT EXISTS raw_requirements TEXT;

-- Per-run agent activity log. Each entry is a JSON object:
--   { "node": str, "summary": str, "ts": ISO8601 }
-- Appended atomically after each LangGraph node completes.
ALTER TABLE public.intake_runs
    ADD COLUMN IF NOT EXISTS run_logs JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.intake_runs.raw_requirements IS
    'Stakeholder-written or informal requirements provided at intake.';

COMMENT ON COLUMN public.intake_runs.run_logs IS
    'Append-only log of agent node completions with summaries, for UI display.';
