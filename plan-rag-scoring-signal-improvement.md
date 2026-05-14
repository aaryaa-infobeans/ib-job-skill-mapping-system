# Plan: Use Available RAG Signals in Scoring + Include Cert Vector in Hybrid Search

---

## What Changed in the Previous Session (Before → After)

### 1. `jd_level_vector` semantic fix
**Before:** `jd_level` field in `RequisitionData` was populated from `parsed_jd["normalized_role"]`
(e.g. `"Backend Engineer"`). The embedding text was `"Job level: Backend Engineer"` — no
seniority information at all.

**After:** `jd_level` is now populated from `parsed_jd["level"]` which holds `SENIOR`/`MID`/`JUNIOR`.
The embedding text is now `"Seniority: SENIOR. Title: Senior Python Developer."` — carries
actual seniority vocabulary that the vector model can use for alignment.

### 2. Level inference chain added to Node 1
**Before:** The LLM prompt had no `level` field. `parsed_jd["level"]` always fell back to `"MID"`.

**After:** LLM prompt now includes `level` in its output schema with inference rules.
Four-layer fallback added in `requisition_parsing.py`: LLM output → title keyword heuristic
→ experience range → default MID.

### 3. Unified `_calculate_skill_group_score` in scoring
**Before:** Two separate functions: `_calculate_mandatory_group_score` and `_calculate_skill_score`.
`_calculate_skill_score` had a logic bug — it iterated raw skill IDs against a canonical-keyed
`preferred_alternatives` dict, so alternative IDs were never checked and profile text fallback
always failed.

**After:** Single unified `_calculate_skill_group_score(member_skill_ids, skill_alternatives, profile_text)`.
Bug fixed: iterates `skill_alternatives.items()` with canonical keys. Short-string guard now
applies to both mandatory and preferred. `_calculate_context_boost` refactored to return
sub-scores in a dict, eliminating duplicate calculations in `execute()`.

---

## Current State (What Exists Now)

After the above changes the pipeline correctly:
- Embeds job level as a seniority-rich phrase
- Infers level from jd_text when not explicitly provided
- Matches skills using canonical alternatives for both mandatory and preferred

But the following signals are **computed and available** yet **never used** in the final score:

| Signal | Where it lives | Status |
|---|---|---|
| `rag_candidate.final_similarity` | `RAGCandidate` | IGNORED in `scoring.py` |
| `rag_candidate.mandatory_similarity` | `RAGCandidate` | IGNORED in `scoring.py` |
| `rag_candidate.preferred_similarity` | `RAGCandidate` | IGNORED in `scoring.py` |
| `rag_candidate.certification_similarity` | `RAGCandidate` | IGNORED in `scoring.py` |
| `cert_vec_sim` | Computed in `_build_structured_candidate` | NOT in `multi_vec_semantic` |
| `full_jd_sim` | `phase0_score_breakdown["vector_sims"]["full_jd"]` | NOT on `RAGCandidate` directly |

---

## Signal Redundancy Map

Before proposing changes, it is critical to understand which signals actually flow
between RAG and Node 5. Only signals that are **read from `RAGCandidate` inside
`scoring.py`** can cause true double-counting in `match_score`.

### How signals flow (or don't) between phases

RAG computes `final_similarity` which aggregates experience, location, work mode,
certifications, keyword matches, and all 5 vector similarities. But:

```
RAGCandidate.final_similarity  →  NEVER READ in scoring.py execute()
RAGCandidate.mandatory_similarity  →  NEVER READ
RAGCandidate.preferred_similarity  →  NEVER READ
RAGCandidate.certification_similarity  →  NEVER READ
```

Because `final_similarity` is never used in Node 5, the experience/location/work mode/cert
signals that appear inside it are **not double-counted** — they are two independent
calculations for two separate purposes (RAG ranks the pool; Node 5 scores the pool).

### The one true overlap

The only `RAGCandidate` field that `scoring.py` actually reads is:

```python
s_score = rag_candidate.jd_level_similarity   # scoring.py line ~305
```

