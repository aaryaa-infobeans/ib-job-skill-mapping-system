/speckit.specify

SYSTEM:
You are a senior software architect. Generate the functional specification for the HITL Candidate Feedback API.

SOURCE OF TRUTH:
- Requirement: Human-in-the-Loop oversight for candidate matches.
- Action: POST /api/v1/requisition/match/feedback
- Strategy: UPSERT based on (team_member_id, correlation_id, reviewer_email).

OUTPUT:
Markdown file `fr-7-hitl-feedback-api.md`.
Include:
- API endpoint and payload details.
- Business rules (Auth, Idempotency, Validation).
- Persistence expectations.
