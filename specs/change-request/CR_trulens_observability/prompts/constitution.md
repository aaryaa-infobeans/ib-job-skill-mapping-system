# Prompt Constitution: TruLens Observability evaluations

## 1. Context
These prompts define the evaluation criteria for TruLens feedback functions (Relevance, Groundedness) used to monitor the talent search pipeline.

## 2. Core Principles
- **Accuracy**: Evaluations must be based strictly on the provided context (JD vs Candidate Profile).
- **Objectivity**: Use a scale of 0.0 to 1.0 for all scores.
- **Explainability**: LLM evaluations should include a brief reasoning snippet.

## 3. Evaluation Dimensions
### 3.1 Relevance
Score how well the candidate profile matches the specific requirements of the job requisition.
### 3.2 Groundedness
Verify that the matching justification provided by the system is supported by the raw candidate profile text.
