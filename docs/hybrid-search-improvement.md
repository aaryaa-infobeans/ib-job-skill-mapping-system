# Hybrid Search Improvement — RAG Retrieval Node

> Design document for upgrading Node 4 (RAG Retrieval) from single-vector to multi-vector hybrid search.
> No code has been changed yet. This document describes what needs to change and why.

---

## Table of Contents

1. [How RAG Retrieval Works Today](#1-how-rag-retrieval-works-today)
2. [What is pgvector — No Separate Vector DB](#2-what-is-pgvector--no-separate-vector-db)
3. [What Vectors Exist and Where](#3-what-vectors-exist-and-where)
4. [The Core Problem — Only 1 of 9 Vectors Is Used](#4-the-core-problem--only-1-of-9-vectors-is-used)
5. [Three Bugs in the Current Implementation](#5-three-bugs-in-the-current-implementation)
6. [The Multi-Vector Pairing Design](#6-the-multi-vector-pairing-design)
7. [Why SQL and Not Python](#7-why-sql-and-not-python)
8. [Why Specialized Pairs Beat the Blended Average](#8-why-specialized-pairs-beat-the-blended-average)
9. [Proposed SQL Query](#9-proposed-sql-query)
10. [Proposed Scoring Formula Changes](#10-proposed-scoring-formula-changes)
11. [jd_level_similarity — The Most Important Change](#11-jd_level_similarity--the-most-important-change)
12. [Downstream Impact on Node 5](#12-downstream-impact-on-node-5)
13. [New Settings Required](#13-new-settings-required)
14. [Files to Change](#14-files-to-change)
15. [Risk and Rollback](#15-risk-and-rollback)
16. [Verification Checklist](#16-verification-checklist)

---

## 1. How RAG Retrieval Works Today

The RAG retrieval node runs a single SQL query against PostgreSQL using pgvector. The SQL:
1. Filters candidates by mandatory skills (BM25 full-text), location, work mode, experience
2. Orders by vector distance (L2) between the JD vector and member embedding
3. Returns the closest rows

Python post-processing then rescores with a weighted formula and returns the top candidates to Node 5.

**Files:**
- Node: `src/app/ai/agents/rag_retrieval.py`
- Agent/Logic: `src/app/ai/utils/rag_retrieval.py`

---

## 2. What is pgvector — No Separate Vector DB

This system has **no separate vector database** (no ChromaDB, Pinecone, Weaviate, etc.).

pgvector is a PostgreSQL extension that adds:
- A `vector(N)` column type for storing float arrays
- The `<->` operator for computing L2 distance between two vectors
- IVFFlat and HNSW indexes for fast approximate nearest-neighbor search

The `team_member_embeddings` table in PostgreSQL IS the vector store. The SQL query IS the retrieval. pgvector computes distances only for the `<->` expressions you write in the SELECT — it has no awareness of other stored vector columns unless explicitly referenced.

---

## 3. What Vectors Exist and Where

### Member side — stored in `team_member_embeddings` by cron

```
Column                    Dimension   Nullable   Index         Populated when
─────────────────────────────────────────────────────────────────────────────
embedding                 768         NO         —             Always (weighted avg)
resume_embedding          768         YES        IVFFlat       Member has resume
skills_embedding          768         YES        IVFFlat       Member has skills
certifications_embedding  768         YES        IVFFlat       Member has certs
```

**How `embedding` is built:**
```
embedding = 0.50 × resume_embedding
          + 0.30 × skills_embedding
          + 0.20 × certifications_embedding
(L2-normalized weighted average)
```

The member's `skills_embedding` represents ALL skills they have — there is no mandatory/preferred distinction on the member side. A member simply has skills.

### JD side — created by Node 3, stored in `state["embedding_result"]`

```
Key                    Content embedded
─────────────────────────────────────────────────────────────────────
full_jd_vector         Raw jd_text (entire job description blob)
jd_level_vector        "Job level: Backend Engineer"
mandatory_vector       "Required skills: Python, FastAPI, PostgreSQL"
preferred_vector       "Preferred skills: Docker, Kubernetes"
certification_vector   "Certifications: AWS SAA. Related concepts: ..."
```

All 5 JD vectors are computed by Node 3 every time and stored in state. They are available to the RAG node. Node 3 file: `src/app/ai/agents/embedding.py`.

---

## 4. The Core Problem — Only 1 of 9 Vectors Is Used

Current SQL (lines 102-125 in `src/app/ai/utils/rag_retrieval.py`):

```sql
e.embedding <-> CAST(:vector AS vector) AS similarity_score
```

The `:vector` parameter is `embedding_result.full_jd_vector`. This is the only vector comparison happening.

That means:
- 3 member vectors sitting in DB with IVFFlat indexes: **never queried**
- 4 out of 5 JD vectors computed by Node 3 every request: **discarded**
- The IVFFlat indexes on `skills_embedding`, `resume_embedding`, `certifications_embedding`: **never used**

The spec (`specs/ai/agent-specs/rag-retrieval.md`) explicitly describes multi-vector routing — mandatory skills → `skills_embedding`, job title → `resume_embedding`, certifications → `certifications_embedding`. This was never implemented. The infrastructure was built (cron produces the vectors, migrations created the indexes) but the RAG query was not updated to use it.

---

## 5. Three Bugs in the Current Implementation

### Bug 1 — LIMIT 10 vs Python [:40] mismatch

```python
# SQL (line 124):
LIMIT 10

# Python post-processing (line 140):
return final_candidates[:40]
```

The SQL returns at most 10 rows. Python tries to slice the top 40. In practice, Node 5 **never receives more than 10 candidates**. This is a silent recall bottleneck — no error, just quietly limited output.

### Bug 2 — Threshold hardcoded, settings ignored

```python
# Code (line 136):
final_candidates = [c for c in candidates if c.final_similarity > 0.40]

# settings.py:
rag_similarity_threshold: float = 0.5   # Never read by RAG code
```

The setting exists but is never consumed.

### Bug 3 — `jd_level_similarity` is the wrong value

```python
# Line 220:
jd_level_similarity=round(semantic_fit, 4),

# Where semantic_fit (line 186) is:
semantic_fit = 1.0 / (1.0 + float(distance))
# and distance = full_jd_vector <-> e.embedding
```

`jd_level_similarity` and `semantic_fit` are the same number. The `jd_level_vector` that was specifically created in Node 3 to represent "Job level: Backend Engineer" is never used. This matters because `jd_level_similarity` is what flows to Node 5 as `s_score` — the semantic gate and 25% weight in `match_score`. See `src/app/ai/utils/scoring.py` line 345.

---

## 6. The Multi-Vector Pairing Design

Each JD vector is paired with the most semantically relevant member vector column:

```
JD Vector               Member Vector                           SQL Alias
────────────────────────────────────────────────────────────────────────────────
full_jd_vector      <-> e.embedding                         → full_jd_distance
                        (weighted avg — broad proximity)
                        Used for ORDER BY (primary sort)

jd_level_vector     <-> COALESCE(resume_embedding,          → level_distance
                                  e.embedding)
                        Resume captures career narrative
                        and role history — best match for
                        "Job level: Backend Engineer"

mandatory_vector    <-> COALESCE(skills_embedding,          → mandatory_skills_distance
                                  e.embedding)
                        Skills column is keyword-dense —
                        "Required skills: Python, FastAPI"
                        vs "Python, FastAPI, Docker, React"

preferred_vector    <-> COALESCE(skills_embedding,          → preferred_skills_distance
                                  e.embedding)
                        Same skills column — skills_embedding
                        covers ALL member skills, both what
                        would be mandatory and preferred

certification_vector <-> COALESCE(certifications_embedding, → cert_distance
                                   e.embedding)
                         Cert column vs cert JD text
```

**Why `skills_embedding` appears twice:**
The member has one skills vector covering all their skills. The JD has two separate vectors (mandatory and preferred requirements). Both are compared against the same member column — pgvector handles both in the same scan pass. The results serve different purposes: `mandatory_skills_distance` feeds the mandatory match signal, `preferred_skills_distance` feeds the preferred match signal.

**Why COALESCE fallback:**
Members who were embedded before the multi-vector columns were added (or whose resume fetch failed) will have NULL for `resume_embedding`, `skills_embedding`, `certifications_embedding`. COALESCE ensures they fall back to `e.embedding` (the weighted average) so no member is excluded from retrieval.

---

## 7. Why SQL and Not Python

The specialized vectors are stored as columns in the `team_member_embeddings` table. To compute similarity between a JD vector (in Python state) and a member vector (in DB), there are two options:

**Option A — Compute distance in SQL (proposed):**
```sql
COALESCE(e.skills_embedding, e.embedding) <-> CAST(:mandatory_vector AS vector)
-- DB computes the distance, returns ONE float per row
-- Data transferred: 3 floats per candidate
```

**Option B — Fetch vectors to Python, compute there:**
```sql
SELECT e.skills_embedding, e.resume_embedding, e.certifications_embedding ...
-- Fetch full 768-dim arrays, then numpy dot product in Python
-- Data transferred: 768 floats × 3 columns × 100 rows ≈ 900KB per request
```

Option A is strictly better:
- pgvector uses IVFFlat index acceleration for `<->` operations
- Only distance scalars (floats) cross the network, not full vectors
- The vector math belongs in the DB where the data lives
- The RAG agent's core job IS the SQL query — improving RAG means improving what the SQL does

---

## 8. Why Specialized Pairs Beat the Blended Average

`e.embedding` is a weighted average of three different content types. When vectors are averaged, each component dilutes the others.

**Example:**

Member: Python, FastAPI, PostgreSQL, Docker (strong backend), resume full of backend narrative.

```
e.embedding = 0.5 × resume_embedding   ← narrative, job titles, experience desc
            + 0.3 × skills_embedding   ← "Python, FastAPI, PostgreSQL, Docker"
            + 0.2 × certs_embedding    ← "AWS SAA"
```

When you do `full_jd_vector <-> e.embedding`, the 50% resume portion introduces noise — the resume discusses things beyond just the skills (company names, project descriptions, soft skills). A candidate with a keyword-heavy resume but weaker actual skills might score similarly to a skilled candidate with a plain resume.

With the specialized pairing:
```
mandatory_vector ("Required: Python, FastAPI, PostgreSQL")
       <->
skills_embedding ("Python, FastAPI, PostgreSQL, Docker")
```

Both vectors are dense with skill vocabulary. The comparison is "apples to apples" — required skills vs member skills with no dilution from resume narrative. A member who actually has those skills scores much higher on this specific comparison.

Similarly, `jd_level_vector ("Job level: Backend Engineer") <-> resume_embedding` measures career-level alignment specifically — did this person's career trajectory match the seniority level required? This is far more precise than comparing "Job level" text to a blended embedding that includes skills and certs.

---

## 9. Proposed SQL Query

**Replaces lines 102-125 in `src/app/ai/utils/rag_retrieval.py`:**

```sql
SELECT
    e.team_member_id,
    COALESCE(tm.designation, '')                                          AS role,
    COALESCE(e.skills_text, '')                                           AS skills,
    COALESCE(e.certifications_text, '')                                   AS certifications_text,
    tm.experience_in_months,
    COALESCE(tm.base_location, '')                                        AS base_location,
    COALESCE(CAST(tm.work_type AS text), 'hybrid')                        AS work_type,

    -- Primary full-JD distance (used for ORDER BY)
    e.embedding <-> CAST(:full_jd_vector AS vector)
                                                                          AS full_jd_distance,

    -- Role/level alignment: jd_level_vector vs resume
    COALESCE(e.resume_embedding, e.embedding)
        <-> CAST(:jd_level_vector AS vector)                              AS level_distance,

    -- Required skills vs member skills
    COALESCE(e.skills_embedding, e.embedding)
        <-> CAST(:mandatory_vector AS vector)                             AS mandatory_skills_distance,

    -- Preferred skills vs member skills (same column, different JD vector)
    COALESCE(e.skills_embedding, e.embedding)
        <-> CAST(:preferred_vector AS vector)                             AS preferred_skills_distance,

    -- Certifications alignment
    COALESCE(e.certifications_embedding, e.embedding)
        <-> CAST(:cert_vector AS vector)                                  AS cert_distance,

    -- BM25 keyword score
    ts_rank(
        to_tsvector('english',
            coalesce(e.skills_text, '') || ' ' ||
            coalesce(e.certifications_text, '') || ' ' ||
            coalesce(e.profile_text, '')
        ),
        websearch_to_tsquery('english', :kw_query)
    )                                                                     AS keyword_score

FROM team_member_embeddings e
LEFT JOIN team_member tm ON tm.team_member_id = e.team_member_id
WHERE {filters}
ORDER BY full_jd_distance ASC
LIMIT :sql_limit
```

**SQL parameters dict (replaces line 65):**

```python
def _to_list(vec):
    return vec.tolist() if isinstance(vec, np.ndarray) else vec

full_jd_vec   = _to_list(embedding_result.full_jd_vector)
jd_level_vec  = _to_list(embedding_result.jd_level_vector)          or full_jd_vec
mandatory_vec = _to_list(embedding_result.mandatory_vector)          or full_jd_vec
preferred_vec = _to_list(embedding_result.preferred_vector)          or full_jd_vec
cert_vec      = _to_list(embedding_result.certification_vector)      or full_jd_vec

params = {
    "full_jd_vector":   full_jd_vec,
    "jd_level_vector":  jd_level_vec,
    "mandatory_vector": mandatory_vec,
    "preferred_vector": preferred_vec,
    "cert_vector":      cert_vec,
    "kw_query":         keyword_query_str,
    "sql_limit":        settings.rag_sql_limit,
}
```

The `or full_jd_vec` fallback on each derived vector handles Node 3 failures gracefully — missing vectors degrade to current single-vector behavior rather than crashing.

---

## 10. Proposed Scoring Formula Changes

### Row unpacking — 13 columns (was 9)

```python
# Old (9 columns):
(team_member_id, role, skills_text, certifications_text,
 experience_in_months, base_location, work_type,
 distance, keyword_score) = row

# New (13 columns):
(team_member_id, role, skills_text, certifications_text,
 experience_in_months, base_location, work_type,
 full_jd_distance, level_distance,
 mandatory_skills_distance, preferred_skills_distance,
 cert_distance, keyword_score) = row
```

### Distance to similarity conversion

```python
def _dist_to_sim(d):
    """L2 distance → 0-1 similarity (same formula as before, now applied to each vector)."""
    return 1.0 / (1.0 + float(d)) if d is not None else 0.0

full_jd_sim       = _dist_to_sim(full_jd_distance)
level_sim         = _dist_to_sim(level_distance)
mandatory_vec_sim = _dist_to_sim(mandatory_skills_distance)
preferred_vec_sim = _dist_to_sim(preferred_skills_distance)
cert_vec_sim      = _dist_to_sim(cert_distance)
```

### Multi-vector composite (replaces single semantic_fit)

```python
# Old:
semantic_fit = 1.0 / (1.0 + float(distance))   # one value

# New: weighted composite of all 4 vector similarities
multi_vec_semantic = (
    full_jd_sim       * settings.rag_weight_full_jd +           # 0.30
    level_sim         * settings.rag_weight_level +             # 0.40
    mandatory_vec_sim * settings.rag_weight_skills_mandatory +  # 0.20
    preferred_vec_sim * settings.rag_weight_skills_preferred    # 0.10
)
# Weights sum to 1.0
```

### total_score — weights now from settings

```python
# Old (hardcoded):
weights = {"semantic": 0.30, "keyword": 0.20, ...}
total_score = semantic_fit * 0.30 + kw_norm * 0.20 + ...

# New (settings-driven for semantic/keyword split):
combined_budget = 0.50   # semantic (0.30) + keyword (0.20) unchanged budget
vec_w = combined_budget * settings.hybrid_ratio_vector   # 0.15 (default 0.3 ratio)
kw_w  = combined_budget * settings.hybrid_ratio_bm25    # 0.35 (default 0.7 ratio)

total_score = (
    multi_vec_semantic * vec_w +           # 0.15 — vector portion
    kw_norm            * kw_w  +           # 0.35 — BM25 portion
    m_score            * 0.30  +           # mandatory keyword text match (unchanged)
    p_score            * 0.05  +           # preferred keyword text match (unchanged)
    experience_relevance * 0.05 +
    c_score            * 0.05  +
    (1.0 if location_comp else 0.0) * 0.025 +
    (1.0 if mode_comp else 0.0)     * 0.025
)
# Total: 0.15 + 0.35 + 0.30 + 0.05 + 0.05 + 0.05 + 0.025 + 0.025 = 1.0
```

### New phase0_score_breakdown fields (additive — no existing key removed)

```python
# 5 new keys added to the existing 10:
"full_jd_vector_sim":          round(full_jd_sim, 4),
"level_vector_sim":            round(level_sim, 4),
"mandatory_skills_vector_sim": round(mandatory_vec_sim, 4),
"preferred_skills_vector_sim": round(preferred_vec_sim, 4),
"cert_vector_sim":             round(cert_vec_sim, 4),
```

These appear in the API response under `detailed_breakdown.phase0_ledger` for each candidate.

### Final filter — from settings

```python
# Old (hardcoded):
final_candidates = [c for c in candidates if c.final_similarity > 0.40]
return final_candidates[:40]

# New (settings-driven):
threshold = settings.rag_similarity_threshold         # 0.40 default
final_candidates = [c for c in candidates if c.final_similarity > threshold]
final_candidates.sort(key=lambda x: x.final_similarity, reverse=True)
return final_candidates[:settings.rag_final_candidates]  # 40 default
```

---

## 11. jd_level_similarity — The Most Important Change

### What it is

`jd_level_similarity` is the one RAG field that directly affects scoring in Node 5. In `src/app/ai/utils/scoring.py` line 345:

```python
s_score = rag_candidate.jd_level_similarity
```

`s_score` is used for:
1. **Semantic gate (Stage 1):** `if s_score < gates["min_semantic"]` → DISQUALIFIED
2. **Semantic weight (Stage 2):** `s_score * role_weights["semantic"]` → contributes 25% to `match_score`

### Current value (wrong)

```python
jd_level_similarity = round(semantic_fit, 4)
# semantic_fit = 1 / (1 + distance)
# distance = full_jd_vector <-> e.embedding
```

This is the same number as `semantic_fit`. The `jd_level_vector` is never used. The signal being fed to Node 5 as "semantic/role alignment" is actually "how close is the full JD text blob to the member's blended profile blob" — a noisy, general similarity.

### New value (correct)

```python
# When rag_use_level_vector = True (default):
jd_level_similarity = round(level_sim, 4)
# level_sim = 1 / (1 + level_distance)
# level_distance = jd_level_vector <-> COALESCE(resume_embedding, e.embedding)
```

This specifically measures: "Does this person's resume/career history align with the stated job level and role category?"

The `jd_level_vector` embeds a short, precise string like `"Job level: Backend Engineer"`. The `resume_embedding` captures the member's career narrative. The similarity between them directly answers the seniority alignment question.

### Feature flag for safe rollback

```python
# In settings.py:
rag_use_level_vector: bool = True

# In code:
jd_level_sim_value = level_sim if settings.rag_use_level_vector else full_jd_sim
```

Setting `RAG_USE_LEVEL_VECTOR=false` in `.env` instantly reverts to old behavior without a code deploy.

---

## 12. Downstream Impact on Node 5

No changes needed in `matching_scoring.py` or `scoring.py`. The field names are preserved.

| Field flowing from Node 4 | Before | After | Effect |
|---|---|---|---|
| `jd_level_similarity` | `1/(1+full_jd_dist)` | `1/(1+level_dist)` | `s_score` in scoring.py measures role alignment instead of blob proximity |
| `phase0_score_breakdown` | 10 keys | 15 keys | Richer audit trail; `matching_scoring.py` passes it through without reading individual keys |
| Candidate count | ≤ 10 (LIMIT bug) | up to 40 | More candidates scored by Node 5; recall improves |
| `final_similarity` | single-vector | multi-vector | Discarded in Node 5 anyway — only used for RAG pre-filter |
| `mandatory_similarity` | text match ratio | text match ratio (unchanged) | Not changed — Node 5 recomputes mandatory match from skill IDs anyway |

---

## 13. New Settings Required

Add to `src/app/settings.py` after `rag_similarity_threshold`:

```python
# Change default from 0.5 to 0.40 (preserve existing behavior)
rag_similarity_threshold: float = 0.40

# RAG retrieval pool sizes
rag_sql_limit: int = 100            # SQL LIMIT — fixes LIMIT 10 bug
rag_final_candidates: int = 40      # cap on candidates passed to Node 5

# Multi-vector composite weights (must sum to 1.0)
rag_weight_full_jd: float = 0.30
rag_weight_level: float = 0.40
rag_weight_skills_mandatory: float = 0.20
rag_weight_skills_preferred: float = 0.10

# Feature flag — set False in .env to revert jd_level_similarity to old behavior
rag_use_level_vector: bool = True
```

All existing settings (`hybrid_ratio_bm25`, `hybrid_ratio_vector`, `rag_similarity_threshold`) are already present and will now be consumed.

---

## 14. Files to Change

| File | Change Type | Summary |
|---|---|---|
| `src/app/settings.py` | Additive | Add 7 new settings fields; change `rag_similarity_threshold` default from 0.5 → 0.40 |
| `src/app/ai/utils/rag_retrieval.py` | Rewrite | New SQL (5 vectors), updated row unpacking (13 cols), new scoring formula, settings-driven threshold/limit |
| `src/app/ai/agents/rag_retrieval.py` | 1-line | Log message only — no functional change needed |

**No changes to:**
- `src/app/ai/state.py` — `retrieved_candidates: Optional[List[Dict]]` already handles any dict shape
- `src/app/ai/agents/matching_scoring.py` — reads same field names
- `src/app/ai/utils/scoring.py` — reads same `jd_level_similarity` field
- `src/app/ai/agents/embedding.py` — all 5 vectors already produced
- Cron pipeline — all 4 member vectors already stored

---

## 15. Risk and Rollback

| Change | Risk Level | Rollback |
|---|---|---|
| LIMIT 10 → 100 | Low | Set `RAG_SQL_LIMIT=10` in `.env` |
| 5-vector SQL with COALESCE | Low | Legacy NULL members fall back to `e.embedding` automatically |
| `jd_level_similarity` source | Medium — shifts `s_score` | Set `RAG_USE_LEVEL_VECTOR=false` in `.env` |
| Threshold 0.5 → 0.40 default | None — preserves existing behavior | Already at 0.40 effectively (hardcoded) |
| Weights from settings | Low | Adjust `HYBRID_RATIO_VECTOR` / `HYBRID_RATIO_BM25` in `.env` |

---

## 16. Verification Checklist

After implementation, verify:

1. **LIMIT fix**: A broad requisition returns more than 10 candidates in the response.

2. **Multi-vector active**: In `detailed_breakdown.phase0_ledger` for any candidate, all 5 keys must exist:
   - `full_jd_vector_sim`
   - `level_vector_sim`
   - `mandatory_skills_vector_sim`
   - `preferred_skills_vector_sim`
   - `cert_vector_sim`

3. **jd_level_similarity correct**: `jd_level_similarity` for a candidate must equal `level_vector_sim` in `phase0_ledger` (not `full_jd_vector_sim`).

4. **Feature flag works**: Set `RAG_USE_LEVEL_VECTOR=false` → `jd_level_similarity` must equal `full_jd_vector_sim`.

5. **No regression**: For a known clear-match requisition, the expected top candidate still appears in the top 3.

6. **Unit test**: `_build_structured_candidate` with a 13-column row unpacks without `IndexError`.
