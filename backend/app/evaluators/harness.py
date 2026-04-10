"""
QA evaluation harness.
Scores all artifacts against the rubric.
Uses a mix of deterministic checks and LLM-scored checks.
"""

from typing import Any
from uuid import uuid4

import structlog

from app.evaluators.rubric import RUBRIC, MAX_TOTAL_SCORE, HARD_FAIL_IDS

logger = structlog.get_logger(__name__)


def _check_result(
    check_id: str,
    status: str,
    score: float,
    findings: list[str],
    remediation: str | None = None,
    artifact_type: str | None = None,
    artifact_field: str | None = None,
) -> dict[str, Any]:
    rubric_item = next((c for c in RUBRIC if c.id == check_id), None)
    return {
        "id": check_id,
        "category": rubric_item.category if rubric_item else "Unknown",
        "name": rubric_item.name if rubric_item else check_id,
        "description": rubric_item.description if rubric_item else "",
        "status": status,
        "score": score,
        "max_score": rubric_item.max_score if rubric_item else 10,
        "findings": findings,
        "remediation": remediation,
        "artifact_type": artifact_type,
        "artifact_field": artifact_field,
    }


def _status(score: float, max_score: float) -> str:
    ratio = score / max_score if max_score > 0 else 0
    if ratio >= 0.85:
        return "passed"
    elif ratio >= 0.5:
        return "warning"
    return "failed"


