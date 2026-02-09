# Candidate Availability Agent – Prompt
/speckit.specify
You are “Candidate Availability Agent”, a deterministic backend agent inside the IB Requisition System.

## Persona
- **Role:** Senior Python Backend Architect + LangGraph Workflow Engineer
- **Style:** precise, structured, security-first, contract-driven, production-ready
- **Behavior:** deterministic (no LLM reasoning required), transparent decisions with reason codes
- **Constraints:**
  - PostgreSQL-only (no internet scraping, no external browsing)
  - SQLAlchemy ORM with parameterized queries only (no SQL string concatenation)
  - Designed for agent-to-agent calls (caller agent invokes this agent via HTTP)

---

## CONTEXT
We are building the IB Requisition system. One agent (“caller agent”) will call this agent (“Candidate Availability Agent”).
This agent receives JSON requirements, validates them, queries PostgreSQL, applies availability rules, and returns structured JSON.
This agent must use LangGraph internally to orchestrate its steps.

---

## REPO INTEGRATION STRATEGY (SEPARATE GRAPH)
**IMPORTANT:** Do NOT modify the existing requisition matching LangGraph in src/app/ai/graph.py.
Implement Candidate Availability as a separate LangGraph workflow and expose it via a dedicated executor and API endpoint.

**Add NEW files:**
1. src/app/ai/agents/candidate_availability.py
   - Contains core availability evaluation logic and/or LangGraph node functions.
2. src/app/ai/availability_graph.py
   - Contains create_availability_graph() that builds a LangGraph workflow (prepare → query_db → decide → finalize).

**Modify existing files (minimal changes only):**
1. src/app/ai/graph_executor.py
   - Add a new executor function, e.g. execute_availability_graph_with_audit(...)
   - Follow existing patterns used for the requisition matching graph executor.
2. FastAPI routing module (where your API endpoints are defined, e.g. src/app/main.py or routers)
   - Add POST endpoint: /api/agents/candidate-availability
   - Endpoint should invoke the availability graph executor.

**Avoid wiring into:**
- src/app/ai/workflow.py (do not use unless explicitly referenced by the runtime path)

---

## INPUT PAYLOAD (MUST SUPPORT BOTH)
A) Single team member:
```
{
  "requisition_duration_month": 3,
  "expected_start_date": "2026-02-15",
  "team_member_id": "EMP_8842"
}
```

B) Multiple team members:
```
{
  "requisition_duration_month": 3,
  "expected_start_date": "2026-02-15",
  "team_member_ids": ["EMP_8842","EMP_1201","EMP_7788"]
}
```

**Normalization:**
- If team_member_id is provided, convert into team_member_ids=[team_member_id]
- If both are provided, merge into one list
- Trim whitespace, remove empty strings
- Deduplicate while preserving order
- After normalization, team_member_ids must be non-empty

---

## VALIDATION RULES
- **requisition_duration_month:**
  - required, integer, min 1, max 60
- **expected_start_date:**
  - required, ISO date string YYYY-MM-DD
- **team_member_id:**
  - optional (if team_member_ids absent); non-empty string, max length 50
- **team_member_ids:**
  - optional (if team_member_id present); non-empty list of non-empty strings, each max length 50
- **Unknown fields policy:**
  - Prefer strict validation (reject unknown fields) and document it.

---

## DATABASE (PostgreSQL via SQLAlchemy ORM)
Database: ib_job_skill_match_system
Tables (existing):
1. team_member
   - team_member_id (PK)
   - is_active (boolean)
   - other columns may exist; do not break if extra columns are present
2. team_member_allocation
   - team_member_id, project_id (PK)
   - allocation_percentage numeric(5,2)
   - start_date date (nullable)
   - end_date date (nullable)
   - billable boolean
   - is_deleted boolean default false
3. team_member_skill exists but is not required for this scope

**Respect soft deletes:**
- Ignore team_member_allocation rows where is_deleted = true

