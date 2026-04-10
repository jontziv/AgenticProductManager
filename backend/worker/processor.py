"""
Job processor: handles a single claimed job end-to-end.
One processor per job type — clean separation.
"""

import json
from typing import Any

import structlog

from app.db.queries import JobsDB, RunsDB, ArtifactsDB, QAReportsDB, ExportsDB
from app.graph.graph import get_graph
from app.graph.state import WorkflowState
from app.evaluators.harness import run_qa_evaluation
from app.services.export_service import generate_export_pack
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


async def process_job(job: dict[str, Any]) -> None:
    job_id = str(job["id"])
    job_type = job["job_type"]
    run_id = str(job["run_id"])
    user_id = str(job["user_id"])

    # Payload stored as JSONB string
    try:
        raw_payload = job.get("payload", "{}")
        payload: dict[str, Any] = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
    except Exception:
        payload = {}

    log = logger.bind(job_id=job_id, job_type=job_type, run_id=run_id)
    log.info("job_processing_start")

    try:
        if job_type == "orchestrate_run":
            await _orchestrate_run(run_id, user_id, job_id, log)
        elif job_type == "regenerate_artifact":
            await _regenerate_artifact(run_id, user_id, payload.get("artifact_type"), job_id, log)
        elif job_type == "run_qa":
            await _run_qa(run_id, user_id, job_id, log)
        elif job_type == "generate_export":
            await _generate_export(run_id, user_id, payload.get("formats", ["markdown", "json"]), job_id, log)
        else:
            raise ValueError(f"Unknown job_type: {job_type}")

        await JobsDB.update_status(job_id, "completed")
        log.info("job_completed")

    except Exception as exc:
        log.exception("job_failed", error=str(exc))
        retry_count = await JobsDB.increment_retry(job_id, str(exc))
        if retry_count >= settings.worker_max_retries:
            await JobsDB.update_status(job_id, "failed", error_message=str(exc))
            await RunsDB.update_status(run_id, "failed")
            log.error("job_terminal_failure", retries=retry_count)
        else:
            log.warning("job_will_retry", retry=retry_count)


