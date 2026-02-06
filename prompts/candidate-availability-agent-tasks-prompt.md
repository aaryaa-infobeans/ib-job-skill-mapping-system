# Candidate Availability Agent (Separate Graph) – Task Backlog

## Milestones/PRs

### PR#1 — Spec Alignment + Pydantic Contracts + Normalization
- [ ] Create request/response Pydantic schemas per spec
  - File: src/app/ai/agents/candidate_availability.py
  - Acceptance: Schemas match all fields, types, and constraints in the spec
- [ ] Implement normalization logic (team_member_id/team_member_ids merge, trim, dedupe, order)
  - File: src/app/ai/agents/candidate_availability.py
  - Acceptance: Normalization produces correct team_member_ids list for all input cases
- [ ] Enforce strict validation (reject unknown fields, validate all constraints)
  - File: src/app/ai/agents/candidate_availability.py
  - Acceptance: Invalid/unknown fields are rejected with 422

### PR#2 — DB Access + Availability Engine (Batch Queries)
- [ ] Implement/reuse SQLAlchemy models and session dependency
  - File: src/app/ai/agents/candidate_availability.py
  - Acceptance: Models match DB schema; session is used per repo pattern
- [ ] Implement batch queries for team_member and team_member_allocation (soft delete, billable, overlap logic)
  - File: src/app/ai/agents/candidate_availability.py
  - Acceptance: Queries fetch all relevant data in 1 query per table; N+1 avoided
- [ ] Apply all availability rules (inactive, not found, overlap, etc.)
  - File: src/app/ai/agents/candidate_availability.py
  - Acceptance: Logic matches spec for all edge cases
- [ ] Build deterministic per-candidate results, conflicts, summary
  - File: src/app/ai/agents/candidate_availability.py
  - Acceptance: Output matches schema, order preserved, no null arrays

### PR#3 — LangGraph Availability Workflow (Separate Graph)
- [ ] Build LangGraph nodes: prepare, query_db, decide, finalize
  - File: src/app/ai/availability_graph.py
  - Acceptance: Each node encapsulates its step; nodes are pure and testable
- [ ] Implement create_availability_graph() in src/app/ai/availability_graph.py
  - File: src/app/ai/availability_graph.py
  - Acceptance: Graph is constructed as per spec; nodes wired in correct order
- [ ] Ensure graph is compiled once and invoked per request via executor
  - File: src/app/ai/availability_graph.py
  - Acceptance: No redundant graph compilation; callable from executor

### PR#4 — Executor + FastAPI Endpoint Integration
- [ ] Add execute_availability_graph_with_audit(...) to src/app/ai/graph_executor.py
  - File: src/app/ai/graph_executor.py
  - Acceptance: Executor runs graph, logs request_id/count/time, handles errors safely
- [ ] Add POST /api/agents/candidate-availability to FastAPI routes
  - File: src/app/main.py (or routers/)
  - Acceptance: Endpoint accepts payload, returns response, status codes per spec
- [ ] Add structured logging (request_id, count, exec time; no secrets)
  - File: src/app/ai/graph_executor.py, src/app/main.py
  - Acceptance: Logs contain required info, never secrets

### PR#5 — Tests + Developer Docs + Postman Examples
- [ ] Add pytest suite for all spec scenarios (NOT_FOUND, INACTIVE, BILLABLE_OVERLAP, ended-before-start, non-billable overlap, NULL end_date, NULL start_date, soft delete ignored, order/dedupe)
  - File: tests/test_candidate_availability.py
  - Acceptance: All scenarios covered, passing
- [ ] Add README/developer note: env vars, uvicorn run, Postman payloads
  - File: README.md or developer note
  - Acceptance: Instructions match plan, sample payloads included
- [ ] Confirm no DB migrations needed (unless spec changes DB)
  - Acceptance: No migration scripts added unless required

## Verification

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

## Postman Test Cases

### Sample Payload: Single Member
```json
{
  "requisition_duration_month": 3,
  "expected_start_date": "2026-02-15",
  "team_member_id": "EMP_8842"
}
```

### Sample Payload: Multiple Members
```json
{
  "requisition_duration_month": 3,
  "expected_start_date": "2026-02-15",
  "team_member_ids": ["EMP_8842", "EMP_1201", "EMP_7788"]
}
```

### Expected Key Fields in Response
- request_id (uuid)
- expected_start_date
- expected_end_date
- requisition_duration_month
- results (ordered, with available, reason_code, reason, conflicts[])
- summary (requested, available_count, unavailable_count, not_found_count)
- errors (empty array if no errors)
