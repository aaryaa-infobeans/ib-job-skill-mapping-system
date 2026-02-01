# Agent Specification: Skill Normalization Agent

## 1. Purpose
This agent takes the raw skill strings extracted by the `JD_Parsing_Agent` and maps them to the canonical skill IDs from the `skill_master` database table.

## 2. Inputs
- The agent receives the entire `GraphState` as input.
- It specifically operates on:
  - `state.parsed_jd.extracted_mandatory_skills`
  - `state.parsed_jd.extracted_preferred_skills`

## 3. Core Logic (LLM & Deterministic)
The agent will use a hybrid approach to normalize skills.

### 3.1. Step 1: Deterministic Matching
- For each raw skill string, the agent will first attempt a direct, case-insensitive match against the `skill_name` in the `skill_master` table.
- It will also check against a pre-defined dictionary of common aliases (e.g., "JS" -> "JavaScript", "Postgres" -> "PostgreSQL").
- If a high-confidence match is found, the corresponding `skill_id` is used.

### 3.2. Step 2: LLM-based Fuzzy Matching
- For any raw skills that could not be matched deterministically, the agent will use an LLM.
- The LLM will be given the unmatched skill string and a list of all canonical skill names from the `skill_master` table.
- The prompt will instruct the LLM to find the most likely match from the canonical list.

**Example Prompt Fragment**:
```
"You are a skill normalization engine. Given the raw skill '{raw_skill_name}' and the following list of canonical skills: [...], identify the best match from the list.

Return ONLY a JSON object with the following structure:
{
  "matched_skill": "..."
}
"
```

## 4. Outputs
- The agent's output is a dictionary conforming to the `NormalizedSkills` schema defined in `state-schema.md`.
- This agent mutates the graph state by populating the `state.normalized_skills` field.

## 5. State Mutations
- **Allowed**:
  - Sets the `state.normalized_skills` field.
- **Forbidden**:
  - Must not modify any other part of the state.

## 6. Guardrails & Failure Handling
- **No Hallucination**: If the LLM cannot find a reasonable match for a skill, it should be instructed to return `null`. Unmatched skills will be logged and ignored for the current matching process. They can be reviewed later to improve the `skill_master` dictionary.
- **Output Validation**: The agent's output MUST conform to the `NormalizedSkills` schema.
- **Failure**: If a critical error occurs (e.g., cannot connect to the database), the agent must populate `state.error_message` and terminate the graph execution.
