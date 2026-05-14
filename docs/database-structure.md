# Database Structure

**Engine**: PostgreSQL | **ORM**: SQLAlchemy | **Source**: [src/app/db/models/models.py](../src/app/db/models/models.py)

---

## Entity Relationship Overview

```
auth_clients ──────────────────────────────────────────┐
     │                                                  │
     └──(1:N)──► requisition_requests ◄──(N:1)── requisition_status_master
                      │
                      ├──(1:1)──► requisition_detail
                      └──(1:N)──► langgraph_checkpoints

category_master ──(1:N)──► skill_master ──(1:N)──► team_member_skill ◄──(N:1)── team_member
                                                           │                          │
                                              (1:N)──► team_member_skill_certification│
                                                                          (1:N)──► team_member_allocation
                                                                          (1:1)──► team_member_embeddings

ingestion_batch_state ──(1:N)──► ingestion_audit_log

llm_request_log          (standalone — no FK)
requisition_match_team_member_feedback  (standalone — no FK)
skill_ontology           (standalone — no FK)
jd_certification_requirements           (standalone — no FK)
pii_scrub_audit          (standalone — no FK, immutable)
```

---

## Tables by Domain

### Authentication

#### `auth_clients`
Registered API consumers. Every request must come from an active client.

| Column | Type | Notes |
|---|---|---|
| `id` | SmallInteger PK | Auto-increment |
| `client_name` | String(100) | Display name |
| `client_code` | String(50) UNIQUE | Machine-readable code |
| `client_secret_hash` | String(255) | Hashed secret (never plaintext) |
| `auth_type` | String(10) | Default `OAUTH` |
| `is_active` | Boolean | Disable without deleting |
| `created_at` | DateTime | UTC |

#### `auth_access_tokens`
Short-lived tokens issued to clients.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `auth_client_id` | SmallInteger FK → auth_clients | |
| `access_token` | String(255) UNIQUE | Token value |
| `expires_at` | DateTime | Hard expiry |
| `is_revoked` | Boolean | Soft revocation |
| `issued_at` | DateTime | UTC |

---

### Requisition Requests

#### `requisition_status_master`
Lookup table. Values seeded at migration time.

| status_id | status_key | Meaning |
|---|---|---|
| 1 | RECEIVED | Queued, not yet processed |
| 2 | PROCESSING | AI pipeline is running |
| 3 | COMPLETED | Result ready |
| 4 | FAILED | Pipeline error |
| 5 | CANCELLED | Abandoned by client |

#### `requisition_requests`
One row per incoming job-matching request.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | Internal ID |
| `request_id` | String(64) UNIQUE | External identifier sent by client |
| `auth_client_id` | SmallInteger FK → auth_clients | |
| `status` | SmallInteger FK → requisition_status_master | |
| `client_name` | String(100) | Denormalised for convenience |
| `correlation_id` | String(100) | Optional tracing token |
| `received_at` | DateTime | |
| `completed_at` | DateTime nullable | Set when status → COMPLETED/FAILED |

#### `requisition_detail`
Stores the raw JSON payload. Separate from `requisition_requests` to keep the metadata table lean.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `requisition_request_id` | Integer FK UNIQUE → requisition_requests | 1:1 |
| `payload_json` | JSONB | Full request body |
| `payload_hash` | CHAR(64) UNIQUE | SHA-256 — prevents duplicate submissions |
| `created_at` | DateTime | |

---

### Skills & Categories

#### `category_master`
Top-level groupings for skills (e.g. "Cloud", "Frontend").

| Column | Type | Notes |
|---|---|---|
| `category_id` | SmallInteger PK | |
| `category_name` | String(100) UNIQUE | |
| `created_at` | DateTime | |

#### `skill_master`
Canonical skill dictionary. Every skill belongs to one category.

| Column | Type | Notes |
|---|---|---|
| `skill_id` | String(50) PK | Slug-style ID |
| `skill_name` | String(100) UNIQUE | Display name |
| `category_id` | SmallInteger FK → category_master | |
| `created_at` | DateTime | |

#### `skill_ontology`
Expands a skill into related terms used during semantic matching.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `core_skill` | String(255) UNIQUE | The canonical skill name |
| `enriched_terms` | ARRAY(String) / JSON | Synonyms and related terms |

Index: `idx_skill_ontology_core_skill`

#### `jd_certification_requirements`
Maps a job description type to the certifications it requires.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `jd_type` | String(255) | Job description category |
| `certification` | String(255) | Required cert name |

Unique: `(jd_type, certification)` | Index: `idx_jd_certification_jd_type`

---

### Team Members

#### `team_member`
Core profile. One row per person in the talent pool.

