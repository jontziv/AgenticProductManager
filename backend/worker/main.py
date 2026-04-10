"""
Background worker entry point.
Polls queued_jobs table and dispatches to processor functions.
Runs until SIGTERM; handles graceful shutdown.
"""

import asyncio
import signal
import sys

import structlog

from app.config import get_settings
from app.db.client import get_db_pool, close_db_pool
from app.db.queries import JobsDB
from worker.processor import process_job

settings = get_settings()
logger = structlog.get_logger(__name__)

HANDLED_JOB_TYPES = [
    "orchestrate_run",
    "regenerate_artifact",
    "run_qa",
    "generate_export",
]

_shutdown = asyncio.Event()


def _handle_signal(sig: int, _frame: object) -> None:
    logger.info("shutdown_signal_received", signal=sig)
    _shutdown.set()


async def run_worker() -> None:
    """Main worker loop: claim and process jobs with concurrency control."""
    logger.info("worker_starting", concurrency=settings.worker_concurrency)
    semaphore = asyncio.Semaphore(settings.worker_concurrency)

    async def process_with_semaphore(job: dict) -> None:
        async with semaphore:
            await process_job(job)

    while not _shutdown.is_set():
        try:
            job = await JobsDB.claim_next(HANDLED_JOB_TYPES)
            if job:
                logger.info("job_claimed", job_id=str(job["id"]), job_type=job["job_type"])
                asyncio.create_task(process_with_semaphore(job))
            else:
                # No jobs — wait before polling again
                await asyncio.sleep(settings.worker_poll_interval_seconds)
        except Exception as exc:
            logger.exception("worker_loop_error", error=str(exc))
            await asyncio.sleep(settings.worker_poll_interval_seconds)

    logger.info("worker_shutting_down")


async def main() -> None:
    # Register OS signals for graceful shutdown
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Initialize DB pool
    await get_db_pool()
    logger.info("db_pool_initialized")

    try:
        await run_worker()
    finally:
        await close_db_pool()
        logger.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
