# Agent Specification: RAG Retrieval Agent

**Version:** 1.3  
**Modified By:** CR-SCORE-003, hybrid-search-improvement  
**Last Updated:** 2026-05-05  

## 1. Purpose
The RAG Retrieval Agent finds the most relevant candidates in the PostgreSQL database using a hybrid search strategy (BM25 + Multi-Vector Semantic Search via pgvector). It acts as a cheap pre-filter — narrowing the full team member pool down to the top N candidates before expensive per-candidate scoring in Node 5.

There is no separate vector database. pgvector runs inside PostgreSQL. The SQL query IS the retrieval.

---

## 2. Hybrid Search Strategy

The agent combines keyword matching and semantic similarity to ensure high recall:
- **BM25 (Keyword)**: `ts_rank` against `skills_text || certifications_text || profile_text` — matches specific skill names, certifications, and titles.
- **Vector (Semantic)**: Five pgvector `<->` distance comparisons, each pairing a JD component vector against the most relevant member embedding column.
- **Weighting**: 70% Keyword / 30% Vector — configurable via `hybrid_ratio_bm25` and `hybrid_ratio_vector` in `settings.py`.

The 70/30 ratio applies to the combined `semantic + keyword` budget (0.50 of total score). Within that:
- `vec_w = 0.50 × hybrid_ratio_vector` (default 0.15)
- `kw_w  = 0.50 × hybrid_ratio_bm25`  (default 0.35)

---

## 3. Multi-Vector Routing

Queries are decomposed and routed to specific embedding columns. Five vector pairs are computed in a single SQL query:

| JD Vector | Target Member Column | SQL Alias | Purpose |
| :--- | :--- | :--- | :--- |
| `full_jd_vector` | `e.embedding` | `full_jd_distance` | Broad proximity — primary `ORDER BY` |
| `jd_level_vector` | `COALESCE(resume_embedding, embedding)` | `level_distance` | Role/seniority alignment → `jd_level_similarity` |
| `mandatory_vector` | `COALESCE(skills_embedding, embedding)` | `mandatory_skills_distance` | Required skills in member skill space |
| `preferred_vector` | `COALESCE(skills_embedding, embedding)` | `preferred_skills_distance` | Preferred skills in member skill space |
| `certification_vector` | `COALESCE(certifications_embedding, embedding)` | `cert_distance` | Certification alignment |

`skills_embedding` is queried twice (once for mandatory, once for preferred) — the member has one skills vector covering all skills with no mandatory/preferred split.

The SQL query orders results by `full_jd_distance ASC`. Python rescores with the multi-vector formula after fetch.

---

## 4. Scoring Formula

### 4a. Per-vector similarity conversion
```
similarity = 1 / (1 + distance)     # L2 distance → 0-1 scale
```

### 4b. Multi-vector composite semantic score
```
multi_vec_semantic = full_jd_sim   × rag_weight_full_jd          (default 0.30)
                   + level_sim     × rag_weight_level             (default 0.40)
                   + mandatory_sim × rag_weight_skills_mandatory  (default 0.20)
                   + preferred_sim × rag_weight_skills_preferred  (default 0.10)
```
Weights configurable in `settings.py`. Must sum to 1.0.

### 4c. Total score
```
total_score = multi_vec_semantic   × vec_w    (0.15 default)
            + bm25_keyword_norm    × kw_w     (0.35 default)
            + mandatory_text_ratio × 0.30
            + preferred_text_ratio × 0.05
            + experience_relevance × 0.05
            + cert_text_ratio      × 0.05
            + location_match       × 0.025
            + work_mode_match      × 0.025
```
Total sums to 1.0.

**Mandatory penalty:** If mandatory skills are present but no text substring matches found → `total_score × 0.6`.

---

## 5. jd_level_similarity — Key Output Field

`jd_level_similarity` is the most important field produced by this agent. Node 5 (`scoring.py:345`) reads it directly as `s_score`, which:
- Controls the **semantic qualification gate** (`s_score < min_semantic` → DISQUALIFIED)
- Contributes **25% weight** to the final `match_score`

