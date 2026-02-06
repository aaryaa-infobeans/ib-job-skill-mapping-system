# Candidate Availability Agent (Separate Graph) – Implementation Plan
/speckit.plan
## A) Plan Summary
Implement the Candidate Availability Agent as a deterministic, contract-driven backend agent for the IB Requisition System, using a separate LangGraph workflow. Strictly follow the provided spec files, supporting both input formats, applying all validation and availability rules, and returning a deterministic response. Integration will be minimal and targeted, with a new FastAPI endpoint and executor, and full testability via Postman and pytest.

## B) Phase-wise PR Plan

**PR#1 — Spec Alignment, Pydantic Contracts, Normalization**
- Identify and list the spec files used:
  - prompts/candidate-availability-agent-prompt.md
- Extract: payload formats, validation rules, output schema, endpoint, reason codes
- Implement request/response Pydantic schemas per spec
- Implement normalization logic (team_member_id/team_member_ids merge, dedupe, order)
- Enforce strict validation (reject unknown fields)
- Done when: All schema/normalization/validation rules are covered and tested (pytest)

**PR#2 — DB Access + Availability Engine (Batch Queries)**
- Implement/reuse SQLAlchemy models and session dependency
- Implement batch queries for team_member and team_member_allocation (soft delete, billable, overlap logic)
- Apply all availability rules (inactive, not found, overlap, etc.)
- Build deterministic per-candidate results, conflicts, summary
- Done when: All DB logic and rules are covered, edge cases tested (pytest)

**PR#3 — LangGraph Availability Workflow (Separate Graph)**
- Build LangGraph nodes: prepare, query_db, decide, finalize
- Implement create_availability_graph() in src/app/ai/availability_graph.py
- Ensure graph is compiled once and invoked per request via executor
- Done when: Workflow is callable and produces correct results (pytest)

**PR#4 — Executor + FastAPI Endpoint Integration**
- Add execute_availability_graph_with_audit(...) to src/app/ai/graph_executor.py
- Add POST /api/agents/candidate-availability to FastAPI routes (src/app/main.py or routers)
- Add structured logging (request_id, count, exec time; no secrets)
- Done when: Endpoint is live, logs as required, and works with Postman/curl

**PR#5 — Tests + Developer Docs + Postman Examples**
- Add pytest suite for all spec scenarios (not found, inactive, overlap, dedupe, soft delete, etc.)
- Add README/developer note: env vars, uvicorn run, Postman payloads
- Confirm no DB migrations needed (unless spec changes DB)
- Done when: All tests pass, docs are clear, Postman/curl works

## C) Final Expected Repository Tree

```
ib-job-skill-mapping-system/
├── src/
│   └── app/
│       ├── ai/
│       │   ├── agents/
│       │   │   └── candidate_availability.py
│       │   ├── availability_graph.py
│       │   ├── graph_executor.py
│       │   └── ...
│       ├── main.py
│       └── ...
├── tests/
│   └── test_candidate_availability.py
├── prompts/
│   └── candidate-availability-agent-prompt.md
└── ...
```

## D) Local Commands Checklist

- **Create venv:**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Install dependencies:**
  ```powershell
  pip install -r requirements.txt
  ```
- **Set DATABASE_URL (PowerShell):**
  ```powershell
  $env:DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/ib_job_skill_match_system"
  ```
- **Run server (Uvicorn):**
  ```powershell
  uvicorn src.app.main:app --host 127.0.0.1 --port 8010 --reload
  ```
- **Run tests:**
  ```powershell
  pytest
  ```
- **Run migrations:**
  No migrations needed (schema unchanged per spec)

## E) Open Questions / Assumptions
- None. All requirements, fields, and rules are defined in the spec files. If ambiguity arises, default to strict contract-driven behavior as described in the specs.
