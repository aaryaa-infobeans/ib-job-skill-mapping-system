# AI Guardrails

## 1. Purpose
This document specifies the mandatory guardrails and safety protocols that MUST be implemented for all AI and LLM interactions within the system. The primary goal is to ensure that AI is used responsibly, deterministically where required, and in a manner that is auditable and secure.

## 2. Core Principle: LLMs for Language, Not Logic
- **Guardrail**: LLMs MUST NOT be used for any form of mathematical calculation, scoring, ranking, or availability evaluation.
- **Rationale**: LLMs are non-deterministic and can make mathematical errors. Core business logic must be repeatable, auditable, and provably correct.
- **Implementation**: The system architecture explicitly separates LLM-based agents (for parsing and explanation) from deterministic Python functions (for scoring and evaluation), as defined in the Graph Topology. All scoring weights and thresholds MUST be configurable and managed outside the LLM prompts.

## 3. Factual Grounding
- **Guardrail**: LLM agents MUST be grounded in the data provided in their context. They MUST NOT be allowed to invent facts or use external knowledge not present in the prompt.
- **Rationale**: To prevent hallucinations and ensure that the output is based solely on the system's data (the requisition and the team member profiles).
- **Implementation**:
  - Prompts will be engineered to explicitly forbid the use of outside information.
  - For the `Explanation_Generation_Agent`, the prompt will command the LLM to only reference the specific skill and experience matches provided.

## 4. Output Schema Enforcement
- **Guardrail**: All LLM agents that are expected to return structured data (e.g., JSON) MUST have their output validated against a predefined schema.
- **Rationale**: LLM output can vary. Enforcing a schema ensures that the data passed to downstream deterministic components is reliable and in the correct format.
- **Implementation**:
  - Pydantic models or similar typed data structures will be used to define the expected output schema for each agent.
  - The output from the LLM will be parsed and validated against this schema.
  - A retry mechanism (e.g., 2 retries) will be implemented to handle cases where the LLM fails to produce a valid schema. If retries fail, the process must terminate gracefully for that request.

## 5. Auditability and Logging
- **Guardrail**: Every interaction with an LLM MUST be logged for audit and compliance purposes.
- **Rationale**: To provide full traceability for debugging, cost management, and security reviews.
- **Traceability**: FR-6.2
- **Implementation**: The `langgraph_checkpoints` table will store the state of the graph and, critically, the `token_count` for every LLM-powered node execution. This creates an immutable audit trail for every AI interaction.

## 6. PII Handling
- **Guardrail**: No sensitive Personally Identifiable Information (PII) should be sent to third-party LLM APIs unless absolutely necessary and permitted by organizational policy.
- **Rationale**: To protect user privacy and comply with data protection regulations.
- **Implementation**:
  - The prompts will be constructed using non-identifiable information where possible. For example, instead of sending a team member's name to the `Explanation_Generation_Agent`, a generic "the candidate" will be used.
  - The system will rely on internal IDs (`team_member_id`) for all processing.
