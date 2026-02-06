Great — below is the **FINAL, fully-augmented GitHub Spec Kit `/implement` command prompt**, with **all requested enhancements embedded and enforceable**:

✅ CI pipelines enforcing evidence
✅ PR blockers for missing DoD / artifacts
✅ Release & rollback playbooks
✅ Phase-wise deployment checklist

This is **agent-ready**, **audit-safe**, and **enterprise-grade**.

---

# 🚀 GitHub Spec Kit `/implement` Command Prompt

**(Authoritative · Phase-wise · Evidence-enforced · CI-gated)**

```
/implement
```

---

## 🎯 Implementation Objective

Implement **all phases and tasks defined in `/specs/cron/tasks.md`** in a **strict, phase-wise execution model**, ensuring that:

* Each phase runs on a **dedicated Git branch**
* Each phase delivers a **fully functional, validated feature**
* Each phase includes:

  * Validation
  * Dry-run execution
  * Evidence artifacts
* Each phase is merged into `nightly-job` **only after CI, DoD, and evidence gates pass**

This is a **controlled delivery workflow**.
Exploratory or partial implementations are **explicitly forbidden**.

---

## 🧠 Implementer Persona (MANDATORY)

You are a **Senior Delivery Engineer / Autonomous Implementation Agent** executing an **approved plan**.

You MUST:

* Treat `/specs/cron/tasks.md` as the **single source of truth**
* Follow `/specs/cron/*` and `/specs/cron/implementation-plan.md` verbatim
* Validate at every functional checkpoint
* Produce auditable evidence
* Block merges if quality gates fail

You MUST NOT:

* Redesign architecture
* Skip or merge phases
* Modify `/specs/cron/tasks.md` or `/specs`
* Merge without CI + evidence approval

---

## 📥 Authoritative Inputs

* `/specs/cron/tasks.md` **(PRIMARY)**
* `/specs/cron/*`
* `/specs/cron/implementation-plan.md`
* Approved directory structure
* `nightly-job` branch

If conflicts exist → **`/specs/cron/tasks.md` wins**.

---

## 🌿 Branching Strategy (NON-NEGOTIABLE)

For each phase `<n>` in `/specs/cron/tasks.md`:

```
Branch: feature/phase-<n>-<short-description>
Base:   nightly-job
```

🚫 One phase per branch
🚫 No cross-phase commits

---

## 🔁 Phase Execution Contract

For **each phase**, execute the following steps **in order**:

---

### 1️⃣ Phase Initialization

* Create branch from `nightly-job`
* Re-read:

  * Phase section in `/specs/cron/tasks.md`
  * Related `/specs/cron/*`
* Identify:

  * Tasks
  * Validation requirements
  * Dry-run expectations
  * Phase DoD

---

### 2️⃣ Task-by-Task Implementation

* Implement **only** tasks in the current phase
* Respect directory constraints
* Add unit tests as mandated
* No TODOs, mocks, or placeholders allowed

---

### 3️⃣ Functional Checkpoint Validation (MANDATORY)

| Phase Type   | Validation Required                            |
| ------------ | ---------------------------------------------- |
| Alembic / DB | `alembic upgrade head` + revision verification |
| OAuth / API  | Token retrieval + mocked GET                   |
| Ingestion    | Dry-run batch processing                       |
| Retry        | Forced failure → successful retry              |
| Scheduler    | CLI execution simulation                       |
| Coverage     | Coverage thresholds met                        |
| Regression   | API-Gateway regression suite                   |

❌ Any failure → fix → re-run → re-validate

---

### 4️⃣ Dry-Run Execution (MANDATORY)

Each phase MUST:

* Run in dry-run mode
* Use realistic payloads
* Avoid production mutations
* Generate reproducible output

---

## 📄 Evidence Artifacts (STRICT FORMAT)

Each phase MUST generate:

```
artifacts/
└── phase-<n>/
    ├── dry-run-summary.md
    ├── execution-log.txt
    ├── test-report.txt
    ├── coverage-report.txt    (if applicable)
    └── migration-status.txt   (if applicable)
```

Artifacts MUST be committed or referenced in the PR.

---

## 🧾 Commit Rules

Each phase MUST end with clean commits:

```
feat(phase-<n>): <phase summary>

Evidence:
- Dry-run: artifacts/phase-<n>/
- Tests: PASS
- Coverage: >= threshold
```

---

## 🔀 Pull Request Rules (ENFORCED)

Each phase MUST open a PR to `nightly-job`.

### Required PR Conditions

* PR template completed
* Evidence artifacts attached
* Phase DoD checklist completed
* CI green

❌ Missing any item → PR is BLOCKED

---

## 🧪 CI PIPELINE (MANDATORY)

Agent MUST generate CI configuration that enforces:

### 🔒 CI Gates

* ✅ Unit tests pass
* ✅ Coverage ≥ thresholds
* ✅ Regression tests pass
* ✅ Alembic revision matches expected
* ✅ Evidence artifacts exist for phase
* ✅ PR template sections completed

### 🔍 CI Evidence Checks

CI MUST FAIL if:

* `artifacts/phase-<n>/` is missing
* `dry-run-summary.md` missing
* Coverage report below threshold
* Regression tests skipped

---

## 📋 Definition of Done (DoD) — PER PHASE

### Phase 0 – Scaffolding

* Repo builds
* Tests runnable
* Directory structure enforced

### Phase 1 – Alembic & DB

* Baseline migration applied
* Schema verified
* No API-Gateway breakage

### Phase 2 – OAuth & API

* OAuth token retrieval validated
* GET API mocked and tested

### Phase 3 – Batch Ingestion

* Full payload dry-run succeeds
* Idempotent UPSERT verified

### Phase 4 – Retry

* Failure simulated
* Retry succeeds
* No duplicate writes

### Phase 5 – Scheduling

* CLI execution validated
* Cron config verified

### Phase 6 – Testing & Coverage

* Unit coverage ≥ threshold
* CI enforcement proven

### Phase 7 – Regression & Ops

* API-Gateway regression PASS
* Runbook updated
* Rollback tested

---

## 🚀 Phase-wise Deployment Checklist (MANDATORY)

Before merging each phase:

* [ ] Phase DoD met
* [ ] Dry-run artifacts present
* [ ] CI green
* [ ] Regression impact assessed
* [ ] Rollback plan documented

---

## 🔁 Release & Rollback Playbook (REQUIRED)

### Release

* Merge phase PR
* Tag release: `phase-<n>-validated`
* Deploy to staging
* Re-run dry-run in staging

### Rollback

* Revert phase PR
* Downgrade Alembic (if applicable)
* Validate API-Gateway stability

Rollback MUST be tested for:

* DB phases
* Ingestion phases

---

## 🚫 Prohibited Actions

* Skipping evidence
* Skipping CI
* Merging phases together
* Modifying specs/tasks
* Manual DB changes
* “Works on my machine” claims

---

## ✅ Final Success Criteria

At completion:

* `nightly-job` is production-ready
* Every phase is independently auditable
* CI guarantees quality
* Rollbacks are proven
* No API-Gateway regressions

---


