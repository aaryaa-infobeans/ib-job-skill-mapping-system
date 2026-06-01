# Scoring Mechanism — First Principles Design (Greenfield)

## Context

Designing a candidate scoring system from scratch using only the data available in the system.
No reference to existing implementation — pure reasoning from data signals to scoring architecture.

---

## Data Available Per Candidate

| Source | Fields |
|--------|--------|
| `TeamMember` | designation, experience_in_months, base_location, work_type, profile_type |
| `TeamMemberSkill` | skill_id, rating (1–10), experience_in_months per skill |
| `TeamMemberSkillCertification` | certificate, issuer, issued_date, valid_till, skill_id |
| `SkillMaster` → `CategoryMaster` | skill_name, category (Backend, Frontend, AI/ML, Cloud…) |
| `TeamMemberAllocation` | allocation_percentage, start_date, end_date |
| `TeamMemberEmbedding` | 3 × 768-dim vectors (resume, skills, certs) + raw text for each |
| `Feedback` | liked (bool), rating 1–5, comment, created_at per past match |
| `SkillOntology` | core_skill, enriched_terms (synonyms) |

## Data Available From the JD

mandatory_skills (IDs + ontology terms), preferred_skills, experience min/max months,
certifications_required, location, work_mode, level (JUNIOR/MID/SENIOR),
full jd_text, priority (HIGH/MEDIUM/LOW), expected_start_date, requisition_duration_month

---

## Guiding Principles

1. **Relevance over quantity** — experience in JD-relevant skills matters more than total career experience
2. **Depth over breadth** — knowing 4 skills deeply beats knowing 8 skills shallowly
3. **Continuous not binary** — avoid hard cliffs; use smooth degradation everywhere possible
4. **Context-conditional** — only score dimensions the JD actually constrains; unconstrained dims don't penalise
5. **Semantic fills gaps** — vector similarity catches what keyword matching misses; it is a complement, not a replacement
6. **Feedback closes the loop** — historical reviewer signal should improve rankings over time
7. **Availability is priority-dependent** — urgency of the JD determines how much availability matters

---

## Architecture: Four Stages

```
Stage 0: Hard Elimination (absolute disqualifiers)
    ↓
Stage 1: Core Score (the candidate-to-JD match quality)
    ↓
Stage 2: Contextual Modifiers (role fit, availability, feedback)
    ↓
Stage 3: Final Score = Core × Modifiers
```

---

## Stage 0 — Hard Elimination (Binary, Before Any Scoring)

These are the only reasons to fully exclude a candidate before computing any score.
Keep this list minimal — over-gating means good candidates never get evaluated.

**Eliminate if:**
- Candidate is not active (`is_active = FALSE`)
- Candidate covers **zero** mandatory skills (by ID, synonym, or semantic — all three checks must fail)

Everything else is a scoring matter, not an exclusion matter.
Specifically: low ratings, experience mismatch, location mismatch, expired certs → these reduce score, they do not eliminate.

---

## Stage 1 — Core Score

The core score has four components. Weight distribution varies by role level (see below).

### Component A: Mandatory Skill Score

This is the most important signal. For each mandatory skill required by the JD:

**Step 1 — Match detection (three passes, in order):**
1. Exact ID match: candidate has the skill_id in their skill list
2. Synonym match: candidate skill name appears in the skill's `enriched_terms` from SkillOntology
3. Semantic match: cosine similarity between JD mandatory skills embedding and candidate skills embedding ≥ threshold

**Step 2 — Contribution per matched skill:**
```
rating_norm   = skill.rating / 10.0              (1–10 scale → 0.1–1.0)
exp_norm      = min(skill.experience_in_months / 48, 1.0)   (cap at 4 years)
contribution  = 0.6 × rating_norm + 0.4 × exp_norm

# Semantic-only match (no DB record) gets a fixed moderate contribution
semantic_only_contribution = 0.40
```

Rationale for 60/40 blend: rating measures current proficiency (more important),
experience measures tenure with the skill (supporting signal).

