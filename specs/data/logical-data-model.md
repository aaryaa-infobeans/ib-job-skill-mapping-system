# Logical Data Model

## 1. Purpose
This document specifies the logical data model for the Job Description to Team Member Skill Mapping System. This model is derived from the Data Requirements section of the SRS.

## 2. Traceability
- **SRS Section**: 4. Data Requirements (Logical View)

## 3. Entity Relationship Diagram (ERD) - Conceptual
A detailed ERD will be created during the design phase. Conceptually, the relationships are:
- A `team_member` has many `team_member_skill` records and many `team_member_allocations`.
- A `team_member_skill` links a `team_member` to a `skill_master` record.
- A `skill_master` belongs to a `category_master`.
- A `requisition_request` has one `requisition_detail` and is associated with an `auth_client`.
- `langgraph_checkpoints` are linked to a `requisition_request`.

## 4. Table Specifications

### `auth_clients`
- **Purpose**: Stores information about client applications that are authorized to access the system.
- **Columns**:
  - `id` (PK)
  - `client_name` (string)
  - `client_code` (string, unique)
  - `client_secret_hash` (string)
  - `auth_type` (string)
  - `is_active` (boolean)
  - `created_at` (timestamp)

### `requisition_requests`
- **Purpose**: Stores metadata for each incoming requisition request.
- **Columns**:
  - `id` (PK)
  - `request_id` (string, unique per source)
  - `auth_client_id` (FK to `auth_clients`)
  - `status` (FK to `requisition_status_master`)
  - `correlation_id` (string, unique)
  - `received_at` (timestamp)
  - `completed_at` (timestamp, nullable)

### `requisition_detail`
- **Purpose**: Stores the raw payload of each requisition request.
- **Columns**:
  - `id` (PK)
  - `requisition_request_id` (FK to `requisition_requests`)
  - `payload_json` (jsonb)
  - `payload_hash` (string)
  - `created_at` (timestamp)

### `team_member`
- **Purpose**: Stores the core profile information for each team member.
- **Columns**:
  - `team_member_id` (PK, string)
  - `designation` (string)
  - `profile_type` (string)
  - `is_active` (boolean)
  - `experience_in_months` (integer)
  - `base_location` (string)
  - `work_type` (string)
  - `profile_url` (string)
  - `created_at` (timestamp)
  - `updated_at` (timestamp)

### `team_member_allocations`
- **Purpose**: Stores the project allocation details for each team member.
- **Columns**:
  - `id` (PK)
  - `team_member_id` (FK to `team_member`)
  - `project_id` (string)
  - `allocation_percentage` (float)
  - `start_date` (date)
  - `end_date` (date, nullable)
  - `billable` (boolean)
  - `is_deleted` (boolean, for soft-delete)

### `skill_master`
- **Purpose**: The canonical dictionary of all skills.
- **Columns**:
  - `skill_id` (PK)
  - `skill_name` (string)
  - `category_id` (FK to `category_master`)
  - `created_at` (timestamp)

### `team_member_skill`
- **Purpose**: Links team members to skills, with proficiency details.
- **Columns**:
  - `id` (PK)
  - `team_member_id` (FK to `team_member`)
  - `skill_id` (FK to `skill_master`)
  - `rating` (integer)
  - `experience_in_months` (integer)
  - `is_deleted` (boolean, for soft-delete)

### `langgraph_checkpoints`
- **Purpose**: Stores the state of the AI agent graph for auditing and debugging.
- **Columns**:
  - `id` (PK)
  - `request_id` (FK to `requisition_requests`)
  - `node_name` (string)
  - `state_json` (jsonb)
  - `token_count` (integer)
  - `created_at` (timestamp)

---
*Other tables like `auth_access_tokens`, `requisition_status_master`, `category_master`, and `skill_certification` are also part of the schema as defined in the SRS.*
