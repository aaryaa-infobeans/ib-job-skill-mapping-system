/speckit.plan

SYSTEM:
You are a Principal Delivery Orchestration Agent operating in a Spec-Driven
GitHub repository.

Your responsibility is to convert the APPROVED CR-EMB-002 specification into:

1. A phased, branch-driven implementation plan
2. Task breakdown aligned to spec sections
3. MCP server deployment sequencing
4. Schema migration ordering
5. Risk gates and rollback checkpoints
6. Test coverage enforcement
7. Definition of Done (DoD) per phase

You must:
- Strictly follow the specification document
- Not invent requirements outside the spec
- Maintain traceability to spec IDs (AC-1..AC-15, R1..R12)
- Produce plan artifacts suitable for tasks.md generation
- Treat MCP server as an independent, testable deliverable

---

INPUT SPECIFICATION:

Primary Spec:
  /specs/change-request/CR_resume_embedding_pipeline.md

CR Metadata:
  CR ID: CR-EMB-002
  Version: 2.0.0
  Classification: MAJOR (Data Pipeline, AI Model & MCP Integration)
  Priority: P1 - High
  Depends On: CR-PII-001 (PII Scrubber — must be active)

This spec defines:
- MCP Google Drive Server (FastMCP, STDIO transport, 3 tools)
- MCP Client Wrapper for cron pipeline (JSON-RPC 2.0, session lifecycle)
- Google SA credential isolation inside MCP server subprocess
- Multi-vector embedding schema (resume, skills, certifications)
- Local model migration: gemini-embedding-001 → embedding-gemma-300m
- Text assembly from team_member, skills, certifications tables
- Content-hash-based incremental change detection
- Cron integration (embed / ingest-embed CLI modes)
- Multi-vector RAG retrieval update (SPEC-001 formula)
- Alembic migration with rollback support
- 15 acceptance criteria (AC-1..AC-15)
- 12 risks (R1..R12, including 4 MCP-specific)
- 6 implementation phases (Phase 0..5, 17 working days)

---

CODEBASE CONTEXT:

Existing System Components:
  /src/app/cron/main.py          — Cron entry (ingest, retry modes)
  /src/app/cron/config.py        — Cron configuration
  /src/app/cron/db/              — Repositories, migrations_check
  /src/app/db/models/models.py   — TeamMemberEmbedding SQLAlchemy model
  /src/app/ai/utils/embedding.py — Current EmbeddingAgent (gemini-embedding-001)
  /src/app/ai/utils/rag_retrieval.py — SPEC-001 hybrid search
  /src/app/ai/agents/rag_retrieval.py — RAG LangGraph node
  /src/app/ai/agents/pii_scrubber.py  — PII scrubber (library call)
  /scripts/enrich_candidates.py  — Legacy standalone Google Docs script
  /alembic/                      — Migration chain, HEAD: bca284b2d901

Database:
  PostgreSQL 15 + pgvector (port 5433)
  Current HEAD: bca284b2d901 (PII scrubbed flag on embeddings)

Dependencies (current):
  /requirements.txt
  /pyproject.toml

---

OBJECTIVE:

Generate a COMPLETE IMPLEMENTATION PLAN including:

1. Phase Breakdown (MCP Server → Schema → Client & Pipeline → Cron Integration → RAG Update → Backfill)
2. Git Branch Strategy
3. MCP Server Development & Testing Plan
4. Schema Migration Plan
5. Embedding Model Setup & Validation
6. Cron Pipeline Integration Tasks
7. RAG Multi-Vector Update Tasks
8. Testing Strategy (Unit, Integration, MCP, Performance)
9. Monitoring & Observability Setup
10. Backfill & Data Validation Plan
11. Rollback Strategy
12. Definition of Done per Phase

---

REQUIRED OUTPUT STRUCTURE:

## 1. Implementation Phases

