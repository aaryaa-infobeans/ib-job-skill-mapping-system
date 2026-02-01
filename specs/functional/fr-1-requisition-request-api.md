# FR-1: Requisition Request API

## 1. Purpose
This document specifies the requirements for the Requisition Request API, which allows client systems to submit job requisitions for skill matching.

## 2. API Specification
- **Method**: `POST`
- **Path**: `/api/v1/jd-skill-mapping`
- **Traceability**: FR-1.1

### 2.1. Request Payload
The request payload MUST adhere to the following JSON structure.

**Fields:**
- `request_id` (string, required): A unique identifier for the request from the source system.
- `schema_version` (string, required): The version of the schema being used (e.g., "v1").
- `source_system` (string, required): The name of the system sending the request.
- `client_name` (string, optional): The name of the client for whom the requisition is being made.
- `job_description` (object, required): An object containing the details of the job description.
  - `client_name` (string, required): The name of the client.
  - `title` (string, required): The job title.
  - `role` (string, required): The role for the position.
  - `requisition_duration_month` (integer, optional, >= 0): The duration of the requisition in months.
  - `expected_start_date` (date, ISO 8601, optional): The expected start date for the role.
  - `priority` (enum, required): `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
  - `location` (array of strings, required): The location(s) for the job.
  - `work_mode` (array of strings, required): The work mode(s) (e.g., "Remote", "Hybrid", "On-site").
  - `experience` (object, optional):
    - `min_months` (number, >= 0): Minimum months of experience.
    - `max_months` (number, >= min_months): Maximum months of experience.
  - `mandatory_skills` (array of strings, optional): A list of mandatory skills.
  - `preferred_skills` (array of strings, optional): A list of preferred skills.
  - `jd_text` (string, required): The full text of the job description.
- `metadata` (object, required): Metadata about the request.

## 3. Validation Rules
The system SHALL validate the following conditions upon receiving a request.
- **Traceability**: FR-1.2

- The request body MUST be a valid JSON object.
- All required fields MUST be present.
- `expected_start_date` MUST be a valid ISO 8601 date string.
- If both `experience.min_months` and `experience.max_months` are provided, `min_months` MUST be less than or equal to `max_months`.

## 4. Persistence
- **Traceability**: FR-1.3

- On successful validation, the system SHALL persist the entire requisition request in the `requisition_requests` and `requisition_detail` tables in the PostgreSQL database.

## 5. Processing
- **Traceability**: FR-1.3

- Upon successful persistence, the system SHALL trigger the AI agent pipeline to:
  1. Parse and normalize the job description.
  2. Extract and normalize skills.
  3. Initiate the matching process against team member data.

## 6. Response
- **Traceability**: FR-1.4

- The system SHALL return a `202 Accepted` HTTP status code on successful receipt and validation of the request.
- The response body MUST include an internal `correlation_id` and the processing `status`.

**Example Response:**
```json
{
  "correlation_id": "CORR-123456789",
  "status": "QUEUED_FOR_PROCESSING"
}
```

## 7. Error Handling
- If validation fails, the system SHALL return a `400 Bad Request` status code with a descriptive error message.
- If an internal error occurs, the system SHALL return a `500 Internal Server Error` status code.
