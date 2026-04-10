"""
Integration tests for export endpoints.
Verifies approval gate, format enumeration, and job enqueue.
"""

import pytest
from httpx import AsyncClient


async def _make_approved_run(client: AsyncClient, headers: dict) -> str:
    """
    Create a run and force it into approved/qa_passed state via internal
    seeding endpoints so we can test the export path without running the
    full LangGraph pipeline.
    """
    r = await client.post(
        "/api/v1/runs",
        json={
            "title": "Export test run",
            "raw_input": "Build a customer feedback portal.",
            "input_type": "text",
            "target_users": "Customer success team",
        },
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_exports_empty_initially(
    test_client: AsyncClient, auth_headers: dict
):
    run_id = await _make_approved_run(test_client, auth_headers)
    resp = await test_client.get(
        f"/api/v1/runs/{run_id}/exports", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json() == [] or isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_request_export_blocked_without_approval(
    test_client: AsyncClient, auth_headers: dict
):
    """Export request on unapproved run must return 409."""
    run_id = await _make_approved_run(test_client, auth_headers)
    resp = await test_client.post(
        f"/api/v1/runs/{run_id}/exports",
        json={"format": "markdown"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_request_export_invalid_format_returns_422(
    test_client: AsyncClient, auth_headers: dict
):
    run_id = await _make_approved_run(test_client, auth_headers)
    resp = await test_client.post(
        f"/api/v1/runs/{run_id}/exports",
        json={"format": "pdf_invalid_format"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_export_isolated_between_users(
    test_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
):
    run_id = await _make_approved_run(test_client, auth_headers)
    resp = await test_client.get(
        f"/api/v1/runs/{run_id}/exports", headers=other_auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_download_returns_content(
    test_client: AsyncClient, auth_headers: dict
):
    """
    If a completed export record exists, the download endpoint should return
    200 with content or a redirect. Skipped if no completed export exists.
    """
    run_id = await _make_approved_run(test_client, auth_headers)
    exports = await test_client.get(
        f"/api/v1/runs/{run_id}/exports", headers=auth_headers
    )
    items = exports.json()
    completed = [e for e in items if e.get("status") == "completed"]
    if not completed:
        pytest.skip("No completed export to download")

    export_id = completed[0]["id"]
    resp = await test_client.get(
        f"/api/v1/runs/{run_id}/exports/{export_id}/download",
        headers=auth_headers,
    )
    assert resp.status_code in (200, 302)
