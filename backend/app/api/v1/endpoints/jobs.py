from fastapi import APIRouter, HTTPException
import structlog

from app.deps import CurrentUser
from app.db.queries import JobsDB, RunsDB
from app.models.jobs import JobResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, current_user: CurrentUser) -> JobResponse:
    job = await JobsDB.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Access check via run ownership
    run = await RunsDB.get(job["run_id"], current_user.user_id)
    if not run:
        raise HTTPException(status_code=403, detail="Forbidden")
    return JobResponse.from_db(job)


@router.post("/jobs/{job_id}/cancel", status_code=204)
async def cancel_job(job_id: str, current_user: CurrentUser) -> None:
    job = await JobsDB.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    run = await RunsDB.get(job["run_id"], current_user.user_id)
    if not run:
        raise HTTPException(status_code=403, detail="Forbidden")
    if job["status"] in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=409, detail="Job already terminal")
    await JobsDB.update_status(job_id, "cancelled")
    logger.info("job_cancelled", job_id=job_id)


@router.get("/runs/{run_id}/jobs", response_model=list[JobResponse])
async def list_run_jobs(run_id: str, current_user: CurrentUser) -> list[JobResponse]:  # noqa: E501
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    rows = await JobsDB.list_by_run(run_id)
    return [JobResponse.from_db(r) for r in rows]


@router.get("/runs/{run_id}/jobs/latest", response_model=JobResponse)
async def get_latest_job(run_id: str, current_user: CurrentUser) -> JobResponse:  # noqa: E501
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    job = await JobsDB.get_latest_for_run(run_id)
    if not job:
        raise HTTPException(status_code=404, detail="No jobs found")
    return JobResponse.from_db(job)
