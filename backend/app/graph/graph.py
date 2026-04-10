"""
LangGraph workflow assembly.
Compiles the full PM artifact generation state machine.
"""

from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import WorkflowState
from app.graph.nodes.ingest import (
    ingest_input_node,
    transcribe_audio_node,
    detect_missing_info_node,
    classify_idea_node,
    choose_pattern_node,
)
from app.graph.nodes.generate import (
    create_problem_framing_node,
    generate_personas_node,
    generate_mvp_scope_node,
    generate_success_metrics_node,
    generate_user_stories_node,
    generate_backlog_node,
    generate_test_cases_node,
    generate_risks_node,
    generate_architecture_node,
    consistency_check_node,
)
from app.graph.nodes.qa import (
    qa_evaluation_node,
    remediation_router_node,
    human_review_gate_node,
    approval_versioning_node,
    export_pack_node,
)


# ── Routing functions ─────────────────────────────────────────────────────────

def route_after_ingest(state: WorkflowState) -> str:
    if state.get("extracted_brief", {}).get("has_audio"):
        return "transcribe_audio"
    return "detect_missing_info"


def route_after_missing_info(state: WorkflowState) -> str:
    if not state.get("can_proceed", True):
        return END  # type: ignore[return-value]
    return "classify_idea"


def route_after_qa(state: WorkflowState) -> str:
    qa = state.get("qa_report", {})
    attempt = state.get("qa_attempt", 0)
    has_hard_fails = qa.get("critical_issues", 0) > 0
    max_attempts_reached = attempt >= 3

    if has_hard_fails and not max_attempts_reached:
        return "remediation_router"
    return "human_review_gate"


def route_after_human_review(state: WorkflowState) -> str:
    decision = state.get("approval_state", "pending")
    if decision == "approved":
        return "approval_versioning"
    if decision == "rejected":
        return END  # type: ignore[return-value]
    return "human_review_gate"  # still pending (interrupt will re-fire)


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_graph() -> Any:
    builder = StateGraph(WorkflowState)

    # ── Register nodes ───────────────────────────────────────────────────────
    builder.add_node("ingest_input", ingest_input_node)
    builder.add_node("transcribe_audio", transcribe_audio_node)
    builder.add_node("detect_missing_info", detect_missing_info_node)
    builder.add_node("classify_idea", classify_idea_node)
    builder.add_node("choose_pattern", choose_pattern_node)
    builder.add_node("create_problem_framing", create_problem_framing_node)
    builder.add_node("generate_personas", generate_personas_node)
    builder.add_node("generate_mvp_scope", generate_mvp_scope_node)
    builder.add_node("generate_success_metrics", generate_success_metrics_node)
    builder.add_node("generate_user_stories", generate_user_stories_node)
    builder.add_node("generate_backlog", generate_backlog_node)
    builder.add_node("generate_test_cases", generate_test_cases_node)
    builder.add_node("generate_risks", generate_risks_node)
    builder.add_node("generate_architecture", generate_architecture_node)
    builder.add_node("consistency_check", consistency_check_node)
    builder.add_node("qa_evaluation", qa_evaluation_node)
    builder.add_node("remediation_router", remediation_router_node)
    builder.add_node("human_review_gate", human_review_gate_node)
    builder.add_node("approval_versioning", approval_versioning_node)
    builder.add_node("export_pack", export_pack_node)

    # ── Entry point ──────────────────────────────────────────────────────────
    builder.set_entry_point("ingest_input")

    # ── Edges ────────────────────────────────────────────────────────────────
    builder.add_conditional_edges(
        "ingest_input",
        route_after_ingest,
        {"transcribe_audio": "transcribe_audio", "detect_missing_info": "detect_missing_info"},
    )
    builder.add_edge("transcribe_audio", "detect_missing_info")
    builder.add_conditional_edges(
        "detect_missing_info",
        route_after_missing_info,
        {"classify_idea": "classify_idea", END: END},
    )
    builder.add_edge("classify_idea", "choose_pattern")
    builder.add_edge("choose_pattern", "create_problem_framing")
    builder.add_edge("create_problem_framing", "generate_personas")
    builder.add_edge("generate_personas", "generate_mvp_scope")
    builder.add_edge("generate_mvp_scope", "generate_success_metrics")
    builder.add_edge("generate_success_metrics", "generate_user_stories")
    builder.add_edge("generate_user_stories", "generate_backlog")
    builder.add_edge("generate_backlog", "generate_test_cases")
    builder.add_edge("generate_test_cases", "generate_risks")
    builder.add_edge("generate_risks", "generate_architecture")
    builder.add_edge("generate_architecture", "consistency_check")
    builder.add_edge("consistency_check", "qa_evaluation")
    builder.add_conditional_edges(
        "qa_evaluation",
        route_after_qa,
        {
            "remediation_router": "remediation_router",
            "human_review_gate": "human_review_gate",
        },
    )
    builder.add_edge("remediation_router", "qa_evaluation")
    builder.add_conditional_edges(
        "human_review_gate",
        route_after_human_review,
        {
            "approval_versioning": "approval_versioning",
            "human_review_gate": "human_review_gate",
            END: END,
        },
    )
    builder.add_edge("approval_versioning", "export_pack")
    builder.add_edge("export_pack", END)

    # ── Compile with checkpointing and human-in-the-loop ─────────────────────
    # MemorySaver for local/test; swap for PostgresSaver in production
    checkpointer = MemorySaver()
    compiled = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review_gate"],
    )
    return compiled


# Singleton graph instance
_graph = None


def get_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