| Column | Type | Notes |
|---|---|---|
| `team_member_id` | String(50) PK | External HR system ID |
| `designation` | String(100) | Job title |
| `profile_type` | String(255) | Profile classification |
| `is_active` | Boolean | Default true |
| `experience_in_months` | Integer | Total experience |
| `base_location` | String(100) | |
| `work_type` | Enum(`wfo`, `wfh`, `hybrid`) | |
| `profile_url` | String(1024) | Link to full profile |
| `created_at` | DateTime | |

#### `team_member_allocation`
Which projects a person is allocated to. Composite PK.

| Column | Type | Notes |
|---|---|---|
| `team_member_id` | String(50) PK FK → team_member | |
| `project_id` | String(50) PK | External project ID |
| `allocation_percentage` | Numeric(5,2) | 0–100 |
| `start_date` | Date | |
| `end_date` | Date | |
| `billable` | Boolean | |
| `is_deleted` | Boolean | Soft delete — do not hard-delete |

#### `team_member_skill`
A person's proficiency in a skill. Composite PK.

| Column | Type | Notes |
|---|---|---|
| `team_member_id` | String(50) PK FK → team_member | |
| `skill_id` | String(50) PK FK → skill_master | |
| `rating` | Integer | Proficiency score |
| `experience_in_months` | Integer | Time spent using this skill |
| `is_deleted` | Boolean | Soft delete |

#### `team_member_skill_certification`
Certifications earned for a specific skill. Uses a composite FK back to `team_member_skill`.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `certification_id` | String(100) | External cert ID |
| `team_member_id` | String(50) | Part of composite FK |
| `skill_id` | String(50) | Part of composite FK |
| `certificate` | String(150) | Certificate name |
| `issuer` | String(100) | Issuing body |
| `issued_date` | Date | |
| `valid_till` | Date | Expiry |

Composite FK: `(team_member_id, skill_id)` → `team_member_skill(team_member_id, skill_id)`

---

### Embeddings (Vector Search)

#### `team_member_embeddings`
Stores three 768-dimensional vectors per person for semantic similarity search via pgvector.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `gen_random_uuid()` |
| `team_member_id` | String(50) FK UNIQUE → team_member | Upsert target |
| `embedding` | Vector(768) | Legacy combined embedding |
| `resume_embedding` | Vector(768) nullable | Resume-specific vector |
| `skills_embedding` | Vector(768) nullable | Skills-specific vector |
| `certifications_embedding` | Vector(768) nullable | Certs-specific vector |
| `profile_text` | Text | Source text for `embedding` |
| `resume_text` | Text | Source text for `resume_embedding` |
| `skills_text` | Text | Source text for `skills_embedding` |
| `certifications_text` | Text | Source text for `certifications_embedding` |
| `embedding_model` | String(100) | Default `embedding-gemma-300m` |
| `content_hash` | CHAR(64) | SHA-256 to skip re-embedding unchanged profiles |
| `resume_fetched_at` | DateTime | Last time resume was pulled |
| `embedding_updated_at` | DateTime | Last vector refresh |
| `pii_scrubbed` | Boolean | Whether PII has been removed from texts |
| `scrubbed_at` | DateTime(tz) | When scrubbing ran |
| `created_at` | DateTime | |

**Indexes**:
- B-tree: `team_member_id`, `created_at`, `content_hash`, `pii_scrubbed`
- IVFFlat (vector ANN): `resume_embedding`, `skills_embedding`, `certifications_embedding`

---

### Feedback & Evaluation

#### `requisition_match_team_member_feedback`
Reviewer thumbs-up/down and ratings for a candidate-requisition match.

| Column | Type | Notes |
|---|---|---|
| `id` | BigInteger PK | Identity sequence |
| `team_member_id` | String(50) | Candidate |
| `correlation_id` | String(100) | Links back to the requisition |
| `reviewer_email` | String(100) | Who reviewed |
| `liked` | Boolean | Quick thumbs indicator |
| `rating` | SmallInteger | 1–5 (CHECK constraint) |
| `comment` | Text | Free-text feedback |
| `created_at` | DateTime(tz) | |
| `updated_at` | DateTime(tz) | Auto-updated by DB trigger |

Unique: `(team_member_id, correlation_id, reviewer_email)` — one review per person per requisition per reviewer.

---

### Ingestion & Batch Processing

#### `ingestion_batch_state`
Lifecycle tracker for profile ingestion runs.

