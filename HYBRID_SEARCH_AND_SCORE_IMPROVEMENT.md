# Hybrid Search & Scoring — Rollout Plan

> Aligned with HYBRID_SEARCH_AND_SCORING_SPEC.docx v6.0.
> Items 1–14 complete. Items 15–17 pending (kept at end).
> Items marked *(unplanned)* were not in the original spec but were implemented in the same period.

---

## Status

| # | Item | Planned | Status | Date |
|---|------|---------|--------|------|
| 1 | Seniority level inference in JD parsing | No | ✅ Done | May 11 |
| 2 | `rag_signals` exposed in API response | No | ✅ Done | May 11 |
| 3 | Infrastructure fixes (logger silencing, alembic `.env` loading) | No | ✅ Done | May 13 |
| 4 | skill_ontology synonym expansion | Yes | ✅ Done | May 19 |
| 5 | True Hybrid Search — pg_bm25 + RRF | Yes | ✅ Done | May 26 |
| 6 | Per-skill rating & experience in scoring | Yes | ✅ Done | May 26 |
| 7 | Test infrastructure (RAG script + Postman scenarios) | No | ✅ Done | Jun 1 |
| 8 | Skill normalization improvements | Yes | ✅ Done | Jun 1 |
| 9 | API schema testing overrides | Yes | ✅ Done | Jun 1 |
| 10 | Infrastructure & settings centralization | Yes | ✅ Done | Jun 1 |
| 11 | Vector distance metric: L2 → Cosine similarity | No | ✅ Done | Jun 4 |
| 12 | Scoring correctness bug fixes | No | ✅ Done | Jun 4 |
| 13 | `role_ontology` DB table | No | ✅ Done | Jun 8 |
| 14 | `skill_config` table: skill family & group config moved to DB | No | ✅ Done | Jun 8 |
| 15 | AI candidate context enrichment | Yes | Next up (unblocked) | — |
| 16 | Cross-encoder reranker | Yes | Unblocked (requires Item 5 — done) | — |
| 17 | RAG weight validation | Yes | Low priority | — |

---

## 1. ✅ Seniority Level Inference in JD Parsing *(unplanned)*

**Commit:** `ae8a0360` — May 11

`requisition_parsing.py` previously relied entirely on the LLM to infer the seniority level.
If the LLM omitted or hallucinated the field, the wrong weight profile was applied in scoring.

A 4-layer deterministic fallback is now applied after the LLM response:

```
LLM output → title keyword match → experience threshold → default MID
```

Title keywords (`senior`, `sr.`, `lead`, `principal`, `architect`, …) and experience thresholds
(≥ 60 months → SENIOR; ≤ 12 months → JUNIOR) are checked in order. `_resolve_level()` is the
single entry point; `_infer_level_from_title()` and `_infer_level_from_experience()` are the
two fallback helpers. The LLM prompt is also updated to explicitly request a `level` field and
document the inference rules.

### Files changed

| File | Change |
|---|---|
| `src/app/ai/agents/requisition_parsing.py` | `_resolve_level()`, `_infer_level_from_title()`, `_infer_level_from_experience()` helpers; updated prompt |
| `src/app/ai/agents/embedding.py` | `jd_level_vector` text fix |
| `src/app/ai/utils/embedding.py` | Embedding utility cleanup |
| `docs/jd-parsing-robustness-improvement.md` | Design doc for this change |

---

## 2. ✅ `rag_signals` Exposed in API Response *(unplanned)*

**Commit:** `33c1fdee` — May 11

A new `rag_signals` dict is added to each candidate entry in the scoring response, surfacing the
six raw RAG similarity values that were previously only visible in internal logs.

```json
"rag_signals": {
    "final_similarity":    0.8421,
    "full_jd_similarity":  0.7903,
    "jd_level_similarity": 0.8112,
    "mandatory_rag_sim":   0.8834,
    "preferred_rag_sim":   0.7651,
    "cert_rag_sim":        0.6203
}
```

### Files changed

| File | Change |
|---|---|
| `src/app/ai/agents/matching_scoring.py` | Add `rag_signals` dict to result entry |
| `src/app/ai/utils/models.py` | Add `full_jd_similarity` field to `RAGCandidate` |

---

## 3. ✅ Infrastructure Fixes *(unplanned)*

**Commits:** `b744b42`, `5f6c270` — May 13

| Commit | File | Change |
|---|---|---|
| `b744b42` | `src/app/logging_config.py` | Silence noisy third-party loggers (`httpx`, `httpcore`, `openai`, `anthropic`, `hpack`) that were flooding structured logs |
| `5f6c270` | `alembic/env.py` | Load `.env` at Alembic startup so `DATABASE_URL` is available during migrations without requiring it to be exported in the shell |

