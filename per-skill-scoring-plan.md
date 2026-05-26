# Per-Skill Rating & Experience in Scoring

## Context

Items 1 and 2 of the hybrid search rollout are complete. Item 3 addresses a differentiation gap in Node 5 scoring: `_calculate_skill_group_score()` gives every matched skill a flat contribution of 1.0 regardless of the candidate's `rating` or `experience_in_months` on that skill. Both fields exist in `TeamMemberSkill` but are never fetched by the scoring query.

**Intended outcome:** Candidates with higher per-skill ratings and more experience rank above those with lower values when all other factors are equal. Profile-text-only matches (fallback when no skill ID is found) receive a partial-credit weight instead of the current full 1.0.

---

## Contribution Formula

Each matched skill's contribution is a **pre-blended scalar** computed in `matching_scoring.py` and stored in a `skill_ratings` dict keyed by `skill_id`:

```
norm_rating  = rating / 5.0          if rating is not None  else 1.0
norm_exp     = min(exp_months / CAP, 1.0)  if exp_months is not None else 1.0

contribution = (skill_rating_weight Ã— norm_rating) + (skill_exp_weight Ã— norm_exp)
```

**Default values (all configurable via settings):**
- `skill_rating_weight = 0.6`
- `skill_exp_weight = 0.4`
- `skill_exp_months_cap = 48`  (4 years = full experience credit)

**Null handling â€” `None` field â†’ 0.5 (neutral/unknown) for that component:**

| rating | exp_months | contribution |
|--------|------------|--------------|
| 5      | 48+        | 0.6Ã—1.0 + 0.4Ã—1.0 = **1.0** |
| 3      | 24         | 0.6Ã—0.6 + 0.4Ã—0.5 = **0.56** |
| None   | 24         | 0.6Ã—0.5 + 0.4Ã—0.5 = **0.50** |
| 4      | None       | 0.6Ã—0.8 + 0.4Ã—0.5 = **0.68** |
| None   | None       | 0.6Ã—0.5 + 0.4Ã—0.5 = **0.50** â† unknown candidate scores below a fully-rated one |

This pre-blended value (always in [0.0, 1.0]) is stored in `skill_ratings[skill_id]` and passed to `_calculate_skill_group_score()`, which treats it as a contribution scalar â€” no blending logic inside the scoring function itself.

---

## Data Flow After Changes

```
DB: team_member_skill {skill_id, rating, experience_in_months}
        |
        v
matching_scoring.py â€” single query, three derivations:
  member_skill_ids = [s.skill_id for s in skill_records]
  skill_ratings    = {s.skill_id: _skill_contribution(s) for s in skill_records}
                     where _skill_contribution() applies the blend formula above
        |
        v
profile_data dict gains "skill_ratings": skill_ratings
        |
        v
scoring.py execute() extracts skill_ratings, passes to both
_calculate_skill_group_score() calls
        |
        v
_calculate_skill_group_score():
  ID match   â†’ contribution = max(skill_ratings[matched_id])  (default 1.0 if absent)
  Text match â†’ contribution = settings.profile_text_match_weight  (default 0.6)
  Missing    â†’ contribution = 0.0
  score = sum(contributions) / total  (was: len(matched) / total)
```

---

## Changes

### 1. `src/app/settings.py`

Add four fields after `scoring_blend_full_jd_weight` (line 151):

```python
# Per-skill contribution blend (rating + experience â†’ single scalar)
skill_rating_weight: float = 0.6       # weight of normalised rating in contribution
skill_exp_weight: float = 0.4          # weight of normalised experience in contribution
skill_exp_months_cap: int = 48         # experience months at which norm_exp = 1.0
profile_text_match_weight: float = 0.6 # contribution for text-only (no ID) matches
```

---

### 2. `src/app/ai/agents/matching_scoring.py`

#### A. Add a module-level helper function (after imports, before `matching_scoring_node`)

