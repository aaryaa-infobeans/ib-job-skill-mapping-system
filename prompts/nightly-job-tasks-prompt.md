Below is the **final, augmented GitHub Spec Kit `/speckit.task` prompt**, updated to **explicitly mandate unit test coverage**, coverage thresholds, and CI enforcement—while preserving everything already agreed (batch ingestion, Alembic, retry isolation, API-Gateway regression).

You can use this **as-is**.

---

# ✅ GitHub Spec Kit `/speckit.task` Prompt

*(with Unit Test Coverage + API-Gateway Regression)*

```
/speckit.task
```

## 🎯 Tasking Objective

Generate a **granular, execution-ready task list** to implement the **Python-based nightly batch ingestion system** as defined in:

* `/specs/cron` (from `/specify`)
* `/specs/cron/implementation-plan.md` (approved implementation plan)

WITH the following **non-negotiable quality guarantees**:

* ✔ Batch retry isolation by `batch_id`
* ✔ Alembic-managed schema evolution
* ✔ **Zero regression in existing API-Gateway features**
* ✔ **Enforced unit test coverage thresholds**

Each task MUST be:

* Independently implementable
* Objectively testable
* Reviewable with evidence
* Traceable to a specific phase and directory

---

## 🧠 Task Author Persona (MANDATORY)

You are a **Senior Software Engineer / Tech Lead** operating in a **shared production platform**.

Your responsibility is to:

* Deliver new ingestion capability
* **Preserve existing API-Gateway behavior**
* **Prove correctness via unit tests, regression tests, and coverage metrics**

No redesign, scope creep, or undocumented assumptions are permitted.

---

## 📁 Mandatory Directory Structure (ENFORCED)

All tasks MUST reference files strictly within this structure (tests included):

```
ib-job-skill-mapping-system/
├── alembic/
│   ├── versions/
│   │   └── 0002_nightly_batch_ingestion_schema.py
│   ├── env.py
│   ├── script.py.mako
│   └── README
│
├── app/cron/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── scheduler.py
│   ├── oauth/
│   │   ├── __init__.py
│   │   └── token_client.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── external_client.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── metadata.py
│   │   ├── repositories.py
│   │   └── migrations_check.py
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── batch_processor.py
│   │   └── retry_manager.py
│   └── utils/
│       ├── __init__.py
│       └── logging.py
│
├── main.py
│
├── scripts/
│   └── run_ingestion.sh
├── tests/cron
│   ├── unit/
│   │   ├── oauth/
│   │   ├── api/
│   │   ├── db/
│   │   ├── processing/
│   │   └── utils/
│   ├── ingestion/
│   ├── test_batch_processing.py
│   └── api_gateway/
│       └── regression/
├── alembic.ini
├── requirements.txt
├── README.md
└── .env.example
```

⚠️ Tasks proposing files outside this structure MUST be rejected.

---

## 🧱 Global Task Rules

* Tasks MUST follow the approved phase order
* Each task MUST include:

  * **Task ID**
  * **Phase**
  * **Description**
  * **Files / Directories impacted**
  * **Dependencies**
  * **Acceptance Criteria**
  * **Validation Evidence**
* No task may span multiple phases
* No implementation code in task output

---

## 📌 Required Task Breakdown (FINAL)

### 🔹 Phase 0 – Repository & Scaffolding

Tasks for:

* Repo bootstrap
* Dependency management
* Test directory scaffolding
* Coverage tooling setup (pytest + coverage)

---

### 🔹 Phase 1 – Database & Alembic Baseline

Tasks for:

* Alembic initialization
* Baseline migration (`0001_initial_schema.py`)
* Schema backward-compatibility validation
* Migration impact analysis on API-Gateway queries

---

### 🔹 Phase 2 – OAuth & External API Integration

Tasks for:

* OAuth token retrieval
* Token caching & refresh logic
* External GET API client
* Header & correlation ID propagation
* Unit tests for all OAuth and API clients

---

### 🔹 Phase 3 – Batch Ingestion & Persistence

Tasks for:

* Payload validation logic
* Category & skill normalization
* UPSERT logic for:

  * `category_master`
  * `skill_master`
  * `team_member`
  * `team_member_allocation`
  * `team_member_skill`
  * `team_member_skill_certification`
* Transaction boundary enforcement
* Unit tests covering:

  * Happy path
  * Duplicate data
  * Partial payloads

---

### 🔹 Phase 4 – Batch Retry & Failure Isolation

Tasks for:

* Batch failure detection
* Retry logic keyed by `batch_id`
* Exponential backoff
* Idempotency guarantees
* Unit tests simulating:

  * Failure on first attempt
  * Successful retry
  * No reprocessing of successful batches

---

### 🔹 Phase 5 – Scheduling & Runtime Execution

Tasks for:

* CLI execution flow
* Cron configuration (2:00 AM IST)
* Manual re-run (`--batch-id`)
* Dry-run mode
* Unit tests for CLI argument parsing & execution paths

---

### 🔹 Phase 6 – Testing, Coverage & Validation (EXTENDED)

#### 🔸 Unit Test Coverage (MANDATORY)

Generate explicit tasks to:

* Implement unit tests under:

  ```
  tests/unit/
  ```
* Cover:

  * OAuth client
  * External API client
  * Batch processor
  * Retry manager
  * Repository / DB logic
  * Migration checks
* Enforce **minimum coverage thresholds**:

  * Overall: **≥ 85%**
  * Critical paths (processing, retry, DB): **≥ 90%**
* Fail CI if coverage drops below threshold
* Produce coverage reports (HTML + XML)

---

#### 🔸 API-Gateway Regression Tests (MANDATORY)

Tasks for:

* Baseline capture of existing API-Gateway behavior
* Regression tests under:

  ```
  tests/api_gateway/regression/
  ```
* Validate:

  * Response shape (no breaking changes)
  * Status codes
  * Pagination & filters
  * Performance thresholds
* Validate API behavior:

  * Before ingestion
  * After ingestion
  * After batch failure & retry

---

### 🔹 Phase 7 – Operational Readiness

Tasks for:

* Logging & observability
* Error taxonomy alignment
* Runbook updates
* Rollback validation
* **Coverage + regression sign-off gate before production**

---

## 🧪 Acceptance & Validation Rules

For EVERY task, define:

* What “done” means
* How it is validated
* Required evidence:

  * Test reports
  * Coverage reports
  * Regression comparison artifacts
  * Migration diffs

Tasks related to coverage MUST include:

* Exact coverage % achieved
* CI enforcement proof

---

## 🚦 Constraints

* Python only
* Alembic mandatory
* No breaking API-Gateway changes
* No schema drift
* No reprocessing of successful batches
* No secrets in code
* Coverage thresholds are **non-negotiable**

---

## 📤 Output Requirements

The `/speckit.task` output MUST:

* Be **Markdown**
* Be task-granular
* Be convertible into:

  * GitHub Issues
  * Jira tickets
* Clearly separate:

  * Ingestion tasks
  * Regression tasks
  * Coverage enforcement tasks
* Avoid vague or advisory language

---

## ✅ Success Criteria

A delivery team must be able to:

* Implement ingestion safely
* Prove batch correctness
* **Demonstrate ≥85% unit test coverage**
* **Demonstrate zero API-Gateway regression**
* Deploy with objective, auditable evidence


