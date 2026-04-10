"""
Export pack generation service.
Builds Markdown, JSON, and HTML export documents from artifact dicts.
"""

import json
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def _artifacts_to_markdown(artifacts: dict[str, Any]) -> str:
    parts = ["# PM Artifact Pack\n", f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n"]

    pf = artifacts.get("problem_framing", {})
    if pf:
        parts.append("\n## Problem Framing\n")
        parts.append(f"**Problem Statement:** {pf.get('problem_statement', '')}\n\n")
        parts.append(f"**Opportunity:** {pf.get('opportunity', '')}\n\n")
        parts.append(f"**Hypothesis:** _{pf.get('hypothesis', '')}_\n\n")
        if pf.get("goals"):
            parts.append("**Goals:**\n" + "\n".join(f"- {g}" for g in pf["goals"]) + "\n")
        if pf.get("non_goals"):
            parts.append("**Non-Goals:**\n" + "\n".join(f"- {g}" for g in pf["non_goals"]) + "\n")
        if pf.get("assumptions"):
            parts.append("**Assumptions:**\n" + "\n".join(f"- {a}" for a in pf["assumptions"]) + "\n")

    personas = artifacts.get("personas", {}).get("personas", [])
    if personas:
        parts.append("\n## User Personas\n")
        for p in personas:
            parts.append(f"### {p.get('name')} — {p.get('role')}\n")
            parts.append(f"**Archetype:** {p.get('archetype', '')}\n\n")
            if p.get("goals"):
                parts.append("**Goals:**\n" + "\n".join(f"- {g}" for g in p["goals"]) + "\n")
            if p.get("pain_points"):
                parts.append("**Pain Points:**\n" + "\n".join(f"- {g}" for g in p["pain_points"]) + "\n")

    scope = artifacts.get("mvp_scope", {})
    if scope:
        parts.append("\n## MVP Scope\n")
        parts.append("### In Scope\n" + "\n".join(f"- {i}" for i in scope.get("in_scope", [])) + "\n")
        parts.append("### Out of Scope\n" + "\n".join(f"- {i}" for i in scope.get("out_of_scope", [])) + "\n")
        if scope.get("core_features"):
            parts.append("### Core Features\n")
            for f in scope["core_features"]:
                parts.append(f"**{f.get('id')} {f.get('name')}** ({f.get('priority')})\n")
                parts.append(f"{f.get('description', '')}\n\n")

    metrics = artifacts.get("success_metrics", {}).get("metrics", [])
    if metrics:
        parts.append("\n## Success Metrics\n\n")
        parts.append("| Metric | Target | Type |\n|---|---|---|\n")
        for m in metrics:
            parts.append(f"| {m.get('metric_name')} | {m.get('target')} | {m.get('signal_type')} |\n")

    stories = artifacts.get("user_stories", {}).get("stories", [])
    if stories:
        parts.append("\n## User Stories\n")
        for s in stories:
            parts.append(f"\n### {s.get('id')} [{s.get('priority')}]\n")
            parts.append(f"As a **{s.get('as_a')}**, I want **{s.get('i_want')}**, so that **{s.get('so_that')}**.\n\n")
            parts.append("**Acceptance Criteria:**\n")
            for ac in s.get("acceptance_criteria", []):
                parts.append(f"- [ ] {ac}\n")
            parts.append(f"\n_Effort: {s.get('estimated_effort')} | Epic: {s.get('epic')}_\n")

    test_cases = artifacts.get("test_cases", {}).get("test_cases", [])
    if test_cases:
        parts.append("\n## Test Cases\n")
        for tc in test_cases:
            parts.append(f"\n### {tc.get('id')} — {tc.get('scenario')}\n")
            parts.append(f"**Type:** {tc.get('test_type')} | **Priority:** {tc.get('priority')}\n\n")
            if tc.get("steps"):
                parts.append("**Steps:**\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(tc["steps"])) + "\n")
            parts.append(f"\n**Expected:** {tc.get('expected_result')}\n")

    risks = artifacts.get("risks", {}).get("risks", [])
    if risks:
        parts.append("\n## Risk Checklist\n\n")
        parts.append("| ID | Category | Impact | Likelihood | Mitigation |\n|---|---|---|---|---|\n")
        for r in risks:
            parts.append(f"| {r.get('id')} | {r.get('category')} | {r.get('impact')} | {r.get('likelihood')} | {r.get('mitigation', '')[:60]}... |\n")

    arch = artifacts.get("architecture", {})
    if arch:
        parts.append("\n## Architecture Recommendation\n")
        parts.append(f"**Recommended:** {arch.get('recommended_option')}\n\n")
        parts.append(f"{arch.get('rationale', '')}\n\n")
        for opt in arch.get("options", []):
            parts.append(f"### Option: {opt.get('name')}{' ✓ Recommended' if opt.get('recommended') else ''}\n")
            parts.append(f"{opt.get('description', '')}\n\n")
            if opt.get("pros"):
                parts.append("**Pros:**\n" + "\n".join(f"+ {p}" for p in opt["pros"]) + "\n")
            if opt.get("cons"):
                parts.append("**Cons:**\n" + "\n".join(f"- {c}" for c in opt["cons"]) + "\n")

    return "\n".join(parts)


def _artifacts_to_jira_csv(artifacts: dict[str, Any]) -> str:
    stories = artifacts.get("user_stories", {}).get("stories", [])
    lines = ["Summary,Description,Issue Type,Priority,Story Points,Epic Link"]
    for s in stories:
        summary = f"[{s.get('id')}] As a {s.get('as_a')}, I want {s.get('i_want')}"
        description = (
            f"So that: {s.get('so_that')}\\n\\n"
            f"Acceptance Criteria:\\n" +
            "\\n".join(f"- {ac}" for ac in s.get("acceptance_criteria", []))
        )
        priority = s.get("priority", "Medium")
        effort = s.get("estimated_effort", "").replace(" points", "").replace(" pt", "")
        epic = s.get("epic", "")
        lines.append(f'"{summary}","{description}","Story","{priority}","{effort}","{epic}"')
    return "\n".join(lines)


def _artifacts_to_html(artifacts: dict[str, Any], run_id: str) -> str:
    md_content = _artifacts_to_markdown(artifacts)
    # Minimal HTML wrapper — renders well for PDF printing
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PM Artifact Pack — {run_id}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #111; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: 8px; }}
  h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 2em; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td, th {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #f5f5f5; }}
  @media print {{ body {{ margin: 0; }} }}
</style>
</head>
<body>
<pre style="white-space: pre-wrap; font-family: inherit;">{md_content}</pre>
</body>
</html>"""


async def generate_export_pack(
    run_id: str,
    artifacts: dict[str, Any],
    formats: list[str] | None = None,
) -> dict[str, Any]:
    """
    Generate export content for requested formats.
    Returns a dict of format -> content string.
    In production, this would upload to Supabase Storage and return URLs.
    """
    if formats is None:
        formats = ["markdown", "json"]

    log = logger.bind(run_id=run_id)
    results: dict[str, Any] = {}

    for fmt in formats:
        try:
            if fmt == "markdown":
                content = _artifacts_to_markdown(artifacts)
                results["markdown"] = {"content": content, "mime": "text/markdown"}

            elif fmt == "json":
                content = json.dumps({
                    "run_id": run_id,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "artifacts": artifacts,
                }, indent=2)
                results["json"] = {"content": content, "mime": "application/json"}

            elif fmt == "html":
                content = _artifacts_to_html(artifacts, run_id)
                results["html"] = {"content": content, "mime": "text/html"}

            elif fmt in ("jira_csv", "linear_csv"):
                content = _artifacts_to_jira_csv(artifacts)
                results[fmt] = {"content": content, "mime": "text/csv"}

            log.info("export_generated", format=fmt, bytes=len(results.get(fmt, {}).get("content", "")))

        except Exception as exc:
            log.error("export_failed", format=fmt, error=str(exc))

    return results
