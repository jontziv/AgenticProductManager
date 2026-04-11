"""
Job processor: handles a single claimed job end-to-end.
One processor per job type — clean separation.
"""

import json
from datetime import datetime, timezone
from typing import Any

import structlog

from groq import RateLimitError

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

    except RateLimitError as exc:
        # Groq daily token limit hit — retrying re-runs all LLM calls and burns
        # the remaining quota. Fail immediately without re-queuing.
        err_msg = "Groq rate limit exceeded. Wait until the daily quota resets before resubmitting."
        log.error("job_rate_limited", error=str(exc))
        await JobsDB.update_status(job_id, "failed", error_message=err_msg)
        await RunsDB.update_status(run_id, "failed")

    except Exception as exc:
        log.exception("job_failed", error=str(exc))

        if job_type == "orchestrate_run":
            # Never retry orchestration jobs. Every retry re-runs the full
            # LangGraph workflow from scratch (MemorySaver checkpoint is lost
            # when initial_state is re-submitted), burning tokens on nodes that
            # already succeeded. Fail immediately and let the user resubmit.
            await JobsDB.update_status(job_id, "failed", error_message=str(exc))
            await RunsDB.update_status(run_id, "failed")
            log.error("orchestration_terminal_failure", error=str(exc))
        else:
            retry_count = await JobsDB.increment_retry(job_id, str(exc))
            if retry_count >= settings.worker_max_retries:
                await JobsDB.update_status(job_id, "failed", error_message=str(exc))
                await RunsDB.update_status(run_id, "failed")
                log.error("job_terminal_failure", retries=retry_count)
            else:
                log.warning("job_will_retry", retry=retry_count)


def _node_summary(node_name: str, updates: dict[str, Any]) -> str:
    """Return a one-line human-readable summary of what a graph node produced."""
    match node_name:
        case "ingest_input":
            return "Input normalized and brief extracted"
        case "detect_missing_info":
            flags = updates.get("missing_info_flags") or []
            can = updates.get("can_proceed", True)
            if not can and flags:
                return f"Gaps detected: {', '.join(str(f) for f in flags[:3])}"
            return "No critical gaps — proceeding with full analysis"
        case "classify_idea":
            idea_type = updates.get("idea_classification") or "?"
            return f"Idea classified as '{idea_type}'"
        case "choose_pattern":
            pattern = updates.get("selected_pattern") or "?"
            return f"Product pattern selected: {pattern}"
        case "create_problem_framing":
            pf = updates.get("problem_framing") or {}
            stmt = (pf.get("problem_statement") or "")[:120]
            return f"Problem framed: {stmt}" if stmt else "Problem framing complete"
        case "generate_personas":
            count = len((updates.get("personas") or {}).get("personas", []))
            return f"{count} persona{'s' if count != 1 else ''} generated"
        case "generate_mvp_scope":
            count = len((updates.get("mvp_scope") or {}).get("in_scope", []))
            return f"MVP scope defined: {count} in-scope item{'s' if count != 1 else ''}"
        case "generate_success_metrics":
            m = updates.get("success_metrics") or {}
            count = len(m.get("leading", [])) + len(m.get("lagging", []))
            return f"Success metrics defined: {count} metric{'s' if count != 1 else ''}"
        case "generate_user_stories":
            count = len((updates.get("user_stories") or {}).get("stories", []))
            return f"{count} user stor{'ies' if count != 1 else 'y'} created"
        case "generate_backlog":
            count = len((updates.get("backlog_items") or {}).get("items", []))
            return f"{count} backlog item{'s' if count != 1 else ''} prioritized"
        case "generate_test_cases":
            count = len((updates.get("test_cases") or {}).get("cases", []))
            return f"{count} test case{'s' if count != 1 else ''} generated"
        case "generate_risks":
            count = len((updates.get("risks") or {}).get("risks", []))
            return f"{count} risk{'s' if count != 1 else ''} identified"
        case "generate_architecture":
            opts = updates.get("architecture") or {}
            count = len(opts.get("options", []))
            return f"{count} architecture option{'s' if count != 1 else ''} evaluated"
        case "consistency_check":
            issues = len(updates.get("consistency_issues") or [])
            return f"Consistency check complete — {issues} issue{'s' if issues != 1 else ''} found"
        case "qa_evaluation":
            qa = updates.get("qa_report") or {}
            rate = qa.get("pass_rate", 0)
            return f"QA complete — {rate:.0f}% pass rate"
        case "human_review_gate":
            return "Awaiting human review"
        case "approval_versioning":
            return "Approval recorded"
        case "build_export_pack":
            return "Export pack assembled"
        case _:
            return f"{node_name.replace('_', ' ').title()} completed"


