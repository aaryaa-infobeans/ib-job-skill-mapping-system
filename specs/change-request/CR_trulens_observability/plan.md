# Implementation Plan: TruLens Observability

## 1. Objective
Establish deep observability for the talent search engine using TruLens to monitor LLM performance, track pipeline health, and provide a unified dashboard for evaluation.

## 2. Work Breakdown Structure

### 2.1 Utility Layer
- **Task 1**: Implement `TalentSearchPipeline` class-based instrumentation wrapper.
- **Task 2**: Configure `TruApp` for consolidated application context mapping (`talent_search_pipeline`).
- **Task 3**: Implement `avg_match_score` and `mandatory_hit_rate` telemetry via OTEL metadata.
- **Task 4**: Resolve TruLens 2.7.2 regressions (AttributeError/TypeError).

### 2.2 Integration Layer
- **Task 5**: Instrument agent nodes with `@instrument` decorators:
  - `requisition_parsing_node`
  - `skill_normalization_node`
  - `matching_scoring_node`
  - `explanation_generation_node`
- **Task 6**: Wrap background graph execution in `TruApp` recording context.
- **Task 7**: Fix trace nesting conflicts ("Already recording" errors).
- **Task 8**: Resolve semantic validation metadata conflicts for search entrypoints.

### 2.3 Documentation & Ops
- **Task 9**: Update root `README.md` with dashboard instructions.
- **Task 10**: Finalize functional specifications (`FR-7`).
- **Task 11**: Create structured prompt plans in `specs/change-request/CR_trulens_observability/prompts/`.

## 3. Success Criteria
- Hierarchical traces are viewable in the TruLens dashboard at port 59511.
- All agent LLM calls roll up into a single searchable record per pipeline run.
- LLM calls accurately report token usage, cost, and latency.
- Semantic validation passes reliably with dynamic job metadata.
