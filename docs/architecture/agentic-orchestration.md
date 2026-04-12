# Agentic Orchestration — IB Job-Skill Mapping System

**Document Version:** 1.1  
**Last Updated:** 2026-04-06  
**Owner:** Technical Architect  

---

## 1. Overview

The system implements a **LangGraph-based multi-agent pipeline** that processes job requisitions through 7 sequential agent nodes, combining deterministic scoring with LLM enrichment and vector-based semantic search to produce ranked candidate recommendations with plain-language reasoning.

All orchestration is asynchronous — the API accepts a request, stores it, and returns immediately. The pipeline executes as a background task. Results are fetched via a separate polling endpoint.

---

## 2. Agent Inventory

| Agent | Module | Role | Primary I/O |
|-------|--------|------|-------------|
| **Requisition Parser** | `agents/requisition_parsing.py` | Extract and normalize JD metadata via LLM | In: raw `job_description` → Out: `ParsedJD` |
| **Skill Normalizer** | `agents/skill_normalization.py` | Map raw skills to canonical `skill_master` IDs | In: `parsed_jd.skills` + ontology → Out: `normalized_skills` |
| **Embedding Agent** | `agents/embedding.py` | Generate 5 component 768-dim vectors for the JD | In: `parsed_jd`, `normalized_skills` → Out: `EmbeddingResult` |
| **RAG Retrieval** | `agents/rag_retrieval.py` | Hybrid BM25+Vector search to filter candidate pool | In: embeddings + JD criteria → Out: top 40 `RAGCandidate` dicts |
| **Matching & Scoring** | `agents/matching_scoring.py` | 3-phase scoring: deterministic → AI confidence → AI override | In: candidates + profiles → Out: `CandidateScores` |
| **Explanation Generator** | `agents/explanation_generation.py` | LLM-generated strengths/gaps analysis for top-N candidates | In: `candidate_scores` + JD → Out: `detailed_explanation` |
| **Result Aggregation** | `agents/result_aggregation.py` | Finalize QUALIFIED/DISQUALIFIED decisions and fit levels | In: `candidate_scores` → Out: `FinalResult` list |

**Helper/Utility Agents:**
- `requisition_validation.py` — Structural validation (JD length, required fields)
- `semantic_validation.py` — LLM-based garbage/nonsense detection (called from Requisition Parser)
- `candidate_availability.py` — Availability window evaluation against `ProjectAllocation`
- `pii_scrubber.py` — PII detection and redaction (currently inactive in main graph; standalone use)

---

## 3. Graph Topology

**Defined in:** `src/app/ai/graph.py`  
**Framework:** LangGraph `StateGraph`

```
START
  │
  ▼
[requisition_parsing]  ──(error)──► END
  │
  ▼ (success)
[skill_normalization]
  │
  ▼
[embedding]
  │
  ▼
[rag_retrieval]
  │
  ▼
[matching_scoring]
  │
  ▼
[explanation_generation]
  │
  ▼
[result_aggregation]
  │
  ▼
END
```

- **Conditional edge:** Only `requisition_parsing → skill_normalization` has a condition (`should_continue_after_parsing()`). All subsequent edges are unconditional.
- **Graph is compiled once** at startup via `StateGraph.compile()` and reused across requests.

---

## 4. Shared State Schema

**Defined in:** `src/app/ai/state.py` (TypedDict: `GraphState`)

| Field | Type | Set By |
|-------|------|--------|
| `requisition_input` | `dict` (request_id, correlation_id, job_description) | API layer |
| `parsed_jd` | `ParsedJD` | Requisition Parser |
| `normalized_skills` | `NormalizedSkills` | Skill Normalizer |
| `embedding_result` | `EmbeddingResult` (5 vectors × 768-d) | Embedding Agent |
| `retrieved_candidates` | `List[RAGCandidate]` (max 40) | RAG Retrieval |
| `candidate_scores` | `List[CandidateScores]` | Matching & Scoring |
| `final_results` | `List[FinalResult]` | Result Aggregation |
| `pii_scrubbed` | `bool` | PII Scrubber (when active) |
| `pii_scrub_metadata` | `dict` | PII Scrubber (when active) |
| `llm_call_logs` | `List[LLMCallLog]` | Any LLM-calling agent |
| `cumulative_tokens` | `int` | Graph Executor (per checkpoint) |
| `cumulative_cost_usd` | `float` | Graph Executor (per checkpoint) |
| `error_message` | `str` | Any agent on failure |