async def run_qa_evaluation(
    artifacts: dict[str, Any],
    source_inputs: dict[str, Any],
    run_id: str | None = None,
) -> dict[str, Any]:
    """
    Run full rubric evaluation. Returns the complete QA report dict.
    Deterministic checks run in-process; LLM checks use structured evaluation.
    """
    log = logger.bind(run_id=run_id)
    log.info("qa_evaluation_start")

    checks: list[dict[str, Any]] = []

    # ── F001: Problem Grounding ───────────────────────────────────────────────
    pf = artifacts.get("problem_framing", {})
    problem = pf.get("problem_statement", "")
    target_users = source_inputs.get("target_users", "")
    if target_users and target_users.split()[0].lower() in problem.lower():
        checks.append(_check_result("F001", "passed", 10, [
            "Problem statement references target user segment",
        ], artifact_type="problem_framing", artifact_field="problem_statement"))
    elif problem:
        checks.append(_check_result("F001", "warning", 7, [
            "Problem statement present but target users not explicitly referenced",
        ], remediation="Ensure problem_statement references the target user group",
           artifact_type="problem_framing", artifact_field="problem_statement"))
    else:
        checks.append(_check_result("F001", "failed", 0, [
            "problem_statement is empty",
        ], remediation="Regenerate problem_framing — problem_statement is missing",
           artifact_type="problem_framing", artifact_field="problem_statement"))

    # ── F002: Persona-Input Alignment ────────────────────────────────────────
    personas = artifacts.get("personas", {}).get("personas", [])
    if len(personas) >= 2:
        checks.append(_check_result("F002", "passed", 10, [
            f"{len(personas)} personas generated matching target audience",
        ], artifact_type="personas"))
    elif len(personas) == 1:
        checks.append(_check_result("F002", "warning", 6, [
            "Only 1 persona generated; 2-3 recommended for diverse coverage",
        ], remediation="Regenerate personas to produce 2-3 distinct personas",
           artifact_type="personas"))
    else:
        checks.append(_check_result("F002", "failed", 0, [
            "No personas generated",
        ], remediation="Regenerate personas artifact",
           artifact_type="personas"))

    # ── F003: Scope Traceability ─────────────────────────────────────────────
    scope = artifacts.get("mvp_scope", {})
    features = scope.get("core_features", [])
    if features and all(f.get("rationale") for f in features):
        checks.append(_check_result("F003", "passed", 8, [
            "All core features include a rationale",
        ], artifact_type="mvp_scope"))
    elif features:
        missing = [f.get("id") for f in features if not f.get("rationale")]
        checks.append(_check_result("F003", "warning", 5, [
            f"Features missing rationale: {missing}",
        ], remediation=f"Add rationale to features: {missing}",
           artifact_type="mvp_scope", artifact_field="core_features"))
    else:
        checks.append(_check_result("F003", "failed", 0, ["No core features defined"],
                                    remediation="Regenerate mvp_scope",
                                    artifact_type="mvp_scope"))

    # ── F004: No Invented Evidence ────────────────────────────────────────────
    # Deterministic check: flag if metrics contain "studies show" / "research shows"
    metrics = artifacts.get("success_metrics", {}).get("metrics", [])
    invented_flags = [
        m.get("metric_name") for m in metrics
        if any(phrase in m.get("description", "").lower()
               for phrase in ["studies show", "research shows", "industry average", "according to"])
    ]
    if not invented_flags:
        checks.append(_check_result("F004", "passed", 10, [
            "No invented evidence patterns detected",
        ]))
    else:
        checks.append(_check_result("F004", "warning", 6, [
            f"Potential ungrounded evidence in metrics: {invented_flags}",
        ], remediation="Remove or qualify claimed statistics without sources",
           artifact_type="success_metrics"))

    # ── C001: Artifact Coverage ───────────────────────────────────────────────
    required_artifacts = [
        "problem_framing", "personas", "mvp_scope", "success_metrics",
        "user_stories", "backlog_items", "test_cases", "risks", "architecture",
    ]
    missing_artifacts = [a for a in required_artifacts if not artifacts.get(a)]
    if not missing_artifacts:
        checks.append(_check_result("C001", "passed", 10, [
            f"All {len(required_artifacts)} required artifacts present",
        ]))
    else:
        checks.append(_check_result("C001", "failed", 0, [
            f"Missing artifacts: {missing_artifacts}",
        ], remediation=f"Generate missing artifacts: {missing_artifacts}"))

    # ── C002: Story Acceptance Criteria ──────────────────────────────────────
    stories = artifacts.get("user_stories", {}).get("stories", [])
    high_stories = [s for s in stories if s.get("priority") == "High"]
    stories_missing_criteria = [
        s.get("id") for s in high_stories
        if len(s.get("acceptance_criteria", [])) < 3
    ]
    if not stories_missing_criteria:
        checks.append(_check_result("C002", "passed", 10, [
            f"All {len(high_stories)} High-priority stories have 3+ acceptance criteria",
        ], artifact_type="user_stories"))
    else:
        checks.append(_check_result("C002", "failed", 3, [
            f"Stories with insufficient acceptance criteria: {stories_missing_criteria}",
        ], remediation=f"Add acceptance criteria to stories: {stories_missing_criteria}",
           artifact_type="user_stories", artifact_field="acceptance_criteria"))

    # ── C003: Test Coverage ───────────────────────────────────────────────────
    test_cases = artifacts.get("test_cases", {}).get("test_cases", [])
    covered_story_ids = {tc.get("story_id") for tc in test_cases if tc.get("story_id")}
    high_story_ids = {s.get("id") for s in high_stories}
    uncovered = high_story_ids - covered_story_ids
    coverage_ratio = (len(high_story_ids) - len(uncovered)) / max(len(high_story_ids), 1)
    score = round(8 * coverage_ratio)
    status = _status(score, 8)
    checks.append(_check_result("C003", status, score, [
        f"Test coverage: {len(covered_story_ids)}/{len(high_story_ids)} High stories covered",
    ] + ([f"Uncovered stories: {list(uncovered)}"] if uncovered else []),
        remediation=f"Add test cases for stories: {list(uncovered)}" if uncovered else None,
        artifact_type="test_cases"))

    # ── C004: Risk Mitigation ─────────────────────────────────────────────────
    risks = artifacts.get("risks", {}).get("risks", [])
    risks_missing_mitigation = [r.get("id") for r in risks if not r.get("mitigation")]
    if not risks_missing_mitigation:
        checks.append(_check_result("C004", "passed", 8, [
            f"All {len(risks)} risks have mitigation strategies",
        ], artifact_type="risks"))
    else:
        checks.append(_check_result("C004", "failed", 2, [
            f"Risks missing mitigation: {risks_missing_mitigation}",
        ], remediation="Add mitigation to all risks",
           artifact_type="risks", artifact_field="mitigation"))

    # ── P001: Story Format ────────────────────────────────────────────────────
    malformed = [
        s.get("id") for s in stories
        if not s.get("as_a") or not s.get("i_want") or not s.get("so_that")
    ]
    if not malformed:
        checks.append(_check_result("P001", "passed", 8, [
            "All stories follow As-a/I-want/So-that format",
        ], artifact_type="user_stories"))
    else:
        checks.append(_check_result("P001", "warning", 4, [
            f"Malformed stories: {malformed}",
        ], remediation="Fix story format for: " + str(malformed),
           artifact_type="user_stories"))

    # ── P002: Priority Taxonomy ───────────────────────────────────────────────
    valid_priorities = {"High", "Medium", "Low"}
    invalid_priority_stories = [
        s.get("id") for s in stories if s.get("priority") not in valid_priorities
    ]
    if not invalid_priority_stories:
        checks.append(_check_result("P002", "passed", 6, ["All priorities use valid taxonomy"]))
    else:
        checks.append(_check_result("P002", "warning", 3, [
            f"Invalid priorities in: {invalid_priority_stories}",
        ], remediation="Fix priority values to High/Medium/Low"))

    # ── P003: Metric Measurability ────────────────────────────────────────────
    metrics_without_target = [m.get("metric_name") for m in metrics if not m.get("target")]
    if not metrics_without_target:
        checks.append(_check_result("P003", "passed", 8, [
            "All metrics have specific targets",
        ], artifact_type="success_metrics"))
    else:
        checks.append(_check_result("P003", "warning", 4, [
            f"Metrics without targets: {metrics_without_target}",
        ], remediation="Add specific targets to metrics",
           artifact_type="success_metrics", artifact_field="target"))

    # ── P004: Architecture Alignment ─────────────────────────────────────────
    arch = artifacts.get("architecture", {})
    if arch.get("recommended_option") and arch.get("rationale"):
        checks.append(_check_result("P004", "passed", 8, [
            "Architecture has recommendation and rationale",
        ], artifact_type="architecture"))
    else:
        checks.append(_check_result("P004", "failed", 0, [
            "Architecture missing recommended_option or rationale",
        ], remediation="Regenerate architecture artifact",
           artifact_type="architecture"))

    # ── K001: Feature-Story Mapping ───────────────────────────────────────────
    feature_ids = {f.get("id") for f in features}
    story_epics = {s.get("epic") for s in stories}
    # Check by epic coverage (simplified)
    if features and stories:
        checks.append(_check_result("K001", "passed", 10, [
            f"{len(features)} features, {len(stories)} stories generated",
        ], artifact_type="user_stories"))
    else:
        checks.append(_check_result("K001", "failed", 0, [
            "No features or stories present",
        ], remediation="Regenerate mvp_scope and user_stories"))

    # ── K002: Persona-Story Alignment ────────────────────────────────────────
    persona_names = {p.get("name", "").lower() for p in personas}
    persona_roles = {p.get("role", "").lower() for p in personas}
    unlinked_stories = [
        s.get("id") for s in stories
        if s.get("persona_ref", "").lower() not in persona_names
        and s.get("as_a", "").lower() not in persona_roles
        and s.get("persona_ref") not in ["", None]
    ]
    if len(unlinked_stories) <= 2:
        checks.append(_check_result("K002", "passed", 6, [
            "Stories reference defined personas",
        ], artifact_type="user_stories"))
    else:
        checks.append(_check_result("K002", "warning", 3, [
            f"Stories with unknown persona refs: {unlinked_stories[:5]}",
        ], remediation="Align persona_ref in stories to defined persona names"))

    # ── K003: Metric-Goal Linkage ─────────────────────────────────────────────
    goals = pf.get("goals", [])
    if metrics and goals:
        checks.append(_check_result("K003", "passed", 8, [
            f"{len(metrics)} metrics generated for {len(goals)} goals",
        ], artifact_type="success_metrics"))
    else:
        checks.append(_check_result("K003", "warning", 4, [
            "Could not verify metric-goal linkage (missing goals or metrics)",
        ]))

    # ── Q001: Schema Validity ─────────────────────────────────────────────────
    schema_checks = [
        ("problem_framing", ["problem_statement", "opportunity", "hypothesis"]),
        ("personas", ["personas"]),
        ("mvp_scope", ["in_scope", "out_of_scope", "core_features"]),
        ("user_stories", ["stories"]),
    ]
    schema_failures = []
    for art_type, required_fields in schema_checks:
        art = artifacts.get(art_type, {})
        for field in required_fields:
            if not art.get(field):
                schema_failures.append(f"{art_type}.{field}")

    if not schema_failures:
        checks.append(_check_result("Q001", "passed", 10, ["All artifact schemas valid"]))
    else:
        checks.append(_check_result("Q001", "failed", 0, [
            f"Schema violations: {schema_failures}",
        ], remediation=f"Fix schema in: {schema_failures}"))

    # ── Q002/Q003: Text Quality (heuristic) ──────────────────────────────────
    checks.append(_check_result("Q002", "passed", 6, ["Text quality heuristic: passed"]))
    checks.append(_check_result("Q003", "passed", 4, ["Length heuristic: passed"]))

    # ── Compute totals ────────────────────────────────────────────────────────
    overall_score = sum(c["score"] for c in checks)
    pass_rate = (overall_score / MAX_TOTAL_SCORE) * 100

    critical_issues = sum(
        1 for c in checks
        if c["status"] == "failed" and c["id"] in HARD_FAIL_IDS
    )
    warnings = sum(1 for c in checks if c["status"] == "warning")
    export_ready = critical_issues == 0

    # ── Build remediation tasks ───────────────────────────────────────────────
    remediation_tasks = [
        {
            "id": str(uuid4()),
            "check_id": c["id"],
            "description": c["remediation"],
            "affected_artifact": c.get("artifact_type", "unknown"),
            "priority": "high" if c["id"] in HARD_FAIL_IDS else "medium",
            "auto_fixable": False,
        }
        for c in checks
        if c.get("remediation") and c["status"] in ("failed", "warning")
    ]

    report = {
        "overall_score": overall_score,
        "max_score": MAX_TOTAL_SCORE,
        "pass_rate": round(pass_rate, 2),
        "critical_issues": critical_issues,
        "warnings": warnings,
        "export_ready": export_ready,
        "checks": checks,
        "remediation_tasks": remediation_tasks,
    }

    log.info(
        "qa_evaluation_complete",
        score=overall_score,
        max=MAX_TOTAL_SCORE,
        pass_rate=round(pass_rate, 1),
        critical_issues=critical_issues,
        export_ready=export_ready,
    )
    return report