**Step 3 — Depth check:**
A skill "contributes" only if `contribution ≥ 0.30` (roughly rating 3/10 + some experience).
Below that, the candidate technically has the skill but not meaningfully.

**Step 4 — Mandatory score:**
```
mandatory_score = sum(contribution_i for each matched skill) / len(mandatory_skills)
```

If no mandatory skills are specified by JD → mandatory_score = 1.0 (unconstrained)

---

### Component B: Preferred Skill Score

Identical calculation method to mandatory, but:
- Missing preferred skills do not disqualify (contribute 0, not a penalty)
- Lower overall weight in final score

```
preferred_score = sum(contributions) / len(preferred_skills)
```

If no preferred skills → preferred_score = 1.0

---

### Component C: Semantic Alignment Score

Two separate vector comparisons, blended:

**C1. Holistic fit** — full JD text embedding vs. candidate full profile embedding
- Captures: seniority tone, domain language, responsibilities alignment
- Similarity: `sim_full = 1 / (1 + L2_distance)`

**C2. Skill-level fit** — JD mandatory skills text embedding vs. candidate skills text embedding
- Captures: technical vocabulary alignment, even when exact IDs don't match
- Similarity: `sim_skills = 1 / (1 + L2_distance)`

```
semantic_score = 0.40 × sim_full + 0.60 × sim_skills
```

Rationale: skill-level alignment matters more than tone-level alignment for technical roles.

---

### Component D: Certification Score

For each required certification:

```
cert_score(c) =
  1.0                                    if cert present and valid (valid_till ≥ today or NULL)
  0.5 × exp(-months_since_expiry / 24)  if cert present but expired
  0.0                                    if cert absent
```

Decay rationale: a cert expired 6 months ago still signals knowledge (score ≈ 0.43).
One expired 3 years ago is nearly meaningless (score ≈ 0.09).

**Relevance weighting** — not all certs are equal for this JD:
```
weight(c) =
  1.5   if cert.skill_id is in mandatory_skill_ids
  1.0   if cert.skill_id is in preferred_skill_ids
  0.5   if cert.skill_id is unrelated to this JD
```

```
cert_score_final = sum(cert_score(c) × weight(c)) / sum(weight(c) for required_certs)
```

If no certifications required → cert_score_final = 1.0

---

### Core Score Combination

```
core_score = (
    w_mandatory × mandatory_score  +
    w_preferred × preferred_score  +
    w_semantic  × semantic_score   +
    w_cert      × cert_score_final
)
```

**Role-level weights:**

| Component | JUNIOR | MID  | SENIOR |
|-----------|--------|------|--------|
| Mandatory | 0.30   | 0.40 | 0.50   |
| Preferred | 0.25   | 0.20 | 0.15   |
| Semantic  | 0.30   | 0.25 | 0.25   |
| Cert      | 0.15   | 0.15 | 0.10   |

Rationale: Juniors are expected to grow into skills → preferred and semantic (potential signals)
weight more. Seniors are hired for proven depth → mandatory dominates.

---

## Stage 2 — Contextual Modifiers

These are multipliers applied to `core_score`. Each operates independently.
**Important:** a modifier only activates if the JD actually constrains that dimension.

---

### Modifier A: Relevant Experience Multiplier

Total experience is a weak signal. Relevant experience is the real signal.

```
relevant_exp_months = sum(
    skill.experience_in_months
    for skill in candidate_skills
    if skill.skill_id in (mandatory_skill_ids ∪ preferred_skill_ids)
)
```

```
if JD specifies min_experience_months:
    exp_ratio = relevant_exp_months / min_experience_months
    experience_multiplier = 0.70 + 0.30 × min(exp_ratio, 1.0)
    # Range: 0.70 (zero relevant exp) → 1.00 (meets or exceeds requirement)
else:
    experience_multiplier = 1.0   # JD doesn't constrain it → no penalty
```

Rationale: 0.70 floor means even a candidate with irrelevant-only experience doesn't get
zeroed out — their skill score still carries them. But 30% of their potential score is
gated on relevant domain experience.

