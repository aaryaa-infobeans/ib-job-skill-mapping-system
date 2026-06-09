# JD Parsing Robustness Improvement — Node 1 & Node 3

Design document for making JD parsing and embedding more robust when optional input fields are absent.

---

## Table of Contents

1. [Problem Summary](#1-problem-summary)
2. [How JD Parsing Works Today](#2-how-jd-parsing-works-today)
3. [Issue 1 — `jd_level_vector` Embeds the Wrong Text](#3-issue-1--jd_level_vector-embeds-the-wrong-text)
4. [Issue 2 — No Seniority Level Extracted by the LLM](#4-issue-2--no-seniority-level-extracted-by-the-llm)
5. [Issue 3 — Other Pipeline Variables Have No Fallback Extraction](#5-issue-3--other-pipeline-variables-have-no-fallback-extraction)
6. [Why Not Enforce Required Fields in the API Schema](#6-why-not-enforce-required-fields-in-the-api-schema)
7. [Proposed Fix — Level Inference Chain](#7-proposed-fix--level-inference-chain)
8. [Proposed Fix — LLM Prompt Enhancement](#8-proposed-fix--llm-prompt-enhancement)
9. [Proposed Fix — `jd_level_text` Construction](#9-proposed-fix--jd_level_text-construction)
10. [Proposed Fix — Mandatory Skills Fallback](#10-proposed-fix--mandatory-skills-fallback)
11. [Files to Change](#11-files-to-change)
12. [Risk and Rollback](#12-risk-and-rollback)
13. [Acceptance Criteria](#13-acceptance-criteria)

---

## 1. Problem Summary

The pipeline depends on several JD fields (seniority level, mandatory skills, experience range) that are optional
in the API schema. When a caller omits them and provides only `jd_text`, the pipeline silently uses incorrect
defaults rather than extracting the information from the text that is already present.

The most impactful case is `jd_level_vector` — the embedding that drives the semantic gate and 25% of the
`match_score` in Node 5 — being built from the wrong text entirely.

---

## 2. How JD Parsing Works Today

```
API Input (RequisitionRequest)
        │
        ▼
Node 1 — requisition_parsing_node
        │   LLM enriches: normalized_title, normalized_role,
        │   mandatory_skills, preferred_skills, experience, certifications
        │
        ▼
Node 3 — embedding_node
        │   Builds 5 JD vectors:
        │     full_jd_vector      ← raw jd_text
        │     jd_level_vector     ← "Job level: {normalized_role}"   ← PROBLEM
        │     mandatory_vector    ← "Required skills: ..."
        │     preferred_vector    ← "Preferred skills: ..."
        │     certification_vector← "Certifications: ..."
        │
        ▼
Node 4 — rag_retrieval_node
        │   Uses jd_level_vector for level_distance comparison
        │   jd_level_similarity flows to Node 5 as s_score
        ▼
Node 5 — matching_scoring_node
        │   s_score = rag_candidate.jd_level_similarity
        │   Used as semantic gate AND 25% of match_score
```

**Relevant files:**
- Node 1: `src/app/ai/agents/requisition_parsing.py`
- Node 3: `src/app/ai/agents/embedding.py`, `src/app/ai/utils/embedding.py`
- Node 5 scoring: `src/app/ai/utils/scoring.py` line 345

---

## 3. Issue 1 — `jd_level_vector` Embeds the Wrong Text

### What the code does

In `src/app/ai/utils/embedding.py` line 35 and 63:

```python
jd_level = getattr(normalized_requisition.original_requisition, 'jd_level', None)
jd_level_text = f"Job level: {jd_level}" if jd_level else None
```

`jd_level` is populated from `parsed_jd.get("normalized_role", "")` in `embedding.py` line 35:

```python
jd_level=parsed_jd.get("normalized_role", ""),
```

### What `normalized_role` actually is

`normalized_role` is the **domain/role category** extracted by the LLM — e.g. `"Backend Engineer"`,
`"Machine Learning Engineer"`, `"Full Stack Developer"`. It is a role category, not a seniority level.

So the text being embedded for `jd_level_vector` is actually:

```
"Job level: Backend Engineer"
```

`"Backend Engineer"` carries **zero seniority information**. It does not tell the system whether the
role is junior, mid, or senior. The vector ends up measuring domain alignment rather than seniority
alignment — almost the same signal as `full_jd_vector`.

### Why this matters

`jd_level_similarity` (produced from this vector) is used in Node 5 as `s_score`:

```python
# src/app/ai/utils/scoring.py line 345
s_score = rag_candidate.jd_level_similarity
```

`s_score` has two effects:
1. **Semantic gate (Stage 1):** `if s_score < gates["min_semantic"]` → candidate DISQUALIFIED
2. **Semantic weight (Stage 2):** `s_score * role_weights["semantic"]` → 25% of `match_score`

A vector built from a domain label (`"Backend Engineer"`) cannot reliably gate or score
seniority alignment. A junior backend developer and a senior architect would produce similar
`jd_level_similarity` values, defeating the purpose of this gate.

---

## 4. Issue 2 — No Seniority Level Extracted by the LLM

### What the LLM prompt returns today

The LLM in `requisition_parsing.py` is asked to return:

```json
{
  "normalized_title": "string - standardized job title",
  "normalized_role": "string - standardized role category",
  "mandatory_skills": [...],
  "preferred_skills": [...],
  "experience": {"min_months": null, "max_months": null},
  "certifications": [...]
}
```

There is no `level` field (JUNIOR / MID / SENIOR) in the LLM output schema.
The LLM has enough information in `jd_text` and `normalized_title` to infer this reliably,
but it is never asked to.

### Where `level` appears downstream

`parsed_jd.get("level", "MID")` is used in `matching_scoring.py` line 186 to select the
role config (weights and gates) in `ScoringAgent`. The LLM never sets this field,
so it always falls back to `"MID"` regardless of the actual job seniority.

---

## 5. Issue 3 — Other Pipeline Variables Have No Fallback Extraction

The API schema (per `specs/functional/fr-1-requisition-request-api.md`) deliberately marks
several fields as optional because `jd_text` is the required fallback source of truth.
The LLM in Node 1 is responsible for extracting these from `jd_text` when absent.

Current gaps where the LLM extraction is either absent or unreliable:

| Variable | Used in | Impact if missing/wrong |
|---|---|---|
| `level` (JUNIOR/MID/SENIOR) | Node 5 role config, `jd_level_vector` | Wrong weights/gates applied; wrong seniority embedding |
| `mandatory_skills` | RAG BM25 filter, Node 5 mandatory gate | BM25 has no keywords; mandatory gate scores 1.0 (no skills = full score) |
| `experience.min_months` | RAG experience filter, Node 5 experience score | No experience gate; all candidates pass |

`preferred_skills` and `certifications` are lower risk — their absence degrades score precision
but does not cause misclassification.

---

## 6. Why Not Enforce Required Fields in the API Schema

The functional spec (`fr-1-requisition-request-api.md`) deliberately keeps these fields optional.
The architectural intent is that `jd_text` alone is sufficient for the pipeline to operate —
the LLM extracts what it needs from the text. Enforcing fields at the schema level would break
existing callers and contradict the spec.

The correct fix is to make the **extraction more robust** inside the pipeline, not to change the
contract at the API boundary.

---

## 7. Proposed Fix — Level Inference Chain

When a caller provides only `jd_text`, level should be inferred using a four-layer chain.
Each layer is only reached if the previous one produces no result.

### Layer 1 — LLM extraction (most reliable)

Ask the LLM explicitly for `level` as part of the `requisition_parsing` output (see Section 8).
The LLM can pick up subtle signals a regex misses: "Staff Engineer" → SENIOR, "IC3" → MID,
"Associate" → JUNIOR, "5+ years leading teams" → SENIOR.

### Layer 2 — Title keyword heuristic

If the LLM returns no level or the field is absent:

```python
SENIOR_KEYWORDS = ["senior", "sr.", "sr ", "lead", "principal", "staff",
                   "architect", "head of", "director"]
JUNIOR_KEYWORDS = ["junior", "jr.", "jr ", "associate", "entry", "intern",
                   "graduate", "fresher", "trainee"]

def infer_level_from_title(title: str) -> str:
    t = title.lower()
    if any(k in t for k in SENIOR_KEYWORDS):
        return "SENIOR"
    if any(k in t for k in JUNIOR_KEYWORDS):
        return "JUNIOR"
    return None   # not determinable from title alone
```

### Layer 3 — Experience range tiebreaker

If title is ambiguous (e.g. plain "Software Developer"):

```python
def infer_level_from_experience(min_months: Optional[int]) -> str:
    if min_months is None:
        return None
    if min_months >= 60:    # 5+ years
        return "SENIOR"
    if min_months <= 12:
        return "JUNIOR"
    return "MID"
```

### Layer 4 — Default to MID

An unqualified title with no experience range is statistically most likely mid-level.
All industry benchmarks (LinkedIn, ISCO-08) treat unqualified role titles as mid-level by default.

```python
inferred_level = (
    llm_level
    or infer_level_from_title(normalized_title)
    or infer_level_from_experience(min_months)
    or "MID"
)
```

This chain runs inside `requisition_parsing_node` after the LLM call, before state is written.

---

## 8. Proposed Fix — LLM Prompt Enhancement

Add `level` to the LLM output schema in `requisition_parsing.py`:

```python
PARSING_PROMPT = """
...existing instructions...

Return ONLY a valid JSON object with this exact structure:
{
  "normalized_title": "string - standardized job title",
  "normalized_role": "string - standardized role category",
  "level": "JUNIOR | MID | SENIOR - inferred from title, responsibilities, and experience",
  "mandatory_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill3", "skill4"],
  "experience": {
    "min_months": number or null,
    "max_months": number or null
  },
  "certifications": ["cert1", "cert2"]
}

Level inference rules:
- SENIOR: title contains Senior/Sr/Lead/Principal/Staff/Architect, OR 5+ years required
- JUNIOR: title contains Junior/Jr/Associate/Entry/Intern/Graduate, OR <= 1 year required
- MID: everything else, or when uncertain
"""
```

Then in `requisition_parsing_node`, after the LLM call:

```python
# Layer 1: LLM result
inferred_level = llm_output.get("level")

# Layer 2: title heuristic
if not inferred_level:
    inferred_level = infer_level_from_title(enriched_jd["normalized_title"])

# Layer 3: experience
if not inferred_level:
    min_m = enriched_jd.get("experience", {}).get("min_months")
    inferred_level = infer_level_from_experience(min_m)

# Layer 4: default
enriched_jd["level"] = inferred_level or "MID"
```

---

## 9. Proposed Fix — `jd_level_text` Construction

In `src/app/ai/utils/embedding.py`, change `jd_level_text` to use the inferred `level`
alongside `normalized_role` and `normalized_title` to produce a seniority-rich phrase:

```python
# Current (wrong):
jd_level_text = f"Job level: {jd_level}"
# e.g. "Job level: Backend Engineer"  ← no seniority signal

# Fix:
level = getattr(req.original_requisition, 'jd_level', 'MID')  # now SENIOR/MID/JUNIOR
title = normalized_title   # "Senior Backend Engineer"

jd_level_text = f"Seniority: {level}. Title: {title}."
# e.g. "Seniority: SENIOR. Title: Senior Backend Engineer."
```

This gives the embedding model actual seniority vocabulary to work with. The `resume_embedding`
on the member side (career narrative) will now find meaningful alignment with seniority language
rather than just domain category text.

The field `jd_level` on `RequisitionData` is renamed conceptually from "role category" to
"seniority level" — its value is now `SENIOR`/`MID`/`JUNIOR` rather than `"Backend Engineer"`.

---

## 10. Proposed Fix — Mandatory Skills Fallback

When `mandatory_skills` is absent from the input, the LLM already tries to extract them from
`jd_text`. The current prompt instructs:

> "If skills are missing or incomplete, extract them from the `jd_text`."

However, the result is merged only when the LLM call succeeds. Add an explicit check after
LLM enrichment:

```python
# In requisition_parsing_node, after LLM merge:
if not enriched_jd.get("extracted_mandatory_skills"):
    logger.warning(
        "No mandatory skills extracted from JD or input. "
        "RAG BM25 filter and Node 5 mandatory gate will have no keywords."
    )
    # Do NOT default to [] silently — log the gap clearly so it is observable.
```

This does not change behavior but makes the gap **observable in logs** so operators can
identify requisitions where skill extraction failed and investigate the `jd_text` quality.

---

## 11. Files to Change

| File | Change Type | Summary |
|---|---|---|
| `src/app/ai/agents/requisition_parsing.py` | Enhancement | Add `level` to LLM prompt output schema; add 4-layer level inference after LLM call; wire `level` into `enriched_jd` |
| `src/app/ai/utils/embedding.py` | Fix | Change `jd_level_text` construction to use `SENIOR/MID/JUNIOR` level + role + title |
| `src/app/ai/agents/embedding.py` | 1-line | Pass `level` from `parsed_jd` into `RequisitionData.jd_level` field |

**No changes to:**
- `src/app/api/schemas/requisition.py` — API contract stays the same; optional fields remain optional
- `src/app/ai/utils/scoring.py` — reads `jd_level_similarity` unchanged; will benefit automatically
- `src/app/ai/utils/rag_retrieval.py` — reads `jd_level_vector` unchanged; will benefit automatically
- `src/app/ai/state.py` — `parsed_jd` is an untyped dict; adding `level` key requires no schema change

---

## 12. Risk and Rollback

| Change | Risk Level | Rollback |
|---|---|---|
| LLM prompt adds `level` field | Low — additive; existing fields unchanged | Remove `level` from prompt; fallback chain handles None |
| 4-layer level inference | Low — always produces JUNIOR/MID/SENIOR; no null propagation | Remove inference; hardcode `"MID"` default |
| `jd_level_text` uses SENIOR/MID/JUNIOR | Medium — shifts `jd_level_vector` semantics; affects `s_score` distribution | Add feature flag `embedding_use_level_text: bool = True`; revert text on False |
| Mandatory skills warning log | None — log only, no behavioral change | Remove log line |

The most impactful change is `jd_level_text`. Candidates who were previously passing the
semantic gate on domain similarity alone may score differently once the gate measures actual
seniority alignment. This is the intended behavior but should be validated against known
requisitions before deploying to production.

---

## 13. Acceptance Criteria

| # | Criterion |
|---|---|
| 1 | Level extracted from `jd_text` — "Senior Python Developer, 5+ years" → `"SENIOR"` |
| 2 | Level default — plain "Software Developer", no experience range → `"MID"` |
| 3 | `jd_level_text` contains SENIOR/MID/JUNIOR (not "Backend Engineer") |
| 4 | `full_jd_vector_sim` and `level_vector_sim` return meaningfully different values for the same candidate |
| 5 | Senior member ranks above junior with identical skills on a "Senior" requisition (requires real `resume_embedding` from cron pipeline; seed data falls back to general embedding) |
| 6 | Explicit `level` in API input is respected (Layer 1 LLM extraction takes priority over heuristics) |
