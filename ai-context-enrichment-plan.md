# AI Candidate Context Enrichment

## Context

Items 1–3 of the hybrid search rollout are complete, including Addendum 1 (cert expiry) and
Addendum 2 (dynamic context weighting). This item addresses a correctness gap in the AI
evaluation layer: `get_ai_fit_confidence()` receives only `profile_text` — a prose composite
built at embedding time — and has no visibility into the structured DB fields that the
deterministic scorer already uses.

**Prerequisites (both now met):**
- Item 3: `skill_records` fetched with `rating` and `experience_in_months` per skill
- Addendum 1: `cert_records` fetched with `valid_till` per certification

---

## Problem

`get_ai_fit_confidence()` receives only `jd_text` and `profile_text`. `profile_text` is a
composite of `skills_text + certifications_text + resume_text` built at embedding time
([embedding_processor.py:318](../../ib-job-skill-mapping-system/src/app/cron/embedding/embedding_processor.py#L318))
— but it contains **no structured signal**: no per-skill ratings, no experience months, no
certification validity status.

This causes two concrete problems:

### 1. AI ↔ DB contradiction

The LLM reads prose like "Python developer" and says "limited Python experience". The DB
shows `rating=2/5, exp=6m` — which explains *why* the score is 0.47 — but the LLM never
saw those numbers. Both signals appear side-by-side in `match_reasons` with no explanation,
confusing API consumers who see `mandatory_matched: ["Python", "FastAPI", "PostgreSQL"]`
alongside `ai_reasoning: "candidate shows limited experience with the required stack"`.

### 2. Stale text vs live DB

`profile_text` is rebuilt only when the embedding cron runs. If a candidate's skills are
updated in `TeamMemberSkill` after the last cron run, DB scoring reflects the current state
but the LLM reasons from the old snapshot.

---

## What NOT to send to the LLM

| Data | Why excluded |
|---|---|
| Allocation / project assignments | Evaluated deterministically by `evaluate_availability()` — LLM reasoning introduces hallucination risk |
| Member name, email, team_member_id | PII / internal identifiers |
| Raw DB row dumps | Noise — nulls, internal metadata, IDs the LLM cannot interpret |
| Full resume text again | Already inside `profile_text`; duplicating inflates tokens without benefit |
| Raw `valid_till` / `issued_date` dates | Pre-process to active/expired label before sending |

---

## Structured Context Block

A structured block appended to `profile_text` before calling the LLM:

```
--- Structured Candidate Data ---
Designation: Senior Software Engineer
Total Experience: 9y 8m

Skills on record:
  - WebMethods: 4/5, 5y 2m
  - Python: 2/5, 6m
  - FastAPI: 2/5, 4m
  - PostgreSQL: 3/5, 2y 0m

Active Certifications:
  WebMethods Certified Developer
```

With this context the LLM will produce: "Python present but only 6 months / rating 2/5" —
aligning with `mandatory_score: 0.47` instead of contradicting `mandatory_matched`.

---

## Token Cost

```
Current per candidate:  ~1 200 tokens
After enrichment:       ~1 400–1 500 tokens  (+200–300)
Delta at $0.0001/1K:    ~$0.00002 per candidate
40 candidates/request:  ~$0.001 per request   ← negligible
```

---

## Data Flow

```
matching_scoring.py (per candidate loop)
  skill_records    (fetched by Item 3 — no new query)
  cert_records     (fetched by Addendum 1 — no new query)
  skill_name_map   (refactored from existing skill_names query — no extra round-trip)
        |
        ↓
  _build_candidate_context(member, skill_records, skill_name_map, cert_records, profile_text)
        |
        ↓  returns enriched_context string
        |
  get_ai_fit_confidence(jd_text, enriched_context)   ← replaces plain profile_text
```

---

## Changes

### 1. `src/app/ai/agents/matching_scoring.py`

#### A. Refactor skill_names query to also return skill_id (no extra DB round-trip)

Replace the current `member_skill_names` query (around lines 160–167):

```python
# BEFORE
member_skill_names = [
    res.skill_name
    for res in db.query(SkillMaster.skill_name)
    .join(TeamMemberSkill, SkillMaster.skill_id == TeamMemberSkill.skill_id)
    .filter(TeamMemberSkill.team_member_id == member.team_member_id)
    .all()
]
```

Replace with:

```python
# AFTER
skill_name_rows = (
    db.query(SkillMaster.skill_id, SkillMaster.skill_name)
    .join(TeamMemberSkill, SkillMaster.skill_id == TeamMemberSkill.skill_id)
    .filter(TeamMemberSkill.team_member_id == member.team_member_id)
    .all()
)
member_skill_names = [r.skill_name for r in skill_name_rows]
skill_name_map = {r.skill_id: r.skill_name for r in skill_name_rows}
```

#### B. Add `_build_candidate_context()` helper (module-level, after `_sanitize_skill_list`)

```python
def _build_candidate_context(
    member,
    skill_records,
    skill_name_map: dict,
    cert_records,
    profile_text: str,
) -> str:
    """Build an enriched context string for LLM evaluation.
    Appends structured skill/cert data so AI reasoning aligns with DB scoring.
    No extra DB queries — reuses skill_records and cert_records already fetched."""
    from datetime import date

    skill_lines = []
    for s in skill_records:
        name = skill_name_map.get(s.skill_id, s.skill_id)
        rating = f"{s.rating}/5" if s.rating is not None else "unrated"
        if s.experience_in_months is not None:
            yrs, mths = divmod(s.experience_in_months, 12)
            exp = f"{yrs}y {mths}m" if yrs else f"{mths}m"
        else:
            exp = "duration unknown"
        skill_lines.append(f"  - {name}: {rating}, {exp}")

    active_certs = [
        c.certificate for c in cert_records
        if c.certificate and (c.valid_till is None or c.valid_till >= date.today())
    ]

    total_exp = member.experience_in_months or 0
    exp_str = f"{total_exp // 12}y {total_exp % 12}m"

    return (
        f"{profile_text}\n\n"
        f"--- Structured Candidate Data ---\n"
        f"Designation: {member.designation or 'N/A'}\n"
        f"Total Experience: {exp_str}\n\n"
        f"Skills on record:\n"
        f"{chr(10).join(skill_lines) if skill_lines else '  None on record'}\n\n"
        f"Active Certifications:\n"
        f"  {', '.join(active_certs) if active_certs else 'None'}"
    )
```

#### C. Replace `profile_text` with `enriched_context` when calling AI

```python
# BEFORE (around line 239)
ai_fit = get_ai_fit_confidence(jd_text, profile_text)

# AFTER
enriched_context = _build_candidate_context(
    member, skill_records, skill_name_map, cert_records, profile_text
)
ai_fit = get_ai_fit_confidence(jd_text, enriched_context)
```

---

### 2. `src/app/ai/utils/ai_confidence.py`

Update the prompt section label — the input now includes structured data, not just prose:

```python
# BEFORE
Candidate Profile:
{profile_text}

# AFTER
Candidate Profile and Structured Data:
{profile_text}
```

No other prompt changes required — the structured block is self-describing.

---

## Tests to Add

### `tests/unit/test_matching_scoring.py` (new file or existing)

```python
from app.ai.agents.matching_scoring import _build_candidate_context
from unittest.mock import MagicMock
from datetime import date, timedelta


def test_build_candidate_context_includes_skill_ratings():
    member = MagicMock(designation="Backend Engineer", experience_in_months=36)
    skill = MagicMock(skill_id="PY1", rating=3, experience_in_months=18)
    cert = MagicMock(certificate="AWS-SAA", valid_till=None)  # no expiry → active
    skill_name_map = {"PY1": "Python"}

    result = _build_candidate_context(member, [skill], skill_name_map, [cert], "base profile")

    assert "Python: 3/5, 1y 6m" in result
    assert "AWS-SAA" in result
    assert "Designation: Backend Engineer" in result
    assert "3y 0m" in result


def test_build_candidate_context_excludes_expired_cert():
    member = MagicMock(designation="Engineer", experience_in_months=24)
    cert = MagicMock(certificate="OLD-CERT", valid_till=date.today() - timedelta(days=1))

    result = _build_candidate_context(member, [], {}, [cert], "base profile")

    assert "OLD-CERT" not in result
    assert "None" in result


def test_build_candidate_context_no_skills_no_certs():
    member = MagicMock(designation=None, experience_in_months=0)

    result = _build_candidate_context(member, [], {}, [], "base profile")

    assert "None on record" in result
    assert "None" in result


def test_build_candidate_context_unrated_skill():
    member = MagicMock(designation="Engineer", experience_in_months=12)
    skill = MagicMock(skill_id="SK1", rating=None, experience_in_months=None)
    skill_name_map = {"SK1": "Kubernetes"}

    result = _build_candidate_context(member, [skill], skill_name_map, [], "base")

    assert "Kubernetes: unrated, duration unknown" in result


def test_build_candidate_context_permanent_cert_included():
    """Cert with valid_till=None (permanent) must appear in active certs."""
    member = MagicMock(designation="Architect", experience_in_months=60)
    cert = MagicMock(certificate="PMP", valid_till=None)

    result = _build_candidate_context(member, [], {}, [cert], "")

    assert "PMP" in result
```

---

## Edge Cases

| Scenario | Behaviour |
|---|---|
| `skill_records` empty | Skill section shows "None on record" |
| All certs expired | Active Certifications shows "None" |
| `valid_till = None` on cert | Permanent cert → included as active |
| `experience_in_months = None` on skill | Shows "duration unknown" |
| `rating = None` on skill | Shows "unrated" |
| `designation = None` on member | Shows "N/A" |
| `profile_text` empty | Structured block still appended; LLM gets data even with no prose |
| `experience_in_months = 0` on member | Shows "0y 0m" — no crash |

---

## Acceptance Criteria

- `ai_reasoning` no longer contradicts `mandatory_matched` for candidates with low-rated skills
- Expired certifications do not appear in the structured block sent to the LLM
- Candidates with no skills or no certs produce valid context strings without errors
- No additional DB queries introduced (reuses `skill_records` from Item 3, `cert_records` from Addendum 1)
- All 5 new unit tests pass

---

## Files to Modify

| File | Change |
|---|---|
| [src/app/ai/agents/matching_scoring.py](../../ib-job-skill-mapping-system/src/app/ai/agents/matching_scoring.py) | Add `_build_candidate_context()` helper; refactor skill_names query to return `(skill_id, skill_name)`; pass enriched context to `get_ai_fit_confidence()` |
| [src/app/ai/utils/ai_confidence.py](../../ib-job-skill-mapping-system/src/app/ai/utils/ai_confidence.py) | Update prompt label from "Candidate Profile" to "Candidate Profile and Structured Data" |
| [tests/unit/test_matching_scoring.py](../../ib-job-skill-mapping-system/tests/unit/test_matching_scoring.py) | Add 5 unit tests for `_build_candidate_context()` |

---

## Estimated Effort

0.5 days — all prerequisite data is already fetched; this is a context assembly and prompt update.
