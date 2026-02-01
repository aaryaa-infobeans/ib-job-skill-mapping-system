# Agent Specification: Availability Evaluation Agent

## 1. Purpose
This agent is a **deterministic function**, not an LLM agent. Its purpose is to evaluate the availability of team members based on the requisition's time requirements and their current allocations.

## 2. Inputs
- The agent receives the entire `GraphState` as input.
- It specifically operates on:
  - `state.requisition_input.job_description.expected_start_date`
  - `state.requisition_input.job_description.requisition_duration_month`
- It will also query the PostgreSQL database for all `team_member_allocations`.

## 3. Core Logic (Deterministic)
The agent will perform the following steps for each active team member:
1.  **Define Requisition Window**: Calculate the `requisition_start_date` and `requisition_end_date` from the input.
2.  **Retrieve Allocations**: Query the `team_member_allocations` table for all non-deleted allocations for the team member that overlap with the requisition window.
3.  **Calculate Total Allocation**: Sum the `allocation_percentage` for all overlapping projects.
4.  **Determine Available Capacity**: Calculate `100 - total_allocation`.
5.  **Make Availability Decision**: A team member is considered available if their available capacity is sufficient to meet a predefined threshold (e.g., if they are less than 80% allocated during the required period).

This logic will be encapsulated in a pure Python function. **No LLM is involved.**

## 4. Outputs
- This agent does not directly produce a final output object for the state.
- Instead, its logic is a critical part of the `Matching_Scoring_Agent`, which uses the availability calculation as a key input for its scoring algorithm. The result of the availability check (`is_available: bool`) will be stored in the `CandidateScores` object.

## 5. State Mutations
- **Allowed**:
  - As part of the `Matching_Scoring_Agent`, it contributes to the creation of the `state.candidate_scores` list.
- **Forbidden**:
  - Does not directly mutate the state.

## 6. Guardrails & Failure Handling
- **Database Connection**: The primary failure mode is an inability to connect to the database. The function must handle this gracefully, log the error, and terminate the graph execution by populating `state.error_message`.
- **Date Logic**: All date and time calculations must be handled carefully, accounting for time zones if necessary, to avoid off-by-one errors.