**Current behavior** (`rag_use_level_vector = True`, default):
```
jd_level_similarity = 1 / (1 + level_distance)
level_distance = jd_level_vector <-> COALESCE(resume_embedding, embedding)
```
Measures: "Does this person's career/resume align with the stated job level and role category?"

**Rollback** (`rag_use_level_vector = False` in `.env`):
```
jd_level_similarity = 1 / (1 + full_jd_distance)
```
Reverts to old behavior (full JD text vs blended embedding) without a code deploy.

---

## 6. Fallback Logic

- **NULL Column Strategy**: `COALESCE(specific_embedding, e.embedding)` in SQL — if `resume_embedding`, `skills_embedding`, or `certifications_embedding` is NULL (legacy or unprocessed member), the query falls back to the weighted-average `e.embedding`. No member is excluded from retrieval.
- **Node 3 vector failure**: If a specific JD component vector is None in state, it falls back to `full_jd_vector` before being passed to SQL.
- **Similarity threshold**: Candidates must exceed `rag_similarity_threshold` (default `0.40`) on `final_similarity` to be returned to Node 5. Configurable in `settings.py`.
- **Pool size**: SQL fetches `rag_sql_limit` rows (default 100). Python returns up to `rag_final_candidates` (default 40) after threshold filtering and sorting.

---

## 7. phase0_score_breakdown

Each candidate dict includes a full audit trail in `phase0_score_breakdown`, visible in the API response under `detailed_breakdown.phase0_ledger`:

| Key | Description |
| :--- | :--- |
| `total_score` | Final RAG score before threshold filter |
| `semantic_fit` | Multi-vector composite score |
| `keyword_score` | Normalised BM25 ts_rank value |
| `mandatory_score` | Mandatory text keyword match ratio |
| `preferred_score` | Preferred text keyword match ratio |
| `experience_relevance` | Partial credit score for experience range |
| `certification_score` | Cert text match ratio |
| `location_compatibility` | Boolean |
| `work_mode_compatibility` | Boolean |
| `mandatory_penalty_assigned` | Boolean — was the 0.6× penalty applied |
| `full_jd_vector_sim` | `full_jd_vector <-> e.embedding` similarity |
| `level_vector_sim` | `jd_level_vector <-> COALESCE(resume_embedding, embedding)` similarity |
| `mandatory_skills_vector_sim` | `mandatory_vector <-> COALESCE(skills_embedding, embedding)` similarity |
| `preferred_skills_vector_sim` | `preferred_vector <-> COALESCE(skills_embedding, embedding)` similarity |
| `cert_vector_sim` | `cert_vector <-> COALESCE(certifications_embedding, embedding)` similarity |

---

## 8. Settings Reference

All RAG-specific settings in `settings.py`:

| Setting | Default | Description |
| :--- | :--- | :--- |
| `hybrid_ratio_bm25` | `0.7` | BM25 share of the semantic+keyword budget |
| `hybrid_ratio_vector` | `0.3` | Vector share of the semantic+keyword budget |
| `rag_similarity_threshold` | `0.40` | Minimum `final_similarity` to pass to Node 5 |
| `rag_sql_limit` | `100` | SQL `LIMIT` — initial candidate pool |
| `rag_final_candidates` | `40` | Maximum candidates returned to Node 5 |
| `rag_weight_full_jd` | `0.30` | Weight of `full_jd_sim` in multi-vector composite |
| `rag_weight_level` | `0.40` | Weight of `level_sim` in multi-vector composite |
| `rag_weight_skills_mandatory` | `0.20` | Weight of `mandatory_vec_sim` in multi-vector composite |
| `rag_weight_skills_preferred` | `0.10` | Weight of `preferred_vec_sim` in multi-vector composite |
| `rag_use_level_vector` | `True` | Use `level_distance` for `jd_level_similarity`; set `False` to revert |

---

## 9. State Mutations

- **Allowed**:
  - Populates `state["retrieved_candidates"]` with candidate dicts containing `team_member_id`, `final_similarity`, `mandatory_similarity`, `preferred_similarity`, `jd_level_similarity`, `certification_similarity`, `phase0_score_breakdown`.
- **Forbidden**:
  - Must not modify any candidate profile data.
  - Must not write to any state key other than `retrieved_candidates` and `error_message`.
