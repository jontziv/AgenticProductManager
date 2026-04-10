"""
Shared pytest fixtures.
Uses environment overrides so tests never touch production config.
"""

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Set test env vars before any imports that hit Settings
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key-not-real")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-32-chars-padding!!")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pm_sidekick_test")
os.environ.setdefault("GROQ_API_KEY", "gsk_test_key_not_real_for_unit_tests")
os.environ.setdefault("APP_ENV", "local")

from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings

# ---------------------------------------------------------------------------
# Module-level constant for E2E mocks that need to import without fixtures
# ---------------------------------------------------------------------------
SAMPLE_ARTIFACTS: dict = {
    "problem_framing": {
        "problem_statement": "Product managers spend 3+ hours weekly aggregating feedback manually.",
        "opportunity": "Reduce feedback aggregation time by 80%.",
        "hypothesis": "Unified classification enables faster prioritization.",
        "goals": ["Reduce weekly feedback time to <30 min"],
        "non_goals": ["Replace Intercom"],
        "assumptions": ["Users have Intercom accounts"],
    },
    "personas": {
        "personas": [
            {
                "name": "Sarah Chen", "role": "Senior Product Manager",
                "archetype": "Analyst",
                "goals": ["Reduce documentation time"],
                "pain_points": ["Manual aggregation"],
                "behaviors": ["Uses Jira daily"],
                "jobs_to_be_done": ["Prioritize roadmap"],
            }
        ]
    },
}


@pytest.fixture(scope="session")
def test_settings():
    return get_settings()


@pytest.fixture
def client():
    """Sync test client for FastAPI."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    """Mock JWT token for authenticated requests."""
    import jwt
    settings = get_settings()
    token = jwt.encode(
        {"sub": "test-user-id", "email": "test@example.com"},
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_intake_payload():
    return {
        "title": "Customer Feedback Analytics Dashboard",
        "business_idea": (
            "Product managers at B2B SaaS companies spend 3+ hours weekly "
            "manually aggregating customer feedback from Intercom, Zendesk, and Slack. "
            "We want to build a unified dashboard that auto-classifies feedback by theme, "
            "sentiment, and urgency."
        ),
        "target_users": "Product managers at B2B SaaS companies (50-500 employees)",
        "meeting_notes": "Stakeholders want MVP in Q2. Budget is $50k. Must integrate with Intercom first.",
        "raw_requirements": "Users need to filter feedback by date range, product area, and sentiment.",
        "constraints": "3-month timeline, team of 3 engineers",
        "timeline": "Q2 2026",
        "assumptions": "Users already have Intercom accounts",
    }


@pytest.fixture
def sample_problem_framing():
    return {
        "problem_statement": "Product managers spend 3+ hours weekly aggregating feedback manually.",
        "opportunity": "Reduce feedback aggregation time by 80% for 10,000 PMs.",
        "hypothesis": "If PMs have unified feedback classification, they will make faster prioritization decisions.",
        "goals": ["Reduce weekly feedback time to <30 min", "Improve prioritization speed by 50%"],
        "non_goals": ["Replace Intercom", "Provide customer success workflows"],
        "assumptions": ["Users have Intercom accounts", "APIs are accessible"],
    }


@pytest.fixture
def sample_personas():
    return {
        "personas": [
            {
                "name": "Sarah Chen",
                "role": "Senior Product Manager",
                "archetype": "Analyst",
                "goals": ["Reduce documentation time", "Better stakeholder alignment"],
                "pain_points": ["Manual aggregation", "Scattered feedback"],
                "behaviors": ["Uses Jira daily", "Weekly reviews"],
                "jobs_to_be_done": ["Prioritize roadmap", "Report to leadership"],
            },
            {
                "name": "Marcus Rodriguez",
                "role": "Product Lead",
                "archetype": "Strategist",
                "goals": ["Clear team focus", "Fast decisions"],
                "pain_points": ["Conflicting signals", "No single source of truth"],
                "behaviors": ["Reviews weekly", "Data-driven"],
                "jobs_to_be_done": ["Set quarterly OKRs", "Manage PM team"],
            },
        ]
    }


@pytest.fixture
def sample_artifacts(sample_problem_framing, sample_personas):
    return {
        "problem_framing": sample_problem_framing,
        "personas": sample_personas,
        "mvp_scope": {
            "in_scope": ["Feedback dashboard", "Theme classification", "Intercom integration"],
            "out_of_scope": ["Mobile app", "Custom ML training"],
            "core_features": [
                {"id": "F001", "name": "Feedback Aggregation", "description": "Pull feedback from Intercom",
                 "rationale": "Core use case", "priority": "P0"},
                {"id": "F002", "name": "Theme Classification", "description": "Auto-classify by theme",
                 "rationale": "Reduces manual work", "priority": "P0"},
            ],
            "deferred_features": ["Mobile view", "Slack integration"],
        },
        "success_metrics": {
            "metrics": [
                {"id": "M001", "category": "Efficiency", "metric_name": "Time on feedback",
                 "description": "Weekly hours spent", "target": "<30 min",
                 "signal_type": "lagging", "measurement_method": "In-app timer"},
            ]
        },
        "user_stories": {
            "stories": [
                {
                    "id": "US-001", "persona_ref": "Sarah Chen",
                    "as_a": "Senior Product Manager",
                    "i_want": "to view all customer feedback in one dashboard",
                    "so_that": "I can prioritize without switching tools",
                    "acceptance_criteria": [
                        "Dashboard loads in <2s",
                        "Shows feedback from last 30 days by default",
                        "Can filter by product area",
                    ],
                    "priority": "High", "estimated_effort": "5",
                    "epic": "Core Dashboard", "linked_test_ids": [],
                },
            ]
        },
        "backlog_items": {
            "epics": [{"epic": "Core Dashboard", "epic_description": "Main workflow",
                       "story_ids": ["US-001"], "priority_rationale": "Foundational"}],
            "total_story_count": 1,
        },
        "test_cases": {
            "test_cases": [
                {
                    "id": "TC-001", "story_id": "US-001",
                    "scenario": "Load feedback dashboard",
                    "preconditions": ["User is logged in", "Intercom connected"],
                    "steps": ["Navigate to /dashboard", "View feedback list"],
                    "expected_result": "Dashboard loads within 2 seconds",
                    "test_type": "e2e", "priority": "High",
                },
            ]
        },
        "risks": {
            "risks": [
                {
                    "id": "R001", "category": "technical",
                    "description": "Intercom API rate limits may throttle ingestion",
                    "likelihood": "Medium", "impact": "High",
                    "mitigation": "Implement exponential backoff and caching",
                    "owner": "Tech Lead", "linked_artifact": "architecture",
                },
            ]
        },
        "architecture": {
            "options": [
                {
                    "name": "Lightweight SaaS",
                    "description": "React + FastAPI + Supabase",
                    "components": ["React frontend", "FastAPI", "Supabase", "Groq"],
                    "data_flow": "User -> React -> FastAPI -> Groq -> DB",
                    "pros": ["Fast to ship", "Low cost"],
                    "cons": ["Limited scale"],
                    "cost_profile": "$50/month at 100 users",
                    "recommended": True,
                }
            ],
            "recommended_option": "Lightweight SaaS",
            "rationale": "Matches MVP timeline and budget constraints",
            "non_functional_requirements": ["<2s load time", "99.5% uptime"],
            "technical_considerations": ["Use connection pooling", "Cache API responses"],
        },
    }
