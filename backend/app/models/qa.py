from datetime import datetime
from typing import Any

from pydantic import BaseModel


class QACheckResponse(BaseModel):
    id: str
    category: str
    name: str
    description: str
    status: str
    score: float
    max_score: float
    findings: list[str]
    remediation: str | None
    artifact_type: str | None
    artifact_field: str | None


class RemediationTaskResponse(BaseModel):
    id: str
    check_id: str
    description: str
    affected_artifact: str
    priority: str
    auto_fixable: bool


class QAReportResponse(BaseModel):
    id: str
    run_id: str
    overall_score: float
    max_score: float
    pass_rate: float
    critical_issues: int
    warnings: int
    export_ready: bool
    checks: list[QACheckResponse]
    remediation_tasks: list[RemediationTaskResponse]
    created_at: datetime

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> "QAReportResponse":
        import json as _json

        def _load_jsonb(val: Any) -> list:
            if val is None:
                return []
            if isinstance(val, str):
                try:
                    return _json.loads(val)
                except Exception:
                    return []
            return val if isinstance(val, list) else []

        return cls(
            id=str(row["id"]),
            run_id=str(row["run_id"]),
            overall_score=row.get("overall_score") or 0,
            max_score=row.get("max_score") or 100,
            pass_rate=row.get("pass_rate") or 0,
            critical_issues=row.get("critical_issues") or 0,
            warnings=row.get("warnings") or 0,
            export_ready=bool(row.get("export_ready", False)),
            checks=_load_jsonb(row.get("checks")),
            remediation_tasks=_load_jsonb(row.get("remediation_tasks")),
            created_at=row["created_at"],
        )
