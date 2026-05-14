# Hybrid Search & Scoring — Next Rollout Plan

> Follow-up to sprint `20260504/swapnil-kunjir/updating-hybrid-search`.
> The five items below are ordered by impact-per-effort. Total estimated effort: ~5–7 working days.

---

## Context

The 11–13 May sprint fixed the foundational correctness issues: real Gemma embeddings, populated `skills_text`, seniority inference in JD parsing, multi-vector RAG retrieval using all 5 JD vectors, and a unified skill group scoring path.

With the foundations sound, the next wave focuses on **accuracy lift** and **plugging gaps introduced or left by the multi-vector rewrite**. The five items below are independent enough to be tackled in parallel by different developers, but the listed order maximises confidence at each step.

---

## 1. Cross-Encoder Reranker Between Node 4 and Node 5

**Estimated effort:** 1–2 days
**Expected impact:** Largest single accuracy lift available right now.

### Why

The new multi-vector composite in `_compute_total_score()` is still **bi-encoder math** — JD and candidate are embedded independently and joined by cosine similarity. A cross-encoder consumes `(jd_text, profile_text)` together and judges them jointly, which catches semantic relationships bi-encoders miss (negation, role-context coupling, skill–experience interactions).

This is the standard "third stage" in modern RAG pipelines and is exactly what your 40-candidate funnel was designed to enable.

### What to build

- New utility module: `src/app/ai/utils/reranker.py`
- Loads a HuggingFace cross-encoder model (suggested: `BAAI/bge-reranker-v2-m3` for quality, or `cross-encoder/ms-marco-MiniLM-L-12-v2` for lower latency)
- Function: `rerank_candidates(jd_text: str, candidates: List[RAGCandidate]) -> List[RAGCandidate]`
- Build input pairs as `(jd_text, profile_text + " " + skills_text)` per candidate
- Run a single batched forward pass (~200ms CPU for 40 pairs, faster on GPU)
- Add `rerank_score` field to `RAGCandidate` and re-sort the list

### Integration point

Inside `rag_retrieval.py`, after `_filter_and_rank()` returns the top-40:

```python
if settings.rerank_enabled:
    candidates = rerank_candidates(parsed_jd["jd_text"], candidates)
```

### Settings to add

```python
rerank_enabled: bool = True
rerank_model_name: str = "BAAI/bge-reranker-v2-m3"
rerank_batch_size: int = 16
```

### Acceptance criteria

- Existing bi-encoder scores remain visible in `rag_signals` for audit
- A flag toggles reranking on/off so the current pipeline can be A/B'd
- 40-candidate rerank adds < 500 ms on CPU at p95
- Unit tests cover empty candidate list, model load failure (graceful fallback to bi-encoder order), and batch processing

---

## 2. Validate the New RAG Weights on Historical Feedback

**Estimated effort:** 1–2 days
**Expected impact:** Confidence that the multi-vector rewrite actually moved the needle, plus calibrated weights for production.

### Why

The sprint set these weights based on intuition:

```
full_jd 25% | level 35% | mandatory 20% | preferred 10% | cert 10%
```

Level at 35% is the highest weight — a strong bet that seniority alignment is the most discriminating retrieval signal. It might well be, but there's currently **no evidence** it beats the old `1.0 * full_jd` setup. Before these constants harden into production, run an offline evaluation.

### What to build

A one-off script: `scripts/eval_rag_weights.py`

**Steps:**

1. Pull 20–50 historical requisitions that have associated rows in `requisition_match_team_member_feedback`
2. For each requisition, replay Node 3 (embedding) and Node 4 (RAG retrieval) — but with the multi-vector SQL returning **all 5 raw distances per candidate** rather than a precomputed composite
3. Score each requisition's candidate list under several weight configurations using NDCG@10, with `liked = true` or `rating >= 4` as the relevance label
4. Configurations to test (at minimum):
   - Old single-vector baseline (full_jd = 1.0)
   - Current production weights (25/35/20/10/10)
   - Level-down (full_jd 35, level 20, rest unchanged)
   - Mandatory-up (mandatory 35, level 20, rest unchanged)
   - Equal weights (20% each)
5. Output a CSV: `weight_config, ndcg_at_5, ndcg_at_10, mrr, num_requisitions`

### Acceptance criteria

