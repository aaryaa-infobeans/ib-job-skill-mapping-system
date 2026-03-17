# Constitution: HITL Candidate Feedback System

## 1. Guiding Principles
- **Integrity**: Every feedback entry MUST be attributable to a authenticated user and tied to a unique match (correlation_id).
- **Transparency**: Every update to a feedback MUST be tracked with an `updated_at` timestamp.
- **Fairness**: Single-reviewer feedback pattern SHALL be enforced to ensure one voice per candidate per match.
- **Resilience**: The system SHOULD handle high-concurrency feedback submission via rate limiting and efficient indexing.

## 2. Technical Commandments
- **Thou Shalt Validate**: All ratings MUST be between 1 and 5.
- **Thou Shalt Authenticate**: Feedback MUST ONLY be accepted from the authenticated reviewer matching the request payload.
- **Thou Shalt Upsert**: Updates MUST NOT create duplicate entries for the same match-reviewer pair.
- **Thou Shalt Log**: All feedback actions MUST generate structured logs including the `correlation_id` and `reviewer_email`.

## 3. Data Governance
- Feedback data is considered semi-structured; while comments are free-form, ratings and sentiment (liked) are structured for analytical use.
- Data MUST be persisted in a normalized PostgreSQL table.
