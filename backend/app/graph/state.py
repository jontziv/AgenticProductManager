"""
LangGraph workflow state. TypedDict — serializable, checkpointable.
All fields optional except run_id/user_id (they are set at entry).
"""

from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    # ── Identity ────────────────────────────────────────────────────────────
    run_id: str
    user_id: str

    # ── Source inputs (raw, never mutated after ingest) ──────────────────────
    source_inputs: dict[str, Any]          # raw intake form values
    audio_transcript: str                  # filled if audio present

    # ── Extracted brief ───────────────────────────────────────────────────────
    extracted_brief: dict[str, Any]        # normalized, validated brief

    # ── Classification ────────────────────────────────────────────────────────
    idea_classification: str               # e.g. "new_product"
    selected_pattern: str                  # e.g. "saas_webapp"
    pattern_rationale: str

    # ── Missing info ──────────────────────────────────────────────────────────
    missing_info_flags: list[str]          # empty = can proceed
    can_proceed: bool

    # ── Artifacts (each is a typed dict matching the Pydantic schema) ─────────
    problem_framing: dict[str, Any]
    personas: dict[str, Any]
    mvp_scope: dict[str, Any]
    success_metrics: dict[str, Any]
    user_stories: dict[str, Any]
    backlog_items: dict[str, Any]
    test_cases: dict[str, Any]
    risks: dict[str, Any]
    architecture: dict[str, Any]

    # ── QA ────────────────────────────────────────────────────────────────────
    consistency_issues: list[str]
    qa_report: dict[str, Any]
    qa_remediation_tasks: list[dict[str, Any]]
    qa_attempt: int                        # track retry count

    # ── Approvals ─────────────────────────────────────────────────────────────
    approval_state: str                    # "pending" | "approved" | "rejected"

    # ── Export ────────────────────────────────────────────────────────────────
    export_pack: dict[str, Any]            # format -> url

    # ── Error / audit ─────────────────────────────────────────────────────────
    error: str | None
    audit_events: list[dict[str, Any]]
    current_node: str