- Report saved to `docs/evals/rag_weight_sweep_<date>.md`
- If current weights are not in the top 2 configurations, propose new defaults and update `settings.py`
- Script is rerunnable as new feedback accumulates

### Note

Don't gate this on having "enough" feedback. Even 20 requisitions with feedback give a directional signal. Better than no evidence.

---

## 3. Add Per-Skill Rating and Experience to Node 5 Scoring

**Estimated effort:** 1–2 days
**Expected impact:** Better candidate differentiation when multiple candidates have the same mandatory skill set.

### Why

`_calculate_skill_group_score()` currently returns a binary matched/missed per skill. But the database already captures:

- `team_member_skill.rating` — proficiency score (higher = better)
- `team_member_skill.experience_in_months` — time spent actively using the skill

Two candidates both matching "Python" can be very different — rating 5 with 4 years vs. rating 2 with 6 months. The current scoring treats them as equal on `mandatory_score`.

### What to change

In `src/app/ai/utils/scoring.py`, modify `_calculate_skill_group_score()`:

```python
# Current: binary match indicator
matched.append(canonical)

# New: weighted match contribution
member_skill = member_skill_map.get(matched_skill_id)  # row from team_member_skill
if member_skill:
    rating_weight = (member_skill.rating or max_rating) / max_rating
    if required_skill_exp_months > 0:
        exp_weight = min(
            (member_skill.experience_in_months or 0) / required_skill_exp_months,
            1.0
        )
    else:
        exp_weight = 1.0
    skill_contribution = rating_weight * exp_weight
else:
    # Match came from profile_text fallback — no skill row, use neutral weight
    skill_contribution = settings.profile_text_match_weight  # e.g. 0.6

matched_with_weights.append((canonical, skill_contribution))

# Group score becomes weighted average rather than count ratio
group_score = sum(w for _, w in matched_with_weights) / len(required_alternatives)
```

### Settings to add

```python
max_skill_rating: int = 5
profile_text_match_weight: float = 0.6   # weight for skills found only via regex
```

### Required prerequisite

The matching code already queries `TeamMemberSkill` (per the existing per-candidate DB flow), but check that `rating` and `experience_in_months` are loaded into `member_skill_ids`. If they aren't, change the query to return rows rather than just IDs.

### Acceptance criteria

- Two candidates with identical skill names but different ratings produce different `mandatory_score` and `preferred_score`
- Profile-text-only matches (no skill row) get the configured neutral weight, not 1.0 or 0
- Existing unit tests in `test_scoring_agent.py` pass after assertion updates
- New test: a high-rated candidate scores strictly higher than a low-rated one on the same skill set

---

## 4. Investigate Two Potential Regressions From This Sprint

**Estimated effort:** 0.5–1 day
**Expected impact:** Fixes silent issues before they show up in production complaints.

Both items below are worth a focused 2-hour spike each. Either could be a real bug or a non-issue once verified — the goal is to know which.

### 4a. Cert weight contributes 10% even when no certs are required

The current weights are static in `_compute_total_score()`. When `parsed_jd["certifications_required"]` is empty, the `cert_vec` is still embedded (from the empty/placeholder text built by `_cert_text()`) and still contributes 10% to the composite. Effectively, 10% of the retrieval ranking signal is noise for non-cert roles — which is most roles.

**Verification:**

- Run two test requisitions through the pipeline — one with certs required, one without
- Inspect `rag_signals.cert_rag_sim` distribution across candidates in the no-cert case
- If variance is low (everyone scores similarly) the impact is minor; if variance is high it's actively distorting rankings

**Fix if confirmed:**

```python
def _compute_total_score(self, distances, certifications_required: List[str]) -> float:
    if not certifications_required:
        # Renormalize the other 4 weights to sum to 1.0
        total = (rag_weight_full_jd + rag_weight_level +
                 rag_weight_skills_mandatory + rag_weight_skills_preferred)
        return (
            full_jd_sim * (rag_weight_full_jd / total)
            + level_sim * (rag_weight_level / total)
            + mandatory_vec_sim * (rag_weight_skills_mandatory / total)
            + preferred_vec_sim * (rag_weight_skills_preferred / total)
        )
    # ... existing 5-vector path
```