---

### Modifier B: Skill Category Alignment Multiplier

Replaces any binary family penalty. Uses actual skill category data from the DB.

**Step 1 — Build JD category vector:**
```
For each mandatory skill in JD:
    category = SkillMaster.category via JOIN
    jd_categories[category] += 1
```

**Step 2 — Build candidate category vector (rating-weighted):**
```
For each skill in candidate profile:
    category = SkillMaster.category via JOIN
    candidate_categories[category] += (skill.rating / 10.0)
```

**Step 3 — Cosine similarity of the two category vectors:**
```
category_alignment = cosine_similarity(jd_categories, candidate_categories)
# 0.0 = completely different category profile, 1.0 = identical distribution
```

**Step 4 — Multiplier:**
```
category_multiplier = 0.80 + 0.20 × category_alignment
# Range: 0.80 (completely misaligned) → 1.00 (perfectly aligned)
```

Rationale: 0.80 floor because even a misaligned candidate isn't worthless if their skill
score is high. But a perfectly aligned one gets a 20% uplift.

---

### Modifier C: Seniority Alignment Multiplier

Candidate's level vs. JD's required level.

**Derive candidate level from two signals:**
```
# From experience
exp_level =
    "SENIOR"  if experience_in_months >= 96   (8 years)
    "JUNIOR"  if experience_in_months < 24    (2 years)
    "MID"     otherwise

# From designation text
desig_level =
    "SENIOR"  if designation contains: senior, sr, lead, principal, staff, architect, head
    "JUNIOR"  if designation contains: junior, jr, associate, intern, trainee, entry
    "MID"     otherwise

# Blend: designation overrides when decisive; fall back to experience
candidate_level = desig_level if desig_level != "MID" else exp_level
```

**Alignment multiplier:**
```
tier_distance = |rank(candidate_level) - rank(jd_level)|   # JUNIOR=0, MID=1, SENIOR=2

seniority_multiplier =
    1.00   if tier_distance == 0   (exact match)
    0.85   if tier_distance == 1   (one level off)
    0.65   if tier_distance == 2   (two levels off)
```

---

### Modifier D: Location and Work Mode Multiplier

Only activates when the JD constrains these dimensions.

```
location_score =
    1.0   if no physical location required (remote/virtual/any)
    1.0   if candidate base_location matches any required location
    0.0   if physical location required but candidate doesn't match

work_mode_score =
    1.0   if JD accepts multiple modes (flexible)
    1.0   if candidate work_type matches required mode
    0.0   if strict mode required and candidate doesn't match

# Only constrained dimensions contribute to context_score
context_score = mean(active dimension scores)
context_multiplier = 0.90 + 0.10 × context_score
# Range: 0.90 (fully mismatched on constrained dims) → 1.00 (fully matched)
```

---

### Modifier E: Availability Multiplier (Priority-Scaled)

```
availability_ratio = available_capacity / 100.0   (0.0 → 1.0)

priority_sensitivity =
    0.15   if JD priority == "HIGH"
    0.08   if JD priority == "MEDIUM"
    0.03   if JD priority == "LOW"

availability_multiplier = 1.0 - priority_sensitivity × (1.0 - availability_ratio)

# HIGH priority, 100% available:  multiplier = 1.00
# HIGH priority, 50% available:   multiplier = 0.925
# HIGH priority, 0% available:    multiplier = 0.85
# LOW priority:  barely matters   multiplier = 0.97–1.00
```

---

### Modifier F: Historical Feedback Prior (If Available)

```
feedback_rows = all past feedback records for this team_member_id

if len(feedback_rows) >= 2:
    # Recency-weighted average (exponential decay, half-life ≈ 6 months)
    weights = [exp(-days_since(f.created_at) / 180) for f in feedback_rows]
    weighted_rating = sum(f.rating × w for f, w in zip(rows, weights)) / sum(weights)
    feedback_score = weighted_rating / 5.0     (normalise to 0–1)

    feedback_multiplier = 0.95 + 0.10 × feedback_score
    # Range: 0.95 (consistently bad reviews) → 1.05 (consistently excellent reviews)
    # Small nudge only — never dominates, but good candidates float up over time
else:
    feedback_multiplier = 1.0   (insufficient data → neutral)
```

