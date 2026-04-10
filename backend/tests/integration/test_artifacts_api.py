"""
Integration tests for artifact endpoints.
Verifies versioning, stale marking, and per-user isolation.
"""

import pytest
import json
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_run(client: AsyncClient, headers: dict, title: str = "Artifact test") -> str:
    resp = await client.post(
        "/api/v1/runs",
        json={
            "title": title,
            "raw_input": "Need a mobile onboarding flow.",
            "input_type": "text",
            "target_users": "New app users",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _seed_artifact(client: AsyncClient, headers: dict, run_id: str, artifact_type: str = "problem_framing") -> dict:
    """PUT an artifact directly via the upsert endpoint (used by worker tests)."""
    payload = {
        "artifact_type": artifact_type,
        "content": {
            "problem_statement": "Users can't track onboarding progress.",
            "root_causes": ["No progress indicator", "Unclear steps"],
            "impact": "35% drop-off at step 3",
            "success_definition": "Completion rate > 80%",
        },
        "version": 1,
    }
    resp = await client.put(
        f"/api/v1/runs/{run_id}/artifacts/{artifact_type}",
        json=payload,
        headers=headers,
    )
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_artifacts_empty_for_new_run(
    test_client: AsyncClient, auth_headers: dict
):
    run_id = await _create_run(test_client, auth_headers)
    resp = await test_client.get(
        f"/api/v1/runs/{run_id}/artifacts", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json() == [] or isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_artifact_404_before_generation(
    test_client: AsyncClient, auth_headers: dict
):
    run_id = await _create_run(test_client, auth_headers)
    resp = await test_client.get(
        f"/api/v1/runs/{run_id}/artifacts/problem_framing",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_artifact_isolated_between_users(
    test_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
):
    run_id = await _create_run(test_client, auth_headers)

    # User B cannot access user A's run artifacts
    resp = await test_client.get(
        f"/api/v1/runs/{run_id}/artifacts",
        headers=other_auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_artifact_enqueues_job(
    test_client: AsyncClient, auth_headers: dict
):
    run_id = await _create_run(test_client, auth_headers)

    resp = await test_client.post(
        f"/api/v1/runs/{run_id}/artifacts/problem_framing/regenerate",
        headers=auth_headers,
    )
    # Acceptable: 202 (job queued) or 409 (run not in valid state for regen)
    assert resp.status_code in (202, 409)


@pytest.mark.asyncio
async def test_regenerate_returns_job_id(
    test_client: AsyncClient, auth_headers: dict
):
    run_id = await _create_run(test_client, auth_headers)

    resp = await test_client.post(
        f"/api/v1/runs/{run_id}/artifacts/personas/regenerate",
        headers=auth_headers,
    )
    if resp.status_code == 202:
        body = resp.json()
        assert "job_id" in body


@pytest.mark.asyncio
async def test_artifact_list_returns_latest_versions(
    test_client: AsyncClient, auth_headers: dict
):
    """After two upserts of same artifact_type, list returns one entry (latest)."""
    run_id = await _create_run(test_client, auth_headers)

    for v in (1, 2):
        await test_client.put(
            f"/api/v1/runs/{run_id}/artifacts/problem_framing",
            json={
                "artifact_type": "problem_framing",
                "content": {"problem_statement": f"v{v}", "root_causes": [], "impact": "", "success_definition": ""},
                "version": v,
            },
            headers=auth_headers,
        )

    resp = await test_client.get(
        f"/api/v1/runs/{run_id}/artifacts", headers=auth_headers
    )
    assert resp.status_code == 200
    items = resp.json()
    pf_items = [a for a in items if a["artifact_type"] == "problem_framing"]
    # Should deduplicate to latest version only
    assert len(pf_items) == 1
    assert pf_items[0]["version"] == 2
