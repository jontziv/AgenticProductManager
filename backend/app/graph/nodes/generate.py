"""
Artifact generation nodes.
Each node generates one artifact type using structured LLM output.
"""

import json
from typing import Any

import structlog

from app.graph.state import WorkflowState
from app.llm.client import generate_structured
from app.llm.routing import ModelRole
from app.models.artifacts import (
    ProblemFraming, Personas, MvpScope, SuccessMetrics,
    UserStories, BacklogItems, TestCases, Risks, Architecture,
)
from app.prompts.registry import get_prompt

logger = structlog.get_logger(__name__)


def _brief(state: WorkflowState) -> dict[str, Any]:
    return state.get("extracted_brief", {})


async def create_problem_framing_node(state: WorkflowState) -> dict[str, Any]:
    log = logger.bind(run_id=state.get("run_id"), node="create_problem_framing")
    log.info("node_start")
    b = _brief(state)
    messages = get_prompt("problem_framing").build_messages(
        business_idea=b.get("business_idea", ""),
        target_users=b.get("target_users", ""),
        meeting_notes=b.get("meeting_notes", "N/A"),
        raw_requirements=b.get("raw_requirements", "N/A"),
        constraints=b.get("constraints", "N/A"),
        timeline=b.get("timeline", "N/A"),
        assumptions=b.get("assumptions", "N/A"),
    )
    result = await generate_structured(
        messages=messages, response_model=ProblemFraming,
        role=ModelRole.STRUCTURED, max_tokens=1500,
        run_id=state.get("run_id"), node_name="create_problem_framing",
    )
    return {"problem_framing": result.model_dump(), "current_node": "create_problem_framing"}


async def generate_personas_node(state: WorkflowState) -> dict[str, Any]:
    log = logger.bind(run_id=state.get("run_id"), node="generate_personas")
    log.info("node_start")
    pf = state.get("problem_framing", {})
    messages = get_prompt("personas").build_messages(
        target_users=_brief(state).get("target_users", ""),
        problem_statement=pf.get("problem_statement", ""),
        business_idea=_brief(state).get("business_idea", ""),
    )
    result = await generate_structured(
        messages=messages, response_model=Personas,
        role=ModelRole.STRUCTURED, max_tokens=1800,
        run_id=state.get("run_id"), node_name="generate_personas",
    )
    return {"personas": result.model_dump(), "current_node": "generate_personas"}


async def generate_mvp_scope_node(state: WorkflowState) -> dict[str, Any]:
    log = logger.bind(run_id=state.get("run_id"), node="generate_mvp_scope")
    log.info("node_start")
    pf = state.get("problem_framing", {})
    b = _brief(state)
    messages = get_prompt("mvp_scope").build_messages(
        problem_statement=pf.get("problem_statement", ""),
        goals=json.dumps(pf.get("goals", [])),
        business_idea=b.get("business_idea", ""),
        constraints=b.get("constraints", "N/A"),
        timeline=b.get("timeline", "N/A"),
    )
    result = await generate_structured(
        messages=messages, response_model=MvpScope,
        role=ModelRole.STRUCTURED, max_tokens=2500,
        run_id=state.get("run_id"), node_name="generate_mvp_scope",
    )
    return {"mvp_scope": result.model_dump(), "current_node": "generate_mvp_scope"}


async def generate_success_metrics_node(state: WorkflowState) -> dict[str, Any]:
    log = logger.bind(run_id=state.get("run_id"), node="generate_success_metrics")
    log.info("node_start")
    pf = state.get("problem_framing", {})
    messages = get_prompt("success_metrics").build_messages(
        goals=json.dumps(pf.get("goals", [])),
        selected_pattern=state.get("selected_pattern", "saas_webapp"),
        target_users=_brief(state).get("target_users", ""),
    )
    result = await generate_structured(
        messages=messages, response_model=SuccessMetrics,
        role=ModelRole.STRUCTURED, max_tokens=1500,
        run_id=state.get("run_id"), node_name="generate_success_metrics",
    )
    return {"success_metrics": result.model_dump(), "current_node": "generate_success_metrics"}


async def generate_user_stories_node(state: WorkflowState) -> dict[str, Any]:
    log = logger.bind(run_id=state.get("run_id"), node="generate_user_stories")
    log.info("node_start")
    scope = state.get("mvp_scope", {})
    personas_data = state.get("personas", {})
    persona_names = [p.get("name", "") for p in personas_data.get("personas", [])]
    messages = get_prompt("user_stories").build_messages(
        core_features=json.dumps(scope.get("core_features", [])),
        persona_names=", ".join(persona_names),
        in_scope=json.dumps(scope.get("in_scope", [])),
    )
    result = await generate_structured(
        messages=messages, response_model=UserStories,
        role=ModelRole.STRUCTURED, max_tokens=4000,
        run_id=state.get("run_id"), node_name="generate_user_stories",
    )
    return {"user_stories": result.model_dump(), "current_node": "generate_user_stories"}


