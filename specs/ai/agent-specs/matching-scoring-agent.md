# Agent Specification: Matching & Scoring Agent

## 1. Purpose
This agent is a **deterministic function**, not an LLM agent. Its purpose is to execute the core matching and scoring logic, comparing the normalized requisition against all available team members.

## 2. Inputs
- The agent receives the entire `GraphState` as input.
- It specifically operates on:
  - `state.normalized_skills`
  - `state.requisition_input.job_description.experience`
- It uses the output of the `Availability_Evaluation_Agent`.
- It will query the PostgreSQL database for all `team_member` and `team_member_skill` records.

## 3. Core Logic (Deterministic)
The agent will iterate through each active and available team member and calculate a series of scores.

### 3.1. Skill Score
- **Mandatory Skills**: Calculate the percentage of `mandatory_skill_ids` that the team member possesses.
  - `mandatory_score = (matched_mandatory_skills / total_mandatory_skills)`
- **Preferred Skills**: Calculate the percentage of `preferred_skill_ids` that the team member possesses.
  - `preferred_score = (matched_preferred_skills / total_preferred_skills)`
- **Combined Skill Score**: A weighted average of the two scores.
  - `skill_score = (0.7 * mandatory_score) + (0.3 * preferred_score)`
  - The weights (0.7, 0.3) MUST be configurable.

### 3.2. Experience Score
- Compare the team member's `experience_in_months` with the requisition's `experience.min_months` and `experience.max_months`.
- The score should be normalized from 0 to 1. For example:
  - If `experience` is below `min_months`, the score is 0.
  - If `experience` is within the range, the score is 1.
  - If `experience` is above `max_months`, the score could be 1 or slightly higher (configurable).

### 3.3. Final Score Aggregation
- The `final_score` is a weighted average of the `skill_score` and `experience_score`.
  - `final_score = (0.8 * skill_score) + (0.2 * experience_score)`
  - The weights (0.8, 0.2) MUST be configurable.

**This logic will be encapsulated in a pure Python function. No LLM is involved.**

## 4. Outputs
- The agent's output is a list of `CandidateScores` objects, as defined in `state-schema.md`.
- This agent mutates the graph state by populating the `state.candidate_scores` field.

## 5. State Mutations
- **Allowed**:
  - Sets the `state.candidate_scores` field.
- **Forbidden**:
  - Must not modify any other part of the state.

## 6. Guardrails & Failure Handling
- **Zero Division**: The code must handle cases where there are no mandatory or preferred skills to avoid division-by-zero errors.
- **Repeatability**: The scoring algorithm must be 100% deterministic and repeatable. Given the same inputs, it must always produce the same scores.
- **Failure**: If a critical error occurs (e.g., database connection failure), the agent must populate `state.error_message` and terminate the graph execution.
