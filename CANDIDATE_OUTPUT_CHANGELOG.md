# Candidate Output Field Changelog

Tracks the evolution of the per-candidate response payload returned by the matching API.
Each entry records what changed, why, and which code owns the field.

---

## Current Output Structure (as of 2026-05-21)

```
match (per candidate)
├── team_member_id
├── profile_score
├── fit_level
├── availability_match
├── explanation[]
└── detailed_breakdown
    ├── phase0_ledger            ← RAG retrieval snapshot
    ├── score_breakdown          ← deterministic scoring components
    ├── match_reasons            ← skill match detail + AI narrative
    ├── ai_confidence_score
    ├── ai_boost_applied
    ├── role_type
    ├── is_qualified
    └── qualification_reason
```

---

## phase0_ledger Field Audit

`phase0_ledger` is built by `_build_breakdown()` in
`src/app/ai/utils/rag_retrieval.py:574` and stored on
`RAGCandidate.phase0_score_breakdown`. It is a **read-only audit snapshot** — none of
these values are re-read by the scoring formula after being written.

### Fields — RETAIN

| Field | Source | Why kept |
|---|---|---|
| `rrf_score` | `1/(k+semantic_rank) + 1/(k+bm25_rank)` | Explains why this candidate was retrieved; primary sort key for candidate pool |
| `semantic_rank` | Position in pgvector ORDER BY result | Retrieval debug — shows vector path ranking |
| `bm25_rank` | Position in pg_bm25 ORDER BY result | Retrieval debug — shows keyword path ranking |
| `bm25_score` | Raw `paradedb.score()` value | Raw BM25 signal; useful for tuning keyword queries |
| `full_jd_vector_sim` | `1/(1 + L2_distance)` vs full JD embedding | Feeds `s_score` blend in Node 5 scoring |
| `level_vector_sim` | `1/(1 + L2_distance)` vs seniority-level JD vector | Primary input to `semantic_similarity` in `score_breakdown` |
| `mandatory_skills_vector_sim` | `1/(1 + L2_distance)` vs mandatory skills vector | Audit signal; shows embedding quality for skill match |
| `preferred_skills_vector_sim` | `1/(1 + L2_distance)` vs preferred skills vector | Audit signal |
| `cert_vector_sim` | `1/(1 + L2_distance)` vs certifications vector | Audit signal |
| `location_compatibility` | Python string check on `base_location` | Pre-filter signal; confirms SQL filter worked |
| `work_mode_compatibility` | Python alias check on `work_type` | Pre-filter signal |
| `mandatory_penalty_assigned` | `bool(mandatory_skills and not mandatory_matches)` | Flags candidates with zero keyword presence for mandatory skills at retrieval time |

---

### Fields — REMOVED from phase0_ledger

#### `mandatory_score`

| | |
|---|---|
| **Was** | `len(keyword_matches) / len(mandatory_skills)` — text substring match on `skills_text` column |
| **Removed** | 2026-05-21 |
| **Reason** | Superseded by `score_breakdown.mandatory_skills_group`, which uses structured DB skill IDs + per-skill rating/experience blend. The text match is a weaker, noisier signal. Example: candidate 2462 showed `0.3333` in ledger (1/3 found in text) while DB scoring found all 3 skills and returned `0.4733`. Keeping both caused confusion — readers assumed the lower ledger number reflected actual skill coverage. |
| **Replaced by** | `score_breakdown.mandatory_skills_group` + `match_reasons.mandatory_matched` / `mandatory_missing` |
| **Code** | `src/app/ai/utils/rag_retrieval.py:529` (removed from breakdown dict only; `m_score` is still computed internally for `mandatory_penalty_assigned`) |

---

#### `preferred_score`

| | |
|---|---|
| **Was** | `len(keyword_matches) / len(preferred_skills)` — text match; defaulted to `1.0` when no preferred skills in JD |
| **Removed** | 2026-05-21 |
| **Reason** | Same weakness as `mandatory_score` — text-based, no rating/experience blend. The default value of `1.0` when preferred skills are absent is misleading: a reader sees `preferred_score: 1.0` and assumes a strong match when it actually means "not applicable". |
| **Replaced by** | `score_breakdown.preferred_skills` + `match_reasons.preferred_matched` / `preferred_missing` |
| **Code** | `src/app/ai/utils/rag_retrieval.py:530` |

---

#### `experience_relevance`

| | |
|---|---|
| **Was** | `_exp_relevance(experience_in_months, experience_req)` — partial credit for candidates outside the JD experience range |
| **Removed** | 2026-05-21 |
| **Reason** | Duplicate computation. `scoring.py:_calculate_experience_score()` recalculates experience fit from the same DB field with identical logic and exposes it via `context_score`. Carrying a parallel copy in the ledger adds no new information and can drift if the scoring formula changes without updating the retrieval copy. |
| **Replaced by** | `score_breakdown.context_score` (aggregated) and `match_reasons.experience_score` |
| **Code** | `src/app/ai/utils/rag_retrieval.py:519` |

---

#### `certification_score`

| | |
|---|---|
| **Was** | `len(cert_matches) / len(certifications)` — text match on `certifications_text` column; defaulted to `1.0` when no certs required |
| **Removed** | 2026-05-21 |
| **Reason** | Same two problems as `preferred_score`: weaker text signal superseded by DB-backed scoring, and misleading `1.0` default when no certifications are required. Authoritative cert result lives in `match_reasons.certification_score`, `certification_matched`, and `certification_missing`. |
| **Replaced by** | `match_reasons.certification_score` + `certification_matched` / `certification_missing` |
| **Code** | `src/app/ai/utils/rag_retrieval.py:531` |

