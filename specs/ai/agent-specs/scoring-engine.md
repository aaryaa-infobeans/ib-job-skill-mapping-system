# Agent Specification: Scoring Engine

**Version:** 1.2  
**Modified By:** CR-SCORE-003  
**Last Updated:** 2026-03-17  

## 1. Purpose
The Scoring Engine is a multi-stage agentic system that evaluates the fit between a candidate and a job description using role-specific logic, hard gates, and AI-driven boosts.

## 2. Scoring Stages

### Phase 0: Configuration
- Determine role type (**SENIOR**, **MID**, **JUNIOR**) based on:
  - Required experience in JD (months).
  - Candidate total experience (months).
  - Seniority thresholds defined in `settings.py`.

### Phase 1: Qualification Gate (Hard Filters)
- Apply mandatory thresholds to prevent low-quality matches:
  - **Senior**: Weighted Skill >= 20%, Semantic Similarity >= 30%
  - **Mid**: Weighted Skill >= 20%, Semantic Similarity >= 20%
  - **Junior**: Weighted Skill >= 15%, Semantic Similarity >= 15%
- Candidates failing gates are assigned a `fit_level` of "LOW" or "DISQUALIFIED".

### Phase 2: Holistic Scoring
- **Base Score** = `(Mandatory * w_m) + (Preferred * w_p) + (Semantic * w_s)`
- **Context Boost** = `min(context_factors_sum * w_c, 0.08)`
  - Includes: Location, Work Mode, Certifications, Title Match.
- **Penalty** = `-0.10` if Skill Family mismatch detected (e.g., Frontend candidate for AI role).

## 3. Role Configurations (from `settings.py`)

| Level | Mand. Weight | Pref. Weight | Sem. Weight | Context Weight | Experience Threshold |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SENIOR** | 0.50 | 0.20 | 0.25 | 0.05 | >= 96 months |
| **MID** | 0.40 | 0.20 | 0.25 | 0.15 | Default |
| **JUNIOR** | 0.30 | 0.30 | 0.25 | 0.15 | < 24 months |

## 4. State Mutations
- **Allowed**:
  - Sets `state.scoring_results` for retrieved candidates.
  - Updates `state.fit_analysis` for each candidate.
- **Forbidden**:
  - Must not modify raw requisition data.

## 5. Traceability
- **SRS Reference**: FR-4 (AI-driven matching and scoring)
- **CR Reference**: CR-SCORE-003 (Refined Scoring Logic)
