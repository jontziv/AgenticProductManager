"""
Unit tests for the QA evaluation harness.
Deterministic checks — no LLM calls, no DB.
"""

import pytest
import pytest_asyncio

from app.evaluators.harness import run_qa_evaluation
from app.evaluators.rubric import HARD_FAIL_IDS


@pytest.mark.asyncio
async def test_full_artifacts_pass(sample_artifacts):
    """Full artifact set with good data should produce no hard fails."""
    report = await run_qa_evaluation(
        artifacts=sample_artifacts,
        source_inputs={"target_users": "Product managers"},
    )
    assert report["critical_issues"] == 0
    assert report["pass_rate"] > 50
    assert report["export_ready"] is True


@pytest.mark.asyncio
async def test_missing_problem_framing_is_hard_fail(sample_artifacts):
    """Absent problem_framing should trigger C001 hard fail."""
    artifacts = {**sample_artifacts, "problem_framing": {}}
    report = await run_qa_evaluation(artifacts=artifacts, source_inputs={})
    assert report["critical_issues"] > 0
    assert report["export_ready"] is False


@pytest.mark.asyncio
async def test_missing_artifact_coverage(sample_artifacts):
    """Removing a required artifact triggers C001 hard fail."""
    artifacts = {k: v for k, v in sample_artifacts.items() if k != "user_stories"}
    report = await run_qa_evaluation(artifacts=artifacts, source_inputs={})
    c001 = next((c for c in report["checks"] if c["id"] == "C001"), None)
    assert c001 is not None
    assert c001["status"] == "failed"
    assert report["export_ready"] is False


@pytest.mark.asyncio
async def test_story_missing_acceptance_criteria(sample_artifacts):
    """High-priority stories without 3 acceptance criteria should fail C002."""
    artifacts = dict(sample_artifacts)
    artifacts["user_stories"] = {
        "stories": [{
            "id": "US-001", "persona_ref": "Sarah Chen",
            "as_a": "PM", "i_want": "see data", "so_that": "I decide",
            "acceptance_criteria": ["one criterion only"],  # < 3
            "priority": "High", "estimated_effort": "3",
            "epic": "Core", "linked_test_ids": [],
        }]
    }
    report = await run_qa_evaluation(artifacts=artifacts, source_inputs={})
    c002 = next((c for c in report["checks"] if c["id"] == "C002"), None)
    assert c002 is not None
    assert c002["status"] == "failed"


@pytest.mark.asyncio
async def test_architecture_missing_recommendation(sample_artifacts):
    """Architecture without recommended_option fails P004 (hard fail)."""
    artifacts = dict(sample_artifacts)
    artifacts["architecture"] = {"options": [], "recommended_option": "", "rationale": ""}
    report = await run_qa_evaluation(artifacts=artifacts, source_inputs={})
    p004 = next((c for c in report["checks"] if c["id"] == "P004"), None)
    assert p004 is not None
    assert p004["status"] == "failed"
    assert report["export_ready"] is False


@pytest.mark.asyncio
async def test_remediation_tasks_populated_on_failure(sample_artifacts):
    """Failed checks should produce remediation tasks."""
    artifacts = {k: v for k, v in sample_artifacts.items() if k != "architecture"}
    report = await run_qa_evaluation(artifacts=artifacts, source_inputs={})
    assert len(report["remediation_tasks"]) > 0
    # Each task should have required fields
    for task in report["remediation_tasks"]:
        assert "id" in task
        assert "description" in task
        assert "affected_artifact" in task
        assert task["priority"] in ("high", "medium", "low")


@pytest.mark.asyncio
async def test_overall_score_within_bounds(sample_artifacts):
    """Overall score should be >= 0 and <= max_score."""
    report = await run_qa_evaluation(artifacts=sample_artifacts, source_inputs={})
    assert 0 <= report["overall_score"] <= report["max_score"]
    assert 0 <= report["pass_rate"] <= 100


def test_hard_fail_ids_defined():
    """Hard fail check IDs should be a non-empty set."""
    assert len(HARD_FAIL_IDS) > 0
    assert "C001" in HARD_FAIL_IDS
    assert "C002" in HARD_FAIL_IDS
