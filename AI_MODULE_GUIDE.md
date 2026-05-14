# AI Module — Complete Working Guide

> Personal reference guide for understanding the agentic pipeline in `src/app/ai/`.
> Not an official doc — written for understanding, not for specs compliance.

---

## Table of Contents

1. [The Big Picture](#1-the-big-picture)
2. [The Shared Memory: GraphState](#2-the-shared-memory-graphstate)
3. [The Graph: How Nodes Are Wired](#3-the-graph-how-nodes-are-wired)
4. [The Runner: graph_executor.py](#4-the-runner-graph_executorpy)
5. [Node 1 — Requisition Parsing](#5-node-1--requisition-parsing)
6. [Node 2 — Skill Normalization](#6-node-2--skill-normalization)
7. [Node 3 — Embedding](#7-node-3--embedding)
8. [Node 4 — RAG Retrieval](#8-node-4--rag-retrieval)
9. [Node 5 — Matching & Scoring](#9-node-5--matching--scoring)
10. [Node 6 — Explanation Generation](#10-node-6--explanation-generation)
11. [Node 7 — Result Aggregation](#11-node-7--result-aggregation)
12. [The LLM Client](#12-the-llm-client)
13. [AI Confidence & Boost](#13-ai-confidence--boost)
14. [Team Member Embeddings: How They're Built (Cron)](#14-team-member-embeddings-how-theyre-built-cron)
15. [5 JD Vectors vs 3 Member Vectors — What's Actually Used](#15-5-jd-vectors-vs-3-member-vectors--whats-actually-used)
16. [Node 4 vs Node 5 — Why Both Exist](#16-node-4-vs-node-5--why-both-exist)
17. [Concrete Input/Output Per Node](#17-concrete-inputoutput-per-node)
18. [Where LLM Is Used vs Deterministic Code](#18-where-llm-is-used-vs-deterministic-code)
19. [Existing Documents to Read](#19-existing-documents-to-read)

---

## 1. The Big Picture

The system uses **LangGraph** — a graph-based agent orchestration library built on top of LangChain. You define a directed graph where each node is a Python function (or LLM call). A single shared state object flows through the graph, getting enriched at each node.

The full request lifecycle:

```
POST /api/v1/jd-skill-mapping/
        │
        ▼
  FastAPI router (jd_skill_mapping.py)
    ├── Saves Requisition to DB (status = 1 RECEIVED)
    ├── Returns 202 immediately ← user gets this right away
    └── Queues background task: process_requisition_with_graph()
                │
                ▼
        graph_executor.py → execute_graph_with_audit()
          ├── Creates LangGraph
          ├── graph.stream(initial_state)  ← streams node by node
          │     ├── Node 1: requisition_parsing   (status → 3 MATCHING)
          │     ├── Node 2: skill_normalization
          │     ├── Node 3: embedding
          │     ├── Node 4: rag_retrieval
          │     ├── Node 5: matching_scoring
          │     ├── Node 6: explanation_generation
          │     └── Node 7: result_aggregation
          ├── After each node: save_checkpoint() + save_llm_request_log()
          └── On finish: store_results() cache + status → 4 COMPLETED

GET /api/v1/jd-skill-mapping/{correlation_id}/matches
        │
        ▼
  Reads from cache → returns ranked candidates
```

---

## 2. The Shared Memory: GraphState

Every node receives the **same object** and writes back to it. It is a Python `TypedDict` defined in `src/app/ai/state.py`.

```python
class GraphState(TypedDict):
    requisition_input: RequisitionInput    # Set by router. Never changes.
    pii_scrubbed: Optional[bool]           # Set by PII node (currently disabled)
    pii_scrub_metadata: Optional[PIIScrubMetadata]
    parsed_jd: Optional[ParsedJD]          # Written by Node 1
    normalized_skills: Optional[NormalizedSkills]  # Written by Node 2
    embedding_result: Optional[Dict]       # Written by Node 3
    retrieved_candidates: Optional[List]   # Written by Node 4
    candidate_scores: Optional[List]       # Written by Node 5
    final_results: Optional[List]          # Written by Node 7
    llm_call_logs: Optional[List]          # Appended by any LLM-calling node
    cumulative_tokens: Optional[int]       # Running token count
    cumulative_cost_usd: Optional[float]   # Running cost in USD
    error_message: Optional[str]           # Set on failure → triggers END
```

**Key sub-types:**

```python
class ParsedJD(TypedDict):
    normalized_title: str
    normalized_role: str
    extracted_mandatory_skills: List[str]
    extracted_preferred_skills: List[str]
    experience: Optional[Dict]             # {min_months, max_months}
    certifications_required: List[str]
    jd_text: str
    location: List[str]
    work_mode: List[str]

class NormalizedSkills(TypedDict):
    mandatory_skill_ids: List[str]         # skill_master IDs
    preferred_skill_ids: List[str]
    mandatory_alternatives: Dict[str, List[str]]  # "Python" → ["sk-001", "sk-022"]
    preferred_alternatives: Dict[str, List[str]]
    mandatory_enriched: Dict[str, List[str]]      # skill_id → [related terms]
    preferred_enriched: Dict[str, List[str]]
    normalized_certifications: List[str]
```

### How state merging works in graph_executor.py

```python
for event in graph.stream(current_state):
    for node_name, state_update in event.items():
        current_state.update(state_update)   # node output merged in
        save_checkpoint(...)                 # persisted to DB after every node
```

Each node only returns the fields it changed. LangGraph merges those back into the full state automatically.

---

## 3. The Graph: How Nodes Are Wired

File: `src/app/ai/graph.py`

```python
workflow = StateGraph(GraphState)

# Register all nodes
workflow.add_node("requisition_parsing", requisition_parsing_node)
workflow.add_node("skill_normalization", skill_normalization_node)
workflow.add_node("embedding", embedding_node)
workflow.add_node("rag_retrieval", rag_retrieval_node)
workflow.add_node("matching_scoring", matching_scoring_node)
workflow.add_node("explanation_generation", explanation_generation_node)
workflow.add_node("result_aggregation", result_aggregation_node)

# Entry point
workflow.set_entry_point("requisition_parsing")

# Only one conditional edge — error check after parsing
workflow.add_conditional_edges(
    "requisition_parsing",
    should_continue_after_parsing,   # checks state["error_message"]
    {"END": END, "skill_normalization": "skill_normalization"}
)

# All other edges are linear
workflow.add_edge("skill_normalization", "embedding")
workflow.add_edge("embedding", "rag_retrieval")
workflow.add_edge("rag_retrieval", "matching_scoring")
workflow.add_edge("matching_scoring", "explanation_generation")
workflow.add_edge("explanation_generation", "result_aggregation")
workflow.add_edge("result_aggregation", END)
```

**Visual:**

```
START
  │
  ▼
[Node 1] requisition_parsing
  │
  ├─── error? ───────────────────────────────────► END
  │
  ▼
[Node 2] skill_normalization
  ▼
[Node 3] embedding
  ▼
[Node 4] rag_retrieval
  ▼
[Node 5] matching_scoring
  ▼
[Node 6] explanation_generation
  ▼
[Node 7] result_aggregation
  ▼
 END
```

> Note: PII Scrubber (Node 0) is coded but **disabled** — the graph skips it and starts at Node 1 directly.

---

## 4. The Runner: graph_executor.py

File: `src/app/ai/graph_executor.py`

This is the engine. It doesn't define the graph — it runs it and manages everything around it:

- Status transitions: `1 RECEIVED → 2 PROCESSING → 3 MATCHING → 4 COMPLETED / 5 FAILED`
- TruLens wrapping: `recorder = trulens_service.get_recorder()` wraps the graph for observability
- Checkpoint saving: after every node, persists state snapshot to `LangGraphCheckpoint` table
- LLM log saving: after every node, persists new LLM call logs to `LLMRequestLog` table
- Result caching: on completion, writes `final_results` to cache

```python
with recorder as recording:
    for event in graph.stream(current_state):
        for node_name, state_update in event.items():
            current_state.update(state_update)

            # Save new LLM logs added by this node
            new_logs = current_state["llm_call_logs"][processed_count:]
            for log in new_logs:
                save_llm_request_log(db, request_id, ...)

            # Save checkpoint (subset of state — no llm_call_logs, those are in their own table)
            checkpoint_state = {
                "parsed_jd": ..., "normalized_skills": ...,
                "candidate_scores": ..., "final_results": ...,
                "cumulative_tokens": ..., "cumulative_cost_usd": ...
            }
            save_checkpoint(db, request_id, node_name, checkpoint_state)

            # Error handling
            if current_state.get("error_message"):
                if "fallback" not in error_message:    # fatal error
                    update_status(FAILED)
```

---

## 5. Node 1 — Requisition Parsing

**File:** `src/app/ai/agents/requisition_parsing.py`
**Supporting files:** `src/app/ai/agents/requisition_validation.py`, `src/app/ai/agents/semantic_validation.py`

**Reads from state:** `requisition_input.job_description`
**Writes to state:** `parsed_jd`, `validation_errors`, `llm_call_logs`, `cumulative_tokens`

**What it does:** Takes raw job description dict → enriched, structured `ParsedJD`. Runs a sequential 3-step pipeline where any failure stops execution immediately — no LLM cost wasted on bad input.

### Internal 3-step flow

```
Step 1: validate_requisition_input()       ← basic checks, no LLM, zero cost
            │
            └── fail → state["error_message"] = "VALIDATION_FAILED: ..." → return early
            
Step 2: validate_requisition_semantics()   ← LLM checks: "is this actually a real JD?"
            │
            └── fail → state["error_message"] = "SEMANTIC_VALIDATION_FAILED: ..." → return early

Step 3: parse_requisition_with_llm()       ← LLM enriches and normalizes
            │
            └── post-check: if had_skills but LLM returned zero skills → SEMANTIC_VALIDATION_FAILED
```

### Step 1 — Basic Validation (requisition_validation.py)

8 deterministic rules checked in order — all must pass:

| # | Field | Rule |
|---|-------|------|
| 1 | `jd_text` | Must be ≥ 50 characters |
| 2 | `title` | Must exist and not equal `"unknown"` |
| 3 | `role` | Must exist and not equal `"unknown"` |
| 4 | Skills vs JD depth | If no mandatory skills → `jd_text` must be ≥ 200 chars |
| 5 | Skill count | ≤ 15 mandatory skills |
| 6 | Experience | `min ≤ max`, both ≤ 360 months (30 years) |
| 7 | `location` | Non-empty list |
| 8 | `work_mode` + `client_name` | Both required, non-empty |

Returns `(is_valid: bool, reasons: List[str])`. All failing rules are collected (not short-circuited) so the caller gets the full list of problems at once.

### Step 2 — Semantic Validation (semantic_validation.py)

Runs only if basic validation passes. Uses LLM to detect garbage data that passed structural checks (e.g. title = `"sdfdsf"`, location = `"dsfdsfsd"`).

**What goes to the LLM:**
- `title`, normalized `role`, normalized `client_name`
- `mandatory_skills`, `preferred_skills`, `location`
- First 500 chars of `jd_text` only (cost control)

**Pre-normalization before LLM:**
- `_normalize_role()` — if role is identical to title (common mistake), falls back to `"Software Development"`
- `_normalize_client_name()` — converts `"N/A"`, `"TBD"`, `"unknown"` → `"CLIENT_TOKEN_UNKNOWN"` so LLM doesn't flag them

**False-positive filter — `_is_known_valid_semantic_error()`:**

After LLM returns errors, each one is run through this filter. Errors matching any of these patterns are silently dropped:

```
- Contains CLIENT_TOKEN_*, PROJECT_TOKEN_*, [REDACTED] → PII tokens, always valid
- Contains "skill" anywhere → skill format errors are ignored (normalization handles them)
- "Invalid client name: ..." with any non-empty value → accepted
- "Invalid job role: not a valid role category" → common false positive
- "Invalid job description: ..." for short/tokenized text → accepted
```

**Fail-open design:** If the LLM call itself fails (timeout, rate limit), semantic validation returns `(True, [])` — passes the request through rather than blocking it. The philosophy: it's better to process a borderline JD than to drop a legitimate one due to LLM availability.

### Step 3 — LLM Parsing (parse_requisition_with_llm)

**Prompt tells LLM:**
- Normalize the job title and role category
- Extract/enrich mandatory and preferred skills from `jd_text`
- Normalize skills to standard technical format
- Extract experience requirements in months
- Return ONLY valid JSON

**Merge logic (important — prevents LLM from downgrading skills):**
```python
# LLM output is merged with originals — it can only ADD, never remove or move
final_mandatory = original_mandatory ∪ new_from_llm  (excluding original_preferred)
final_preferred = original_preferred ∪ new_from_llm  (excluding original_mandatory)
```
If `"Python"` was already in mandatory, the LLM cannot reclassify it as preferred. Skills are promoted but never demoted.

**Post-parse empty-skill check:**
```python
if had_skills and not m_skills and not p_skills:
    → SEMANTIC_VALIDATION_FAILED: "Could not predict any valid skills from the provided text."
```
If the input had skills but the LLM returned none (e.g. all input was garbage the LLM ignored), the node rejects the result rather than passing an empty skill list downstream.

**Fallback:** If LLM fails → `_fallback_parse()` returns the original raw input as-is with no enrichment. Pipeline continues with what we have.

---

## 6. Node 2 — Skill Normalization

**File:** `src/app/ai/agents/skill_normalization.py`

**Reads from state:** `parsed_jd`
**Writes to state:** `normalized_skills`, `llm_call_logs`

**What it does:** Maps human-readable skill names → canonical `skill_master` IDs stored in DB.

### Why this matters

The scoring engine in Node 5 works with **skill IDs**, not strings. `"js"`, `"JavaScript"`, `"ES6"` all need to map to the same `skill_master` ID or the candidate who has `"JavaScript"` won't match a JD that said `"js"`.

### The normalization pipeline

```
DB: skill_ontology table   →  {core_skill: [enriched_terms]}
                               e.g. "Python" → ["Django", "Flask", "asyncio", "pandas"]
                               The full ontology is passed to the LLM as context.

DB: skill_master table     →  {skill_name_lower: skill_id}
                               e.g. "python" → "sk-001"
                               Used for ID resolution AFTER LLM runs.

LLM call:
  Input: {mandatory: ["js", "postgres"], preferred: ["k8s"], ontology: {...full ontology...}}
  Output: [
    {"raw": "js",       "canonical": "JavaScript", "enriched": ["TypeScript", "React"]},
    {"raw": "postgres", "canonical": "PostgreSQL",  "enriched": ["SQL", "pgvector"]},
    {"raw": "k8s",      "canonical": "Kubernetes",  "enriched": ["Docker", "Helm"]}
  ]

Post-LLM ID resolution per returned item:
  1. Alias check: if canonical.lower() in SKILL_ALIASES → resolve alias first
                  e.g. "js" → "JavaScript" (15 hardcoded common aliases)
  2. Direct lookup: skill_master_map[canonical.lower()] → skill_id
  3. Fuzzy match: _find_fuzzy_matches(canonical, skill_master_map)
                  → finds all skill_ids where canonical is a SUBSTRING of any skill_name
                  → threshold: canonical must be ≥ 3 chars (prevents "js", "go" over-matching)
  4. Merge: skill_group = direct_match + fuzzy_matches (deduplicated)
  5. Store as mandatory_alternatives["JavaScript"] = ["sk-100", "sk-101", ...]
```

### Fuzzy match threshold detail

```python
def _find_fuzzy_matches(term, skill_master_map):
    if len(term) < 3:   # "js", "go" → skip, too short to substring-match safely
        return []
    return [skill_id for skill_name, skill_id in skill_master_map.items()
            if term.lower() in skill_name]
```

This intentionally casts a wide net — `"python"` would match `"python"`, `"python3"`, `"python developer"`. All matches feed into the alternatives group, so a candidate with any of them satisfies the requirement.

### Unresolvable skills — empty alternatives

If no skill_master match is found (direct or fuzzy), the raw name is still stored:
```python
mandatory_alternatives["UnknownTool"] = []   # empty list
```
This ensures downstream scoring sees the requirement was present even though no ID could be resolved. The scoring agent handles `[]` gracefully (counts as missing).

### mandatory_alternatives — the key output

```python
"mandatory_alternatives": {
    "JavaScript": ["sk-100", "sk-101"],   # JS or JS Advanced both count
    "PostgreSQL":  ["sk-003", "sk-031"],   # PostgreSQL or PostgreSQL Advanced both count
    "REST APIs":   ["sk-004"],
    "UnknownTool": []                      # couldn't resolve — treated as missing in scoring
}
```

In Node 5, for each required skill *group*, if the candidate has **any one** of the alternative IDs → they match that requirement. This prevents failing a candidate who has "PostgreSQL Advanced" when the JD asked for "PostgreSQL".

### Fallback (LLM fails)

`_normalize_deterministic_fallback()` — much simpler:
1. Direct name → skill_master lookup (lowercased)
2. Alias lookup via SKILL_ALIASES → then skill_master lookup
3. No fuzzy matching, no enrichment, no alternatives map per skill

This runs per-skill in isolation, so the resulting `mandatory_alternatives` is flat 1:1 mapping (no groups).

---

## 7. Node 3 — Embedding

**File:** `src/app/ai/agents/embedding.py`
**Utility:** `src/app/ai/utils/embedding.py`, `src/app/ai/utils/gemma_embedding.py`

**Reads from state:** `parsed_jd`, `normalized_skills`
**Writes to state:** `embedding_result`

**What it does:** Generates 5 separate 768-dimensional vectors for different parts of the JD.

### Backend selection — 3-step priority chain

```python
model_name = (
    settings.embedding_model          # 1. EMBEDDING_MODEL env var (explicit override)
    or settings.gemma_model_path       # 2. GEMMA_MODEL_PATH (same model cron uses)
    or settings.embedding_model_name   # 3. default "google/embeddinggemma-300m"
)

if "gemini" in model_name.lower():
    → Google GenAI API (task_type="retrieval_query")
else:
    → Local GemmaEmbeddingAgent via SentenceTransformer
```

### The 5 vectors and what text each receives

| Vector | Input text sent to model | Used where |
|--------|--------------------------|------------|
| `jd_level_vector` | `"Job level: Backend Engineer"` | Node 4 post-SQL → `jd_level_similarity` → Node 5 semantic score |
| `mandatory_vector` | `"Required skills: Python, FastAPI, ..."` | **Currently unused** |
| `preferred_vector` | `"Preferred skills: Docker, K8s, ..."` | **Currently unused** |
| `certification_vector` | `"Certifications: AWS SAA. Related concepts: ..."` | **Currently unused** |
| `full_jd_vector` | `"search_query: {raw jd_text}"` | Node 4 SQL `e.embedding <-> :vector` |

The `search_query:` prefix on `full_jd_vector` is **Gemma-specific** — the model was trained to treat this prefix as a signal that the text is a retrieval query, not a document to be indexed. Omitting it would return slightly different vector geometry and degrade search quality.

### The local Gemma model (GemmaEmbeddingAgent)

Model: `google/embeddinggemma-300m` (gated on HuggingFace, requires `HF_TOKEN` env var).

Loaded via `SentenceTransformer`, **not** raw `transformers`. This is intentional — the checkpoint has **Dense projection layers** after mean pooling that `transformers` alone won't apply. Using `SentenceTransformer.encode()` ensures the full pipeline (tokenize → pool → project → L2-normalize) runs correctly.

```python
# Token limit guard (TD-001): sentence-transformers v3+ has a bug where
# tokenizer.model_max_length can be unreliably large. We clamp it:
safe_max_length = min(self.MAX_TOKENS, self.tokenizer.model_max_length)  # MAX_TOKENS = 2048
self._st_model.max_seq_length = safe_max_length
```

Output: 768-dim float32, already L2-normalized (`normalize_embeddings=True`).

### Empty vs error vectors

```python
# Empty text → zero vector (safe — won't interfere with cosine similarity)
if not text_input or text_input.strip() == "":
    return np.zeros(768).astype(np.float32)

# Model/API failure → random vector (degraded path — logs error)
except Exception:
    return np.random.randn(768).astype(np.float32)
```

Zero vectors are intentional neutral values. Random vectors are a last-resort fallback that keeps the pipeline running but will produce meaningless similarity scores — the error log is the signal to investigate.

### Serialization detail

Numpy arrays are converted to Python lists before going into `state["embedding_result"]` — numpy is not JSON-serializable and the state gets checkpointed to DB. Node 4 converts them back to numpy arrays immediately on reading.

---

## 8. Node 4 — RAG Retrieval

**File:** `src/app/ai/agents/rag_retrieval.py`
**Utility:** `src/app/ai/utils/rag_retrieval.py`

**Reads from state:** `embedding_result`, `parsed_jd`, `normalized_skills`
**Writes to state:** `retrieved_candidates`

**What it does:** Hybrid BM25 + vector search against `team_member_embeddings` to shortlist candidates before full scoring.

### Why RAG exists — the funnel problem

Running full AI scoring (DB queries per member, LLM calls, regex) on 500 people costs time and money. RAG is the **cheap pre-filter** that narrows to the 40 best before expensive scoring starts.

### Pre-SQL keyword string building

Two separate keyword strings are built before the query runs:

```python
# 1. ALL skills + certs combined — used in SELECT for BM25 scoring
keyword_query_str = '"Machine Learning" OR Python OR "AWS Solutions Architect"'
# Multi-word skills are quoted so tsquery treats them as phrases, not individual words

# 2. Mandatory skills only — used in WHERE as a hard gate
mandatory_query_str = 'Python OR "PostgreSQL" OR Docker'
```

### The single SQL query

```sql
SELECT
    e.team_member_id,
    tm.designation, e.skills_text, e.certifications_text,
    tm.experience_in_months, tm.base_location, tm.work_type,
    e.embedding <-> CAST(:vector AS vector) AS similarity_score,   -- pgvector L2 distance
    ts_rank(
        to_tsvector('english',
            COALESCE(e.skills_text, '') || ' ' ||     -- COALESCE: NULL → '' to prevent NULL propagation
            COALESCE(e.certifications_text, '') || ' ' ||
            COALESCE(e.profile_text, '')
        ),
        websearch_to_tsquery('english', :kw_query)
    ) AS keyword_score
FROM team_member_embeddings e
LEFT JOIN team_member tm ON tm.team_member_id = e.team_member_id
WHERE
    e.embedding IS NOT NULL AND tm.is_active = true
    -- HARD FILTER: must match at least 1 mandatory skill via full-text search
    AND to_tsvector('english', COALESCE(skills_text,'') || ...) @@ websearch_to_tsquery(:m_query)
    AND tm.base_location ILIKE '%Pune%'        -- location (if provided)
    AND CAST(tm.work_type AS text) ILIKE '%hybrid%'  -- work mode (Remote→wfh, WFO→wfo, Hybrid→hybrid)
    AND tm.experience_in_months BETWEEN 60 AND 9999
ORDER BY similarity_score ASC    -- L2: lower distance = more similar, so ASC
LIMIT 10
```

**Why COALESCE?** Without it, `NULL || ' ' || 'Python'` = `NULL` in SQL. COALESCE converts NULL columns to empty strings before concatenation so `tsvector` always gets a valid string.

Two scoring signals come back from SQL:
- `similarity_score`: Raw L2 distance (0 = identical, higher = further away). Lower is better — hence `ORDER BY ASC`.
- `keyword_score`: BM25 `ts_rank` score — higher = stronger keyword match.

**LIMIT 10** is intentionally tight. The hard filters (mandatory skills, location, work mode, experience) are expected to pre-qualify candidates well. If filters are loose, this could be a recall bottleneck worth watching.

### Post-SQL scoring in Python

```python
# Score normalization formulas:
semantic_fit = 1.0 / (1.0 + distance)          # L2 distance → 0-1 similarity (never 0 or 1 exactly)

kw_norm = keyword_score / (0.03 + keyword_score) # Saturation curve → 0-1
# The 0.03 constant prevents exact 1.0 for very high ts_rank values, keeps scale consistent

m_score = len(mandatory_matches) / max(len(mandatory_skills), 1)  # ratio of keyword substring matches

# Experience: graceful degradation, not binary
exp_score = 1.0 if in_range else max(0.0, 1.0 - diff / max(12, min_months))
# If 6 months short of a 24-month min → partial credit rather than zero

weights = {
    "semantic":     0.30,
    "keyword":      0.20,
    "mandatory":    0.30,   # combined: semantic + mandatory = 60% of total
    "preferred":    0.05,
    "experience":   0.05,
    "certification":0.05,
    "location":     0.025,
    "work_mode":    0.025   # weights sum to exactly 1.0
}

total_score = sum(component * weight for each component)

# Mandatory penalty: passed SQL filter but zero Python substring matches → 40% cut
if mandatory_skills and not any_mandatory_found_in_python:
    total_score *= 0.6  # handles tangential tsquery matches (stemming artefacts)

# Final cut
final_candidates = [c for c in candidates if c.final_similarity > 0.40][:40]
```

The Python mandatory check is a **second, simpler pass** after the SQL tsvector check. SQL uses stemming + full-text parsing; Python uses raw substring. Both together catch cases where tsquery matched tangentially.

### What gets passed to Node 5

```python
{
    "team_member_id": "TM-042",
    "final_similarity": 0.81,       # rough overall score — DISCARDED in Node 5
    "jd_level_similarity": 0.88,    # ← THIS SURVIVES — becomes semantic_score in Node 5
    "mandatory_similarity": 0.75,
    "phase0_score_breakdown": {...}  # full breakdown preserved for audit trail
}
```

---

## 9. Node 5 — Matching & Scoring

**File:** `src/app/ai/agents/matching_scoring.py`
**Utility:** `src/app/ai/utils/scoring.py`, `src/app/ai/utils/ai_confidence.py`

**Reads from state:** `normalized_skills`, `parsed_jd`, `retrieved_candidates`
**Writes to state:** `candidate_scores`

**What it does:** The authoritative scoring pass. For each of the 40 RAG candidates, runs precise deterministic scoring + AI confidence evaluation.

### Per-candidate flow

```
1. DB queries (4 per candidate):
   - TeamMemberSkill           → member_skill_ids (actual skill_master IDs)
   - TeamMemberSkillCertification → member_certs
   - TeamMemberEmbedding       → profile_text (for text-based fallback matching)
   - SkillMaster JOIN          → member_skill_names (human-readable, for penalty check)

2. evaluate_availability(db, member_id, start_date, duration, threshold=80%)
   → {"is_available": True, "available_capacity": 85.0}
   Note: is_available does NOT disqualify — stored as context for recruiter only.

3. ScoringAgent.execute()  ← deterministic, no LLM
   → ScoringResult with match_score + detailed_breakdown

4. get_ai_fit_confidence()   ← LLM (ONLY if Stage 1 gates passed — cost control)
   → {"confidence_score": 0.84, "reasoning": "...", "key_strengths": [], "major_gaps": []}

5. AI Senior Waiver check    ← can override DISQUALIFIED → QUALIFIED for senior candidates
   (only if disqualification was from semantic gate, not skill gate)

6. calculate_ai_boost()      ← deterministic formula
   → small score addition based on AI confidence

7. _sanitize_skill_list()    ← PII filter on matched/missing skill lists
   → strips CLIENT_TOKEN_*, PROJECT_TOKEN_*, hex-only values before storing
```

### Availability check internals (availability.py)

```python
# Step 1: Calculate requisition window
start_date = expected_start_date or today
end_date = start_date + timedelta(days=duration_months * 30)

# Step 2: Find overlapping allocations (classic interval overlap condition)
# Two ranges overlap when: A.start < B.end AND A.end > B.start
# This catches all 4 overlap cases:
#   Req: |-------|
#   1. Wraps:   |-----------|    allocation.start < req.end AND allocation.end > req.start ✓
#   2. Left:    |------| →       same condition ✓
#   3. Right:      |------|      same condition ✓
#   4. Inside:    |-----|        same condition ✓
# Soft-deleted allocations (is_deleted=True) are excluded.

# Step 3: Sum percentages
total_allocation = sum(alloc.allocation_percentage for alloc in overlapping)
available_capacity = max(0.0, 100.0 - total_allocation)  # max() guards against over-allocation
is_available = total_allocation < 80.0  # 80% threshold leaves capacity buffer
```

### ScoringAgent internals (scoring.py)

**Phase 0 — Role classification (all weights from settings, nothing hardcoded):**
```python
role_type = SENIOR   # experience >= senior_exp_threshold OR "SR"/"SENIOR" in jd_level
           | MID     # everything else
           | JUNIOR  # experience < junior_exp_threshold OR "JR"/"JUNIOR" in jd_level
```

Each role has its own weight set AND gate thresholds. Seniors get stricter gates but higher mandatory weight; juniors get more forgiving gates.

**Stage 1 — Hard qualification gates:**
```python
# Mandatory skill matching: TWO-PASS check per required skill
for canonical, alt_ids in mandatory_alternatives.items():
    # Pass 1: set intersection against member's skill_master IDs
    if any(sid in member_skill_ids for sid in alt_ids):
        matched.append(canonical); continue

    # Pass 2: word-boundary regex against profile_text
    # Prevents "git" matching "digital", "scala" matching "scalable"
    pattern = r'(?<![a-z0-9_])' + re.escape(canonical.lower()) + r'(?![a-z0-9_])'
    if re.search(pattern, profile_text.lower()):
        matched.append(canonical)
    else:
        missing.append(canonical)

mandatory_group_score = len(matched) / len(mandatory_alternatives)

# Preferred skills: same two-pass logic
# Skill groups (Python/JS/SQL/BigData/AI_ML/Cloud from settings) expand matching:
# e.g. "pandas" in profile_text satisfies a "python" requirement group

weighted_skill_sum = (mandatory_score × weight_m) + (preferred_score × weight_p)

# Both gates must pass — fail either → DISQUALIFIED with specific reason message
if weighted_skill_sum < min_skill_weighted:
    → "Disqualified: Weighted skill score (0.18) below 0.20 barrier."
if semantic_score < min_semantic:
    → "Disqualified: Semantic similarity (0.31) below 0.40 threshold."
```

**Stage 2 — Full weighted score:**
```python
match_score = (
    mandatory_score  × weight_mandatory  +   # e.g. 0.50 for senior
    preferred_score  × weight_preferred  +   # e.g. 0.20
    semantic_score   × weight_semantic   +   # e.g. 0.25 (RAG jd_level_similarity)
    context_contribution                     # capped at settings.context_boost_cap (8% max)
    + skill_family_penalty                   # negative value (usually 0.0)
)
```

**Context contribution detail:**
```python
# 5 sub-scores combined, each weighted by settings values:
raw_context = (
    exp_score       × weight_experience +     # 1.0 if ≥ min_months, else proportional
    cert_score      × weight_certification +  # matched/required
    loc_score       × weight_location +       # 1.0 if match or "remote"/"any", else 0.0
    mode_score      × weight_work_mode +      # 1.0 if mode matches (wfh=remote mapping)
    title_score     × weight_jd_text          # 1.0 if jd_title substring of designation
)
# Normalize to 0-1 by dividing by total context weights
normalized = raw_context / total_context_weight

# Cap at 8% max contribution regardless of how high the context scores are
context_contribution = min(normalized × role_weights["context"], context_boost_cap)
```

**Skill family penalty:**
```python
# Only fires if JD is a backend/AI role (keyword list from settings)
# Checks candidate's actual skill names:
f_count = count of frontend keywords in member_skill_names  # react, angular, vue, css, html, etc.
b_count = count of backend keywords in member_skill_names   # python, java, node, django, etc.

if f_count > b_count and f_count > 1:
    penalty = settings.skill_family_penalty  # negative, subtracted from match_score
```

**AI Confidence + Boost:**
```python
# ONLY runs if Stage 1 gates passed — deliberately gated to save LLM cost on rejects
if is_qualified:
    ai_fit = get_ai_fit_confidence(jd_text, profile_text)
    confidence_score = ai_fit["confidence_score"]  # 0.0–1.0

    # AI Senior Waiver: ONLY for semantic gate failure, NOT skill gate failure
    # Use case: senior with niche profile text that scores low on generic vectors
    if not scoring_result.is_qualified and is_senior:
        if "Semantic similarity" in qualification_reason:  # explicit check
            if confidence_score >= settings.ai_override_threshold_senior:
                is_qualified = True   # override — logged as ai_override_applied=True

    # AI Boost: linear interpolation between boost_mid and boost_senior
    ai_boost = calculate_ai_boost(confidence_score)

final_score = match_score + ai_boost   (clamped 0.0–1.0)
```

---

## 10. Node 6 — Explanation Generation

**File:** `src/app/ai/agents/explanation_generation.py`
**Utility:** `src/app/ai/utils/explanation_prompt.py`

**Reads from state:** `candidate_scores`, `parsed_jd`
**Writes to state:** mutates `candidate_scores` in-place (adds `detailed_explanation` to each)

**What it does:** Generates human-readable strengths/gaps/summary for each candidate. Does zero scoring — purely translates the Phase 1 ledger into text.

### Cost-control split

```python
# candidate_scores is already sorted by final_score descending (from Node 5)
for i, candidate in enumerate(candidate_scores):
    if i < settings.max_llm_explanations:   # top N → LLM (rich, narrative)
        llm_result = _generate_llm_explanation(...)
    else:                                    # rest → template (zero cost, instant)
        llm_result = _generate_template_explanation(...)
```

Only the highest-scoring candidates get LLM explanations. Everyone else gets a formatted string from `score_breakdown`. This prevents O(n) LLM calls for 40 candidates.

### What the LLM receives (the Phase 1 ledger prompt)

The prompt in `explanation_prompt.py` passes the **full scoring audit trail** as structured sections:

```
Candidate: TM-042 | Score: 79.00% | Role: SENIOR | Fit: HIGH
Job: Senior Python Developer | Backend Engineer | Pune

PHASE 1 SCORING LEDGER:
1. Mandatory Skills: required=[Python,FastAPI,PostgreSQL], satisfaction=75.00%
   Matched: Python, FastAPI | Missing: PostgreSQL

2. Preferred Skills: Matched: Docker | Missing: Kubernetes, Redis

3. Certifications: Matched: None | Missing: None

4. Semantic Similarity: 88.00%

5. Location: ✅  Work Mode: ✅

6. Context Boost: 0.0560 | Experience: 84 months

7. Penalties: 0.00

8. AI Confidence: 0.84 | AI Boost: +0.0600 | Override: Not Applied
   AI Reasoning: Strong Python and FastAPI expertise. PostgreSQL missing but Redis shows DB competency.
```

The prompt explicitly instructs: **"Do not assume or hallucinate requirements not explicitly listed in the REQUISITION REQUIREMENTS or PHASE 1 SCORING LEDGER sections."**

### Gap injection guardrail (post-processing)

After the LLM responds, the agent verifies gaps are concrete — it does NOT trust the LLM to always mention them:

```python
# Mandatory gaps: inserted at position [0] (highest priority, shown first)
if mandatory_missing:
    if not any("mandatory" in gap.lower() for gap in current_gaps):
        current_gaps.insert(0, f"Missing mandatory skills: {', '.join(mandatory_missing)}")

# Preferred gaps: appended (lower priority)
if preferred_missing:
    if not any("preferred" in gap.lower() for gap in current_gaps):
        current_gaps.append(f"Missing preferred skills: {', '.join(preferred_missing[:3])}")
        # Capped at 3 — avoids overwhelming the gap list

# Cert gaps: appended (same pattern)
if cert_missing:
    if not any("certification" in gap.lower() for gap in current_gaps):
        current_gaps.append(f"Missing certifications: {', '.join(cert_missing)}")
```

Duplicate check (`any("mandatory" in gap.lower() ...)`) prevents inserting the same gap twice if the LLM already mentioned it.

### Robust JSON parsing (ai_confidence.py — also used here)

`_parse_json_robustly()` handles the 3 most common LLM JSON formatting failures:
1. Direct `json.loads()` — works for clean JSON
2. Markdown block extraction — finds ` ```json ... ``` ` wrapper and strips it
3. First `{` to last `}` extraction — handles LLM that adds a preamble sentence before the JSON

If all 3 fail → returns `{}` and logs an error. Node falls back to template explanation.

---

## 11. Node 7 — Result Aggregation

**File:** `src/app/ai/agents/result_aggregation.py`

**Reads from state:** `candidate_scores` (with `detailed_explanation` attached by Node 6)
**Writes to state:** `final_results`, `total_evaluated`, `total_qualified`, `metrics`

**What it does:** The simplest and final node. No scoring, no LLM, no DB. Pure reshaping of `candidate_scores` into the API-ready `final_results` format.

### Per-candidate transformation

```python
# Fit level — same thresholds as Node 6 (no shared constant — must stay in sync manually)
fit_level = "HIGH"   if final_score >= 0.75
          | "MEDIUM" if final_score >= 0.50
          | "LOW"    otherwise

status = "QUALIFIED" if is_qualified else "DISQUALIFIED"

# Score conversion: internal float → API percentage
profile_score = round(final_score * 100, 2)   # 0.79 → 79.0

# Explanation: flat list of strings assembled from detailed_explanation dict
explanation = [
    "Summary: Strong match for Senior Python Developer role",
    "Analysis: Final Score: 0.79. Mandatory Group=0.75...",
    "Strengths: Strong Python & FastAPI expertise...",
    "Gaps: Missing mandatory skills: PostgreSQL...",
    "Recommendation: Suitable for interview — address PostgreSQL gap"
]
# Fallback if detailed_explanation is missing: ["Status: QUALIFIED", "Reasoning: ...", "AI Analysis: ..."]
```

### The detailed_breakdown — full audit trail

Each `final_result` entry carries the complete scoring history for downstream use:
```python
"detailed_breakdown": {
    "phase0_ledger":        ...,   # RAG retrieval scores (Node 4)
    "score_breakdown":      ...,   # ScoringAgent weight components (Node 5)
    "match_reasons":        ...,   # matched/missing skills, certs (Node 5)
    "ai_confidence_score":  ...,
    "ai_boost_applied":     ...,
    "role_type":            ...,   # SENIOR / MID / JUNIOR
    "is_qualified":         ...,
    "qualification_reason": ...    # exact gate failure message if DISQUALIFIED
}
```

### Final state mutations

```python
state["final_results"]   = [list of result_entry dicts, order preserved from Node 5 sort]
state["total_evaluated"] = len(candidate_scores)
state["total_qualified"] = count of QUALIFIED candidates

# Consolidated metrics — single place to read total LLM cost for this request
state["metrics"] = {
    "total_evaluated": ...,
    "total_qualified": ...,
    "token_count":  state["cumulative_tokens"],    # running total from ALL nodes
    "cost_usd":     state["cumulative_cost_usd"]   # running total from ALL nodes
}
```

The `metrics` dict consolidates token/cost totals that were incrementally accumulated by every LLM-calling node (parsing, semantic validation, skill normalization, AI confidence, explanation generation).

---

## 12. The LLM Client

**File:** `src/app/ai/utils/llm_client.py`

A singleton (`llm_client = LLMClient()`) initialized once at module import. Supports 3 providers:

```
settings.llm_provider = "openai" → OpenAI client  → gpt-4-turbo (or configured model)
                       = "groq"  → Groq client    → llama-3.1-70b
                       = "google"→ genai.Client   → gemini-2.5-flash
```

All providers go through `chat_completion()`:
- Exponential backoff retry on 429 rate limit (up to 5 attempts, delay = `2^attempt` seconds)
- Returns `(content_str, usage_dict)` — same interface regardless of provider
- `get_completion_cost(usage)` → calculates USD from token counts × per-million rates

Each `_openai_completion`, `_groq_completion`, `_google_completion` is decorated `@instrument` for TruLens capture.

---

## 13. AI Confidence & Boost

**File:** `src/app/ai/utils/ai_confidence.py`

### get_ai_fit_confidence(jd_text, profile_text)

LLM prompt:
```
Evaluate fit between Candidate Profile and Job Description.
Focus on experience alignment, skill depth (beyond keywords), and career trajectory.

Job Description: {jd_text}
Candidate Profile: {profile_text}

Return JSON: {confidence_score (0.0-1.0), reasoning, key_strengths, major_gaps}
```

Returns `{"confidence_score": 0.84, "reasoning": "...", "key_strengths": [...], "major_gaps": [...]}`

Has robust JSON parsing with 3 fallback strategies (direct parse → markdown block → first `{` to last `}`).

### calculate_ai_boost(confidence)

```python
if confidence < settings.ai_confidence_threshold_boost:
    return 0.0

# Linear interpolation between boost_mid and boost_senior
boost = boost_mid + (boost_senior - boost_mid) * (confidence - threshold) / (1.0 - threshold)
return min(boost, boost_senior)
```

---

## 14. Team Member Embeddings: How They're Built (Cron)

**File:** `src/app/cron/embedding/embedding_processor.py`

The cron job (`python -m app.cron.main`) runs on a schedule to keep team member embeddings fresh.

### Per-member pipeline

```
1. assemble_skills_text(member_id, db)
   → "Python, FastAPI, PostgreSQL, Docker, ..."

2. assemble_certifications_text(member_id, db)
   → "AWS Certified Solutions Architect, ..."

3. MCPResumeClient.fetch_resume_sync(profile_url)
   → raw resume text from Google Drive

4. PIIScrubber.scrub_text(resume_text)
   → redacted resume text

5. SHA-256 hash of (resume || skills || certs)
   → if hash unchanged and not --force: SKIP (no re-embed)

6. GemmaEmbeddingAgent.embed_text() × 3:
   → resume_embedding    [768 floats]
   → skills_embedding    [768 floats]
   → certs_embedding     [768 floats]

7. Weighted average:
   → embedding = resume * 0.50 + skills * 0.30 + certs * 0.20
   → L2-normalized

8. upsert_team_member_embeddings() → DB commit
```

### What's stored in team_member_embeddings table

```
embedding               → pgvector(768)  — the weighted average (used for <-> search)
resume_embedding        → pgvector(768)  — individual (stored, not yet used in search)
skills_embedding        → pgvector(768)  — individual (stored, not yet used in search)
certifications_embedding→ pgvector(768)  — individual (stored, not yet used in search)
profile_text            → text           — "Skills: ...\nCertifications: ...\nResume: ..."
skills_text             → text           — raw skill names (for BM25 tsvector)
certifications_text     → text           — raw cert names (for BM25 tsvector)
resume_text             → text           — scrubbed resume (for BM25 and AI confidence)
content_hash            → text           — SHA-256 for skip-if-unchanged logic
```

---

## 15. 5 JD Vectors vs 3 Member Vectors — What's Actually Used

This is confusing because the number of vectors on each side doesn't match. Here's the actual usage:

### JD side (Node 3 creates 5, but only 2 are used)

| JD Vector | Actually used? | Where |
|-----------|---------------|-------|
| `full_jd_vector` | **YES** | Node 4 SQL: `e.embedding <-> :vector` (L2 distance) |
| `jd_level_vector` | **YES** | Node 4 post-SQL: becomes `jd_level_similarity` → used by ScoringAgent as `semantic_score` |
| `mandatory_vector` | **NO** | Created, stored in state, never queried |
| `preferred_vector` | **NO** | Created, stored in state, never queried |
| `certification_vector` | **NO** | Created, stored in state, never queried |

### Member side (4 vectors stored, only 1 used for search)

| Member Vector | Actually used? | Where |
|---------------|---------------|-------|
| `embedding` (weighted avg) | **YES** | Node 4 SQL `<->` distance against `full_jd_vector` |
| `resume_embedding` | **NO** | Stored for future multi-vector search (CR-EMB-002, not activated) |
| `skills_embedding` | **NO** | Same |
| `certifications_embedding` | **NO** | Same |

**Bottom line:** Node 4 SQL does `full_jd_vector <-> embedding (weighted avg)`. That's the only vector-to-vector comparison happening. Everything else is either keyword text (BM25) or stored for future use.

---

## 16. Node 4 vs Node 5 — Why Both Exist

They look similar ("find good candidates") but solve different problems:

### Node 4 (RAG) — "Who could possibly match?" (Cheap, broad, approximate)

| | Detail |
|--|--------|
| Operates on | Pre-computed embeddings in DB (built offline by cron) |
| Skill check | `"python" in skills_text.lower()` — substring match |
| Cost | 1 SQL query, pure DB |
| Output | Top 40 with rough similarity score |
| Purpose | Eliminate obviously wrong people before expensive scoring |

### Node 5 (Scoring) — "Who actually qualifies?" (Expensive, precise, authoritative)

| | Detail |
|--|--------|
| Operates on | Live DB queries per candidate (skills table, certs, allocations) |
| Skill check | Set intersection of `skill_master_id` arrays + word-boundary regex |
| Cost | N DB queries + 1 LLM call per qualified candidate |
| Output | Final scores with precise breakdown, AI boost, qualification decision |
| Purpose | Make the actual hiring-quality judgment |

### The Node 4 score is discarded

Node 4's `final_similarity` is **thrown away** in Node 5. Only `jd_level_similarity` survives — it becomes the `semantic_similarity` component of the final score.

Everything else is recalculated from scratch using structured DB data (actual `skill_master` IDs, not text substrings).

```
ALL TEAM MEMBERS (e.g. 500+)
         │
    [Node 4 RAG]
    1 SQL query — fast, approximate
    "Does the profile mention the right words? Are vectors geometrically close?"
         │
    TOP 40 CANDIDATES
         │
    [Node 5 Scoring]
    Per-candidate DB lookups + deterministic math + LLM
    "Do they ACTUALLY have the skills? Are they available? What's their real score?"
         │
    FINAL RANKED LIST (precise, auditable)
```

**Node 4 is the bouncer (fast, rough). Node 5 is the interview panel (slow, thorough).**

---

## 17. Concrete Input/Output Per Node

Using example: "Senior Python Developer" role at Pune/Remote, Hybrid, 5+ years, mandatory: Python, FastAPI, PostgreSQL.

---

### Graph initialized (router)

```json
{
  "requisition_input": {
    "request_id": "REQ-2024-001",
    "correlation_id": "corr-abc-123",
    "job_description": {
      "title": "Senior Python Developer",
      "role": "Backend Engineer",
      "jd_text": "We need a senior Python developer with 5+ years...",
      "mandatory_skills": ["Python", "FastAPI", "PostgreSQL"],
      "preferred_skills": ["Docker", "Kubernetes"],
      "certifications": [],
      "experience": {"min_months": 60, "max_months": null},
      "location": ["Pune", "Remote"],
      "work_mode": ["Hybrid"]
    }
  },
  "parsed_jd": null,
  "normalized_skills": null,
  "embedding_result": null,
  "retrieved_candidates": null,
  "candidate_scores": null,
  "final_results": null,
  "error_message": null
}
```

---

### After Node 1 — requisition_parsing

LLM found `"REST APIs"` in the `jd_text` and added it. Original skills stayed mandatory.

```json
{
  "parsed_jd": {
    "normalized_title": "Senior Python Developer",
    "normalized_role": "Backend Engineer",
    "extracted_mandatory_skills": ["Python", "FastAPI", "PostgreSQL", "REST APIs"],
    "extracted_preferred_skills": ["Docker", "Kubernetes", "Redis"],
    "experience": {"min_months": 60, "max_months": null},
    "certifications_required": [],
    "jd_text": "We need a senior Python developer with 5+ years...",
    "location": ["Pune", "Remote"],
    "work_mode": ["Hybrid"]
  },
  "llm_call_logs": [
    {"agent_name": "requisition_parsing", "total_tokens": 820, "cost_usd": 0.0041}
  ],
  "cumulative_tokens": 820
}
```

---

### After Node 2 — skill_normalization

LLM normalized aliases; direct + fuzzy lookup found skill IDs. `mandatory_alternatives` maps each required skill to all equivalent IDs.

```json
{
  "normalized_skills": {
    "mandatory_skill_ids": ["sk-001", "sk-002", "sk-003", "sk-004"],
    "preferred_skill_ids": ["sk-010", "sk-011", "sk-015"],
    "mandatory_alternatives": {
      "Python":     ["sk-001", "sk-022"],
      "FastAPI":    ["sk-002"],
      "PostgreSQL": ["sk-003", "sk-031"],
      "REST APIs":  ["sk-004", "sk-041"]
    },
    "preferred_alternatives": {
      "Docker":     ["sk-010"],
      "Kubernetes": ["sk-011"],
      "Redis":      ["sk-015"]
    },
    "mandatory_enriched": {
      "sk-001": ["Django", "Flask", "asyncio"],
      "sk-003": ["SQL", "pgvector", "PostGIS"]
    },
    "normalized_certifications": [],
    "certification_enriched": {}
  }
}
```

---

### After Node 3 — embedding

5 vectors created. Only `full_jd_vector` and `jd_level_vector` are used downstream.

```json
{
  "embedding_result": {
    "jd_level_vector":      [0.021, -0.043, 0.112, ...],
    "mandatory_vector":     [0.084,  0.031, -0.009, ...],
    "preferred_vector":     [-0.012, 0.067, 0.044, ...],
    "certification_vector": [0.0, 0.0, 0.0, ...],
    "full_jd_vector":       [0.055, -0.018, 0.033, ...],
    "model": "google/embeddinggemma-300m"
  }
}
```

---

### After Node 4 — rag_retrieval

SQL ran, returned top matches above 40% threshold. Scores here are rough approximations.

```json
{
  "retrieved_candidates": [
    {
      "team_member_id": "TM-042",
      "final_similarity": 0.81,
      "jd_level_similarity": 0.88,
      "mandatory_similarity": 0.75,
      "preferred_similarity": 0.60,
      "certification_similarity": 1.0,
      "phase0_score_breakdown": {
        "semantic_fit": 0.88,
        "keyword_score": 0.72,
        "mandatory_score": 0.75,
        "experience_relevance": 1.0,
        "mandatory_penalty_assigned": false
      }
    },
    {"team_member_id": "TM-017", "final_similarity": 0.74, "jd_level_similarity": 0.71, "...": "..."},
    {"team_member_id": "TM-091", "final_similarity": 0.61, "jd_level_similarity": 0.65, "...": "..."}
  ]
}
```

---

### After Node 5 — matching_scoring

Precise scores based on actual DB data. `final_similarity` from Node 4 is discarded. `jd_level_similarity: 0.88` becomes `semantic_similarity` in the breakdown.

```json
{
  "candidate_scores": [
    {
      "team_member_id": "TM-042",
      "final_score": 0.79,
      "is_qualified": true,
      "role_type": "SENIOR",
      "base_agentic_score": 0.73,
      "ai_confidence_score": 0.84,
      "ai_boost": 0.06,
      "ai_override_applied": false,
      "score_breakdown": {
        "mandatory_skills_group": 0.75,
        "preferred_skills": 0.60,
        "semantic_similarity": 0.88,
        "context_score": 0.70,
        "context_contribution": 0.056,
        "weight_m": 0.50,
        "weight_p": 0.20,
        "weight_s": 0.25,
        "penalties": 0.0
      },
      "match_reasons": {
        "mandatory_matched": ["Python", "FastAPI"],
        "mandatory_missing": ["PostgreSQL"],
        "preferred_matched": ["Docker"],
        "preferred_missing": ["Kubernetes", "Redis"],
        "certification_matched": [],
        "certification_missing": [],
        "experience_score": 1.0,
        "location_matched": true,
        "work_mode_matched": true
      },
      "ai_reasoning": "Strong Python and FastAPI expertise. PostgreSQL is missing but Redis experience shows DB competency.",
      "is_available": true
    }
  ]
}
```

---

### After Node 6 — explanation_generation

`detailed_explanation` added to each candidate dict (in-place mutation):

```json
{
  "detailed_explanation": {
    "summary": "Strong match for Senior Python Developer role",
    "fit_analysis": "Final Score: 0.79. Mandatory Group=0.75, Semantic=0.88, Context=0.056, AI Boost=0.06",
    "strengths": [
      "Strong Python & FastAPI expertise",
      "Excellent semantic alignment with JD",
      "AI Boost applied (+0.06)"
    ],
    "gaps": [
      "Missing mandatory skills: PostgreSQL",
      "Missing preferred skills: Kubernetes, Redis"
    ],
    "recommendation": "Suitable for interview — address PostgreSQL gap during screening"
  }
}
```

---

### After Node 7 — result_aggregation

Final API-ready output:

```json
{
  "final_results": [
    {
      "team_member_id": "TM-042",
      "profile_score": 79.0,
      "fit_level": "HIGH",
      "status": "QUALIFIED",
      "availability_match": true,
      "explanation": [
        "Summary: Strong match for Senior Python Developer role",
        "Analysis: Final Score: 0.79. Mandatory Group=0.75, Semantic=0.88...",
        "Strengths: Strong Python & FastAPI expertise, Excellent semantic alignment...",
        "Gaps: Missing mandatory skills: PostgreSQL, Missing preferred: Kubernetes...",
        "Recommendation: Suitable for interview — address PostgreSQL gap"
      ],
      "detailed_breakdown": {
        "phase0_ledger": {"semantic_fit": 0.88, "keyword_score": 0.72, "...": "..."},
        "score_breakdown": {"mandatory_skills_group": 0.75, "semantic_similarity": 0.88, "...": "..."},
        "match_reasons": {"mandatory_matched": ["Python", "FastAPI"], "mandatory_missing": ["PostgreSQL"], "...": "..."},
        "ai_confidence_score": 0.84,
        "ai_boost_applied": 0.06,
        "role_type": "SENIOR",
        "is_qualified": true,
        "qualification_reason": "Qualified"
      }
    }
  ],
  "total_evaluated": 3,
  "total_qualified": 2,
  "metrics": {
    "token_count": 3420,
    "cost_usd": 0.0187
  }
}
```

---

## 18. Where LLM Is Used vs Deterministic Code

| Step | File | LLM or Deterministic |
|------|------|----------------------|
| Basic validation | `requisition_validation.py` | **Deterministic** (length, field checks) |
| Semantic validation | `semantic_validation.py` | **LLM** |
| Parse + normalize JD | `requisition_parsing.py` | **LLM** |
| Normalize skills to canonical | `skill_normalization.py` | **LLM** |
| Generate JD embeddings | `embedding.py` + `gemma_embedding.py` | **Local model** (Gemma, not API) |
| Retrieve candidates | `rag_retrieval.py` | **SQL** (pgvector + BM25) |
| Mandatory skill matching | `scoring.py` | **Deterministic** (set intersection + regex) |
| Experience/cert/location scoring | `scoring.py` | **Deterministic** (arithmetic) |
| Availability check | `availability.py` | **Deterministic** (date + allocation math) |
| AI fit confidence | `ai_confidence.py` | **LLM** (qualified candidates only) |
| AI boost calculation | `ai_confidence.py` | **Deterministic** (linear formula) |
| AI senior waiver | `matching_scoring.py` | **Deterministic** (threshold check) |
| Generate explanations (top N) | `explanation_generation.py` | **LLM** |
| Generate explanations (rest) | `explanation_generation.py` | **Deterministic** (template) |
| Qualify/disqualify + format | `result_aggregation.py` | **Deterministic** |

**Core design rule (from specs):** LLMs are used for language tasks only — parsing, normalization, explanation. All scoring math is deterministic Python. This ensures scores are reproducible and auditable regardless of which LLM provider is active.

---

## 19. Existing Documents to Read

These are ranked by how useful they are vs. how up-to-date they are:

### Highly useful — read these

| File | What it covers |
|------|---------------|
| `docs/architecture/agentic-orchestration.md` | Most complete architecture doc. Agent inventory, graph topology, state flow. Updated April 2026. Closest thing to what this guide covers officially. |
| `specs/ai/langgraph-overview.md` | Why LangGraph was chosen, the core design principle (LLMs for language, not logic) |
| `specs/ai/ai-guardrails.md` | PII handling, output schema enforcement, LLM constraints, auditability rules |
| `specs/ai/graph-topology.md` | Node descriptions and edge definitions (NOTE: references PII node as active — it's disabled in current code) |
| `specs/ai/state-schema.md` | State schema definitions (NOTE: older version, actual code has more fields) |
| `search_and_scoring_logic.md` | Root-level file about the scoring formula — check this for weight values |

### Per-agent specs (useful for individual node deep-dives)

| File | Covers |
|------|--------|
| `specs/ai/agent-specs/matching-scoring-agent.md` | Phase 1 scoring logic, role configs, qualification gates |
| `specs/ai/agent-specs/skill-normalization-agent.md` | Ontology lookup, canonical mapping, fuzzy matching |
| `specs/ai/agent-specs/result-aggregation-agent.md` | Qualification decisions, fit levels |
| `specs/ai/agent-specs/availability-evaluation-agent.md` | Allocation-based availability logic |

### Operational docs (useful when running the system)

| File | Covers |
|------|--------|
| `docs/setup-cron-ingest-embed.md` | How to run the cron embedding pipeline |
| `docs/operations/resumption_cron.md` | How graph resumption works when a run gets stuck |
| `docs/runbooks/local_dev.md` | Local dev setup |
| `docs/checkpoint-visual-guide.md` | Visual guide to the LangGraph checkpoint/audit system |

### Specs to read for API contract understanding

| File | Covers |
|------|--------|
| `specs/functional/fr-1-requisition-request-api.md` | POST endpoint schema — what the API accepts |
| `specs/functional/fr-2-requisition-match-response.md` | GET endpoint schema — what the API returns |

### Warning: these docs have drifted from current code

- `specs/ai/graph-topology.md` — shows PII Scrubber as active Node 0; in code it's disabled
- `specs/ai/state-schema.md` — older schema, missing `embedding_result`, `retrieved_candidates`, `token_metrics`, `llm_call_logs`
- `docs/architecture/overview.md` — mostly a stub, says "TODO: Add architecture diagram"

When in doubt, **the code is the truth**. These docs describe intent; the code describes what actually runs.
