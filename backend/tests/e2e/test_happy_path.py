"""
E2E test: happy path from intake submission to export.

These tests exercise the full stack but mock the Groq LLM calls to keep
execution deterministic and fast. The LangGraph graph runs real nodes;
only `generate_structured` is patched to return fixture data.

Run with:  pytest tests/e2e/ -m e2e --timeout=60
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from tests.conftest import SAMPLE_ARTIFACTS   # re-use fixture data as mock LLM returns


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_intake_payload() -> dict:
    return {
        "title": "E2E Happy Path",
        "raw_input": (
            "We need to help product managers build backlogs faster. "
            "Today they spend 3+ hours per sprint writing stories manually. "
            "Target users: PMs at mid-size SaaS companies. "
            "Constraint: must integrate with Jira."
        ),
        "input_type": "text",
        "target_users": "Product managers at SaaS companies",
        "business_context": "Reduce PM overhead by 50%",
        "constraints": "Jira integration required",
    }


async def _poll_until_terminal(client: AsyncClient, run_id: str, headers: dict, timeout: int = 45) -> dict:
    """Poll the run status until it reaches a terminal state or times out."""
    for _ in range(timeout):
        resp = await client.get(f"/api/v1/runs/{run_id}", headers=headers)
        assert resp.status_code == 200
        run = resp.json()
        if run["status"] in ("qa_passed", "failed", "cancelled", "approved", "exported"):
            return run
        await asyncio.sleep(1)
    raise TimeoutError(f"Run {run_id} did not reach terminal state in {timeout}s")


# ---------------------------------------------------------------------------
# Fixture: mock LLM to return deterministic artifacts
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_groq_client():
    """
    Patch generate_structured to return sample artifact content without
    hitting the Groq API. The return type must match whatever Pydantic model
    is requested; we return a MagicMock that passes isinstance checks via spec.
    """
    import app.llm.client as llm_module

    async def _fake_generate(model, prompt_name, response_model, **kwargs):
        # Return a mock that validates as the requested Pydantic model
        instance = MagicMock(spec=response_model)
        # Populate with sample data where available
        if hasattr(response_model, "model_fields"):
            for field_name in response_model.model_fields:
                sample_val = SAMPLE_ARTIFACTS.get(prompt_name, {}).get(field_name, f"mock_{field_name}")
                setattr(instance, field_name, sample_val)
        return instance

    with patch.object(llm_module, "generate_structured", side_effect=_fake_generate):
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_happy_path(test_client: AsyncClient, auth_headers: dict):
    """
    Full workflow: create run → poll until qa_passed → approve → request export → verify export.
    """
    # 1. Create run
    create_resp = await test_client.post(
        "/api/v1/runs", json=_make_intake_payload(), headers=auth_headers
    )
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "queued"

    # 2. Wait for processing (mocked LLM, should be fast)
    run = await _poll_until_terminal(test_client, run_id, auth_headers)
    assert run["status"] == "qa_passed", f"Expected qa_passed, got {run['status']}"

    # 3. Verify artifacts populated
    artifacts_resp = await test_client.get(
        f"/api/v1/runs/{run_id}/artifacts", headers=auth_headers
    )
    assert artifacts_resp.status_code == 200
    artifacts = artifacts_resp.json()
    artifact_types = {a["artifact_type"] for a in artifacts}
    expected = {"problem_framing", "personas", "user_stories", "architecture"}
    assert expected.issubset(artifact_types), f"Missing artifacts: {expected - artifact_types}"

    # 4. Verify QA report
    qa_resp = await test_client.get(f"/api/v1/runs/{run_id}/qa", headers=auth_headers)
    assert qa_resp.status_code == 200
    qa = qa_resp.json()
    assert qa["export_ready"] is True
    assert qa["critical_issues"] == 0

    # 5. Approve run
    approve_resp = await test_client.post(
        f"/api/v1/runs/{run_id}/approval",
        json={"approved": True, "comment": "All good, ship it"},
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200

    # 6. Verify run status updated to approved
    run_resp = await test_client.get(f"/api/v1/runs/{run_id}", headers=auth_headers)
    assert run_resp.json()["status"] == "approved"

    # 7. Request export
    for fmt in ("markdown", "json"):
        export_resp = await test_client.post(
            f"/api/v1/runs/{run_id}/exports",
            json={"format": fmt},
            headers=auth_headers,
        )
        assert export_resp.status_code in (200, 201, 202), \
            f"Export request for {fmt} failed: {export_resp.status_code}"

    # 8. List exports and verify entries exist
    exports_resp = await test_client.get(
        f"/api/v1/runs/{run_id}/exports", headers=auth_headers
    )
    assert exports_resp.status_code == 200
    exports = exports_resp.json()
    assert len(exports) >= 1


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_dashboard_shows_completed_run(test_client: AsyncClient, auth_headers: dict):
    """After a run completes, it must appear in the user's run list."""
    create_resp = await test_client.post(
        "/api/v1/runs", json=_make_intake_payload(), headers=auth_headers
    )
    run_id = create_resp.json()["id"]

    await _poll_until_terminal(test_client, run_id, auth_headers)

    list_resp = await test_client.get("/api/v1/runs", headers=auth_headers)
    assert list_resp.status_code == 200
    ids = [r["id"] for r in list_resp.json()["items"]]
    assert run_id in ids