---

## Score Flow Reference

Clarifies which node owns each scoring signal to avoid future duplication.

| Signal | Output field | Node | Data source |
|---|---|---|---|
| Candidate retrieval ranking | `phase0_ledger.rrf_score` | RAG retrieval (`rag_retrieval.py`) | pgvector + pg_bm25 SQL |
| Mandatory skill coverage | `score_breakdown.mandatory_skills_group` | Scoring (`scoring.py`) | `TeamMemberSkill` rows + rating/exp blend |
| Preferred skill coverage | `score_breakdown.preferred_skills` | Scoring (`scoring.py`) | `TeamMemberSkill` rows + rating/exp blend |
| Semantic alignment | `score_breakdown.semantic_similarity` | Scoring (`scoring.py`) | `level_vector_sim` × 0.70 + `full_jd_vector_sim` × 0.30 |
| Experience fit | `match_reasons.experience_score` | Scoring (`scoring.py`) | `TeamMember.experience_in_months` vs JD min/max |
| Certification fit | `match_reasons.certification_score` | Scoring (`scoring.py`) | `TeamMemberSkillCertification` rows |
| Location / work mode | `match_reasons.location_matched`, `work_mode_matched` | Scoring (`scoring.py`) | `TeamMember.base_location`, `work_type` |
| AI narrative | `explanation[]`, `match_reasons.ai_reasoning` | AI confidence (`ai_confidence.py`) | LLM on JD text + profile text |
| Final score | `profile_score` | Scoring + AI boost | `match_score × 100` + optional `ai_boost` |

---

## Scoring Behaviour Changes

Changes that do not add or remove output fields but alter how existing field values are
computed. Tracked here because they affect score reproducibility and debuggability.

---

### `score_breakdown.context_score` — dynamic weighting (Pending)

| | |
|---|---|
| **Was** | Fixed denominator: `total_weight = weight_exp + weight_cert + weight_loc + weight_mode + weight_title` (always 0.45). Every non-required criterion defaults to 1.0 and still consumes its full weight share. |
| **Now** | Dynamic denominator: only criteria that the JD actually constrains contribute to both the numerator and denominator. Non-constraining criteria are excluded entirely. |
| **Why** | For a JD with `location=["Remote"]`, `work_mode=["Remote","Hybrid"]`, and no required certs, all three of those criteria defaulted to 1.0 for every candidate → `context_score = 0.8` and `context_contribution = 0.04` was identical for all candidates. The context component added a flat constant and provided zero differentiation. |
| **Active rules** | Experience: active only when `min_experience_months` is set. Certification: active only when `required_certifications` is non-empty. Location: active only when at least one physical location is required (excludes "Remote"/"Any"/"WFH"). Work mode: active only when exactly one mode is required. Title: always active. |
| **Impact on output** | `context_score` and `context_contribution` will now vary between candidates for the same JD when the active criteria differ between them (e.g. one candidate meets experience, another does not). |
| **Code** | `src/app/ai/utils/scoring.py:_calculate_context_boost()` |
| **Plan ref** | Addendum 2 in `watch-plan-hybrid-search-rollout-plan-md-encapsulated-owl.md` |

---

### `match_reasons.certification_score` — no-cert default (Pending)

| | |
|---|---|
| **Was** | `_calculate_certification_score()` returns `{"score": 1.0, ...}` when `required_certifications` is empty. This 1.0 was multiplied by `weight_certification` and added to `context_score` for all candidates. |
| **Now** | When `required_certifications` is empty, the certification criterion is excluded from both numerator and denominator in `_calculate_context_boost()` (handled by the dynamic weighting change above). The `1.0` default inside `_calculate_certification_score()` itself is unchanged — it remains the correct return value when no certs are required — but the caller no longer uses it in the aggregation. |
| **Why** | `cert_score = 1.0` for all candidates when no certs are required means the 0.10 certification weight was spent giving everyone the same free bonus. It inflated `context_score` uniformly and made the cert weight meaningless for JDs without certification requirements. |
| **Impact on output** | `certification_score` in `match_reasons` remains 1.0 when no certs required (correct). `context_score` will be lower and will reflect only truly constraining factors. |
| **Code** | `src/app/ai/utils/scoring.py:_calculate_context_boost()` |
| **Plan ref** | Addendum 2 in `watch-plan-hybrid-search-rollout-plan-md-encapsulated-owl.md` |

---

## RRF Constant Change Log

| Date | k value | Pool size | Reason |
|---|---|---|---|
| Original | 60 | ~1500 | Elasticsearch/Weaviate default — not tuned for this system |
| 2026-05-21 | **Pending → 40** | 1500, growing to ~5000 | k=60 compresses rank #1 vs rank #40 to only 1.64× separation within the 100-candidate fetch cap — too little discrimination for a structured HR pool. k=40 gives 1.95× separation and scales safely to ~5000 members without revisiting. |

**Action required:** Move hardcoded `_k = 60` in `src/app/ai/utils/rag_retrieval.py:536`
to `settings.rrf_k: int = 40` so it can be tuned without a code deploy.

---

## How to Use This Document

- When **removing** a field from the output, add an entry under the relevant section with the date, what the field was, and what replaces it.
- When **adding** a new field, document which node computes it, what data source it reads, and why it cannot be derived from an existing field.
- Always cross-reference the source file and line number so entries stay verifiable against the code.