async def generate_backlog_node(state: WorkflowState) -> dict[str, Any]:
    log = logger.bind(run_id=state.get("run_id"), node="generate_backlog")
    log.info("node_start")
    stories = state.get("user_stories", {}).get("stories", [])
    messages = get_prompt("backlog_items").build_messages(
        stories_json=json.dumps(stories[:20]),  # cap to avoid token overflow
    )
    result = await generate_structured(
        messages=messages, response_model=BacklogItems,
        role=ModelRole.STRUCTURED, max_tokens=1500,
        run_id=state.get("run_id"), node_name="generate_backlog",
    )
    return {"backlog_items": result.model_dump(), "current_node": "generate_backlog"}


async def generate_test_cases_node(state: WorkflowState) -> dict[str, Any]:
    log = logger.bind(run_id=state.get("run_id"), node="generate_test_cases")
    log.info("node_start")
    stories = state.get("user_stories", {}).get("stories", [])
    # Cap at 10 stories to keep input tokens manageable.
    # Acceptance criteria are already embedded in each story object — passing
    # them again as a separate field doubles input size with no benefit.
    capped = stories[:10]
    messages = get_prompt("test_cases").build_messages(
        stories_json=json.dumps(capped),
        acceptance_criteria=json.dumps([]),  # kept for template compat; stories have criteria inline
    )
    result = await generate_structured(
        messages=messages, response_model=TestCases,
        role=ModelRole.STRUCTURED, max_tokens=4000,
        run_id=state.get("run_id"), node_name="generate_test_cases",
    )
    return {"test_cases": result.model_dump(), "current_node": "generate_test_cases"}


async def generate_risks_node(state: WorkflowState) -> dict[str, Any]:
    log = logger.bind(run_id=state.get("run_id"), node="generate_risks")
    log.info("node_start")
    scope = state.get("mvp_scope", {})
    b = _brief(state)
    messages = get_prompt("risks").build_messages(
        in_scope=json.dumps(scope.get("in_scope", [])),
        selected_pattern=state.get("selected_pattern", "saas_webapp"),
        constraints=b.get("constraints", "N/A"),
        assumptions=json.dumps(state.get("problem_framing", {}).get("assumptions", [])),
    )
    result = await generate_structured(
        messages=messages, response_model=Risks,
        role=ModelRole.STRUCTURED, max_tokens=2000,
        run_id=state.get("run_id"), node_name="generate_risks",
    )
    return {"risks": result.model_dump(), "current_node": "generate_risks"}


async def generate_architecture_node(state: WorkflowState) -> dict[str, Any]:
    log = logger.bind(run_id=state.get("run_id"), node="generate_architecture")
    log.info("node_start")
    scope = state.get("mvp_scope", {})
    messages = get_prompt("architecture").build_messages(
        selected_pattern=state.get("selected_pattern", "saas_webapp"),
        core_features=json.dumps(scope.get("core_features", [])),
        constraints=_brief(state).get("constraints", "N/A"),
    )
    result = await generate_structured(
        messages=messages, response_model=Architecture,
        role=ModelRole.SYNTHESIS, max_tokens=2500,
        run_id=state.get("run_id"), node_name="generate_architecture",
    )
    return {"architecture": result.model_dump(), "current_node": "generate_architecture"}


async def consistency_check_node(state: WorkflowState) -> dict[str, Any]:
    """Cross-artifact consistency check — uses compact summary to minimise tokens."""
    from pydantic import BaseModel as BM

    class ConsistencyResult(BM):
        issues: list[str]
        is_consistent: bool

    log = logger.bind(run_id=state.get("run_id"), node="consistency_check")
    log.info("node_start")

    # Build a compact summary instead of dumping full artifact JSON.
    # Full dumps were ~3k input tokens; this is ~300.
    pf = state.get("problem_framing", {})
    personas = state.get("personas", {}).get("personas", [])
    scope = state.get("mvp_scope", {})
    stories = state.get("user_stories", {}).get("stories", [])
    metrics_data = state.get("success_metrics", {}).get("metrics", [])

    summary = {
        "problem_statement": (pf.get("problem_statement", "") or "")[:200],
        "goals": [(g[:80] if isinstance(g, str) else str(g)[:80]) for g in (pf.get("goals") or [])],
        "persona_roles": [p.get("role", "") for p in personas],
        "feature_ids": [f.get("id") for f in (scope.get("core_features") or [])],
        "story_count": len(stories),
        "story_epics": list({s.get("epic", "") for s in stories}),
        "metric_names": [m.get("metric_name", "") for m in metrics_data],
    }

    messages = get_prompt("consistency_check").build_messages(summary=json.dumps(summary, indent=2))
    result = await generate_structured(
        messages=messages, response_model=ConsistencyResult,
        role=ModelRole.SYNTHESIS, max_tokens=512,
        run_id=state.get("run_id"), node_name="consistency_check",
    )
    log.info("consistency_result", is_consistent=result.is_consistent, issues=len(result.issues))
    return {"consistency_issues": result.issues, "current_node": "consistency_check"}