`level_sim` therefore appears in:
1. RAG `multi_vec_semantic` at 40% weight → influences which candidates enter the top 40
2. Node 5 `s_score` at 25% of `match_score` → influences the final ranking

This is the only place where the same computed value is used in both phases AND
contributes to the final `match_score`. Everything else in RAG and Node 5 is parallel,
not additive.

### Why the original Change 2 was wrong

The earlier draft proposed:
```python
s_score = jd_level_similarity * 0.70 + final_similarity * 0.30
```

`final_similarity` contains `level_sim` at 40% of its semantic component. Blending
it into `s_score` would count level a third time inside the Node 5 formula — the
one place where double-counting is truly additive. **This change is dropped.**

---

## Revised Proposed Changes

### Change 1 — RAG: Add cert vector to `_compute_total_score`

**Problem:** `cert_vec_sim` is fetched from pgvector (`cert_distance` column), converted to
similarity, and stored in `phase0_score_breakdown["vector_sims"]["cert"]` — but it is NOT
included in `multi_vec_semantic`. The vector cost is paid, but the signal is dropped.

**Secondary benefit:** Reducing `rag_weight_level` from 0.40 to 0.35 partially mitigates
the level over-weighting in the RAG phase identified above.

**Files:** `src/app/ai/utils/rag_retrieval.py`, `src/app/settings.py`

Current `multi_vec_semantic` weights (must sum to 1.0):
```
full_jd: 0.30 + level: 0.40 + mandatory: 0.20 + preferred: 0.10 = 1.00
```

Proposed (redistribute to make room for cert):
```
full_jd: 0.25 + level: 0.35 + mandatory: 0.20 + preferred: 0.10 + cert: 0.10 = 1.00
```

Code change in `_compute_total_score` (`rag_retrieval.py` line ~333):
```python
# Before:
multi_vec_semantic = (
    full_jd_sim       * settings.rag_weight_full_jd +
    level_sim         * settings.rag_weight_level +
    mandatory_vec_sim * settings.rag_weight_skills_mandatory +
    preferred_vec_sim * settings.rag_weight_skills_preferred
)

# After:
multi_vec_semantic = (
    full_jd_sim       * settings.rag_weight_full_jd +
    level_sim         * settings.rag_weight_level +
    mandatory_vec_sim * settings.rag_weight_skills_mandatory +
    preferred_vec_sim * settings.rag_weight_skills_preferred +
    cert_vec_sim      * settings.rag_weight_cert
)
```

Settings changes (`settings.py`):
```python
rag_weight_full_jd: float = 0.25     # was 0.30
rag_weight_level: float = 0.35       # was 0.40
rag_weight_cert: float = 0.10        # new
```

---

### Change 2 — Scoring: Add `full_jd_sim` as a second semantic signal (replaces earlier blend)

