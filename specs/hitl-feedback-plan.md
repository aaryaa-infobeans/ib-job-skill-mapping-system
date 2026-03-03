# Implementation Plan: HITL Candidate Feedback API

## 1. Objective
Establish a robust feedback mechanism for candidate matches to allow human-in-the-loop oversight and data collection for future model tuning.

## 2. Work Breakdown Structure (WBS)

### 2.1 Database Layer
- **Task 1**: Create `requisition_match_team_member_feedback` table.
- **Task 2**: Implement `updated_at` trigger for automatic timestamp management.
- **Task 3**: Add unique constraint on `(team_member_id, correlation_id, reviewer_email)`.

### 2.2 Service Layer
- **Task 4**: Implement `FeedbackRepository` with UPSERT logic.
- **Task 5**: Implement `FeedbackService` for business validation (rating range, email check).

### 2.3 API Layer
- **Task 6**: Define `FeedbackCreate` and `FeedbackResponse` Pydantic schemas.
- **Task 7**: Implement `POST /api/v1/requisition/match/feedback` endpoint with token validation.
- **Task 7**: Implement `POST /api/v1/requisition/match/feedback` endpoint with token validation.
- **Task 8**: Implement `GET /api/v1/requisition/match/feedback/{correlation_id}/{team_member_id}` to retrieve existing feedback.
- **Task 8**: Implement in-memory rate limiting (20 req/min).

### 2.4 Verification
- **Task 9**: Write integration tests covering success, update, authorization failure, and rate limiting.

## 3. Technical Sequencing
1.  **DB Migrations**: Run first to ensure the table structure is present.
2.  **Repo/Service Implementation**: Build the core logic.
3.  **API Integration**: Expose the logic via FastAPI.
4.  **Verification**: Execute the test suite.

## 4. Acceptance Criteria
- Feedback is correctly persisted/updated in the DB.
- Rejects invalid ratings (>5 or <1).
- Rejects unauthorized submissions (email mismatch).
- Passes all integration tests in `tests/integration/test_feedback.py`.
