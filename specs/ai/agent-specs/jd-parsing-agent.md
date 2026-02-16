# Agent Specification: JD Parsing Agent

**Version:** 1.1  
**Modified By:** CR_PII_scrubber (CR-PII-001)  
**Last Updated:** 2026-02-16  

## 1. Purpose
This agent is responsible for taking the raw job description text and other details from the requisition and converting them into a structured format.

**Note (CR-PII-001):** This agent receives PII-scrubbed data from Node 0 (`PII_Scrubber_Agent`). All personal identifiers have been redacted/masked/tokenized before this agent processes the data.

## 2. Inputs
- The agent receives the entire `GraphState` as input.
- It specifically operates on:
  - `state.requisition_input.job_description.jd_text` (PII-scrubbed)
  - `state.requisition_input.job_description.title` (PII-scrubbed)
  - `state.requisition_input.job_description.role` (PII-scrubbed)
  - `state.requisition_input.job_description.mandatory_skills`
  - `state.requisition_input.job_description.preferred_skills`
- **PII Safety (CR-PII-001)**: All input fields have been processed by `PII_Scrubber_Agent`. Names, contact information, and business-sensitive data are already sanitized.

## 3. Core Logic (LLM Prompt)
The agent will use an LLM with a prompt engineered to perform the following actions:
- Read the `jd_text`.
- Identify the key responsibilities and requirements.
- Extract any skills mentioned directly in the text that are not already listed in the `mandatory_skills` or `preferred_skills` arrays.
- Normalize the job `title` and `role` to a standard internal taxonomy if applicable (e.g., "Senior Software Engineer" -> "SSE").
- Consolidate all identified skills into two lists: a definitive list of mandatory skills and a definitive list of preferred skills.

**Example Prompt Fragment**:
```
"You are a helpful HR assistant. Given the following job description text, title, and existing skill lists, your task is to parse the information and return a structured JSON object.

...

- From the 'jd_text', extract all technical skills, tools, and platforms.
- Combine the skills from 'jd_text' with the provided 'mandatory_skills' and 'preferred_skills' lists.
- Normalize the job 'title' to a standard role.

Return ONLY a JSON object with the following structure:
{
  "normalized_title": "...",
  "normalized_role": "...",
  "extracted_mandatory_skills": [...],
  "extracted_preferred_skills": [...]
}
"
```

## 4. Outputs
- The agent's output is a dictionary conforming to the `ParsedJD` schema defined in `state-schema.md`.
- This agent mutates the graph state by populating the `state.parsed_jd` field.

## 5. State Mutations
- **Allowed**:
  - Sets the `state.parsed_jd` field.
- **Forbidden**:
  - Must not modify any other part of the state.

## 6. Guardrails & Failure Handling
- **Output Validation**: The agent's output MUST be a valid JSON object that conforms to the `ParsedJD` schema. If the LLM output is not valid, the agent should retry up to 2 times.
- **Failure**: If the agent fails to produce a valid output after retries, it MUST populate the `state.error_message` field with a descriptive error and terminate the graph execution for this request. The request status should be updated to "FAILED_PARSING".
- **Deterministic**: While the LLM's extraction might have minor variations, the output format is strictly enforced.
