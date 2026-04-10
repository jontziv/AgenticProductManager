---
name: pm-artifact-orchestrator
description: Turn stakeholder notes or ideas into structured PM artifacts with traceability, approval gates, and minimal hallucination.
---

Use this when asked to transform meeting notes, rough requirements, or business ideas into PM deliverables.

## Operating rules
- Work in stages. Do not generate everything at once if the intake is incomplete.
- Always distinguish facts, assumptions, and recommendations.
- Preserve traceability across artifacts.
- Prefer compact structured output over essay-style prose.
- Regenerate only the downstream artifacts affected by edits.

## Process
1. Normalize the intake.
2. Extract the smallest valid structured brief.
3. Classify the idea type and product pattern.
4. Surface missing information and risky assumptions.
5. Generate artifacts in the canonical order.
6. Run the QA evaluator before export.
7. If QA fails, create remediation tasks and block export.

## Canonical order
1. Problem framing
2. Personas
3. MVP scope
4. Success metrics
5. User stories
6. Backlog items
7. Test cases
8. Risk checklist
9. Lightweight architecture recommendation
10. QA report
11. Export pack

## Traceability rules
- Every problem statement maps to at least one persona and one success metric.
- Every story maps to a persona, value outcome, and acceptance criteria.
- Every acceptance criterion maps to at least one test case.
- Every risk links to an artifact or assumption it threatens.
- Every architecture recommendation must reference scope and non-functional needs.

## Missing-data policy
Treat these as critical if absent:
- target user or user group
- core problem / pain
- primary outcome
- major constraints
- timeline or urgency

If critical data is missing:
- ask focused questions, or
- continue with labeled assumptions if a best-effort draft is requested.

## Output contract
Load `artifact-contracts.md` for required sections, limits, and formatting.