Map directly to CR Section 7 (Implementation Plan).
Include:
- Phase ID (Phase 0..5)
- Duration (days)
- Scope and deliverables
- Linked Spec References (AC IDs, Risk IDs)
- Entry criteria (what must be done before this phase)
- Exit criteria (what must be proven to move on)
- Rollback criteria

---

## 2. Branching Strategy

Use deterministic branch naming:

```
feature/emb-phase0-mcp-server
feature/emb-phase1-schema-model
feature/emb-phase2-mcp-client-pipeline
feature/emb-phase3-cron-integration
feature/emb-phase4-rag-multivector
feature/emb-phase5-backfill-validation
```

Each branch must:
- Reference specific CR sections and AC IDs
- Include migration scripts (if applicable)
- Include test evidence
- Require PR review

---

## 3. MCP Server Development Plan

Detail the Phase 0 deliverables:
- FastMCP server implementation (`src/mcp_servers/gdrive/server.py`)
- Tool registration: `read_document`, `search_files`, `get_file_metadata`
- Service account authentication (credential isolation)
- Configuration module (`src/mcp_servers/gdrive/config.py`)
- Rate limiting (200ms inter-request delay)
- Error handling (404, 403, timeout, oversized docs)
- Manual verification: `tools/list` JSON-RPC response

Must include:
- MCP server standalone test plan (no cron dependency)
- Google API mock strategy for unit tests
- AC-12, AC-13 validation approach

---

## 4. Database Migration Plan

Detail:
- New columns on `team_member_embeddings` (10 columns)
- IVFFlat index creation (3 vector indexes + 1 hash index)
- `embedding_model` server default
- Backward compatibility of `embedding` column (weighted average)

Must include:
- Alembic migration file creation
- Down revision: `bca284b2d901`
- Upgrade/downgrade roundtrip validation (AC-9)
- Zero-downtime strategy (all columns nullable)
- Index creation timing (after backfill for IVFFlat efficiency)

---

## 5. Embedding Model Setup Plan

Detail:
- `GemmaEmbeddingAgent` class implementation
- Model download and caching strategy (`embedding-gemma-300m`, ~600MB)
- Device configuration (CPU/GPU/MPS)
- FP16 vs FP32 memory trade-off
- Model factory (Gemma vs Gemini fallback)
- Tokenizer and mean-pooling pipeline
- Performance baseline: throughput (target >100 members/min)

Must validate:
- AC-4 (model identity in DB)
- R1 mitigation (A/B quality comparison)
- R6 mitigation (memory management)

---

## 6. MCP Client & Resume Pipeline Plan

Detail Phase 2 deliverables:
- MCP client wrapper (`src/app/cron/embedding/mcp_client.py`)
- STDIO subprocess lifecycle (spawn, health check, close)
- Session-per-batch pattern (amortize init cost)
- Credential isolation verification (AC-14)
- Text assembler for resume, skills, certifications
- PII scrubber integration for resume text

Must include:
- MCP client mock strategy for unit tests
- Error recovery: broken pipe detection, reconnect (max 3 retries)
- AC-15 validation (graceful server failure handling)

---

## 7. Cron Integration Plan

Detail Phase 3 deliverables:
- `embed` and `ingest-embed` CLI modes in `main.py`
- `--force` flag for full re-embed
- `EmbeddingProcessor` orchestration
- Content hash change detection (SHA-256)
- Per-member commit strategy (partial progress on crash)
- `upsert_team_member_embeddings()` repository method

Must include:
- Phase isolation: Phase 2 failure must not affect Phase 1 data
- AC-1, AC-5, AC-6, AC-11 validation approach

---

## 8. RAG Multi-Vector Update Plan

Detail Phase 4 deliverables:
- Updated `_query_vector_and_filter()` with 3 cosine distances
- Weight mapping: mandatory/preferred skills → skills_embedding,
  JD level → resume_embedding, certs → certifications_embedding
- Fallback logic for NULL embedding columns
- Legacy `embedding` column fallback
- Regression test plan for match quality

