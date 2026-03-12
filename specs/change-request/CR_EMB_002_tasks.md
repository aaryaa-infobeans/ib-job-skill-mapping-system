# CR-EMB-002 Task Breakdown

**CR:** CR-EMB-002 v2.0.0
**Plan Version:** 1.0.0
**Generated:** 2026-03-10
**Status:** APPROVED FOR EXECUTION
**Depends On:** CR-PII-001 (HEAD `bca284b2d901` confirmed)
**Total Duration:** 17 working days
**Task Count:** TASK-EMB-001..TASK-EMB-065

---

## Table of Contents

- [Phase 0: MCP Google Drive Server](#phase-0-mcp-google-drive-server) — TASK-EMB-001..008
- [Phase 1: Schema & Embedding Model](#phase-1-schema--embedding-model) — TASK-EMB-009..019
- [Phase 2: MCP Client & Resume Pipeline](#phase-2-mcp-client--resume-pipeline) — TASK-EMB-020..029
- [Phase 3: Cron Integration](#phase-3-cron-integration) — TASK-EMB-030..040
- [Phase 4: RAG Multi-Vector Update](#phase-4-rag-multi-vector-update) — TASK-EMB-041..050
- [Phase 5: Backfill & Validation](#phase-5-backfill--validation) — TASK-EMB-051..060
- [Cross-Phase CI](#cross-phase-ci) — TASK-EMB-061..065

---

## Phase 0: MCP Google Drive Server

### Branch: `feature/emb-phase0-mcp-server`
### Days: 1–2

---

### Epic: Package Scaffold

#### TASK-EMB-001: Scaffold MCP Server Package Directory Structure

- **Description:** Create Python package skeleton for the MCP Google Drive server. Add `src/mcp_servers/__init__.py` and `src/mcp_servers/gdrive/__init__.py` with empty or minimal content. Create `tests/mcp_servers/__init__.py` for test discovery.
- **Inputs:** None (no prior phase dependency)
- **Outputs:** `src/mcp_servers/__init__.py`, `src/mcp_servers/gdrive/__init__.py`, `tests/mcp_servers/__init__.py`
- **Spec Refs:** Plan §3 | CR §3.4.1 | AC-12
- **Acceptance Criteria:** `python -c "import src.mcp_servers.gdrive"` executes without ImportError on a clean venv with `mcp[cli]` installed.
- **Definition of Done:**
  - [ ] `src/mcp_servers/__init__.py` created
  - [ ] `src/mcp_servers/gdrive/__init__.py` created
  - [ ] `tests/mcp_servers/__init__.py` created
  - [ ] No import errors from package root
- **Dependencies:** None
- **Owner:** Backend
- **Type:** Build

---

### Epic: SA Auth & Config

#### TASK-EMB-002: Implement MCP Server Configuration Module

- **Description:** Implement `src/mcp_servers/gdrive/config.py` exposing: `SA_KEY_PATH` (resolved from `GOOGLE_SERVICE_ACCOUNT_FILE` env var, default `/secrets/sa-key.json`), `DRIVE_SCOPES` (`["https://www.googleapis.com/auth/drive.readonly"]`), `RATE_LIMIT_DELAY_MS = 200`, `MAX_DOC_SIZE_BYTES = 102400`, `MAX_RETRIES = 3`.
- **Inputs:** Environment variable `GOOGLE_SERVICE_ACCOUNT_FILE`
- **Outputs:** `src/mcp_servers/gdrive/config.py`
- **Spec Refs:** Plan §3.3 | CR §3.4.1 | R8, R11
- **Acceptance Criteria:** `from src.mcp_servers.gdrive.config import SA_KEY_PATH, RATE_LIMIT_DELAY_MS` succeeds; `RATE_LIMIT_DELAY_MS == 200`; `MAX_DOC_SIZE_BYTES == 102400`.
- **Definition of Done:**
  - [ ] All five config values exported
  - [ ] `SA_KEY_PATH` reads from env var with `/secrets/sa-key.json` fallback
  - [ ] Module importable without a real SA key file present
- **Dependencies:** TASK-EMB-001
- **Owner:** Backend
- **Type:** Configure

---

### Epic: Tool Implementation

#### TASK-EMB-003: Implement FastMCP Server with Three Registered Tools

- **Description:** Implement `src/mcp_servers/gdrive/server.py` (~180 lines). Create a `FastMCP` instance named `"gdrive-resume-server"`. Register three tools via `@mcp.tool()`: `read_document(url, file_id)`, `search_files(query, max_results)`, `get_file_metadata(file_id)`. Implement `_get_drive_service()`, `_get_docs_service()`, `_extract_doc_id()`, `_read_structural_elements()` helpers. SA credentials loaded only inside this file via `config.SA_KEY_PATH`. Entry point: `if __name__ == "__main__": mcp.run(transport="stdio")`.
- **Inputs:** `src/mcp_servers/gdrive/config.py`, `mcp[cli]>=1.0`, `google-api-python-client>=2.120`, `google-auth>=2.28`
- **Outputs:** `src/mcp_servers/gdrive/server.py`
- **Spec Refs:** Plan §3.1, §3.2 | CR §3.4.1 | AC-12, AC-13 | R8, R9, R10, R11
- **Acceptance Criteria:** `python -m src.mcp_servers.gdrive.server` starts without error; a `tools/list` JSON-RPC 2.0 request returns exactly `read_document`, `search_files`, `get_file_metadata` (AC-12).
- **Definition of Done:**
  - [ ] `FastMCP` instance named `"gdrive-resume-server"` created
  - [ ] All three tools registered with correct input/output schemas
  - [ ] SA credentials loaded only inside server process (never passed to caller)
  - [ ] STDIO transport entry point present
  - [ ] `python -m src.mcp_servers.gdrive.server` starts without import error
- **Dependencies:** TASK-EMB-002
- **Owner:** Backend
- **Type:** Build

---

### Epic: Error Handling & Rate Limiting

#### TASK-EMB-004: Implement Rate Limiting and Structured Error Handling

- **Description:** Add 200ms inter-request rate limiter inside `server.py` enforced between Google API calls. Implement structured error responses: `{"error": "not_found", "text": ""}` for 404, `{"error": "permission_denied"}` for 403, `{"error": "quota_exceeded"}` after 3 retries, `{"warning": "truncated"}` for docs >100KB. Implement exponential backoff (1s, 2s, 4s) for transient failures. Truncate docs exceeding `MAX_DOC_SIZE_BYTES` before returning.
- **Inputs:** `src/mcp_servers/gdrive/server.py`, `src/mcp_servers/gdrive/config.py`
- **Outputs:** Updated `src/mcp_servers/gdrive/server.py` with rate limiter and error handlers
- **Spec Refs:** Plan §3.4 | CR §3.4.4 | R8, R11
- **Acceptance Criteria:** Mock Google API returning HTTP 404 → response contains `{"error": "not_found"}`; mock 150KB text → `len(result["text"]) <= 102400` and `"warning"` key present.
- **Definition of Done:**
  - [ ] 200ms delay enforced between consecutive Google API calls
  - [ ] All 5 error codes handled with structured `{"error": "<code>"}` responses
  - [ ] 100KB truncation with `{"warning": "truncated"}` in response
  - [ ] Exponential backoff: 3 retries at 1s, 2s, 4s before returning error
- **Dependencies:** TASK-EMB-003
- **Owner:** Backend
- **Type:** Build

---

### Epic: Unit Tests

#### TASK-EMB-005: Write MCP Server Unit Tests

- **Description:** Implement `tests/mcp_servers/test_gdrive_server.py` (~150 lines) with 10 tests using `unittest.mock.patch("googleapiclient.discovery.build")`. Tests must run without a real SA key, without DB, without cron. Cover: `test_tools_list_returns_three_tools`, `test_read_document_happy_path_google_doc`, `test_read_document_file_id_extraction`, `test_read_document_invalid_url_returns_error`, `test_read_document_404_returns_not_found`, `test_read_document_403_returns_permission_denied`, `test_read_document_oversized_truncates_at_100kb`, `test_search_files_returns_file_list`, `test_get_file_metadata_returns_dict`, `test_auth_config_reads_env_var`.
- **Inputs:** `src/mcp_servers/gdrive/server.py`, `src/mcp_servers/gdrive/config.py`, fixture dicts in `tests/fixtures/gdrive/sample_doc.json`
- **Outputs:** `tests/mcp_servers/test_gdrive_server.py`, `tests/fixtures/gdrive/sample_doc.json`
- **Spec Refs:** Plan §3.5, §3.6 | CR §6.5 | AC-12, AC-13
- **Acceptance Criteria:** `pytest tests/mcp_servers/test_gdrive_server.py -v` exits with code 0; all 10 tests pass.
- **Definition of Done:**
  - [ ] All 10 named tests implemented
  - [ ] Mocked via `unittest.mock.patch("googleapiclient.discovery.build")`
  - [ ] No real SA key, DB, or network required
  - [ ] `pytest tests/mcp_servers/ -v` exits 0
- **Dependencies:** TASK-EMB-004
- **Owner:** QA
- **Type:** Test

---

### Epic: Phase Gate & Rollback

#### TASK-EMB-006: Risk Gate RG-R10 — Verify tools/list Returns All Three Tools

- **Description:** Execute the RG-R10 risk gate check. Confirm that `tools/list` JSON-RPC call to the running MCP server returns exactly `read_document`, `search_files`, `get_file_metadata`. If any tool is missing after 3 server restart attempts, block Phase 0 merge. Record result in PR description.
- **Inputs:** `src/mcp_servers/gdrive/server.py` running on STDIO; Python MCP test client or in-process `server.list_tools()` call
- **Outputs:** Risk gate pass/fail record in PR description
- **Spec Refs:** Plan §3.6 | AC-12 | R10
- **Acceptance Criteria:** `tools/list` response contains `{"tools": [{"name": "read_document"}, {"name": "search_files"}, {"name": "get_file_metadata"}]}` — all three present (RG-R10 PASS). Any missing tool = RG-R10 FAIL → merge blocked.
- **Definition of Done:**
  - [ ] `tools/list` invoked against running server
  - [ ] All 3 tool names confirmed present
  - [ ] Result recorded in PR description
  - [ ] Merge blocked if any tool absent
- **Dependencies:** TASK-EMB-005
- **Owner:** QA
- **Type:** Verify

---

#### TASK-EMB-007: Phase Gate GATE-0 — MCP Server Standalone Verification

- **Description:** Execute GATE-0 exit criteria. Run `python -m src.mcp_servers.gdrive.server` and confirm: (1) server starts without error, (2) `tools/list` returns 3 tools (AC-12), (3) all 10 unit tests pass, (4) code reviewed and merged. Document that AC-13 real-SA test is deferred to Phase 5. This gate blocks Phase 2.
- **Inputs:** All Phase 0 deliverables merged to `feature/emb-phase0-mcp-server`
- **Outputs:** GATE-0 checklist signed off in PR; merge to integration branch
- **Spec Refs:** Plan §1 (Phase 0 Exit Criteria) | AC-12 | R10
- **Acceptance Criteria:** All Phase 0 DoD checkboxes ticked; `pytest tests/mcp_servers/ -v` passes; peer review complete; branch merged.
- **Definition of Done:**
  - [ ] Server starts without error
  - [ ] `tools/list` returns 3 tools (AC-12 satisfied)
  - [ ] All 10 unit tests green
  - [ ] AC-13 deferral to Phase 5 documented
  - [ ] Code reviewed and merged to `feature/emb-phase0-mcp-server`
  - [ ] GATE-0 signed off — Phase 2 unblocked
- **Dependencies:** TASK-EMB-006
- **Owner:** Backend
- **Type:** Validate

---

#### TASK-EMB-008: Phase 0 Rollback — Delete MCP Server Package

- **Description:** Document and test the Phase 0 rollback procedure. Rollback: `rm -rf src/mcp_servers/`; verify that `python -m app.cron.main ingest` still succeeds (no import of mcp_servers in cron path). No DB changes; zero-risk rollback. Trigger condition: server fails `tools/list` after 3 restart attempts OR SA credential loading causes security audit failure.
- **Inputs:** `src/mcp_servers/` directory tree
- **Outputs:** Verified rollback procedure documented; cron ingest unaffected
- **Spec Refs:** Plan §12.1 | R10
- **Acceptance Criteria:** After `rm -rf src/mcp_servers/`, `python -m app.cron.main ingest` exits 0 without ImportError.
- **Definition of Done:**
  - [ ] Rollback steps documented in PR/runbook
  - [ ] Verified: cron ingest mode unaffected after `src/mcp_servers/` removal
  - [ ] No DB state changes introduced in Phase 0 (confirmed)
- **Dependencies:** TASK-EMB-007
- **Owner:** DevOps
- **Type:** Validate

---

## Phase 1: Schema & Embedding Model

### Branch: `feature/emb-phase1-schema-model`
### Days: 3–5

---

### Epic: Dependency Pinning

#### TASK-EMB-009: Pin New Python Dependencies in requirements.txt

- **Description:** Add pinned versions for all new Phase 1 dependencies to `requirements.txt`: `transformers>=4.40`, `torch` (CPU-only variant), `sentencepiece>=0.2.0`, `mcp[cli]>=1.0`, `google-auth>=2.28`, `google-api-python-client>=2.120`. Verify CPU-only `torch` install size (~200MB acceptable). Confirm `mcp[cli]` is compatible with Python 3.13. Record exact resolved versions.
- **Inputs:** Current `requirements.txt`, Python 3.13 environment
- **Outputs:** Updated `requirements.txt` with 6 new pinned dependencies
- **Spec Refs:** Plan §1 (Phase 1 Entry Criteria) | CR §6.3.1 | R6
- **Acceptance Criteria:** `pip install -r requirements.txt` completes without conflict; `python -c "import transformers, torch, mcp"` succeeds.
- **Definition of Done:**
  - [ ] All 6 packages added with version constraints
  - [ ] CPU-only `torch` variant specified (not full CUDA build)
  - [ ] `pip install -r requirements.txt` exits 0 in clean venv
  - [ ] Python 3.13 compatibility confirmed for `mcp[cli]`
- **Dependencies:** None
- **Owner:** Backend
- **Type:** Configure

---

### Epic: Alembic Migration

#### TASK-EMB-010: Create Alembic Migration — Add Multi-Vector Embedding Columns

- **Description:** Generate Alembic migration `alembic/versions/<rev_id>_add_multi_vector_embeddings.py` with `down_revision='bca284b2d901'`. The `upgrade()` adds 10 columns to `team_member_embeddings`: `resume_embedding Vector(768) nullable`, `skills_embedding Vector(768) nullable`, `certifications_embedding Vector(768) nullable`, `resume_text Text nullable`, `skills_text Text nullable`, `certifications_text Text nullable`, `embedding_model String(100) server_default='embedding-gemma-300m'`, `content_hash CHAR(64) nullable`, `resume_fetched_at DateTime nullable`, `embedding_updated_at DateTime nullable`. Creates 4 indexes: `idx_tme_resume_embedding` (IVFFlat, lists=10), `idx_tme_skills_embedding` (IVFFlat, lists=10), `idx_tme_certifications_embedding` (IVFFlat, lists=10), `idx_tme_content_hash` (B-tree). The `downgrade()` drops all 4 indexes then all 10 columns in reverse order.
- **Inputs:** Staging DB at HEAD `bca284b2d901` confirmed; `pgvector` extension installed
- **Outputs:** `alembic/versions/<rev_id>_add_multi_vector_embeddings.py`
- **Spec Refs:** Plan §4 | CR §3.2, §5.1 | AC-9 | R5
- **Acceptance Criteria:**
  ```bash
  alembic upgrade head
  # Verify:
  SELECT column_name FROM information_schema.columns
  WHERE table_name = 'team_member_embeddings'
  ORDER BY column_name;
  # Must include all 10 new columns
  alembic downgrade bca284b2d901
  # Verify: 10 new columns absent; original 7 columns intact
  alembic upgrade head
  # Verify: re-application succeeds (idempotency — AC-9)
  ```
- **Definition of Done:**
  - [ ] `down_revision='bca284b2d901'` set correctly
  - [ ] `upgrade()` adds all 10 columns with correct types and nullability
  - [ ] `embedding_model` has `server_default='embedding-gemma-300m'`
  - [ ] All 4 indexes created in `upgrade()`; dropped in `downgrade()`
  - [ ] Full roundtrip (upgrade → downgrade → upgrade) passes on staging DB (AC-9)
- **Dependencies:** TASK-EMB-009
- **Owner:** Backend
- **Type:** Build

---

### Epic: SQLAlchemy Model Update

#### TASK-EMB-011: Update TeamMemberEmbedding SQLAlchemy Model

- **Description:** Update `src/app/db/models/models.py` at the `TeamMemberEmbedding` class (currently line 287). Add all 10 new column definitions matching the migration schema: `resume_embedding`, `skills_embedding`, `certifications_embedding` as `Vector(768)` nullable; text columns as `Text` nullable; `embedding_model` as `String(100)` with `server_default`; `content_hash` as `CHAR(64)` nullable; `resume_fetched_at`, `embedding_updated_at` as `DateTime` nullable.
- **Inputs:** `alembic/versions/<rev_id>_add_multi_vector_embeddings.py` (column spec), `src/app/db/models/models.py`
- **Outputs:** Updated `src/app/db/models/models.py`
- **Spec Refs:** Plan §4.1 | CR §3.2.1 | AC-4
- **Acceptance Criteria:** `from src.app.db.models.models import TeamMemberEmbedding; assert hasattr(TeamMemberEmbedding, 'resume_embedding')` — all 10 new attributes accessible without error.
- **Definition of Done:**
  - [ ] All 10 new columns declared on `TeamMemberEmbedding`
  - [ ] Column types match migration exactly
  - [ ] No regressions to existing 7 columns
  - [ ] Import succeeds without DB connection
- **Dependencies:** TASK-EMB-010
- **Owner:** Backend
- **Type:** Build

---

### Epic: Alembic Migration (continued)

#### TASK-EMB-012: Update ACCEPTABLE_REVISIONS in migrations_check.py

- **Description:** Add the new Alembic revision ID (generated by TASK-EMB-010) to the `ACCEPTABLE_REVISIONS` set in `src/app/cron/db/migrations_check.py`. Current set has 11 entries with HEAD `bca284b2d901`; after this task it must have 12 entries. Verify the cron migration check passes with the new revision applied.
- **Inputs:** New revision ID from TASK-EMB-010; `src/app/cron/db/migrations_check.py`
- **Outputs:** Updated `src/app/cron/db/migrations_check.py`
- **Spec Refs:** Plan §4.4 | CR §5.1
- **Acceptance Criteria:** `python -m app.cron.main ingest` does not exit with code 3 (SCHEMA_MISMATCH) after `alembic upgrade head` applied. `len(ACCEPTABLE_REVISIONS) == 12`.
- **Definition of Done:**
  - [ ] New revision ID string added to `ACCEPTABLE_REVISIONS`
  - [ ] `len(ACCEPTABLE_REVISIONS) == 12`
  - [ ] Cron schema check passes on staging DB at new HEAD
- **Dependencies:** TASK-EMB-010
- **Owner:** Backend
- **Type:** Configure

---

### Epic: Model Factory & Settings

#### TASK-EMB-013: Add Embedding Settings to src/app/settings.py

- **Description:** Add four new settings to `src/app/settings.py`: `embedding_model_name` (default `"embedding-gemma-300m"`), `gemma_model_path` (default `None`; resolves to HuggingFace cache if None), `embedding_device` (default `"cpu"`), `mcp_gdrive_server_path` (default `"src/mcp_servers/gdrive/server.py"`). Settings must be overridable via environment variables.
- **Inputs:** `src/app/settings.py`
- **Outputs:** Updated `src/app/settings.py`
- **Spec Refs:** Plan §5 | CR §4.2 (Appendix D) | R6
- **Acceptance Criteria:** `from src.app.settings import settings; assert settings.embedding_device == "cpu"` passes without env override. Setting `EMBEDDING_DEVICE=cuda` env var causes `settings.embedding_device == "cuda"`.
- **Definition of Done:**
  - [ ] All 4 new settings added
  - [ ] Each overridable via env var
  - [ ] Default `embedding_device="cpu"` confirmed
- **Dependencies:** None (can run in parallel with TASK-EMB-010)
- **Owner:** Backend
- **Type:** Configure

---

### Epic: GemmaEmbeddingAgent

#### TASK-EMB-014: Implement GemmaEmbeddingAgent Class

- **Description:** Implement `src/app/ai/utils/gemma_embedding.py` (~130 lines). Class `GemmaEmbeddingAgent`: `MODEL_NAME = "google/embedding-gemma-300m"`, `DIMENSION = 768`, `MAX_TOKENS = 2048`. `__init__(device="cpu")` loads `AutoTokenizer` and `AutoModel` from `MODEL_NAME` using `torch_dtype=torch.float32` for CPU, `torch.float16` otherwise. `embed_text(text: str) -> np.ndarray` tokenizes → forward pass → mean pooling over valid tokens → L2 normalize → returns `(768,)` ndarray. `embed_batch(texts: list[str]) -> list[np.ndarray]` batched variant. Model loading must be separated from inference (load in `__init__`, infer in `embed_text`/`embed_batch`) to enable memory profiling (R6).
- **Inputs:** `transformers>=4.40`, `torch`, `sentencepiece>=0.2.0`, `src/app/settings.py`
- **Outputs:** `src/app/ai/utils/gemma_embedding.py`
- **Spec Refs:** Plan §5.1, §5.2, §5.3 | CR §3.3, §3.3.2 | AC-4 | R6
- **Acceptance Criteria:** With mocked `AutoModel.from_pretrained` returning fixed tensors: `GemmaEmbeddingAgent().embed_text("test")` returns ndarray of shape `(768,)` with L2 norm ≈ 1.0 (±1e-6). `GemmaEmbeddingAgent.MODEL_NAME == "google/embedding-gemma-300m"`.
- **Definition of Done:**
  - [ ] `embed_text()` returns `(768,)` unit-norm ndarray
  - [ ] `embed_batch()` returns list of `(768,)` arrays
  - [ ] Model loading in `__init__`; inference in separate methods
  - [ ] FP16 selected when `device != "cpu"` (R6 mitigation)
  - [ ] `MODEL_NAME` constant set to `"google/embedding-gemma-300m"`
- **Dependencies:** TASK-EMB-009, TASK-EMB-013
- **Owner:** AI
- **Type:** Build

---

#### TASK-EMB-015: Implement get_embedding_agent() Model Factory

- **Description:** Add `get_embedding_agent()` factory function to `src/app/ai/utils/embedding.py`. Reads `settings.embedding_model_name`. If `"embedding-gemma-300m"`: returns `GemmaEmbeddingAgent(device=settings.embedding_device)`. If `"gemini-embedding-001"` or any `gemini-*`: returns existing `EmbeddingAgent()`. Factory enables R1 A/B testing by swapping agents without code changes.
- **Inputs:** `src/app/ai/utils/embedding.py`, `src/app/ai/utils/gemma_embedding.py`, `src/app/settings.py`
- **Outputs:** Updated `src/app/ai/utils/embedding.py` with `get_embedding_agent()`
- **Spec Refs:** Plan §5.4 | CR §2.1 | R1
- **Acceptance Criteria:** `get_embedding_agent()` with `EMBEDDING_MODEL=embedding-gemma-300m` returns `GemmaEmbeddingAgent` instance. With `EMBEDDING_MODEL=gemini-embedding-001` returns existing `EmbeddingAgent` instance.
- **Definition of Done:**
  - [ ] Factory reads `settings.embedding_model_name`
  - [ ] Returns correct agent type per setting
  - [ ] Gemini fallback path unchanged
  - [ ] A/B test path documented in docstring
- **Dependencies:** TASK-EMB-014
- **Owner:** AI
- **Type:** Build

---

### Epic: Unit Tests

#### TASK-EMB-016: Write GemmaEmbeddingAgent Unit Tests

- **Description:** Implement `tests/ai/test_gemma_embedding.py` (~100 lines). Patch `AutoModel.from_pretrained` and `AutoTokenizer.from_pretrained` to return mocks producing fixed tensors. Cover: `test_gemma_agent_embed_text_returns_768_dim_unit_vector`, `test_gemma_agent_embed_batch_returns_list`, `test_gemma_agent_model_name_constant`, `test_gemma_agent_fp16_on_non_cpu_device`, `test_gemma_agent_fp32_on_cpu_device`. Add performance test: `test_throughput_100_texts` — embed 100 fixed-length strings; assert elapsed < 60s on CPU (≥100 members/minute — R3 / AC-11).
- **Inputs:** `src/app/ai/utils/gemma_embedding.py`
- **Outputs:** `tests/ai/test_gemma_embedding.py`, `tests/fixtures/embeddings/sample_768.npy`
- **Spec Refs:** Plan §5.5, §9.3 | CR §6.5 | AC-11 | R3, R6
- **Acceptance Criteria:** `pytest tests/ai/test_gemma_embedding.py -v` exits 0; ≥5 unit tests + 1 throughput test pass.
- **Definition of Done:**
  - [ ] ≥5 unit tests pass (mocked model)
  - [ ] `test_throughput_100_texts` passes (100 texts < 60s CPU)
  - [ ] FP16/FP32 dtype switching verified
  - [ ] No real model download required for tests
- **Dependencies:** TASK-EMB-014
- **Owner:** QA
- **Type:** Test

---

### Epic: Phase Gate & Rollback

#### TASK-EMB-017: Risk Gate RG-R6 — Verify Gemma Model Memory Footprint

- **Description:** Execute RG-R6 check. Load `GemmaEmbeddingAgent()` in a subprocess; measure RSS memory before and after model load using `psutil.Process().memory_info().rss`. Assert RSS increase < 2GB (FP32 CPU path expected ~1.2GB). If RSS > 2GB: block Phase 3 merge and escalate. Document result in PR.
- **Inputs:** `src/app/ai/utils/gemma_embedding.py`, `psutil`
- **Outputs:** Memory measurement log in PR description
- **Spec Refs:** Plan §5.3 | R6
- **Acceptance Criteria:** RSS increase from model load < 2,000,000,000 bytes (2GB). RG-R6 PASS if < 2GB; FAIL (blocks Phase 3 merge) if ≥ 2GB.
- **Definition of Done:**
  - [ ] RSS measured before/after `GemmaEmbeddingAgent()` instantiation
  - [ ] Result documented: measured RSS increase in MB
  - [ ] RG-R6 PASS/FAIL verdict recorded in PR
- **Dependencies:** TASK-EMB-014
- **Owner:** Platform
- **Type:** Verify

---

#### TASK-EMB-018: Phase Gate GATE-1 — Alembic Roundtrip and 768-dim Vector Output

- **Description:** Execute GATE-1 exit criteria. Confirm: (1) `alembic upgrade head` → `alembic downgrade bca284b2d901` → `alembic upgrade head` all succeed on staging DB (AC-9); (2) `GemmaEmbeddingAgent().embed_text("test")` returns `ndarray` of shape `(768,)` with L2 norm ≈ 1.0; (3) `SELECT DISTINCT embedding_model FROM team_member_embeddings` returns `('embedding-gemma-300m',)` for any existing rows with default applied; (4) all unit tests pass. This gate blocks Phase 3.
- **Inputs:** All Phase 1 deliverables on staging DB
- **Outputs:** GATE-1 checklist signed off; branch merged
- **Spec Refs:** Plan §1 (Phase 1 Exit Criteria) | AC-4, AC-9
- **Acceptance Criteria:**
  ```sql
  SELECT DISTINCT embedding_model FROM team_member_embeddings;
  -- Expected: ('embedding-gemma-300m',)
  ```
  Alembic roundtrip exits 0 all three steps; `ndarray.shape == (768,)`; `np.linalg.norm(ndarray) ≈ 1.0`.
- **Definition of Done:**
  - [ ] Alembic roundtrip passes (AC-9)
  - [ ] `embed_text("test")` returns shape `(768,)` unit vector
  - [ ] `embedding_model` default `'embedding-gemma-300m'` confirmed (AC-4)
  - [ ] `ACCEPTABLE_REVISIONS` updated (TASK-EMB-012)
  - [ ] All unit tests pass (≥5 in `test_gemma_embedding.py`)
  - [ ] Code reviewed and merged
  - [ ] GATE-1 signed off — Phase 3 unblocked
- **Dependencies:** TASK-EMB-016, TASK-EMB-017, TASK-EMB-012
- **Owner:** Backend
- **Type:** Validate

---

#### TASK-EMB-019: Phase 1 Rollback — alembic downgrade bca284b2d901

- **Description:** Document and verify the Phase 1 rollback procedure. Rollback: `alembic downgrade bca284b2d901`; revert `models.py`, `settings.py`, `migrations_check.py` to pre-phase state. Verify all 10 new columns are dropped; original 7 columns intact; no data loss in pre-existing rows. Trigger conditions: migration fails on staging, or `torch` RSS exceeds host budget (R6 FAIL from TASK-EMB-017).
- **Inputs:** Staging DB at new HEAD; original `models.py` revision
- **Outputs:** Verified rollback procedure documented
- **Spec Refs:** Plan §12.1 | AC-9 | R6
- **Acceptance Criteria:**
  ```sql
  -- After alembic downgrade bca284b2d901:
  SELECT column_name FROM information_schema.columns
  WHERE table_name = 'team_member_embeddings';
  -- Must NOT include resume_embedding, skills_embedding, etc.
  -- Must include original 7 columns
  ```
- **Definition of Done:**
  - [ ] `alembic downgrade bca284b2d901` executes without error
  - [ ] All 10 new columns absent after downgrade
  - [ ] Original 7 columns intact
  - [ ] Existing row data in original columns unaffected
  - [ ] Rollback steps documented
- **Dependencies:** TASK-EMB-018
- **Owner:** Backend
- **Type:** Validate

---

## Phase 2: MCP Client & Resume Pipeline

### Branch: `feature/emb-phase2-mcp-client-pipeline`
### Days: 6–8

---

### Epic: MCP Client Wrapper (STDIO, session-per-batch)

#### TASK-EMB-020: Scaffold cron/embedding Package

- **Description:** Create the `src/app/cron/embedding/` Python package. Add `src/app/cron/embedding/__init__.py`. Create `tests/cron/__init__.py` if not already present.
- **Inputs:** Phase 0 merged (`src/mcp_servers/gdrive/server.py` available)
- **Outputs:** `src/app/cron/embedding/__init__.py`, `tests/cron/__init__.py`
- **Spec Refs:** Plan §6 | CR §2.1
- **Acceptance Criteria:** `python -c "import src.app.cron.embedding"` succeeds without error.
- **Definition of Done:**
  - [ ] Package `__init__.py` created
  - [ ] Import succeeds
- **Dependencies:** TASK-EMB-007 (Phase 0 gate)
- **Owner:** Backend
- **Type:** Build

---

#### TASK-EMB-021: Implement MCPResumeClient with STDIO Subprocess Management

- **Description:** Implement `src/app/cron/embedding/mcp_client.py` (~120 lines). Class `MCPResumeClient`: `__init__(server_script)` creates `StdioServerParameters` with SA key passed **only to subprocess env** (not to cron process env). `fetch_resume(profile_url) -> dict | None` is async: enters `stdio_client()` context, creates `ClientSession`, calls `session.initialize()`, calls `session.call_tool("read_document", {"url": profile_url})`, returns parsed JSON dict. `fetch_resume_sync(profile_url) -> str | None` wraps with `asyncio.run()`; returns `result["text"]` or `None`. Session lifecycle: one session held open per batch (session-per-batch pattern — amortize 500ms init cost over full 39-member batch).
- **Inputs:** `mcp[cli]>=1.0`, `src/mcp_servers/gdrive/server.py` (Phase 0), Phase 1 DB model
- **Outputs:** `src/app/cron/embedding/mcp_client.py`
- **Spec Refs:** Plan §6.1, §6.3 | CR §3.4.2 | AC-14 | R12
- **Acceptance Criteria:** `MCPResumeClient.fetch_resume_sync("https://docs.google.com/...")` with mocked `ClientSession` returns non-empty string. `StdioServerParameters` env dict contains `GOOGLE_SERVICE_ACCOUNT_FILE`; cron process `os.environ` does NOT contain it (AC-14).
- **Definition of Done:**
  - [ ] `fetch_resume_sync()` implemented as sync wrapper over async `fetch_resume()`
  - [ ] `StdioServerParameters` passes SA key only to subprocess env
  - [ ] Session-per-batch lifecycle managed in context manager
  - [ ] Returns `None` (not raises) on empty doc or parse error
- **Dependencies:** TASK-EMB-020
- **Owner:** Backend
- **Type:** Build

---

#### TASK-EMB-022: Implement Broken-Pipe Recovery and Graceful Server Failure Handling

- **Description:** Add broken-pipe and server crash recovery to `MCPResumeClient`. On `BrokenPipeError` or any connection exception from `session.call_tool()`: (1) log member ID and exception type, (2) attempt subprocess restart (max 3 attempts, 2s delay), (3) if 3 consecutive failures: abort resume fetching for all remaining members, continue with skills/certs-only embedding. Return `None` for any failed member (never raise). Set cron exit code to `EXIT_PARTIAL` (1) not `EXIT_FATAL` (2) if >0 members succeeded. Per-member partial progress is preserved via Phase 3 per-member commits.
- **Inputs:** `src/app/cron/embedding/mcp_client.py`
- **Outputs:** Updated `src/app/cron/embedding/mcp_client.py` with retry/recovery logic
- **Spec Refs:** Plan §6.2, §6.4 | CR §3.4.4 | AC-15 | R9
- **Acceptance Criteria:** Mock `session.call_tool` raising `BrokenPipeError` 3 times: retry count = 3, then `fetch_resume_sync()` returns `None` without raising. Mock SIGKILL on subprocess mid-session: cron continues, remaining members processed without resume text.
- **Definition of Done:**
  - [ ] Max 3 reconnect attempts with 2s delay between
  - [ ] Returns `None` after 3 consecutive failures (never raises)
  - [ ] `EXIT_PARTIAL` (code 1) set when some members failed, some succeeded
  - [ ] Per-member commit approach means prior successes not lost on failure
- **Dependencies:** TASK-EMB-021
- **Owner:** Backend
- **Type:** Build

---

### Epic: Text Assembler

#### TASK-EMB-023: Implement Text Assembler for Resume, Skills, and Certifications

- **Description:** Implement `src/app/cron/embedding/text_assembler.py` (~120 lines) with three pure functions: `assemble_resume_text(team_member, resume_content) -> str` (no DB call; uses passed ORM object for designation, location, work_type, experience_in_months, prepends structured header to resume content); `assemble_skills_text(member_id, db) -> str` (JOINs `team_member_skill` → `skill_master` → `category_master`; maps rating ≥8 → Expert, ≥5 → Intermediate, else → Beginner; returns `""` if no skills); `assemble_certifications_text(member_id, db) -> str` (JOINs `team_member_skill_certification` → `team_member_skill` → `skill_master`; status = Active if `valid_till >= date.today()` else Expired; returns `""` if no certs).
- **Inputs:** `src/app/db/models/models.py` (Phase 1 — updated schema), SQLAlchemy session
- **Outputs:** `src/app/cron/embedding/text_assembler.py`
- **Spec Refs:** Plan §6.5 | CR §3.5 | AC-5
- **Acceptance Criteria:** `assemble_skills_text(member_id, db)` with mock DB returning 1 skill (rating=9) → output contains `"Expert"`. `assemble_certifications_text()` with no certs → returns `""`. `assemble_resume_text()` output contains `"Designation:"` and `"Resume:"`.
- **Definition of Done:**
  - [ ] All three functions implemented and return correct formats
  - [ ] Empty inputs return `""` for skills and certs assemblers
  - [ ] No side effects beyond DB reads
  - [ ] Text format matches CR Appendix B and C examples
- **Dependencies:** TASK-EMB-011 (Phase 1 model), TASK-EMB-020
- **Owner:** Backend
- **Type:** Build

---

### Epic: Cron Config Extension

#### TASK-EMB-024: Extend Cron Config with MCP and Embedding Settings

- **Description:** Add six new fields to `src/app/cron/config.py`: `embedding_model` (default `"embedding-gemma-300m"`), `mcp_server_script` (default `"src/mcp_servers/gdrive/server.py"`), `mcp_server_env` (dict, default `{}`), `embedding_batch_size` (default `32`), `force_re_embed` (bool, default `False`), `mcp_client_max_retries` (default `3`).
- **Inputs:** `src/app/cron/config.py`
- **Outputs:** Updated `src/app/cron/config.py`
- **Spec Refs:** Plan §6 | CR §3.7, Appendix D
- **Acceptance Criteria:** `from src.app.cron.config import CronConfig; c = CronConfig(); assert c.embedding_batch_size == 32` passes.
- **Definition of Done:**
  - [ ] All 6 new fields added
  - [ ] Existing config fields unmodified
  - [ ] Defaults match spec
- **Dependencies:** TASK-EMB-020
- **Owner:** Backend
- **Type:** Configure

---

### Epic: Credential Isolation

#### TASK-EMB-025: Verify and Test Credential Isolation (AC-14)

- **Description:** Write explicit test asserting credential isolation. In `tests/cron/test_mcp_client.py`, add `test_credential_isolation_env_not_in_cron_process`: set up a controlled env without `GOOGLE_SERVICE_ACCOUNT_FILE`; instantiate `MCPResumeClient`; assert `"GOOGLE_SERVICE_ACCOUNT_FILE" not in os.environ`. Confirm `StdioServerParameters` env dict contains the key. Document K8s pod spec requirement: SA key secret mounted as file, path injected only into MCP server subprocess env.
- **Inputs:** `src/app/cron/embedding/mcp_client.py`
- **Outputs:** Credential isolation test in `tests/cron/test_mcp_client.py`; K8s spec note in PR
- **Spec Refs:** Plan §6.3 | CR §3.4.2, §6.4 | AC-14
- **Acceptance Criteria:** `test_credential_isolation_env_not_in_cron_process` passes. K8s pod spec requirement documented.
- **Definition of Done:**
  - [ ] Test asserts `GOOGLE_SERVICE_ACCOUNT_FILE not in os.environ` in cron process
  - [ ] `StdioServerParameters.env` contains SA key (subprocess only)
  - [ ] K8s deployment note documented in PR description
- **Dependencies:** TASK-EMB-021
- **Owner:** Security
- **Type:** Verify

---

### Epic: Unit Tests

#### TASK-EMB-026: Write MCP Client Unit Tests

- **Description:** Implement `tests/cron/test_mcp_client.py` (~120 lines) covering: `test_session_lifecycle_init_call_close` (verify `initialize()`, `call_tool()`, session closed in order), `test_fetch_resume_sync_returns_text` (mock returns `{"text": "resume content"}`), `test_fetch_resume_sync_empty_doc_returns_none` (mock returns `{"text": ""}`), `test_broken_pipe_triggers_reconnect_max_3` (mock raises `BrokenPipeError` 3 times; assert 3 retries then `None`), `test_credential_isolation_env_not_in_cron_process`, `test_server_crash_returns_none_gracefully`. Mock strategy: `AsyncMock` for `ClientSession`, patch `stdio_client` context manager.
- **Inputs:** `src/app/cron/embedding/mcp_client.py`
- **Outputs:** `tests/cron/test_mcp_client.py`
- **Spec Refs:** Plan §9.2 | CR §6.5 | AC-14, AC-15 | R9
- **Acceptance Criteria:** `pytest tests/cron/test_mcp_client.py -v` exits 0; all 6 tests pass.
- **Definition of Done:**
  - [ ] All 6 named tests implemented
  - [ ] `AsyncMock` used for session methods
  - [ ] No real MCP server or SA key needed
  - [ ] `pytest tests/cron/test_mcp_client.py -v` exits 0
- **Dependencies:** TASK-EMB-022, TASK-EMB-025
- **Owner:** QA
- **Type:** Test

---

#### TASK-EMB-027: Write Text Assembler Unit Tests

- **Description:** Implement `tests/cron/test_text_assembler.py` (~150 lines) covering: `test_assemble_resume_text_includes_designation_location`, `test_assemble_skills_text_expert_label_for_rating_gte_8`, `test_assemble_skills_text_intermediate_for_rating_5_to_7`, `test_assemble_skills_text_empty_skills_returns_empty_string`, `test_assemble_certifications_text_active_status_for_future_date`, `test_assemble_certifications_text_expired_status_for_past_date`, `test_assemble_certifications_text_no_certs_returns_empty_string`. Mock DB session using MagicMock with `.query().join().filter().all()` returning fixture data.
- **Inputs:** `src/app/cron/embedding/text_assembler.py`
- **Outputs:** `tests/cron/test_text_assembler.py`
- **Spec Refs:** Plan §9.3 | CR §3.5 | AC-5
- **Acceptance Criteria:** `pytest tests/cron/test_text_assembler.py -v` exits 0; ≥7 tests pass.
- **Definition of Done:**
  - [ ] ≥7 tests cover both happy paths and empty-return cases
  - [ ] Proficiency label logic tested (Expert/Intermediate/Beginner)
  - [ ] Active/Expired cert status logic tested
  - [ ] No real DB needed
- **Dependencies:** TASK-EMB-023
- **Owner:** QA
- **Type:** Test

---

### Epic: Phase Gate & Rollback

#### TASK-EMB-028: Risk Gate RG-R9 — Verify No Fatal Failure on 3 MCP Reconnects

- **Description:** Execute RG-R9 risk gate. Simulate 3 consecutive MCP subprocess crashes using `test_broken_pipe_triggers_reconnect_max_3` harness. Confirm: cron does NOT exit with code 2 (FATAL); remaining members (skills/certs) are still processed; partial results committed. If 3 consecutive crashes cause cron to abort or corrupt data: block Phase 2 merge.
- **Inputs:** `tests/cron/test_mcp_client.py::test_broken_pipe_triggers_reconnect_max_3`
- **Outputs:** RG-R9 PASS/FAIL verdict in PR
- **Spec Refs:** Plan §6.2 | CR §3.4.4 | R9
- **Acceptance Criteria:** After 3 `BrokenPipeError`s: `fetch_resume_sync()` returns `None`; cron exit code is `EXIT_PARTIAL` (1) not `EXIT_FATAL` (2); no exception propagated. RG-R9 FAIL = any of these violated → merge blocked.
- **Definition of Done:**
  - [ ] Simulated 3-crash scenario executed
  - [ ] Exit code verified (1, not 2)
  - [ ] No exception raised to caller
  - [ ] RG-R9 verdict recorded in PR
- **Dependencies:** TASK-EMB-026
- **Owner:** QA
- **Type:** Verify

---

#### TASK-EMB-029: Phase 2 Rollback — Delete cron/embedding Package

- **Description:** Document and verify the Phase 2 rollback procedure. Rollback: `rm -rf src/app/cron/embedding/`; revert `src/app/cron/config.py` to pre-phase state. Verify that `python -m app.cron.main ingest` and `python -m app.cron.main retry` still succeed. No DB impact. Trigger conditions: STDIO subprocess management causes cron wall-clock > 30 min, or MCP session overhead (R12) measured >5s/member.
- **Inputs:** `src/app/cron/embedding/` package, `src/app/cron/config.py`
- **Outputs:** Verified rollback procedure documented
- **Spec Refs:** Plan §12.1 | R12
- **Acceptance Criteria:** After removing `src/app/cron/embedding/` and reverting `config.py`: `python -m app.cron.main ingest` exits 0; `python -m app.cron.main retry` exits 0.
- **Definition of Done:**
  - [ ] Rollback steps documented
  - [ ] Verified: ingest and retry modes unaffected
  - [ ] No DB state change from Phase 2 (confirmed)
- **Dependencies:** TASK-EMB-028
- **Owner:** DevOps
- **Type:** Validate

---

## Phase 3: Cron Integration

### Branch: `feature/emb-phase3-cron-integration`
### Days: 9–12

---

### Epic: EmbeddingProcessor (SHA-256, per-member commit)

#### TASK-EMB-030: Implement EmbeddingProcessor Core Orchestration

- **Description:** Implement `src/app/cron/embedding/embedding_processor.py` (~200 lines). Class `EmbeddingProcessor(__init__(db, mcp_client, embedding_agent, settings))`. Method `run(force=False) -> ProcessingResult`: (1) `SELECT team_member WHERE is_deleted = False ORDER BY team_member_id`; (2) for each member: fetch `profile_url`, fetch current `content_hash`, assemble `skills_text` and `certifications_text`; (3) if `profile_url`: fetch `resume_text` via `MCPResumeClient`; (4) scrub `resume_text` via PII scrubber; (5) compute `new_hash = sha256(f"{resume_text}||{skills_text}||{certs_text}".encode("utf-8")).hexdigest()`; (6) if `new_hash == stored_hash AND NOT force`: skip and increment `skip_count`; (7) else: embed all three → call `upsert_team_member_embeddings()` → commit per-member. Returns `ProcessingResult(success_count, skip_count, error_count, error_members: list[str])`.
- **Inputs:** Phase 1 (`GemmaEmbeddingAgent`, `TeamMemberEmbedding` model), Phase 2 (`MCPResumeClient`, `text_assembler`), `src/app/cron/db/repositories.py`
- **Outputs:** `src/app/cron/embedding/embedding_processor.py`
- **Spec Refs:** Plan §7.2, §7.3, §7.4 | CR §3.6 | AC-1, AC-6 | R7
- **Acceptance Criteria:** On second run with no data changes, `ProcessingResult.skip_count == total_member_count` (all skipped — AC-6). SHA-256 of identical content produces identical hash (deterministic).
- **Definition of Done:**
  - [ ] `run()` implements all 7 steps in order
  - [ ] SHA-256 hash computed from `f"{resume_text}||{skills_text}||{certs_text}"`
  - [ ] Hash-match skip logic implemented (AC-6)
  - [ ] `ProcessingResult` dataclass returned with all four fields
  - [ ] Per-member commit after each successful upsert
- **Dependencies:** TASK-EMB-011, TASK-EMB-014, TASK-EMB-021, TASK-EMB-023
- **Owner:** Backend
- **Type:** Build

---

#### TASK-EMB-031: Integrate PII Scrubber for Resume Text Pre-Processing

- **Description:** In `EmbeddingProcessor.run()`, call the PII scrubber (from `src/app/ai/agents/pii_scrubber.py`) on `resume_text` before any embedding or DB write. Scrubbing must occur AFTER fetching from MCP and BEFORE storing in `resume_text` column. If scrubber returns empty string, treat as empty resume (skip resume embedding, leave `resume_embedding = NULL`). Log scrubber call per member for audit trail.
- **Inputs:** `src/app/ai/agents/pii_scrubber.py` (CR-PII-001, interface unchanged), `src/app/cron/embedding/embedding_processor.py`
- **Outputs:** Updated `embedding_processor.py` with PII scrub step
- **Spec Refs:** Plan §7.2 | CR §2.1, §3.6 | AC-5
- **Acceptance Criteria:** Manual inspection of `resume_text` column after embed run shows no raw PII patterns (names, emails, phone numbers). Unit test: mock PII scrubber returning `""` → `resume_embedding` is `NULL` for that member (AC-5).
- **Definition of Done:**
  - [ ] PII scrubber called on `resume_text` before DB write
  - [ ] Scrubbing happens after MCP fetch, before embedding
  - [ ] Empty scrubber output → `resume_embedding = NULL`, member not errored
  - [ ] Scrubber call logged per member
- **Dependencies:** TASK-EMB-030
- **Owner:** AI
- **Type:** Build

---

#### TASK-EMB-032: Implement Legacy embedding Weighted Average Population

- **Description:** In `EmbeddingProcessor`, after all three component embeddings are generated, compute and store the weighted average in the legacy `embedding` column: `embedding = L2_normalize(0.50 * resume_emb + 0.30 * skills_emb + 0.20 * certs_emb)`. Handle partial availability: if any component is NULL, re-weight and re-normalize from available vectors only (e.g., resume + skills only → `normalize(0.625 * resume + 0.375 * skills)`; skills only → `skills_emb`). This satisfies AC-7.
- **Inputs:** `src/app/cron/embedding/embedding_processor.py`
- **Outputs:** Updated `embedding_processor.py` with weighted average logic; updated `upsert_team_member_embeddings()` to write `embedding` column
- **Spec Refs:** Plan §8.3 | CR §3.2.2 | AC-7
- **Acceptance Criteria:** For 5 spot-checked team members: `embedding` column value equals `L2_normalize(0.50 * resume_emb + 0.30 * skills_emb + 0.20 * certs_emb)` to 4 decimal places (AC-7).
- **Definition of Done:**
  - [ ] Weighted average computed for all 4 availability combinations
  - [ ] L2 normalization applied after weighting
  - [ ] `embedding` column written in every upsert
  - [ ] 5-member spot-check passes (AC-7)
- **Dependencies:** TASK-EMB-030
- **Owner:** AI
- **Type:** Build

---

### Epic: upsert_team_member_embeddings()

#### TASK-EMB-033: Implement upsert_team_member_embeddings() Repository Method

- **Description:** Add `upsert_team_member_embeddings(db, member_id, payload: EmbeddingPayload)` to `src/app/cron/db/repositories.py`. Uses PostgreSQL `INSERT INTO team_member_embeddings (...) ON CONFLICT (team_member_id) DO UPDATE SET ...`. Updates all 10 new columns plus legacy `embedding` column and `embedding_updated_at = NOW()`. Must NOT touch `profile_text`, `metadata`, `pii_scrubbed`, `scrubbed_at` (owned by Phase 1 ingestion). `EmbeddingPayload` is a dataclass/TypedDict covering all writable fields.
- **Inputs:** `src/app/cron/db/repositories.py`, `src/app/db/models/models.py` (Phase 1)
- **Outputs:** Updated `src/app/cron/db/repositories.py`
- **Spec Refs:** Plan §7.5 | CR §3.7 | AC-1, AC-2, AC-3
- **Acceptance Criteria:** `upsert_team_member_embeddings()` with a new `member_id` → row inserted. Called again with same `member_id` → row updated (no duplicate). `profile_text` and `pii_scrubbed` columns unchanged after upsert.
- **Definition of Done:**
  - [ ] `INSERT ... ON CONFLICT DO UPDATE` pattern implemented
  - [ ] All 10 new columns + `embedding` + `embedding_updated_at` written
  - [ ] `profile_text`, `metadata`, `pii_scrubbed`, `scrubbed_at` NOT in UPDATE SET
  - [ ] `EmbeddingPayload` type defined
- **Dependencies:** TASK-EMB-011
- **Owner:** Backend
- **Type:** Build

---

### Epic: CLI Modes (embed/ingest-embed/--force)

#### TASK-EMB-034: Add embed and ingest-embed CLI Modes to main.py

- **Description:** Update `src/app/cron/main.py` (currently 461 lines) to add two new argparse subcommands: `embed` (runs embedding phase only; accepts `--force` flag; spawns MCP server subprocess, calls `EmbeddingProcessor.run()`, tears down MCP server) and `ingest-embed` (runs existing ingest phase in committed transaction, then embed phase in separate transactions; `--force` propagated to embed phase). Exit codes unchanged: 0=SUCCESS, 1=PARTIAL, 2=FATAL, 3=SCHEMA_MISMATCH, 4=AUTH_FAILED.
- **Inputs:** `src/app/cron/main.py`, `src/app/cron/embedding/embedding_processor.py`, `src/app/cron/embedding/mcp_client.py`
- **Outputs:** Updated `src/app/cron/main.py`
- **Spec Refs:** Plan §7.1, §7.6 | CR §3.7.1 | AC-1, AC-6, AC-11
- **Acceptance Criteria:**
  ```bash
  python -m app.cron.main embed           # exits 0 on staging DB
  python -m app.cron.main ingest-embed    # exits 0 on staging DB
  python -m app.cron.main embed --force   # re-embeds all (skip_count = 0)
  python -m app.cron.main ingest          # still works (no regression)
  ```
- **Definition of Done:**
  - [ ] `embed` subcommand added with `--force` flag
  - [ ] `ingest-embed` subcommand added
  - [ ] `ingest` and `retry` modes unchanged
  - [ ] MCP server subprocess started at embed phase begin, torn down at end
  - [ ] `--force` bypasses content hash check
- **Dependencies:** TASK-EMB-030, TASK-EMB-033
- **Owner:** Backend
- **Type:** Build

---

### Epic: Phase Isolation

#### TASK-EMB-035: Verify Ingest-Embed Phase Isolation (Transaction Boundary)

- **Description:** Verify that in `ingest-embed` mode, the ingestion phase (Phase 1) runs in a separate DB transaction that is committed before the embedding phase begins. Implement and run the integration test `test_e2e_ingest_embed_phase_isolation`: inject a deliberate error in the embed phase; confirm ingest phase data is committed and intact in DB. MCP server crash during embed must NOT roll back ingestion data.
- **Inputs:** `src/app/cron/main.py`, `tests/cron/test_embedding_processor.py`
- **Outputs:** Phase isolation integration test added to `tests/cron/test_embedding_processor.py`
- **Spec Refs:** Plan §7.6 | CR §3.7 | R3
- **Acceptance Criteria:** After embed phase error injection: `SELECT count(*) FROM team_member WHERE ...` shows ingested rows intact; embed rows may be partial.
- **Definition of Done:**
  - [ ] `test_e2e_ingest_embed_phase_isolation` implemented and passes
  - [ ] Ingest transaction committed before embed begins (verified via test)
  - [ ] Embed crash does not rollback ingest data
- **Dependencies:** TASK-EMB-034
- **Owner:** QA
- **Type:** Test

---

### Epic: Integration Tests

#### TASK-EMB-036: Emit Observability Metrics from EmbeddingProcessor and MCPResumeClient

- **Description:** Instrument `EmbeddingProcessor` and `MCPResumeClient` to emit all metrics defined in Plan §10. Required metric emissions: `mcp_session_init_duration_seconds` (Histogram, `server=gdrive`) on subprocess spawn+init; `mcp_tool_call_total` (Counter, `tool=read_document`, `status=success|error`) per tool call; `mcp_tool_call_error_total` (Counter, `error_type=not_found|permission_denied|quota_exceeded|crash`) per error type; `mcp_server_uptime_seconds` (Gauge, `server=gdrive`) while subprocess running; `embedding_generation_duration_seconds` (Histogram, `type=resume|skills|certifications`) per embedding call; `resume_fetch_success_total` (Counter, `status=success|skipped|error`) per member fetch; `embedding_skip_total` (Counter, `reason=hash_match|no_content`) per skip; `embedding_batch_total_duration_seconds` (Histogram) total phase duration.
- **Inputs:** `src/app/cron/embedding/embedding_processor.py`, `src/app/cron/embedding/mcp_client.py`, existing structured logging infrastructure in `src/app/cron/`
- **Outputs:** Updated `embedding_processor.py` and `mcp_client.py` with metric emissions
- **Spec Refs:** Plan §10.1, §10.2, §10.3 | CR §6.6
- **Acceptance Criteria:** After `embed` run, structured logs contain entries with all 8 metric names. `embedding_skip_total{reason=hash_match}` > 0 on second run. Alert thresholds documented: `mcp_server_start_failed` P1; `resume_fetch_error_rate_high` P2 at >10%; `embedding_phase_duration_exceeded` P2 at >900s.
- **Definition of Done:**
  - [ ] All 8 metrics emitted with correct labels
  - [ ] Alert thresholds referenced in code comments
  - [ ] `embedding_batch_total_duration_seconds` emitted at phase end
  - [ ] `mcp_tool_call_error_total` labeled by error type
- **Dependencies:** TASK-EMB-030, TASK-EMB-022
- **Owner:** Platform
- **Type:** Build

---

#### TASK-EMB-037: Write EmbeddingProcessor Integration Tests

- **Description:** Implement `tests/cron/test_embedding_processor.py` (~200 lines). Unit section (~10 tests): `test_content_hash_same_input_same_hash`, `test_content_hash_different_input_different_hash`, `test_embedding_processor_skips_on_hash_match`, `test_embedding_processor_embeds_on_hash_mismatch`, `test_embedding_processor_pii_scrub_empty_result_skips_resume_embedding`. Integration section (≥5 tests using test DB): `test_e2e_cron_embed_mcp_mock_to_db` (real SQLite or test PG; mocked MCP; verify row inserted with all 3 embeddings), `test_e2e_ingest_embed_phase_isolation`, `test_embed_force_flag_re_embeds_all`, `test_embed_second_run_skips_unchanged`, `test_upsert_does_not_touch_profile_text`.
- **Inputs:** `src/app/cron/embedding/embedding_processor.py`, test DB
- **Outputs:** `tests/cron/test_embedding_processor.py`
- **Spec Refs:** Plan §9.3, §9.4 | CR §6.5 | AC-1, AC-5, AC-6 | R7
- **Acceptance Criteria:** `pytest tests/cron/test_embedding_processor.py -v` exits 0; ≥15 tests pass (10 unit + 5 integration).
- **Definition of Done:**
  - [ ] ≥10 unit tests pass (mocked model + mocked MCP)
  - [ ] ≥5 integration tests pass (real test DB)
  - [ ] Hash skip logic verified in test
  - [ ] PII scrub integration tested
  - [ ] `pytest tests/cron/test_embedding_processor.py -v` exits 0
- **Dependencies:** TASK-EMB-035, TASK-EMB-031
- **Owner:** QA
- **Type:** Test

---

### Epic: Phase Gate & Rollback

#### TASK-EMB-038: Risk Gate RG-R3 — Throughput ≥ 100 Members/Min on CPU

- **Description:** Execute RG-R3 risk gate. Run `tests/ai/test_gemma_embedding.py::test_throughput_100_texts` in the Phase 3 branch context. Assert 100 `embed_text()` calls complete in < 60 seconds on CPU. If throughput < 100/min: log RG-R3 escalation warning; document ONNX Runtime fallback plan; block Phase 3 merge pending resolution.
- **Inputs:** `src/app/ai/utils/gemma_embedding.py` loaded with real model weights
- **Outputs:** Throughput measurement (texts/second); RG-R3 PASS/FAIL verdict in PR
- **Spec Refs:** Plan §5.5 | AC-11 | R3
- **Acceptance Criteria:** 100 `embed_text()` calls complete in < 60s (≥100/min). RG-R3 FAIL = < 100/min → Phase 3 merge blocked until resolved.
- **Definition of Done:**
  - [ ] Throughput measured on CPU device
  - [ ] Result documented: `N texts/second`
  - [ ] RG-R3 PASS/FAIL verdict in PR
  - [ ] ONNX fallback plan documented if < 100/min
- **Dependencies:** TASK-EMB-037
- **Owner:** AI
- **Type:** Verify

---

#### TASK-EMB-039: Phase Gate GATE-2 — Hash Skip ≥80% on Second Run and PII Verified

- **Description:** Execute GATE-2 exit criteria. Run `python -m app.cron.main embed` twice against staging DB (no data changes between runs). Confirm: (1) second run skip rate ≥ 80% — `embedding_skip_total{reason=hash_match}` / total members ≥ 0.80 (AC-6); (2) `resume_text` column contains no raw PII patterns — manual spot-check 5 members (AC-5); (3) all integration tests pass; (4) embedding phase completes in < 5 minutes for 39 members (AC-11). This gate blocks Phase 4.
- **Inputs:** Staging DB with Phase 1–3 applied; all Phase 3 tests green
- **Outputs:** GATE-2 checklist signed off; branch merged
- **Spec Refs:** Plan §1 (Phase 3 Exit Criteria) | AC-1, AC-5, AC-6, AC-11
- **Acceptance Criteria:**
  ```bash
  python -m app.cron.main embed   # first run
  python -m app.cron.main embed   # second run → check logs for skip_count
  # embedding_skip_total{reason=hash_match} / total_members >= 0.80 (AC-6)
  # Total duration < 5 minutes (AC-11)
  ```
  Manual check of `SELECT resume_text FROM team_member_embeddings LIMIT 5` shows no PII (AC-5).
- **Definition of Done:**
  - [ ] Second-run skip rate ≥ 80% confirmed (AC-6)
  - [ ] No PII patterns in `resume_text` (spot-check 5 members, AC-5)
  - [ ] Embed phase < 5 min for 39 members (AC-11)
  - [ ] All integration tests green
  - [ ] Code reviewed and merged
  - [ ] GATE-2 signed off — Phase 4 unblocked
- **Dependencies:** TASK-EMB-038
- **Owner:** Backend
- **Type:** Validate

---

#### TASK-EMB-040: Phase 3 Rollback — Revert main.py and repositories.py

- **Description:** Document and verify Phase 3 rollback. Rollback: revert `src/app/cron/main.py` to pre-phase argparse state (remove `embed`/`ingest-embed` modes); revert `src/app/cron/db/repositories.py` (remove `upsert_team_member_embeddings()`); delete `src/app/cron/embedding/embedding_processor.py`. Verify: `python -m app.cron.main ingest` succeeds; legacy `embedding` and `profile_text` columns are untouched. Trigger conditions: embed phase causes cron duration > 30-min SLA (R3), or OOM from Gemma model load (R6 FAIL from TASK-EMB-017).
- **Inputs:** `src/app/cron/main.py`, `src/app/cron/db/repositories.py`, `embedding_processor.py`
- **Outputs:** Verified rollback procedure documented
- **Spec Refs:** Plan §12.1 | R3, R6
- **Acceptance Criteria:** After rollback: `python -m app.cron.main ingest` exits 0; `SELECT embedding FROM team_member_embeddings LIMIT 1` returns existing embedding (unmodified).
- **Definition of Done:**
  - [ ] Rollback steps documented
  - [ ] Ingest mode unaffected after rollback
  - [ ] Legacy `embedding` column data preserved (Phase 3 writes only to new columns)
- **Dependencies:** TASK-EMB-039
- **Owner:** DevOps
- **Type:** Validate

---

## Phase 4: RAG Multi-Vector Update

### Branch: `feature/emb-phase4-rag-multivector`
### Days: 13–15

---

### Epic: Baseline Capture

#### TASK-EMB-041: Capture Baseline Match Quality for A/B Comparison

- **Description:** Before any Phase 4 code changes, capture baseline match quality for ≥ 2 test requisitions. Run:
  ```bash
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:9001/api/v1/jd-skill-mapping/{test_req_id_1}/matches > baseline_matches_req1.json
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:9001/api/v1/jd-skill-mapping/{test_req_id_2}/matches > baseline_matches_req2.json
  ```
  Record: top-3 candidate IDs, mean/max/min score distribution for each test requisition. Store as test fixtures for regression comparison in TASK-EMB-047.
- **Inputs:** Staging environment with Phase 1–3 deployed; ≥2 test requisition IDs
- **Outputs:** `tests/fixtures/rag/baseline_matches_req1.json`, `tests/fixtures/rag/baseline_matches_req2.json`
- **Spec Refs:** Plan §8.4 | R1
- **Acceptance Criteria:** Both baseline files captured with top-3 IDs, mean/max/min scores. Stored in `tests/fixtures/rag/`.
- **Definition of Done:**
  - [ ] ≥2 test requisitions baseline captured
  - [ ] Top-3 candidate IDs recorded
  - [ ] Score distribution (mean/max/min) recorded
  - [ ] Fixtures stored in `tests/fixtures/rag/`
- **Dependencies:** TASK-EMB-039 (Phase 3 gate — data populated)
- **Owner:** QA
- **Type:** Validate

---

### Epic: _query_vector_and_filter() routing

#### TASK-EMB-042: Update _query_vector_and_filter() for Multi-Vector Cosine Routing

- **Description:** Update `_query_vector_and_filter()` in `src/app/ai/utils/rag_retrieval.py`. Replace the single `TeamMemberEmbedding.embedding` column used for ALL distances with semantic routing: `mandatory_sim` → `skills_embedding.cosine_distance(jd_mandatory_embedding)`; `preferred_sim` → `skills_embedding.cosine_distance(jd_preferred_embedding)`; `jd_level_sim` → `resume_embedding.cosine_distance(jd_level_embedding)`; `cert_sim` → `certifications_embedding.cosine_distance(jd_cert_embedding)`. Implement using SQLAlchemy `case()` construct.
- **Inputs:** `src/app/ai/utils/rag_retrieval.py`, Phase 1 schema (new columns exist), Phase 3 data (some rows populated)
- **Outputs:** Updated `src/app/ai/utils/rag_retrieval.py`
- **Spec Refs:** Plan §8.1 | CR §3.8.1 | AC-8
- **Acceptance Criteria:** `_query_vector_and_filter()` with all 3 new embedding columns populated: `mandatory_sim` computed against `skills_embedding`; `jd_level_sim` computed against `resume_embedding`; `cert_sim` computed against `certifications_embedding` (verified via query plan or mock assertion).
- **Definition of Done:**
  - [ ] All 4 distance computations use semantically correct columns
  - [ ] `case()` constructs used for conditional column selection
  - [ ] Existing function signature unchanged (backward compatible)
- **Dependencies:** TASK-EMB-041
- **Owner:** AI
- **Type:** Build

---

### Epic: NULL fallback

#### TASK-EMB-043: Implement NULL Fallback Logic for Missing Embedding Columns

- **Description:** Add NULL fallback within `_query_vector_and_filter()` SQLAlchemy `case()` expressions: if `skills_embedding IS NULL` → use legacy `embedding` for mandatory/preferred; if `resume_embedding IS NULL` → use legacy `embedding` for jd_level; if `certifications_embedding IS NULL` → return `literal(1.0)` (cosine distance = 1.0 → similarity = 0.0, no penalty no boost). This ensures backward compatibility during the Phase 3→Phase 4 transition window.
- **Inputs:** `src/app/ai/utils/rag_retrieval.py`
- **Outputs:** Updated `src/app/ai/utils/rag_retrieval.py` with NULL fallback in all three `case()` blocks
- **Spec Refs:** Plan §8.2 | CR §3.8.2 | AC-7, AC-8
- **Acceptance Criteria:** Query with `skills_embedding = NULL` row: `mandatory_sim` uses `embedding` column (fallback active). Query with `certifications_embedding = NULL`: `cert_sim = 0.0` (not error). Query with all NULL new columns: full fallback to legacy `embedding` path.
- **Definition of Done:**
  - [ ] Fallback to `embedding` for skills and resume NULL paths
  - [ ] `literal(1.0)` for `certifications_embedding IS NULL` (→ 0.0 similarity)
  - [ ] No SQLAlchemy error when new columns are NULL
- **Dependencies:** TASK-EMB-042
- **Owner:** AI
- **Type:** Build

---

### Epic: Legacy embedding weighted avg (verification)

#### TASK-EMB-044: Verify Legacy embedding Column Spot-Check (AC-7)

- **Description:** Execute AC-7 spot-check on staging DB. For 5 team members with all 3 embeddings populated, compute the expected weighted average manually: `expected = L2_normalize(0.50 * resume_emb + 0.30 * skills_emb + 0.20 * certs_emb)`. Compare against `SELECT embedding FROM team_member_embeddings WHERE team_member_id = ?`. Assert values match to 4 decimal places.
- **Inputs:** Staging DB with Phase 3 backfill applied; Python numpy for comparison
- **Outputs:** AC-7 verification result recorded in PR
- **Spec Refs:** Plan §8.3 | CR §3.2.2 | AC-7
- **Acceptance Criteria:**
  ```sql
  SELECT team_member_id, embedding, resume_embedding, skills_embedding, certifications_embedding
  FROM team_member_embeddings
  WHERE resume_embedding IS NOT NULL
    AND skills_embedding IS NOT NULL
    AND certifications_embedding IS NOT NULL
  LIMIT 5;
  ```
  For each row: `np.allclose(embedding, normalize(0.50*R + 0.30*S + 0.20*C), atol=1e-4)` is True (AC-7).
- **Definition of Done:**
  - [ ] 5 members spot-checked
  - [ ] All 5 pass `np.allclose(atol=1e-4)` comparison (AC-7)
  - [ ] Result recorded in PR
- **Dependencies:** TASK-EMB-043
- **Owner:** QA
- **Type:** Validate

---

#### TASK-EMB-045: Update RAG Agent to Pass Multi-Vector Columns Through GraphState

- **Description:** Update `src/app/ai/agents/rag_retrieval.py` to pass multi-vector column data through `GraphState` to `_query_vector_and_filter()`. This is a low-impact change: ensure the agent reads `skills_embedding`, `resume_embedding`, `certifications_embedding` columns from the ORM query result and makes them available in state as needed. Existing `rag_retrieval.py` function signature change must be backward compatible.
- **Inputs:** `src/app/ai/agents/rag_retrieval.py`, `src/app/ai/utils/rag_retrieval.py`
- **Outputs:** Updated `src/app/ai/agents/rag_retrieval.py`
- **Spec Refs:** Plan §8 | CR §2.1 | AC-8
- **Acceptance Criteria:** `/api/v1/jd-skill-mapping/{test_req_id}/matches` returns non-empty results using multi-vector path (AC-8).
- **Definition of Done:**
  - [ ] `GraphState` passes multi-vector columns to filter function
  - [ ] `rag_retrieval.py` agent node unchanged in signature
  - [ ] Matches endpoint returns results (AC-8 satisfied)
- **Dependencies:** TASK-EMB-043
- **Owner:** AI
- **Type:** Build

---

### Epic: Regression Tests

#### TASK-EMB-046: Measure RAG Query Latency P50 (Performance Gate)

- **Description:** Implement `tests/ai/test_rag_retrieval.py::test_rag_query_latency_p50_under_65ms`. Execute `_query_vector_and_filter()` 50 times against test DB with pre-populated vectors. Assert P50 latency < 65ms. Also assert P50 does not regress > 30% from baseline single-vector latency.
- **Inputs:** `src/app/ai/utils/rag_retrieval.py`, test DB with multi-vector rows
- **Outputs:** Latency measurements in test output
- **Spec Refs:** Plan §8.4, §9.5 | CR §6.2
- **Acceptance Criteria:** `pytest tests/ai/test_rag_retrieval.py::test_rag_query_latency_p50_under_65ms -v` passes; median latency of 50 calls < 65ms.
- **Definition of Done:**
  - [ ] 50-call benchmark implemented
  - [ ] P50 < 65ms asserted
  - [ ] Test passes in staging environment
- **Dependencies:** TASK-EMB-043
- **Owner:** QA
- **Type:** Test

---

#### TASK-EMB-047: Write RAG Multi-Vector Regression Tests

- **Description:** Implement regression tests in `tests/ai/test_rag_retrieval.py` covering: `test_multi_vector_mandatory_uses_skills_embedding` (all 3 cols populated → `mandatory_sim` uses `skills_embedding`), `test_multi_vector_jd_level_uses_resume_embedding`, `test_fallback_skills_null_uses_legacy` (`skills_embedding = NULL` → uses `embedding`), `test_fallback_resume_null_uses_legacy`, `test_fallback_certs_null_is_zero` (`certifications_embedding = NULL` → `cert_sim = 0.0`), `test_matches_endpoint_returns_results` (full E2E with test requisition). Compare top-3 results against baselines from TASK-EMB-041: assert no regression > 5% in mean match score (R1).
- **Inputs:** `src/app/ai/utils/rag_retrieval.py`, baseline fixtures from TASK-EMB-041, test DB
- **Outputs:** `tests/ai/test_rag_retrieval.py`
- **Spec Refs:** Plan §8.4, §9.4 | CR §6.5 | AC-7, AC-8 | R1
- **Acceptance Criteria:** `pytest tests/ai/test_rag_retrieval.py -v` exits 0; all 6 tests pass; mean match score regression < 5% vs baseline (R1).
- **Definition of Done:**
  - [ ] All 6 named tests implemented and pass
  - [ ] NULL fallback paths tested (2 fallback + 1 zero-cert tests)
  - [ ] Baseline comparison: mean score within 5% of baseline (R1)
  - [ ] `pytest tests/ai/test_rag_retrieval.py -v` exits 0
- **Dependencies:** TASK-EMB-046, TASK-EMB-041
- **Owner:** QA
- **Type:** Test

---

### Epic: Phase Gate & Rollback

#### TASK-EMB-048: Risk Gate RG-R1 — Match Quality Regression ≤ 5% vs Baseline

- **Description:** Execute RG-R1 risk gate. Compare multi-vector match results from `test_matches_endpoint_returns_results` against baselines from TASK-EMB-041. Compute regression: `(baseline_mean_score - post_mean_score) / baseline_mean_score`. If regression > 5%: block Phase 4 merge; investigate root cause (likely weighted-average tuning issue); consider reverting to Gemini via factory (R1 mitigation). Document comparison results.
- **Inputs:** Post-Phase-4 match results; baseline fixtures from TASK-EMB-041
- **Outputs:** Regression calculation (% delta); RG-R1 PASS/FAIL verdict in PR
- **Spec Refs:** Plan §8.4, §11.3 | R1
- **Acceptance Criteria:** `(baseline_mean - post_mean) / baseline_mean <= 0.05` for both test requisitions. RG-R1 FAIL if > 5% → merge blocked.
- **Definition of Done:**
  - [ ] Regression computed for both test requisitions
  - [ ] Result documented: `% regression = X%` per requisition
  - [ ] RG-R1 PASS/FAIL verdict in PR
  - [ ] Merge blocked if > 5% regression
- **Dependencies:** TASK-EMB-047
- **Owner:** AI
- **Type:** Verify

---

#### TASK-EMB-049: Phase Gate GATE-4 — Match Quality Not Regressed > 5%

- **Description:** Execute GATE-4 exit criteria. Confirm: (1) RG-R1 PASS from TASK-EMB-048; (2) P50 latency ≤ 65ms from TASK-EMB-046; (3) all 6 regression tests pass; (4) AC-7 spot-check passed (TASK-EMB-044); (5) `/matches` endpoint returns results (AC-8). This gate blocks Phase 5.
- **Inputs:** All Phase 4 deliverables on staging
- **Outputs:** GATE-4 checklist signed off; branch merged
- **Spec Refs:** Plan §1 (Phase 4 Exit Criteria) | AC-7, AC-8 | R1
- **Acceptance Criteria:** All GATE-4 criteria met; branch merged to integration; Phase 5 unblocked.
- **Definition of Done:**
  - [ ] RG-R1 PASS (≤5% regression)
  - [ ] P50 latency ≤ 65ms (TASK-EMB-046)
  - [ ] All 6 regression tests green (TASK-EMB-047)
  - [ ] AC-7 spot-check passed (TASK-EMB-044)
  - [ ] AC-8 satisfied (`/matches` returns results)
  - [ ] Code reviewed and merged
  - [ ] GATE-4 signed off — Phase 5 unblocked
- **Dependencies:** TASK-EMB-048
- **Owner:** AI
- **Type:** Validate

---

#### TASK-EMB-050: Phase 4 Rollback — Revert rag_retrieval.py to Single-Vector

- **Description:** Document and verify Phase 4 rollback. Rollback: revert `src/app/ai/utils/rag_retrieval.py` and `src/app/ai/agents/rag_retrieval.py` to pre-phase state (single `embedding` column); redeploy. No DB changes. Verify `/matches` endpoint still returns results using legacy `embedding` column. Trigger condition: RG-R1 FAIL (match quality degrades > 5%).
- **Inputs:** Pre-phase `rag_retrieval.py` state; staging environment
- **Outputs:** Verified rollback procedure documented
- **Spec Refs:** Plan §12.1 | R1
- **Acceptance Criteria:** After revert: `GET /api/v1/jd-skill-mapping/{test_req_id}/matches` returns non-empty results using legacy `embedding` column path. Backfill data in new columns preserved (not dropped).
- **Definition of Done:**
  - [ ] Rollback steps documented
  - [ ] `/matches` returns results after revert
  - [ ] New embedding column data preserved in DB (no DROP)
  - [ ] Legacy `embedding` column path confirmed working
- **Dependencies:** TASK-EMB-049
- **Owner:** DevOps
- **Type:** Validate

---

## Phase 5: Backfill & Validation

### Branch: `feature/emb-phase5-backfill-validation`
### Days: 16–17

---

### Epic: Pre-backfill snapshot

#### TASK-EMB-051: Capture Pre-Backfill State Snapshot

- **Description:** Before executing backfill, capture baseline state with the following SQL on staging/production DB:
  ```sql
  SELECT
    COUNT(*) AS total_members,
    COUNT(embedding) AS members_with_legacy_embedding,
    COUNT(resume_embedding) AS members_with_resume_embedding,
    COUNT(skills_embedding) AS members_with_skills_embedding,
    COUNT(certifications_embedding) AS members_with_cert_embedding
  FROM team_member_embeddings;
  ```
  Expected pre-backfill: `resume_embedding = 0`, `skills_embedding = 0`, `certifications_embedding = 0`. Also capture match quality baseline (if not already done in TASK-EMB-041). Store snapshot output as `docs/backfill_snapshot_pre.txt`.
- **Inputs:** Production or staging DB at Phase 4 HEAD (all code deployed, no backfill yet)
- **Outputs:** `docs/backfill_snapshot_pre.txt` with counts; baseline match quality JSON if not already captured
- **Spec Refs:** Plan §11.1 | CR §5.2
- **Acceptance Criteria:** SQL returns `members_with_resume_embedding = 0` (pre-backfill state confirmed). Snapshot file saved.
- **Definition of Done:**
  - [ ] Pre-backfill SQL executed and output saved
  - [ ] `resume_embedding`, `skills_embedding`, `certifications_embedding` counts all 0 confirmed
  - [ ] `docs/backfill_snapshot_pre.txt` created
- **Dependencies:** TASK-EMB-049 (Phase 4 gate)
- **Owner:** DevOps
- **Type:** Validate

---

### Epic: DDL migration

#### TASK-EMB-052: Execute DDL Migration on Production DB

- **Description:** Apply the Alembic migration to production (or final staging) DB:
  ```bash
  alembic upgrade head
  ```
  Verify all 10 new columns appear in `information_schema.columns` for `team_member_embeddings`. Confirm 4 IVFFlat indexes created. Confirm `ACCEPTABLE_REVISIONS` in `migrations_check.py` passes schema check.
- **Inputs:** Production DB at HEAD `bca284b2d901`; migration from TASK-EMB-010
- **Outputs:** DB at new migration HEAD; 10 new columns present
- **Spec Refs:** Plan §11.2 (Phase A) | CR §5.1 | AC-9
- **Acceptance Criteria:**
  ```sql
  SELECT column_name FROM information_schema.columns
  WHERE table_name = 'team_member_embeddings'
  ORDER BY column_name;
  -- Must include: certifications_embedding, certifications_text, content_hash,
  --   embedding_model, embedding_updated_at, resume_embedding, resume_fetched_at,
  --   resume_text, skills_embedding, skills_text
  ```
- **Definition of Done:**
  - [ ] `alembic upgrade head` exits 0
  - [ ] All 10 new columns confirmed in `information_schema`
  - [ ] All 4 indexes present in `pg_indexes`
  - [ ] Cron schema check passes (no SCHEMA_MISMATCH exit code)
- **Dependencies:** TASK-EMB-051
- **Owner:** DevOps
- **Type:** Build

---

### Epic: embed --force run

#### TASK-EMB-053: Execute Full Backfill — embed --force for All 39 Members

- **Description:** Run the full backfill against production/staging DB with all 39 team members:
  ```bash
  python -m app.cron.main embed --force 2>&1 | tee docs/backfill_execution.log
  ```
  Monitor `embedding_batch_total_duration_seconds` metric and stdout. Backfill must complete without FATAL exit (exit code ≠ 2). Members without `profile_url` must be gracefully skipped (R8). Capture execution log.
- **Inputs:** Production DB at new migration HEAD; all 39 team members in `team_member` table; Google SA provisioned (R4)
- **Outputs:** `docs/backfill_execution.log`; populated `resume_embedding`, `skills_embedding`, `certifications_embedding` columns
- **Spec Refs:** Plan §11.2 (Phase B) | CR §5.2 | AC-1, AC-11 | R4, R8
- **Acceptance Criteria:** `embed --force` exits with code 0 or 1 (PARTIAL OK, FATAL not OK). Completes in < 5 minutes (AC-11). Log shows graceful skip for members without `profile_url` (R8).
- **Definition of Done:**
  - [ ] `embed --force` executed and log captured
  - [ ] Exit code 0 or 1 (not 2)
  - [ ] Completed in < 5 minutes (AC-11)
  - [ ] Members without `profile_url` logged as skipped (not errored)
- **Dependencies:** TASK-EMB-052
- **Owner:** DevOps
- **Type:** Build

---

### Epic: Validation SQL (AC-1..AC-4)

#### TASK-EMB-054: Execute Post-Backfill Validation SQL Queries (AC-1..AC-4)

- **Description:** Run all four validation queries from Plan §11.2 (Phase C):
  ```sql
  -- AC-1: resume_embedding count vs members with profile_url
  SELECT
    COUNT(*) FILTER (WHERE resume_embedding IS NOT NULL) AS resume_embedded,
    COUNT(*) FILTER (WHERE profile_url IS NOT NULL) AS has_profile_url
  FROM team_member t
  LEFT JOIN team_member_embeddings e ON t.team_member_id = e.team_member_id;

  -- AC-2: skills_embedding count vs members with ≥1 skill
  SELECT
    COUNT(*) FILTER (WHERE skills_embedding IS NOT NULL) AS skills_embedded,
    COUNT(DISTINCT tms.team_member_id) AS members_with_skills
  FROM team_member_skill tms
  LEFT JOIN team_member_embeddings tme ON tms.team_member_id = tme.team_member_id
  WHERE tms.is_deleted = false;

  -- AC-3: certifications_embedding count
  SELECT COUNT(*) FILTER (WHERE certifications_embedding IS NOT NULL) AS certs_embedded
  FROM team_member_embeddings;

  -- AC-4: model identity
  SELECT DISTINCT embedding_model FROM team_member_embeddings;
  -- Expected: ('embedding-gemma-300m',)
  ```
  Save results to `docs/backfill_validation_results.txt`.
- **Inputs:** Production DB post-backfill
- **Outputs:** `docs/backfill_validation_results.txt`
- **Spec Refs:** Plan §11.2 | CR §9 (AC-1..AC-4) | AC-1, AC-2, AC-3, AC-4
- **Acceptance Criteria:** AC-1: `resume_embedded >= has_profile_url`. AC-2: `skills_embedded >= members_with_skills`. AC-3: `certs_embedded > 0`. AC-4: only `'embedding-gemma-300m'` returned.
- **Definition of Done:**
  - [ ] All 4 SQL queries executed
  - [ ] AC-1 satisfied: `resume_embedded >= has_profile_url`
  - [ ] AC-2 satisfied: `skills_embedded >= members_with_skills`
  - [ ] AC-3 satisfied: `certs_embedded > 0`
  - [ ] AC-4 satisfied: `DISTINCT embedding_model = ('embedding-gemma-300m',)`
  - [ ] Results saved to `docs/backfill_validation_results.txt`
- **Dependencies:** TASK-EMB-053
- **Owner:** QA
- **Type:** Validate

---

### Epic: Full pytest (AC-10)

#### TASK-EMB-055: Execute Full Test Suite — pytest tests/ -v (AC-10)

- **Description:** Run the complete test suite:
  ```bash
  pytest tests/ -v --tb=short 2>&1 | tee docs/pytest_full_run.log
  ```
  All tests must pass. This covers: `tests/mcp_servers/` (Phase 0), `tests/ai/` (Phase 1 + Phase 4), `tests/cron/` (Phase 2 + Phase 3). Any failures are blocking — investigate and fix before proceeding.
- **Inputs:** Full codebase at Phase 5; all Phases 0–4 merged
- **Outputs:** `docs/pytest_full_run.log`; exit code 0
- **Spec Refs:** Plan §9.6 | CR §9 | AC-10
- **Acceptance Criteria:** `pytest tests/ -v` exits with code 0 (AC-10). Zero test failures. Log saved.
- **Definition of Done:**
  - [ ] `pytest tests/ -v` exits 0 (AC-10)
  - [ ] Zero failures, zero errors
  - [ ] Log saved to `docs/pytest_full_run.log`
- **Dependencies:** TASK-EMB-054
- **Owner:** QA
- **Type:** Test

---

### Epic: Match quality comparison

#### TASK-EMB-056: Post-Backfill Match Quality Comparison (R1 Final Validation)

- **Description:** Run test requisitions through `/matches` endpoint post-backfill:
  ```bash
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:9001/api/v1/jd-skill-mapping/{test_req_id_1}/matches > post_matches_req1.json
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:9001/api/v1/jd-skill-mapping/{test_req_id_2}/matches > post_matches_req2.json
  ```
  Compare against baselines from TASK-EMB-041. Assess: same candidate set surfaced? Score distribution similar or improved? Top-3 ranking stable? Mean score regression < 5% (R1 final). Document comparison in PR.
- **Inputs:** `tests/fixtures/rag/baseline_matches_req*.json` (from TASK-EMB-041); post-backfill `/matches` responses
- **Outputs:** Match quality comparison in `docs/match_quality_comparison.txt`
- **Spec Refs:** Plan §11.3 | R1
- **Acceptance Criteria:** `(baseline_mean - post_mean) / baseline_mean <= 0.05` for both requisitions. Top-3 candidates unchanged or improved. No FATAL regression.
- **Definition of Done:**
  - [ ] Post-backfill match results captured for ≥2 requisitions
  - [ ] Score regression < 5% vs baseline (R1 final PASS)
  - [ ] Top-3 ranking assessed
  - [ ] Comparison saved to `docs/match_quality_comparison.txt`
- **Dependencies:** TASK-EMB-055
- **Owner:** AI
- **Type:** Validate

---

#### TASK-EMB-057: Validate Graceful Skip for Private/Unshared Google Docs (R8)

- **Description:** Confirm members with unshared or private Google Docs are handled gracefully. Run:
  ```sql
  SELECT team_member_id, resume_text
  FROM team_member_embeddings
  WHERE resume_text IS NULL AND team_member_id IN (
    SELECT team_member_id FROM team_member WHERE profile_url IS NOT NULL
  );
  ```
  For each result, confirm cron logs contain `"resume fetch: permission_denied"` or `"not_found"` — not errors that aborted the run. Verify cron exit code was not FATAL (2) for these members.
- **Inputs:** Production DB post-backfill; cron execution log from TASK-EMB-053
- **Outputs:** R8 validation result documented
- **Spec Refs:** Plan §11.4 | CR §9 | R8
- **Acceptance Criteria:** All members with `resume_text IS NULL` AND `profile_url IS NOT NULL` appear in cron logs as `permission_denied` or `not_found` skips (not fatal errors). Cron run completed despite these members.
- **Definition of Done:**
  - [ ] SQL identifies members with private/unshared docs
  - [ ] Each member found in cron logs as graceful skip
  - [ ] No FATAL exit triggered by private doc access
  - [ ] R8 validation result documented
- **Dependencies:** TASK-EMB-053
- **Owner:** QA
- **Type:** Validate

---

### Epic: Runbooks

#### TASK-EMB-058: Create MCP Server and Embedding Pipeline Troubleshooting Runbooks

- **Description:** Create two runbook files:

  **`docs/runbooks/mcp-server-troubleshooting.md`** covering:
  - Subprocess won't start: Python path, `mcp[cli]` not installed, SA file missing
  - Credential errors: `GOOGLE_SERVICE_ACCOUNT_FILE` path wrong, SA key expired
  - STDIO buffer overflow symptoms (large document hang)
  - Manual `tools/list` test command
  - How to restart MCP server mid-batch (kill PID, rerun `embed --force`)

  **`docs/runbooks/embedding-pipeline-troubleshooting.md`** covering:
  - `embedding-gemma-300m` model not found (HuggingFace cache miss, offline env)
  - Google API quota exceeded (how to check via MCP server logs)
  - OOM during embedding (R6): reduce `embedding_batch_size`, switch to FP16
  - Slow embedding (R3): profile `embed_batch()`, check GPU availability
  - Partial backfill recovery: identify members with NULL columns, rerun for them
- **Inputs:** Operational knowledge from Phases 0–5; alert definitions from Plan §10.3
- **Outputs:** `docs/runbooks/mcp-server-troubleshooting.md`, `docs/runbooks/embedding-pipeline-troubleshooting.md`
- **Spec Refs:** Plan §10.4 | CR §6.6
- **Acceptance Criteria:** Both runbook files exist and contain all specified sections. Alert names `mcp_server_start_failed`, `resume_fetch_error_rate_high`, `embedding_phase_duration_exceeded` referenced in runbooks.
- **Definition of Done:**
  - [ ] `docs/runbooks/mcp-server-troubleshooting.md` created with all 5 sections
  - [ ] `docs/runbooks/embedding-pipeline-troubleshooting.md` created with all 5 sections
  - [ ] All 3 alert names referenced
  - [ ] Partial backfill recovery steps included
- **Dependencies:** TASK-EMB-056
- **Owner:** DevOps
- **Type:** Document

---

### Epic: Prod readiness checklist

#### TASK-EMB-059: Performance Benchmark — Embedding Throughput and RAG Latency

- **Description:** Execute final performance benchmarks to validate AC-11 and P50 latency SLA:
  ```bash
  # Embedding throughput (AC-11)
  python -m app.cron.main embed --force
  # Measure total duration from logs: embedding_batch_total_duration_seconds
  # Must be < 5 minutes (300s) for 39 members

  # RAG latency
  pytest tests/ai/test_rag_retrieval.py::test_rag_query_latency_p50_under_65ms -v
  # P50 must be < 65ms
  ```
  Record results in `docs/performance_benchmark.txt`.
- **Inputs:** Production/staging env post-backfill; `tests/ai/test_rag_retrieval.py`
- **Outputs:** `docs/performance_benchmark.txt`
- **Spec Refs:** Plan §9.5 | CR §6.2 | AC-11
- **Acceptance Criteria:** Embed phase < 5 minutes for 39 members (AC-11); RAG P50 < 65ms. Both thresholds documented.
- **Definition of Done:**
  - [ ] Embed throughput measured and documented (< 5 min = pass)
  - [ ] RAG P50 latency measured (< 65ms = pass)
  - [ ] Results saved to `docs/performance_benchmark.txt`
- **Dependencies:** TASK-EMB-055
- **Owner:** Platform
- **Type:** Validate

---

#### TASK-EMB-060: Phase Gate GATE-5 — All Tests Green and Prod Readiness Signed Off

- **Description:** Execute GATE-5 final exit criteria. All of the following must be confirmed before declaring CR-EMB-002 complete: (1) all tests pass — `pytest tests/ -v` exits 0 (AC-10, from TASK-EMB-055); (2) AC-1 through AC-4 SQL validation passed (TASK-EMB-054); (3) AC-5 PII verified (TASK-EMB-039); (4) AC-11 performance < 5 min (TASK-EMB-059); (5) match quality not regressed > 5% (TASK-EMB-056); (6) R8 graceful skip confirmed (TASK-EMB-057); (7) both runbooks created (TASK-EMB-058); (8) data preservation guarantee: no rollback needed — backfill is additive to nullable columns only.
- **Inputs:** All Phase 5 deliverables
- **Outputs:** GATE-5 sign-off; CR-EMB-002 marked COMPLETE
- **Spec Refs:** Plan §13 (Phase 5 DoD) | CR §9 | AC-1..AC-15
- **Acceptance Criteria:** All 8 items above confirmed. `pytest tests/ -v` exits 0. All AC-1..AC-15 satisfied across phases.
- **Definition of Done:**
  - [ ] `pytest tests/ -v` exits 0 (AC-10)
  - [ ] AC-1: `resume_embedded >= has_profile_url`
  - [ ] AC-2: `skills_embedded >= members_with_skills`
  - [ ] AC-3: `certs_embedded > 0`
  - [ ] AC-4: `DISTINCT embedding_model = ('embedding-gemma-300m',)`
  - [ ] AC-5: no raw PII in `resume_text` (spot-check)
  - [ ] AC-11: backfill < 5 min
  - [ ] AC-10: full test suite green
  - [ ] Match quality ≤ 5% regression vs baseline (R1 final)
  - [ ] R8 graceful skip confirmed
  - [ ] Both runbooks created
  - [ ] Data preservation guarantee documented
  - [ ] CR-EMB-002 marked COMPLETE
- **Dependencies:** TASK-EMB-057, TASK-EMB-058, TASK-EMB-059
- **Owner:** Backend
- **Type:** Validate

---

## Cross-Phase CI

### Branch: All feature branches (enforced in CI pipeline)

---

### Epic: CI Guardrails

#### TASK-EMB-061: Implement Spec Traceability CI Check

- **Description:** Add a CI check that validates all AC-1..AC-15 identifiers appear in at least one test file or task reference. Script reads `tests/**/*.py` and `specs/change-request/CR_EMB_002_tasks.md`; asserts each AC-ID string is present. Fails PR merge if any AC is uncovered.
- **Inputs:** All test files across phases; `CR_EMB_002_tasks.md`
- **Outputs:** CI traceability script; pass/fail gate on all PRs
- **Spec Refs:** Plan §15 | CR §9
- **Acceptance Criteria:** CI script outputs coverage report; fails if any `AC-\d+` from AC-1..AC-15 is absent from test files.
- **Definition of Done:**
  - [ ] Traceability script implemented
  - [ ] Runs on all phase PRs
  - [ ] All AC-1..AC-15 covered (CI passes on final Phase 5 PR)
- **Dependencies:** None (can be set up after TASK-EMB-001)
- **Owner:** DevOps
- **Type:** Configure

---

#### TASK-EMB-062: Implement Credential Isolation Scan in CI

- **Description:** Add a CI scan that asserts `GOOGLE_SERVICE_ACCOUNT_FILE` is never referenced in `src/app/cron/` (except as a string in tests or config). Scan using `grep -r "GOOGLE_SERVICE_ACCOUNT_FILE" src/app/cron/` — any match outside of `mcp_client.py`'s `StdioServerParameters` env dict and `test_credential_isolation_*` tests triggers a CI failure.
- **Inputs:** `src/app/cron/` source tree
- **Outputs:** CI credential scan script; pass/fail gate on Phase 2+ PRs
- **Spec Refs:** Plan §6.3 | CR §6.4 | AC-14
- **Acceptance Criteria:** CI scan passes when `GOOGLE_SERVICE_ACCOUNT_FILE` only appears in `mcp_client.py` (subprocess env dict) and test assertions. Fails if found in any other cron source file.
- **Definition of Done:**
  - [ ] Scan script implemented and added to CI
  - [ ] Runs on Phase 2+ PRs
  - [ ] False-positive exceptions documented (test files, `mcp_client.py` subprocess env)
- **Dependencies:** TASK-EMB-021
- **Owner:** Security
- **Type:** Configure

---

#### TASK-EMB-063: Add Migration Dry-Run CI Gate for Phase 1 PR

- **Description:** Add a CI job to the Phase 1 PR pipeline that runs the full Alembic roundtrip against a fresh test DB:
  ```bash
  alembic upgrade head
  python -c "import psycopg2; ..."  # Assert 10 new columns present
  alembic downgrade bca284b2d901
  python -c "..."  # Assert 10 columns absent, 7 original intact
  alembic upgrade head
  python -c "..."  # Assert idempotent re-apply
  ```
  CI fails if any step fails. Satisfies AC-9 in automated pipeline.
- **Inputs:** Phase 1 migration file; CI test DB
- **Outputs:** CI migration roundtrip job; AC-9 automated validation
- **Spec Refs:** Plan §4.5 | AC-9
- **Acceptance Criteria:** CI job exits 0 for all three alembic steps. Fails PR merge if any step fails (AC-9 gate).
- **Definition of Done:**
  - [ ] CI job added to Phase 1 PR pipeline
  - [ ] All 3 alembic steps asserted
  - [ ] Merge blocked on any step failure
- **Dependencies:** TASK-EMB-010
- **Owner:** DevOps
- **Type:** Configure

---

#### TASK-EMB-064: Add Performance Regression Guard to CI

- **Description:** Add a CI performance guard that runs `test_throughput_100_texts` and `test_rag_query_latency_p50_under_65ms` on every Phase 3+ PR. Assert: embed throughput ≥ 100/min (R3 guard); RAG P50 < 65ms. If either fails, PR merge is blocked with a performance regression label. Baselines stored as CI environment variables.
- **Inputs:** `tests/ai/test_gemma_embedding.py::test_throughput_100_texts`, `tests/ai/test_rag_retrieval.py::test_rag_query_latency_p50_under_65ms`
- **Outputs:** CI performance guard job; pass/fail gate on Phase 3+ PRs
- **Spec Refs:** Plan §5.5, §9.5 | AC-11 | R3
- **Acceptance Criteria:** CI job fails PR merge if throughput < 100/min or RAG P50 ≥ 65ms.
- **Definition of Done:**
  - [ ] Performance CI job added to Phase 3+ pipelines
  - [ ] Both thresholds enforced
  - [ ] Merge blocked on regression
- **Dependencies:** TASK-EMB-016
- **Owner:** DevOps
- **Type:** Configure

---

#### TASK-EMB-065: Add MCP tools/list Health Check to CI

- **Description:** Add a CI health check that starts the MCP server and verifies `tools/list` returns all 3 tools. Run before every Phase 0+ PR merge:
  ```bash
  python -m src.mcp_servers.gdrive.server &
  sleep 1
  # Send tools/list JSON-RPC 2.0 request via MCP test client
  # Assert response contains read_document, search_files, get_file_metadata
  ```
  Fails PR merge if any tool missing (RG-R10 automated gate — AC-12).
- **Inputs:** `src/mcp_servers/gdrive/server.py`
- **Outputs:** CI `tools/list` health check job; automated RG-R10 enforcement
- **Spec Refs:** Plan §3.6 | AC-12 | R10
- **Acceptance Criteria:** CI job passes only when all 3 tool names present in `tools/list` response. Blocks merge if any tool missing (RG-R10).
- **Definition of Done:**
  - [ ] CI health check job implemented
  - [ ] `tools/list` response validated for all 3 tool names
  - [ ] Runs on all Phase 0+ PRs
  - [ ] RG-R10 gate automated (AC-12)
- **Dependencies:** TASK-EMB-005
- **Owner:** DevOps
- **Type:** Configure

---

## Summary

### Task Count by Phase

| Phase | Tasks | Branch | Days |
|-------|-------|--------|------|
| Phase 0: MCP Google Drive Server | TASK-EMB-001..008 (8 tasks) | `feature/emb-phase0-mcp-server` | 1–2 |
| Phase 1: Schema & Embedding Model | TASK-EMB-009..019 (11 tasks) | `feature/emb-phase1-schema-model` | 3–5 |
| Phase 2: MCP Client & Resume Pipeline | TASK-EMB-020..029 (10 tasks) | `feature/emb-phase2-mcp-client-pipeline` | 6–8 |
| Phase 3: Cron Integration | TASK-EMB-030..040 (11 tasks) | `feature/emb-phase3-cron-integration` | 9–12 |
| Phase 4: RAG Multi-Vector Update | TASK-EMB-041..050 (10 tasks) | `feature/emb-phase4-rag-multivector` | 13–15 |
| Phase 5: Backfill & Validation | TASK-EMB-051..060 (10 tasks) | `feature/emb-phase5-backfill-validation` | 16–17 |
| Cross-Phase CI | TASK-EMB-061..065 (5 tasks) | All branches | Ongoing |
| **Total** | **65 tasks** | | **17 days** |

### Acceptance Criteria Coverage

| AC | Covered By |
|----|-----------|
| AC-1 | TASK-EMB-030, TASK-EMB-034, TASK-EMB-054, TASK-EMB-060 |
| AC-2 | TASK-EMB-033, TASK-EMB-054, TASK-EMB-060 |
| AC-3 | TASK-EMB-033, TASK-EMB-054, TASK-EMB-060 |
| AC-4 | TASK-EMB-011, TASK-EMB-018, TASK-EMB-054, TASK-EMB-060 |
| AC-5 | TASK-EMB-031, TASK-EMB-039, TASK-EMB-060 |
| AC-6 | TASK-EMB-030, TASK-EMB-039, TASK-EMB-060 |
| AC-7 | TASK-EMB-032, TASK-EMB-044, TASK-EMB-049 |
| AC-8 | TASK-EMB-045, TASK-EMB-047, TASK-EMB-049 |
| AC-9 | TASK-EMB-010, TASK-EMB-018, TASK-EMB-019, TASK-EMB-063 |
| AC-10 | TASK-EMB-055, TASK-EMB-060 |
| AC-11 | TASK-EMB-016, TASK-EMB-039, TASK-EMB-053, TASK-EMB-059 |
| AC-12 | TASK-EMB-003, TASK-EMB-006, TASK-EMB-007, TASK-EMB-065 |
| AC-13 | TASK-EMB-003, TASK-EMB-005, TASK-EMB-007 |
| AC-14 | TASK-EMB-021, TASK-EMB-025, TASK-EMB-026, TASK-EMB-062 |
| AC-15 | TASK-EMB-022, TASK-EMB-026, TASK-EMB-028 |

### Risk Coverage

| Risk | Covered By |
|------|-----------|
| R1 | TASK-EMB-015, TASK-EMB-041, TASK-EMB-047, TASK-EMB-048, TASK-EMB-056 |
| R2 | TASK-EMB-004 (200ms rate limiter in MCP server) |
| R3 | TASK-EMB-016, TASK-EMB-038, TASK-EMB-064 |
| R4 | TASK-EMB-001 (SA provisioning noted in entry criteria), TASK-EMB-053 |
| R5 | TASK-EMB-010 (lists=10 with IVFFlat; sequential scan auto-used for small datasets) |
| R6 | TASK-EMB-014, TASK-EMB-017, TASK-EMB-040 |
| R7 | TASK-EMB-030 (SHA-256 on content, not URL) |
| R8 | TASK-EMB-004, TASK-EMB-022, TASK-EMB-053, TASK-EMB-057 |
| R9 | TASK-EMB-022, TASK-EMB-026, TASK-EMB-028 |
| R10 | TASK-EMB-006, TASK-EMB-007, TASK-EMB-065 |
| R11 | TASK-EMB-002, TASK-EMB-004 |
| R12 | TASK-EMB-021, TASK-EMB-036 (`mcp_session_init_duration_seconds` monitored) |

### Risk Gate Summary

| Gate | Condition | Blocks | Task |
|------|-----------|--------|------|
| RG-R10 | `tools/list` missing any of 3 tools | Phase 0 merge | TASK-EMB-006 |
| RG-R9 | 3 consecutive MCP reconnect failures without graceful skip | Phase 2 merge | TASK-EMB-028 |
| RG-R6 | Gemma RSS > 2GB | Phase 3 merge | TASK-EMB-017 |
| RG-R3 | Throughput < 100 members/min CPU | Phase 3 merge | TASK-EMB-038 |
| RG-R1 | Match quality regression > 5% | Phase 4 merge | TASK-EMB-048 |

### Reflection Gate Summary

| Gate | Condition | Blocks | Task |
|------|-----------|--------|------|
| GATE-0 | `tools/list` returns 3 tools independently | Phase 2 | TASK-EMB-007 |
| GATE-1 | Alembic roundtrip + 768-dim unit vector output | Phase 3 | TASK-EMB-018 |
| GATE-2 | Hash skip ≥80% on 2nd run + PII scrubber verified | Phase 4 | TASK-EMB-039 |
| GATE-4 | Match quality not regressed > 5% vs baseline | Phase 5 | TASK-EMB-049 |
| GATE-5 | All tests green + prod readiness signed off | CR Complete | TASK-EMB-060 |

---

*Generated from CR-EMB-002 v2.0.0. All spec references (§) resolve to `specs/change-request/CR_resume_embedding_pipeline.md`. All plan references resolve to `specs/change-request/CR_EMB_002_plan.md`.*
