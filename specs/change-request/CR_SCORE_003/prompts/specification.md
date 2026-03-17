/specify

SYSTEM:
You are a Principal Software Architect responsible for refining the candidate scoring and matching logic.
Your objective is to formalize the transition to a role-specific scoring system and a multi-vector RAG strategy.

OBJECTIVE:
Create a new Change Request specification:
File path: /specs/change-request/CR_SCORE_003/spec.md

REQUIREMENTS:
1. Define role levels (SENIOR, MID, JUNIOR) and their respective experience thresholds.
2. Specify scoring weights for each role level.
3. Define hard gates for skill matching and semantic similarity.
4. Document the context boost capping logic (8% cap).
5. Specify the skill family mismatch penalty (-0.10).
6. Detail the multi-vector RAG strategy using google/embeddinggemma-300m.

ACCEPTANCE CRITERIA:
- Role-specific gates are clearly defined.
- Scoring formula includes all components (Weights, Boosts, Penalties).
- Multi-vector routing is mapped to specific database columns.