async def _orchestrate_run(run_id: str, user_id: str, job_id: str, log: Any) -> None:
    """Run the full LangGraph workflow for a new intake run."""
    run = await RunsDB.get_by_id(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    await RunsDB.update_status(run_id, "processing")

    # Build graph input from DB columns
    initial_state: WorkflowState = {
        "run_id": run_id,
        "user_id": user_id,
        "source_inputs": {
            "business_idea": run.get("raw_input") or "",
            "target_users": run.get("target_users") or "",
            "business_context": run.get("business_context") or "",
            "constraints": run.get("constraints") or "",
            "input_type": run.get("input_type") or "text",
        },
        "qa_attempt": 0,
        "audit_events": [],
    }

    graph = get_graph()
    config = {"configurable": {"thread_id": run_id}}

    final_state: WorkflowState = {}
    async for event in graph.astream(initial_state, config=config):
        node_name = list(event.keys())[0] if event else None
        if node_name:
            log.debug("graph_node_complete", node=node_name)
            final_state.update(list(event.values())[0] if event else {})

    # Persist generated artifacts
    artifact_keys = [
        "problem_framing", "personas", "mvp_scope", "success_metrics",
        "user_stories", "backlog_items", "test_cases", "risks", "architecture",
    ]
    for key in artifact_keys:
        content = final_state.get(key)  # type: ignore[call-overload]
        if content:
            await ArtifactsDB.upsert(run_id, user_id, key, content)

    # Persist QA report
    qa = final_state.get("qa_report") or {}  # type: ignore[call-overload]
    if qa:
        await QAReportsDB.upsert(
            run_id=run_id,
            user_id=user_id,
            overall_score=float(qa.get("overall_score", 0)),
            max_score=float(qa.get("max_score", 100)),
            pass_rate=float(qa.get("pass_rate", 0)),
            critical_issues=int(qa.get("critical_issues", 0)),
            export_ready=bool(qa.get("export_ready", False)),
            checks=qa.get("checks", []),
            remediation_tasks=qa.get("remediation_tasks", []),
        )

    # Update run — only columns that actually exist in the schema
    idea_type = final_state.get("idea_classification")  # type: ignore[call-overload]
    await RunsDB.update_status(
        run_id, "needs_review",
        langgraph_thread_id=run_id,
        **({"idea_type": idea_type} if idea_type else {}),
    )

    log.info("orchestration_complete", artifacts=len(artifact_keys))


async def _regenerate_artifact(
    run_id: str,
    user_id: str,
    artifact_type: str | None,
    job_id: str,
    log: Any,
) -> None:
    """Regenerate a single artifact using the current run state."""
    if not artifact_type:
        raise ValueError("artifact_type required for regeneration")

    # Load current artifacts from DB to use as context
    artifacts_rows = await ArtifactsDB.list_by_run(run_id)
    current_state: dict[str, Any] = {}
    for row in artifacts_rows:
        key = row["artifact_type"]
        content = row.get("content") or {}
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                content = {}
        current_state[key] = content

    # Import the right generator node
    from app.graph.nodes import generate as gen_nodes
    generator_map = {
        "problem_framing": gen_nodes.create_problem_framing_node,
        "personas": gen_nodes.generate_personas_node,
        "mvp_scope": gen_nodes.generate_mvp_scope_node,
        "success_metrics": gen_nodes.generate_success_metrics_node,
        "user_stories": gen_nodes.generate_user_stories_node,
        "backlog_items": gen_nodes.generate_backlog_node,
        "test_cases": gen_nodes.generate_test_cases_node,
        "risks": gen_nodes.generate_risks_node,
        "architecture": gen_nodes.generate_architecture_node,
    }

    node_fn = generator_map.get(artifact_type)
    if not node_fn:
        raise ValueError(f"No generator for artifact_type: {artifact_type}")

    run = await RunsDB.get_by_id(run_id)
    source_inputs = {
        "business_idea": (run.get("raw_input") or "") if run else "",
        "target_users": (run.get("target_users") or "") if run else "",
        "business_context": (run.get("business_context") or "") if run else "",
        "constraints": (run.get("constraints") or "") if run else "",
    }

    workflow_state: WorkflowState = {
        "run_id": run_id,
        "user_id": user_id,
        "source_inputs": source_inputs,
        "extracted_brief": source_inputs,
        **{k: v for k, v in current_state.items()},  # type: ignore[misc]
    }

    updates = await node_fn(workflow_state)
    new_content = updates.get(artifact_type)
    if new_content:
        await ArtifactsDB.upsert(run_id, user_id, artifact_type, new_content)

    log.info("artifact_regenerated", artifact_type=artifact_type)


async def _run_qa(run_id: str, user_id: str, job_id: str, log: Any) -> None:
    """Run QA evaluation and persist report."""
    artifacts_rows = await ArtifactsDB.list_by_run(run_id)
    artifacts: dict[str, Any] = {}
    for row in artifacts_rows:
        key = row["artifact_type"]
        content = row.get("content") or {}
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                content = {}
        artifacts[key] = content

    run = await RunsDB.get_by_id(run_id)
    source_inputs: dict[str, Any] = {}
    if run:
        source_inputs = {
            "business_idea": run.get("raw_input") or "",
            "target_users": run.get("target_users") or "",
            "business_context": run.get("business_context") or "",
        }

    qa_report = await run_qa_evaluation(artifacts=artifacts, source_inputs=source_inputs, run_id=run_id)

    await QAReportsDB.upsert(
        run_id=run_id,
        user_id=user_id,
        overall_score=float(qa_report.get("overall_score", 0)),
        max_score=float(qa_report.get("max_score", 100)),
        pass_rate=float(qa_report.get("pass_rate", 0)),
        critical_issues=int(qa_report.get("critical_issues", 0)),
        export_ready=bool(qa_report.get("export_ready", False)),
        checks=qa_report.get("checks", []),
        remediation_tasks=qa_report.get("remediation_tasks", []),
    )

    new_status = "qa_passed" if qa_report.get("export_ready") else "needs_review"
    await RunsDB.update_status(run_id, new_status)
    log.info("qa_complete", export_ready=qa_report.get("export_ready"))


async def _generate_export(run_id: str, user_id: str, formats: list[str], job_id: str, log: Any) -> None:
    """Generate export files and upload to Supabase Storage."""
    artifacts_rows = await ArtifactsDB.list_by_run(run_id)
    artifacts: dict[str, Any] = {}
    for row in artifacts_rows:
        key = row["artifact_type"]
        content = row.get("content") or {}
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                content = {}
        artifacts[key] = content

    pack = await generate_export_pack(run_id=run_id, artifacts=artifacts, formats=formats)

    for fmt, data in pack.items():
        content_str = data.get("content", "")
        content_bytes = content_str.encode("utf-8")
        file_url: str | None = None

        try:
            from app.db.client import get_supabase_client
            client = get_supabase_client()
            bucket = settings.export_storage_bucket
            path = f"{run_id}/{fmt}.{_ext(fmt)}"
            client.storage.from_(bucket).upload(
                path=path,
                file=content_bytes,
                file_options={"content-type": data.get("mime", "text/plain")},
            )
            file_url = client.storage.from_(bucket).get_public_url(path)
        except Exception as exc:
            log.warning("storage_upload_failed", format=fmt, error=str(exc))

        await ExportsDB.create(
            run_id=run_id,
            user_id=user_id,
            fmt=fmt,
            download_url=file_url,
            file_size_bytes=len(content_bytes),
        )

    await RunsDB.update_status(run_id, "exported")
    log.info("exports_generated", formats=list(pack.keys()))


def _ext(fmt: str) -> str:
    return {"markdown": "md", "json": "json", "html": "html",
            "jira_csv": "csv", "linear_csv": "csv"}.get(fmt, "txt")
