# Hybrid Search & Scoring — Rollout Plan

> Aligned with HYBRID_SEARCH_AND_SCORING_SPEC.docx v6.0.
> Items 1 and 2 complete (incl. post-implementation filter improvements). Item 3 complete (incl. Addendums 1–5).
> Items 7–9 complete (normalization, output enrichment, availability scoring, infrastructure).
> Item 4 (AI context enrichment) is next — unblocked. Cross-encoder renumbered to Item 5.

---

## Status

| # | Item | Status |
|---|------|--------|
| 1 | skill_ontology synonym expansion | ✅ Done |
| 2 | True Hybrid Search — pg_bm25 + RRF | ✅ Done (incl. filter improvements) |
| 3 | Per-skill rating & experience in scoring | ✅ Done (incl. Addendums 1–5) |
| 4 | AI candidate context enrichment | Next up (unblocked — see plan) |
| 5 | Cross-encoder reranker | Unblocked (requires Item 2 — done) |
| 6 | RAG weight validation | Low priority — see note |
| 7 | Skill normalization improvements | ✅ Done |
| 8 | API schema testing overrides | ✅ Done |
| 9 | Infrastructure & settings centralization | ✅ Done |

---

## 1. ✅ skill_ontology Synonym Expansion (DONE)

Completed in commit d844d56. Mandatory and preferred skill names from the JD parser are expanded
through `skill_ontology.enriched_terms` before being used in the BM25 keyword query. A JD with
"ReactJS" now matches a candidate who wrote "React.js".

---

## 2. ✅ True Hybrid Search — pg_bm25 + RRF (DONE)

**Original plan:** `hybrid-search-pg-bm25-plan.md`

**Replaces old Items 2 and 3** from the original plan. Both the Python `rank_bm25` windowed
approach (old Item 2) and the full-corpus A/B flag (old Item 3) are superseded by this
implementation, which delivers full-corpus true BM25 natively in the database.

### Why old Items 2 and 3 are removed

| Old item | What it proposed | Why superseded |
|---|---|---|
| Old Item 2 | Python `rank_bm25` over 100-row SQL result | Windowed BM25 — IDF computed over 100 rows, not full corpus. Boolean tsvector pre-filter still determined who entered the pool. Not true BM25 retrieval. |
| Old Item 3 | Full-corpus A/B flag — fetch all 1,500 rows, Python BM25 | pg_bm25 already computes IDF over the full corpus at index time. No A/B flag, no Python-side corpus, no memory overhead from fetching all members. |

### What was implemented

**Infrastructure:**
- Docker image: `paradedb/paradedb:latest` (PostgreSQL 18 with pg_search + pgvector bundled)
- Alembic migration `20260519_01`: `CREATE EXTENSION pg_search` + `CREATE INDEX idx_tme_bm25 ON team_member_embeddings USING bm25 (id, skills_text, certifications_text, profile_text) WITH (key_field='id')`
- Index covers all three text columns; IDF is computed over the full ~1,500-member corpus at index time