```python
def _skill_contribution(skill_record) -> float:
    """Blend normalised rating and experience into a single 0-1 contribution scalar.
    None fields default to 0.5 (neutral/unknown) â€” candidates with no metadata score
    below those with confirmed high ratings but above those with confirmed low ratings."""
    norm_rating = (skill_record.rating / 5.0) if skill_record.rating is not None else 0.5
    norm_exp = (
        min(skill_record.experience_in_months / settings.skill_exp_months_cap, 1.0)
        if skill_record.experience_in_months is not None
        else 0.5
    )
    return settings.skill_rating_weight * norm_rating + settings.skill_exp_weight * norm_exp
```

#### B. Replace the skill-ID list comprehension (lines 129â€“134)

**Remove:**
```python
member_skill_ids = [
    skill.skill_id 
    for skill in db.query(TeamMemberSkill)
    .filter(TeamMemberSkill.team_member_id == member.team_member_id)
    .all()
]
```

**Replace with (same number of DB round-trips):**
```python
skill_records = (
    db.query(TeamMemberSkill)
    .filter(TeamMemberSkill.team_member_id == member.team_member_id)
    .all()
)
member_skill_ids = [s.skill_id for s in skill_records]
skill_ratings = {s.skill_id: _skill_contribution(s) for s in skill_records}
```

#### C. Add `skill_ratings` to `profile_data` (lines 171â€“193)

```python
profile_data = {
    "skill_ids": member_skill_ids,
    "skill_ratings": skill_ratings,   # NEW â€” pre-blended contribution per skill_id
    "skill_names": member_skill_names,
    ...
}
```

---

### 3. `src/app/ai/utils/scoring.py`

#### A. `_calculate_skill_group_score()` â€” new signature + body (replaces lines 113â€“139)

```python
def _calculate_skill_group_score(
    self,
    member_skill_ids: List[str],
    skill_alternatives: Dict[str, List[str]],
    profile_text: str = "",
    skill_ratings: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Two-pass skill group matching: skill ID check then profile text fallback.
    When skill_ratings is provided: ID matches use max(contribution of matched ids),
    text-only matches use settings.profile_text_match_weight.
    When skill_ratings is None all contributions are 1.0 (backward-compatible)."""
    if not skill_alternatives:
        return {"score": 1.0, "matched": [], "missing": []}

    member_skills = set(member_skill_ids)
    p_text_lower = (profile_text or "").lower()
    matched, missing = [], []
    contribution_sum = 0.0

    for canonical, alt_ids in skill_alternatives.items():
        matched_ids = [sid for sid in alt_ids if sid in member_skills]
        if matched_ids:
            matched.append(canonical)
            if skill_ratings is not None:
                contribution = max(skill_ratings.get(sid, 1.0) for sid in matched_ids)
            else:
                contribution = 1.0
            contribution_sum += contribution
            continue

        group_name = self._get_skill_group(canonical)
        members = self.skill_groups.get(group_name, [canonical])
        found = self._skill_found_in_text(members, p_text_lower)
        if found:
            matched.append(canonical)
            contribution_sum += settings.profile_text_match_weight
        else:
            missing.append(canonical)

    total = len(skill_alternatives)
    return {"score": contribution_sum / total if total else 1.0, "matched": matched, "missing": missing}
```

#### B. `execute()` â€” extract and pass `skill_ratings` (around lines 265â€“296)

After `jd_text = profile_data.get("jd_text", "")` (line 268), insert:
```python
skill_ratings = profile_data.get("skill_ratings")
```

Pass `skill_ratings` as 4th arg to the mandatory call (lines 281â€“285):
```python
m_res = self._calculate_skill_group_score(
    profile_data.get("skill_ids", []),
    mandatory_alternatives,
    profile_text,
    skill_ratings,
)
```

Pass `skill_ratings` as 4th arg to the preferred call (lines 291â€“295):
```python
_p = self._calculate_skill_group_score(
    profile_data.get("skill_ids", []),
    _pref_alts,
    profile_text,
    skill_ratings,
)
```

---

### 4. `tests/unit/test_scoring_agent.py`

`test_skill_group_score_id_match` (lines 13â€“18) â€” **no change needed**; `skill_ratings=None` default â†’ `contribution = 1.0`, score stays 1.0.

