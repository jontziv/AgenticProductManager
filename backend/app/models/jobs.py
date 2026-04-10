from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class JobTypeEnum(str, Enum):
    ORCHESTRATE_RUN = "orchestrate_run"
    REGENERATE_ARTIFACT = "regenerate_artifact"
    RUN_QA = "run_qa"
    GENERATE_EXPORT = "generate_export"


class JobResponse(BaseModel):
    id: str
    run_id: str
    job_type: str
    status: str
    progress: int | None
    current_step: str | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> "JobResponse":
        return cls(
            id=str(row["id"]),
            run_id=str(row["run_id"]),
            job_type=row["job_type"],
            status=row["status"],
            progress=row.get("progress"),
            current_step=row.get("current_step"),
            error_message=row.get("error_message"),
            retry_count=row.get("retry_count", 0),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
