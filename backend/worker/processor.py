"""
Job processor: handles a single claimed job end-to-end.
One processor per job type — clean separation.
"""

import ast
import json
from typing import Any

import structlog

from app.db.queries import JobsDB, RunsDB, ArtifactsDB, QAReportsDB
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

    # Safely parse payload (stored as string repr in DB)
    try:
        raw_payload = job.get("payload", "{}")
        payload: dict[str, Any] = (
            json.loads(raw_payload) if raw_payload.startswith("{") else ast.literal_eval(raw_payload)
        )
    except Exception:
        payload = {}

    log = logger.bind(job_id=job_id, job_type=job_type, run_id=run_id)
    log.info("job_processing_start")

    try:
        if job_type == "orchestrate_run":
            await _orchestrate_run(run_id, job_id, log)
        elif job_type == "regenerate_artifact":
            await _regenerate_artifact(run_id, payload.get("artifact_type"), job_id, log)
        elif job_type == "run_qa":
            await _run_qa(run_id, job_id, log)
        elif job_type == "generate_export":
            await _generate_export(run_id, payload.get("formats", ["markdown", "json"]), job_id, log)
        else:
            raise ValueError(f"Unknown job_type: {job_type}")

        await JobsDB.update_status(job_id, "completed", progress=100)
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


async def _orchestrate_run(run_id: str, job_id: str, log: Any) -> None:
    """Run the full LangGraph workflow for a new intake run."""
    run = await RunsDB.get(run_id, user_id="")  # service-level access

    # For service-level reads without user_id filtering we need a permissive query
    # In prod, use service role which bypasses RLS
    if not run:
        raise ValueError(f"Run {run_id} not found")

    await RunsDB.update_status(run_id, "processing")
    await JobsDB.update_status(job_id, "running", current_step="ingest_input", progress=5)

    # Reconstruct source_inputs from DB
    try:
        raw = run.get("source_inputs", "{}")
        source_inputs: dict[str, Any] = (
            json.loads(raw) if isinstance(raw, str) and raw.startswith("{")
            else (raw if isinstance(raw, dict) else {})
        )
    except Exception:
        source_inputs = {}

    initial_state: WorkflowState = {
        "run_id": run_id,
        "user_id": str(run.get("user_id", "")),
        "source_inputs": source_inputs,
        "qa_attempt": 0,
        "audit_events": [],
    }

    graph = get_graph()
    config = {"configurable": {"thread_id": run_id}}

    node_progress = {
        "ingest_input": 5, "transcribe_audio": 10, "detect_missing_info": 15,
        "classify_idea": 18, "choose_pattern": 20,
        "create_problem_framing": 25, "generate_personas": 32,
        "generate_mvp_scope": 39, "generate_success_metrics": 46,
        "generate_user_stories": 53, "generate_backlog": 60,
        "generate_test_cases": 67, "generate_risks": 74,
        "generate_architecture": 81, "consistency_check": 86,
        "qa_evaluation": 90, "remediation_router": 93,
        "human_review_gate": 97,
    }

    final_state: WorkflowState = {}

    async for event in graph.astream(initial_state, config=config):
        node_name = list(event.keys())[0] if event else None
        if node_name:
            progress = node_progress.get(node_name, 50)
            await JobsDB.update_status(job_id, "running", current_step=node_name, progress=progress)
            log.debug("graph_node_complete", node=node_name, progress=progress)
            final_state.update(list(event.values())[0] if event else {})

    # Persist all generated artifacts to DB
    artifact_keys = [
        "problem_framing", "personas", "mvp_scope", "success_metrics",
        "user_stories", "backlog_items", "test_cases", "risks", "architecture",
    ]
    for key in artifact_keys:
        content = final_state.get(key)  # type: ignore[call-overload]
        if content:
            await ArtifactsDB.upsert(run_id, key, content)

    # Persist QA report
    qa = final_state.get("qa_report", {})  # type: ignore[call-overload]
    if qa:
        await QAReportsDB.create(
            run_id=run_id,
            overall_score=qa.get("overall_score", 0),
            max_score=qa.get("max_score", 100),
            pass_rate=qa.get("pass_rate", 0),
            critical_issues=qa.get("critical_issues", 0),
            warnings=qa.get("warnings", 0),
            export_ready=qa.get("export_ready", False),
            report_json=qa,
        )

    # Update run status
    missing = final_state.get("missing_info_flags", [])  # type: ignore[call-overload]
    classification = final_state.get("idea_classification")  # type: ignore[call-overload]
    pattern = final_state.get("selected_pattern")  # type: ignore[call-overload]

    await RunsDB.update_status(
        run_id, "awaiting_review",
        missing_info_flags=str(missing),
        idea_classification=classification,
        selected_pattern=pattern,
        graph_thread_id=run_id,
    )

    log.info("orchestration_complete", artifacts=len(artifact_keys))


