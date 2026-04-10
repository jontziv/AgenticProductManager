---
name: pm-artifact-orchestrator
description: Generates, validates, and orchestrates the full set of PM artifacts from structured intake data using the LangGraph workflow. Covers the 14-node pipeline from problem framing through export pack.
triggers:
  - "generate artifacts"
  - "run the orchestrator"
  - "build the backlog"
  - "create PM artifacts from"
  - "orchestrate run"
---

# PM Artifact Orchestrator

## What this skill does
Walks through the 14-node LangGraph pipeline and produces a complete artifact set from structured intake data.

## Node execution order
1. `sanitize_input` — strip PII, normalize whitespace
2. `extract_structured_intake` — parse raw text into typed IntakeBrief
3. `classify_idea_type` — feature | product | process | research (FAST model)
4. `detect_missing_data` — flag gaps; list assumptions for missing fields
5. `generate_problem_frame` — ProblemFraming with statement, opportunity, hypothesis, goals, non_goals, assumptions
6. `generate_personas` — max 3 Persona objects with JTBD and pain points
7. `generate_mvp_scope` — in_scope, out_of_scope, core_features (P0/P1), deferred_features
8. `generate_success_metrics` — leading + lagging metrics, each with measurement_method
9. `generate_stories_and_backlog` — User stories with AC (min 3 per High-priority story), epic grouping
10. `generate_test_cases` — TC per story, covering happy path + edge cases
11. `generate_risks` — Risk objects with likelihood, impact, mitigation, owner
12. `generate_architecture_options` — max 2 options; recommended=True on exactly one
13. `run_qa_evaluation` — 17-check rubric; hard fails block export
14. `export_pack_node` — markdown, JSON, HTML, Jira CSV, Linear CSV

## Routing rules
- `detect_missing_data` → if critical fields missing: `request_human_input` (stops graph, stores partial state)
- `run_qa_evaluation` → hard fail count > 0: `create_remediation_tasks_if_needed` → `request_human_approval` (interrupt_before)
- `run_qa_evaluation` → no hard fails: `request_human_approval` directly

## Calling from Python

```python
from app.graph.graph import get_graph
from app.graph.state import WorkflowState

graph = get_graph()
initial_state: WorkflowState = {
    "run_id": run_id,
    "user_id": user_id,
    "intake": intake_brief_dict,
}
config = {"configurable": {"thread_id": run_id}}

async for event in graph.astream(initial_state, config=config):
    # event is a dict keyed by node name
    node_name = list(event.keys())[0]
    node_output = event[node_name]
    # persist artifacts to DB as they stream out
    await save_artifact(run_id, node_name, node_output)
```

## Resuming after human approval

```python
# User has approved via UI; send approval signal to resume
await graph.aupdate_state(
    config,
    {"approvals": {"human_review": {"approved": True, "comment": comment}}},
    as_node="human_review_gate",
)
async for event in graph.astream(None, config=config):
    ...
```

## Hard fail check IDs (block export)
`F001, F004, C001, C002, P004, K001, Q001`

## Output artifact types
`problem_framing | personas | mvp_scope | success_metrics | user_stories | backlog_items | test_cases | risks | architecture`

## Examples

### Generate artifacts from meeting notes
```
User: Generate PM artifacts from these meeting notes: [notes text]
→ sanitize → extract → classify → detect_missing → ... → qa_evaluation
```

### Regenerate a single stale artifact
```python
from app.graph.nodes.generate import generate_personas
updated = await generate_personas(current_state)
await save_artifact(run_id, "personas", updated["personas"])
await mark_downstream_stale(run_id, upstream="personas")
```
