"""
Unit tests for export service — deterministic, no LLM/DB calls.
"""

import pytest
import pytest_asyncio
import json

from app.services.export_service import (
    _artifacts_to_markdown,
    _artifacts_to_jira_csv,
    generate_export_pack,
)


def test_markdown_contains_problem_statement(sample_artifacts):
    md = _artifacts_to_markdown(sample_artifacts)
    assert "Problem Framing" in md
    assert sample_artifacts["problem_framing"]["problem_statement"] in md


def test_markdown_contains_personas(sample_artifacts):
    md = _artifacts_to_markdown(sample_artifacts)
    assert "Sarah Chen" in md


def test_markdown_contains_stories(sample_artifacts):
    md = _artifacts_to_markdown(sample_artifacts)
    assert "US-001" in md


def test_jira_csv_has_header(sample_artifacts):
    csv = _artifacts_to_jira_csv(sample_artifacts)
    assert csv.startswith("Summary,")
    lines = csv.strip().split("\n")
    assert len(lines) >= 2  # header + at least one story


def test_jira_csv_contains_story(sample_artifacts):
    csv = _artifacts_to_jira_csv(sample_artifacts)
    assert "US-001" in csv


@pytest.mark.asyncio
async def test_generate_pack_returns_all_formats(sample_artifacts):
    pack = await generate_export_pack("test-run-id", sample_artifacts, formats=["markdown", "json", "html"])
    assert "markdown" in pack
    assert "json" in pack
    assert "html" in pack


@pytest.mark.asyncio
async def test_json_export_is_valid_json(sample_artifacts):
    pack = await generate_export_pack("test-run-id", sample_artifacts, formats=["json"])
    content = pack["json"]["content"]
    parsed = json.loads(content)
    assert parsed["run_id"] == "test-run-id"
    assert "artifacts" in parsed


@pytest.mark.asyncio
async def test_html_export_is_valid_html(sample_artifacts):
    pack = await generate_export_pack("test-run-id", sample_artifacts, formats=["html"])
    content = pack["html"]["content"]
    assert content.startswith("<!DOCTYPE html>")
    assert "<title>" in content


@pytest.mark.asyncio
async def test_empty_artifacts_does_not_crash():
    pack = await generate_export_pack("run-id", {}, formats=["markdown", "json"])
    assert "markdown" in pack
    assert "json" in pack
