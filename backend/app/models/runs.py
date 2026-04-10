"""Pydantic models for intake runs and approvals."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Request models ────────────────────────────────────────────────────────────

class CreateRunRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    business_idea: str = Field(min_length=10)
    target_users: str = Field(min_length=5)
    meeting_notes: str | None = None
    raw_requirements: str | None = None
    constraints: str | None = None
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
            artifact_count=row.get("artifact_count", 0),
            qa_score=row.get("qa_score"),
        )


class SourceDocumentResponse(BaseModel):
    id: str
    doc_type: str
    content: str
    created_at: datetime

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> "SourceDocumentResponse":
        return cls(
            id=str(row["id"]),
            doc_type=row["doc_type"],
            content=row["content"],
            created_at=row["created_at"],
        )


class RunResponse(BaseModel):
    id: str
    workspace_id: str | None
    user_id: str
    title: str
    status: str
    graph_thread_id: str | None
    current_node: str | None
    missing_info_flags: list[str]
    idea_classification: str | None
    selected_pattern: str | None
    created_at: datetime
    updated_at: datetime
    source_documents: list[SourceDocumentResponse] = []
    artifacts: list[Any] = []
    latest_qa_report: Any | None = None

    @classmethod
    def from_db(
        cls,
        row: dict[str, Any],
        artifacts: list[dict[str, Any]] | None = None,
    ) -> "RunResponse":
        from app.models.artifacts import ArtifactResponse  # avoid circular
        return cls(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]) if row.get("workspace_id") else None,
            user_id=str(row["user_id"]),
            title=row["title"],
            status=row["status"],
            graph_thread_id=row.get("graph_thread_id"),
            current_node=row.get("current_node"),
            missing_info_flags=row.get("missing_info_flags") or [],
            idea_classification=row.get("idea_classification"),
            selected_pattern=row.get("selected_pattern"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            artifacts=[ArtifactResponse.from_db(a) for a in (artifacts or [])],
        )


class ApprovalResponse(BaseModel):
    id: str
    run_id: str
    user_id: str
    decision: str
    comment: str | None
    created_at: datetime

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> "ApprovalResponse":
        return cls(
            id=str(row["id"]),
            run_id=str(row["run_id"]),
            user_id=str(row["user_id"]),
            decision=row["decision"],
            comment=row.get("comment"),
            created_at=row["created_at"],
        )
