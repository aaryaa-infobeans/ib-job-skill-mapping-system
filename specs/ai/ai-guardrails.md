# AI Guardrails

**Version:** 1.1  
**Modified By:** CR_PII_scrubber (CR-PII-001)  
**Last Updated:** 2026-02-16  

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
- **Rationale**: To protect user privacy and comply with data protection regulations (GDPR, CCPA, ISO 27001, SOC 2).
- **Implementation**:
  - The prompts will be constructed using non-identifiable information where possible. For example, instead of sending a team member's name to the `Explanation_Generation_Agent`, a generic "the candidate" will be used.
  - The system will rely on internal IDs (`team_member_id`) for all processing.

### 6.1. Automated PII Scrubbing (NEW: CR-PII-001)
- **Guardrail**: ALL data entering the RAG pipeline MUST pass through automated PII detection and scrubbing (Node 0: `PII_Scrubber_Agent`).
- **Enforcement Points**:
  1. **Ingestion-Time**: Before embedding generation or vector storage
  2. **Retrieval-Time**: Secondary filtering before API responses (defense-in-depth)
  3. **Logging**: All logs, metrics, and traces sanitized (no raw PII)
- **Detection Methods**:
  - **Pattern-Based (Regex)**: Email (100% recall), phone (95% recall), DOB, postal codes
  - **NER-Based (SpaCy)**: Names (F1≥0.90), locations, organizations
  - **Dictionary-Based**: Client names, project names (business-sensitive data)
- **Scrubbing Actions**:
  - **Redaction**: Full names, addresses → `<NAME_REDACTED>`, `<ADDRESS_REDACTED>`
  - **Masking**: Phone numbers → `+1-***-0123`, emails → `j***@company.com`
  - **Tokenization**: Client/project names → `CLIENT_TOKEN_{hash}`, `PROJECT_TOKEN_{hash}`
  - **Hashing**: Email/phone → `EMAIL_HASH_{sha256_prefix}` (for deduplication)
- **Validation Gate**: Database constraint enforces `pii_scrubbed = TRUE` before storage
- **Audit Trail**: Every scrubbing operation logged in `pii_scrub_audit` table (immutable, 7-year retention)
- **Fail-Closed Policy**: If scrubbing fails → reject request (HTTP 503)
- **Performance**: Scrubbing latency ≤ 50ms (p95), false positive rate ≤ 3%
- **Compliance**: GDPR Article 5(1)(c), CCPA §1798.100, ISO 27001 A.18.1.4, SOC 2 PI1.2

### 6.2. LLM Prompt Construction
- **Guardrail**: LLM prompts MUST NOT contain raw PII.
- **Implementation**: All LLM agents (`JD_Parsing_Agent`, `Explanation_Generation_Agent`) receive pre-scrubbed data from upstream nodes.
- **Verification**: Automated tests validate prompts contain no PII patterns before execution.
