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
        report_data = row.get("report_json", {})
        return cls(
            id=str(row["id"]),
            run_id=str(row["run_id"]),
            overall_score=row.get("overall_score", 0),
            max_score=row.get("max_score", 100),
            pass_rate=row.get("pass_rate", 0),
            critical_issues=row.get("critical_issues", 0),
            warnings=row.get("warnings", 0),
            export_ready=row.get("export_ready", False),
            checks=report_data.get("checks", []),
            remediation_tasks=report_data.get("remediation_tasks", []),
            created_at=row["created_at"],
        )
