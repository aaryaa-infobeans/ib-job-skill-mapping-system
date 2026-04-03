# ADR-001: Multi-Agent Framework Architecture

**Status:** Accepted
**Date:** 2026-03-31
**Authors:** Agent Migration Team

## Context

The IB Job Skill Mapping System processes job requisitions through an 8-node LangGraph pipeline: PII scrubbing, requisition parsing, skill normalization, embedding generation, RAG retrieval, matching/scoring, explanation generation, and result aggregation. The system works but suffers from several architectural limitations:

- **Monolithic state**: A single `GraphState` TypedDict is threaded through all nodes, creating tight coupling.
- **God-object config**: `settings.py` contains 80+ fields imported everywhere.
- **No independent lifecycle**: Agents can't be started, stopped, or replaced independently.
- **No observability hooks**: No per-agent metrics, tracing, or health reporting.
- **No hot-swap**: Adding or modifying an agent requires code changes and a full restart.

## Decision

We adopted a **strangler-fig migration** to wrap the existing brownfield code in a new plug-and-play agent framework, preserving all existing behavior while adding:

1. **BaseAgent ABC** with `initialize()`, `handle()`, `health_check()`, `shutdown()` lifecycle.
2. **Message-passing** via immutable Pydantic `Message` objects with `trace_id` propagation.
3. **Data-driven routing** — routes defined in YAML config with JSONPath conditions.
4. **AgentRegistry** with semver constraint resolution and plugin discovery.
5. **Orchestrator** managing per-agent asyncio workers with bounded queues (backpressure).
6. **Observability** — Prometheus metrics, optional OpenTelemetry tracing, structured JSON logging.
7. **Hot-reload** — file-watching config reloader with safe runtime enable/disable/reconfigure.
8. **Dead-letter store** — failed messages stored for inspection and replay.

## Consequences

### Positive
- Each agent has an independent lifecycle and can be tested, deployed, and monitored independently.
- Adding a new agent requires only: a Python file, a YAML config block, and routing rules — zero framework code changes.
- The routing graph is validated at startup (unknown agents, unreachable agents, cycles).
- Brownfield code runs unmodified inside the agent wrappers via anti-corruption layers.
- Per-agent Prometheus metrics and health checks are automatic.

### Negative / Trade-offs
- Two orchestration systems coexist during migration (LangGraph + new framework).
- The strangler-fig wrappers add a thin adapter layer (~50 lines per agent).
- 10 brownfield TODOs remain (DB session injection, LLM client injection, Redis wiring) — tracked in `TASK-MIGRATE-001` through `TASK-MIGRATE-010`.

### Risks
- Config drift between `agents.yaml` and `settings.py` during the coexistence period — mitigated by `_build_scoped_config()` which merges infrastructure config into agent scopes.
- Shared `sys.modules` in tests when brownfield modules have heavy dependencies — mitigated by pre-populating mock modules.

## Alternatives Considered

1. **Full rewrite**: Rejected — too risky for a production system with no comprehensive test coverage.
2. **LangGraph extension**: Rejected — LangGraph's shared-state model inherently couples agents.
3. **Off-the-shelf framework (Prefect, Temporal)**: Rejected — adds operational complexity for a system that runs on a single server with asyncio.

## Architecture Overview

```
config/agents.yaml
    │
    ▼
┌─────────────────────────────┐
│  ConfigLoader (5-stage)     │
│  env → schema → routing     │
│  → agent-schema → business  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Orchestrator               │
│  ┌─────────────────────┐    │
│  │ AgentRegistry        │    │
│  │ (resolve by semver)  │    │
│  └─────────┬───────────┘    │
│            │                │
│  ┌─────────▼───────────┐    │
│  │ Per-Agent Workers    │    │
│  │ (asyncio.Queue)      │    │
│  └─────────┬───────────┘    │
│            │                │
│  ┌─────────▼───────────┐    │
│  │ RoutingEngine        │    │
│  │ (JSONPath conditions)│    │
│  └─────────────────────┘    │
└─────────────────────────────┘
```

## Test Coverage

| Phase | Test File | Tests | Description |
|-------|-----------|-------|-------------|
| 3 | test_agent_framework.py | 31 | Message, HealthStatus, BaseAgent, Registry, Semver |
| 4 | test_config_loader.py | 27 | Config loading, validation, env substitution |
| 5 | test_orchestrator.py | 21 | RoutingEngine, lifecycle, retry, health |
| 6 | test_migration_agents.py | 16 | Per-agent wrapper behavior, trace propagation |
| 7 | test_observability.py | 20 | Metrics, tracing, DLQ, log adapter |
| 8 | test_hot_reload.py | 8 | File watching, hot-swap, feature flags |
| 9 | test_integration.py | 4 | Full 7-agent pipeline end-to-end |
| **Total** | | **127** | |

## Migration TODO Tracker

| ID | Description | Status |
|----|-------------|--------|
| TASK-MIGRATE-001 | Wire PII audit logger to injected DB session | Pending |
| TASK-MIGRATE-002 | Replace llm_client singleton in requisition parsing | Pending |
| TASK-MIGRATE-003 | Replace SessionLocal() in skill normalization | Pending |
| TASK-MIGRATE-004 | Redirect OpenAI hardcode through LLMClient | Pending |
| TASK-MIGRATE-005 | Inject embedding config from agents.yaml | Pending |
| TASK-MIGRATE-006 | Replace SessionLocal() in RAG retrieval | Pending |
| TASK-MIGRATE-007 | Replace SessionLocal() in scoring | Pending |
| TASK-MIGRATE-008 | Inject weight profiles from agents.yaml | Pending |
| TASK-MIGRATE-009 | Replace llm_client singleton in explanation | Pending |
| TASK-MIGRATE-010 | Wire Redis backend for results cache | Pending |
