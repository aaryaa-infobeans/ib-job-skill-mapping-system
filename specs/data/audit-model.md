# Audit Model

## 1. Purpose
This document specifies the data model and requirements for auditing system activities, focusing on traceability of requests and all interactions with AI/LLM components.

## 2. Guiding Principles
- **Immutability**: Audit records SHOULD be immutable. Once written, they should not be changed.
- **Traceability**: It must be possible to trace every incoming request from its origin to the final response, including all intermediate steps.
- **Compliance**: The audit model must capture all necessary data to comply with organizational policies and potential regulatory requirements, especially regarding AI usage.

## 3. Audit Data Models

### 3.1. API Request Audit
- **Purpose**: To log every incoming API request.
- **Implementation**: While application logs (FR-6.1) will capture this, the database provides a persistent, long-term audit trail.
  - The `requisition_requests` table, with its `request_id`, `auth_client_id`, `correlation_id`, and `received_at` fields, serves as the primary audit log for requisition submissions.
  - The `sync_logs` (or a `sync_batches` database table) serves as the audit log for bulk upsert operations, keyed by `batch_id`.

### 3.2. AI/LLM Interaction Audit
- **Purpose**: To specifically audit every call to an LLM for cost, compliance, and debugging.
- **Traceability**: FR-6.2
- **Implementation**: The `langgraph_checkpoints` table is the primary mechanism for this audit trail.
- **Table**: `langgraph_checkpoints`
  - `id` (PK): Unique identifier for the audit entry.
  - `request_id` (FK): Links the audit entry directly to the originating `requisition_requests` record.
  - `node_name` (string): The specific AI agent or node in the LangGraph that was executed (e.g., "JD_Parsing_Agent").
  - `state_json` (jsonb): A snapshot of the state of the graph *after* the node was executed. This provides a complete picture of the data at that point in the workflow.
  - `token_count` (integer): The number of tokens consumed by the LLM in this step. This is critical for cost monitoring.
  - `created_at` (timestamp): When the interaction occurred.

## 4. Audit Trail Example
Consider a single requisition request with `request_id = 'XYZ-123'`. The audit trail in the database would look like this:

1.  **A record is created in `requisition_requests`**:
    - `request_id`: 'XYZ-123'
    - `correlation_id`: 'CORR-987'
    - ...other metadata

2.  **Multiple records are created in `langgraph_checkpoints` as the AI pipeline runs**:
    - `request_id`: 'XYZ-123', `node_name`: 'JD_Parsing_Agent', `state_json`: {...}, `token_count`: 500
    - `request_id`: 'XYZ-123', `node_name`: 'Skill_Normalization_Agent', `state_json`: {...}, `token_count`: 300
    - `request_id`: 'XYZ-123', `node_name`: 'Explanation_Generation_Agent', `state_json`: {...}, `token_count`: 800

This model allows for a complete reconstruction of the entire process for any given request.
