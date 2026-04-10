# PM Sidekick: Agentic Intake-to-Backlog Workbench

## Mission
Build a workflow-first product manager sidekick. The system converts stakeholder notes, requirements, and ideas into reviewed PM artifacts. This is not a chat bot. It is a staged application with forms, orchestration, approvals, and exportable deliverables.

## Product shape
Primary stages:
1. Idea intake
2. Classification + missing-data check
3. Scope and assumptions review
4. MVP brief
5. Stories + backlog
6. Test cases + risks
7. Architecture recommendation
8. AI QA review
9. Export pack

## Non-negotiables
- Prefer deterministic workflows over free-form agent loops.
- Use LangGraph state + checkpoints for resumable execution.
- Keep prompts small; move long procedures to skills.
- Separate facts, assumptions, and recommendations.
- Never hallucinate users, constraints, metrics baselines, integrations, or market evidence.
- Block export on QA hard fails.
- Preserve traceability: requirement -> artifact -> story -> acceptance criteria -> test -> metric/risk.
- If upstream artifacts change, mark downstream artifacts stale and regenerate selectively.

## Preferred implementation
- Frontend: React + TypeScript or equivalent.
- Backend/orchestrator: Python + LangGraph/LangChain or equivalent.
- Persistence: Postgres for app state, artifact versions, approvals, and checkpoints.
- Background jobs: worker queue for generation, QA, and export.
- Provider layer: Groq only, behind a thin model adapter.
- Contracts: JSON Schema / OpenAPI / Zod / Pydantic at all boundaries.

## LangGraph design
State keys:
- intake
- classification
- assumptions
- brief
- personas
- scope
- metrics
- backlog
- test_cases
- risks
- architecture
- qa_report
- approvals
- export_pack

Default node order:
1. sanitize_input
2. extract_structured_intake
3. classify_idea_type
4. detect_missing_data
5. generate_problem_frame
6. generate_personas
7. generate_mvp_scope
8. generate_success_metrics
9. generate_stories_and_backlog
10. generate_test_cases
11. generate_risks
12. generate_architecture_options
13. run_qa_evaluation
14. create_remediation_tasks_if_needed
15. request_human_approval
16. export_artifacts

Routing rules:
- Missing critical intake data -> stop, ask focused questions, or proceed with explicit assumptions only.
- QA hard fail -> no export.
- User edits approved artifact -> invalidate dependent nodes only.
- Long-running steps -> queue asynchronously and persist status by job ID.

## Output rules
- Keep outputs concise, structured, and decision-ready.
- Prefer tables and typed objects over prose walls.
- Max 3 personas unless explicitly requested.
- Max 2 architecture options; recommend 1.
- Every story needs acceptance criteria and linked test coverage.
- Risks must include mitigation and owner.
- Metrics must distinguish leading vs lagging signals.

## Security and config
- Store secrets only in local `.env` and platform secret stores.
- Never hardcode keys or tokens.
- `.env` must always stay in `.gitignore`.
- Commit only `.env.example` with placeholders.
- Validate required env vars on startup and fail fast.
- Do not log secrets, raw tokens, or full sensitive payloads.

## Deployment stance
- Vercel: frontend, previews, UI hosting.
- Render: API, worker, Postgres, optional Redis.
- Expose `/healthz` on every web service.
- Separate local, preview, staging, and production env values.
- Production deploys require lint, typecheck, tests, build, and smoke checks.

## Testing stance
- Unit tests for pure logic, schemas, reducers, utilities.
- Integration tests for API routes, persistence, queues, and graph nodes.
- Regression tests for prompts, schemas, and evaluator scoring.
- E2E tests for happy path and one remediation path.
- Snapshot tests are allowed only for stable structured outputs.

## Default behavior for Claude
- Read this file for project facts.
- Load skills for procedures instead of expanding this file.
- When implementing features, optimize for maintainability, traceability, and production readiness.
- Favor simple, typed, testable code over framework cleverness.

## Skills
Use these instead of bloating `CLAUDE.md`:
- `/pm-artifact-orchestrator`
- `/qa-evaluator`
- `/groq-model-routing`
- `/engineering-standards`
- `/deployment-readiness`
