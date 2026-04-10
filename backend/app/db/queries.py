"""
Typed database query wrappers. All queries use asyncpg directly.
All mutations are parameterized — no string interpolation.
Column names match supabase/migrations/001_initial_schema.sql exactly.
"""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.db.client import get_db_pool


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Runs ──────────────────────────────────────────────────────────────────────

class RunsDB:
    @staticmethod
    async def list_by_user(user_id: str) -> list[dict[str, Any]]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT r.*,
                       COUNT(a.id) AS artifact_count,
                       qr.pass_rate AS qa_score
                FROM intake_runs r
                LEFT JOIN artifacts a ON a.run_id = r.id AND a.status != 'stale'
                LEFT JOIN LATERAL (
                    SELECT pass_rate FROM qa_reports
                    WHERE run_id = r.id
                    ORDER BY created_at DESC LIMIT 1
                ) qr ON true
                WHERE r.user_id = $1
                GROUP BY r.id, qr.pass_rate
                ORDER BY r.created_at DESC
                """,
                user_id,
            )
        return [dict(r) for r in rows]

    @staticmethod
    async def get(run_id: str, user_id: str) -> dict[str, Any] | None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM intake_runs WHERE id = $1 AND user_id = $2",
                run_id, user_id,
            )
        return dict(row) if row else None

    @staticmethod
    async def create(
        run_id: str,
        user_id: str,
        title: str,
        raw_input: str,
        target_users: str | None = None,
        business_context: str | None = None,
        constraints: str | None = None,
        input_type: str = "text",
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO intake_runs
                    (id, user_id, title, status, raw_input, input_type,
                     target_users, business_context, constraints)
                VALUES ($1, $2, $3, 'queued', $4, $5, $6, $7, $8)
                RETURNING *
                """,
                run_id, user_id, title, raw_input, input_type,
                target_users, business_context, constraints,
            )
        return dict(row)  # type: ignore[arg-type]

    @staticmethod
    async def update_status(run_id: str, status: str, **kwargs: Any) -> None:
        pool = await get_db_pool()
        set_pairs = ["status = $2", "updated_at = $3"]
        params: list[Any] = [run_id, status, _now()]
        idx = 4
        for key, val in kwargs.items():
            set_pairs.append(f"{key} = ${idx}")
            params.append(val)
            idx += 1
        async with pool.acquire() as conn:
            await conn.execute(
                f"UPDATE intake_runs SET {', '.join(set_pairs)} WHERE id = $1",
                *params,
            )

    @staticmethod
    async def delete(run_id: str) -> None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM intake_runs WHERE id = $1", run_id)


# ── Artifacts ─────────────────────────────────────────────────────────────────

class ArtifactsDB:
    @staticmethod
    async def list_by_run(run_id: str) -> list[dict[str, Any]]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT ON (artifact_type) *
                FROM artifacts
                WHERE run_id = $1
                ORDER BY artifact_type, version DESC
                """,
                run_id,
            )
        return [dict(r) for r in rows]

    @staticmethod
    async def get_latest(run_id: str, artifact_type: str) -> dict[str, Any] | None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM artifacts
                WHERE run_id = $1 AND artifact_type = $2
                ORDER BY version DESC LIMIT 1
                """,
                run_id, artifact_type,
            )
        return dict(row) if row else None

    @staticmethod
    async def upsert(
        run_id: str,
        user_id: str,
        artifact_type: str,
        content_json: dict[str, Any],
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get current max version
            current = await conn.fetchval(
                "SELECT MAX(version) FROM artifacts WHERE run_id = $1 AND artifact_type = $2",
                run_id, artifact_type,
            )
            version = (current or 0) + 1
            artifact_id = str(uuid4())
            row = await conn.fetchrow(
                """
                INSERT INTO artifacts
                    (id, run_id, user_id, artifact_type, version, content, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'ready')
                RETURNING *
                """,
                artifact_id, run_id, user_id, artifact_type, version,
                json.dumps(content_json),
            )
        return dict(row)  # type: ignore[arg-type]

    @staticmethod
    async def mark_stale(run_id: str, artifact_type: str) -> None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE artifacts SET status = 'stale', updated_at = $3
                WHERE run_id = $1 AND artifact_type = $2
                """,
                run_id, artifact_type, _now(),
            )


# ── QA Reports ────────────────────────────────────────────────────────────────

class QAReportsDB:
    @staticmethod
    async def get_latest(run_id: str) -> dict[str, Any] | None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM qa_reports WHERE run_id = $1 ORDER BY created_at DESC LIMIT 1",
                run_id,
            )
        return dict(row) if row else None

    @staticmethod
    async def upsert(
        run_id: str,
        user_id: str,
        overall_score: float,
        max_score: float,
        pass_rate: float,
        critical_issues: int,
        export_ready: bool,
        checks: list[dict[str, Any]],
        remediation_tasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        report_id = str(uuid4())
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO qa_reports
                    (id, run_id, user_id, overall_score, max_score, pass_rate,
                     critical_issues, export_ready, checks, remediation_tasks)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (run_id) DO UPDATE SET
                    overall_score = EXCLUDED.overall_score,
                    max_score = EXCLUDED.max_score,
                    pass_rate = EXCLUDED.pass_rate,
                    critical_issues = EXCLUDED.critical_issues,
                    export_ready = EXCLUDED.export_ready,
                    checks = EXCLUDED.checks,
                    remediation_tasks = EXCLUDED.remediation_tasks,
                    updated_at = NOW()
                RETURNING *
                """,
                report_id, run_id, user_id,
                overall_score, max_score, pass_rate,
                critical_issues, export_ready,
                json.dumps(checks), json.dumps(remediation_tasks),
            )
        return dict(row)  # type: ignore[arg-type]


