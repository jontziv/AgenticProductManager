"""
Central model routing table. One place to change all model assignments.
Prefer cheapest adequate model per task type.
"""

from enum import Enum
from functools import lru_cache

from app.config import get_settings


class ModelRole(str, Enum):
    FAST = "fast"            # Classification, extraction, tagging
    STRUCTURED = "structured"  # Schema-critical JSON artifact generation
    SYNTHESIS = "synthesis"  # Higher-quality writing, architecture, QA evaluation
    EVAL = "eval"            # QA/evaluation rubric scoring
    AUDIO = "audio"          # Whisper transcription
    AUDIO_FALLBACK = "audio_fallback"


@lru_cache(maxsize=1)
def get_model_routing() -> dict[ModelRole, str]:
    s = get_settings()
    return {
        ModelRole.FAST: s.groq_model_fast,
        ModelRole.STRUCTURED: s.groq_model_structured,
        ModelRole.SYNTHESIS: s.groq_model_synthesis,
        ModelRole.EVAL: s.groq_model_eval,
        ModelRole.AUDIO: s.groq_model_audio,
        ModelRole.AUDIO_FALLBACK: s.groq_model_audio_fallback,
    }


def get_model(role: ModelRole) -> str:
    return get_model_routing()[role]


# Task-to-model mapping (informational — use get_model() in code)
TASK_MODEL_GUIDE = {
    "ingest_input": ModelRole.FAST,
    "detect_missing_info": ModelRole.FAST,
    "classify_idea": ModelRole.FAST,
    "choose_pattern": ModelRole.FAST,
    "normalize_extract": ModelRole.STRUCTURED,
    "create_problem_framing": ModelRole.STRUCTURED,
    "generate_personas": ModelRole.STRUCTURED,
    "generate_mvp_scope": ModelRole.STRUCTURED,
    "generate_success_metrics": ModelRole.STRUCTURED,
    "generate_user_stories": ModelRole.STRUCTURED,
    "generate_backlog": ModelRole.STRUCTURED,
    "generate_test_cases": ModelRole.STRUCTURED,
    "generate_risks": ModelRole.STRUCTURED,
    "generate_architecture": ModelRole.SYNTHESIS,
    "consistency_check": ModelRole.SYNTHESIS,
    "qa_evaluation": ModelRole.EVAL,
    "remediation_router": ModelRole.EVAL,
    "transcribe_audio": ModelRole.AUDIO,
}