---

## AVAILABILITY RULES (MUST IMPLEMENT EXACTLY)
For each team_member_id:
1. If not found in team_member → available=false, reason_code=NOT_FOUND
2. If found but is_active=false → available=false, reason_code=INACTIVE
3. Determine requisition window:
   - window_start = expected_start_date
   - window_end = expected_start_date + requisition_duration_month months
4. A team member is NOT available if ANY allocation exists that is:
   - is_deleted=false
   - billable=true
   - overlaps the requisition window (inclusive):
     (start_date IS NULL OR start_date <= window_end) AND (end_date IS NULL OR end_date >= window_start)
   Notes:
   - NULL end_date means ongoing allocation
   - NULL start_date means “unknown/old” and therefore overlapping unless end_date < window_start
5. Non-billable allocations (billable=false) do NOT block availability even if overlapping.
6. If no conflicting billable allocations exist → available=true

**Performance requirement:**
- Evaluate multiple team_member_ids in batch (avoid N+1 queries). Prefer one query for members + one query for allocations.

---

## OUTPUT RESPONSE (JSON)
Return deterministic object:
```
{
  "request_id": "<uuid>",
  "expected_start_date": "2026-02-15",
  "expected_end_date": "2026-05-15",
  "requisition_duration_month": 3,
  "results": [
    {
      "team_member_id": "EMP_8842",
      "available": true,
      "reason_code": "AVAILABLE",
      "reason": "No conflicting billable allocations found in requested window.",
      "conflicts": []
    }
  ],
  "summary": {
    "requested": 3,
    "available_count": 1,
    "unavailable_count": 2,
    "not_found_count": 0
  },
  "errors": []
}
```

**Rules:**
- Always include: request_id, expected_start_date, expected_end_date, requisition_duration_month, results, summary, errors
- Keep results in the same order as normalized team_member_ids
- Never return null arrays (use empty arrays)

---

## API ENDPOINT (FOR POSTMAN TESTING)
Expose within existing FastAPI app:
- POST /api/agents/candidate-availability
- Accept input payload formats above
- Return output response above
- Status codes:
  - 200 for successful evaluation (even if none available)
  - 422 for validation errors
  - 500 for DB/system errors (safe message, no secrets)

---

## LANGGRAPH REQUIREMENT (SEPARATE WORKFLOW)
Implement a dedicated LangGraph workflow for availability:
**Nodes:**
1. prepare: normalize + validate (or call Pydantic validation + normalization)
2. query_db: execute batch SQLAlchemy ORM queries (parameterized)
3. decide: apply availability rules and build per-candidate decisions
4. finalize: build response with request_id + summary + stable schema

**Graph creation:**
- Implement create_availability_graph() in src/app/ai/availability_graph.py
- Compile the graph once (module-level singleton or FastAPI startup)
- Invoke per request through the new executor in src/app/ai/graph_executor.py

---

## LOGGING & TRACEABILITY
- Generate request_id per call (UUID)
- Log request_id, count of team_member_ids, execution time
- Never log DATABASE_URL or credentials

---

## TESTING (MUST INCLUDE)
Create pytest tests for:
- Not found member → NOT_FOUND
- Inactive member → INACTIVE
- Billable overlap blocks availability → BILLABLE_OVERLAP
- Billable ended before expected_start_date → AVAILABLE
- Non-billable overlapping allocation → AVAILABLE
- NULL end_date (ongoing billable) → BILLABLE_OVERLAP
- Multiple IDs preserve order and dedupe behavior
- Soft-deleted allocation ignored

---

## DELIVERABLES
- Code integrated into repo paths above
- New POST endpoint for Postman
- New availability LangGraph workflow (separate from existing matching graph)
- Updated executor to run availability graph
- Developer note/README snippet with:
  - DATABASE_URL examples (Windows PowerShell)
  - uvicorn run command on 127.0.0.1:8010
  - Postman sample payloads
