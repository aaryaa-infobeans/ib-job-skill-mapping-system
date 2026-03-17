# Implementation Plan: Scoring Logic and Embedding Transition Refinement

**Branch**: `CR-SCORE-003-scoring-refinement` | **Date**: 2026-03-17 | **Spec**: `spec.md`

## Summary
The plan involves refactoring the `ScoringAgent` to use dynamic settings, implementing the `GemmaEmbeddingAgent` for local inference, and updating the RAG retrieval logic to support multi-vector comparison.

## Technical Context
**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, SQLAlchemy, LangGraph, Transformers (HuggingFace)  
**Storage**: PostgreSQL with pgvector  
**Testing**: pytest  
**Performance Goals**: < 200ms p95 RAG retrieval  
**Constraints**: < 2GB RAM for local Gemma model  

## Constitution Check
- **API-First**: All scoring gates are exposed via the `/matches` endpoint. (Pass)
- **AI-Driven**: Uses local Gemma model and LLM-based fit evaluation. (Pass)
- **Security**: PII scrubbing remains mandatory before embedding. (Pass)

## Project Structure (Impacted Files)
```text
src/app/
├── ai/
│   ├── utils/
│   │   ├── scoring.py         # Primary logic for role-based weights and gates
│   │   ├── gemma_embedding.py # NEW: Local Gemma-300m agent
│   │   ├── rag_retrieval.py   # Multi-vector routing logic
│   │   └── models.py          # Updated Pydantic/Dataclass models
│   └── agents/
│       ├── matching_scoring.py # Orchestrates scoring flow
│       └── candidate_availability.py # Pydantic V2 migration
├── settings.py                # Externalized weights and thresholds
└── logging_config.py          # Timezone-aware logging fix
```

## Implementation Phases

### Phase 1: Foundation (Settings & Logging)
- Externalize all scoring weights and seniority thresholds into `settings.py`.
- Apply timezone-aware logging fix to `logging_config.py`.

### Phase 2: Embedding System Transition
- Implement `GemmaEmbeddingAgent` using HuggingFace Transformers.
- Update `EmbeddingResult` model to support 768-D vectors.

### Phase 3: Scoring Engine Refactoring
- Implement `_get_role_configs()` and gate logic in `ScoringAgent`.
- Implement Context Boost capping (8%) and Skill Family penalties (-10%).
- Migrate `candidate_availability.py` to Pydantic V2.

### Phase 4: RAG Retrieval Update
- Update `_query_vector_and_filter` to route to specific embedding columns.
- Implement legacy fallback logic for single-vector rows.

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| Multi-Vector Complexity | Higher match precision | Single vector dilutes semantic meaning between skills and biography. |
