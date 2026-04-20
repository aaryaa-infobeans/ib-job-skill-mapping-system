# Change Request: TruLens Observability Integration (CR-OBS-001)

## 1. Description
Integrate TruLens into the talent search pipeline to provide automated tracing, LLM instrumentation, and evaluation capabilities.

## 2. Requirements
- **FR-7.1 Tracing**: Capture full hierarchical execution traces of the search pipeline.
- **FR-7.2 LLM Monitoring**: Instrument Groq API calls for token, cost, and latency tracking.
- **FR-7.3 Context Unification**: Consolidate all agent sub-spans into a single `talent_search_pipeline` application record.
- **FR-7.4 Compliance**: Maintain an audit trail of LLM interactions via persistent `trulens_events`.
- **FR-7.5 Dashboard**: Enable a visual dashboard for deep trace inspection and debugging at port 59511.

## Task Checklist: TruLens Observability

- [x] Create `src/app/ai/utils/trulens_helper.py` with `TalentSearchPipeline` class
- [x] Implement `@instrument` decorators on all agent nodes
- [x] Resolve dependency conflicts (rich, attrs, trulens 2.7.2)
- [x] Consolidate app context to `talent_search_pipeline`
- [x] Wrap background worker execution in `TruApp` context
- [x] Fix "Already recording with a context manager" nesting errors
- [x] Resolve semantic validation metadata conflicts for search entrypoint
- [x] Instrument semantic validation logic for trace visibility
- [x] Verify span capture in `trulens_events`
- [x] Update `requirements.txt`
- [x] Update root `README.md` with dashboard instructions
- [x] Update project specifications folder
- [x] Finalize `FR-7` Functional Specification

## 3. Scope
- Implementation of `TalentSearchPipeline` class with `@instrument` decorators.
- Refactoring of background workers to use instrumented search entrypoints.
- Dependency management for `trulens-eval` and Python 3.13 compatibility.
- Resolution of trace nesting ("Already recording") and semantic validation conflicts.

## 4. Constraints
- **OTEL Standards**: Use OpenTelemetry-based tracing provided by TruLens 2.7.2.
- **Non-blocking**: Instrumentation must not interfere with background job completion.
- **Minimal Intrusion**: Retain existing DB-based audit logs for redundancy.
