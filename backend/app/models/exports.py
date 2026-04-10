from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ExportFormatEnum(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    JIRA_CSV = "jira_csv"
    LINEAR_CSV = "linear_csv"


class ExportRequest(BaseModel):
    run_id: str
    formats: list[ExportFormatEnum]


class ExportResponse(BaseModel):
    id: str
    run_id: str
    format: str
    file_url: str
    file_size_bytes: int
    generated_at: datetime

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> "ExportResponse":
        return cls(
            id=str(row["id"]),
            run_id=str(row["run_id"]),
            format=row["format"],
            file_url=row["file_url"],
            file_size_bytes=row.get("file_size_bytes", 0),
            generated_at=row["generated_at"],
        )
