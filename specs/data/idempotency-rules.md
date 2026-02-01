# Idempotency Rules

## 1. Purpose
This document specifies the idempotency requirements for the system's write operations to ensure that repeated requests do not result in unintended side effects, such as duplicate data.

## 2. Idempotency for Requisition Submissions

### 2.1. API Endpoint
- `POST /api/v1/jd-skill-mapping`

### 2.2. Mechanism
- **Traceability**: FR-1.1
- The `request_id` field in the request payload is the key to enforcing idempotency.
- The system MUST check if a `requisition_request` with the given `request_id` from the same `source_system` already exists.
- **If the request exists and was processed successfully**: The system SHOULD return a `200 OK` or `202 Accepted` status with the `correlation_id` of the original request. It MUST NOT create a new record.
- **If the request exists but failed processing**: The system MAY re-initiate processing for the existing record.
- **If the request does not exist**: The system SHALL create a new record and proceed with processing.

## 3. Idempotency for Bulk Upserts

### 3.1. API Endpoint
- `POST /api/v1/team-members/skill-availability/bulk-upsert`

### 3.2. Mechanism
- **Traceability**: FR-3.4

#### 3.2.1. Batch-Level Idempotency
- The `metadata.batch_id` is the key for batch-level idempotency.
- The system SHOULD log the `batch_id` of every batch it receives.
- If a request with a previously processed `batch_id` is received, the system SHOULD return a `409 Conflict` status to indicate a potential duplicate submission. The client can then decide whether to resubmit. This prevents costly re-processing of large batches.

#### 3.2.2. Record-Level Idempotency (Upsert)
- The core idempotency logic is at the record level, implemented as an "upsert" (update or insert) operation.
- **For Team Member Skills**: The combination of `team_member_id` and `skill_id` uniquely identifies a skill record for a team member.
  - If a record with this combination exists, the system SHALL update the `rating`, `experience_in_months`, and `is_deleted` fields.
  - If it does not exist, the system SHALL insert a new record.
- **For Team Member Allocations**: The combination of `team_member_id` and `project_id` uniquely identifies an allocation record.
  - If a record with this combination exists, the system SHALL update the `allocation_percentage`, `start_date`, `end_date`, `billable`, and `is_deleted` fields.
  - If it does not exist, the system SHALL insert a new record.
- **Soft Deletes**: The `is_deleted` flag is crucial. When `true`, it marks the record as inactive but does not physically delete it from the database, thus preserving historical data.