---

## 5. Orchestration Layer

**Defined in:** `src/app/ai/graph_executor.py`  
**Function:** `execute_graph_with_audit(initial_state, request_id, db) → final_state`

The executor wraps graph execution with per-node checkpointing and audit logging:

```
execute_graph_with_audit()
  │
  ├─ Update requisition status → PROCESSING
  │
  ├─ graph.stream(initial_state):
  │    For each completed node:
  │      ├─ Extract token metrics from state
  │      ├─ Save new LLM call logs → llm_request_log table
  │      ├─ Serialize state → langgraph_checkpoint table
  │      └─ Accumulate cumulative_tokens + cumulative_cost_usd
  │
  ├─ On error_message in state → log error checkpoint; update status → FAILED
  │
  ├─ On success → store_results(correlation_id, final_results, metrics)
  │
  └─ Update requisition status → COMPLETED
```

---

## 6. API Entry Point & Background Execution

**Router:** `src/app/api/routers/jd_skill_mapping.py`  
**Endpoint:** `POST /api/v1/jd-skill-mapping/`

```
POST /api/v1/jd-skill-mapping/
  │
  ├─ Validate token (OAuth2)
  ├─ Check for duplicate request_id
  ├─ Store requisition (status = PENDING)
  ├─ Enqueue background task: process_requisition_with_graph()
  └─ Return HTTP 202 { request_id, correlation_id }

Background: process_requisition_with_graph()
  └─ Build initial_state from request
  └─ Call execute_graph_with_audit()
  └─ Results available at GET /api/v1/matches/{correlation_id}
```

---

## 7. Embedding Pipeline

### 7.1 Request-Time (JD Embeddings)

**Agent:** `agents/embedding.py`  
**Models:** Gemini `text-embedding-004` (remote) or local Gemma `embedding-gemma-300m` (768-d)

Five component vectors are generated per requisition:

| Vector | Input Text Template |
|--------|---------------------|
| `jd_level_vector` | `"Job level: {normalized_role}"` |
| `mandatory_vector` | `"Required skills: {mandatory_skills}"` |
| `preferred_vector` | `"Preferred skills: {preferred_skills}"` |
| `certification_vector` | `"Certifications: {certs}"` |
| `full_jd_vector` | `"search_query: {full_jd_text}"` |

### 7.2 Batch (Profile Embeddings — Cron)

**Processor:** `src/app/cron/embedding/embedding_processor.py`

For each team member:
1. Assemble text from profile header + resume content (via MCP from Google Drive)
2. Assemble skills text (JOIN `skill_master` → category + proficiency labels)
3. Assemble certifications text (JOIN certs + active/expired status)
4. Generate embedding with `EmbeddingAgent`
5. Store vector to `team_member_embedding.embedding` (pgvector)
6. Skip if content hash unchanged (idempotent)

---

## 8. Hybrid Search (RAG Retrieval)

**Agent:** `agents/rag_retrieval.py`  
**Strategy:** 70% BM25 + 30% vector cosine similarity

```
hybrid_score = (bm25_score × 0.7) + (cosine_sim × 0.3) + boost_scores

Boost components:
  + skill_match_boost    (mandatory + preferred skill overlap)
  + location_boost       (location match)
  + work_mode_boost      (remote/hybrid/onsite alignment)
  + experience_boost     (within expected range)
  + certification_boost  (required certs matched)

Hard filter (Skill Gate):
  WHERE (mandatory_boost + preferred_boost) >= seniority_threshold

ORDER BY hybrid_score DESC
LIMIT 40
```

