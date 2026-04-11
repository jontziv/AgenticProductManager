"""
ingest_input: Validate and normalize the raw intake form submission.
detect_missing_info: Identify critical gaps; flag or set can_proceed.
transcribe_audio: Transcribe audio if present.
"""

import json
from typing import Any

import structlog

from app.graph.state import WorkflowState
from app.llm.client import generate_structured, transcribe_audio as _transcribe
from app.llm.routing import ModelRole
from app.prompts.registry import get_prompt
from pydantic import BaseModel  # used by ClassificationResult

logger = structlog.get_logger(__name__)


# ── Pydantic schemas for LLM node outputs ────────────────────────────────────

class ClassificationResult(BaseModel):
    idea_type: str
    confidence: str
    rationale: str


# ── Deterministic pattern lookup (no LLM call) ────────────────────────────────

_PATTERN_MAP: dict[str, str] = {
    "new_product": "saas_webapp",
    "feature_addition": "saas_webapp",
    "platform_improvement": "api_first",
    "internal_tool": "internal_tool",
    "api_product": "api_first",
    "marketplace": "marketplace",
}

_PATTERN_RATIONALE: dict[str, str] = {
    "saas_webapp": "Standard SaaS web application pattern for consumer/B2B products",
    "api_first": "API-first pattern for developer products and platform improvements",
    "internal_tool": "Internal tooling pattern with minimal external dependencies",
    "marketplace": "Two-sided marketplace pattern with buyer/seller flows",
    "mobile_first": "Mobile-native pattern for consumer mobile products",
    "data_platform": "Data platform pattern for analytics and reporting products",
}


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def ingest_input_node(state: WorkflowState) -> dict[str, Any]:
    """Validate source inputs and build normalized brief."""
    log = logger.bind(run_id=state.get("run_id"), node="ingest_input")
    log.info("node_start")

    inputs = state.get("source_inputs", {})

    # Build a clean combined text brief for downstream prompts
    brief_parts = []
    if inputs.get("business_idea"):
        brief_parts.append(f"IDEA:\n{inputs['business_idea']}")
    if inputs.get("meeting_notes"):
        brief_parts.append(f"MEETING NOTES:\n{inputs['meeting_notes']}")
    if inputs.get("raw_requirements"):
        brief_parts.append(f"RAW REQUIREMENTS:\n{inputs['raw_requirements']}")
    if inputs.get("constraints"):
        brief_parts.append(f"CONSTRAINTS:\n{inputs['constraints']}")
    if inputs.get("assumptions"):
        brief_parts.append(f"ASSUMPTIONS:\n{inputs['assumptions']}")

    extracted_brief = {
        "title": inputs.get("title", ""),
        "business_idea": inputs.get("business_idea", ""),
        "target_users": inputs.get("target_users", ""),
        "meeting_notes": inputs.get("meeting_notes", ""),
        "raw_requirements": inputs.get("raw_requirements", ""),
        "timeline": inputs.get("timeline", ""),
        "constraints": inputs.get("constraints", ""),
        "assumptions": inputs.get("assumptions", ""),
        "combined_text": "\n\n".join(brief_parts),
        "has_audio": bool(inputs.get("audio_file_url")),
    }

    return {
        "extracted_brief": extracted_brief,
        "current_node": "ingest_input",
        "audit_events": [{"event": "ingest_input_complete", "run_id": state.get("run_id")}],
    }


async def transcribe_audio_node(state: WorkflowState) -> dict[str, Any]:
    """Download and transcribe audio if present in source inputs."""
    log = logger.bind(run_id=state.get("run_id"), node="transcribe_audio")
    log.info("node_start")

    audio_url = state.get("source_inputs", {}).get("audio_file_url")
    if not audio_url:
        return {"current_node": "transcribe_audio"}

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(audio_url)
            resp.raise_for_status()
            audio_bytes = resp.content
            filename = audio_url.split("/")[-1]

        transcript = await _transcribe(audio_bytes, filename, run_id=state.get("run_id"))
        log.info("transcription_complete", chars=len(transcript))

        # Append transcript to extracted brief
        brief = dict(state.get("extracted_brief", {}))
        brief["audio_transcript"] = transcript
        brief["combined_text"] = brief.get("combined_text", "") + f"\n\nAUDIO TRANSCRIPT:\n{transcript}"

        return {
            "audio_transcript": transcript,
            "extracted_brief": brief,
            "current_node": "transcribe_audio",
        }
    except Exception as exc:
        log.error("transcription_error", error=str(exc))
        # Non-fatal: continue without transcript
        return {"current_node": "transcribe_audio"}


async def detect_missing_info_node(state: WorkflowState) -> dict[str, Any]:
    """Identify gaps deterministically — no LLM call.

    Form validation already ensures title, business_idea, target_users, and
    raw_requirements are present. This node checks optional supporting fields
    and surfaces any gaps as advisory assumptions only. Execution always proceeds.
    """
    log = logger.bind(run_id=state.get("run_id"), node="detect_missing_info")
    log.info("node_start")

    brief = state.get("extracted_brief", {})
    optional_fields = {
        "meeting_notes": "No meeting notes provided — generating from idea description only",
        "constraints": "No constraints specified — assuming standard budget/timeline",
        "timeline": "No timeline specified — treating as open-ended",
        "assumptions": "No explicit assumptions provided",
    }
    missing = [k for k, _ in optional_fields.items() if not brief.get(k) or not str(brief[k]).strip()]
    flags = [optional_fields[k] for k in missing]

    log.info("missing_info_result", missing_count=len(missing), can_proceed=True)

    return {
        "missing_info_flags": flags,
        "can_proceed": True,
        "current_node": "detect_missing_info",
    }


async def classify_idea_node(state: WorkflowState) -> dict[str, Any]:
    """Classify the idea type using the fast model."""
    log = logger.bind(run_id=state.get("run_id"), node="classify_idea")
    log.info("node_start")

    brief = state.get("extracted_brief", {})
    prompt = get_prompt("classify_idea")
    messages = prompt.build_messages(
        business_idea=brief.get("business_idea", ""),
        target_users=brief.get("target_users", ""),
    )

    result = await generate_structured(
        messages=messages,
        response_model=ClassificationResult,
        role=ModelRole.FAST,
        run_id=state.get("run_id"),
        node_name="classify_idea",
    )

    return {
        "idea_classification": result.idea_type,
        "current_node": "classify_idea",
    }


async def choose_pattern_node(state: WorkflowState) -> dict[str, Any]:
    """Choose product pattern via deterministic lookup — no LLM call.

    The idea_classification from the previous node is sufficient to select the
    right pattern. An LLM call here adds latency and tokens with no quality gain.
    """
    log = logger.bind(run_id=state.get("run_id"), node="choose_pattern")
    log.info("node_start")

    idea_type = state.get("idea_classification", "new_product")
    pattern = _PATTERN_MAP.get(idea_type, "saas_webapp")
    rationale = _PATTERN_RATIONALE.get(pattern, "Default SaaS web application pattern")

    log.info("pattern_selected", idea_type=idea_type, pattern=pattern)

    return {
        "selected_pattern": pattern,
        "pattern_rationale": rationale,
        "current_node": "choose_pattern",
    }