**Add four new tests** after the existing `test_skill_group_score_id_match`:

```python
def test_skill_group_score_rating_and_exp_weighted(scoring_agent):
    """ID-matched skill with pre-blended contribution 0.56 (rating=3, exp=24m)."""
    # 0.6*(3/5) + 0.4*(24/48) = 0.36 + 0.20 = 0.56
    res = scoring_agent._calculate_skill_group_score(
        ["PYTHON_ID"],
        {"Python": ["PYTHON_ID"]},
        skill_ratings={"PYTHON_ID": 0.56},
    )
    assert res["score"] == approx(0.56)
    assert res["matched"] == ["Python"]
    assert res["missing"] == []


def test_skill_group_score_rating_differentiates_candidates(scoring_agent):
    """Two candidates with same skill but different blended contributions score differently."""
    alts = {"Python": ["PYTHON_ID"]}
    res_high = scoring_agent._calculate_skill_group_score(
        ["PYTHON_ID"], alts, skill_ratings={"PYTHON_ID": 1.0}   # rating=5, exp=48+
    )
    res_low = scoring_agent._calculate_skill_group_score(
        ["PYTHON_ID"], alts, skill_ratings={"PYTHON_ID": 0.4}   # lower rating+exp
    )
    assert res_high["score"] == approx(1.0)
    assert res_low["score"] == approx(0.4)
    assert res_high["score"] > res_low["score"]


def test_skill_group_score_none_fields_neutral(scoring_agent):
    """Both rating=None and exp=None â†’ contribution 0.5 (neutral), not 1.0."""
    # _skill_contribution returns 0.6*0.5 + 0.4*0.5 = 0.50 when both are None
    res = scoring_agent._calculate_skill_group_score(
        ["PYTHON_ID"],
        {"Python": ["PYTHON_ID"]},
        skill_ratings={"PYTHON_ID": 0.5},
    )
    assert res["score"] == approx(0.5)


def test_skill_group_score_profile_text_match_weight(scoring_agent):
    """Text-only match contributes profile_text_match_weight, not 1.0."""
    from app.settings import settings
    res = scoring_agent._calculate_skill_group_score(
        [],
        {"Python": ["PYTHON_ID"]},
        profile_text="senior python developer with 5 years experience",
        skill_ratings={},
    )
    assert res["score"] == approx(settings.profile_text_match_weight)
    assert res["matched"] == ["Python"]
    assert res["missing"] == []
```

Also add a unit test for `_skill_contribution` in `matching_scoring.py`:

```python
# In tests/unit/test_matching_scoring.py (new file or existing)
from app.ai.agents.matching_scoring import _skill_contribution
from unittest.mock import MagicMock

def test_skill_contribution_both_present():
    skill = MagicMock(rating=3, experience_in_months=24)
    result = _skill_contribution(skill)
    assert result == approx(0.6 * 0.6 + 0.4 * 0.5)  # 0.36 + 0.20 = 0.56

def test_skill_contribution_rating_none():
    # None rating â†’ neutral 0.5; experience still used
    skill = MagicMock(rating=None, experience_in_months=24)
    result = _skill_contribution(skill)
    assert result == approx(0.6 * 0.5 + 0.4 * 0.5)  # 0.30 + 0.20 = 0.50

def test_skill_contribution_exp_none():
    # None exp â†’ neutral 0.5; rating still used
    skill = MagicMock(rating=4, experience_in_months=None)
    result = _skill_contribution(skill)
    assert result == approx(0.6 * 0.8 + 0.4 * 0.5)  # 0.48 + 0.20 = 0.68

def test_skill_contribution_both_none():
    # Both None â†’ 0.5 neutral; scores below a fully-rated candidate
    skill = MagicMock(rating=None, experience_in_months=None)
    result = _skill_contribution(skill)
    assert result == approx(0.6 * 0.5 + 0.4 * 0.5)  # 0.50
```

---

## Edge Cases