---

## 4. ✅ skill_ontology Synonym Expansion

**Commit:** `d844d56` — May 19

Mandatory and preferred skill names from the JD parser are expanded through
`skill_ontology.enriched_terms` before being used in the BM25 keyword query. A JD with
"ReactJS" now matches a candidate who wrote "React.js".

---

## 5. ✅ True Hybrid Search — pg_bm25 + RRF

**Commits:** `857cbbd`, `3d0da340` — May 26 / Jun 1

**Original plan:** `hybrid-search-pg-bm25-plan.md`

Replaces the old Python `rank_bm25` windowed approach and the full-corpus A/B flag with true
full-corpus BM25 natively in the database.

### Infrastructure

- Docker image: `paradedb/paradedb:latest` (PostgreSQL 18 with pg_search + pgvector bundled)
- Alembic migration `20260519_01`: `CREATE EXTENSION pg_search` + BM25 index on `team_member_embeddings` covering `skills_text`, `certifications_text`, `profile_text`

### Two independent retrieval paths

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
  LIMIT 100
  All 5 vector distances also computed in SELECT for fair scoring of keyword-only candidates
```

### Merge & RRF ranking

`_merge_result_sets()` deduplicates by `team_member_id`; semantic rows take priority for
duplicates. Keyword-only candidates are appended after all semantic candidates.

```
k = 60  (standard constant)
RRF_score(candidate) = Σ  1 / (k + rank_in_path)
                      each path the candidate appears in