**Problem:** `s_score` currently uses only `jd_level_similarity` (seniority alignment).
There is no signal in Node 5 that captures **overall JD-to-profile semantic similarity**
independent of seniority. `full_jd_sim` (the full JD embedding vs member's resume embedding)
fills this gap without introducing any overlap with the deterministic scoring components.

**Why `full_jd_sim` and not `final_similarity`:**
- `final_similarity` contains experience, location, keyword counts → already in context boost
- `final_similarity` contains `level_sim` at 40% of its semantic component → would triple-count level
- `full_jd_sim` is a pure vector-to-vector distance: full JD text embedding ↔ member resume embedding
  It has no experience/location/keyword terms and does not contain `level_sim`
- It is the one RAG-computed signal with zero overlap with anything else in Node 5

**What needs to happen:** `full_jd_sim` is currently only in
`phase0_score_breakdown["vector_sims"]["full_jd"]`. It needs to be promoted to a top-level
field on `RAGCandidate` so `scoring.py` can read it.

**Files:** `src/app/ai/utils/models.py`, `src/app/ai/utils/rag_retrieval.py`,
`src/app/ai/utils/scoring.py`, `src/app/settings.py`

Step 1 — Add field to `RAGCandidate` (`models.py`):
```python
@dataclass
class RAGCandidate:
    ...
    full_jd_similarity: float = 0.0   # ← new field
```

Step 2 — Populate it in `_build_structured_candidate` (`rag_retrieval.py`):
```python
return RAGCandidate(
    ...
    full_jd_similarity=round(full_jd_sim, 4),   # ← new
    ...
)
```

Step 3 — Use it in `scoring.py` execute():
```python
# Before:
s_score = rag_candidate.jd_level_similarity

# After:
_blend = settings.scoring_blend_full_jd_weight   # default 0.30
s_score = (
    rag_candidate.jd_level_similarity * (1.0 - _blend) +
    rag_candidate.full_jd_similarity   * _blend
)
```

New setting:
```python
scoring_blend_full_jd_weight: float = 0.30
```

At 0.30: 70% seniority alignment + 30% overall JD semantic fit. No double-counting.

---

### Change 3 — Output: Surface unused RAG signals in score_dict

**Problem:** `mandatory_similarity`, `preferred_similarity`, `certification_similarity`, and
`final_similarity` on `RAGCandidate` are silently dropped when building `score_dict`.

**File:** `src/app/ai/agents/matching_scoring.py`

Add to `score_dict`:
```python
"rag_signals": {
    "final_similarity":    round(rag_candidate.final_similarity, 4),
    "full_jd_similarity":  round(rag_candidate.full_jd_similarity, 4),
    "jd_level_similarity": round(rag_candidate.jd_level_similarity, 4),
    "mandatory_rag_sim":   round(rag_candidate.mandatory_similarity, 4),
    "preferred_rag_sim":   round(rag_candidate.preferred_similarity, 4),
    "cert_rag_sim":        round(rag_candidate.certification_similarity, 4),
},
```

No scoring logic changes — purely additive observability.

---

## Files to Change

| File | Change Type | Detail |
|---|---|---|
| `src/app/settings.py` | Add 2 settings, modify 2 | Add `rag_weight_cert`, `scoring_blend_full_jd_weight`; lower `rag_weight_full_jd` and `rag_weight_level` |
| `src/app/ai/utils/models.py` | Add 1 field | Add `full_jd_similarity: float = 0.0` to `RAGCandidate` |
| `src/app/ai/utils/rag_retrieval.py` | 2-line addition | Add `cert_vec_sim` to `multi_vec_semantic`; populate `full_jd_similarity` on `RAGCandidate` |
| `src/app/ai/utils/scoring.py` | 4-line change | Replace single `s_score` assignment with blend of `jd_level_similarity` + `full_jd_similarity` |
| `src/app/ai/agents/matching_scoring.py` | Additive | Add `rag_signals` dict to `score_dict` |

**No changes to:**
- `src/app/ai/agents/embedding.py` — cert vector already generated; full_jd vector already generated
- `tests/unit/test_scoring_agent.py` — blend is settings-driven; existing 9 tests pass unchanged

---

## Execution Order

1. `settings.py` — add/change the four weight settings
2. `models.py` — add `full_jd_similarity` field to `RAGCandidate`
3. `rag_retrieval.py` — add cert_vec_sim to multi_vec_semantic; populate `full_jd_similarity`
4. `scoring.py` — replace s_score line with blend of level + full_jd
5. `matching_scoring.py` — add `rag_signals` to score_dict

---

## Verification

1. `pytest tests/unit/test_scoring_agent.py -v` — all 9 tests pass unchanged
2. Live request — confirm `score_dict["rag_signals"]["full_jd_similarity"]` is non-zero and
   **different** from `jd_level_similarity` (proves the two signals are orthogonal)
3. Live request — confirm `score_breakdown["semantic_similarity"]` is a blended value,
   not identical to `jd_level_similarity`
4. Live request with cert requirements — confirm `phase0_ledger["vector_sims"]["cert"]`
   is non-trivial and top RAG candidates shift relative to before
5. Sanity check for level over-weighting: for a requisition with level=SENIOR, verify that
   a junior member with otherwise identical skills ranks below a senior member — and that
   the gap is not disproportionately large compared to skill match differences
