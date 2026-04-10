"""
DB-backed job queue. Idempotent, retryable, inspectable.
Jobs are claimed atomically using SELECT FOR UPDATE SKIP LOCKED.
"""

from enum import Enum
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone

from app.db.client import get_db_pool


class JobType(str, Enum):
    ORCHESTRATE_RUN = "orchestrate_run"
    REGENERATE_ARTIFACT = "regenerate_artifact"
    RUN_QA = "run_qa"
    GENERATE_EXPORT = "generate_export"


class JobQueue:
    @staticmethod
    async def enqueue(
        run_id: str,
        job_type: JobType,
        payload: dict[str, Any],
        priority: int = 0,
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO queued_jobs
                (id, run_id, job_type, status, payload, priority, retry_count, created_at, updated_at)
                VALUES ($1, $2, $3, 'queued', $4, $5, 0, $6, $6)
                RETURNING *
                """,
                job_id, run_id, job_type.value, str(payload), priority, now,
            )
        return dict(row)  # type: ignore[arg-type]