```

Candidates in both paths receive scores from both paths — explicit rank-additive advantage.

### Business constraint filters

Active in both SQL paths via the shared `filters` list, with defensive guard logic:
- Location: virtual/WFH terms stripped; filter skipped if all entries are virtual
- Work mode: unknown values silently dropped; no filter added if all are unmappable
- Experience: out-of-range values, `min_months=0`, and inverted ranges repaired or discarded

### Files changed

| File | Change |
|---|---|
| `docker-compose.yml` | Image → `paradedb/paradedb:latest`; volume → `/var/lib/postgresql` |
| `alembic/versions/20260519_01_add_pg_bm25_index.py` | New migration: pg_search extension + BM25 index |
| `src/app/settings.py` | Added `rag_keyword_fetch_limit: int = 100` |
| `src/app/ai/utils/rag_retrieval.py` | Full rewrite of retrieval + ranking logic |
| `Makefile` | Added `db-dump` and `db-reset` targets for team DB sync |

### Acceptance criteria

- `alembic_version` = `20260519_01`; `\di idx_tme_bm25` shows index on `team_member_embeddings`
- Logs show `RAG SQL (semantic)` row count + `RAG SQL (keyword/pg_bm25)` row count + `keyword-only=N`
- `phase0_score_breakdown` contains `rrf_score`, `semantic_rank`, `bm25_rank` keys
- `RAGCandidate.profile_text` is non-empty for candidates with profile data
- Empty keyword edge case: only SQL #1 runs, all `bm25_score = 0.0`, no crash
- A candidate appearing in both paths ranks above an equal-quality candidate appearing in only one path

---

## 6. ✅ Per-Skill Rating & Experience in Scoring

**Commits:** `f3028b0`, `31213c4` — May 26 / Jun 1

**Full plan:** `per-skill-scoring-plan.md`

`_calculate_skill_group_score()` previously gave every matched skill a flat contribution of 1.0
regardless of `rating` or `experience_in_months`.

### What was implemented

- `_skill_contribution()` helper: blends `rating/5.0` (weight 0.6) and `min(exp_months/48, 1.0)` (weight 0.4). `None` fields default to 0.5 (neutral).
- `_calculate_skill_group_score()`: ID-matched skills use the blended contribution; profile-text-only matches use `settings.profile_text_match_weight` (0.6).
- **Addendum 1 (cert expiry):** `_calculate_certification_score()` accepts `cert_validity` dict; expired certs move to `expired` list and count as missing. Exposed in `match_reasons.certification_expired`.
- **Addendum 2 (dynamic context weighting):** `_calculate_context_boost()` only includes criteria the JD actually constrains — non-constraining criteria are excluded so their weight doesn't inflate everyone's context score identically.

### Acceptance criteria

- Two candidates with the same skill but different ratings produce different `mandatory_score`
- Profile-text-only matches receive `profile_text_match_weight`, not 1.0
- Expired certs appear in `certification_expired`, not `certification_matched`
- Remote-only JD: location criterion excluded from context score denominator

---

## 7. ✅ Test Infrastructure *(unplanned)*

**Commits:** `f388ca2`, `50597557` — Jun 1

| Artifact | Purpose |
|---|---|
| `tests/check_rag_retrieval.py` | Manual end-to-end RAG retrieval verification script — runs both SQL paths against a live DB and prints ranked output with RRF breakdown |
| `tests/postman/query.sql` | Ad-hoc SQL query for Postman/pgAdmin inspection |
| `tests/postman/candidate_*_match_scenarios.json` (×12) | Per-candidate Postman test scenario collections based on real candidate data |

---

## 8. ✅ Skill Normalization Improvements

**Commit:** `901055536` — Jun 1

**Plan details:** `per-skill-scoring-plan.md` (Addendum 4); `hybrid-search-pg-bm25-plan.md` (filter improvements).

### A. Direct skill-ID bypass ("Blocker-2 fix")

When the API caller already knows the `skill_master` UUIDs, the LLM normalization step (Node 2)
is skipped by providing `mandatory_skill_ids` / `preferred_skill_ids` in the request. Node 2
detects these fields, builds the `alternatives` map directly from the DB (one query, no LLM call).

### B. Raw name fallback in fuzzy matching

```
canonical match → raw name direct match → fuzzy on canonical → fuzzy on raw name
```

Prevents "JPA" expanding to "Java Persistence API" and then failing to match when the DB stores "JPA".

### C. Fuzzy match deduplication

`fuzzy_ids` are filtered against the already-collected `skill_group` before appending, preventing
duplicate skill IDs in the alternatives map.

### Files changed

| File | Change |
|---|---|
| `src/app/ai/agents/skill_normalization.py` | Direct ID bypass block; raw name fallback; fuzzy dedup |
| `src/app/api/schemas/requisition.py` | Add `mandatory_skill_ids`, `preferred_skill_ids`, `target_member_ids` to `JobDescription` |
| `src/app/api/routers/jd_skill_mapping.py` | Promote `target_member_ids` to top-level graph state |

---

## 9. ✅ API Schema Testing Overrides

**Commit:** `901055536` — Jun 1

Three optional fields added to `JobDescription` for exact-match and controlled integration testing:

| Field | Type | Purpose |
|---|---|---|
| `mandatory_skill_ids` | `Optional[List[str]]` | Pre-resolved UUIDs; skips LLM normalization in Node 2 |
| `preferred_skill_ids` | `Optional[List[str]]` | Same as above for preferred skills |
| `target_member_ids` | `Optional[List[str]]` | Candidate UUIDs that must appear in the scoring pool |

### Acceptance criteria

- Request with `mandatory_skill_ids` set: logs show "Skill normalization bypassed via direct IDs"; no LLM call in Node 2
- Request with `target_member_ids`: those candidates appear in the final result set regardless of RRF rank
- All three fields default to `None`; existing requests without them are unaffected

---

## 10. ✅ Infrastructure & Settings Centralization

**Commit:** `e5c68228` — Jun 1

| Module | Old | New |
|---|---|---|
| `llm_client.py` | `max_retries = 5`, `base_delay = 2.0` hardcoded; `os.getenv()` API key fallback | Read from `settings.llm_max_retries`, `settings.llm_retry_base_delay` |
| `ranking.py` | `float(os.getenv("FIT_SCORE_THRESHOLD", "0.5"))` | `settings.fit_score_threshold` |
| `result_aggregation.py` | Float values not rounded in output | `_round_floats()` recursive helper applied to all result entries (rounds to 2 decimal places) |
| `result_aggregation.py` | `base_agentic_score` not surfaced | Added to result entry alongside `ai_confidence_score` |

### New settings fields

```python
llm_max_retries: int = 5
llm_retry_base_delay: float = 2.0
```

### Files changed

| File | Change |
|---|---|
| `src/app/ai/utils/llm_client.py` | Remove `os.getenv()` fallbacks; read retry params from settings |
| `src/app/ai/utils/ranking.py` | Read `fit_score_threshold` from settings; remove `os` import |
| `src/app/ai/agents/result_aggregation.py` | Add `_round_floats()` helper; apply to result entries; expose `base_agentic_score` |
| `src/app/settings.py` | Add `llm_max_retries`, `llm_retry_base_delay` |

---

## 11. ✅ Vector Distance Metric: L2 → Cosine Similarity *(unplanned)*

**Commit:** `c5ff9f7` — Jun 4

All five RAG SQL distance operators changed from L2 (`<->`) to cosine (`<=>`). `_dist_to_sim`
updated from `1/(1+d)` to `1-d` to match cosine semantics (cosine distance is already in [0,1];
the old formula unnecessarily compressed the range). A dedicated Alembic migration adds
`ivfflat` cosine indexes on all embedding columns.

### Files changed

| File | Change |
|---|---|
| `src/app/ai/utils/rag_retrieval.py` | `<->` → `<=>` in both SQL paths; `_dist_to_sim` formula updated |
| `alembic/versions/20260601_01_add_cosine_index_embedding.py` | New migration: cosine IVFFlat indexes on all embedding columns |

---

## 12. ✅ Scoring Correctness Bug Fixes *(unplanned)*

**Commit:** `c5ff9f7` — Jun 4

Three silent correctness bugs found and fixed while working on the cosine similarity switch:

| Bug | Fix |
|---|---|
| `_build_candidate_context` looked up mandatory skill ratings by name but semantic hits append `" (semantic)"` to the key, causing all semantic-matched skills to show `None` proficiency | Strip `" (semantic)"` suffix before the lookup |
| `qualification_status` in `match_reasons` was set before the AI override step, so it never reflected the final overridden value | Set `qualification_status` after `is_qualified` is determined post-AI override |
| `availability_score` was computed from the wrong variable instead of the actual `availability_result` dict | Use `availability_result.get("available_capacity")` directly |

---

## 13. ✅ `role_ontology` DB Table *(unplanned)*

**Commit:** `a95e9fd` — Jun 8

New DB table `role_ontology` that mirrors `skill_ontology` but for roles. Maps a canonical role
name to an internal `profile_type` code, a list of aliases (e.g. "Software Dev" → "Software
Engineer"), and domain-specific `enriched_terms` for BM25 expansion.

### Files changed

| File | Change |
|---|---|
| `alembic/versions/20260604_01_add_role_ontology.py` | New migration: `role_ontology` table + indexes |
| `src/app/db/models/models.py` | `RoleOntology` ORM model |
| `scripts/dev/seed_role_ontology.sql` | Seed data: ~40 canonical roles |
| `scripts/dev/seed_jd_certification_requirements.sql` | Seed data: JD-level cert requirements |

---

## 14. ✅ `skill_config` Table: Skill Family & Group Config Moved to DB *(unplanned)*

**Commit:** `65a8d64` — Jun 8

Skill family keyword lists (`frontend`, `backend`, `backend_ai`) and skill groupings
(`python`, `javascript`, `sql`, `big_data`, `ai_ml`, `cloud`) were hardcoded in `settings.py`
as long comma-separated strings. Moved to a new `skill_config` DB table so they can be updated
without a redeploy.

### Files changed

| File | Change |
|---|---|
| `alembic/versions/20260608_01_add_skill_config.py` | New migration: `skill_config` table |
| `src/app/db/models/models.py` | `SkillConfig` ORM model |
| `src/app/db/repositories/skill_config.py` | New repository: loads all rows at startup, exposes `get_skill_groups()` / `get_family_keywords()` with hardcoded fallback |
| `src/app/main.py` | FastAPI `lifespan` event calls `load_skill_config(db)` on startup |
| `src/app/settings.py` | Removed `frontend_keywords`, `backend_keywords`, `backend_ai_indicators`, and all `skill_group_*` string fields |

---

## 15. AI Candidate Context Enrichment

**Status:** Unblocked — Item 6 and Addendum 1 are complete.
**Full plan:** `ai-context-enrichment-plan.md`

Appends a structured candidate data block (designation, total experience, per-skill ratings +
experience months, active certifications) to `profile_text` before calling `get_ai_fit_confidence()`.
Eliminates the AI ↔ DB contradiction where the LLM contradicts `mandatory_matched` because it
only sees prose, not the structured ratings that explain why `mandatory_score` is low.

No new DB queries — reuses `skill_records` (Item 6) and `cert_records` (Addendum 1).

### Acceptance criteria

- `ai_reasoning` no longer contradicts `mandatory_matched` for candidates with low-rated skills
- Expired certifications do not appear in the structured block sent to the LLM
- Candidates with no skills or no certs produce valid context strings without errors
- No additional DB queries introduced

---

## 16. Cross-Encoder Reranker

**Prerequisite:** `RAGCandidate.profile_text` populated — confirmed done by Item 5.

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

## 17. RAG Weight Validation

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

## Rollout Order Rationale

Items 1–14 are complete. Item 15 (AI context enrichment) is the next correctness fix — its
prerequisites are now live, so it is immediately unblocked. Item 16 (cross-encoder) is a quality
improvement that can run after Item 15 or in parallel. Item 17 (RAG weight validation) is a
low-priority audit checkpoint — run only if retrieval quality concerns arise after Items 15–16 are live.
