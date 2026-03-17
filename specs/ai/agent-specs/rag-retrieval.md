# Agent Specification: RAG Retrieval Agent

**Version:** 1.2  
**Modified By:** CR-SCORE-003  
**Last Updated:** 2026-03-17  

## 1. Purpose
The RAG Retrieval Agent is responsible for finding the most relevant candidates in the PostgreSQL database using a hybrid search strategy (BM25 + Multi-Vector Semantic Search).

## 2. Hybrid Search Strategy
The agent combines keyword matching and semantic similarity to ensure high recall:
- **BM25 (Keyword)**: Matches specific skill names, certifications, and titles.
- **Vector (Semantic)**: Captures conceptual overlap (e.g., "AI Developer" matching "Machine Learning Engineer").
- **Weighting**: Typically 70% Keyword / 30% Vector (configurable in `settings.py`).

## 3. Multi-Vector Routing
Queries are decomposed and routed to specific embedding columns:

| Query Component | Target Vector Column |
| :--- | :--- |
| Mandatory Skills | `skills_embedding` |
| Preferred Skills | `skills_embedding` |
| Job Title / Role | `resume_embedding` |
| Certifications | `certifications_embedding` |

## 4. Fallback Logic
- **NULL Column Strategy**: If a candidate lacks the specific multi-vector (legacy data), the search falls back to the legacy `embedding` column or the `profile_text` keyword search.
- **Thresholds**: Candidates must meet the `rag_similarity_threshold` (default 0.5) to be retrieved for scoring.

## 5. State Mutations
- **Allowed**:
  - Populates `state.retrieved_candidates` with candidate IDs and initial search scores.
- **Forbidden**:
  - Must not modify any candidate profile data.