# ── Jobs ──────────────────────────────────────────────────────────────────────

class JobsDB:
    @staticmethod
    async def get(job_id: str) -> dict[str, Any] | None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM queued_jobs WHERE id = $1", job_id)
        return dict(row) if row else None

    @staticmethod
    async def list_by_run(run_id: str) -> list[dict[str, Any]]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM queued_jobs WHERE run_id = $1 ORDER BY created_at DESC",
                run_id,
            )
        return [dict(r) for r in rows]

    @staticmethod
    async def get_latest_for_run(run_id: str) -> dict[str, Any] | None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM queued_jobs WHERE run_id = $1 ORDER BY created_at DESC LIMIT 1",
                run_id,
            )
        return dict(row) if row else None

    @staticmethod
    async def update_status(
        job_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE queued_jobs
                SET status = $2,
                    error_message = COALESCE($3, error_message),
                    updated_at = $4,
                    started_at = CASE WHEN $2 = 'running' AND started_at IS NULL
                                      THEN $4 ELSE started_at END,
                    completed_at = CASE WHEN $2 IN ('completed','failed','cancelled')
                                        THEN $4 ELSE completed_at END
                WHERE id = $1
                """,
                job_id, status, error_message, _now(),
            )

    @staticmethod
    async def increment_retry(job_id: str, error_message: str) -> int:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE queued_jobs
                SET retry_count = retry_count + 1, error_message = $2,
                    status = 'queued', updated_at = $3
                WHERE id = $1
                RETURNING retry_count
                """,
                job_id, error_message, _now(),
            )
        return row["retry_count"] if row else 0  # type: ignore[index]

    @staticmethod
    async def claim_next(job_types: list[str]) -> dict[str, Any] | None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE queued_jobs
                SET status = 'running', started_at = $2, updated_at = $2
                WHERE id = (
                    SELECT id FROM queued_jobs
                    WHERE status = 'queued' AND job_type = ANY($1)
                      AND retry_count < max_retries
                    ORDER BY priority ASC, created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *
                """,
                job_types, _now(),
            )
        return dict(row) if row else None


# ── Approvals ─────────────────────────────────────────────────────────────────

class ApprovalsDB:
    @staticmethod
    async def create(
        run_id: str,
        user_id: str,
        decision: str,   # "approved" | "rejected"
        comment: str | None,
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        approval_id = str(uuid4())
        approved = decision == "approved"
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO approvals (id, run_id, user_id, approved, comment)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (run_id) DO UPDATE SET
                    approved = EXCLUDED.approved,
                    comment = EXCLUDED.comment
                RETURNING *
                """,
                approval_id, run_id, user_id, approved, comment,
            )
        return dict(row)  # type: ignore[arg-type]

    @staticmethod
    async def list_by_run(run_id: str) -> list[dict[str, Any]]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM approvals WHERE run_id = $1 ORDER BY created_at DESC",
                run_id,
            )
        return [dict(r) for r in rows]


# ── Exports ───────────────────────────────────────────────────────────────────

class ExportsDB:
    @staticmethod
    async def create(
        run_id: str,
        user_id: str,
        fmt: str,
        storage_path: str | None = None,
        download_url: str | None = None,
        file_size_bytes: int | None = None,
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        export_id = str(uuid4())
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO export_records
                    (id, run_id, user_id, format, status, storage_path, download_url, file_size_bytes)
                VALUES ($1, $2, $3, $4, 'queued', $5, $6, $7)
                RETURNING *
                """,
                export_id, run_id, user_id, fmt,
                storage_path, download_url, file_size_bytes,
            )
        return dict(row)  # type: ignore[arg-type]

    @staticmethod
    async def update_status(
        export_id: str,
        status: str,
        storage_path: str | None = None,
        download_url: str | None = None,
        file_size_bytes: int | None = None,
        error_message: str | None = None,
    ) -> None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE export_records SET
                    status = $2,
                    storage_path = COALESCE($3, storage_path),
                    download_url = COALESCE($4, download_url),
                    file_size_bytes = COALESCE($5, file_size_bytes),
                    error_message = COALESCE($6, error_message),
                    updated_at = NOW()
                WHERE id = $1
                """,
                export_id, status, storage_path, download_url,
                file_size_bytes, error_message,
            )

    @staticmethod
    async def list_by_run(run_id: str) -> list[dict[str, Any]]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM export_records WHERE run_id = $1 ORDER BY created_at DESC",
                run_id,
            )
        return [dict(r) for r in rows]