async def _orchestrate_run(run_id: str, user_id: str, job_id: str, log: Any) -> None:
    """Run the full LangGraph workflow for a new intake run.

    Checkpoint-aware: if MemorySaver already holds a checkpoint for this run_id
    (i.e. the job was retried within the same worker process after a mid-run
    failure), we pass None as input so LangGraph resumes from the last completed
    node instead of restarting from ingest_input with a fresh initial_state.
    """
    run = await RunsDB.get_by_id(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    graph = get_graph()
    config = {"configurable": {"thread_id": run_id}}

    # Decide whether to start fresh or resume from an existing checkpoint.
    # Passing initial_state to astream() when a checkpoint already exists causes
    # LangGraph to overwrite the saved state (including audit_events=[]) and
    # re-execute from ingest_input — exactly the restart loop we are fixing.
    existing = await graph.aget_state(config)
    if existing and existing.next:
        # Resume: checkpoint is mid-workflow; do not reset state.
        log.info("orchestration_resuming", next_nodes=list(existing.next))
        stream_input: WorkflowState | None = None
    else:
        # Fresh start: build full input from DB record.
        stream_input = {
            "run_id": run_id,
            "user_id": user_id,
            "source_inputs": {
                "business_idea": run.get("raw_input") or "",
                "target_users": run.get("target_users") or "",
                "business_context": run.get("business_context") or "",
                "raw_requirements": run.get("raw_requirements") or "",
                "constraints": run.get("constraints") or "",
                "input_type": run.get("input_type") or "text",
            },
            "qa_attempt": 0,
            "audit_events": [],
        }

    await RunsDB.update_status(run_id, "processing")

    final_state: WorkflowState = {}
    async for event in graph.astream(stream_input, config=config):
        node_name = list(event.keys())[0] if event else None
        if node_name:
            node_updates = list(event.values())[0] if event else {}
            log.debug("graph_node_complete", node=node_name)
            final_state.update(node_updates)
            summary = _node_summary(node_name, node_updates)
            await RunsDB.append_log(run_id, {
                "node": node_name,
                "summary": summary,
                "ts": datetime.now(timezone.utc).isoformat(),
            })

    # On resume, final_state only contains updates from nodes that ran in this
    # execution. Fill gaps from the MemorySaver checkpoint (which holds the full
    # accumulated state across all executions for this thread_id).
    checkpoint = await graph.aget_state(config)
    if checkpoint and checkpoint.values:
        checkpoint_values: dict[str, Any] = dict(checkpoint.values)
        for k, v in checkpoint_values.items():
            if k not in final_state or not final_state[k]:  # type: ignore[operator]
                final_state[k] = v  # type: ignore[assignment]

    # missing_info_flags are advisory assumptions — the graph always proceeds now
    missing_flags: list[str] = final_state.get("missing_info_flags") or []  # type: ignore[call-overload]

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

    # Update run status — surface any advisory flags as assumptions on the run record
    idea_type = final_state.get("idea_classification")  # type: ignore[call-overload]
    extra: dict[str, Any] = {"langgraph_thread_id": run_id}
    if idea_type:
        extra["idea_type"] = idea_type
    if missing_flags:
        extra["missing_info"] = json.dumps(missing_flags)
    await RunsDB.update_status(run_id, "needs_review", **extra)

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
