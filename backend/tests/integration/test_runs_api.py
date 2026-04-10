"""
Integration tests for /api/v1/runs endpoints.
Requires: TEST_DATABASE_URL env var pointing at a real Postgres test DB.
Each test runs in a transaction that is rolled back on teardown.
"""

import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.pool import get_pool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_payload(title: str = "Test idea") -> dict:
    return {
        "title": title,
        "raw_input": "We need a dashboard so PMs can track sprint velocity.",
        "input_type": "text",
        "target_users": "Product managers",
        "business_context": "Internal tooling initiative",
        "constraints": "Must work on mobile",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_run_returns_201(test_client: AsyncClient, auth_headers: dict):
    resp = await test_client.post(
        "/api/v1/runs",
        json=_run_payload(),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_create_run_enqueues_job(test_client: AsyncClient, auth_headers: dict):
    resp = await test_client.post(
        "/api/v1/runs",
        json=_run_payload("Enqueue check"),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    run_id = resp.json()["id"]

    jobs_resp = await test_client.get(
        f"/api/v1/runs/{run_id}/jobs",
        headers=auth_headers,
    )
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert len(jobs) >= 1
    assert jobs[0]["job_type"] == "orchestrate_run"
    assert jobs[0]["status"] in ("queued", "running")


@pytest.mark.asyncio
async def test_list_runs_returns_only_own(
    test_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
):
    """Runs created by user A must not appear in user B's list."""
    await test_client.post("/api/v1/runs", json=_run_payload("Mine"), headers=auth_headers)

    resp_b = await test_client.get("/api/v1/runs", headers=other_auth_headers)
    assert resp_b.status_code == 200
    ids = [r["id"] for r in resp_b.json()["items"]]

    resp_a = await test_client.get("/api/v1/runs", headers=auth_headers)
    own_ids = [r["id"] for r in resp_a.json()["items"]]

    for oid in own_ids:
        assert oid not in ids


@pytest.mark.asyncio
async def test_get_run_404_for_other_user(
    test_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
):
    create = await test_client.post(
        "/api/v1/runs", json=_run_payload(), headers=auth_headers
    )
    run_id = create.json()["id"]

    resp = await test_client.get(f"/api/v1/runs/{run_id}", headers=other_auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_run_returns_full_record(test_client: AsyncClient, auth_headers: dict):
    create = await test_client.post(
        "/api/v1/runs", json=_run_payload("Full record"), headers=auth_headers
    )
    run_id = create.json()["id"]

    resp = await test_client.get(f"/api/v1/runs/{run_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == run_id
    assert "title" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/runs")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_cancel_run_sets_status(test_client: AsyncClient, auth_headers: dict):
    create = await test_client.post(
        "/api/v1/runs", json=_run_payload("To cancel"), headers=auth_headers
    )
    run_id = create.json()["id"]

    cancel = await test_client.post(
        f"/api/v1/runs/{run_id}/cancel", headers=auth_headers
    )
    assert cancel.status_code in (200, 204)

    get = await test_client.get(f"/api/v1/runs/{run_id}", headers=auth_headers)
    assert get.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_delete_run_removes_record(test_client: AsyncClient, auth_headers: dict):
    create = await test_client.post(
        "/api/v1/runs", json=_run_payload("To delete"), headers=auth_headers
    )
    run_id = create.json()["id"]

    delete = await test_client.delete(f"/api/v1/runs/{run_id}", headers=auth_headers)
    assert delete.status_code in (200, 204)

    get = await test_client.get(f"/api/v1/runs/{run_id}", headers=auth_headers)
    assert get.status_code == 404


@pytest.mark.asyncio
async def test_approval_requires_qa_pass(test_client: AsyncClient, auth_headers: dict):
    """Submitting approval on a freshly-queued run should return 409 (not qa_passed)."""
    create = await test_client.post(
        "/api/v1/runs", json=_run_payload("Approval check"), headers=auth_headers
    )
    run_id = create.json()["id"]

    resp = await test_client.post(
        f"/api/v1/runs/{run_id}/approval",
        json={"approved": True, "comment": "LGTM"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_run_invalid_payload_returns_422(
    test_client: AsyncClient, auth_headers: dict
):
    resp = await test_client.post(
        "/api/v1/runs",
        json={"title": ""},   # missing required raw_input
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_runs_pagination(test_client: AsyncClient, auth_headers: dict):
    # Create 3 runs
    for i in range(3):
        await test_client.post(
            "/api/v1/runs", json=_run_payload(f"Paginate {i}"), headers=auth_headers
        )

    page1 = await test_client.get(
        "/api/v1/runs?limit=2&offset=0", headers=auth_headers
    )
    assert page1.status_code == 200
    body = page1.json()
    assert len(body["items"]) <= 2
    assert "total" in body
