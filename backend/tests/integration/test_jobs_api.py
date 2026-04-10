"""
Integration tests for job and QA endpoints.
"""

import pytest
from httpx import AsyncClient


async def _make_run(client: AsyncClient, headers: dict) -> str:
    r = await client.post(
        "/api/v1/runs",
        json={
            "title": "Job test run",
            "raw_input": "Automate procurement approvals.",
            "input_type": "text",
            "target_users": "Finance team",
        },
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Job listing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_jobs_for_run(test_client: AsyncClient, auth_headers: dict):
    run_id = await _make_run(test_client, auth_headers)
    resp = await test_client.get(f"/api/v1/runs/{run_id}/jobs", headers=auth_headers)
    assert resp.status_code == 200
    jobs = resp.json()
    assert isinstance(jobs, list)


@pytest.mark.asyncio
async def test_job_has_required_fields(test_client: AsyncClient, auth_headers: dict):
    run_id = await _make_run(test_client, auth_headers)
    resp = await test_client.get(f"/api/v1/runs/{run_id}/jobs", headers=auth_headers)
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) >= 1
    job = jobs[0]
    for field in ("id", "run_id", "job_type", "status", "created_at"):
        assert field in job, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_jobs_isolated_between_users(
    test_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
):
    run_id = await _make_run(test_client, auth_headers)
    resp = await test_client.get(
        f"/api/v1/runs/{run_id}/jobs", headers=other_auth_headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# QA report
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_qa_report_404_before_evaluation(
    test_client: AsyncClient, auth_headers: dict
):
    run_id = await _make_run(test_client, auth_headers)
    resp = await test_client.get(f"/api/v1/runs/{run_id}/qa", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_qa_report_structure_when_present(
    test_client: AsyncClient, auth_headers: dict, sample_artifacts: dict
):
    """
    Seed a completed QA report directly (bypassing the worker) and verify
    the response shape.
    """
    run_id = await _make_run(test_client, auth_headers)

    # Seed a QA report via internal endpoint (worker would normally do this)
    seed_resp = await test_client.put(
        f"/api/v1/runs/{run_id}/qa",
        json={
            "overall_score": 72,
            "max_score": 100,
            "pass_rate": 72.0,
            "critical_issues": 0,
            "export_ready": True,
            "checks": [],
            "remediation_tasks": [],
        },
        headers=auth_headers,
    )
    if seed_resp.status_code not in (200, 201, 204):
        pytest.skip("QA seed endpoint not available; skipping shape assertion")

    resp = await test_client.get(f"/api/v1/runs/{run_id}/qa", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    for field in ("overall_score", "max_score", "pass_rate", "critical_issues", "export_ready", "checks"):
        assert field in body, f"Missing QA field: {field}"
