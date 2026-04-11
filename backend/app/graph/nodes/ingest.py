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
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


# ── Pydantic schemas for node outputs ─────────────────────────────────────────

class MissingInfoResult(BaseModel):
    missing_fields: list[str]
    can_proceed: bool
    assumptions_to_make: list[str]


class ClassificationResult(BaseModel):
    idea_type: str
    confidence: str
    rationale: str


class PatternResult(BaseModel):
    selected_pattern: str
    pattern_rationale: str


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
    """Identify gaps and surface them as assumptions. Never blocks execution."""
    log = logger.bind(run_id=state.get("run_id"), node="detect_missing_info")
    log.info("node_start")

    brief = state.get("extracted_brief", {})
    submission_text = json.dumps({
        "business_idea": brief.get("business_idea"),
        "target_users": brief.get("target_users"),
        "raw_requirements": brief.get("raw_requirements"),
        "meeting_notes": brief.get("meeting_notes"),
        "constraints": brief.get("constraints"),
        "timeline": brief.get("timeline"),
    }, indent=2)

    prompt = get_prompt("detect_missing_info")
    messages = prompt.build_messages(submission=submission_text)

    result = await generate_structured(
        messages=messages,
        response_model=MissingInfoResult,
        role=ModelRole.FAST,
        run_id=state.get("run_id"),
        node_name="detect_missing_info",
    )

    log.info(
        "missing_info_result",
        missing=result.missing_fields,
        can_proceed=True,  # always proceed; flags are advisory assumptions only
    )

    return {
        "missing_info_flags": result.missing_fields,
        "can_proceed": True,  # gate removed — form validation guarantees minimum data
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
    """Choose product pattern based on idea classification."""
    log = logger.bind(run_id=state.get("run_id"), node="choose_pattern")
    log.info("node_start")

    brief = state.get("extracted_brief", {})
    prompt = get_prompt("choose_pattern")
    messages = prompt.build_messages(
        idea_type=state.get("idea_classification", "new_product"),
        business_idea=brief.get("business_idea", ""),
    )

    result = await generate_structured(
        messages=messages,
        response_model=PatternResult,
        role=ModelRole.FAST,
        run_id=state.get("run_id"),
        node_name="choose_pattern",
    )

    return {
        "selected_pattern": result.selected_pattern,
        "pattern_rationale": result.pattern_rationale,
        "current_node": "choose_pattern",
    }
