"""
Typed database query wrappers. All queries use asyncpg directly.
All mutations are parameterized — no string interpolation.
"""

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
        source_inputs: dict[str, Any],
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        now = _now()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO intake_runs (id, user_id, title, status, source_inputs, created_at, updated_at)
                VALUES ($1, $2, $3, 'pending', $4, $5, $5)
                RETURNING *
                """,
                run_id, user_id, title,
                str(source_inputs),  # stored as jsonb
                now,
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
        artifact_type: str,
        content_json: dict[str, Any],
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        now = _now()
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
                INSERT INTO artifacts (id, run_id, artifact_type, version, content_json, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, 'draft', $6, $6)
                RETURNING *
                """,
                artifact_id, run_id, artifact_type, version,
                str(content_json), now,
            )
        return dict(row)  # type: ignore[arg-type]

    @staticmethod
    async def mark_stale(run_id: str, artifact_type: str) -> None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE artifacts SET status = 'stale', updated_at = $3 WHERE run_id = $1 AND artifact_type = $2",
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
    async def create(
        run_id: str,
        overall_score: float,
        max_score: float,
        pass_rate: float,
        critical_issues: int,
        warnings: int,
        export_ready: bool,
        report_json: dict[str, Any],
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        report_id = str(uuid4())
        now = _now()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO qa_reports
                (id, run_id, overall_score, max_score, pass_rate, critical_issues, warnings, export_ready, report_json, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                RETURNING *
                """,
                report_id, run_id, overall_score, max_score, pass_rate,
                critical_issues, warnings, export_ready, str(report_json), now,
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
        current_step: str | None = None,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE queued_jobs
                SET status = $2, current_step = COALESCE($3, current_step),
                    progress = COALESCE($4, progress),
                    error_message = COALESCE($5, error_message),
                    updated_at = $6
                WHERE id = $1
                """,
                job_id, status, current_step, progress, error_message, _now(),
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
                SET status = 'running', updated_at = $2
                WHERE id = (
                    SELECT id FROM queued_jobs
                    WHERE status = 'queued' AND job_type = ANY($1)
                    ORDER BY created_at ASC
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
        decision: str,
        comment: str | None,
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        approval_id = str(uuid4())
        now = _now()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO approvals (id, run_id, user_id, decision, comment, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                approval_id, run_id, user_id, decision, comment, now,
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
        fmt: str,
        file_url: str,
        file_size_bytes: int,
    ) -> dict[str, Any]:
        pool = await get_db_pool()
        export_id = str(uuid4())
        now = _now()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO exports (id, run_id, format, file_url, file_size_bytes, generated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                export_id, run_id, fmt, file_url, file_size_bytes, now,
            )
        return dict(row)  # type: ignore[arg-type]

    @staticmethod
    async def list_by_run(run_id: str) -> list[dict[str, Any]]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM exports WHERE run_id = $1 ORDER BY generated_at DESC",
                run_id,
            )
        return [dict(r) for r in rows]