| Scenario | Behaviour |
|---|---|
| `rating=None, exp=None` | `0.6Ã—0.5 + 0.4Ã—0.5 = 0.50` â€” neutral; ranks below high-rated, above low-rated |
| `rating=None, exp=24m` | `0.6Ã—0.5 + 0.4Ã—0.5 = 0.50` â€” neutral rating + mid experience |
| `rating=4, exp=None` | `0.6Ã—0.8 + 0.4Ã—0.5 = 0.68` â€” solid rating; neutral exp |
| `rating=0, exp=0` | `0.6Ã—0.0 + 0.4Ã—0.0 = 0.0` â€” zero proficiency; skill in `matched` list but zero contribution |
| `exp_months > cap (48)` | `min(exp/48, 1.0)` â€” capped at 1.0, no over-credit for very long tenure |
| Multiple alt_ids matched | `max(skill_ratings[sid] for sid in matched_ids)` â€” best contribution wins |
| Member has no skills | `skill_records = []`; all skills fall to text-match path |
| `skill_ratings=None` (old call paths) | backward-compatible: `contribution = 1.0` for all ID matches |

---

## Backward Compatibility

- `skill_ratings=None` default in `_calculate_skill_group_score()` â†’ all existing unit tests (`test_execute_full_match`, `test_execute_mid_role`) produce identical scores (contribution = 1.0 in the `skill_ratings is None` branch, unchanged).
- The neutral-0.5 default only activates once `matching_scoring.py` is updated and starts passing actual `skill_ratings` dicts. Members with no rating/exp data will see their `mandatory_score` drop to ~0.50 per unrated skill â€” expected and intentional.
- Text-match behavior changes only when `skill_ratings` is not None. Until then, text matches still contribute 1.0.

---

## Files Modified

| File | Change |
|---|---|
| [src/app/settings.py](src/app/settings.py) | Add `skill_rating_weight`, `skill_exp_weight`, `skill_exp_months_cap`, `profile_text_match_weight` |
| [src/app/ai/agents/matching_scoring.py](src/app/ai/agents/matching_scoring.py) | Add `_skill_contribution()` helper; fetch full skill records; build `skill_ratings` dict; add to `profile_data` |
| [src/app/ai/utils/scoring.py](src/app/ai/utils/scoring.py) | New `skill_ratings` param + contribution-sum logic in `_calculate_skill_group_score()`; pass through in `execute()` |
| [tests/unit/test_scoring_agent.py](tests/unit/test_scoring_agent.py) | Add 4 new rating/text-match tests |
| [tests/unit/test_matching_scoring.py](tests/unit/test_matching_scoring.py) | Add 4 unit tests for `_skill_contribution()` null-handling |

---

## Verification

1. `pytest tests/unit/test_scoring_agent.py tests/unit/test_matching_scoring.py -v` â€” all existing tests pass; 8 new tests pass.
2. Construct two `profile_data` dicts identical except `skill_ratings={"PYTHON_ID": 1.0}` vs `{"PYTHON_ID": 0.56}`, call `scoring_agent.execute()` on both â€” assert `mandatory_score` differs.
3. After an end-to-end API call, check that `score_breakdown.mandatory_skills_group` reflects sub-1.0 values for members with incomplete skill metadata.

---

## Addendum: Certification Expiry Check

### Why

`TeamMemberSkillCertification` has `issued_date` and `valid_till` (both `Date`, nullable). Currently `_calculate_certification_score()` is binary â€” a cert either matches by name or it doesn't. An expired certification (i.e. `valid_till < today`) should not count as a match; the candidate no longer holds a valid credential.

Recency decay via `issued_date` is intentionally skipped â€” the cert score is capped inside an 8% context contribution, making fine-grained decay noise rather than signal.

### Null handling

| valid_till | Behaviour |
|---|---|
| Future date | Valid â†’ counts as matched (1.0 contribution) |
| Past date | Expired â†’ treated as not held (moves to `missing` + `expired` audit list) |
| None | No expiry tracked (e.g. degree, permanent cert) â†’ valid â†’ counts as matched |

