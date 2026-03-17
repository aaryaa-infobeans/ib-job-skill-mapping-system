# Feature Specification: Scoring Logic and Embedding Transition Refinement

**Feature Branch**: `CR-SCORE-003-scoring-refinement`  
**Created**: 2026-03-17  
**Status**: Approved  
**CR ID**: CR-SCORE-003  

## 1. Overview

This change request formalizes the transition from a single-vector search to a granular multi-vector RAG strategy and matures the scoring engine from hardcoded values to dynamic, role-specific weights and hard gates.

### 1.1 Problem Statement
The previous scoring logic used uniform weights across all seniority levels and relied on a single embedding vector for all semantic comparisons. This led to:
1.  **Seniority Mismatch**: Senior roles require different weighting (e.g., more emphasis on mandatory skills) than Junior roles.
2.  **Semantic Imprecision**: A single vector combining resume, skills, and certs dilutes the specific matching quality for individual requirements.
3.  **Lack of Guardrails**: No hard gates existed to disqualify candidates who failed basic technical pillars.

## 2. User Scenarios & Testing

### User Story 1 - Role-Specific Scoring (Priority: P1)
As a recruiter, I want the system to automatically adjust scoring weights based on candidate seniority (SENIOR, MID, JUNIOR).

**Acceptance Scenarios**:
1. **Given** a Senior Python Developer JD, **When** a candidate with 10 years experience is scored, **Then** mandatory skills should contribute 50% to the base score.
2. **Given** a Junior role, **When** a candidate with 1 year experience is scored, **Then** mandatory skills should only contribute 30% to account for potential growth.

### User Story 2 - Technical Hard Gates (Priority: P1)
As a hiring manager, I want the system to disqualify candidates who fall below a minimum technical skill threshold, regardless of their other scores.

**Acceptance Scenarios**:
1. **Given** a Senior role, **When** a candidate matches less than 20% of mandatory skill groups, **Then** they should be marked as "Disqualified" or "LOW" fit with a gate failure reason.

### User Story 3 - Multi-Vector Semantic Retrieval (Priority: P2)
As a system architect, I want semantic search to compare JD skills against candidate skills and JD title against candidate resumes separately.

**Acceptance Scenarios**:
1. **Given** a multi-vector index, **When** a search is performed, **Then** `skills_embedding` is used for skill similarity and `resume_embedding` is used for role/experience similarity.

## 3. Requirements

### 3.1 Functional Requirements
- **FR-001**: System MUST determine role level (SENIOR | MID | JUNIOR) based on JD level text or candidate experience years.
- **FR-002**: System MUST apply role-specific weights for Mandatory, Preferred, Semantic, and Context scores.
- **FR-003**: System MUST enforce hard gates (`min_skill_weighted` and `min_semantic`) per role level.
- **FR-004**: System MUST cap the total Context Support Boost at 8% (0.08) of the final score.
- **FR-005**: System MUST apply a `-0.10` penalty for "family mismatches" (e.g., frontend profile for backend role).
- **FR-006**: System MUST utilize `google/embeddinggemma-300m` as the primary local embedding model (768 dimensions).
- **FR-007**: System MUST support multi-vector routing (`mandatory_sim` -> `skills_embedding`, `jd_level_sim` -> `resume_embedding`).

### 3.2 Technical Specifications

#### Role Configuration Matrix
| Role Level | Experience Threshold | Mand. Weight | Pref. Weight | Sem. Weight | Context Weight | Min Skill Gate | Min Sem. Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SENIOR** | >= 96 months | 0.50 | 0.20 | 0.25 | 0.05 | 0.20 | 0.30 |
| **MID** | Default | 0.40 | 0.20 | 0.25 | 0.15 | 0.20 | 0.20 |
| **JUNIOR** | < 24 months | 0.30 | 0.30 | 0.25 | 0.15 | 0.15 | 0.15 |

#### Scoring Formula
`Final Score = (Mandatory * w_m) + (Preferred * w_p) + (Semantic * w_s) + min(Context_Contribution, 0.08) + Penalty`

## 4. Success Criteria

- **SC-001**: Unit tests for `ScoringAgent` pass with 100% coverage on all role levels.
- **SC-002**: Retrieval latency for multi-vector search remains under 200ms (p95).
- **SC-003**: 100% of qualified candidates in a test batch meet the role-specific gate requirements.
