"""
Artifact endpoints: read, trigger partial regeneration, QA.
"""

from fastapi import APIRouter, HTTPException, status
import structlog

from app.deps import CurrentUser
from app.db.queries import RunsDB, ArtifactsDB, QAReportsDB
from app.models.artifacts import ArtifactResponse, ArtifactTypeEnum
from app.models.qa import QAReportResponse
from app.queue.jobs import JobQueue, JobType

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/{run_id}/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(run_id: str, current_user: CurrentUser) -> list[ArtifactResponse]:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    rows = await ArtifactsDB.list_by_run(run_id)
    return [ArtifactResponse.from_db(r) for r in rows]


@router.get("/{run_id}/artifacts/{artifact_type}", response_model=ArtifactResponse)
async def get_artifact(
    run_id: str,
    artifact_type: ArtifactTypeEnum,
    current_user: CurrentUser,
) -> ArtifactResponse:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    row = await ArtifactsDB.get_latest(run_id, artifact_type.value)
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return ArtifactResponse.from_db(row)


@router.post(
    "/{run_id}/artifacts/{artifact_type}/regenerate",
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_artifact(
    run_id: str,
    artifact_type: ArtifactTypeEnum,
    current_user: CurrentUser,
) -> dict:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Mark artifact stale
    await ArtifactsDB.mark_stale(run_id, artifact_type.value)

    job = await JobQueue.enqueue(
        run_id=run_id,
        job_type=JobType.REGENERATE_ARTIFACT,
        payload={"run_id": run_id, "artifact_type": artifact_type.value},
    )

    logger.info("artifact_regeneration_queued", run_id=run_id, artifact_type=artifact_type.value)
    return {"job_id": str(job["id"])}


@router.get("/{run_id}/qa", response_model=QAReportResponse)
async def get_qa_report(run_id: str, current_user: CurrentUser) -> QAReportResponse:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    row = await QAReportsDB.get_latest(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="No QA report yet")
    return QAReportResponse.from_db(row)


@router.post("/{run_id}/qa/evaluate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_qa_evaluation(run_id: str, current_user: CurrentUser) -> dict:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    job = await JobQueue.enqueue(
        run_id=run_id,
        job_type=JobType.RUN_QA,
        payload={"run_id": run_id},
    )

    logger.info("qa_evaluation_queued", run_id=run_id)
    return {"job_id": str(job["id"])}
