from fastapi import APIRouter, HTTPException, status
import structlog

from app.deps import CurrentUser
from app.db.queries import RunsDB, ExportsDB
from app.models.exports import ExportRequest, ExportResponse
from app.queue.jobs import JobQueue, JobType

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def request_export(body: ExportRequest, current_user: CurrentUser) -> dict:
    run = await RunsDB.get(body.run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run["status"] not in ("approved", "exported"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run must be approved before exporting",
        )

    job = await JobQueue.enqueue(
        run_id=body.run_id,
        job_type=JobType.GENERATE_EXPORT,
        payload={"run_id": body.run_id, "formats": [f.value for f in body.formats]},
    )

    logger.info("export_queued", run_id=body.run_id, formats=body.formats)
    return {"job_id": str(job["id"])}


@router.get("/runs/{run_id}/exports", response_model=list[ExportResponse])
async def list_exports(run_id: str, current_user: CurrentUser) -> list[ExportResponse]:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    rows = await ExportsDB.list_by_run(run_id)
    return [ExportResponse.from_db(r) for r in rows]