---

## Stage 3 — Final Score

```
final_score = core_score
            × experience_multiplier
            × category_multiplier
            × seniority_multiplier
            × context_multiplier
            × availability_multiplier
            × feedback_multiplier

final_score = clamp(final_score, 0.0, 1.0)
```

**Soft qualification gate (smooth, not a cliff):**

Instead of a hard pass/fail threshold, apply a sigmoid that smoothly suppresses
low mandatory-skill-coverage candidates without a sudden drop-off:

```
gate_value = 1 / (1 + exp(-15 × (mandatory_score - 0.25)))

final_score = final_score × gate_value
```

Behavior:
- mandatory_score = 0.05 → gate ≈ 0.05  (nearly excluded, very low coverage)
- mandatory_score = 0.25 → gate ≈ 0.50  (halved — borderline)
- mandatory_score = 0.45 → gate ≈ 0.95  (barely affected — solid coverage)
- mandatory_score = 0.65 → gate ≈ 0.99  (effectively no penalty)

---

## Score Breakdown Output (Per Candidate)

Every result should carry a full decomposition so rankings are explainable:

```json
{
  "final_score": 0.81,
  "core_score": 0.74,
  "mandatory_score": 0.88,
  "preferred_score": 0.60,
  "semantic_score": 0.71,
  "cert_score": 0.50,
  "modifiers": {
    "experience_multiplier": 0.94,
    "category_multiplier": 0.97,
    "seniority_multiplier": 1.00,
    "context_multiplier": 1.00,
    "availability_multiplier": 0.97,
    "feedback_multiplier": 1.03
  },
  "gate_value": 0.98,
  "mandatory_matched": ["Python", "FastAPI"],
  "mandatory_missing": ["Kubernetes"],
  "cert_breakdown": {
    "AWS Solutions Architect": {"score": 1.0, "status": "valid"},
    "CKA": {"score": 0.0, "status": "absent"}
  },
  "candidate_level": "MID",
  "jd_level": "MID",
  "relevant_exp_months": 38,
  "category_alignment": 0.85
}
```

---

## Why Multiplicative Modifiers, Not Additive

Additive formulas allow a very high score in one dimension to compensate for near-zero in another.
A candidate with 0 mandatory skills but great semantic similarity can still score 0.45 additively.

Multiplicative modifiers prevent false compensation — a weak modifier propagates to the final score.
But using a sigmoid gate (not a hard zero) ensures smooth behavior at boundaries, avoiding cliff drops.

The combination of **additive core** (skills + semantics, role-weighted) + **multiplicative modifiers**
(context, fit, availability) gives:
- Role-appropriate weighting of the core technical match
- Hard constraints that cannot be bought off by strength in other dimensions
- Smooth degradation rather than arbitrary pass/fail lines

---

## Full Signal Summary

| Component | Stage | Input Data | Active When |
|-----------|-------|------------|-------------|
| Mandatory skill score | Core | skill rating, exp, ontology, skill embedding | Always |
| Preferred skill score | Core | skill rating, exp, ontology | Always |
| Semantic alignment | Core | 2 × vector embeddings (full + skills) | Always |
| Certification score | Core | cert records, valid_till, issued_date, skill_id | JD requires certs |
| Relevant experience | Modifier | per-skill exp months vs JD min | JD sets min_exp |
| Category alignment | Modifier | SkillMaster.category_id + candidate skill ratings | Always |
| Seniority alignment | Modifier | designation text + experience months vs JD level | Always |
| Location / work mode | Modifier | base_location, work_type | JD constrains these |
| Availability | Modifier | available_capacity + JD priority | Always (scaled by priority) |
| Feedback prior | Modifier | feedback table, recency-weighted avg | ≥ 2 feedback rows exist |
| Soft gate | Sigmoid | mandatory_score | Always |