| Column | Type | Notes |
|---|---|---|
| `batch_id` | String(100) PK | |
| `correlation_id` | String(100) | Tracing token |
| `status` | String(20) | PENDING / PROCESSING / COMPLETED / FAILED |
| `total_records` | Integer | Expected count |
| `processed_records` | Integer | Success count |
| `failed_records` | Integer | Failure count |
| `started_at` | DateTime | |
| `completed_at` | DateTime | |
| `error_message` | Text | Top-level error if FAILED |
| `metadata` | JSONB | Extra context |

#### `ingestion_audit_log`
Append-only event stream for a batch. Deleted when parent batch is deleted (`CASCADE`).

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `batch_id` | String(100) FK CASCADE → ingestion_batch_state | |
| `correlation_id` | String(100) | |
| `event_type` | String(50) | START / PROCESS / COMPLETE / FAIL etc. |
| `event_details` | JSONB | Event-specific payload |
| `timestamp` | DateTime | |
| `severity` | String(20) | INFO / WARN / ERROR |
| `source` | String(100) | Component that emitted the event |

---

### Logging & Audit

#### `llm_request_log`
Tracks every LLM call for cost analysis and debugging.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `request_id` | String(64) | Linked requisition (no FK — for flexibility) |
| `agent_name` | String(255) | Which agent made the call |
| `prompt_name` | String(255) | Logical name of the prompt |
| `model` | String(255) | LLM model used |
| `prompt_tokens` | Integer | |
| `completion_tokens` | Integer | |
| `total_tokens` | Integer | |
| `cost_usd` | Numeric(10,6) | Computed cost |
| `status` | String(50) | Default `SUCCESS` |
| `error_message` | Text | Populated on failure |
| `created_at` | DateTime | |

#### `langgraph_checkpoints`
Snapshot of the AI agent graph state at each node, used for debugging and potential resume.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `request_id` | String(64) FK → requisition_requests | |
| `node_name` | String(50) | Graph node that produced the snapshot |
| `state_json` | JSONB | Full graph state at this point |
| `token_count` | Integer | Tokens consumed up to this node |
| `created_at` | DateTime | |

#### `pii_scrub_audit`
Compliance log for all PII scrubbing operations. **Immutable** — a DB trigger blocks UPDATE and DELETE.

| Column | Type | Notes |
|---|---|---|
| `id` | BigInteger PK | Part of composite PK for partitioning |
| `timestamp` | DateTime(tz) PK | Partition key |
| `operation` | String(50) | scrub / tokenize / validate |
| `entity_type` | String(50) | requisition / team_member |
| `entity_id` | String(100) | ID of the affected entity |
| `field_name` | String(100) | Which field was scrubbed |
| `pii_type` | String(50) | name / email / phone / client_name etc. |
| `action_taken` | String(50) | redacted / tokenized / pattern_matched |
| `original_value_hash` | String(64) | SHA-256 of original — raw value never stored |
| `scrubbed_value` | Text | Safe replacement value |
| `detection_method` | String(50) | ner / regex / whitelist |
| `confidence_score` | Numeric(5,4) | 0.0000 – 1.0000 |
| `user_id` | BigInteger | Who triggered the operation |
| `session_id` | String(100) | |
| `metadata` | JSONB | Additional context |

Partitioned by `RANGE(timestamp)` — monthly partitions recommended for 7-year retention policy (NFR-PII-003).

---

## Special Design Patterns

### Soft Deletes
`team_member_allocation` and `team_member_skill` have an `is_deleted` flag. Records are never hard-deleted — always filter with `WHERE is_deleted = false`.

### SHA-256 Deduplication
Two places use content hashing to prevent duplicate work:
- `requisition_detail.payload_hash` — identical payloads are rejected at the DB level (UNIQUE constraint)
- `team_member_embeddings.content_hash` — embedding pipeline skips members whose profile text has not changed

### Multi-Vector Embeddings
Each team member has **three separate vectors** in `team_member_embeddings`:
- `resume_embedding` — general resume/experience content
- `skills_embedding` — skills-focused text
- `certifications_embedding` — certifications text

This allows the matching pipeline to query each dimension independently and weight them differently per requisition.

### Immutable Audit Log
`pii_scrub_audit` enforces append-only writes via a PostgreSQL trigger (`prevent_pii_audit_modification_trigger`). Any `UPDATE` or `DELETE` raises an exception at the DB level — application code cannot bypass this.

### Composite Foreign Key
`team_member_skill_certification` links to `team_member_skill` via a composite FK on `(team_member_id, skill_id)` because the parent table's PK is itself composite.

---

## Enum Types

### `work_type_enum` (PostgreSQL native enum)
Used in `team_member.work_type`.

| Value | Meaning |
|---|---|
| `wfo` | Work from office |
| `wfh` | Work from home |
| `hybrid` | Mix of both |
