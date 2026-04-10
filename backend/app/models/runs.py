"""Pydantic models for intake runs and approvals."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Request models ────────────────────────────────────────────────────────────

class CreateRunRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    business_idea: str = Field(min_length=10, description="Main idea / meeting notes")
    target_users: str = Field(min_length=3)
    constraints: str | None = None
    meeting_notes: str | None = None
    raw_requirements: str | None = None
    timeline: str | None = None
    assumptions: str | None = None
    audio_file_url: str | None = None


class ApprovalRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str | None = None


# ── Response models ───────────────────────────────────────────────────────────

class RunSummaryResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    artifact_count: int = 0
    qa_score: float | None = None

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> "RunSummaryResponse":
        return cls(
            id=str(row["id"]),
            title=row["title"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            artifact_count=int(row.get("artifact_count") or 0),
            qa_score=float(row["qa_score"]) if row.get("qa_score") is not None else None,
        )


class RunResponse(BaseModel):
    id: str
    user_id: str
    title: str
    status: str
    raw_input: str
    input_type: str
    target_users: str | None
    business_context: str | None
    constraints: str | None
    idea_type: str | None
    langgraph_thread_id: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    artifacts: list[Any] = []

    @classmethod
    def from_db(
        cls,
        row: dict[str, Any],
        artifacts: list[dict[str, Any]] | None = None,
    ) -> "RunResponse":
        from app.models.artifacts import ArtifactResponse  # avoid circular
        return cls(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            title=row["title"],
            status=row["status"],
            raw_input=row.get("raw_input") or "",
            input_type=row.get("input_type") or "text",
            target_users=row.get("target_users"),
            business_context=row.get("business_context"),
            constraints=row.get("constraints"),
            idea_type=row.get("idea_type"),
            langgraph_thread_id=row.get("langgraph_thread_id"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row.get("completed_at"),
            artifacts=[ArtifactResponse.from_db(a) for a in (artifacts or [])],
        )


class ApprovalResponse(BaseModel):
    id: str
    run_id: str
    user_id: str
    decision: str          # "approved" | "rejected" — derived from boolean
    comment: str | None
    created_at: datetime

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> "ApprovalResponse":
        # DB stores approved as BOOLEAN; map back to decision string
        approved_bool = row.get("approved")
        decision = "approved" if approved_bool else "rejected"
        return cls(
            id=str(row["id"]),
            run_id=str(row["run_id"]),
            user_id=str(row["user_id"]),
            decision=decision,
            comment=row.get("comment"),
            created_at=row["created_at"],
        )