### Data flow

```
DB: team_member_skill_certification {certificate, valid_till, ...}
        |
        v
matching_scoring.py â€” single query, two derivations:
  member_certs  = [c.certificate for c in cert_records if c.certificate]
  cert_validity = {
      c.certificate: (c.valid_till is None or c.valid_till >= date.today())
      for c in cert_records if c.certificate
  }
        |
        v
profile_data gains "cert_validity": cert_validity
        |
        v
scoring.py execute() extracts cert_validity, passes to _calculate_certification_score()
        |
        v
_calculate_certification_score():
  for each required cert:
    not in member_certs       â†’ missing
    in member_certs + valid   â†’ matched
    in member_certs + expired â†’ expired (surfaced separately) + counted as missing for score
  score = len(matched) / len(required_certs)
  returns: {"score", "matched", "missing", "expired"}
```

### Changes

#### 1. `src/app/ai/agents/matching_scoring.py`

Replace the current cert list comprehension:

```python
# Current
member_certs = [
    cert.certificate
    for cert in db.query(TeamMemberSkillCertification)
    .filter(TeamMemberSkillCertification.team_member_id == member.team_member_id)
    .all()
]
```

With a single query + two derivations:

```python
from datetime import date

cert_records = (
    db.query(TeamMemberSkillCertification)
    .filter(TeamMemberSkillCertification.team_member_id == member.team_member_id)
    .all()
)
member_certs = [c.certificate for c in cert_records if c.certificate]
cert_validity = {
    c.certificate: (c.valid_till is None or c.valid_till >= date.today())
    for c in cert_records if c.certificate
}
```

Add to `profile_data`:

```python
profile_data = {
    ...
    "certifications": member_certs,
    "cert_validity": cert_validity,   # NEW
    ...
}
```

#### 2. `src/app/ai/utils/scoring.py` â€” `_calculate_certification_score()`

New signature (replaces lines 224â€“229):

```python
def _calculate_certification_score(
    self,
    member_certs: List[str],
    required_certs: List[str],
    cert_validity: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    if not required_certs:
        return {"score": 1.0, "matched": [], "missing": [], "expired": []}
    matched, missing, expired = [], [], []
    for c in required_certs:
        if c not in member_certs:
            missing.append(c)
        elif cert_validity is not None and not cert_validity.get(c, True):
            expired.append(c)   # has cert but it lapsed
        else:
            matched.append(c)
    score = len(matched) / len(required_certs)
    return {"score": score, "matched": matched, "missing": missing + expired, "expired": expired}
```

#### 3. `src/app/ai/utils/scoring.py` â€” `execute()`

Extract `cert_validity` after `skill_exp_months`:

```python
cert_validity = profile_data.get("cert_validity")
```

Pass to `_calculate_context_boost()` via `profile_data` (already passed as-is), **and** pass explicitly when calling `_calculate_certification_score()` inside `_calculate_context_boost()`:

```python
# Inside _calculate_context_boost():
cert_res = self._calculate_certification_score(
    profile_data.get("certifications", []),
    profile_data.get("required_certifications", []),
    profile_data.get("cert_validity"),   # NEW
)
```

#### 4. `src/app/ai/utils/models.py` â€” `ScoringBreakdown`

Add one field:

```python
certification_expired: List[str] = []
```

#### 5. `src/app/ai/utils/scoring.py` â€” `detailed` ScoringBreakdown construction

Pass `certification_expired`:

```python
detailed = ScoringBreakdown(
    ...
    certification_matched=cert_res["matched"],
    certification_missing=cert_res["missing"],
    certification_expired=cert_res["expired"],   # NEW
    ...
)
```

#### 6. `src/app/ai/agents/matching_scoring.py` â€” `match_reasons`

Expose expired certs in the API response:

```python
"match_reasons": {
    ...
    "certification_expired": _sanitize_skill_list(
        scoring_result.detailed_breakdown.certification_expired
    ),
    ...
}
```

### Tests to add (`tests/unit/test_scoring_agent.py`)

