# Prompt Implementation Plan: TruLens Evaluations

## 1. Objective
Define and integrate LLM-based evaluation prompts for automated feedback in the TruLens dashboard.

## 2. Tasks
- **Task 1**: Define the 'Relevance' system prompt based on `trulens.feedback.templates.rag.Relevance`.
- **Task 2**: Define the 'Groundedness' system prompt to audit matching justifications.
- **Task 3**: Integrate prompts into the `TalentSearchPipeline` feedback loop (Phase 2).

## 3. Success Criteria
- Evaluation scores are consistently generated for every record.
- Scores accurately reflect the "human-perceived" quality of the match.