async def _regenerate_artifact(
    run_id: str,
    artifact_type: str | None,
    job_id: str,
    log: Any,
) -> None:
    """Regenerate a single artifact using the current run state."""
    if not artifact_type:
        raise ValueError("artifact_type required for regeneration")

    await JobsDB.update_status(job_id, "running", current_step=f"regenerate_{artifact_type}", progress=10)

    # Load current artifacts from DB to use as context
    artifacts_rows = await ArtifactsDB.list_by_run(run_id)
    current_state: dict[str, Any] = {}
    for row in artifacts_rows:
        key = row["artifact_type"]
        content = row.get("content_json", {})
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

    # Load source inputs
    run = await RunsDB.get(run_id, user_id="")
    try:
        raw = run.get("source_inputs", "{}") if run else "{}"
        source_inputs = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        source_inputs = {}

    workflow_state: WorkflowState = {
        "run_id": run_id,
        "source_inputs": source_inputs,
        "extracted_brief": {**source_inputs},
        **{k: v for k, v in current_state.items()},  # type: ignore[misc]
    }

    updates = await node_fn(workflow_state)
    new_content = updates.get(artifact_type)
    if new_content:
        await ArtifactsDB.upsert(run_id, artifact_type, new_content)

    await JobsDB.update_status(job_id, "completed", progress=100)
    log.info("artifact_regenerated", artifact_type=artifact_type)


async def _run_qa(run_id: str, job_id: str, log: Any) -> None:
    """Run QA evaluation and persist report."""
    await JobsDB.update_status(job_id, "running", current_step="qa_evaluation", progress=20)

    artifacts_rows = await ArtifactsDB.list_by_run(run_id)
    artifacts: dict[str, Any] = {}
    for row in artifacts_rows:
        key = row["artifact_type"]
        content = row.get("content_json", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                content = {}
        artifacts[key] = content

    run = await RunsDB.get(run_id, user_id="")
    source_inputs: dict[str, Any] = {}
    if run:
        try:
            raw = run.get("source_inputs", "{}")
            source_inputs = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            pass

    qa_report = await run_qa_evaluation(artifacts=artifacts, source_inputs=source_inputs, run_id=run_id)

    await QAReportsDB.create(
        run_id=run_id,
        overall_score=qa_report["overall_score"],
        max_score=qa_report["max_score"],
        pass_rate=qa_report["pass_rate"],
        critical_issues=qa_report["critical_issues"],
        warnings=qa_report["warnings"],
        export_ready=qa_report["export_ready"],
        report_json=qa_report,
    )

    if not qa_report["export_ready"]:
        await RunsDB.update_status(run_id, "awaiting_review")
    else:
        await RunsDB.update_status(run_id, "awaiting_approval")

    log.info("qa_complete", export_ready=qa_report["export_ready"])


async def _generate_export(run_id: str, formats: list[str], job_id: str, log: Any) -> None:
    """Generate export files and upload to Supabase Storage."""
    from app.db.queries import ExportsDB

    await JobsDB.update_status(job_id, "running", current_step="generate_export", progress=20)

    artifacts_rows = await ArtifactsDB.list_by_run(run_id)
    artifacts: dict[str, Any] = {}
    for row in artifacts_rows:
        key = row["artifact_type"]
        content = row.get("content_json", {})
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

        # Upload to Supabase Storage
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
            # Fall back to data URI for dev
            import base64
            b64 = base64.b64encode(content_bytes).decode()
            file_url = f"data:{data.get('mime', 'text/plain')};base64,{b64[:200]}..."

        await ExportsDB.create(
            run_id=run_id,
            fmt=fmt,
            file_url=file_url,
            file_size_bytes=len(content_bytes),
        )

    await RunsDB.update_status(run_id, "exported")
    log.info("exports_generated", formats=list(pack.keys()))


def _ext(fmt: str) -> str:
    return {"markdown": "md", "json": "json", "html": "html",
            "jira_csv": "csv", "linear_csv": "csv"}.get(fmt, "txt")