```python
def test_certification_score_expired_not_counted(scoring_agent):
    """An expired cert is not counted as a match; score drops."""
    res = scoring_agent._calculate_certification_score(
        member_certs=["AWS-SAA"],
        required_certs=["AWS-SAA"],
        cert_validity={"AWS-SAA": False},   # expired
    )
    assert res["score"] == approx(0.0)
    assert res["matched"] == []
    assert "AWS-SAA" in res["missing"]
    assert res["expired"] == ["AWS-SAA"]


def test_certification_score_valid_cert_counted(scoring_agent):
    """A valid cert (future expiry) counts as matched."""
    res = scoring_agent._calculate_certification_score(
        member_certs=["AWS-SAA"],
        required_certs=["AWS-SAA"],
        cert_validity={"AWS-SAA": True},
    )
    assert res["score"] == approx(1.0)
    assert res["matched"] == ["AWS-SAA"]
    assert res["expired"] == []


def test_certification_score_no_expiry_counted(scoring_agent):
    """A cert with no valid_till (None â†’ True in cert_validity) counts as matched."""
    res = scoring_agent._calculate_certification_score(
        member_certs=["PMP"],
        required_certs=["PMP"],
        cert_validity={"PMP": True},   # valid_till was None â†’ True
    )
    assert res["score"] == approx(1.0)
    assert res["matched"] == ["PMP"]


def test_certification_score_no_validity_dict_backward_compat(scoring_agent):
    """cert_validity=None falls back to original binary behavior."""
    res = scoring_agent._calculate_certification_score(
        member_certs=["AWS-SAA"],
        required_certs=["AWS-SAA"],
    )
    assert res["score"] == approx(1.0)
    assert res["matched"] == ["AWS-SAA"]
```

### Edge Cases

| Scenario | Behaviour |
|---|---|
| `valid_till = None` | `cert_validity[name] = True` â€” no expiry â†’ counted as valid |
| `valid_till` in past | `cert_validity[name] = False` â€” expired â†’ score 0, appears in `expired` + `missing` |
| `cert_validity = None` (no dict passed) | Backward-compatible: `cert_validity.get(c, True)` is never called; cert counted if name matches |
| `certificate = None` in DB row | Filtered out by `if c.certificate` guard in both `member_certs` and `cert_validity` |
| Required cert not in member_certs at all | Goes into `missing` (unchanged from current behaviour) |

### Files Modified (addendum)

| File | Change |
|---|---|
| [src/app/ai/agents/matching_scoring.py](src/app/ai/agents/matching_scoring.py) | Replace cert list comprehension with full record fetch; build `cert_validity` dict; add to `profile_data`; expose `certification_expired` in `match_reasons` |
| [src/app/ai/utils/scoring.py](src/app/ai/utils/scoring.py) | Update `_calculate_certification_score()` signature + logic; pass `cert_validity` from `_calculate_context_boost()`; populate `certification_expired` in `ScoringBreakdown` |
| [src/app/ai/utils/models.py](src/app/ai/utils/models.py) | Add `certification_expired: List[str] = []` to `ScoringBreakdown` |
| [tests/unit/test_scoring_agent.py](tests/unit/test_scoring_agent.py) | Add 4 cert expiry tests |

---

## Addendum 2: Context Score Dynamic Weighting

### Problem

`_calculate_context_boost()` uses **fixed weights** for all five sub-signals regardless of
whether the JD actually constrains them. For a JD with `location=["Bangalore","Remote"]`,
`work_mode=["Remote","Hybrid"]`, and no required certifications:

- `cert_score = 1.0` for every candidate (no certs required â†’ free default)
- `loc_score = 1.0` for every candidate ("remote" in list â†’ line 277 short-circuits to 1.0)
- `mode_score = 1.0` for most candidates (both Remote and Hybrid accepted)

Result: `context_score = 0.8` and `context_contribution = 0.04` is **identical for all
candidates**. The 5% context weight adds a flat constant to every profile score and
provides zero differentiation.

### Root Cause

