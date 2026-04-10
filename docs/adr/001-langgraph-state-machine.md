# ADR-001: Use LangGraph for workflow orchestration

**Status:** Accepted  
**Date:** 2026-04-10

## Context

The product requires a deterministic multi-step workflow that:
- Executes 14 sequential nodes, some with conditional routing
- Supports human-in-the-loop approval (pause + resume)
- Provides checkpointing so in-progress runs survive worker restarts
- Allows selective node re-execution when upstream artifacts change
- Is resumable across HTTP requests (API enqueues, worker processes)

Alternatives considered:

1. **Custom Python async state machine** — lowest overhead, but requires building checkpointing, interrupt/resume, conditional routing, and streaming from scratch.
2. **Temporal / Prefect / Airflow** — purpose-built workflow engines. Heavyweight for an MVP; adds infra complexity (Temporal cluster or Prefect server).
3. **LangGraph** — designed exactly for agentic state machines with checkpoints. Integrates with LangChain ecosystem. Supports `interrupt_before` for human-in-the-loop. Has `MemorySaver` and `PostgresSaver` for checkpoints.
4. **Pure function chain with DB state** — store state in DB after each step, re-read on resume. Simpler but loses streaming + checkpoint granularity.

## Decision

Use **LangGraph** with `MemorySaver` checkpointing for MVP.

- `StateGraph` + `TypedDict` state: typed, inspectable state at every node
- `interrupt_before=["human_review_gate"]`: clean pause/resume for approval
- `astream()`: real-time event streaming to the worker for artifact persistence
- `get_graph()` singleton: compile once, reuse across jobs (efficient)

## Consequences

**Positive:**
- Conditional routing (missing data, QA fail, remediation loop) is declarative
- `MemorySaver` checkpoint is free and requires no infra for MVP
- `astream` lets the worker persist each artifact as it's generated
- Upgrading from `MemorySaver` to `AsyncPostgresSaver` requires one line change

**Negative:**
- LangGraph is evolving quickly — API may change between minor versions
- `MemorySaver` is in-process only; a worker restart loses in-flight state
- Graph compilation happens at import time — slow first request after cold start

**Mitigation:**
- Pin `langgraph==0.2.62` in `requirements.txt`
- Worker handles `SIGTERM` gracefully — marks in-flight jobs as `failed` for retry
- `get_graph()` is a cached singleton to minimize cold-start impact
