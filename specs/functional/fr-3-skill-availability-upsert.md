# FR-3: Team Member Skills & Availability Upsert API (OBSOLETE - REMOVED)

**Version:** 1.1  
**Modified By:** CR_PII_scrubber (CR-PII-001)  
**Last Updated (Removal):** 2026-02-11  
**Last Updated (PII Note):** 2026-02-16  

**Status:** REMOVED  
**Date Removed:** 2026-02-11  
**Reason:** Bulk upsert endpoint and all related functionality have been removed from the system.

**Note (CR-PII-001):** If this endpoint is reinstated in the future, all team member data MUST pass through PII scrubbing (Node 0) before ingestion into the RAG pipeline.

---

## ⚠️ THIS SPECIFICATION IS NO LONGER APPLICABLE

The `/api/v1/team-members/skill-availability/bulk-upsert` endpoint has been permanently removed along with:
- Router: `src/app/api/routers/skill_availability.py` (DELETED)
- All bulk upsert test files (DELETED)
- Related integration tests (DELETED)

This functionality is no longer part of the IB Job Skill Mapping System.

---

## Original Specification (For Historical Reference Only)

## 1. Purpose
This document specifies the requirements for the Team Member Skills & Availability Upsert API, which allows for bulk updates of team member data from source systems.

## 2. API Specification
- **Method**: `POST`
- **Path**: `/api/v1/team-members/skill-availability/bulk-upsert`
- **Traceability**: FR-3.1

### 2.1. Request Payload
The request payload MUST adhere to the provided "Candidate Skill Availability Payload" structure.
- **Traceability**: FR-3.2, FR-3.3

**High-Level Structure:**
```json
{
  "metadata": { ... },
  "team_members": [ ... ]
}
```

**Key Fields:**
- `metadata` (object, required):
  - `batch_id` (string, required): A unique identifier for the sync batch.
  - `timestamp` (ISO 8601, required): The timestamp of the batch creation.
  - `total_records`, `batch_number`, `total_batches`, `records_in_batch` (integers, required).
  - `source_system`, `schema_version` (strings, required).
  - `status` (object, required): `code`, `key`, `message`.
- `team_members` (array of objects, required):
  - `team_member_id` (string, required): Primary identifier for the team member.
  - `team_member_status` (enum, required): `active`, `inactive`, `terminated`, etc.
  - `experience_in_months` (integer, required).
  - `full_name` (string, required).
  - `allocations` (array of objects, optional): Project allocation details.
    - `is_deleted` (boolean): For soft-deleting allocations.
  - `skills` (array of objects, optional): Skill details.
    - `is_deleted` (boolean): For soft-deleting skills.

## 3. Idempotency and Persistence
- **Traceability**: FR-3.4, FR-3.5

- The system MUST implement idempotent upsert logic. For a given `team_member_id` and `skill_id` or `allocation_id`, new records update existing ones.
- Records with `is_deleted = true` MUST be marked as inactive (soft-delete) but retained for historical purposes.
- Sync metadata and processing results for each batch MUST be persisted in `sync_logs` files or a dedicated audit table.

## 4. Response
- **Traceability**: FR-3.6

- On successful receipt of the batch, the system SHALL return an HTTP `202 Accepted` status.
- The response body MUST contain a simple summary of the sync processing, such as records received, inserted, updated, and failed.

## 5. Error Handling
- If the request payload fails validation, the system SHALL return a `400 Bad Request` status code.
- If the `batch_id` has been processed before, the system MAY return a `409 Conflict` status code, or it MAY re-process the batch if the logic is truly idempotent. This decision should be finalized during implementation.
- If an internal error occurs during processing, the details MUST be logged against the `batch_id` for later analysis.