---

## 9. Scoring Logic (3-Phase)

**Utility:** `src/app/ai/utils/scoring.py`  
**Class:** `ScoringAgent`

### Phase 1 — Deterministic

Role-weighted composite score from five components:

| Component | SENIOR weight | MID weight | JUNIOR weight |
|-----------|--------------|------------|---------------|
| Mandatory Skills (M) | 0.50 | 0.40 | 0.30 |
| Preferred Skills (P) | 0.20 | 0.20 | 0.30 |
| Semantic Similarity (S) | 0.25 | 0.25 | 0.25 |
| Certification (C) | 0.05 | 0.15 | 0.15 |

**Qualification Gates (both must pass):**

| Seniority | Skill Gate (M+P) | Semantic Gate (S) |
|-----------|-----------------|-------------------|
| SENIOR (≥96 mo) | ≥ 0.20 | ≥ 0.30 |
| MID (24–96 mo) | ≥ 0.08 | ≥ 0.20 |
| JUNIOR (<24 mo) | ≥ 0.15 | ≥ 0.15 |

Fails either gate → DISQUALIFIED (score capped at gate threshold).

### Phase 2 — AI Confidence

For QUALIFIED candidates: call `get_ai_fit_confidence(jd_text, profile_text)` → returns `confidence_score` (0.0–1.0) + key strengths/gaps. Adds to scoring ledger.

### Phase 3 — AI Override & Boost

- **Senior Waiver:** Candidate failed semantic gate but passed skill gate + AI confidence ≥ threshold → flip to QUALIFIED (override flag set)
- **AI Boost:** Apply `calculate_ai_boost(confidence_score)` to final score for QUALIFIED candidates

---

## 10. LLM Client

**File:** `src/app/ai/utils/llm_client.py`  
**Class:** `LLMClient`

Providers (configured via `settings.llm_provider`):

| Provider | Default Model | Use Case |
|----------|--------------|----------|
| `openai` | `gpt-4-turbo-preview` | Default |
| `groq` | `llama-3-70b` | Cost-optimized |
| `google` | `gemini-2.5-flash` | Multimodal alternative |

**Retry:** Max 5 retries, exponential backoff (2ⁿ seconds), 429-aware.  
**Cost tracking:** Every call extracts `usage` tokens → `get_completion_cost()` → accumulated in state.

---

## 11. MCP Client (Resume Fetching)

**File:** `src/app/cron/embedding/mcp_client.py`  
**Class:** `MCPResumeClient`  
**Server:** `src/mcp_servers/gdrive/server.py` (FastMCP, STDIO transport)

The MCP server exposes three tools:
- `read_document(url, file_id)` — Fetch Google Drive document text
- `search_files(query, max_results)` — Search Drive
- `get_file_metadata(file_id)` — File metadata

Client features:
- **Session pooling** per batch (amortizes ~500ms init cost)
- **Broken-pipe recovery** — up to 3 reconnect attempts with exponential backoff
- **Sync wrapper** — `asyncio.run()` around async core for cron compatibility
- **Graceful degradation** — returns `None` on failure (does not block pipeline)

---

## 12. Cron Batch Ingestion

**Entry point:** `src/app/cron/main.py`

```
python -m app.cron.main [subcommand] [flags]

Subcommands:
  (default)       Full ingest + embed cycle
  embed           Embedding phase only (skip data fetch)
  ingest-embed    Ingest then embed (separate transactions)

Flags:
  --force         Re-embed even if content hash unchanged
  --retry-failed  Process only previously failed batches
  --dry-run       Validate without committing
  --log-level     DEBUG | INFO | WARNING
```

**Pre-flight checks:** DB connection → schema version → OAuth authentication.

**Batch processor** (`processing/batch_processor.py`): one transaction per batch, PENDING → PROCESSING → SUCCESS/FAILED lifecycle, automatic rollback on error.

