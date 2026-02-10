Perfect. Below is the **revised `/speckit.plan` prompt** with the **explicit directory structure added as a first-class planning artifact** and referenced consistently across phases.

You can copy-paste this **as-is** into GitHub Spec Kit.

---

# ✅ GitHub Spec Kit `/speckit.plan` Prompt

*(with enforced directory structure)*

```
/speckit.plan
```

## 🎯 Planning Objective

Generate a **phase-wise, execution-ready implementation plan** to build the previously specified **Python-based nightly batch ingestion service** that:

* Uses **OAuth 2.0 (Client Credentials)**
* Consumes an **external GET API** returning Team Member Skill & Availability payloads
* Processes data in **batches**
* Persists into relational tables using **idempotent UPSERTs**
* Retries **only failed batches** using `batch_id`
* Manages schema evolution using **Alembic**
* Runs nightly at **2:00 AM IST**
* Conforms **strictly** to the directory structure defined below

The plan must be **engineering-ready**, **risk-aware**, and suitable for **direct execution**.

---

## 🧠 Planner Persona (MANDATORY)

You are a **Principal Engineer / Technical Program Lead** with deep experience in:

* Python ingestion systems
* Database migration governance (Alembic)
* OAuth-secured integrations
* Batch reliability & retry isolation
* Production cron / K8s scheduling

You optimize for **clarity, incremental delivery, and operational safety**.

---

## 📁 Mandatory Directory Structure (NON-NEGOTIABLE)

All phases and tasks MUST reference and produce artifacts **within this structure**:

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
│
├── tests/
│   └── test_batch_processing.py
│
├── alembic.ini
├── requirements.txt
├── README.md
└── .env.example
```

⚠️ **No deviation, flattening, or restructuring is allowed.**

---

## 🧱 Planning Constraints

* Follow existing `/specs/cron` exactly
* Python only
* Alembic mandatory for all schema changes
* No schema redesign
* Batch retry isolation is mandatory
* No reprocessing of successful batches

---

## 📌 Required Plan Structure

### 1️⃣ Phase Breakdown

Divide work into **clear, sequential phases**, such as:

* Phase 0 – Repository & scaffolding
* Phase 1 – Database & Alembic baseline
* Phase 2 – OAuth & external API integration
* Phase 3 – Batch ingestion & persistence
* Phase 4 – Retry & failure isolation
* Phase 5 – Scheduling & operations
* Phase 6 – Hardening & validation

Each phase MUST specify:

* Purpose
* Related `/specs/cron` references
* Directories/files involved
* Validation checkpoints

---

### 2️⃣ Task-Level Execution Plan

For each phase, define **atomic tasks** with:

* **Task name**
* **Description**
* **Directory / file(s) impacted**
* **Dependencies**
* **Deliverables**
* **Acceptance criteria**

Example:

> Task: Implement OAuth token retrieval
> Location: `app/oauth/token_client.py`
> Depends on: Phase 0
> DoD: Token cached, refreshed, error-handled

---

### 3️⃣ Alembic & Schema Governance Plan

Explicitly include:

* Baseline migration (`0001_initial_schema.py`)
* Forward-only migration policy
* Alembic revision validation via `migrations_check.py`
* Enforcement before batch execution

---

### 4️⃣ Batch Processing & Retry Plan

Define:

* Batch lifecycle using `metadata.batch_id`
* Transaction boundaries in `batch_processor.py`
* Retry logic in `retry_manager.py`
* How partial writes are prevented

---

### 5️⃣ Scheduling & Runtime Plan

Include:

* CLI execution flow via `app/main.py`
* Nightly cron execution using `scripts/run_ingestion.sh`
* Manual re-run with `--batch-id`
* Dry-run mode

---

### 6️⃣ Testing Strategy Plan

Cover:

* Unit tests (`tests/`)
* Batch retry simulation
* DB integration tests
* Alembic revision compatibility checks

---

### 7️⃣ Risk & Mitigation Table

Include:

* OAuth outages
* Partial batch failure
* Schema drift
* Duplicate ingestion
* Cron misfires

---

### 8️⃣ Definition of Done (DoD)

Provide:

* Phase-level DoD
* System-level DoD
* Production readiness checklist

---

## 📤 Output Expectations

The `/speckit.plan` output MUST:

* Be **Markdown only**
* Reference the directory structure explicitly
* Be implementation-oriented
* Avoid generic advice
* Be convertible directly into engineering tickets

---

## 🚦 Success Criteria

A senior engineer must be able to:

* Implement directly from the plan
* Validate each phase independently
* Deploy safely to production
* Operate without undocumented assumptions

---
