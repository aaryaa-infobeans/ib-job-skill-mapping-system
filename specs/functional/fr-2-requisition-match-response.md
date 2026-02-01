# FR-2: Requisition Match Response

## 1. Purpose
This document specifies the requirements for the Requisition Match Response API, which allows clients to retrieve the ranked list of team members who match a given requisition.

## 2. API Specification
- **Method**: `GET`
- **Path**: `/api/v1/jd-skill-mapping/{correlation_id}/matches`
- **Traceability**: FR-2.1

### 2.1. Path Parameters
- `correlation_id` (string, required): The internal correlation ID returned by the Requisition Request API (FR-1).

### 2.2. Query Parameters
- `limit` (integer, optional, default: 50): The maximum number of matches to return.

## 3. Response Payload
- **Traceability**: FR-2.2

The response payload MUST adhere to the following JSON structure.

**Fields:**
- `metadata` (object, required):
  - `correlation_id` (string, required): The correlation ID of the request.
  - `timestamp` (string, ISO 8601, required): The timestamp when the response was generated.
  - `total_records` (integer, required): The total number of matching records found.
  - `batch_number` (integer, required): The current batch number.
  - `total_batches` (integer, required): The total number of batches.
  - `records_in_batch` (integer, required): The number of records in the current batch.
  - `source_system` (string, required): The name of this system.
  - `schema_version` (string, required): The schema version of the response.
  - `status` (object, required):
    - `code` (integer, required): The status code (0 for success).
    - `key` (string, required): A key representing the status (e.g., "MATCHING_COMPLETED").
    - `message` (string, required): A human-readable status message.
- `team_members` (array of objects, required): A list of matched team members.
  - `team_member_id` (string, required): The ID of the team member.
  - `profile_score` (float, required): The overall match score (0-100).
  - `fit_level` (enum, required): `HIGH`, `MEDIUM`, `LOW`.
  - `availability_match` (boolean, required): Indicates if the team member's availability matches.
  - `explanation` (array of strings, required): Human-readable explanations for the match.

## 4. Business Logic
- **Traceability**: FR-2.3, FR-2.4, FR-2.5

- The `profile_score` MUST be an aggregation of skill match, experience fit, and availability.
- The `fit_level` MUST be derived from the `profile_score` based on pre-defined thresholds.
- The `explanation` array MUST contain at least one human-readable string explaining the match.
- The `metadata.correlation_id` MUST correspond to the original requisition request.

## 5. Error Handling
- If the `correlation_id` is not found, the system SHALL return a `404 Not Found` status code.
- If the matching process is still ongoing, the system MAY return a `202 Accepted` with a status indicating the progress.
- If an internal error occurs, the system SHALL return a `500 Internal Server Error` status code.
