-- ============================================================================
-- Migration 004: Add missing_info column to intake_runs
-- Stores the list of missing fields detected by the LLM when can_proceed=false.
-- ============================================================================

ALTER TABLE public.intake_runs
    ADD COLUMN IF NOT EXISTS missing_info JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.intake_runs.missing_info IS
    'List of missing info flags produced by detect_missing_info node. '
    'Non-empty means the run stopped early awaiting clarification.';