### 4b. Senior with niche profile may now fail retrieval before AI Senior Waiver can rescue them

The level vector at 35% weight is strong by design. But the AI Senior Waiver in Node 5 only runs on candidates that **reach Node 5**. If a senior with an unusual profile gets dropped at the Node 4 cutoff (top-40 by composite similarity), the waiver never gets a chance to override.

**Verification:**

- Identify 5–10 known-good senior placements from history (recruiter-confirmed strong candidates)
- For each, replay their original requisition through Node 4 with the new weights
- Confirm they still appear in the top-40
- Specifically check candidates whose `jd_level_similarity` is high but whose `mandatory_similarity` is low (the unusual-skills senior case)

**Fix if confirmed:**

- Increase the Node 4 LIMIT from 10 to 50–80 to give more headroom (the SQL is cheap; the cost is in Node 5)
- OR: add a senior-only carve-out that includes the top-20 by `level_similarity` regardless of composite rank

This investigation is most important before increasing the cross-encoder reranker's reliance on Node 4's shortlist (Item 1). If Node 4 drops good seniors today, the reranker will not save them.

---

## 5. Expand the BM25 Mandatory Query Through `skill_ontology`

**Estimated effort:** 0.5 day
**Expected impact:** Recall improvement for candidates whose profiles use skill synonyms.

### Why

`_build_keyword_strings()` in `rag_retrieval.py` currently builds the mandatory `tsquery` directly from skill names extracted by the parser. If the JD says "ReactJS" but a candidate's profile says "React.js", BM25 misses the match — and since this query is in the **WHERE clause as a hard filter**, the candidate is filtered out entirely.

The `skill_ontology` table exists precisely for this purpose. `skill_ontology.enriched_terms` is an array of synonyms per canonical skill (e.g. `react` → `['ReactJS', 'React.js', 'React Native']`), but it's currently used only inside Node 2 (skill normalization), not in Node 4 retrieval.

### What to change

In `rag_retrieval.py`, before building `mandatory_query_str`:

```python
def _expand_mandatory_terms(mandatory_skills: List[str], db: Session) -> List[str]:
    """Expand each mandatory skill through skill_ontology synonyms."""
    expanded = set()
    for skill in mandatory_skills:
        expanded.add(skill)
        rows = db.execute(
            text("SELECT enriched_terms FROM skill_ontology WHERE LOWER(core_skill) = LOWER(:s)"),
            {"s": skill}
        ).fetchall()
        for row in rows:
            if row.enriched_terms:
                expanded.update(row.enriched_terms)
    return list(expanded)

# In _build_keyword_strings:
expanded_mandatory = _expand_mandatory_terms(mandatory_skills, db)
mandatory_query_str = " OR ".join(f'"{t}"' if " " in t else t for t in expanded_mandatory)
```

### Index check

The guide notes `idx_skill_ontology_core_skill` already exists, so the lookup is O(1) per skill. For 5–10 mandatory skills per JD this adds ~5–10 ms.

### Acceptance criteria

- A JD with "ReactJS" matches a candidate whose `skills_text` only contains "React.js"
- A JD with "PostgreSQL" matches a candidate with "Postgres" in their profile
- Unit test: mock `skill_ontology` with known synonym pairs and verify the expanded query string includes them
- Fallback: if `skill_ontology` lookup fails or returns nothing, use the original skill name (don't break the pipeline)

---

## Rollout Order Summary

| # | Item | Effort | Risk | Why this order |
|---|------|--------|------|----------------|
| 1 | Cross-encoder reranker | 1–2 d | Low | Biggest single quality lift; isolated behind a flag |
| 2 | RAG weight validation | 1–2 d | None (offline) | Confirms the sprint's choices before more weight-dependent work |
| 3 | Per-skill rating & experience in scoring | 1–2 d | Low | Better differentiation; uses existing DB columns |
| 4 | Cert-weight & senior-retrieval audits | 0.5–1 d | None (investigation) | Catches potential regressions from this sprint |
| 5 | BM25 ontology expansion | 0.5 d | Low | Recall improvement; small, safe change |

**Total: ~5–7 working days.**

Items 1, 3, and 5 are independent and can be parallelised across developers. Item 2 should ideally land before any further weight tuning. Item 4 is a checkpoint, not a feature — schedule it as a single afternoon spike.
