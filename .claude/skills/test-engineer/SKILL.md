---
name: test-engineer
description: Test conventions, fixture patterns, and test execution commands for the PM Sidekick backend and frontend test suites.
triggers:
  - "write a test"
  - "add a test"
  - "how do I test"
  - "run tests"
  - "test coverage"
  - "pytest"
  - "playwright"
---

# Test Engineer

## Backend test layers

| Layer | Location | What it tests | External deps |
|-------|----------|---------------|---------------|
| Unit | `tests/unit/` | Pure logic, schemas, evaluator, config | None |
| Integration | `tests/integration/` | FastAPI routes, DB queries, job queue | Postgres (test DB) |
| E2E | `tests/e2e/` | Full stack: intake → QA → approve → export | Postgres + mocked LLM |

## Running tests

```bash
# Unit tests (no DB required)
cd backend
pytest tests/unit/ -v

# Integration tests (requires TEST_DATABASE_URL)
pytest tests/integration/ -v -m integration

# E2E tests (requires DB + mocked LLM)
pytest tests/e2e/ -v -m e2e --timeout=60

# All tests with coverage
pytest --cov=app --cov=worker --cov-report=html
```

## Shared fixtures (`tests/conftest.py`)

```python
@pytest.fixture
def sample_artifacts() -> dict:
    """Complete 9-artifact set used across unit, integration, and E2E tests."""
    ...

@pytest.fixture
def auth_headers() -> dict:
    """Returns {"Authorization": "Bearer <valid-test-JWT>"} signed with test secret."""
    ...
```

## Integration test setup

Integration tests use `AsyncClient` with `ASGITransport`:

```python
@pytest_asyncio.fixture(scope="session")
async def test_client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client
```

Two auth fixtures are available for isolation tests:
- `auth_headers` — user A
- `other_auth_headers` — user B (for testing 404 on cross-user access)

## E2E mock pattern

Mock `generate_structured` to avoid LLM calls:

```python
@pytest.fixture(autouse=True)
def mock_groq_client():
    import app.llm.client as llm_module
    async def _fake_generate(model, prompt_name, response_model, **kwargs):
        instance = MagicMock(spec=response_model)
        return instance
    with patch.object(llm_module, "generate_structured", side_effect=_fake_generate):
        yield
```

## Unit test patterns

### QA harness tests
```python
@pytest.mark.asyncio
async def test_hard_fail_blocks_export(sample_artifacts):
    artifacts = {**sample_artifacts, "user_stories": {"stories": []}}
    report = await run_qa_evaluation(artifacts=artifacts, source_inputs={})
    assert report["export_ready"] is False
    assert report["critical_issues"] > 0
```

### Config validation tests
```python
def test_missing_groq_key_raises():
    with pytest.raises((ValidationError, ValueError)):
        Settings(groq_api_key="gsk_replace_me", ...)
```

### Export service tests
```python
@pytest.mark.asyncio
async def test_json_export_is_valid_json(sample_artifacts):
    pack = await generate_export_pack("run-id", sample_artifacts, formats=["json"])
    parsed = json.loads(pack["json"]["content"])
    assert parsed["run_id"] == "run-id"
```

## Frontend tests (Playwright)

```bash
# Install browsers once
cd frontend
npx playwright install

# Run E2E tests
npm run test:e2e

# Run with UI
npx playwright test --ui
```

Playwright tests live in `frontend/tests/e2e/` and target `http://localhost:5173`.

## CI test matrix

```yaml
# .github/workflows/ci.yml runs:
- Unit tests (always)
- Integration tests (if DB_URL secret set)
- E2E tests (on main/release branches only)
- Frontend type-check + build
```

## Coverage requirements

- Unit tests: aim for >90% coverage on `app/evaluators/`, `app/llm/`, `app/config.py`
- Integration: aim for >70% coverage on `app/routers/`
- Uncovered code in `worker/` is acceptable for MVP; add tests before scaling

## Test data conventions

- Never use production run IDs or user IDs in tests
- Use `uuid.uuid4()` for all test IDs
- JWT tokens in tests must use `SUPABASE_JWT_SECRET=test-jwt-secret-32-chars-padding!!`
- Test DB: `postgresql://postgres:postgres@localhost:5432/pm_sidekick_test`
