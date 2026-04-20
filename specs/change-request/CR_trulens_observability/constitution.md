# Constitution: TruLens Observability System

## 1. Guiding Principles
- **Accuracy**: LLM usage and cost data MUST be recorded with high precision for audit purposes.
- **Performance**: Instrumentation MUST NOT introduce significant latency to the critical path (P95 < 2s).
- **Separation of Concerns**: Observability logic MUST remain decoupled from business logic.

## 2. Technical Commandments
- **Thou Shalt Trace**: All LLM calls MUST be captured within a valid trace context.
- **Thou Shalt Not Duplicate**: Instrumentation MUST be non-intrusive and avoid redundant logging.
- **Thou Shalt Persist**: All traces MUST be written to a persistent datastore (`default.sqlite`).

## 3. Data Integrity
- Usage metrics MUST handle failure scenarios gracefully, ensuring `total_tokens` is always reported.
- Metadata MUST include enough context (query, result count) to allow for effective filtering and analysis.
