# FR-4: AI Matching & Scoring

## 1. Purpose
This document specifies the functional requirements for the AI-driven matching and scoring process. This is the core logic that evaluates and ranks team members against job requisitions.

## 2. AI Agent Orchestration
- **Traceability**: FR-4.1, FR-4.2

- The system SHALL use a `JD/Requisition Parsing Agent` to normalize the role, title, and seniority from the incoming requisition, and to extract skills from all relevant fields (`mandatory_skills`, `preferred_skills`, `jd_text`).
- The system SHALL use a `Skill Extraction & Normalization Agent` to map all skill strings (from both requisitions and team member profiles) to a canonical skill dictionary (e.g., "JS", "Javascript" -> "JavaScript").

## 3. Scoring Logic
- **Traceability**: FR-4.3

The system MUST compute scores using deterministic, non-LLM-based logic.

### 3.1. Skill Match Score
- A score MUST be calculated based on the match between the requisition's skills and the team member's skills.
- The calculation MUST differentiate between `mandatory_skills` and `preferred_skills`, with a higher weight given to mandatory skills.
- The score SHOULD also consider proficiency indicators like `rating` and `experience_in_months` for each skill.

### 3.2. Availability Match
- An availability match MUST be determined by comparing the `expected_start_date` and `requisition_duration_month` with the team member's `allocations`.
- The system MUST calculate the team member's free capacity within the required window.

## 4. Output Generation
- **Traceability**: FR-4.4, FR-4.5

### 4.1. Aggregate Scores
- The system MUST produce an aggregate `match_score` (0-1) that combines the skill match score, experience fit, and availability.
- A boolean `availability_match` flag MUST be generated.
- A `fit_level` (e.g., HIGH, MEDIUM, LOW) MUST be derived from the aggregate `match_score`.

### 4.2. Explanation Generation
- The system SHALL use an `Explanation Generation Agent` to produce human-readable reasons for each match.
- Explanations MUST include:
  - A summary of matched mandatory and preferred skills.
  - A comparison of the team member's experience vs. the required experience.
  - A statement about the team member's availability.

## 5. Guardrails
- LLMs MUST NOT be used for any mathematical calculations, including scoring, weighting, or availability calculations.
- All scoring algorithms MUST be deterministic and repeatable.
- The output of all AI agents involved in the scoring process MUST be auditable.
