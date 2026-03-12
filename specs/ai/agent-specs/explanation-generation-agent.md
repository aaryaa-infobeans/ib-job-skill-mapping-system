# Agent Specification: Explanation Generation Agent

**Version:** 1.1  
**Modified By:** CR_PII_scrubber (CR-PII-001)  
**Last Updated:** 2026-02-16  

## 1. Purpose
This agent is responsible for generating concise, human-readable explanations for why a team member is a good match for a requisition. It translates the deterministic scores into natural language.

**Note (CR-PII-001):** This agent MUST NOT leak PII in generated explanations. All references use generic identifiers ("the candidate", `team_member_id`) rather than names or contact information.

## 2. Inputs
- The agent receives the entire `GraphState` as input.
- It specifically operates on the list of `state.candidate_scores`.
- For each candidate, it will look at the `skill_score`, `experience_score`, `is_available`, and the underlying `match_reasons` (the specific skills that were matched).

## 3. Core Logic (LLM Prompt)
The agent will iterate through the top N candidates (e.g., top 20) from the `candidate_scores` list. For each candidate, it will use an LLM with a prompt engineered to generate a summary.

**Example Prompt Fragment**:
```
"You are a helpful HR assistant. A candidate has been matched to a job with the following details:
- Matched 3 out of 3 mandatory skills: Python, DBMS, AWS.
- Matched 2 out of 5 preferred skills: Docker, K8s.
- Candidate experience: 60 months. Required experience: 36-84 months.
- Candidate is available.

Generate a brief, bulleted list of 2-3 points explaining why this candidate is a good fit. Use a positive and professional tone.

Return ONLY a JSON object with the following structure:
{
  "explanations": [
    "Explanation point 1",
    "Explanation point 2"
  ]
}
"
```
The prompt will be dynamically populated with the structured match data for each candidate.

## 4. Outputs
- The agent will generate a list of explanation strings for each candidate.
- This agent contributes to the creation of the `FinalResult` object by providing the content for the `explanation` field.

## 5. State Mutations
- **Allowed**:
  - The agent's output is used by the `Result_Aggregation_Agent` to populate the `state.final_results.explanation` field. It does not directly mutate the state itself.
- **Forbidden**:
  - Must not modify any other part of the state.

## 6. Guardrails & Failure Handling
- **Factual Grounding**: The prompt MUST strictly instruct the LLM to only use the information provided (skills matched, experience, availability) and not to invent or infer any other qualifications.
- **Conciseness**: The prompt should instruct the LLM to keep the explanations brief and to the point.
- **PII Prevention (CR-PII-001)**: 
  - The prompt MUST instruct the LLM to use generic references: "the candidate", "this team member"
  - The prompt MUST forbid including names, emails, phone numbers, or addresses
  - Output validation MUST scan for PII patterns (regex + NER) before returning explanations
  - If PII detected in output → regenerate with stricter prompt or use template fallback
- **Output Validation**: The agent must validate that the LLM output is a valid JSON object with the expected structure. If not, it should retry.
- **Failure**: If the LLM fails to generate an explanation for a candidate, a default, template-based explanation can be used as a fallback (e.g., "Matches required skills and experience."). The error should be logged.
