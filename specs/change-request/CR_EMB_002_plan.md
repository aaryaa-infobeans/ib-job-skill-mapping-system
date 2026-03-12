# CR-EMB-002 Implementation Plan

**Plan Version:** 1.0.0  
**CR ID:** CR-EMB-002  
**CR Version:** 2.0.0  
**Generated:** 2026-03-09  
**Status:** APPROVED FOR EXECUTION  
**Depends On:** CR-PII-001 (active, HEAD `bca284b2d901` confirmed)  
**Output:** Suitable for `/speckit.tasks` generation input

---

## Table of Contents

1. [Implementation Phases](#1-implementation-phases)
2. [Branching Strategy](#2-branching-strategy)
3. [MCP Server Development Plan](#3-mcp-server-development-plan)
4. [Database Migration Plan](#4-database-migration-plan)
5. [Embedding Model Setup Plan](#5-embedding-model-setup-plan)
6. [MCP Client & Resume Pipeline Plan](#6-mcp-client--resume-pipeline-plan)
7. [Cron Integration Plan](#7-cron-integration-plan)
8. [RAG Multi-Vector Update Plan](#8-rag-multi-vector-update-plan)
9. [Testing Strategy](#9-testing-strategy)
10. [Monitoring & Observability Setup](#10-monitoring--observability-setup)
11. [Backfill & Data Validation Plan](#11-backfill--data-validation-plan)
12. [Rollback Strategy](#12-rollback-strategy)
13. [Definition of Done (DoD)](#13-definition-of-done-dod)
14. [Dependency Matrix](#14-dependency-matrix)
15. [Branch-to-Spec Traceability](#15-branch-to-spec-traceability)

---

## 1. Implementation Phases

Six phases derived directly from CR §7.1. Total duration: **17 working days**.

---

### Phase 0 — MCP Google Drive Server

| Attribute       | Value                                           |
|-----------------|-------------------------------------------------|
| **Branch**      | `feature/emb-phase0-mcp-server`                |
| **Duration**    | Days 1–2 (2 days)                              |
| **Spec Ref**    | CR §3.4.1, §3.4.3, §3.4.4                     |
| **AC IDs**      | AC-12, AC-13                                   |
| **Risk IDs**    | R8, R9, R10, R11                               |

**Scope:**  
Create the standalone MCP Google Drive server (`FastMCP`, STDIO transport) with 3 registered tools: `read_document`, `search_files`, `get_file_metadata`. Google Service Account authentication is loaded **only inside this process**. The cron pipeline must never see the SA key.

**Deliverables:**
- `src/mcp_servers/__init__.py` (package root)
- `src/mcp_servers/gdrive/__init__.py`
- `src/mcp_servers/gdrive/server.py` (~180 lines) — FastMCP server, 3 tools, SA auth
- `src/mcp_servers/gdrive/config.py` (~40 lines) — SA path, scopes, rate limit, max doc size
- `tests/mcp_servers/test_gdrive_server.py` (~150 lines) — unit tests, mocked Google API

**Entry Criteria:**
- CR-PII-001 is merged and active (`bca284b2d901` is HEAD in target branch)
- Google SA provisioning request submitted (R4 mitigation — start in parallel)
- `mcp[cli]` version confirmed compatible with Python 3.13
- `google-api-python-client` and `google-auth` pinned versions identified

**Exit Criteria:**
- `python -m src.mcp_servers.gdrive.server` starts without error
- `tools/list` JSON-RPC call returns exactly: `read_document`, `search_files`, `get_file_metadata` (AC-12)
- `read_document` called with a valid Google Doc URL returns non-empty `text` field in test harness (AC-13 — requires SA provisioned; else mocked in unit tests)
- All 6–8 unit tests pass against mocked Google APIs
- Code reviewed and merged to `feature/emb-phase0-mcp-server`

**Rollback Criteria:**
- Delete `src/mcp_servers/` directory tree
- No DB changes — zero-risk rollback
- Required if: server fails to respond to `tools/list` after 3 restart attempts, or SA credential loading causes security audit failure

---

### Phase 1 — Schema & Embedding Model

| Attribute       | Value                                             |
|-----------------|---------------------------------------------------|
| **Branch**      | `feature/emb-phase1-schema-model`                |
| **Duration**    | Days 3–5 (3 days)                                |
| **Spec Ref**    | CR §3.2, §3.3, §5.1                             |
| **AC IDs**      | AC-4, AC-9                                        |
| **Risk IDs**    | R1, R5, R6                                       |

**Scope:**  
Apply Alembic schema migration adding 10 columns and 4 indexes to `team_member_embeddings`. Update the `TeamMemberEmbedding` SQLAlchemy model at `src/app/db/models/models.py` (currently at line 287). Implement `GemmaEmbeddingAgent` as a new class at `src/app/ai/utils/gemma_embedding.py`.

**Deliverables:**
- `alembic/versions/<rev_id>_add_multi_vector_embeddings.py` — upgrade/downgrade, `down_revision='bca284b2d901'`
- `src/app/db/models/models.py` — 10 new columns on `TeamMemberEmbedding` (all nullable except `embedding_model` default)
- `src/app/ai/utils/gemma_embedding.py` (~130 lines) — `GemmaEmbeddingAgent`, mean-pooling, L2-normalize, FP16/FP32
- `src/app/ai/utils/embedding.py` — model factory method `get_embedding_agent()` (Gemma vs Gemini fallback)
- `src/app/settings.py` — add `embedding_model_name`, `gemma_model_path`, `embedding_device`, `mcp_gdrive_server_path`
- `src/app/cron/db/migrations_check.py` — add new Alembic revision ID to `ACCEPTABLE_REVISIONS` set
- `requirements.txt` — add `transformers>=4.40`, `torch` (CPU), `sentencepiece>=0.2.0`, `mcp[cli]>=1.0`, `google-auth>=2.28`, `google-api-python-client>=2.120`
- `tests/ai/test_gemma_embedding.py` (~100 lines) — unit tests with mocked `AutoModel`

**Entry Criteria:**
- Phase 0 branch merged (or running in parallel — schema is independent)
- `requirements.txt` dependency versions identified and pinned
- Staging DB has `bca284b2d901` as HEAD (confirmed before migration)
- `torch` CPU-only variant install size verified (~200MB acceptable)

**Exit Criteria:**
- `alembic upgrade head` completes without error on staging DB
- `alembic downgrade bca284b2d901` drops all 10 new columns and 4 indexes cleanly (AC-9)
- `alembic upgrade head` again succeeds (full roundtrip)
- `SELECT column_name FROM information_schema.columns WHERE table_name = 'team_member_embeddings'` shows all 10 new columns
- `GemmaEmbeddingAgent().embed_text("test")` returns `ndarray` of shape `(768,)` with unit L2 norm
- Model recorded as `'embedding-gemma-300m'` in `embedding_model` column (AC-4)
- `ACCEPTABLE_REVISIONS` set updated with new revision ID
- Unit tests pass (≥5 tests for Gemma agent)

**Rollback Criteria:**
- `alembic downgrade bca284b2d901` — drops all new columns; existing data unaffected
- Revert `models.py`, `settings.py`, `migrations_check.py` to pre-phase state
- Required if: migration fails on staging, or `torch` memory footprint (R6) exceeds host budget

---

### Phase 2 — MCP Client & Resume Pipeline

| Attribute       | Value                                                  |
|-----------------|--------------------------------------------------------|
| **Branch**      | `feature/emb-phase2-mcp-client-pipeline`              |
| **Duration**    | Days 6–8 (3 days)                                     |
| **Spec Ref**    | CR §3.4.2, §3.5                                      |
| **AC IDs**      | AC-14, AC-15                                          |
| **Risk IDs**    | R9, R12                                               |

**Scope:**  
Implement the MCP client wrapper that spawns the Phase 0 server as a STDIO child process and manages its session lifecycle. Implement text assemblers for resume, skills, and certifications text. Extend `src/app/cron/config.py` with MCP/embedding settings. Google SA credentials must **not** be present in the cron process environment (AC-14).

**Deliverables:**
- `src/app/cron/embedding/__init__.py`
- `src/app/cron/embedding/mcp_client.py` (~120 lines) — `MCPResumeClient`, STDIO spawn, `fetch_resume_sync()`, broken-pipe recovery (max 3 reconnects)
- `src/app/cron/embedding/text_assembler.py` (~120 lines) — `assemble_resume_text()`, `assemble_skills_text()`, `assemble_certifications_text()`
- `src/app/cron/config.py` — add: `embedding_model`, `mcp_server_script`, `mcp_server_env`, `embedding_batch_size`, `force_re_embed`
- `tests/cron/test_mcp_client.py` (~120 lines) — session lifecycle, error recovery, credential isolation assertion
- `tests/cron/test_text_assembler.py` (~150 lines) — all three assembler functions

**Entry Criteria:**
- Phase 0 merged (MCP server `server.py` available at `src/mcp_servers/gdrive/server.py`)
- `mcp[cli]` installed in venv
- DB model updated (Phase 1) so text assembler queries reflect current schema

**Exit Criteria:**
- `MCPResumeClient` spawns server subprocess without error (tested with Phase 0 server)
- `fetch_resume_sync()` returns non-empty string for a mocked MCP session
- Credential isolation verified: `GOOGLE_SERVICE_ACCOUNT_FILE` is **absent** from cron process `os.environ` (AC-14)
- MCP server crash during fetch: cron logs error, skips member, completes remaining work (AC-15)
- Broken pipe triggers reconnect up to 3 times, then graceful skip (R9)
- All unit tests pass (≥10 tests across client + assembler)

**Rollback Criteria:**
- Delete `src/app/cron/embedding/` package directory
- Revert `src/app/cron/config.py` to pre-phase state
- No DB impact — zero-risk rollback
- Required if: STDIO subprocess management causes cron instability, or MCP session overhead (R12) measured >5s/member

---

### Phase 3 — Cron Integration

| Attribute       | Value                                                     |
|-----------------|-----------------------------------------------------------|
| **Branch**      | `feature/emb-phase3-cron-integration`                    |
| **Duration**    | Days 9–12 (4 days)                                       |
| **Spec Ref**    | CR §3.6, §3.7                                            |
| **AC IDs**      | AC-1, AC-5, AC-6, AC-11                                  |
| **Risk IDs**    | R2, R3, R7                                               |

**Scope:**  
Wire Phase 1 (schema/model) and Phase 2 (client/assembler) into the existing cron runner at `src/app/cron/main.py` (currently 461 lines, modes: `ingest`, `retry`). Add `embed` and `ingest-embed` modes. Add `--force` flag. Implement `EmbeddingProcessor` with SHA-256 content-hash change detection and per-member commit strategy.

**Deliverables:**
- `src/app/cron/embedding/embedding_processor.py` (~200 lines) — `EmbeddingProcessor`, content hash, PII scrub call, per-member commit, batch orchestration
- `src/app/cron/main.py` — `embed` and `ingest-embed` CLI modes added to argparse; MCP server subprocess init/teardown per run
- `src/app/cron/db/repositories.py` — `upsert_team_member_embeddings()` method for multi-vector UPSERT
- `tests/cron/test_embedding_processor.py` (~200 lines) — batch flow, hash skip logic, PII scrub integration

**Entry Criteria:**
- Phase 1 merged: `TeamMemberEmbedding` model has 10 new columns; `GemmaEmbeddingAgent` available
- Phase 2 merged: `MCPResumeClient` and `text_assembler` modules available
- Schema migration applied to target DB (`alembic upgrade head`)
- `ACCEPTABLE_REVISIONS` includes new migration revision ID

**Exit Criteria:**
- `python -m app.cron.main embed` runs without error against staging DB
- `python -m app.cron.main ingest-embed` runs Phase 1 (ingest) then Phase 2 (embed) sequentially
- `python -m app.cron.main embed --force` re-embeds all members regardless of content hash
- On second run (no changes), `embedding_skip_rate` shows all members skipped (AC-6)
- `resume_text` column contains no raw PII patterns (manual inspection) (AC-5)
- Embedding phase for 39 members completes in <5 minutes (AC-11)
- MCP server crash during Phase 3 does NOT corrupt Phase 1 (ingestion) data — verified via separate DB transaction isolation
- Integration tests pass (≥5 tests)
- `SELECT count(*) FROM team_member_embeddings WHERE resume_embedding IS NOT NULL` returns expected count (partial AC-1)

**Rollback Criteria:**
- Revert `src/app/cron/main.py` to pre-phase argparse state
- Revert `src/app/cron/db/repositories.py`
- Delete `src/app/cron/embedding/embedding_processor.py`
- No DB data loss — `embedding` and `profile_text` columns are never modified by Phase 3
- Required if: embedding phase causes cron duration to exceed 30-min SLA (R3), or OOM from Gemma model load (R6)

---

### Phase 4 — RAG Multi-Vector Update

| Attribute       | Value                                          |
|-----------------|------------------------------------------------|
| **Branch**      | `feature/emb-phase4-rag-multivector`          |
| **Duration**    | Days 13–15 (3 days)                           |
| **Spec Ref**    | CR §3.8                                       |
| **AC IDs**      | AC-7, AC-8                                    |
| **Risk IDs**    | R1                                            |

**Scope:**  
Update `_query_vector_and_filter()` in `src/app/ai/utils/rag_retrieval.py` (currently uses single `TeamMemberEmbedding.embedding` column for ALL cosine distances: `mandatory_sim`, `preferred_sim`, `jd_level_sim`, `cert_sim`). Switch to multi-vector: `skills_embedding` for mandatory/preferred, `resume_embedding` for JD level, `certifications_embedding` for certifications. Add NULL fallback to legacy `embedding` column. Maintain legacy `embedding` column as weighted average (AC-7).

**Deliverables:**
- `src/app/ai/utils/rag_retrieval.py` — updated `_query_vector_and_filter()` with 3 cosine distances and NULL-fallback logic
- `src/app/ai/agents/rag_retrieval.py` — pass multi-vector column data through `GraphState` (low-impact change)
- `tests/ai/test_rag_retrieval.py` — regression tests for match quality (before/after comparison on test requisitions)

**Entry Criteria:**
- Phase 1 merged (schema columns exist)
- Phase 3 merged (at least some team members have non-NULL `skills_embedding`, `resume_embedding`, `certifications_embedding`)
- Baseline match quality score recorded for at least 2 test requisitions (for R1 A/B comparison)

**Exit Criteria:**
- `_query_vector_and_filter()` queries `skills_embedding` for mandatory skills cosine distance
- `_query_vector_and_filter()` queries `resume_embedding` for JD level cosine distance
- `_query_vector_and_filter()` queries `certifications_embedding` for cert cosine distance
- All three fallback to `embedding` column when respective column is NULL
- Legacy `embedding` column in DB equals `normalize(0.50 * resume + 0.30 * skills + 0.20 * certs)` — spot-checked for 5 members (AC-7)
- Test requisition returns candidates via `/api/v1/jd-skill-mapping/{id}/matches` endpoint (AC-8)
- RAG query latency ≤65ms (P50) — measured in performance test
- Regression tests pass (≥5 tests including 2 multi-vector path, 1 fallback path, 2 NULL path)

**Rollback Criteria:**
- Revert `src/app/ai/utils/rag_retrieval.py` to pre-phase state (single `embedding` column)
- Revert `src/app/ai/agents/rag_retrieval.py`
- No DB changes — zero-risk rollback
- Required if: match quality degrades >5% vs baseline A/B comparison (R1)

---

### Phase 5 — Backfill & Validation

| Attribute       | Value                                                      |
|-----------------|------------------------------------------------------------|
| **Branch**      | `feature/emb-phase5-backfill-validation`                  |
| **Duration**    | Days 16–17 (2 days)                                       |
| **Spec Ref**    | CR §5.2, §5.3                                            |
| **AC IDs**      | AC-1, AC-2, AC-3, AC-10                                   |
| **Risk IDs**    | R4, R8                                                    |

**Scope:**  
Execute full backfill of all 39 existing team members with `profile_url` set. Validate non-NULL embedding counts. Run end-to-end match quality comparison. Execute full test suite.

**Deliverables:**
- Backfill execution log (stdout capture of `embed --force` run)
- Validation SQL results (pre/post counts)
- Performance benchmark results (throughput + RAG latency)
- Updated runbook entries (2 new sections in `docs/runbooks/`)
- Dependency update: `docs/` phase completion report

**Entry Criteria:**
- All Phases 0–4 merged and deployed to staging
- Google SA provisioned (R4) and `GOOGLE_SERVICE_ACCOUNT_FILE` available in cron environment
- All prior phase DoD checklists signed off
- Baseline match results for test requisitions recorded (for comparison)

**Exit Criteria:**
- `SELECT count(*) FROM team_member_embeddings WHERE resume_embedding IS NOT NULL` ≥ number of members with `profile_url` (AC-1)
- `SELECT count(*) FROM team_member_embeddings WHERE skills_embedding IS NOT NULL` ≥ number of members with ≥1 skill (AC-2)
- `SELECT count(*) FROM team_member_embeddings WHERE certifications_embedding IS NOT NULL` ≥ number of members with ≥1 cert (AC-3)
- `SELECT DISTINCT embedding_model FROM team_member_embeddings` returns only `'embedding-gemma-300m'` (AC-4)
- `pytest tests/ -v` exits with code 0 (AC-10)
- Backfill of 39 members completes in <5 minutes (AC-11)
- Match quality for test requisitions is equal or improved vs baseline (R1 final validation)
- Members without `profile_url` are gracefully skipped (R8 validation)

**Rollback Criteria:**
- No rollback needed — backfill only writes to new nullable columns
- Multi-vector RAG can be toggled off via Phase 4 rollback without losing backfill data
- Data in new columns is preserved indefinitely unless `alembic downgrade` is explicitly run

---

## 2. Branching Strategy

### Branch Names

```
feature/emb-phase0-mcp-server
feature/emb-phase1-schema-model
feature/emb-phase2-mcp-client-pipeline
feature/emb-phase3-cron-integration
feature/emb-phase4-rag-multivector
feature/emb-phase5-backfill-validation
```

All branches fork from `main` (or current integration branch). Merges require PR review.

### Branch Requirements

Each branch **must** include before PR approval:

| Branch | Migration Script | Test Evidence Required | CR Sections | AC IDs |
|--------|-----------------|------------------------|-------------|--------|
| `feature/emb-phase0-mcp-server` | None | `test_gdrive_server.py` all green | §3.4.1, §3.4.3, §3.4.4 | AC-12, AC-13 |
| `feature/emb-phase1-schema-model` | `alembic/versions/<rev>_add_multi_vector_embeddings.py` | `test_gemma_embedding.py` all green + roundtrip proof | §3.2, §3.3, §5.1 | AC-4, AC-9 |
| `feature/emb-phase2-mcp-client-pipeline` | None | `test_mcp_client.py` + `test_text_assembler.py` all green | §3.4.2, §3.5 | AC-14, AC-15 |
| `feature/emb-phase3-cron-integration` | None | `test_embedding_processor.py` all green | §3.6, §3.7 | AC-1, AC-5, AC-6, AC-11 |
| `feature/emb-phase4-rag-multivector` | None | `test_rag_retrieval.py` regression tests all green | §3.8 | AC-7, AC-8 |
| `feature/emb-phase5-backfill-validation` | None (data only) | Full `pytest tests/ -v` log + validation SQL output | §5.2, §5.3 | AC-1, AC-2, AC-3, AC-10 |

### Merge Order

```
Phase 0 ─┐
Phase 1 ──┼──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
          │
          └── (independent, can merge in parallel with Phase 0)
```

Phase 0 and Phase 1 can run in parallel. Phase 2 requires Phase 0. Phase 3 requires Phases 1 and 2. Phase 4 requires Phase 1. Phase 5 requires Phases 3 and 4.

---

## 3. MCP Server Development Plan

**Target file:** `src/mcp_servers/gdrive/server.py`  
**Framework:** FastMCP (Python MCP SDK, `mcp[cli]>=1.0`)  
**Transport:** STDIO (stdin/stdout, co-located process)  
**Protocol:** JSON-RPC 2.0

### 3.1 Tool Registration

Three MCP tools must be registered via `@mcp.tool()` decorator on the `FastMCP` instance named `"gdrive-resume-server"`:

| Tool | Input | Output | Error Codes |
|------|-------|--------|-------------|
| `read_document` | `url: str` or `file_id: str` | `{text, title, mime_type, modified_time}` | `not_found`, `permission_denied`, `oversized`, `parse_error` |
| `search_files` | `query: str`, `max_results: int = 10` | `{files: [{id, name, mime_type}]}` | `quota_exceeded`, `auth_error` |
| `get_file_metadata` | `file_id: str` | `{id, name, size, modifiedTime, mimeType}` | `not_found`, `permission_denied` |

### 3.2 Service Account Authentication

Authentication lives **only inside `server.py`**. Loading sequence:
1. Read SA key path from `GOOGLE_SERVICE_ACCOUNT_FILE` env var (default: `/secrets/sa-key.json`)
2. Create `service_account.Credentials` with scope `https://www.googleapis.com/auth/drive.readonly`
3. Build `drive` (v3) and `docs` (v1) service objects per-request (lazy init via `_get_drive_service()` / `_get_docs_service()`)

**The cron pipeline subprocess never receives this env var in its own process environment** — it is passed only to the MCP server subprocess via `StdioServerParameters(env={...})`.

### 3.3 Configuration Module

`src/mcp_servers/gdrive/config.py` exposes:
- `SA_KEY_PATH` — resolved from env var
- `DRIVE_SCOPES` — `["https://www.googleapis.com/auth/drive.readonly"]`
- `RATE_LIMIT_DELAY_MS` — 200 (enforced between Google API calls)
- `MAX_DOC_SIZE_BYTES` — 102400 (100KB; truncate and warn beyond this)
- `MAX_RETRIES` — 3 (exponential backoff: 1s, 2s, 4s)

### 3.4 Rate Limiting & Error Handling

Internal rate limiter enforces 200ms delay between Google API calls to stay under 300 RPM (CR §3.4.4). Error responses follow the pattern `{"error": "<code>", "text": ""}` so the MCP client can distinguish error types without parsing exception strings.

| Google API Status | MCP Server Response | Cron Pipeline Action |
|-------------------|---------------------|-----------------------|
| 404 Not Found | `{"error": "not_found"}` | Log warning; skip member; `resume_text = NULL` |
| 403 Forbidden | `{"error": "permission_denied"}` | Log warning; flag in `metadata` JSONB |
| 429 Rate Limited | Retry 3× with backoff; then `{"error": "quota_exceeded"}` | Skip member; log P2 alert trigger |
| Empty document | `{"text": "", "error": null}` | Skip resume embedding; skills/certs still processed |
| Doc >100KB | Truncate to 100KB; include `{"warning": "truncated"}` | Use truncated text; log warning |

### 3.5 Standalone Test Plan

Tests in `tests/mcp_servers/test_gdrive_server.py` must be runnable **without cron, without DB, without a real SA key**:

```
test_tools_list_returns_three_tools          # AC-12
test_read_document_happy_path_google_doc     # AC-13 (mocked Docs API)
test_read_document_404_returns_error_dict
test_read_document_403_returns_error_dict
test_read_document_oversized_truncates
test_search_files_returns_file_list
test_get_file_metadata_returns_dict
test_auth_config_reads_env_var              # SA path from env
```

**Mock strategy:** Patch `googleapiclient.discovery.build` with `unittest.mock.patch`. Return pre-built fixture dicts representing Google Docs API responses.

### 3.6 AC-12 / AC-13 Validation Approach

- **AC-12:** Automated — `test_tools_list_returns_three_tools` calls `server.list_tools()` directly (or sends JSON-RPC `tools/list` via in-process MCP test client) and asserts response contains exactly 3 tool names
- **AC-13:** Requires real SA credential. Validated in Phase 5 (backfill) via end-to-end run. In Phase 0, validated with mock; document in DoD that real credential test is deferred to Phase 5.

---

## 4. Database Migration Plan

**Target table:** `team_member_embeddings`  
**Current HEAD:** `bca284b2d901`  
**New revision:** `<rev_id>_add_multi_vector_embeddings` (generated by Alembic)  
**Target file:** `alembic/versions/<rev_id>_add_multi_vector_embeddings.py`

### 4.1 New Columns

All 10 new columns are **nullable** (except `embedding_model` which has a server default). This ensures zero-downtime — existing rows are unaffected by DDL.

| Column | SQLAlchemy Type | Nullable | Server Default |
|--------|----------------|----------|----------------|
| `resume_embedding` | `Vector(768)` | Yes | — |
| `skills_embedding` | `Vector(768)` | Yes | — |
| `certifications_embedding` | `Vector(768)` | Yes | — |
| `resume_text` | `Text` | Yes | — |
| `skills_text` | `Text` | Yes | — |
| `certifications_text` | `Text` | Yes | — |
| `embedding_model` | `String(100)` | No | `'embedding-gemma-300m'` |
| `content_hash` | `CHAR(64)` | Yes | — |
| `resume_fetched_at` | `DateTime` | Yes | — |
| `embedding_updated_at` | `DateTime` | Yes | — |

### 4.2 Indexes

Four new indexes created after column addition:

```
idx_tme_resume_embedding        — IVFFlat, vector_cosine_ops, lists=10
idx_tme_skills_embedding        — IVFFlat, vector_cosine_ops, lists=10
idx_tme_certifications_embedding — IVFFlat, vector_cosine_ops, lists=10
idx_tme_content_hash            — B-tree on content_hash
```

> **R5 Note:** IVFFlat requires `lists` to be ≤ sqrt(row_count) for efficiency. With 39 rows, `lists=10` may trigger a PostgreSQL warning. This is acceptable; sequential scan will be used implicitly for small datasets. Revisit `lists` value at 1000+ rows.

### 4.3 Backward Compatibility

The existing `embedding` column (`Vector(768)`) is **never dropped or modified**. It continues to serve the existing RAG retrieval path during the Phase 3→Phase 4 transition window. After Phase 3, the `EmbeddingProcessor` will populate it as a weighted average:

```
embedding = L2_normalize(0.50 × resume_embedding + 0.30 × skills_embedding + 0.20 × certifications_embedding)
```

If any component is NULL (e.g., no resume URL), the weighted average is computed from available vectors only, re-normalized.

### 4.4 Alembic `migrations_check.py` Update

After generating the migration, add the new revision ID string to the `ACCEPTABLE_REVISIONS` set in `src/app/cron/db/migrations_check.py`. This is currently at 11 entries with HEAD `bca284b2d901`; after Phase 1 it will be **12 entries**.

### 4.5 Upgrade/Downgrade Roundtrip Validation (AC-9)

CI gate for Phase 1 PR must execute:

```bash
alembic upgrade head
# Assert: 10 new columns present in information_schema
alembic downgrade bca284b2d901
# Assert: 10 new columns absent; original 7 columns present
alembic upgrade head
# Assert: re-application succeeds (idempotency)
```

All three steps must succeed to satisfy AC-9.

### 4.6 Index Creation Timing

IVFFlat indexes are created during `upgrade()` (i.e., at DDL time before backfill). For the current dataset size of 39 rows, this is inconsequential. For production scaling, if row count exceeds 10,000, `CONCURRENTLY` index creation should be evaluated to avoid table lock.

---

## 5. Embedding Model Setup Plan

**Model:** `google/embedding-gemma-300m`  
**Target class:** `GemmaEmbeddingAgent` in `src/app/ai/utils/gemma_embedding.py`  
**Output dimension:** 768 (native — matches current `Vector(768)` pgvector columns)

### 5.1 Class Implementation

`GemmaEmbeddingAgent` wraps HuggingFace `transformers`:
- `__init__(device: str = "cpu")` — loads `AutoTokenizer` and `AutoModel` from `MODEL_NAME = "google/embedding-gemma-300m"`
- `embed_text(text: str) -> np.ndarray` — tokenize → forward pass → mean pooling over valid tokens → L2 normalize → return `(768,)` ndarray
- `embed_batch(texts: list[str]) -> list[np.ndarray]` — batched variant for throughput
- Class constant `DIMENSION = 768`, `MAX_TOKENS = 2048`
- `torch_dtype=torch.float16` if `device != "cpu"` else `torch.float32` (R6: FP16 reduces memory from ~1.2GB to ~600MB on GPU/MPS)

### 5.2 Model Download & Caching

- First run: `AutoModel.from_pretrained("google/embedding-gemma-300m")` downloads ~600MB to HuggingFace cache (`~/.cache/huggingface/hub/`)
- Subsequent runs: loaded from local disk cache (~8s cold start, one-time per cron run)
- Pinning: specify `revision=<commit_hash>` in `from_pretrained()` to fix model version. Record pinned hash in `src/app/settings.py` as `GEMMA_MODEL_REVISION`.
- In K8s: mount a shared PVC for the HuggingFace cache to avoid re-download on pod restart

### 5.3 Memory Management (R6 Mitigation)

- Model is loaded **only during cron embed phase**, not at application startup
- `EmbeddingProcessor` instantiates `GemmaEmbeddingAgent` at phase start, holds reference for full batch, explicitly deletes after batch completes
- For CPU: FP32 (~1.2GB) — acceptable for 4GB host as per CR §6.3.2
- For GPU/MPS: FP16 (~600MB) — auto-selected when `EMBEDDING_DEVICE` ≠ `"cpu"`

### 5.4 Model Factory

`src/app/ai/utils/embedding.py` gains a `get_embedding_agent()` factory:
- Reads `EMBEDDING_MODEL` env var (default: `"embedding-gemma-300m"`)
- If `"embedding-gemma-300m"`: returns `GemmaEmbeddingAgent(device=settings.embedding_device)`
- If `"gemini-embedding-001"` (or any `gemini-*`): returns existing `EmbeddingAgent()`
- Factory enables R1 A/B testing by running both agents against 10 sample members and comparing cosine similarity distributions

### 5.5 Throughput Baseline (AC-11 / R3)

Performance test `tests/ai/test_gemma_embedding.py::test_throughput_100_texts` must demonstrate:
- 100 `embed_text()` calls in <60 seconds on CPU (≥100 members/minute)
- If throughput <100/min on CPU: log R3 escalation warning; document ONNX Runtime fallback plan

### 5.6 AC-4 Validation

After `EmbeddingProcessor` writes embeddings, `embedding_model` column is set to `GemmaEmbeddingAgent.MODEL_NAME` (`"google/embedding-gemma-300m"` — trimmed to `"embedding-gemma-300m"` for the VARCHAR(100) column). Validated by:
```sql
SELECT DISTINCT embedding_model FROM team_member_embeddings;
-- Expected: ('embedding-gemma-300m',)
```

---

## 6. MCP Client & Resume Pipeline Plan

**Target file:** `src/app/cron/embedding/mcp_client.py`  
**Pattern:** STDIO subprocess managed by `MCPResumeClient`; session-per-batch

### 6.1 STDIO Subprocess Lifecycle

```
1. Phase start: MCPResumeClient.__init__() — configure StdioServerParameters
2. Batch begin: enter async context stdio_client() → spawns subprocess
3. Session begin: ClientSession.initialize() — capability negotiation
4. Per-member: session.call_tool("read_document", {"url": ...})
5. Batch end: exit ClientSession context (graceful shutdown)
6. Phase end: exit stdio_client context (subprocess terminated)
```

**Session-per-batch:** One MCP session is held open for the entire 39-member batch. MCP server process startup cost (~500ms) is paid once, not per-member (CR §6.2 amortization).

**Synchronous wrapper:** `fetch_resume_sync(profile_url: str) -> str | None` runs `asyncio.run()` around the async fetch. Used by `EmbeddingProcessor` which is synchronous.

### 6.2 Broken-Pipe Recovery (R9 Mitigation)

If `session.call_tool()` raises a connection error or broken-pipe exception:
1. Log error with member ID and exception type
2. Attempt subprocess restart (max 3 attempts, 2s delay between)
3. If 3 consecutive crashes: abort resume fetching for all remaining members; continue with skills/certs-only embedding (no MCP call needed)
4. Partial progress is saved via per-member commits (Phase 3)

### 6.3 Credential Isolation Verification (AC-14)

In `mcp_client.py`:
- `StdioServerParameters(env={"GOOGLE_SERVICE_ACCOUNT_FILE": os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")})` — passes SA path only to the subprocess environment
- The cron process itself must **NOT** have `GOOGLE_SERVICE_ACCOUNT_FILE` in its env at runtime. This is enforced by K8s pod spec: SA key secret is mounted as a file and the path is injected into the MCP server subprocess env, not the cron pod env.
- AC-14 test: `assert "GOOGLE_SERVICE_ACCOUNT_FILE" not in os.environ` in cron process (unit test with controlled env)

### 6.4 Graceful Server Failure Handling (AC-15)

Scenario: MCP server subprocess crashes mid-batch (SIGKILL in test harness):
- `MCPResumeClient.fetch_resume_sync()` catches all exceptions at the tool-call level
- Returns `None` on any failure
- `EmbeddingProcessor` treats `None` resume text as: set `resume_text = None`, skip resume embedding for this member, continue with skills + certs embedding if available
- Cron phase exits with `EXIT_PARTIAL` (code 1) not `EXIT_FATAL` (code 2) if >0 members succeeded
- AC-15 test: mock `ClientSession.call_tool` to raise `BrokenPipeError`; assert `embed` mode completes without raising

### 6.5 Text Assembler

`src/app/cron/embedding/text_assembler.py` implements three pure functions (no side effects beyond DB reads):

| Function | DB Query | Output |
|----------|----------|--------|
| `assemble_resume_text(member, content)` | None (uses passed TeamMember ORM object) | Structured text with designation, location, work type, experience, resume content |
| `assemble_skills_text(member_id, db)` | JOIN `team_member_skill` → `skill_master` → `category_master` | Structured skills profile with proficiency labels and experience years |
| `assemble_certifications_text(member_id, db)` | JOIN `team_member_skill_certification` → `team_member_skill` → `skill_master` | Structured certs with issuer, status (Active/Expired), related skill |

Empty result (no skills/no certs) returns `""` — `EmbeddingProcessor` skips embedding for empty text, leaving column NULL.

---

## 7. Cron Integration Plan

**Target file:** `src/app/cron/main.py` (currently 461 lines, exit codes 0–4)  
**New modes:** `embed`, `ingest-embed`  
**New flag:** `--force`

### 7.1 CLI Mode Additions

Existing argparse in `main.py` gains:

```
Subcommand: embed
  --force       Re-embed all members regardless of content hash
  
Subcommand: ingest-embed
  Runs ingest phase first, then embed phase in sequence
  --force       Propagated to embed phase
```

Exit codes are unchanged: 0=SUCCESS, 1=PARTIAL, 2=FATAL, 3=SCHEMA_MISMATCH, 4=AUTH_FAILED. The `embed` mode may return PARTIAL (1) if some members failed (e.g., MCP server errors) while others succeeded.

### 7.2 EmbeddingProcessor Orchestration

`src/app/cron/embedding/embedding_processor.py` class `EmbeddingProcessor`:

```
__init__(db, mcp_client, embedding_agent, settings)
run(force: bool = False) -> ProcessingResult
  1. SELECT team_member WHERE is_deleted = False ORDER BY team_member_id
  2. For each member:
     a. Fetch profile_url from TeamMember
     b. Fetch current content_hash from TeamMemberEmbedding
     c. Assemble skills_text and certifications_text via text_assembler
     d. If profile_url set: fetch resume_text via MCPResumeClient
     e. Scrub resume_text via PII scrubber (if non-empty)
     f. Compute new_hash = sha256(resume_text || skills_text || certs_text)
     g. If new_hash == stored_hash AND NOT force: skip (AC-6)
     h. Else: embed all three texts → upsert to DB → commit per-member
```

### 7.3 Content Hash Change Detection (AC-6)

SHA-256 of `f"{resume_text}||{skills_text}||{certifications_text}"` encoded as UTF-8. Stored in `content_hash` CHAR(64) column. On second run with no changes, all members are skipped — verified via `embedding_skip_rate` metric. Expected skip rate: 80–90% on typical nightly runs (R7: hash detects changes regardless of URL stability).

### 7.4 Per-Member Commit Strategy

Each team member's embedding data is written and committed to the DB individually (not in a single transaction for the entire batch). This ensures:
- Partial progress is preserved if cron crashes or times out mid-batch
- MCP server failure for member N does not rollback members 1..N-1
- `ProcessingResult` tracks `{success_count, skip_count, error_count, error_members: list[str]}`

### 7.5 Repository Method

`src/app/cron/db/repositories.py` gains `upsert_team_member_embeddings(db, member_id, payload: EmbeddingPayload)`:
- Uses PostgreSQL `INSERT ... ON CONFLICT (team_member_id) DO UPDATE SET ...`
- Updates all new columns plus `embedding` (weighted average), `embedding_updated_at = NOW()`
- Does NOT touch `profile_text`, `metadata`, `pii_scrubbed`, `scrubbed_at` (owned by Phase 1 ingestion)

### 7.6 Phase Isolation

The `ingest-embed` mode runs ingestion (Phase 1 pipeline) in a separate DB transaction that is committed before the embedding phase begins. The embedding phase opens its own transactions. A crash in the embedding phase cannot roll back ingestion data.

---

## 8. RAG Multi-Vector Update Plan

**Target method:** `_query_vector_and_filter()` in `src/app/ai/utils/rag_retrieval.py`  
**Current state:** ALL cosine distances (`mandatory_sim`, `preferred_sim`, `jd_level_sim`, `cert_sim`) use the single `TeamMemberEmbedding.embedding` column  
**Target state:** Each distance uses the semantically appropriate column

### 8.1 Vector Routing

| Score Component | Current Column | Target Column | Fallback (NULL) |
|----------------|----------------|---------------|-----------------|
| `mandatory_sim` | `embedding` | `skills_embedding` | `embedding` |
| `preferred_sim` | `embedding` | `skills_embedding` | `embedding` |
| `jd_level_sim` | `embedding` | `resume_embedding` | `embedding` |
| `cert_sim` | `embedding` | `certifications_embedding` | `0.0` (no certs → no cert score) |

### 8.2 NULL Fallback Logic

In the SQLAlchemy query within `_query_vector_and_filter()`:

```python
# Pseudo-code for the query construction
mandatory_vec = case(
    (TeamMemberEmbedding.skills_embedding != None, 
     TeamMemberEmbedding.skills_embedding.cosine_distance(jd_mandatory_embedding)),
    else_=TeamMemberEmbedding.embedding.cosine_distance(jd_mandatory_embedding)
)

resume_vec = case(
    (TeamMemberEmbedding.resume_embedding != None,
     TeamMemberEmbedding.resume_embedding.cosine_distance(jd_level_embedding)),
    else_=TeamMemberEmbedding.embedding.cosine_distance(jd_level_embedding)
)

cert_vec = case(
    (TeamMemberEmbedding.certifications_embedding != None,
     TeamMemberEmbedding.certifications_embedding.cosine_distance(jd_cert_embedding)),
    else_=literal(1.0)  # 1.0 cosine distance = 0.0 similarity; no penalty, no boost
)
```

### 8.3 Legacy `embedding` Column Population (AC-7)

`EmbeddingProcessor` (Phase 3) computes the weighted average after all three embeddings are generated:

```
if resume_emb and skills_emb and certs_emb:
    blended = 0.50 * resume_emb + 0.30 * skills_emb + 0.20 * certs_emb
elif resume_emb and skills_emb:
    blended = normalize(0.625 * resume_emb + 0.375 * skills_emb)
elif skills_emb only:
    blended = skills_emb
... (all combinations)
blended = L2_normalize(blended)
```

AC-7 spot-check: for 5 team members, manually verify `embedding` column equals computed weighted average to 4 decimal places.

### 8.4 Regression Test Plan

`tests/ai/test_rag_retrieval.py` must cover:

| Test | Scenario | Assertion |
|------|----------|-----------|
| `test_multi_vector_mandatory_uses_skills_embedding` | All 3 columns populated | `mandatory_sim` is computed against `skills_embedding` |
| `test_multi_vector_jd_level_uses_resume_embedding` | All 3 columns populated | `jd_level_sim` uses `resume_embedding` |
| `test_fallback_skills_null_uses_legacy` | `skills_embedding = NULL` | `mandatory_sim` falls back to `embedding` column |
| `test_fallback_resume_null_uses_legacy` | `resume_embedding = NULL` | `jd_level_sim` falls back to `embedding` column |
| `test_fallback_certs_null_is_zero` | `certifications_embedding = NULL` | `cert_sim = 0.0` |
| `test_matches_endpoint_returns_results` | Full E2E with test requisition | Non-empty matches list returned |

---

## 9. Testing Strategy

### 9.1 MCP Server Tests (~10 tests)

**File:** `tests/mcp_servers/test_gdrive_server.py`  
**Mock strategy:** `unittest.mock.patch("googleapiclient.discovery.build")` returning fixture dicts  
**CI gate:** Must pass before `feature/emb-phase0-mcp-server` PR approval

```
test_tools_list_returns_three_tools
  → Assert tools/list response contains read_document, search_files, get_file_metadata

test_read_document_happy_path_google_doc
  → Mock docs().get() returns fixture doc; assert text non-empty, title matches

test_read_document_file_id_extraction
  → Assert _extract_doc_id() correctly parses Google Docs URL formats

test_read_document_invalid_url_returns_error
  → Assert {"error": ..., "text": ""} when URL is unparseable

test_read_document_404_returns_not_found
  → Mock HttpError 404; assert {"error": "not_found"}

test_read_document_403_returns_permission_denied
  → Mock HttpError 403; assert {"error": "permission_denied"}

test_read_document_oversized_truncates_at_100kb
  → Mock 150KB text; assert len(result["text"]) <= 102400 and "warning" in result

test_search_files_returns_file_list
  → Mock files().list() returns 3 items; assert len(result["files"]) == 3

test_get_file_metadata_returns_dict
  → Mock files().get() returns dict; assert id, name, mimeType present

test_auth_config_reads_env_var
  → Set GOOGLE_SERVICE_ACCOUNT_FILE in env; assert config.SA_KEY_PATH resolves correctly
```

### 9.2 MCP Client Tests (~6 tests)

**File:** `tests/cron/test_mcp_client.py`  
**Mock strategy:** `AsyncMock` for `ClientSession`, patch `stdio_client` context manager

```
test_session_lifecycle_init_call_close
  → Verify initialize() called, tool called with correct args, session closed

test_fetch_resume_sync_returns_text
  → Mock call_tool returns {"text": "resume content"}; assert string returned

test_fetch_resume_sync_empty_doc_returns_none
  → Mock call_tool returns {"text": ""}; assert None returned

test_broken_pipe_triggers_reconnect_max_3
  → Mock call_tool raises BrokenPipeError 3 times; assert retry count = 3, then None

test_credential_isolation_env_not_in_cron_process
  → Assert "GOOGLE_SERVICE_ACCOUNT_FILE" not in os.environ during MCPResumeClient use

test_server_crash_returns_none_gracefully
  → Mock subprocess exit code 1 mid-session; assert fetch_resume_sync returns None, no exception
```

### 9.3 Embedding Pipeline Tests (~10 tests)

**Files:** `tests/cron/test_text_assembler.py`, `tests/cron/test_embedding_processor.py`, `tests/ai/test_gemma_embedding.py`  
**Mock strategy:** Patch `AutoModel.from_pretrained` to return a mock that produces fixed tensors

```
test_assemble_resume_text_includes_designation_location
test_assemble_skills_text_expert_label_for_rating_gte_8
test_assemble_skills_text_empty_skills_returns_empty_string
test_assemble_certifications_text_active_status_for_future_date
test_assemble_certifications_text_no_certs_returns_empty_string
test_content_hash_same_input_same_hash
test_content_hash_different_input_different_hash
test_embedding_processor_skips_on_hash_match
test_embedding_processor_embeds_on_hash_mismatch
test_gemma_agent_embed_text_returns_768_dim_unit_vector
```

**Performance test:**  
`tests/ai/test_gemma_embedding.py::test_throughput_100_texts` — embeds 100 fixed-length strings; asserts elapsed < 60s on CPU.

### 9.4 Integration Tests (~5 tests)

**File:** `tests/cron/test_embedding_processor.py` (integration section) + `tests/ai/test_rag_retrieval.py`

```
test_e2e_cron_embed_mcp_mock_to_db
  → Uses real SQLite or test PG DB; mocked MCP client; verify row inserted with all 3 embeddings

test_e2e_ingest_embed_phase_isolation
  → Inject error in embed phase; verify ingest phase data is committed

test_alembic_upgrade_downgrade_roundtrip
  → CI: alembic upgrade head → check columns → alembic downgrade bca284b2d901 → check absent

test_rag_multi_vector_retrieval_returns_matches
  → Populate team_member_embeddings with test vectors; call _query_vector_and_filter(); assert results

test_rag_fallback_null_skills_embedding
  → Insert row with skills_embedding=NULL; verify mandatory_sim uses embedding column
```

### 9.5 Performance Tests (~3 tests)

```
test_embedding_throughput_100_members_per_minute
  → Benchmark embed_batch(100 texts); assert < 60s on CPU

test_rag_query_latency_p50_under_65ms
  → Execute _query_vector_and_filter() 50 times; assert median < 65ms

test_mcp_session_init_under_2s
  → Time stdio_client init + ClientSession.initialize(); assert < 2000ms
```

### 9.6 CI Gating Requirements

| Phase | Required Tests | Gate |
|-------|---------------|------|
| Phase 0 PR | `test_gdrive_server.py` (10 tests) | All pass |
| Phase 1 PR | `test_gemma_embedding.py` + alembic roundtrip | All pass |
| Phase 2 PR | `test_mcp_client.py` + `test_text_assembler.py` | All pass |
| Phase 3 PR | `test_embedding_processor.py` | All pass |
| Phase 4 PR | `test_rag_retrieval.py` | All pass |
| Phase 5 PR | Full `pytest tests/ -v` | All pass (AC-10) |

### 9.7 Naming Conventions

- Test functions: `test_<unit>_<scenario>_<expected_outcome>`
- Fixture files: `tests/fixtures/gdrive/sample_doc.json`, `tests/fixtures/embeddings/sample_768.npy`
- Mock classes: `MockGoogleDocsClient`, `MockMCPSession`, `MockGemmaAgent`

---

## 10. Monitoring & Observability Setup

Aligned to CR §6.6 Operational Impact. Metrics are emitted by `EmbeddingProcessor` and `MCPResumeClient` using the existing structured logging infrastructure in `src/app/cron/`.

### 10.1 MCP Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `mcp_session_init_duration_seconds` | Histogram | `server=gdrive` | Time from subprocess spawn to `initialize()` complete |
| `mcp_tool_call_total` | Counter | `tool=<name>`, `status=success\|error` | Per-tool invocation count |
| `mcp_tool_call_error_total` | Counter | `error_type=not_found\|permission_denied\|quota_exceeded\|crash` | Error breakdown |
| `mcp_server_uptime_seconds` | Gauge | `server=gdrive` | How long current MCP server subprocess has been running |

### 10.2 Embedding Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `embedding_generation_duration_seconds` | Histogram | `type=resume\|skills\|certifications` | Per-embedding inference time |
| `resume_fetch_success_total` | Counter | `status=success\|skipped\|error` | Resume fetch outcomes per batch |
| `embedding_skip_total` | Counter | `reason=hash_match\|no_content` | Members skipped (change detection) |
| `embedding_batch_total_duration_seconds` | Histogram | — | Total embedding phase duration per cron run |

### 10.3 Alerts

| Alert | Threshold | Severity | Runbook |
|-------|-----------|----------|---------|
| `mcp_server_start_failed` | MCP subprocess exit code ≠ 0 on init | P1 | `docs/runbooks/mcp-server-troubleshooting.md` |
| `resume_fetch_error_rate_high` | `mcp_tool_call_error_total` / `mcp_tool_call_total` > 10% in batch | P2 | `docs/runbooks/embedding-pipeline-troubleshooting.md` |
| `embedding_phase_duration_exceeded` | `embedding_batch_total_duration_seconds` > 900 (15 min) | P2 | `docs/runbooks/embedding-pipeline-troubleshooting.md` |

### 10.4 Runbook Entries

Two new sections in `docs/runbooks/`:

**`docs/runbooks/mcp-server-troubleshooting.md`** covers:
- Subprocess won't start (Python path, `mcp[cli]` not installed, SA file missing)
- Credential errors (`GOOGLE_SERVICE_ACCOUNT_FILE` path wrong, SA key expired)
- STDIO buffer overflow symptoms (large document causing hang)
- Manual `tools/list` test command
- How to restart MCP server mid-batch (kill PID, rerun `embed --force` for failed members)

**`docs/runbooks/embedding-pipeline-troubleshooting.md`** covers:
- `embedding-gemma-300m` model not found (HuggingFace cache miss, offline env)
- Google API quota exceeded (how to check via MCP server logs)
- OOM during embedding (R6): reduce `embedding_batch_size` in config, switch to FP16
- Slow embedding (R3): profile `embed_batch()`, check for GPU availability
- Partial backfill recovery: identify members with NULL columns, rerun for them

---

## 11. Backfill & Data Validation Plan

Aligned to CR §5.2 (Data Backfill Strategy). Executed in Phase 5.

### 11.1 Pre-Backfill Snapshot

Before executing backfill, capture baseline state:

```sql
-- Pre-backfill counts
SELECT 
    COUNT(*) AS total_members,
    COUNT(embedding) AS members_with_legacy_embedding,
    COUNT(resume_embedding) AS members_with_resume_embedding,
    COUNT(skills_embedding) AS members_with_skills_embedding,
    COUNT(certifications_embedding) AS members_with_cert_embedding
FROM team_member_embeddings;
```

Expected before backfill: `resume_embedding = 0`, `skills_embedding = 0`, `certifications_embedding = 0`.

Also capture baseline match quality:

```bash
# Run test requisition through /matches endpoint; capture response JSON
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:9001/api/v1/jd-skill-mapping/{test_req_id}/matches > baseline_matches.json
```

### 11.2 Backfill Execution

**Phase A — DDL migration** (~5 seconds):
```bash
alembic upgrade head
```
Verify: all 10 new columns appear in `information_schema.columns`.

**Phase B — Data backfill** (~5 minutes):
```bash
python -m app.cron.main embed --force
```
Monitor: watch `embedding_batch_total_duration_seconds` metric and stdout log.

**Phase C — Validation queries** (~1 second):
```sql
-- AC-1: Members with resume_embedding (should equal members WITH profile_url)
SELECT 
    COUNT(*) FILTER (WHERE resume_embedding IS NOT NULL) AS resume_embedded,
    COUNT(*) FILTER (WHERE profile_url IS NOT NULL) AS has_profile_url
FROM team_member t
LEFT JOIN team_member_embeddings e ON t.team_member_id = e.team_member_id;

-- AC-2: Members with skills_embedding (should equal members with ≥1 skill)
SELECT
    COUNT(*) FILTER (WHERE skills_embedding IS NOT NULL) AS skills_embedded,
    COUNT(DISTINCT team_member_id) AS members_with_skills
FROM team_member_skill
WHERE is_deleted = false;

-- AC-3: Members with certifications_embedding
SELECT
    COUNT(*) FILTER (WHERE certifications_embedding IS NOT NULL) AS certs_embedded
FROM team_member_embeddings;

-- AC-4: Model identity
SELECT DISTINCT embedding_model FROM team_member_embeddings;
-- Expected: (embedding-gemma-300m,)
```

**Phase D — Deploy multi-vector RAG** (code deploy):
```bash
git checkout feature/emb-phase4-rag-multivector
git merge main  # Get latest after Phase 3 merge
# Deploy updated rag_retrieval.py
```

### 11.3 Post-Backfill Match Quality Comparison

After Phase D deployment, run test requisition again:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:9001/api/v1/jd-skill-mapping/{test_req_id}/matches > post_matches.json
```

Compare:
- Candidate set (same members? new members surfaced?)
- Score distribution (mean/max/min — should be similar or higher with multi-vector)
- Top-3 ranking stability (if dramatically different, investigate R1)

Acceptable outcome: top-3 candidates unchanged or improved; no regression beyond 5% in mean match score.

### 11.4 R8 Validation (Private/Unshared Docs)

Confirm members with unshared or private Google Docs are handled gracefully:
```sql
SELECT team_member_id, resume_text
FROM team_member_embeddings
WHERE resume_text IS NULL AND team_member_id IN (
    SELECT team_member_id FROM team_member WHERE profile_url IS NOT NULL
);
```
These should appear in cron logs as `"resume fetch: permission_denied"` or `"not_found"` — not as errors that aborted the run.

---

## 12. Rollback Strategy

### 12.1 Per-Phase Rollback Table

| Phase | Rollback Action | Data Impact | Time Estimate | Automated Trigger |
|-------|----------------|-------------|----------------|-------------------|
| **Phase 0 — MCP Server** | `git revert`; delete `src/mcp_servers/` directory tree | None | <2 minutes | MCP server fails to respond to `tools/list` after 3 restart attempts |
| **Phase 1 — Schema & Model** | `alembic downgrade bca284b2d901`; revert `models.py`, `settings.py`, `migrations_check.py` | Drops 10 new columns (no data in them pre-backfill) | <5 minutes | Migration fails on staging; or torch OOM on prod host |
| **Phase 2 — MCP Client** | `git revert`; delete `src/app/cron/embedding/` package (client + assembler only); revert `config.py` | None | <2 minutes | STDIO subprocess instability causes cron runtime >30 min |
| **Phase 3 — Cron Integration** | Revert `main.py` (remove `embed`/`ingest-embed` modes); revert `repositories.py`; delete `embedding_processor.py` | None — legacy `embedding` column untouched | <5 minutes | Embed phase causes ingest phase data corruption (should not occur due to phase isolation) |
| **Phase 4 — RAG Update** | Revert `rag_retrieval.py` and `agents/rag_retrieval.py` to pre-phase state; redeploy | None — `embedding` column still populated | <5 minutes | Match quality degrades >5% vs baseline (R1 final validation) |
| **Phase 5 — Backfill** | No rollback needed; data in new nullable columns is retained | New columns remain populated | N/A | N/A — backfill is additive only |

### 12.2 Rollback Time Objective

All phases: **<15 minutes** from decision to rollback complete. Phase 1 schema rollback is the longest (~5 min for `alembic downgrade` on large table) but still well within 15-min objective.

### 12.3 Automated Rollback Triggers

Monitored conditions that automatically trigger a rollback alert (human confirmation required for destructive operations):

| Condition | Metric/Log Signal | Trigger Phase Rollback |
|-----------|------------------|------------------------|
| MCP server startup failure | `mcp_server_start_failed` alert fired | Phase 0 |
| Cron duration > 30 min (SLA breach) | `embedding_batch_total_duration_seconds` > 1800 | Phase 2 or Phase 3 |
| Migration failure on staging | `alembic upgrade` non-zero exit | Phase 1 |
| Match quality regression > 5% | Post-deploy comparison script | Phase 4 |
| OOM during embedding | `MemoryError` in cron logs | Phase 3 (reduce batch size first) |

### 12.4 Data Restoration Guarantees

- The original `embedding` and `profile_text` columns are **never modified** by Phases 0–3. Pre-CR-EMB-002 RAG behavior is always restorable by reverting Phase 4.
- The `bca284b2d901` migration state (PII scrubbed flag) is preserved by `alembic downgrade bca284b2d901` — it does not drop PII columns.
- No foreign key relationships are changed — rollback of Phase 1 will not orphan any records.

---

## 13. Definition of Done (DoD)

### Phase 0: MCP Server DoD

- [ ] `src/mcp_servers/gdrive/server.py` implements `FastMCP` with 3 tools (`read_document`, `search_files`, `get_file_metadata`)
- [ ] `src/mcp_servers/gdrive/config.py` exposes SA path, scopes, rate limit, max doc size
- [ ] Unit tests pass: all 10 tests in `tests/mcp_servers/test_gdrive_server.py` green
- [ ] `tools/list` JSON-RPC call returns all 3 tool names (AC-12 — automated or manual)
- [ ] Error responses for 404, 403, oversized, empty doc all return structured `{"error": ...}` dict
- [ ] Rate limiter enforces 200ms inter-request delay (unit tested via mock timer)
- [ ] Code reviewed by 1 peer and merged to `feature/emb-phase0-mcp-server`

### Phase 1: Schema & Model DoD

- [ ] `alembic/versions/<rev>_add_multi_vector_embeddings.py` created with correct `down_revision='bca284b2d901'`
- [ ] `alembic upgrade head` succeeds on staging DB without error
- [ ] `alembic downgrade bca284b2d901` + `alembic upgrade head` roundtrip succeeds (AC-9)
- [ ] `TeamMemberEmbedding` model in `src/app/db/models/models.py` reflects all 10 new columns
- [ ] `GemmaEmbeddingAgent` in `src/app/ai/utils/gemma_embedding.py` returns `ndarray` of shape `(768,)` with L2 norm ≈ 1.0
- [ ] Model factory `get_embedding_agent()` in `src/app/ai/utils/embedding.py` returns correct agent type
- [ ] `requirements.txt` updated with pinned versions for `transformers`, `torch`, `sentencepiece`, `mcp[cli]`, `google-auth`, `google-api-python-client`
- [ ] `ACCEPTABLE_REVISIONS` in `migrations_check.py` updated with new revision ID
- [ ] Unit tests pass: ≥5 tests in `tests/ai/test_gemma_embedding.py` green
- [ ] Model downloads and produces 768-dim vectors (verified in dev environment)
- [ ] Code reviewed and merged

### Phase 2: MCP Client & Pipeline DoD

- [ ] `src/app/cron/embedding/mcp_client.py`: `MCPResumeClient` spawns STDIO subprocess, manages session lifecycle, implements `fetch_resume_sync()`
- [ ] Credential isolation verified: `GOOGLE_SERVICE_ACCOUNT_FILE` absent from cron process env (AC-14)
- [ ] Broken-pipe reconnect: max 3 retries before graceful skip (R9)
- [ ] MCP server crash during fetch: cron continues, member skipped, no exception propagated (AC-15)
- [ ] `src/app/cron/embedding/text_assembler.py`: all three assembler functions tested and correct
- [ ] `src/app/cron/config.py` updated with MCP/embedding fields
- [ ] Unit tests pass: ≥6 tests in `test_mcp_client.py` + ≥5 tests in `test_text_assembler.py` green
- [ ] Code reviewed and merged

### Phase 3: Cron Integration DoD

- [ ] `python -m app.cron.main embed` runs without error on staging DB
- [ ] `python -m app.cron.main ingest-embed` completes Phase 1 then Phase 2 sequentially
- [ ] `--force` flag bypasses content hash check (re-embeds all members)
- [ ] Second run (no data changes): all members skipped via content hash (AC-6)
- [ ] `resume_text` column contains no raw PII patterns for any member (manual spot-check) (AC-5)
- [ ] `upsert_team_member_embeddings()` in `repositories.py` handles INSERT and UPDATE correctly
- [ ] Per-member commit strategy: crash mid-batch preserves already-committed members
- [ ] Embedding phase for 39 members completes in <5 minutes (AC-11)
- [ ] Integration tests pass: ≥5 tests in `test_embedding_processor.py` green
- [ ] Code reviewed and merged

### Phase 4: RAG Multi-Vector DoD

- [ ] `_query_vector_and_filter()` in `rag_retrieval.py` uses `skills_embedding` for mandatory/preferred distances
- [ ] `_query_vector_and_filter()` uses `resume_embedding` for JD level distance
- [ ] `_query_vector_and_filter()` uses `certifications_embedding` for cert distance
- [ ] NULL fallback to `embedding` column implemented for all three paths
- [ ] NULL `certifications_embedding` returns `cert_sim = 0.0` (not error)
- [ ] Legacy `embedding` column populated as weighted average (AC-7) — spot-checked for 5 members
- [ ] Test requisition returns matches via `/api/v1/jd-skill-mapping/{id}/matches` (AC-8)
- [ ] RAG query latency P50 ≤ 65ms (performance test)
- [ ] Regression tests pass: ≥5 tests in `test_rag_retrieval.py` green
- [ ] Code reviewed and merged

### Phase 5: Backfill & Validation DoD

- [ ] `alembic upgrade head` applied to production DB
- [ ] `python -m app.cron.main embed --force` completed without FATAL exit
- [ ] `SELECT count(*) WHERE resume_embedding IS NOT NULL` equals expected count for members with `profile_url` (AC-1)
- [ ] `SELECT count(*) WHERE skills_embedding IS NOT NULL` equals expected count for members with ≥1 skill (AC-2)
- [ ] `SELECT count(*) WHERE certifications_embedding IS NOT NULL` equals expected count for members with ≥1 cert (AC-3)
- [ ] `SELECT DISTINCT embedding_model` returns only `'embedding-gemma-300m'` (AC-4)
- [ ] `pytest tests/ -v` exits with code 0 (AC-10)
- [ ] Backfill completed in <5 minutes (AC-11)
- [ ] Match quality for test requisitions equal or improved vs baseline (R1 validation)
- [ ] Members without `profile_url` gracefully skipped — logged, not errored (R8 validation)
- [ ] Runbook entries added: `docs/runbooks/mcp-server-troubleshooting.md`, `docs/runbooks/embedding-pipeline-troubleshooting.md`
- [ ] Phase completion report created

---

## 14. Dependency Matrix

| Task | Depends On | Blocks | Phase |
|------|-----------|--------|-------|
| MCP Server (`src/mcp_servers/gdrive/server.py`) | Google SA provisioned (R4); `mcp[cli]` installed | Phase 2: MCP Client | Phase 0 |
| Schema Migration (`alembic upgrade head`) | `bca284b2d901` confirmed as current HEAD | Phase 3: Cron Integration; Phase 4: RAG | Phase 1 |
| `GemmaEmbeddingAgent` | `transformers`, `torch`, `sentencepiece` installed | Phase 3: Cron Integration | Phase 1 |
| `TeamMemberEmbedding` model update | Schema Migration | Phase 3: Cron Integration; Phase 4: RAG | Phase 1 |
| `ACCEPTABLE_REVISIONS` update | New migration revision ID | Cron schema validation | Phase 1 |
| MCP Client (`mcp_client.py`) | Phase 0 (MCP Server available) | Phase 3: Cron Integration | Phase 2 |
| Text Assembler (`text_assembler.py`) | None (standalone) | Phase 3: Cron Integration | Phase 2 |
| `EmbeddingProcessor` | Phase 1 (schema + model) + Phase 2 (client + assembler) | Phase 5: Backfill | Phase 3 |
| `embed` / `ingest-embed` CLI modes | Phase 3: EmbeddingProcessor | Phase 5: Backfill | Phase 3 |
| RAG Multi-Vector update | Phase 1 (schema), Phase 3 (data populated for testing) | Phase 5: Validation | Phase 4 |
| Backfill execution | Phase 3 + Phase 4 both merged | Production deploy | Phase 5 |
| Google SA Provisioning (Infra) | InfoSec review | Phase 0 integration testing; Phase 5 AC-13 | Pre-Phase 0 |

---

## 15. Branch-to-Spec Traceability

| Branch | CR Sections | AC IDs | Risk IDs | Test File(s) |
|--------|-------------|--------|----------|-------------|
| `feature/emb-phase0-mcp-server` | §3.4.1, §3.4.3, §3.4.4 | AC-12, AC-13 | R8, R9, R10, R11 | `tests/mcp_servers/test_gdrive_server.py` |
| `feature/emb-phase1-schema-model` | §3.2, §3.3, §5.1 | AC-4, AC-9 | R1, R5, R6 | `tests/ai/test_gemma_embedding.py` + alembic roundtrip |
| `feature/emb-phase2-mcp-client-pipeline` | §3.4.2, §3.5 | AC-14, AC-15 | R9, R12 | `tests/cron/test_mcp_client.py`, `tests/cron/test_text_assembler.py` |
| `feature/emb-phase3-cron-integration` | §3.6, §3.7 | AC-1, AC-5, AC-6, AC-11 | R2, R3, R7 | `tests/cron/test_embedding_processor.py` |
| `feature/emb-phase4-rag-multivector` | §3.8 | AC-7, AC-8 | R1 | `tests/ai/test_rag_retrieval.py` |
| `feature/emb-phase5-backfill-validation` | §5.2, §5.3 | AC-1, AC-2, AC-3, AC-10 | R4, R8 | Full `pytest tests/ -v` |

### Acceptance Criteria Coverage Matrix

| AC ID | Description (short) | Phase | Branch |
|-------|---------------------|-------|--------|
| AC-1 | `resume_embedding` populated for members with `profile_url` | Phase 3 (partial) + Phase 5 | `emb-phase3-cron-integration`, `emb-phase5-backfill-validation` |
| AC-2 | `skills_embedding` populated for members with ≥1 skill | Phase 3 (partial) + Phase 5 | `emb-phase3-cron-integration`, `emb-phase5-backfill-validation` |
| AC-3 | `certifications_embedding` populated for members with ≥1 cert | Phase 3 (partial) + Phase 5 | `emb-phase3-cron-integration`, `emb-phase5-backfill-validation` |
| AC-4 | `embedding_model = 'embedding-gemma-300m'` in DB | Phase 1 (default) + Phase 3 (written) | `emb-phase1-schema-model`, `emb-phase3-cron-integration` |
| AC-5 | PII scrubber runs on `resume_text` before storage | Phase 3 | `emb-phase3-cron-integration` |
| AC-6 | Unchanged members skipped on second run | Phase 3 | `emb-phase3-cron-integration` |
| AC-7 | Legacy `embedding` = weighted avg of new vectors | Phase 3 | `emb-phase3-cron-integration` |
| AC-8 | RAG returns multi-vector matches | Phase 4 | `emb-phase4-rag-multivector` |
| AC-9 | Alembic upgrade+downgrade roundtrip | Phase 1 | `emb-phase1-schema-model` |
| AC-10 | All tests pass | Phase 5 | `emb-phase5-backfill-validation` |
| AC-11 | 39 members embedded in <5 minutes | Phase 3 (perf) + Phase 5 | `emb-phase3-cron-integration`, `emb-phase5-backfill-validation` |
| AC-12 | `tools/list` returns 3 MCP tools | Phase 0 | `emb-phase0-mcp-server` |
| AC-13 | `read_document` returns resume text for valid URL | Phase 0 (mocked) + Phase 5 (real SA) | `emb-phase0-mcp-server`, `emb-phase5-backfill-validation` |
| AC-14 | SA credentials NOT in cron process env | Phase 2 | `emb-phase2-mcp-client-pipeline` |
| AC-15 | MCP server crash handled gracefully | Phase 2 | `emb-phase2-mcp-client-pipeline` |

### Risk Coverage Matrix

| Risk | Description (short) | Phase | Branch | Mitigation |
|------|---------------------|-------|--------|------------|
| R1 | Gemma quality lower than Gemini | Phase 1 + Phase 4 + Phase 5 | `emb-phase1-schema-model`, `emb-phase4-rag-multivector` | A/B test 10 samples; Gemini fallback via factory |
| R2 | Google Docs API quota during backfill | Phase 3 | `emb-phase3-cron-integration` | MCP 200ms rate limit (39 docs << 300 RPM limit) |
| R3 | CPU inference too slow at scale | Phase 3 | `emb-phase3-cron-integration` | Throughput test early; ONNX fallback documented |
| R4 | SA provisioning blocked | Pre-Phase 0 | — | Start InfoSec request before Phase 0; mock SA in tests |
| R5 | IVFFlat degrades at <100 rows | Phase 1 | `emb-phase1-schema-model` | Sequential scan auto-used; revisit `lists` at 1000+ rows |
| R6 | Memory pressure from Gemma | Phase 1 + Phase 3 | `emb-phase1-schema-model` | Load model only during cron; FP16 for GPU; unload after |
| R7 | `profile_url` stable but content changed | Phase 3 | `emb-phase3-cron-integration` | SHA-256 content hash detects changes regardless of URL |
| R8 | Private/unshared Google Docs | Phase 0 + Phase 5 | `emb-phase0-mcp-server`, `emb-phase5-backfill-validation` | MCP returns `permission_denied`; cron skips gracefully |
| R9 | MCP server subprocess crash mid-batch | Phase 0 + Phase 2 | `emb-phase0-mcp-server`, `emb-phase2-mcp-client-pipeline` | Max 3 reconnect attempts; partial progress via per-member commits |
| R10 | MCP SDK breaking change | Phase 0 | `emb-phase0-mcp-server` | Pin `mcp[cli]` exact version; integration test validates `tools/list` |
| R11 | STDIO buffer overflow on large docs | Phase 0 | `emb-phase0-mcp-server` | `MAX_DOC_SIZE_BYTES = 102400` (100KB); truncate and warn |
| R12 | MCP session startup latency | Phase 2 | `emb-phase2-mcp-client-pipeline` | Session-per-batch (amortized); `mcp_session_init_duration` metric monitored |

---

*Plan generated from CR-EMB-002 v2.0.0 specification. All section references (§) resolve to `specs/change-request/CR_resume_embedding_pipeline.md`.*  
*Codebase grounding: actual file paths and class names verified against workspace at generation time.*
