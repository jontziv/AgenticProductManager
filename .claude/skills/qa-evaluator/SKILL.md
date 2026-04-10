---
name: qa-evaluator
description: Runs the 17-check deterministic QA rubric against a complete artifact set. Returns a QaReport with scores, hard-fail flags, and remediation tasks. No LLM calls — all checks are structural/rule-based.
triggers:
  - "run QA"
  - "evaluate artifacts"
  - "check artifact quality"
  - "qa harness"
  - "rubric check"
---

# QA Evaluator

## What this skill does
Evaluates all artifacts against a 17-check rubric. Returns a structured `QaReport`. Hard fails block export.

## Running the evaluator

```python
from app.evaluators.harness import run_qa_evaluation

report = await run_qa_evaluation(
    artifacts=state["artifacts"],
    source_inputs={"target_users": state["intake"]["target_users"]},
)
# report["export_ready"] is False if any hard fail triggered
```

## Check categories and IDs

| ID   | Category     | Name                        | Hard Fail | Max Score |
|------|--------------|-----------------------------|-----------|-----------|
| F001 | Faithfulness | Problem Grounding           | YES       | 10        |
| F002 | Faithfulness | Persona Alignment           | no        | 8         |
| F003 | Faithfulness | Scope Traceability          | no        | 8         |
| F004 | Faithfulness | Metric Measurability        | YES       | 8         |
| C001 | Completeness | Artifact Coverage           | YES       | 15        |
| C002 | Compliance   | Story AC Count              | YES       | 10        |
| C003 | Compliance   | Story Format                | no        | 5         |
| C004 | Compliance   | Priority Taxonomy           | no        | 5         |
| P001 | Consistency  | Persona-Story Alignment     | no        | 8         |
| P002 | Consistency  | Feature-Story Mapping       | no        | 8         |
| P003 | Consistency  | Metric-Goal Linkage         | no        | 8         |
| P004 | Consistency  | Architecture Recommendation | YES       | 10        |
| K001 | Compliance   | Risk Mitigation             | YES       | 8         |
| K002 | Compliance   | Test Coverage               | no        | 8         |
| Q001 | Format       | Schema Validity             | YES       | 5         |
| Q002 | Format       | Text Quality                | no        | 5         |
| Q003 | Format       | Length Bounds               | no        | 5         |

**Total max score: 130 → normalized to 100 in pass_rate**

## Hard fail IDs
```python
HARD_FAIL_IDS = {"F001", "F004", "C001", "C002", "P004", "K001", "Q001"}
```

## Report structure

```python
{
    "overall_score": 87,         # raw points earned
    "max_score": 130,
    "pass_rate": 66.9,           # percentage
    "critical_issues": 0,        # count of hard fail triggers
    "export_ready": True,        # False if any hard fail
    "checks": [
        {
            "id": "C001",
            "category": "Completeness",
            "name": "Artifact Coverage",
            "status": "passed",   # or "failed" or "skipped"
            "score": 15,
            "max_score": 15,
            "detail": "All 9 artifact types present.",
            "hard_fail": True,
        },
        ...
    ],
    "remediation_tasks": [
        {
            "id": "REM-001",
            "check_id": "C002",
            "description": "Add at least 3 acceptance criteria to US-003 (High priority)",
            "affected_artifact": "user_stories",
            "priority": "high",
        }
    ]
}
```

## Common remediation patterns

### C002 — Story missing acceptance criteria
Trigger: High-priority story with < 3 acceptance criteria.
Fix: add criteria that are measurable and testable.

### C001 — Missing artifact type
Trigger: One of the 9 expected artifact types absent from artifacts dict.
Fix: regenerate the missing artifact node via `regenerate_artifact` job.

### P004 — No architecture recommendation
Trigger: `architecture.recommended_option` is empty or None.
Fix: set `recommended: true` on exactly one option and populate `rationale`.

### K001 — Risk without mitigation
Trigger: Any risk with empty `mitigation` field.
Fix: add concrete mitigation steps and owner for each risk.

## Adding a new check
1. Add `CheckDef` to `app/evaluators/rubric.py`
2. Implement the check function in `app/evaluators/harness.py`
3. Call it inside `run_qa_evaluation()` and append result to `checks`
4. Add to `HARD_FAIL_IDS` if it should block export
5. Write a unit test in `tests/unit/test_qa_harness.py`
