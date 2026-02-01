# Logical Data Model

## 1. Purpose
This document specifies the logical data model for the Job Description to Team Member Skill Mapping System. This model is derived from the `ib-job-skill-mapping-system.sql` schema file.

## 2. Traceability
- **Source Schema**: `specs-data/ib-job-skill-mapping-system.sql`
- **SRS Section**: 4. Data Requirements (Logical View)

## 3. Entity Relationship Diagram (ERD) - Conceptual
-   A `team_member` has many `team_member_skill` records and many `team_member_allocation` records.
-   A `team_member_skill` is a linking table between `team_member` and `skill_master`. It can have many `skill_certification` records.
-   A `skill_master` belongs to one `category_master`.
-   A `requisition_request` is submitted by an `auth_client` and has a `status` from `requisition_status_master`.
-   Each `requisition_request` has a one-to-one relationship with a `requisition_detail` record.
-   `langgraph_checkpoints` are linked to a `requisition_request` to audit the AI pipeline.
-   `auth_access_tokens` are issued to an `auth_client`.

## 4. Table Specifications

### `auth_clients`
- **Purpose**: Stores information about client applications authorized to access the system.
- **Columns**:
  - `id` (SMALLINT, PK, Identity)
  - `client_name` (VARCHAR(100), Not Null)
  - `client_code` (VARCHAR(50), Not Null, Unique)
  - `client_secret_hash` (VARCHAR(255), Not Null)
  - `auth_type` (VARCHAR(10), Not Null, Default: 'OAUTH')
  - `is_active` (BOOLEAN, Not Null, Default: TRUE)
  - `created_at` (TIMESTAMP, Not Null, Default: CURRENT_TIMESTAMP)

### `auth_access_tokens`
- **Purpose**: Stores access tokens issued to clients.
- **Columns**:
  - `id` (INT, PK, Identity)
  - `auth_client_id` (SMALLINT, Not Null, FK to `auth_clients.id`)
  - `access_token` (VARCHAR(255), Not Null, Unique)
  - `expires_at` (TIMESTAMP, Not Null)
  - `is_revoked` (BOOLEAN, Not Null, Default: FALSE)
  - `issued_at` (TIMESTAMP, Not Null, Default: CURRENT_TIMESTAMP)

### `requisition_status_master`
- **Purpose**: A master table for the possible statuses of a requisition request.
- **Columns**:
  - `status_id` (SMALLINT, PK)
  - `status_key` (VARCHAR(40), Not Null, Unique)
  - `status_message` (VARCHAR(255), Not Null)

### `requisition_requests`
- **Purpose**: Stores metadata for each incoming requisition request.
- **Columns**:
  - `id` (INT, PK, Identity)
  - `request_id` (VARCHAR(64), Not Null, Unique)
  - `auth_client_id` (SMALLINT, Not Null, FK to `auth_clients.id`)
  - `status` (SMALLINT, Not Null, FK to `requisition_status_master.status_id`)
  - `client_name` (VARCHAR(100), Not Null)
  - `correlation_id` (VARCHAR(100), Nullable)
  - `received_at` (TIMESTAMP, Not Null, Default: CURRENT_TIMESTAMP)
  - `completed_at` (TIMESTAMP, Nullable)

### `requisition_detail`
- **Purpose**: Stores the raw JSON payload of each requisition request.
- **Columns**:
  - `id` (INT, PK, Identity)
  - `requisition_request_id` (INT, Not Null, Unique, FK to `requisition_requests.id`)
  - `payload_json` (JSONB, Not Null)
  - `payload_hash` (CHAR(64), Not Null, Unique)
  - `created_at` (TIMESTAMP, Not Null, Default: CURRENT_TIMESTAMP)

### `category_master`
- **Purpose**: A master table for skill categories.
- **Columns**:
  - `category_id` (SMALLINT, PK, Identity)
  - `category_name` (VARCHAR(100), Not Null, Unique)
  - `created_at` (TIMESTAMP, Default: now())

### `skill_master`
- **Purpose**: The canonical dictionary of all skills.
- **Columns**:
  - `skill_id` (VARCHAR(50), PK)
  - `skill_name` (VARCHAR(100), Not Null, Unique)
  - `category_id` (SMALLINT, Not Null, FK to `category_master.category_id`)
  - `created_at` (TIMESTAMP, Default: now())

### `team_member`
- **Purpose**: Stores the core profile information for each team member.
- **Columns**:
  - `team_member_id` (VARCHAR(50), PK)
  - `designation` (VARCHAR(100), Nullable)
  - `profile_type` (VARCHAR(50), Nullable)
  - `is_active` (BOOLEAN, Default: TRUE)
  - `experience_in_months` (INTEGER, Nullable)
  - `base_location` (VARCHAR(100), Nullable)
  - `work_type` (work_type_enum, Nullable) - Enum: ('wfo', 'wfh', 'hybrid')
  - `profile_url` (VARCHAR(1024), Nullable)
  - `created_at` (TIMESTAMP, Default: now())

### `team_member_allocation`
- **Purpose**: Stores the project allocation details for each team member.
- **Columns**:
  - `team_member_id` (VARCHAR(50), PK, FK to `team_member.team_member_id`)
  - `project_id` (VARCHAR(50), PK)
  - `allocation_percentage` (NUMERIC(5,2), Nullable)
  - `start_date` (DATE, Nullable)
  - `end_date` (DATE, Nullable)
  - `billable` (BOOLEAN, Nullable)
  - `is_deleted` (BOOLEAN, Default: FALSE)

### `team_member_skill`
- **Purpose**: Links team members to skills, with proficiency details.
- **Columns**:
  - `team_member_id` (VARCHAR(50), PK, FK to `team_member.team_member_id`)
  - `skill_id` (VARCHAR(50), PK, FK to `skill_master.skill_id`)
  - `rating` (INTEGER, Nullable)
  - `experience_in_months` (INTEGER, Nullable)
  - `is_deleted` (BOOLEAN, Default: FALSE)

### `skill_certification`
- **Purpose**: Stores certification details for a specific team member's skill.
- **Columns**:
  - `id` (INT, PK, Identity)
  - `certification_id` (VARCHAR(100), Nullable)
  - `team_member_id` (VARCHAR(50), Not Null)
  - `skill_id` (VARCHAR(50), Not Null)
  - `certificate` (VARCHAR(150), Nullable)
  - `issuer` (VARCHAR(100), Nullable)
  - `issued_date` (DATE, Nullable)
  - `valid_till` (DATE, Nullable)
  - **Composite FK**: (`team_member_id`, `skill_id`) -> `team_member_skill(team_member_id, skill_id`)

### `langgraph_checkpoints`
- **Purpose**: Stores the state of the AI agent graph for auditing and debugging.
- **Columns**:
  - `id` (INT, PK, Identity)
  - `request_id` (VARCHAR(64), Not Null, FK to `requisition_requests.request_id`)
  - `node_name` (VARCHAR(50), Not Null)
  - `state_json` (JSONB, Not Null)
  - `token_count` (INT, Nullable)
  - `created_at` (TIMESTAMP, Not Null, Default: CURRENT_TIMESTAMP)
