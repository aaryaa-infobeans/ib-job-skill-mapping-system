# Prompt Specifications: TruLens Evaluators

## 1. Relevance Evaluation Prompt
**Target Node**: `matching_scoring_node`
**Input**: `requisition_input`, `candidate_explanation`
**Logic**: Analyze if the matched candidate's key strengths (as explained) directly address the mandatory and preferred requirements of the job description.
**Output**: Float [0.0 - 1.0]

## 2. Groundedness Evaluation Prompt
**Target Node**: `explanation_generation_node`
**Input**: `candidate_profile_text`, `candidate_explanation`
**Logic**: Verify that every claim made in the matching explanation (e.g., "Has 5 years of Python") is explicitly present in the candidate's raw profile data.
**Output**: Float [0.0 - 1.0]
