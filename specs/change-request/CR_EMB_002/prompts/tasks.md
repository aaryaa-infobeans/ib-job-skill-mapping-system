/speckit.tasks

SYSTEM: Principal Delivery Breakdown Agent — convert the APPROVED CR-EMB-002 Implementation Plan into an atomic, traceable tasks.md. No code. No scope invention. Tasks only.

Source files:
- Plan: /specs/change-request/CR_EMB_002/plan.md
- Spec: /specs/change-request/CR_EMB_002/spec.md

CR: CR-EMB-002 v2.0.0 | Depends on: CR-PII-001 (HEAD bca284b2d901) | 17 days | AC-1..AC-15 | R1..R12

---

PHASE MAP (branch → days → AC → risks):

| Phase | Branch | Days | Key AC | Key Risks |
|-------|--------|------|--------|-----------|
| 0: MCP Server | feature/emb-phase0-mcp-server | 1–2 | AC-12, AC-13 | R8–R11 |
| 1: Schema & Model | feature/emb-phase1-schema-model | 3–5 | AC-4, AC-9 | R1, R5, R6 |
| 2: MCP Client & Pipeline | feature/emb-phase2-mcp-client-pipeline | 6–8 | AC-14, AC-15 | R9, R12 |
| 3: Cron Integration | feature/emb-phase3-cron-integration | 9–12 | AC-1, AC-5, AC-6, AC-11 | R2, R3, R7 |
| 4: RAG Multi-Vector | feature/emb-phase4-rag-multivector | 13–15 | AC-7, AC-8 | R1 |
| 5: Backfill & Validation | feature/emb-phase5-backfill-validation | 16–17 | AC-1..AC-3, AC-10 | R4, R8 |

---

KEY FILES:

New: src/mcp_servers/gdrive/server.py, config.py | src/app/ai/utils/gemma_embedding.py | src/app/cron/embedding/{mcp_client,text_assembler,embedding_processor}.py | alembic/versions/<rev>_add_multi_vector_embeddings.py | tests/{mcp_servers,cron,ai}/*.py | docs/runbooks/{mcp-server,embedding-pipeline}-troubleshooting.md

Modified: src/app/db/models/models.py (10 cols on TeamMemberEmbedding) | src/app/ai/utils/{embedding,rag_retrieval}.py | src/app/ai/agents/rag_retrieval.py | src/app/cron/{main,config}.py | src/app/cron/db/{repositories,migrations_check}.py | src/app/settings.py | requirements.txt

DB: table=team_member_embeddings, HEAD=bca284b2d901, migration adds 10 cols + 4 IVFFlat indexes

---

OUTPUT: /specs/change-request/CR_EMB_002/tasks.md

Structure each phase as:

## Phase N: <Name>
### Branch: feature/emb-phase<n>-<slug>
### Epic: <Epic Name>

#### TASK-EMB-NNN: <Imperative Title>
- **Description:** what to build/verify
- **Inputs:** deps, config, data
- **Outputs:** files/artifacts produced
- **Spec Refs:** Plan §X | CR §Y | AC-nn | R-nn
- **Acceptance Criteria:** testable condition with exact SQL/CLI where applicable
- **Definition of Done:** checkbox list
- **Dependencies:** TASK-EMB-xxx (if any)
- **Owner:** Backend | AI | Platform | QA | DevOps | Security
- **Type:** Build | Configure | Test | Validate | Document | Verify

Task IDs are sequential (TASK-EMB-001..NNN) across all phases.

---

EPICS PER PHASE:

Phase 0: Package Scaffold | Tool Implementation (read_document, search_files, get_file_metadata) | SA Auth & Config | Error Handling & Rate Limiting | Unit Tests | Phase Gate & Rollback
Phase 1: Alembic Migration | SQLAlchemy Model Update | GemmaEmbeddingAgent | Model Factory & Settings | Dependency Pinning | Unit Tests | Phase Gate & Rollback
Phase 2: MCP Client Wrapper (STDIO, session-per-batch) | Text Assembler | Cron Config Extension | Credential Isolation | Unit Tests | Phase Gate & Rollback
Phase 3: EmbeddingProcessor (SHA-256, per-member commit) | CLI Modes (embed/ingest-embed/--force) | upsert_team_member_embeddings() | Phase Isolation | Integration Tests | Phase Gate & Rollback
Phase 4: _query_vector_and_filter() routing | NULL fallback | Legacy embedding weighted avg | Regression Tests | Phase Gate & Rollback
Phase 5: Pre-backfill snapshot | DDL migration | embed --force run | Validation SQL (AC-1..AC-4) | Full pytest (AC-10) | Match quality comparison | Runbooks | Prod readiness checklist
Cross-Phase CI: spec traceability check | credential isolation scan | migration dry-run | perf regression guard | tools/list health check

---

REFLECTION GATES (include as explicit tasks at end of each phase):

- GATE-0 (end of Phase 0): tools/list returns 3 tools independently — AC-12 — blocks Phase 2
- GATE-1 (end of Phase 1): alembic roundtrip + 768-dim vector output — AC-9 — blocks Phase 3
- GATE-2 (end of Phase 3): hash skip ≥80% on 2nd run (AC-6) + PII scrubber verified (AC-5) — blocks Phase 4
- GATE-4 (end of Phase 4): match quality not regressed >5% vs baseline — R1 — blocks Phase 5
- GATE-5 (end of Phase 5): all tests green (AC-10) + prod readiness signed off

---

RISK GATES (include as blocking tasks; merge blocked if condition met):

| ID | Condition | Blocks |
|----|-----------|--------|
| RG-R1 | Match quality regression >5% | Phase 4 merge |
| RG-R3 | Throughput <100 members/min CPU | Phase 3 merge |
| RG-R6 | Gemma RSS >2GB | Phase 3 merge |
| RG-R9 | 3 consecutive MCP reconnect failures without graceful skip | Phase 2 merge |
| RG-R10 | tools/list missing any of 3 tools | Phase 0 merge |

---

ROLLBACK TASKS (one per phase):

- Phase 0: delete src/mcp_servers/; verify cron unaffected
- Phase 1: `alembic downgrade bca284b2d901`; verify 10 cols dropped, 7 original intact
- Phase 2: delete src/app/cron/embedding/; verify ingest/retry modes work
- Phase 3: revert main.py; `python -m app.cron.main ingest` succeeds; legacy embedding col untouched
- Phase 4: revert rag_retrieval.py; /matches returns results via single embedding col
- Phase 5: no rollback; document data preservation guarantee

---

RULES:
- Tasks atomic (1–3 days), single-branch, independently testable
- All AC-1..AC-15 and R1..R12 covered across tasks or risk gates
- Migration tasks reference down_revision='bca284b2d901' and include upgrade+downgrade
- Embedding tasks separate model loading from inference; include memory check (R6)
- Observability tasks reference exact metric names from plan §10 (non-optional)
- Validation tasks include exact SQL or CLI command

Output file: /specs/change-request/CR_EMB_002/tasks.md
