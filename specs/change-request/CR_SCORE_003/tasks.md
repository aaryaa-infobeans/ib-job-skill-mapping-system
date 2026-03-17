# Tasks: Scoring Logic and Embedding Transition Refinement

**Input**: Design documents from `spec.md`
**Prerequisites**: plan.md (required), spec.md (required)

## Phase 1: Foundational (Blocking Prerequisites)
- [x] T001 Externalize scoring weights and thresholds in `src/app/settings.py`
- [x] T002 Fix deprecated `datetime.utcnow()` in `src/app/logging_config.py`
- [x] T003 Migrate `CandidateAvailabilityRequest` to Pydantic V2 in `src/app/ai/agents/candidate_availability.py`

## Phase 2: User Story 1 & 2 - Role-Based Scoring & Gating
**Goal**: Implement dynamic weighting and hard gates per seniority level.

- [x] T004 Implement `ScoringAgent._get_role_configs` for SENIOR, MID, JUNIOR in `src/app/ai/utils/scoring.py`
- [x] T005 Implement hard gate checks in `ScoringAgent.execute`
- [x] T006 Implement Context Boost capping logic (8% max)
- [x] T007 Implement Skill Family penalty logic (-10% for mismatches)
- [x] T008 Update `tests/unit/test_scoring_agent.py` to validate new logic

## Phase 3: User Story 3 - Multi-Vector RAG
**Goal**: Transition to granular semantic search.

- [x] T009 Implement `GemmaEmbeddingAgent` in `src/app/ai/utils/gemma_embedding.py`
- [x] T010 Update `EmbeddingResult` dimension validation in `src/app/ai/utils/models.py`
- [x] T011 Update `_query_vector_and_filter` in `src/app/ai/utils/rag_retrieval.py` for multi-vector routing
- [x] T012 Add legacy NULL fallback for single-vector rows

## Phase 4: Polish & Validation
- [x] T013 Run integration test `tests/integration/test_rag_first_scoring.py`
- [x] T014 Verify end-to-end flow with `test_and_view_matches.py`
- [x] T015 Generate AI explanation prompts in `src/app/ai/utils/explanation_prompt.py`