**Two independent retrieval paths (SQL #1 and SQL #2):**

```
SQL #1 (semantic):
  Pure composite vector retrieval — no keyword gate in WHERE clause
  ORDER BY weighted composite of 5 vector distances:
    full_jd × 0.25 + level × 0.35 + mandatory × 0.20 + preferred × 0.10 + cert × 0.10
  BM25 score attached via LEFT JOIN subquery (col 14) — does not affect retrieval order
  LIMIT 100

SQL #2 (keyword):
  WHERE e @@@ paradedb.parse(:bm25_query)   ← true pg_bm25, full-corpus IDF
  ORDER BY paradedb.score(e.id) DESC
  LIMIT 100 (matches semantic pool size)
  All 5 vector distances also computed in SELECT for fair scoring of keyword-only candidates
```

**Merge:**
- `_merge_result_sets()` deduplicates by `team_member_id`; semantic rows take priority for duplicates
- Keyword-only candidates appended after all semantic candidates

**Phase 0 ranking — Reciprocal Rank Fusion (RRF):**

Replaces the old `_compute_total_score()` weighted formula. RRF uses rank position only —
no scale mismatch between BM25 scores and vector distances:

```
k = 60  (standard constant)
RRF_score(candidate) = Σ  1 / (k + rank_in_path)
                      each path the candidate appears in

Candidates in BOTH paths receive scores from both paths added together — explicit rank-additive
advantage over candidates appearing in only one path.
```

**What Phase 0 passes to Node 5 (unchanged):**
- `mandatory_similarity`, `preferred_similarity`, `certification_similarity` — text match ratios, computed in Phase 0, used by Node 5 scorer
- `jd_level_similarity`, `full_jd_similarity` — vector similarities, used by Node 5 `s_score`
- `profile_text` — used by cross-encoder reranker (Item 5)
- `phase0_score_breakdown` — audit ledger containing RRF score, semantic rank, BM25 rank, vector sims, text match scores

**What Phase 0 no longer computes:**
- `experience_relevance`, `location_comp`, `mode_comp` in ranking — Node 5 (`scoring.py`) computes these independently from raw profile data. Removed from Phase 0's ranking formula entirely.
- Arbitrary BM25 weight (0.35) and vector weight (0.15) in scoring formula — replaced by RRF.
- 0.6× mandatory penalty in retrieval — removed; Node 5 owns qualification logic.

**Business constraint filters (location, work_mode, experience):**
Active in both SQL paths via the shared `filters` list. Defensive guard logic prevents bad JD
input from producing zero-result queries:
- Location: virtual/work-mode terms (`"Remote"`, `"WFH"`, `"Anywhere"`, etc.) are stripped before
  the filter is built. If all entries are virtual, the location filter is skipped entirely.
- Work mode: unknown values (e.g. `"Flexible"`, `"Onsite"`) are silently dropped via an alias
  map. If all entries are unmappable, no work_mode filter is added.
- Experience: out-of-range values (negative or > 600 months), `min_months=0`, and inverted ranges
  (`min > max`) are repaired or discarded rather than generating a nonsensical WHERE clause.

### Files changed

| File | Change |
|---|---|
| `docker-compose.yml` | Image → `paradedb/paradedb:latest`; volume → `/var/lib/postgresql` |
| `alembic/versions/20260519_01_add_pg_bm25_index.py` | New migration: pg_search extension + BM25 index |
| `src/app/settings.py` | Added `rag_keyword_fetch_limit: int = 100` |
| `src/app/ai/utils/rag_retrieval.py` | Full rewrite of retrieval + ranking logic (see above) |
| `Makefile` | Added `db-dump` and `db-reset` targets for team DB sync |

### Acceptance criteria

- `alembic_version` = `20260519_01`; `\di idx_tme_bm25` shows index on `team_member_embeddings`
- Logs show `RAG SQL (semantic)` row count + `RAG SQL (keyword/pg_bm25)` row count + `keyword-only=N`
- `phase0_score_breakdown` contains `rrf_score`, `semantic_rank`, `bm25_rank` keys
- `RAGCandidate.profile_text` is non-empty for candidates with profile data
- Empty keyword edge case (no mandatory/preferred/cert skills): only SQL #1 runs, all `bm25_score = 0.0`, no crash
- A candidate appearing in both paths ranks above an equal-quality candidate appearing in only one path

---

## 3. ✅ Per-Skill Rating & Experience in Scoring (DONE)

**Full plan:** `per-skill-scoring-plan.md`

`_calculate_skill_group_score()` previously gave every matched skill a flat contribution of 1.0
regardless of `rating` or `experience_in_months`. Both fields exist in `TeamMemberSkill`.

### What was implemented

- `_skill_contribution()` helper: blends `rating/5.0` (weight 0.6) and `min(exp_months/48, 1.0)` (weight 0.4) into a single 0–1 scalar. `None` fields default to 0.5 (neutral).
- `_calculate_skill_group_score()`: ID-matched skills use the blended contribution; profile-text-only matches use `settings.profile_text_match_weight` (0.6).
- **Addendum 1 (cert expiry):** `_calculate_certification_score()` now accepts `cert_validity` dict; expired certs move to `expired` list and count as missing for score. Exposed in `match_reasons.certification_expired`.
- **Addendum 2 (dynamic context weighting):** `_calculate_context_boost()` now only includes criteria the JD actually constrains in both numerator and denominator. Non-constraining criteria (e.g. remote-only location, flexible work mode, no required certs) are excluded so their weight doesn't inflate everyone's context score identically.

### Acceptance criteria

- Two candidates with the same skill but different ratings produce different `mandatory_score`
- Profile-text-only matches receive `profile_text_match_weight`, not 1.0
- Expired certs appear in `certification_expired`, not `certification_matched`
- Remote-only JD: location criterion excluded from context score denominator

---

## 4. AI Candidate Context Enrichment

**Status:** Unblocked — Item 3 and Addendum 1 are complete.
**Full plan:** `ai-context-enrichment-plan.md`

Appends a structured candidate data block (designation, total experience, per-skill ratings +
experience months, active certifications) to `profile_text` before calling `get_ai_fit_confidence()`.
Eliminates the AI ↔ DB contradiction where the LLM contradicts `mandatory_matched` because it
only sees prose, not the structured ratings that explain why `mandatory_score` is low.

No new DB queries — reuses `skill_records` (Item 3) and `cert_records` (Addendum 1).

### Acceptance criteria

- `ai_reasoning` no longer contradicts `mandatory_matched` for candidates with low-rated skills
- Expired certifications do not appear in the structured block sent to the LLM
- Candidates with no skills or no certs produce valid context strings without errors
- No additional DB queries introduced

---

## 5. Cross-Encoder Reranker

**Prerequisite:** `RAGCandidate.profile_text` populated — confirmed done by Item 2.

### Files to change

- `src/app/ai/utils/reranker.py` (new file): loads `BAAI/bge-reranker-v2-m3` via `CrossEncoder`
  from `sentence-transformers`; exposes `rerank(jd_text, candidates)` that builds
  `(jd_text, candidate.profile_text)` pairs and returns candidates re-sorted by score
- `requirements.txt`: add `sentence-transformers`
- `src/app/settings.py`: add `use_cross_encoder_reranker: bool = False` and
  `cross_encoder_model_name: str = "BAAI/bge-reranker-v2-m3"`
- `src/app/ai/utils/rag_retrieval.py`: call `reranker.rerank()` after the top-40 are selected,
  gated on `settings.use_cross_encoder_reranker`

### Acceptance criteria

- When flag is `False`: order identical to RRF composite (no regression)
- When flag is `True`: top-40 re-sorted by cross-encoder score; RRF scores remain in
  `phase0_score_breakdown` for audit
- 40-candidate rerank < 500 ms on CPU at p95

---

## 6. RAG Weight Validation

*(Priority reduced after RRF adoption.)*

With RRF as the Phase 0 ranking mechanism, `rag_weight_*` values only influence which
100 candidates enter SQL #1's semantic pool (via the composite ORDER BY). They no longer
affect how candidates are ranked within the merged pool. SQL #2 (BM25 path) also provides
a safety net for candidates displaced by weight miscalibration.

### Files to add

- `scripts/eval_rag_weights.py`: fetches stored requisitions with feedback; scores candidate
  pools under 5 weight configurations; computes NDCG@10 and MRR; outputs comparison table

### Acceptance criteria

- If current weights are not in top-2 configurations, update `rag_weight_*` defaults in
  `settings.py` with the winning configuration

---

## 7. ✅ Skill Normalization Improvements (DONE)

**Plan details:** `per-skill-scoring-plan.md` (Addendum 4, output enrichment); `hybrid-search-pg-bm25-plan.md` (filter improvements).

### A. Direct skill-ID bypass ("Blocker-2 fix")

When the API caller already knows the `skill_master` UUIDs (e.g. an integration test or a pre-resolved request), the LLM normalization step (Node 2) can be skipped entirely by providing:

```json
"job_description": {
    "mandatory_skill_ids": ["uuid-1", "uuid-2"],
    "preferred_skill_ids": ["uuid-3"]
}
```

Node 2 detects these fields, builds the `alternatives` map directly from the DB (one query, no LLM call), and returns. This eliminates name→ID mapping uncertainty in testing.

### B. Raw name fallback in fuzzy matching

Previously, if the LLM expanded "JPA" to "Java Persistence API" and the DB stored the skill as "JPA", the direct match failed and fuzzy match was attempted on the expanded form — also failing. Now a second attempt uses the original raw JD name before falling through to fuzzy:

```
canonical match → raw name direct match → fuzzy on canonical → fuzzy on raw name
```

### C. Fuzzy match deduplication

`fuzzy_ids` are filtered against the already-collected `skill_group` before being appended, preventing duplicate skill IDs in the alternatives map.

### Files Changed

| File | Change |
|---|---|
| `src/app/ai/agents/skill_normalization.py` | Direct ID bypass block; raw name fallback; fuzzy dedup |
| `src/app/api/schemas/requisition.py` | Add `mandatory_skill_ids`, `preferred_skill_ids`, `target_member_ids` to `JobDescription` |
| `src/app/api/routers/jd_skill_mapping.py` | Promote `target_member_ids` to top-level graph state |

---

## 8. ✅ API Schema Testing Overrides (DONE)

Three optional fields added to `JobDescription` for exact-match testing and controlled integration testing:

| Field | Type | Purpose |
|---|---|---|
| `mandatory_skill_ids` | `Optional[List[str]]` | Pre-resolved UUIDs; skips LLM normalization in Node 2 |
| `preferred_skill_ids` | `Optional[List[str]]` | Same as above for preferred skills |
| `target_member_ids` | `Optional[List[str]]` | Candidate UUIDs that must appear in the scoring pool |

`target_member_ids` is promoted to top-level graph state in `process_requisition_with_graph()` so Node 4 can read it directly without re-parsing the JD payload.

### Acceptance criteria

- Request with `mandatory_skill_ids` set: logs show "Skill normalization bypassed via direct IDs"; no LLM call in Node 2
- Request with `target_member_ids`: those candidates appear in the final result set regardless of RRF rank
- All three fields default to `None`; existing requests without them are unaffected

---

## 9. ✅ Infrastructure & Settings Centralization (DONE)

Small cross-cutting improvements that remove hardcoded values and `os.getenv()` calls in favor of the Settings class.

### Changes

| Module | Old | New |
|---|---|---|
| `llm_client.py` | `max_retries = 5`, `base_delay = 2.0` hardcoded; `os.getenv()` API key fallback | Read from `settings.llm_max_retries`, `settings.llm_retry_base_delay`; API keys read from settings only |
| `ranking.py` | `float(os.getenv("FIT_SCORE_THRESHOLD", "0.5"))` | `settings.fit_score_threshold` |
| `result_aggregation.py` | Float values not rounded in output | `_round_floats()` recursive helper applied to all result entries (rounds to 2 decimal places) |
| `result_aggregation.py` | `base_agentic_score` not surfaced | Added to result entry so it is visible in API response alongside `ai_confidence_score` |

### New settings fields

```python
# settings.py
llm_max_retries: int = 5
llm_retry_base_delay: float = 2.0
```

`fit_score_threshold` was already a settings field; `os.getenv()` in `ranking.py` was redundant.

### Files Changed

| File | Change |
|---|---|
| `src/app/ai/utils/llm_client.py` | Remove `os.getenv()` fallbacks; read retry params from settings |
| `src/app/ai/utils/ranking.py` | Read `fit_score_threshold` from settings; remove `os` import |
| `src/app/ai/agents/result_aggregation.py` | Add `_round_floats()` helper; apply to result entries; expose `base_agentic_score` |
| `src/app/settings.py` | Add `llm_max_retries`, `llm_retry_base_delay` |

---

## Rollout Order Rationale

Items 1–3 are complete. Item 4 (AI context enrichment) is the next correctness fix — its
prerequisites are now live, so it is immediately unblocked. Item 5 (cross-encoder) is a quality
improvement that can run after Item 4 or in parallel. Item 6 (RAG weight validation) is a
low-priority audit checkpoint — run only if retrieval quality concerns arise after Items 4–5 are live.