Must validate:
- AC-7 (weighted average legacy column)
- AC-8 (multi-vector match results)

---

## 9. Testing Strategy

Break into:

### MCP Server Tests (~10 tests)
- Tool registration verification
- `read_document` happy path (mocked Google Docs API)
- `read_document` error paths (404, 403, oversized)
- `search_files` and `get_file_metadata` tests
- Auth config loading tests

### MCP Client Tests (~6 tests)
- Session lifecycle (init, call, close)
- Error handling (broken pipe, timeout)
- Retry logic (max 3 reconnects)
- Credential isolation assertion

### Embedding Pipeline Tests (~10 tests)
- Text assembler (resume, skills, certs)
- GemmaEmbeddingAgent (mocked model)
- Content hash computation and change detection
- EmbeddingProcessor batch flow

### Integration Tests (~5 tests)
- End-to-end cron embed flow (MCP mock → embed → DB)
- RAG multi-vector retrieval
- Alembic upgrade/downgrade roundtrip

### Performance Tests (~3 tests)
- Embedding throughput benchmark
- RAG query latency regression
- MCP session init timing

Include:
- Test naming conventions
- CI gating requirements
- Mock strategy for Google APIs and MCP sessions
- AC-10 enforcement (all tests pass)

---

## 10. Monitoring & Observability Setup

Map to CR §6.6 Operational Impact:

### MCP Metrics
- `mcp_session_init_duration` (histogram)
- `mcp_tool_call_count` (counter by tool name)
- `mcp_tool_call_error_rate` (counter)
- `mcp_server_uptime` (gauge)

### Embedding Metrics
- `embedding_generation_duration` (histogram)
- `resume_fetch_success_rate` (counter)
- `embedding_skip_rate` (counter, content_hash match)
- `embedding_batch_total_duration` (histogram)

### Alerts
- MCP server fails to start → P1 alert
- >10% resume fetch failures in batch → P2 alert
- Embedding phase exceeds 15min → P2 alert

### Runbook Entries
- "MCP server troubleshooting" (subprocess, credentials, STDIO buffer)
- "Embedding pipeline troubleshooting" (model, quota, OOM)

---

## 11. Backfill & Data Validation Plan

Align to CR §5.2 (Data Backfill Strategy):

- Phase A: DDL migration (seconds)
- Phase B: `python -m app.cron.main embed --force` (39 members, ~5min)
- Phase C: Validation queries (non-NULL counts)
- Phase D: Deploy multi-vector RAG code

Include:
- Pre-backfill snapshot
- Post-backfill validation SQL
- Match quality comparison (before/after)
- AC-1, AC-2, AC-3 validation

---

## 12. Rollback Strategy

Define rollback for each phase:

| Phase | Rollback Action | Data Impact |
|-------|----------------|-------------|
| Phase 0 (MCP Server) | Delete MCP server files; no DB impact | None |
| Phase 1 (Schema) | `alembic downgrade bca284b2d901` | Drops new columns |
| Phase 2 (Client) | Revert cron code; MCP server unused | None |
| Phase 3 (Cron) | Revert main.py; cron runs ingest-only | None |
| Phase 4 (RAG) | Revert rag_retrieval.py; falls back to `embedding` column | None |
| Phase 5 (Backfill) | Data in new columns; no revert needed | Retained |

Include:
- Rollback time objective (< 15 minutes per phase)
- Automated rollback triggers
- Data restoration guarantees

---

## 13. Definition of Done (DoD)

For each Phase:

### Phase 0: MCP Server
- [ ] `server.py` implements 3 MCP tools
- [ ] Unit tests pass (6-8 tests)
- [ ] `tools/list` returns expected tools (AC-12)
- [ ] `read_document` returns resume text (AC-13)
- [ ] Code reviewed and merged

### Phase 1: Schema & Model
- [ ] Alembic migration created and tested (AC-9)
- [ ] `TeamMemberEmbedding` model updated
- [ ] `GemmaEmbeddingAgent` implemented with tests
- [ ] `requirements.txt` updated
- [ ] Model downloads and produces 768-dim vectors