```python
# Current â€” denominator is always the same regardless of which criteria apply
total_context_weight = (
    settings.weight_experience    +   # 0.10
    settings.weight_certification +   # 0.10  â† spent even when no certs required
    settings.weight_location      +   # 0.10  â† spent even when remote is accepted
    settings.weight_work_mode     +   # 0.10  â† spent even when all modes accepted
    settings.weight_jd_text           # 0.05
)   # = 0.45 always
```

### Fix â€” Exclude non-constraining criteria from both numerator and denominator

A criterion is **active** (contributes to both `active_sum` and `active_weight`) only when
the JD actually constrains it. When inactive, its weight is redistributed proportionally to
the remaining active criteria.

| Criterion | Active when |
|---|---|
| Experience | `min_experience_months` is set in parsed JD |
| Certification | `required_certifications` list is non-empty |
| Location | At least one physical location in `required_locations` (i.e. not only "Remote"/"Any") |
| Work mode | Exactly one work mode required (multiple accepted = no real constraint) |
| Title | Always active (designation match is always a differentiator) |

### Changes

#### `src/app/ai/utils/scoring.py` â€” `_calculate_context_boost()` (replaces lines 181â€“234)

```python
def _calculate_context_boost(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Dynamic context scoring: only criteria the JD actually constrains are weighted.
    Non-constraining criteria are excluded from both numerator and denominator so their
    weight flows to the criteria that can actually differentiate candidates."""

    active_sum = 0.0
    active_weight = 0.0

    # --- Experience ---
    exp_score = self._calculate_experience_score(
        profile_data.get("experience_months", 0),
        profile_data.get("min_experience_months"),
        profile_data.get("max_experience_months"),
    )
    if profile_data.get("min_experience_months"):
        active_sum    += exp_score * settings.weight_experience
        active_weight += settings.weight_experience

    # --- Certification ---
    cert_res = self._calculate_certification_score(
        profile_data.get("certifications", []),
        profile_data.get("required_certifications", []),
        profile_data.get("cert_validity"),
    )
    if profile_data.get("required_certifications"):
        active_sum    += cert_res["score"] * settings.weight_certification
        active_weight += settings.weight_certification

    # --- Location ---
    _VIRTUAL_LOCS = {"remote", "any", "wfh", "anywhere", "global", "worldwide"}
    required_locations = profile_data.get("required_locations", [])
    physical_locs = [l for l in required_locations if l.strip().lower() not in _VIRTUAL_LOCS]
    loc_score = self._calculate_location_score(
        profile_data.get("location"), required_locations
    )
    if physical_locs:   # only constraining if at least one physical location is required
        active_sum    += loc_score * settings.weight_location
        active_weight += settings.weight_location

    # --- Work mode ---
    required_work_modes = profile_data.get("required_work_modes", [])
    mode_score = self._calculate_work_mode_score(
        profile_data.get("work_mode"), required_work_modes
    )
    if len(required_work_modes) == 1:   # single mode = real constraint; multiple = flexible
        active_sum    += mode_score * settings.weight_work_mode
        active_weight += settings.weight_work_mode

    # --- Title â€” always active ---
    jd_text = profile_data.get("jd_text") or ""
    lines = jd_text.splitlines()
    jd_title = lines[0].lower() if lines else ""
    if "title" in profile_data:
        jd_title = profile_data.get("title", "").lower()
    member_desig = (profile_data.get("designation") or "").lower()
    title_score = 0.0
    if jd_title and member_desig:
        if jd_title in member_desig or member_desig in jd_title:
            title_score = 1.0
    active_sum    += title_score * settings.weight_jd_text
    active_weight += settings.weight_jd_text

    aggregate = active_sum / active_weight if active_weight > 0 else 0.0

    return {
        "score": aggregate,
        "exp_score": exp_score,
        "cert_res": cert_res,
        "loc_score": loc_score,
        "mode_score": mode_score,
    }
```

### Before / After for the example JD

JD: `location=["Bangalore","Remote"]`, `work_mode=["Remote","Hybrid"]`, no certs,
`min_experience_months=60`.

