"""Pydantic models for artifacts and their typed content schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ArtifactTypeEnum(str, Enum):
    PROBLEM_FRAMING = "problem_framing"
    PERSONAS = "personas"
    MVP_SCOPE = "mvp_scope"
    SUCCESS_METRICS = "success_metrics"
    USER_STORIES = "user_stories"
    BACKLOG_ITEMS = "backlog_items"
    TEST_CASES = "test_cases"
    RISKS = "risks"
    ARCHITECTURE = "architecture"
    QA_REPORT = "qa_report"
    EXPORT_PACK = "export_pack"


# ── Artifact content schemas ──────────────────────────────────────────────────

class ProblemFraming(BaseModel):
    problem_statement: str
    opportunity: str
    hypothesis: str
    goals: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class Persona(BaseModel):
    name: str
    role: str
    archetype: str = ""
    goals: list[str]
    pain_points: list[str]
    behaviors: list[str]
    jobs_to_be_done: list[str] = Field(default_factory=list)


class Personas(BaseModel):
    personas: list[Persona] = Field(min_length=1, max_length=3)


class CoreFeature(BaseModel):
    id: str
    name: str
    description: str
    rationale: str
    priority: str = Field(pattern="^(P0|P1|P2)$")


class MvpScope(BaseModel):
    in_scope: list[str]
    out_of_scope: list[str]
    core_features: list[CoreFeature]
    deferred_features: list[str] = Field(default_factory=list)


class SuccessMetric(BaseModel):
    id: str
    category: str
    metric_name: str
    description: str
    target: str
    baseline: str | None = None
    signal_type: str = Field(pattern="^(leading|lagging)$")
    measurement_method: str


class SuccessMetrics(BaseModel):
    metrics: list[SuccessMetric]


class UserStory(BaseModel):
    id: str
    persona_ref: str
    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: list[str] = Field(min_length=1)
    priority: str = Field(pattern="^(High|Medium|Low)$")
    estimated_effort: str
    epic: str
    linked_test_ids: list[str] = Field(default_factory=list)


class UserStories(BaseModel):
    stories: list[UserStory]


class BacklogEpic(BaseModel):
    epic: str
    epic_description: str
    story_ids: list[str]
    priority_rationale: str


class BacklogItems(BaseModel):
    epics: list[BacklogEpic]
    total_story_count: int


class TestCase(BaseModel):
    id: str
    story_id: str | None = None
    scenario: str
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str]
    expected_result: str
    test_type: str = Field(pattern="^(unit|integration|e2e|manual)$")
    priority: str = Field(pattern="^(High|Medium|Low)$")


class TestCases(BaseModel):
    test_cases: list[TestCase]


class Risk(BaseModel):
    id: str
    category: str
    description: str
    likelihood: str = Field(pattern="^(High|Medium|Low)$")
    impact: str = Field(pattern="^(High|Medium|Low)$")
    mitigation: str
    owner: str
    linked_artifact: str | None = None


class Risks(BaseModel):
    risks: list[Risk]


class ArchitectureOption(BaseModel):
    name: str
    description: str
    components: list[str]
    data_flow: str
    pros: list[str]
    cons: list[str]
    cost_profile: str
    recommended: bool


class Architecture(BaseModel):
    options: list[ArchitectureOption] = Field(min_length=1, max_length=2)
    recommended_option: str
    rationale: str
    non_functional_requirements: list[str]
    technical_considerations: list[str]


# ── Response models ───────────────────────────────────────────────────────────

class ArtifactResponse(BaseModel):
    id: str
    run_id: str
    artifact_type: str
    version: int
    content: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> "ArtifactResponse":
        return cls(
            id=str(row["id"]),
            run_id=str(row["run_id"]),
            artifact_type=row["artifact_type"],
            version=row["version"],
            content=row["content_json"] if isinstance(row["content_json"], dict) else {},
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
