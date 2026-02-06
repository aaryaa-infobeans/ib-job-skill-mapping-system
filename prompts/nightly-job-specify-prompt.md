Below is an **updated GitHub Spec Kit `/specify` command prompt** that **explicitly integrates Alembic** for database schema migrations, aligned with your **Python nightly batch ingestion service**, OAuth-based GET consumption, batch retry by `batch_id`, and the target tables you listed.

You can use this **as-is** with GitHub Spec Kit.

---

# ✅ GitHub Spec Kit `/specify` Command Prompt (with Alembic)

```
/specify
```

## 🎯 Objective

Generate a **complete technical specification** for a **Python-based nightly batch ingestion service** that:

1. Authenticates with an **external system using OAuth 2.0 (Client Credentials)**
2. Consumes a **GET-based external API** that returns a **Team Member Skill & Availability payload**
3. Processes data in **batches**
4. Persists data into the following database tables of existing database `ib_job_skill_mapping` running in dockerized container:

   * `category_master`
   * `skill_master`
   * `team_member`
   * `team_member_allocation`
   * `team_member_skill`
   * `skill_certification`
5. Uses **Alembic** to manage **database schema migrations**
6. Retries **only the failed batch** based on `batch_id`
7. Runs as a **Python script schedulable nightly at 2:00 AM IST**

---

## 🧠 System Persona (MANDATORY)

You are a **Senior Python Platform Architect & Data Engineer** with deep expertise in:

* OAuth 2.0 (Client Credentials)
* Python ETL pipelines
* Alembic & SQLAlchemy Core
* PostgreSQL schema evolution
* Idempotent batch processing
* Failure isolation & retry mechanisms
* Cron / Kubernetes CronJob scheduling

You reason step-by-step and document assumptions and trade-offs explicitly.

---

## 🔐 Authentication & API Consumption

### OAuth 2.0

* Client Credentials Grant
* Secure token retrieval and caching
* Token refresh before expiry
* No secrets hardcoded (env / vault only)

### External API

```
GET {external_base_url}/api/v1/team-members/skill-availability/bulk-upsert
```

**Headers**

* `Authorization: Bearer <access_token>`
* `X-Correlation-ID`
* `X-Batch-ID`

> Constraint: GET is non-standard for bulk data retrieval intended for persistence.
> This must be documented as a **legacy external constraint**.

---

## 📦 Payload & Batch Semantics

* Payload contains:

  * `metadata.batch_id`
  * `metadata.batch_number`
  * `metadata.total_batches`
  * `team_members[]`
* Each batch must be:

  * Independently processed
  * Transactionally isolated
  * Idempotent
* Batch failure must not affect other batches

---

## 🗄️ Database & Alembic Requirements

### Database Strategy

* PostgreSQL (assumed unless stated otherwise)
* SQLAlchemy **Core** preferred over ORM for ingestion paths
* Explicit UPSERT (`ON CONFLICT`) semantics

### Alembic Integration (MANDATORY)

The specification MUST define:

1. **Alembic Project Structure**

   ```
   alembic/
     versions/
   alembic.ini
   ```

2. **Migration Ownership**

   * All schema changes must be expressed via Alembic revisions
   * No manual DDL in runtime ingestion code

4. **Versioning Rules**

   * One logical change per migration
   * Forward-only migrations (no destructive downgrade in prod)
   * Explicit revision dependencies

5. **Runtime Enforcement**

   * Ingestion job MUST:

     * Check current Alembic revision
     * Fail fast if schema is behind expected revision

6. **Environment Support**

   * Separate migration configs for:

     * local
     * test
     * prod

---

## 🔁 Batch Processing & Retry Rules

* Each batch processed within a single DB transaction
* On failure:

  * Rollback transaction
  * Persist failure state keyed by `batch_id`
* Retry behavior:

  * Retry only failed `batch_id`
  * Configurable max retries
  * Exponential backoff
* Successful batches must never be reprocessed

---

## ⏰ Scheduling Requirements

* Python CLI-executable script
* Default cron schedule:

  ```
  0 2 * * *
  ```
* Support:

  * Manual run
  * `--batch-id` retry
  * `--dry-run`

---

## 🧱 Required Specification Outputs

### `/specs/cron/architecture.md`

* End-to-end architecture
* OAuth → Fetch → Validate → Persist → Retry
* Mermaid sequence diagram

### `/specs/cron/alembic-migrations.md`

* Alembic setup
* Migration lifecycle
* Versioning policy
* Failure scenarios

### `/specs/cron/database-mapping.md`

* Payload → Table mapping
* Natural keys
* UPSERT logic

### `/specs/cron/api-integration.md`

* OAuth flow
* Error handling
* Rate limits

### `/specs/cron/batch-processing.md`

* Batch lifecycle
* Retry semantics
* Idempotency guarantees

### `/specs/cron/scheduler.md`

* Cron setup
* Deployment options

### `/specs/cron/error-handling.md`

* Error taxonomy
* Logging & observability

### `/specs/cron/non-functional-requirements.md`

* Performance
* Security
* Auditability
* Scalability

---

## 🧪 Validation & Quality Gates

* Alembic revision validation before job execution
* Schema compatibility checks
* Transaction rollback on failure
* Explicit assumptions
* Definition of Done (DoD)

---

## 🚦 Constraints

* Python only
* Alembic mandatory for schema evolution
* No schema changes outside migrations
* No hardcoded secrets
* No reprocessing of successful batches

---

## 📌 Deliverable Standard

* Markdown only
* GitHub-review ready
* Deterministic and reproducible
* Production-grade, enterprise-compliant

---