| Criterion | Active? | Score | Weight used |
|---|---|---|---|
| Experience | Yes (`min=60m`) | 1.0 | 0.10 |
| Certification | **No** (none required) | â€” | 0 |
| Location | **No** (only Remote â†’ virtual) | â€” | 0 |
| Work mode | **No** (2 modes â†’ flexible) | â€” | 0 |
| Title | Yes (always) | 0.0 | 0.05 |

```
active_sum    = 1.0Ã—0.10 + 0.0Ã—0.05 = 0.10
active_weight = 0.10 + 0.05         = 0.15
context_score = 0.10 / 0.15         = 0.667
```

Now candidates with experience below the minimum will score differently from those who meet
it, and title matches produce a real uplift â€” instead of everyone getting 0.8 flat.

### Edge Cases

| Scenario | Behaviour |
|---|---|
| No active criteria at all (no min exp, no certs, remote-only, flexible mode, no title) | `active_weight = 0` â†’ `aggregate = 0.0`; context contributes nothing (correct: JD has no context constraints) |
| JD requires exactly one location, no remote | Location is active and differentiates by city |
| JD requires only "WFO" | Work mode is active (single mode constraint) |
| JD has no experience requirement | Experience excluded; weight redistributed to title |

### Tests to add (`tests/unit/test_scoring_agent.py`)

```python
def test_context_boost_excludes_inactive_criteria(scoring_agent):
    """When cert, location, and work_mode are unconstrained, only exp and title are active."""
    profile_data = {
        "experience_months": 72,
        "min_experience_months": 60,      # active â€” candidate exceeds it
        "max_experience_months": None,
        "certifications": [],
        "required_certifications": [],    # inactive
        "location": "Bangalore",
        "required_locations": ["Remote"], # virtual only â†’ inactive
        "work_mode": "wfh",
        "required_work_modes": ["Remote", "Hybrid"],  # multiple â†’ inactive
        "designation": "Staff Engineer",
        "jd_text": "Senior Backend Engineer",
        "title": "Senior Backend Engineer",
    }
    result = scoring_agent._calculate_context_boost(profile_data)
    # active_weight = weight_experience(0.10) + weight_jd_text(0.05) = 0.15
    # active_sum    = 1.0*0.10 + 0.0*0.05 = 0.10  (title doesn't match)
    assert result["score"] == approx(0.10 / 0.15)


def test_context_boost_all_criteria_active(scoring_agent):
    """All five criteria active and satisfied â†’ context_score = 1.0."""
    profile_data = {
        "experience_months": 72,
        "min_experience_months": 60,
        "max_experience_months": None,
        "certifications": ["AWS-SAA"],
        "required_certifications": ["AWS-SAA"],
        "location": "Bangalore",
        "required_locations": ["Bangalore"],   # physical â†’ active
        "work_mode": "wfo",
        "required_work_modes": ["WFO"],        # single mode â†’ active
        "designation": "Senior Backend Engineer",
        "jd_text": "",
        "title": "Senior Backend Engineer",
    }
    result = scoring_agent._calculate_context_boost(profile_data)
    assert result["score"] == approx(1.0)


def test_context_boost_no_active_criteria(scoring_agent):
    """No constraints at all â†’ active_weight=0 â†’ score=0.0, not an error."""
    profile_data = {
        "experience_months": 24,
        "min_experience_months": None,        # no min exp
        "required_certifications": [],
        "required_locations": ["Remote"],     # virtual
        "required_work_modes": ["Remote", "Hybrid"],
        "designation": "",
        "jd_text": "",
        "title": "",
    }
    result = scoring_agent._calculate_context_boost(profile_data)
    assert result["score"] == approx(0.0)
```

### Files Modified (addendum 2)

| File | Change |
|---|---|
| [src/app/ai/utils/scoring.py](src/app/ai/utils/scoring.py) | Replace fixed-weight `_calculate_context_boost()` with dynamic active-criterion weighting |
| [tests/unit/test_scoring_agent.py](tests/unit/test_scoring_agent.py) | Add 3 dynamic context boost tests |

---