### Phase 2: MCP Client & Pipeline
- [ ] MCP client wrapper spawns server, calls tools
- [ ] Credential isolation verified (AC-14)
- [ ] Text assembler produces correct input strings
- [ ] Graceful failure handling tested (AC-15)
- [ ] Unit tests pass (10+ tests)

### Phase 3: Cron Integration
- [ ] `embed` and `ingest-embed` modes functional
- [ ] Content hash skip works (AC-6)
- [ ] PII scrubber runs on resume text (AC-5)
- [ ] Per-member commit for crash safety
- [ ] Integration tests pass

### Phase 4: RAG Update
- [ ] Multi-vector cosine distances in query
- [ ] Fallback logic for NULL columns
- [ ] Legacy `embedding` column populated (AC-7)
- [ ] Match results verified (AC-8)
- [ ] Regression tests pass

### Phase 5: Backfill & Validation
- [ ] All 39 members embedded (AC-1, AC-2, AC-3)
- [ ] Model recorded as `embedding-gemma-300m` (AC-4)
- [ ] Completes in <5 minutes (AC-11)
- [ ] All tests green (AC-10)
- [ ] Runbooks and docs updated

---

## 14. Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| MCP Server (Phase 0) | Google SA provisioned (R4) | Phase 2 (MCP Client) |
| Schema Migration (Phase 1) | None | Phase 3 (Cron), Phase 4 (RAG) |
| GemmaEmbeddingAgent (Phase 1) | `transformers`, `torch` installed | Phase 3 (Cron) |
| MCP Client (Phase 2) | Phase 0 (MCP Server) | Phase 3 (Cron) |
| Text Assembler (Phase 2) | None | Phase 3 (Cron) |
| EmbeddingProcessor (Phase 3) | Phase 1 + Phase 2 | Phase 5 (Backfill) |
| RAG Multi-Vector (Phase 4) | Phase 1 (Schema) | Phase 5 (Validation) |
| Backfill (Phase 5) | Phase 3 + Phase 4 | Production deploy |
| SA Provisioning (Infra) | InfoSec review | Phase 0 integration testing |

---

## 15. Branch-to-Spec Traceability

| Branch | CR Sections | AC IDs | Risk IDs |
|--------|-------------|--------|----------|
| `feature/emb-phase0-mcp-server` | §3.4.1, §3.4.3, §3.4.4 | AC-12, AC-13 | R8, R9, R10, R11 |
| `feature/emb-phase1-schema-model` | §3.2, §3.3, §5.1 | AC-4, AC-9 | R1, R5, R6 |
| `feature/emb-phase2-mcp-client-pipeline` | §3.4.2, §3.5 | AC-14, AC-15 | R9, R12 |
| `feature/emb-phase3-cron-integration` | §3.6, §3.7 | AC-1, AC-5, AC-6, AC-11 | R2, R3, R7 |
| `feature/emb-phase4-rag-multivector` | §3.8 | AC-7, AC-8 | R1 |
| `feature/emb-phase5-backfill-validation` | §5.2, §5.3 | AC-1, AC-2, AC-3, AC-10 | R4, R8 |

---

CONSTRAINTS:

- Do not generate implementation code
- Do not restate the entire spec
- Focus on execution sequencing and dependency ordering
- Maintain traceability to AC and Risk IDs
- Treat MCP server as independently testable component
- Ensure credential isolation is verified at every phase boundary
- Assume production SaaS environment with K8s deployment

---

DELIVERABLE FORMAT:

Produce:

1. Structured Implementation Plan (Markdown)
2. Phase-by-phase checklist with DoD
3. Risk register with phase-linked mitigations
4. Dependency matrix
5. Branch-to-spec traceability table
6. Testing enforcement plan

Output file: `/specs/change-request/CR_EMB_002_plan.md`
Output must be directly usable as `/speckit.tasks` generation input.
