"""
Run endpoints: CRUD for intake runs, trigger orchestration, approvals.
"""

import asyncio
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from app.deps import CurrentUser
from app.db.queries import RunsDB, ArtifactsDB, ApprovalsDB, JobsDB, QAReportsDB
from app.models.runs import (
    CreateRunRequest,
    RunResponse,
    RunSummaryResponse,
    ApprovalRequest,
    ApprovalResponse,
)
from app.queue.jobs import JobQueue, JobType

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("", response_model=list[RunSummaryResponse])
async def list_runs(current_user: CurrentUser) -> list[RunSummaryResponse]:
    rows = await RunsDB.list_by_user(current_user.user_id)
    return [RunSummaryResponse.from_db(r) for r in rows]


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    body: CreateRunRequest,
    current_user: CurrentUser,
) -> RunResponse:
    run_id = str(uuid4())

    run = await RunsDB.create(
        run_id=run_id,
        user_id=current_user.user_id,
        title=body.title,
        raw_input=body.business_idea,
        target_users=body.target_users,
        business_context=body.meeting_notes,
        raw_requirements=body.raw_requirements,
        constraints=body.constraints,
        input_type="text",
    )

    # Enqueue the orchestration job
    await JobQueue.enqueue(
        run_id=run_id,
        user_id=current_user.user_id,
        job_type=JobType.ORCHESTRATE_RUN,
        payload={"run_id": run_id},
    )

    logger.info("run_created", run_id=run_id, user_id=current_user.user_id)
    return RunResponse.from_db(run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, current_user: CurrentUser) -> RunResponse:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    artifacts, qa_report = await asyncio.gather(
        ArtifactsDB.list_by_run(run_id),
        QAReportsDB.get_latest(run_id),
    )
    return RunResponse.from_db(run, artifacts=artifacts, qa_report=qa_report)


@router.post("/{run_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_run(run_id: str, current_user: CurrentUser) -> None:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    cancelled_jobs = await JobsDB.cancel_by_run(run_id)
    await RunsDB.update_status(run_id, "cancelled")
    logger.info("run_cancelled", run_id=run_id, cancelled_jobs=cancelled_jobs)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(run_id: str, current_user: CurrentUser) -> None:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    # Cancel any pending/running jobs first so the worker doesn't pick them up
    await JobsDB.cancel_by_run(run_id)
    await RunsDB.delete(run_id)
    logger.info("run_deleted", run_id=run_id)


@router.post("/{run_id}/approval", response_model=ApprovalResponse)
async def submit_approval(
    run_id: str,
    body: ApprovalRequest,
    current_user: CurrentUser,
) -> ApprovalResponse:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run["status"] not in ("needs_review", "qa_passed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run is in status '{run['status']}', not awaiting approval",
        )

    approval = await ApprovalsDB.create(
        run_id=run_id,
        user_id=current_user.user_id,
        decision=body.decision,
        comment=body.comment,
    )

    new_status = "approved" if body.decision == "approved" else "needs_review"
    await RunsDB.update_status(run_id, new_status)

    logger.info("approval_submitted", run_id=run_id, decision=body.decision)
    return ApprovalResponse.from_db(approval)


@router.post("/{run_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_run(run_id: str, current_user: CurrentUser) -> dict:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    await RunsDB.update_status(run_id, "pending")

    job = await JobQueue.enqueue(
        run_id=run_id,
        user_id=current_user.user_id,
        job_type=JobType.ORCHESTRATE_RUN,
        payload={"run_id": run_id},
    )

    logger.info("run_regeneration_queued", run_id=run_id, user_id=current_user.user_id)
    return {"job_id": str(job["id"])}


@router.get("/{run_id}/approvals", response_model=list[ApprovalResponse])
async def list_approvals(run_id: str, current_user: CurrentUser) -> list[ApprovalResponse]:
    run = await RunsDB.get(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    rows = await ApprovalsDB.list_by_run(run_id)
    return [ApprovalResponse.from_db(r) for r in rows]