**Exit codes:** 0=SUCCESS, 1=PARTIAL_SUCCESS, 2=FATAL_ERROR, 3=SCHEMA_MISMATCH, 4=AUTHENTICATION_FAILED.

---

## 13. Database Tables (Orchestration-Relevant)

| Table | Purpose |
|-------|---------|
| `requisition_request` | Request lifecycle (PENDING → PROCESSING → COMPLETED/FAILED) |
| `langgraph_checkpoint` | Per-node state snapshots for audit/replay |
| `llm_request_log` | LLM call observability (agent, model, tokens, cost, status) |
| `team_member_embedding` | Profile vectors (pgvector) + content hash |
| `skill_master` | Canonical skill definitions |
| `skill_ontology` | Skill enrichment and equivalence mappings |
| `project_allocation` | Availability tracking for scoring |
| `pii_audit_log` | PII detection audit trail |

---

## 14. Error Handling Summary

| Agent | Fallback |
|-------|----------|
| Requisition Parser | LLM failure → passthrough parsing |
| Skill Normalizer | LLM rate-limit → deterministic alias matching |
| Embedding Agent | Model error → zero-vectors (768-d) |
| RAG Retrieval | No embeddings → BM25-only mode |
| Explanation Generator | LLM failure → template-based fallback explanation |

Graph-level: `error_message` field propagates failures. Conditional routing routes to END on fatal errors. All failures update requisition status to FAILED and log a checkpoint.

---

## 15. End-to-End Request Flow

```
Client
  │
  └─► POST /api/v1/jd-skill-mapping/
        │
        ├─ Store requisition (PENDING)
        ├─ Return 202 { request_id, correlation_id }
        │
        └─ [Background Task]
              │
              ▼
           execute_graph_with_audit()
              │
              ├─ [requisition_parsing]
              │     Semantic validation + LLM enrichment → ParsedJD
              │
              ├─ [skill_normalization]
              │     Ontology lookup + LLM mapping → skill_ids
              │
              ├─ [embedding]
              │     5 × 768-d vectors for JD components
              │
              ├─ [rag_retrieval]
              │     Hybrid BM25+Vector search → top 40 candidates
              │
              ├─ [matching_scoring]
              │     3-phase scoring: deterministic + AI confidence + override
              │
              ├─ [explanation_generation]
              │     LLM strengths/gaps for top-5 QUALIFIED candidates
              │
              └─ [result_aggregation]
                    QUALIFIED/DISQUALIFIED + fit_level → store_results()

Client
  └─► GET /api/v1/matches/{correlation_id}
        └─ Retrieve from results cache
```

---

## 16. Configuration Reference

**File:** `src/app/settings.py`

| Setting | Default | Description |
|---------|---------|-------------|
| `llm_provider` | `"openai"` | LLM backend |
| `openai_model` | `"gpt-4-turbo-preview"` | Model for LLM agents |
| `embedding_model` | `"google/embedding-gemma-300m"` | Embedding model |
| `hybrid_search_ratio_bm25` | `0.7` | BM25 weight in hybrid search |
| `hybrid_search_ratio_vector` | `0.3` | Vector weight in hybrid search |
| `rag_similarity_threshold` | `0.5` | Minimum similarity for RAG gate |
| `max_llm_explanations` | `5` | Top-N candidates to explain via LLM |
| `weight_mandatory_senior` | `0.50` | Phase 1 weight — mandatory skills (SENIOR) |
| `weight_semantic_senior` | `0.25` | Phase 1 weight — semantic similarity (SENIOR) |
| `ai_override_threshold_senior` | `0.75` | Minimum AI confidence to trigger senior waiver |
| `senior_exp_threshold` | `96` | Experience (months) for SENIOR classification |
| `junior_exp_threshold` | `24` | Experience (months) for JUNIOR classification |

---

*This document reflects the live codebase as of 2026-04-06. Update when graph topology, agent responsibilities, or scoring weights change.*
