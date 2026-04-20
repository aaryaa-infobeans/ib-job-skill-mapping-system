# FR-6: Logging, Monitoring, and Audit

**Version:** 1.1  
**Modified By:** CR_PII_scrubber (CR-PII-001)  
**Last Updated:** 2026-02-16  

## 1. Purpose
This document specifies the requirements for logging, monitoring, and auditing to ensure system observability, traceability, and compliance.

## 2. Logging
- **Traceability**: FR-6.1

### 2.1. Application Logs
- The system SHALL log all significant events, including:
  - API requests and responses (at least metadata and status codes).
  - The outcome of all AI agent executions.
  - Summaries of matching processes (e.g., number of candidates evaluated).
  - Processing status of sync batches (`batch_id`, success/failure, record counts).
- Logs MUST be structured (e.g., JSON) to facilitate machine parsing and analysis.
- Each log entry MUST include a `correlation_id` to trace a request through the system.

### 2.2. Audit Logs
- **Traceability**: FR-6.2
- The system MUST store a separate, immutable audit trail for all LLM interactions.
- Each audit record MUST include:
  - The `request_id` from the original requisition.
  - The name of the LangGraph node/agent being called.
  - The number of tokens used in the interaction.
  - A timestamp.
- This data is critical for compliance, cost analysis, and debugging AI agent behavior.

### 2.3. PII Scrubbing Audit Trail (NEW: CR-PII-001)
- **Traceability**: CR-PII-001 (NFR-PII-003)
- The system MUST store an immutable audit trail for every PII scrubbing operation.
- Each audit record in `pii_scrub_audit` table MUST include:
  - `audit_id` (UUID): Unique identifier
  - `timestamp`: When scrubbing occurred
  - `source_table` and `source_record_id`: What data was scrubbed
  - `pii_detected` (JSONB): Array of detected PII types with confidence scores
    - Example: `[{"type": "email", "confidence": 1.0, "action": "hash"}, {"type": "person", "confidence": 0.92, "action": "redact"}]`
  - `rule_version`: Version of scrubbing rules applied
  - `scrubber_version`: Version of scrubbing service
  - `triggered_by`: What initiated scrubbing (e.g., "ingestion_api")
  - `processing_time_ms`: Latency measurement
- **Retention**: 7 years (regulatory requirement)
- **Immutability**: No UPDATE/DELETE operations allowed (database constraint)
- **Access**: Query API at `GET /api/v1/admin/pii-audit?source_id={id}&from={date}&to={date}`

### 2.4. Log Sanitization (NEW: CR-PII-001)
- **Traceability**: CR-PII-001 (NFR-PII-002)
- All application logs, error logs, and debug logs MUST NOT contain raw PII.
- **Implementation**:
  - Structured logging with explicit PII-safe fields only
  - Log aggregation pipeline applies final scrubbing pass
  - Automated daily scans detect PII patterns in stored logs
- **Example Safe Logging**:
  ```python
  logger.info(
      "Scrubbed email",
      extra={
          "pii_type": "email",
          "action": "hash",
          "input_length": len(email),
          "output_hash_prefix": hashed_email[:8],
          "confidence": 1.0
      }
  )
  ```

## 3. Monitoring
- **Traceability**: FR-6.3

### 3.1. Health Endpoint
- The system SHALL provide a `GET /api/v1/health` endpoint.
- This endpoint SHALL check the health of the service and its downstream dependencies (e.g., database connectivity).
- It MUST return an HTTP `200 OK` status if the system is healthy, and a `503 Service Unavailable` otherwise.

### 3.2. Metrics Endpoint
- The system SHALL provide a `GET /api/v1/metrics` endpoint.
- This endpoint MUST expose key application metrics in a format compatible with a monitoring solution like Prometheus.
- Metrics SHALL include, but are not limited to:
  - API request latency, volume, and error rates (per endpoint).
  - AI agent execution time.
  - LLM token usage.
  - Database query performance.

### 3.3. Observability with TruLens
- The system SHALL integrate TruLens for deep LLM observability and evaluation.
- **Traceability**: FR-6.4
- The system MUST capture:
  - Full execution traces of the team member search pipeline.
  - LLM input/output, latency, and token usage for all enrichment calls.
  - Custom feedback metrics (e.g., matching scores, hit rates) as metadata.
- TruLens data SHALL be stored in a persistent SQLite database (`default.sqlite`) for longitudinal analysis.

## 4. Tracing
- The system SHOULD implement distributed tracing to provide a detailed view of requests as they flow through the various components (APIs, AI agents, database).
- Trace data SHOULD be correlated with logs using the `correlation_id`.
- **Instrumentation**: FR-6.5
  - All critical LangGraph nodes MUST be instrumented for observability.
  - The search pipeline SHALL use the `TruApp` (OTEL-based) provider for non-intrusive tracing.
