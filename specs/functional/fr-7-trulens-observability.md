# FR-7: TruLens Observability and LLM Evaluation

**Version:** 1.1  
**Last Updated:** 2026-04-17  

## 1. Purpose
This document specifies the requirements for deep LLM observability, tracing, and evaluation using TruLens to ensure high-quality matching results and cost transparency.

## 2. Observability Requirements

### 2.1. Hierarchical Pipeline Tracing
- The system MUST implement hierarchical tracing of the LangGraph-based talent search pipeline using a class-based instrumentation pattern (`TalentSearchPipeline`).
- Each execution cycle MUST be captured as a root trace with nested sub-spans for individual agent nodes.
- Traces MUST be accessible via the TruLens dashboard for debugging and analysis.

### 2.2. LLM Instrumentation
- All calls to the Groq LLM API MUST be instrumented to capture:
  - Exact prompt sent to the model.
  - Full model response (text and structured JSON).
  - Accurate token usage (prompt, completion, and total tokens).
  - LLM execution latency and cost metrics.

### 2.3. Context Unification
- The system MUST consolidate all observability data under a unified application context (`talent_search_pipeline`).
- Internal agent sub-spans MUST roll up into the primary application record to prevent fragmented dashboard view.

### 2.4. Custom Metrics Telemetry
- The system MUST log the following custom metrics via OTEL metadata for every search request:
  - `avg_match_score`: Average semantic similarity score of returned candidates.
  - `mandatory_hit_rate`: Percentage of results meeting mandatory skill thresholds.

## 3. Evaluation Framework

### 3.1. Feedback Functions
- The system SHOULD integrate TruLens feedback templates (Relevance, Groundedness) to evaluate matching quality over time.

### 3.2. Dashboard Access
- The system SHALL provide a centralized dashboard reachable at port 59511.
- Dashboard views MUST be filterable by `app_name=talent_search_pipeline`.

## 4. Technical Specifications
- **Provider**: TruLens 2.7.2 (OTEL-based).
- **Instrumentation API**: `TuApp` context managers and `@instrument` decorators.
- **Persistence**: SQLite database (`default.sqlite`).
- **Traceability**: FR-7.1 to FR-7.5.
