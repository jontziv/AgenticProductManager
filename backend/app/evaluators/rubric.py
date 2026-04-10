"""
QA evaluation rubric.
Defines categories, check definitions, weights, and hard-fail rules.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class CheckDef:
    id: str
    category: str
    name: str
    description: str
    max_score: float
    is_hard_fail: bool = False  # if True, failing this blocks export


RUBRIC: list[CheckDef] = [
    # ── Faithfulness ─────────────────────────────────────────────────────────
    CheckDef("F001", "Faithfulness", "Problem Grounding",
             "Problem statement references input facts, not invented claims",
             max_score=10, is_hard_fail=True),
    CheckDef("F002", "Faithfulness", "Persona-Input Alignment",
             "Personas match stated target users",
             max_score=10),
    CheckDef("F003", "Faithfulness", "Scope Traceability",
             "MVP scope decisions trace to problem framing",
             max_score=8),
    CheckDef("F004", "Faithfulness", "No Invented Evidence",
             "No metrics, integrations, or market data presented as fact without source",
             max_score=10, is_hard_fail=True),

    # ── Completeness ─────────────────────────────────────────────────────────
    CheckDef("C001", "Completeness", "Artifact Coverage",
             "All required artifact types are present and non-empty",
             max_score=10, is_hard_fail=True),
    CheckDef("C002", "Completeness", "Story Acceptance Criteria",
             "Every P0/High story has at least 3 acceptance criteria",
             max_score=10, is_hard_fail=True),
    CheckDef("C003", "Completeness", "Test Coverage",
             "High-priority acceptance criteria have corresponding test cases",
             max_score=8),
    CheckDef("C004", "Completeness", "Risk Mitigation",
             "Every identified risk has a specific mitigation strategy",
             max_score=8),

    # ── Compliance ────────────────────────────────────────────────────────────
    CheckDef("P001", "Compliance", "Story Format",
             "User stories follow As-a/I-want/So-that format",
             max_score=8),
    CheckDef("P002", "Compliance", "Priority Taxonomy",
             "Priorities use only defined values (High/Medium/Low, P0/P1/P2)",
             max_score=6),
    CheckDef("P003", "Compliance", "Metric Measurability",
             "Success metrics have quantifiable targets",
             max_score=8),
    CheckDef("P004", "Compliance", "Architecture Alignment",
             "Architecture recommendation addresses scope and identified risks",
             max_score=8, is_hard_fail=True),

    # ── Consistency ───────────────────────────────────────────────────────────
    CheckDef("K001", "Consistency", "Feature-Story Mapping",
             "Every core feature has at least one user story",
             max_score=10, is_hard_fail=True),
    CheckDef("K002", "Consistency", "Persona-Story Alignment",
             "User stories reference defined persona roles",
             max_score=6),
    CheckDef("K003", "Consistency", "Metric-Goal Linkage",
             "Success metrics connect to stated goals",
             max_score=8),

    # ── Format & Quality ─────────────────────────────────────────────────────
    CheckDef("Q001", "Format", "Schema Validity",
             "Artifact JSON conforms to required schema shapes",
             max_score=10, is_hard_fail=True),
    CheckDef("Q002", "Format", "Text Readability",
             "Prose is clear, professional, and free of obvious errors",
             max_score=6),
    CheckDef("Q003", "Format", "Length Appropriateness",
             "Text fields are neither too terse nor overly verbose",
             max_score=4),
]

MAX_TOTAL_SCORE = sum(c.max_score for c in RUBRIC)
HARD_FAIL_IDS = {c.id for c in RUBRIC if c.is_hard_fail}
