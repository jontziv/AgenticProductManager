"""
QA evaluation and remediation router nodes.
"""

import json
from typing import Any

import structlog

from app.graph.state import WorkflowState
from app.evaluators.harness import run_qa_evaluation

logger = structlog.get_logger(__name__)

MAX_QA_ATTEMPTS = 3


async def qa_evaluation_node(state: WorkflowState) -> dict[str, Any]:
    """Run full QA evaluation harness against all artifacts."""
    log = logger.bind(run_id=state.get("run_id"), node="qa_evaluation")
    log.info("node_start")

    attempt = state.get("qa_attempt", 0) + 1

    artifacts = {
        "problem_framing": state.get("problem_framing", {}),
        "personas": state.get("personas", {}),
        "mvp_scope": state.get("mvp_scope", {}),
        "success_metrics": state.get("success_metrics", {}),
        "user_stories": state.get("user_stories", {}),
        "backlog_items": state.get("backlog_items", {}),
        "test_cases": state.get("test_cases", {}),
        "risks": state.get("risks", {}),
        "architecture": state.get("architecture", {}),
    }

    source_inputs = state.get("source_inputs", {})
    qa_report = await run_qa_evaluation(
        artifacts=artifacts,
        source_inputs=source_inputs,
        run_id=state.get("run_id"),
    )

    log.info(
        "qa_complete",
        attempt=attempt,
        score=qa_report.get("overall_score"),
        critical_issues=qa_report.get("critical_issues"),
        export_ready=qa_report.get("export_ready"),
    )

    return {
        "qa_report": qa_report,
        "qa_remediation_tasks": qa_report.get("remediation_tasks", []),
        "qa_attempt": attempt,
        "current_node": "qa_evaluation",
    }


async def remediation_router_node(state: WorkflowState) -> dict[str, Any]:
    """
    Handle QA hard fails by triggering targeted artifact regeneration.
    After max attempts, give up and let the run proceed to human review.
    """
    log = logger.bind(run_id=state.get("run_id"), node="remediation_router")
    log.info("node_start")

    tasks = state.get("qa_remediation_tasks", [])
    attempt = state.get("qa_attempt", 0)

    if attempt >= MAX_QA_ATTEMPTS or not tasks:
        log.warning("remediation_exhausted", attempt=attempt)
        return {"current_node": "remediation_router"}

    # Process only the highest priority tasks
    high_priority = [t for t in tasks if t.get("priority") == "high"][:3]

    log.info("remediating", task_count=len(high_priority))

    # For now, mark affected artifacts as stale; downstream regeneration
    # would re-run specific artifact nodes. In a full impl, this would
    # selectively re-enter the graph at the right node.
    # For MVP: log remediation intent and let QA retry catch improvements.
    for task in high_priority:
        log.info("remediation_task", artifact=task.get("affected_artifact"), desc=task.get("description"))

    return {"current_node": "remediation_router"}


async def human_review_gate_node(state: WorkflowState) -> dict[str, Any]:
    """
    Interrupt point for human approval. The graph pauses here.
    Resumption happens when the API receives an approval submission.
    """
    # This node is registered as interrupt_before in graph.py
    # When interrupted, the state is persisted by the checkpointer.
    # Resume by calling graph.invoke() with the updated state after approval.
    return {
        "approval_state": state.get("approval_state", "pending"),
        "current_node": "human_review_gate",
    }


async def approval_versioning_node(state: WorkflowState) -> dict[str, Any]:
    """Finalize artifact versions after approval."""
    log = logger.bind(run_id=state.get("run_id"), node="approval_versioning")
    log.info("approval_finalized", decision=state.get("approval_state"))
    return {"current_node": "approval_versioning"}


async def export_pack_node(state: WorkflowState) -> dict[str, Any]:
    """Generate export pack in all requested formats."""
    from app.services.export_service import generate_export_pack

    log = logger.bind(run_id=state.get("run_id"), node="export_pack")
    log.info("node_start")

    pack = await generate_export_pack(
        run_id=state.get("run_id", ""),
        artifacts={
            "problem_framing": state.get("problem_framing", {}),
            "personas": state.get("personas", {}),
            "mvp_scope": state.get("mvp_scope", {}),
            "success_metrics": state.get("success_metrics", {}),
            "user_stories": state.get("user_stories", {}),
            "backlog_items": state.get("backlog_items", {}),
            "test_cases": state.get("test_cases", {}),
            "risks": state.get("risks", {}),
            "architecture": state.get("architecture", {}),
        },
    )
    return {"export_pack": pack, "current_node": "export_pack"}
