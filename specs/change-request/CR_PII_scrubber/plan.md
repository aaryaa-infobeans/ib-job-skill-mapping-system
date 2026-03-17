# CR-PII-001: PII Scrubber Implementation Plan

**Change Request:** CR-PII-001 (PII Scrubber for RAG Pipeline)  
**Plan Version:** 2.0.0  
**Generated:** 2026-02-17  
**Updated:** 2026-02-17  
**Status:** Ready for Execution  
**Planning Horizon:** 4-5 weeks  
**Deployment Strategy:** One-Shot Rollout  

---

## Executive Summary

This implementation plan translates the approved CR-PII-001 specification into an actionable, **one-shot deployment** roadmap. The plan follows a branch-driven development strategy with comprehensive pre-deployment validation, ensuring zero-downtime migration while protecting $45M ARR in at-risk revenue and achieving $7.5M annual risk reduction through GDPR/CCPA compliance.

**Key Deliverables:**
- 4-week development + 1-week deployment with comprehensive pre-production testing
- One-shot 100% rollout with full regression validation in staging
- Zero-downtime migration of 250,000 legacy embeddings (completed pre-deployment)
- 150 new tests (100 unit, 30 integration, 20 compliance)
- 5 operational runbooks + 4 ADRs
- Full audit trail with 7-year retention

**Critical Success Factors:**
- F1-score ≥ 0.90 for NER detection (validated in staging)
- False positive rate ≤ 3% (validated on production-like data)
- Scrubbing latency ≤ 50ms (p95) (load tested at 2x production capacity)
- 100% backward compatibility (validated with legacy data)
- < 30 minute rollback capability (blue-green deployment)
- 100% backfill completion before production deployment

---

## 1. Implementation Phases

### Phase 1: Infrastructure & Core Development (Week 1)

**Scope:** Foundational infrastructure, dependencies, tooling, and core scrubber engine development.

**Linked Spec References:**
- NFR-PII-001 (Performance requirements)
- NFR-PII-003 (Audit logging)
- FR-PII-001 to FR-PII-004 (All scrubbing requirements)
- Section 8.1 (Migration strategy)

**Infrastructure Tasks:**
- [x] Stakeholder approval obtained (CISO, DPO, Legal, Engineering)
- [ ] Provision GPU instance (NVIDIA T4) for NER model hosting
- [ ] Install SpaCy `en_core_web_trf` model (560MB) + validation
- [ ] Create `pii_scrub_audit` table + rollback scripts
- [ ] Configure Prometheus metrics + Grafana dashboards
- [ ] Set up PagerDuty integration for critical alerts
- [ ] Establish CI/CD pipeline gates (test coverage ≥ 85%, performance regression checks)

**Core Development Tasks (Parallel Track):**

- [ ] Implement pattern loader from YAML config (`pii-scrubbing-rules-v1.yaml`)
- [ ] Build regex engine for: email (100% recall), phone (95% recall), DOB (90% recall)
- [ ] Add Unicode support for international names/addresses
- [ ] Integrate SpaCy `en_core_web_trf` with GPU acceleration
- [ ] Implement CPU fallback for degraded mode (if GPU unavailable)
- [ ] Configure confidence thresholds: STRICT (≥0.50), BALANCED (≥0.85)
- [ ] Build entity detection for: PERSON, GPE, ORG, DATE, CARDINAL
- [ ] Whitelist integration for skill names (Python, Java, Ruby, etc.)
- [ ] Implement hash-based tokenization (deterministic SHA-256 tokens)
- [ ] Build fuzzy matching engine (Levenshtein, threshold=0.85)
- [ ] Client/project name detection from database sources (refresh every 1h)
- [ ] Implement deterministic replacement engine (salt-based hashing, masking)
- [ ] Create audit record schema and immutable audit log
- [ ] Implement observability integration (Prometheus metrics, structured logging)
- [ ] Unit tests: 100 tests covering all components (AC-F-001 through AC-F-008)

**Exit Criteria:**
- ✅ All infrastructure components pass health checks
- ✅ NER model F1-score ≥ 0.90 on 5,000-sample test set
- ✅ False positive rate ≤ 3% on skill/tech terms
- ✅ Scrubbing latency ≤ 50ms p95 (validated in test environment)
- ✅ 100 unit tests pass with ≥ 95% code coverage
- ✅ All FR-PII-001 through FR-PII-004 implemented

**Duration:** 1 week  
**Owner:** Platform Engineering + Backend Engineering Team  
**Risk Level:** MEDIUM

---

### Phase 2: Integration & Testing (Week 2)

**Scope:** LangGraph integration, state schema updates, database migrations, comprehensive testing.

**Linked Spec References:**
- Section 5.1 (Pipeline topology)
- Section 11.1 (Graph topology impact)
- ai/graph-topology.md v1.1
- ai/state-schema.md v1.1

**Integration & Migration Tasks:**
- [ ] Define `PII_Scrubber_Agent` class implementing `BaseAgent` interface
- [ ] Add edge: `START` → `PII_Scrubber_Agent` → `JD_Parsing_Agent`
- [ ] Add `PIIScrubMetadata` dataclass and `pii_scrubbed` flag to state schema
- [ ] Create validation checkpoint (reject unscrubbed data with HTTP 422)
- [ ] Create Alembic migration: add columns, indexes (CONCURRENTLY)

- [ ] Create Alembic migration: add columns, indexes (CONCURRENTLY)
- [ ] Update graph topology diagram in specs/ai/graph-topology.md

**Testing Tasks:**
- [ ] Integration tests: 30 tests (pipeline, database, API, retrieval)
- [ ] Compliance tests: 20 tests (GDPR, CCPA, audit trail, PII leak detection)
- [ ] Performance tests: Load test at 20,000 profiles/min (2x production capacity) for 1 hour
- [ ] Chaos tests: Fail-closed behavior, circuit breakers, degraded mode

**Exit Criteria:**
- ✅ Node 0 successfully inserts before all existing agents
- ✅ Validation gate rejects 100% of unscrubbed data in tests
- ✅ State schema backward compatible with existing checkpoints
- ✅ Database migration completes without locks (< 5 sec)
- ✅ 50 integration + compliance tests pass
- ✅ Load test passes at 20,000 profiles/min
- ✅ LangGraph end-to-end validated (100 test requisitions)

**Duration:** 1 week  
**Owner:** AI/Backend Engineering + QA Team  
**Risk Level:** MEDIUM-HIGH

---

### Phase 3: Pre-Production Validation (Weeks 3-4)

**Scope:** Complete backfill in staging, validate match quality, comprehensive regression testing.

**Linked Spec References:**
- Section 8.1 (Backfill strategy)
- AC-M-001 (Backfill completion)
- AC-M-002 (Match quality preservation)

**Staging Backfill Tasks:**
- [ ] Deploy scrubber to staging environment
- [ ] Execute complete backfill in staging: 250,000 legacy records
  - Batch processing: 25,000 records/day (accelerated for staging)
  - Checksum validation: 100% of records
  - Integrity verification: Row counts, full PII leak scans
- [ ] Validate audit logs created for all backfilled records
- [ ] Validate 0 raw PII in `profile_text_scrubbed` (scan all 250,000 records)

**Validation Tasks:**
- [ ] A/B testing in staging: Match quality scrubbed vs. unscrubbed
  - Validate match quality within ±5% baseline (AC-M-002)
  - Test with 10,000 realistic requisitions
  - Measure retrieval latency (≤ 200ms p95)
- [ ] Full regression testing against staging
  - All 150 tests (unit + integration + compliance)
  - Performance benchmarks at 2x production load
  - Penetration testing: Attempt PII extraction
- [ ] Automated PII leak scans: Logs, metrics, traces (expect 0)
- [ ] Manual review: 1,000 random scrubbed profiles for false positives

**Production Preparation:**
- [ ] Create production backfill scripts (optimized from staging)
- [ ] Document backfill execution plan
- [ ] Schedule backfill window (off-peak hours)
- [ ] Test and validate rollback procedure in staging

**Exit Criteria:**
- ✅ Staging backfill 100% complete (250,000 records)
- ✅ 0 data loss (checksum validation passes)
- ✅ 0 PII detected in backfilled records (full scan)
- ✅ Match quality within ±5% baseline (A/B test)
- ✅ All 150 tests pass in staging
- ✅ Load test passes at 20,000 profiles/min
- ✅ False positive rate ≤ 3%
- ✅ 0 PII leaks in logs/metrics/traces
- ✅ Rollback procedure tested successfully

**Duration:** 2 weeks  
**Owner:** Backend Engineering + Data Team + QA  
**Risk Level:** HIGH (critical validation phase)

---

### Phase 4: Production Deployment (Week 5)

**Scope:** One-shot 100% production rollout with pre-completed backfill, blue-green deployment.

**Linked Spec References:**
- Section 13.3 (Deployment plan - one-shot)
- Section 9 (Rollback strategy)
- All acceptance criteria (AC-F-*, AC-NF-*, AC-C-*, AC-M-*)

**Pre-Deployment - Days 1-2:**
- [ ] Execute production backfill (off-peak hours, 5-day window)
  - Process 250,000 legacy records using proven staging scripts
  - Target: 50,000 records/day
  - Continuous monitoring: Checksums, PII leak scans
- [ ] Verify 100% backfill completion
- [ ] Final validation: 0 PII in production backfilled records (scan 10,000 sample)

**Deployment - Day 3:**
- [ ] Deploy scrubber to production (blue-green strategy)
  - Blue: Current production (no scrubber)
  - Green: New production (with scrubber)
- [ ] Run smoke tests in green (100 test requisitions)
- [ ] Validate green environment health (infrastructure, NER model, audit logging, metrics)
- [ ] Switch 100% traffic to green (atomic cutover)
- [ ] Monitor 4-hour critical observation period:
  - Scrubber error rate < 1%
  - Scrubbing latency ≤ 50ms p95
  - Match quality within ±5% baseline
  - 0 PII leaks in logs
  - No customer escalations
- [ ] Enable database constraint: `CHECK (pii_scrubbed = TRUE)`
- [ ] Update RAG queries: `WHERE pii_scrubbed = TRUE`

**Post-Deployment - Days 4-5:**
- [ ] 48-hour monitoring:
  - Automated PII leak scanning
  - Performance monitoring (latency, throughput, errors)
  - Match quality validation
  - Customer feedback monitoring
- [ ] Decommission blue environment (if no issues)
- [ ] Archive legacy embeddings to S3 (encrypted, 7-year retention)
- [ ] Generate compliance reports (GDPR, CCPA, ISO 27001, SOC 2)

**Exit Criteria:**
- ✅ Production backfill 100% complete (250,000 records)
- ✅ 100% traffic scrubbed for 48 hours with 0 critical issues
- ✅ Database constraint enforced
- ✅ 0 PII leaks detected (automated + manual review)
- ✅ Scrubbing latency ≤ 50ms p95 (AC-NF-001)
- ✅ Match quality within ±5% baseline (AC-M-002)
- ✅ False positive rate ≤ 3% (AC-F-004)
- ✅ All acceptance criteria met (AC-F-001 through AC-M-004)
- ✅ No customer escalations
- ✅ Compliance reports generated

**Rollback Criteria (Auto-trigger within 48 hours):**
- > 1 PII instance detected in logs
- Scrubber error rate > 5% for 10+ minutes
- Match quality degradation > 10% vs baseline
- > 3 customer escalations in 24 hours
- Performance degradation > 25%

**Rollback Procedure (< 30 minutes):**
- Atomic switch back to blue environment
- Update RAG queries to include unscrubbed data
- Disable database constraint
- Investigate root cause

**Duration:** 1 week (5 days active + 2 days buffer)  
**Owner:** Full Engineering + SRE + Legal + Security  
**Risk Level:** HIGH (production deployment)

---

### Phase 5: Post-Deployment Optimization (Week 6 - Optional)

**Scope:** Performance tuning, documentation finalization, operational handoff.

**Linked Spec References:**
- Section 5.2 (Future enhancements)
- Section 8.2 (Re-indexing strategy)

**Tasks:**
- [ ] Re-index vector embeddings on scrubbed data only
- [ ] Optimize NER batch size based on production metrics
- [ ] Tune GPU memory allocation for optimal throughput
- [ ] Complete all 5 runbooks
- [ ] Complete all 4 ADRs
- [ ] Update API documentation
- [ ] Train SRE team
- [ ] Conduct tabletop exercises (rollback, PII leak response)
- [ ] Post-implementation review

**Exit Criteria:**
- ✅ All runbooks and ADRs published
- ✅ SRE team trained
- ✅ Post-implementation review complete
- ✅ KPIs meet or exceed targets

**Duration:** 1 week (optional)  
**Owner:** SRE + Documentation Team  
**Risk Level:** LOW

---

## 2. Branching Strategy

### Git Branch Naming Convention

All branches MUST follow this deterministic naming pattern:

```
feature/pii-scrubber-<component>
```

### Branch Definitions (Updated for One-Shot Deployment)

| Branch Name | Phases | Scope | PR Reviewers Required |
|-------------|--------|-------|-----------------------|
| **feature/pii-scrubber-core** | Phase 1 | Pattern engine, NER, tokenization, determinism, audit, observability | Security + 2 Backend Eng |
| **feature/pii-scrubber-integration** | Phase 2 | Graph topology (Node 0), state schema, validation gates, database migrations | AI Eng + Backend Eng + DBA |
| **feature/pii-scrubber-testing** | Phase 2 | Integration tests, compliance tests, performance tests, chaos tests | QA Lead + Backend Eng |
| **feature/pii-scrubber-backfill** | Phase 3 | Staging backfill scripts, validation scripts, production backfill prep | Backend Eng + Data Eng |
| **feature/pii-scrubber-deployment** | Phase 4 | Blue-green deployment config, monitoring dashboards, rollback scripts | SRE + Engineering Director |
| **feature/pii-scrubber-docs** | Phase 5 | Runbooks, ADRs, API docs, compliance reports | Documentation Team + Security |

### Branch Lifecycle Requirements

Each branch MUST include:

1. **Spec Section Reference** in PR description
2. **Migration Scripts** (if schema changes)
3. **Test Evidence** (coverage ≥ 90%)
4. **Security Review** (mandatory for all PRs, SAST scan must pass)
5. **Documentation Updates**

### Merge Strategy

- **Merge to `main`:** Requires 2 approvals + passing CI/CD
- **Deployment:** Blue-green deployment with atomic rollback capability
- **Tagging:** Phase completion tagged: `v1.1.0-phase-1`, `v1.1.0-phase-2`, etc.
- **Final Release:** `v1.1.0-production` (after Phase 4 complete)

---

## 3. Database Migration Plan

### 3.1 Migration Sequencing (Zero-Downtime Strategy)

**Execution Order:**

```sql
-- Step 1: Create audit table (Phase 1, Week 1)
- [ ] Test circuit breaker behavior under failure scenarios
- [ ] Validate graceful degradation (NER → regex-only mode)

**Exit Criteria:**
- ✅ 0 PII leaks detected in 7-day monitoring period
- ✅ False positive rate ≤ 3% (improved from canary)
- ✅ Scrubbing latency ≤ 50ms p95 (meets target)
- ✅ Cache hit rate ≥ 60%
- ✅ Load test passes at 10,000 profiles/min

**Rollback Criteria:**
- Performance degradation > 25% compared to baseline
- False positive rate > 5%
- Cache hit rate < 40% (insufficient optimization)

**Duration:** 2 weeks  
**Owner:** Backend + SRE Team  
**Risk Level:** MEDIUM

---

## 2. Branching Strategy

### Git Branch Naming Convention

All branches MUST follow this deterministic naming pattern:

```
feature/pii-scrubber-<component>-<spec-section>
```

### Branch Definitions

| Branch Name | Spec Section Reference | Scope | PR Reviewers Required |
|-------------|----------------------|-------|-----------------------|
| **feature/pii-phase1-infrastructure** | FR-PII-001 to FR-PII-004, NFR-PII-002 | Pattern engine, NER integration, observability, audit table | Security + 2 Backend Engineers |
| **feature/pii-phase2-integration** | Section 5.1, Section 11.1 | Graph topology (Node 0), state schema, database migrations, testing suite | AI Engineer + Backend Engineer + DBA |
| **feature/pii-phase3-validation** | Section 8.1, NFR-PII-001 | Staging backfill (250k records), A/B testing, regression testing | Backend + Data Engineer |
| **feature/pii-phase4-deployment** | Section 13.3 | Production backfill completion, blue-green deployment, constraint enforcement | SRE + Engineering Director |
| **feature/pii-phase5-optimization** | Section 5.2, Section 8.2 | Performance tuning, documentation finalization, operational handoff | SRE + Documentation Team |

### Branch Lifecycle Requirements

Each branch MUST include:

1. **Spec Section Reference** in PR description:
   ```markdown
   ## Spec References
   - FR-PII-001: Pattern-based detection
   - NFR-PII-001: Performance requirements
   ```

2. **Migration Scripts** (if schema changes):
   ```
   alembic/versions/20260217_add_pii_scrub_audit.py
   alembic/versions/20260217_rollback_pii_scrub_audit.py
   ```

3. **Test Evidence** (mandatory for PR approval):
   - Unit test coverage ≥ 90% for new code
   - Integration tests for all new API endpoints
   - Performance test results (if applicable)

4. **Security Review** (required for all PRs):
   - Security team MUST approve before merge
   - Automated SAST scan MUST pass (no high/critical findings)

5. **Documentation Updates**:
   - Update affected spec files (version bump)
   - Add/update ADRs if architectural decisions made
   - Update runbooks if operational procedures change

### Merge Strategy

- **Merge to `main`:** Requires 2 approvals + passing CI/CD
- **Deployment:** Blue-green deployment with automated rollback
- **Tagging:** Each phase completion tagged: `v1.1.0-phase-1`, `v1.1.0-phase-2`, etc.

---

## 3. Database Migration Plan

### 3.1 Migration Sequencing (Zero-Downtime Strategy)

**Execution Order:**

```sql
-- Step 1: Create audit table (Phase 1, Week 1)
-- File: alembic/versions/20260217_001_create_pii_scrub_audit.py

CREATE TABLE pii_scrub_audit (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    source_table VARCHAR(100) NOT NULL,
    source_record_id VARCHAR(255) NOT NULL,
    pii_detected JSONB NOT NULL,
    rule_version VARCHAR(20) NOT NULL,
    scrubber_version VARCHAR(20) NOT NULL,
    triggered_by VARCHAR(100),
    processing_time_ms INT,
    
    -- Immutability constraint (prevent UPDATE/DELETE)
    CONSTRAINT no_update_delete CHECK (false)
);

-- Indexes for query performance
CREATE INDEX idx_audit_timestamp ON pii_scrub_audit(timestamp DESC);
CREATE INDEX idx_audit_source ON pii_scrub_audit(source_table, source_record_id);

-- Permissions (read-only for application, write-only for scrubber service)
REVOKE UPDATE, DELETE ON pii_scrub_audit FROM app_user;
GRANT INSERT, SELECT ON pii_scrub_audit TO scrubber_service;

COMMIT;
```

```sql
-- Step 2: Modify team_member_embeddings (Phase 2, Week 2)
-- File: alembic/versions/20260217_002_add_pii_columns.py

-- Add new columns (nullable initially)
ALTER TABLE team_member_embeddings
  ADD COLUMN pii_scrubbed BOOLEAN DEFAULT FALSE,
  ADD COLUMN profile_text_scrubbed TEXT,
  ADD COLUMN scrub_metadata JSONB;

-- Create index (CONCURRENTLY to avoid locks)
CREATE INDEX CONCURRENTLY idx_embeddings_scrubbed_only
  ON team_member_embeddings(embedding)
  WHERE pii_scrubbed = TRUE;

-- Add comment for documentation
COMMENT ON COLUMN team_member_embeddings.pii_scrubbed IS 
  'Indicates if PII scrubbing completed (required=TRUE post-migration)';

COMMIT;
```

```sql
-- Step 3: Enable constraint (Phase 4, Week 5 - Production Deployment)
-- File: alembic/versions/20260217_003_enforce_pii_constraint.py

-- Make pii_scrubbed NOT NULL (after backfill completes)
ALTER TABLE team_member_embeddings
  ALTER COLUMN pii_scrubbed SET NOT NULL,
  ALTER COLUMN pii_scrubbed SET DEFAULT TRUE;

-- Enforce pii_scrubbed = TRUE constraint
ALTER TABLE team_member_embeddings
  ADD CONSTRAINT check_pii_scrubbed CHECK (pii_scrubbed = TRUE);

-- Make profile_text_scrubbed NOT NULL
ALTER TABLE team_member_embeddings
  ALTER COLUMN profile_text_scrubbed SET NOT NULL;

COMMIT;
```

### 3.2 Rollback Scripts

```sql
-- Rollback Step 3: Remove constraint
-- File: alembic/versions/20260217_003_rollback.py

ALTER TABLE team_member_embeddings
  DROP CONSTRAINT IF EXISTS check_pii_scrubbed,
  ALTER COLUMN pii_scrubbed DROP NOT NULL,
  ALTER COLUMN pii_scrubbed SET DEFAULT FALSE,
  ALTER COLUMN profile_text_scrubbed DROP NOT NULL;

COMMIT;
```

```sql
-- Rollback Step 2: Remove columns
-- File: alembic/versions/20260217_002_rollback.py

DROP INDEX CONCURRENTLY IF EXISTS idx_embeddings_scrubbed_only;

ALTER TABLE team_member_embeddings
  DROP COLUMN IF EXISTS pii_scrubbed,
  DROP COLUMN IF EXISTS profile_text_scrubbed,
  DROP COLUMN IF EXISTS scrub_metadata;

COMMIT;
```

```sql
-- Rollback Step 1: Drop audit table
-- File: alembic/versions/20260217_001_rollback.py

DROP TABLE IF EXISTS pii_scrub_audit CASCADE;

COMMIT;
```

### 3.3 Transaction Safety & Lock Management

**Zero-Downtime Guarantees:**

1. **Step 1 (Audit Table):** New table creation, no locks on existing tables
2. **Step 2 (Add Columns):** Nullable columns added with `DEFAULT`, no full table rewrite (PostgreSQL ≥ 11)
3. **Step 2 (Create Index):** `CREATE INDEX CONCURRENTLY` avoids exclusive locks
4. **Step 3 (Constraint):** Applied only after backfill completes (100% of data already compliant)

**Lock Monitoring:**

```sql
-- Monitor active locks during migration
SELECT 
  pid, 
  locktype, 
  relation::regclass, 
  mode, 
  granted 
FROM pg_locks 
WHERE relation = 'team_member_embeddings'::regclass;
```

**Timeout Configuration:**

```sql
-- Set statement timeout to prevent long-running migrations
SET statement_timeout = '30s';
```

### 3.4 Backfill Execution Plan

**Batch Processing Script:**

```python
# scripts/backfill_legacy_embeddings.py

import psycopg2
from pii_scrubber import PIIScrubber
import hashlib

def backfill_batch(batch_size=1000, target_records=250000):
    scrubber = PIIScrubber(mode="STRICT")
    processed = 0
    
    while processed < target_records:
        # Fetch batch of unscrubbed records
        records = fetch_unscrubbed_batch(batch_size)
        if not records:
            break
        
        for record in records:
            try:
                # Re-scrub profile text
                scrubbed_result = scrubber.scrub(record['profile_text'])
                
                # Calculate checksum for integrity validation
                checksum = hashlib.sha256(
                    record['profile_text'].encode()
                ).hexdigest()
                
                # Update record
                update_record(
                    record_id=record['id'],
                    pii_scrubbed=True,
                    profile_text_scrubbed=scrubbed_result['text'],
                    scrub_metadata={
                        'pii_detected': scrubbed_result['pii_detected'],
                        'rule_version': '1.0.0',
                        'scrubber_version': '1.2.3',
                        'backfill_timestamp': datetime.utcnow().isoformat(),
                        'original_checksum': checksum
                    }
                )
                
                processed += 1
                if processed % 1000 == 0:
                    print(f"Backfill progress: {processed}/{target_records}")
            
            except Exception as e:
                log_backfill_error(record['id'], str(e))
                continue
    
    print(f"Backfill complete: {processed} records processed")

def fetch_unscrubbed_batch(batch_size):
    """Fetch records where pii_scrubbed = FALSE or NULL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, team_member_id, profile_text
        FROM team_member_embeddings
        WHERE (pii_scrubbed = FALSE OR pii_scrubbed IS NULL)
        LIMIT %s
        FOR UPDATE SKIP LOCKED
    """, (batch_size,))
    return cursor.fetchall()
```

**Monitoring Dashboard:**

```prometheus
# Backfill progress metrics
backfill_records_processed_total
backfill_records_failed_total
backfill_duration_seconds
backfill_progress_percent
```

---

## 4. Graph Topology Update Plan

### 4.1 Node 0 Insertion (PII_Scrubber_Agent)

**LangGraph Topology Changes:**

```python
# Before: Existing graph (pre-CR)
graph = StateGraph(RequisitionInput)
graph.add_node("jd_parsing", JDParsingAgent())
graph.add_node("skill_extraction", SkillExtractionAgent())
# ... more nodes ...
graph.set_entry_point("jd_parsing")

# After: New graph (post-CR)
graph = StateGraph(RequisitionInput)
graph.add_node("pii_scrubber", PIIScrubberAgent())  # NEW NODE 0
graph.add_node("jd_parsing", JDParsingAgent())
graph.add_node("skill_extraction", SkillExtractionAgent())
# ... more nodes ...

# Update entry point
graph.set_entry_point("pii_scrubber")  # CHANGED

# Add edges
graph.add_edge("pii_scrubber", "jd_parsing")  # NEW EDGE
graph.add_edge("jd_parsing", "skill_extraction")
# ... more edges ...
```

**PIIScrubberAgent Implementation:**

```python
# src/agents/pii_scrubber_agent.py

from typing import Dict, Any
from agents.base_agent import BaseAgent
from pii_scrubber import PIIScrubber
from state_schema import RequisitionInput, PIIScrubMetadata

class PIIScrubberAgent(BaseAgent):
    """
    Node 0: PII Scrubber Agent
    
    Spec References:
    - FR-PII-001 to FR-PII-004
    - Section 5.1 (Pipeline topology)
    """
    
    def __init__(self, mode: str = "STRICT"):
        super().__init__(name="PII_Scrubber_Agent")
        self.scrubber = PIIScrubber(mode=mode)
    
    def process(self, state: RequisitionInput) -> RequisitionInput:
        """
        Scrub PII from all text fields in state.
        
        Returns:
            Updated state with scrubbed text and metadata
        """
        # Scrub job description
        jd_result = self.scrubber.scrub(state.job_description)
        
        # Scrub team member profiles (if present)
        scrubbed_profiles = []
        for profile in state.team_member_profiles:
            profile_result = self.scrubber.scrub(profile.profile_text)
            scrubbed_profiles.append({
                **profile,
                'profile_text_scrubbed': profile_result['text'],
                'pii_scrubbed': True,
                'scrub_metadata': PIIScrubMetadata(
                    pii_detected=profile_result['pii_detected'],
                    rule_version='1.0.0',
                    scrubber_version='1.2.3'
                )
            })
        
        # Update state
        state.job_description_scrubbed = jd_result['text']
        state.pii_scrubbed = True
        state.scrub_metadata = PIIScrubMetadata(
            pii_detected=jd_result['pii_detected'],
            rule_version='1.0.0',
            scrubber_version='1.2.3'
        )
        state.team_member_profiles = scrubbed_profiles
        
        # Create audit record
        self._create_audit_record(state, jd_result)
        
        return state
```

### 4.2 Validation Gate Enforcement

**Implementation:**

```python
# src/agents/validation_gate.py

class ValidationGate:
    """
    Enforces pii_scrubbed = TRUE before JD Parsing Agent.
    
    Spec Reference: Section 5.1 (Order of operations)
    """
    
    @staticmethod
    def validate_scrubbing(state: RequisitionInput) -> None:
        """
        Raises ValidationError if data not scrubbed.
        """
        if not state.pii_scrubbed:
            logger.critical(
                "Unscrubbed data detected at validation gate",
                extra={
                    "requisition_id": state.requisition_id,
                    "alert": "PII_SCRUBBER_BYPASS_ATTEMPT"
                }
            )
            raise ValidationError(
                "PII scrubbing required before processing",
                status_code=422
            )
        
        # Validate all profiles scrubbed
        for profile in state.team_member_profiles:
            if not profile.get('pii_scrubbed'):
                raise ValidationError(
                    f"Profile {profile['id']} not scrubbed",
                    status_code=422
                )
```

**Edge Definition:**

```python
# Add conditional edge with validation
graph.add_conditional_edges(
    "pii_scrubber",
    lambda state: validate_scrubbing(state) or "jd_parsing",
    {
        "jd_parsing": "jd_parsing",
        ValidationError: END  # Halt graph execution on validation failure
    }
)
```

### 4.3 State Schema Updates

**New Dataclass:**

```python
# src/state_schema.py

from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class PIIScrubMetadata:
    """
    Metadata about PII scrubbing operation.
    
    Spec Reference: ai/state-schema.md v1.1
    """
    pii_detected: List[Dict[str, Any]]  # [{"type": "email", "confidence": 1.0}]
    rule_version: str
    scrubber_version: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class RequisitionInput:
    """
    Updated state schema with PII scrubbing fields.
    """
    requisition_id: str
    job_description: str
    job_description_scrubbed: str = None  # NEW FIELD
    pii_scrubbed: bool = False  # NEW FIELD
    scrub_metadata: PIIScrubMetadata = None  # NEW FIELD
    team_member_profiles: List[Dict] = None
    # ... existing fields ...
```

### 4.4 Backward Compatibility Handling

**Checkpoint Migration:**

```python
# src/checkpoints/migrate_checkpoints.py

def migrate_checkpoint_schema(old_checkpoint: Dict) -> Dict:
    """
    Migrate checkpoints from v1.0 to v1.1 (adds PII fields).
    """
    new_checkpoint = old_checkpoint.copy()
    
    # Add new fields with default values
    if 'pii_scrubbed' not in new_checkpoint:
        new_checkpoint['pii_scrubbed'] = False
        new_checkpoint['job_description_scrubbed'] = None
        new_checkpoint['scrub_metadata'] = None
    
    return new_checkpoint
```

**Serialization:**

```python
# Ensure backward compatibility in state serialization
def serialize_state(state: RequisitionInput) -> Dict:
    """Serialize state to JSON (includes PII fields if present)."""
    return {
        'requisition_id': state.requisition_id,
        'job_description': state.job_description,
        'job_description_scrubbed': state.job_description_scrubbed,  # Omit if None
        'pii_scrubbed': state.pii_scrubbed,
        'scrub_metadata': state.scrub_metadata.to_dict() if state.scrub_metadata else None,
        # ... other fields ...
    }
```

---

## 5. Scrubber Component Tasks

### 5.1 Regex Engine (FR-PII-001)

**Task Breakdown:**

| Task ID | Description | Spec Reference | Acceptance Criteria | Owner |
|---------|-------------|---------------|---------------------|-------|
| **SC-001** | Implement email regex pattern | FR-PII-001 | 100% recall on 1,000 test emails | Backend Eng |
| **SC-002** | Implement phone regex (E.164 + US formats) | FR-PII-001 | 95% recall on 1,000 test phones | Backend Eng |
| **SC-003** | Implement DOB regex (MM/DD/YYYY) | FR-PII-001 | 95% recall on 1,000 test dates | Backend Eng |
| **SC-004** | Implement postal code regex (US + UK) | FR-PII-001 | 90% recall on 500 test codes | Backend Eng |
| **SC-005** | YAML config loader for patterns | FR-PII-001 | Load 20 patterns in < 100ms | Backend Eng |
| **SC-006** | Unicode support for international names | FR-PII-001 | Support 10+ languages | Backend Eng |
| **SC-007** | Pattern validation on startup | FR-PII-001 | Reject 10 invalid patterns | Backend Eng |

**Implementation File:** `src/pii_scrubber/regex_engine.py`

**Test File:** `tests/unit/test_regex_engine.py` (30 tests)

---

### 5.2 NER Integration (FR-PII-002)

**Task Breakdown:**

| Task ID | Description | Spec Reference | Acceptance Criteria | Owner |
|---------|-------------|---------------|---------------------|-------|
| **SC-101** | Integrate SpaCy `en_core_web_trf` | FR-PII-002 | F1 ≥ 0.90 on test corpus | ML Eng |
| **SC-102** | GPU acceleration setup (CUDA) | NFR-PII-001 | Latency ≤ 20ms p95 | ML Eng |
| **SC-103** | CPU fallback mode | Section 7.1 | Degraded mode active on GPU failure | ML Eng |
| **SC-104** | Confidence threshold configuration | FR-PII-006 | STRICT (≥0.50), BALANCED (≥0.85) | ML Eng |
| **SC-105** | Entity type detection (PERSON, GPE, ORG, etc.) | FR-PII-002 | 5 entity types supported | ML Eng |
| **SC-106** | Whitelist integration for skill names | NFR-PII-004 | False positive rate ≤ 3% | ML Eng |
| **SC-107** | Batch processing (50 profiles/batch) | NFR-PII-001 | Throughput ≥ 500 profiles/sec | ML Eng |

**Implementation File:** `src/pii_scrubber/ner_engine.py`

**Test File:** `tests/unit/test_ner_engine.py` (20 tests)

---

### 5.3 Business-Sensitive Rule Engine (FR-PII-003)

**Task Breakdown:**

| Task ID | Description | Spec Reference | Acceptance Criteria | Owner |
|---------|-------------|---------------|---------------------|-------|
| **SC-201** | Database-backed client name loader | FR-PII-003 | Refresh every 1 hour | Backend Eng |
| **SC-202** | Fuzzy matching (Levenshtein, threshold=0.85) | FR-PII-003 | Detect "Acme Corp" vs "ACME Corporation" | Backend Eng |
| **SC-203** | Tokenization vault implementation | Section 3.5 | Store 10,000+ tokens | Backend Eng |
| **SC-204** | Token generation (SHA-256 prefix) | FR-PII-004 | Deterministic token generation | Backend Eng |
| **SC-205** | S3/database source for client lists | FR-PII-003 | Support 2 source types | Backend Eng |
| **SC-206** | Case-insensitive matching | FR-PII-003 | Ignore case in comparisons | Backend Eng |

**Implementation File:** `src/pii_scrubber/business_sensitive_engine.py`

**Test File:** `tests/unit/test_business_sensitive_engine.py` (15 tests)

---

### 5.4 Tokenization Vault Integration (Section 3.5)

**Task Breakdown:**

| Task ID | Description | Spec Reference | Acceptance Criteria | Owner |
|---------|-------------|---------------|---------------------|-------|
| **SC-301** | Create `pii_token_vault` table | Section 3.5 | Encrypted storage | DBA |
| **SC-302** | Token generation API | Section 3.5 | Generate unique tokens | Backend Eng |
| **SC-303** | Detokenization API (authorized only) | Section 3.5 | Role-based access control | Backend Eng |
| **SC-304** | Audit logging for detokenization | NFR-PII-003 | Log all vault access | Backend Eng |
| **SC-305** | Redis caching for tokens (1-hour TTL) | NFR-PII-001 | 60% cache hit rate | Backend Eng |

**Implementation File:** `src/pii_scrubber/tokenization_vault.py`

**Test File:** `tests/unit/test_tokenization_vault.py` (10 tests)

---

### 5.5 Determinism Validation (FR-PII-004)

**Task Breakdown:**

| Task ID | Description | Spec Reference | Acceptance Criteria | Owner |
|---------|-------------|---------------|---------------------|-------|
| **SC-401** | Salt-based hashing (SHA-256) | FR-PII-004 | Static salt from env var | Backend Eng |
| **SC-402** | Greedy decoding for NER | FR-PII-004 | No sampling in NER | ML Eng |
| **SC-403** | Determinism test suite | AC-F-005 | 1,000 iterations identical | QA Eng |
| **SC-404** | Salt rotation procedure | FR-PII-004 | Quarterly rotation documented | Security Eng |

**Implementation File:** `src/pii_scrubber/determinism.py`

**Test File:** `tests/unit/test_determinism.py` (10 tests)

---

### 5.6 Strict/Balanced Mode Config (FR-PII-006)

**Task Breakdown:**

| Task ID | Description | Spec Reference | Acceptance Criteria | Owner |
|---------|-------------|---------------|---------------------|-------|
| **SC-501** | Mode configuration loader | FR-PII-006 | Load from env var | Backend Eng |
| **SC-502** | STRICT mode implementation | FR-PII-006 | Scrub confidence ≥ 0.50 | Backend Eng |
| **SC-503** | BALANCED mode implementation | FR-PII-006 | Scrub confidence ≥ 0.85 | Backend Eng |
| **SC-504** | Mode switching without restart | FR-PII-006 | Hot-reload on config change | Backend Eng |

**Implementation File:** `src/pii_scrubber/config.py`

**Test File:** `tests/unit/test_scrubber_modes.py` (8 tests)

---

### 5.7 Hot-Reload Rule Support (FR-PII-003)

**Task Breakdown:**

| Task ID | Description | Spec Reference | Acceptance Criteria | Owner |
|---------|-------------|---------------|---------------------|-------|
| **SC-601** | SIGHUP signal handler | FR-PII-003 | Reload on SIGHUP | Backend Eng |
| **SC-602** | `/admin/reload-pii-rules` API endpoint | FR-PII-003 | HTTP 200 on success | Backend Eng |
| **SC-603** | Rule validation before reload | FR-PII-003 | Reject invalid YAML | Backend Eng |
| **SC-604** | Audit log for rule changes | NFR-PII-003 | Log all reloads | Backend Eng |
| **SC-605** | Zero-downtime reload | FR-PII-003 | Reload in < 5 seconds | Backend Eng |

**Implementation File:** `src/pii_scrubber/hot_reload.py`

**Test File:** `tests/integration/test_hot_reload.py` (5 tests)

---

## 6. Testing Plan

### 6.1 Unit Tests (Target: 100 tests)

**Test Suite Organization:**

```
tests/unit/
├── test_regex_engine.py (30 tests)
│   ├── test_email_detection_100_samples
│   ├── test_phone_detection_us_formats
│   ├── test_phone_detection_e164_formats
│   ├── test_dob_detection_mmddyyyy
│   ├── test_postal_code_us
│   ├── test_postal_code_uk
│   ├── test_unicode_support
│   └── ... (23 more)
│
├── test_ner_engine.py (20 tests)
│   ├── test_person_detection_high_confidence
│   ├── test_gpe_detection
│   ├── test_org_detection
│   ├── test_whitelist_skill_names
│   ├── test_batch_processing
│   ├── test_gpu_acceleration
│   ├── test_cpu_fallback
│   └── ... (13 more)
│
├── test_business_sensitive_engine.py (15 tests)
│   ├── test_client_name_fuzzy_match
│   ├── test_tokenization_deterministic
│   ├── test_database_source_loader
│   └── ... (12 more)
│
├── test_tokenization_vault.py (10 tests)
│   ├── test_token_generation_unique
│   ├── test_detokenization_authorized
│   ├── test_audit_logging
│   └── ... (7 more)
│
├── test_determinism.py (10 tests)
│   ├── test_scrubber_determinism_1000_iterations
│   ├── test_salt_based_hashing
│   └── ... (8 more)
│
├── test_scrubber_modes.py (8 tests)
│   ├── test_strict_mode_threshold
│   ├── test_balanced_mode_threshold
│   └── ... (6 more)
│
└── test_audit_logging.py (10 tests)
    ├── test_audit_record_creation
    ├── test_audit_immutability
    └── ... (8 more)
```

**Test Naming Convention:**

```python
def test_{component}_{behavior}_{expected_outcome}():
    """
    Spec Reference: FR-PII-XXX, AC-F-XXX
    
    Test that {component} {behavior} results in {expected_outcome}.
    """
    pass
```

**Coverage Requirements:**

- **Minimum Coverage:** 90% for all new code
- **Critical Paths:** 100% coverage for scrubbing logic, determinism, audit logging
- **CI Gate:** Build fails if coverage drops below 85%

---

### 6.2 Integration Tests (Target: 30 tests)

**Test Suite Organization:**

```
tests/integration/
├── test_end_to_end_pipeline.py (10 tests)
│   ├── test_requisition_with_pii_scrubbed_full_graph
│   ├── test_validation_gate_rejects_unscrubbed
│   ├── test_audit_log_created_for_pipeline
│   └── ... (7 more)
│
├── test_database_constraints.py (5 tests)
│   ├── test_unscrubbed_data_rejected_by_constraint
│   ├── test_pii_scrubbed_true_required
│   └── ... (3 more)
│
├── test_api_validation.py (5 tests)
│   ├── test_ingestion_api_pii_filtered
│   ├── test_retrieval_api_secondary_filter
│   └── ... (3 more)
│
├── test_retrieval_filtering.py (5 tests)
│   ├── test_rag_query_no_pii_leakage
│   ├── test_secondary_filter_redacts_pii
│   └── ... (3 more)
│
└── test_backfill_process.py (5 tests)
    ├── test_backfill_integrity_validation
    ├── test_backfill_checksum_verification
    └── ... (3 more)
```

**Integration Test Characteristics:**

- **Database Required:** Tests run against real PostgreSQL instance (staging)
- **External Services:** NER model, Redis, tokenization vault
- **Test Data:** Synthetic PII corpus (10,000 profiles)
- **Execution Time:** ~10 minutes (parallelized)

---

### 6.3 Compliance Tests (Target: 20 tests)

**Test Suite Organization:**

```
tests/compliance/
├── test_gdpr_compliance.py (5 tests)
│   ├── test_gdpr_article_5_data_minimization
│   ├── test_gdpr_article_25_data_protection_by_design
│   └── ... (3 more)
│
├── test_ccpa_compliance.py (5 tests)
│   ├── test_ccpa_right_to_deletion
│   ├── test_ccpa_right_to_know
│   └── ... (3 more)
│
├── test_audit_trail.py (5 tests)
│   ├── test_audit_log_7_year_retention
│   ├── test_audit_log_immutability
│   └── ... (3 more)
│
└── test_pii_leak_detection.py (5 tests)
    ├── test_no_pii_in_application_logs
    ├── test_no_pii_in_prometheus_metrics
    ├── test_no_pii_in_distributed_traces
    └── ... (2 more)
```

**Compliance Test Execution:**

- **Frequency:** Daily (automated in CI/CD)
- **Evidence Collection:** Test results stored for audit trail
- **Failure Handling:** Critical alert if any compliance test fails

---

### 6.4 CI/CD Gating Requirements

**Pre-Commit Hooks:**

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pii-scan
        name: PII Leak Scan
        entry: scripts/scan_for_pii_in_code.sh
        language: system
        pass_filenames: false
```

**CI Pipeline Gates:**

```yaml
# .github/workflows/pii-scrubber-ci.yml
name: PII Scrubber CI

on: [pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run unit tests
        run: pytest tests/unit/ --cov=src/pii_scrubber --cov-report=xml
      - name: Check coverage
        run: |
          coverage=$(grep 'line-rate' coverage.xml | sed 's/.*line-rate="\([0-9.]*\)".*/\1/')
          if (( $(echo "$coverage < 0.90" | bc -l) )); then
            echo "Coverage $coverage below 90% threshold"
            exit 1
          fi
  
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: test
    steps:
      - name: Run integration tests
        run: pytest tests/integration/ --maxfail=1
  
  compliance-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run compliance tests
        run: pytest tests/compliance/
      - name: Archive compliance evidence
        run: tar -czf compliance-evidence.tar.gz test-results/
  
  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run performance benchmarks
        run: pytest tests/performance/ --benchmark-only
      - name: Check performance regression
        run: python scripts/check_performance_regression.py
  
  pii-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Scan codebase for PII
        run: python scripts/scan_for_pii.py --fail-on-detection
```

**Merge Requirements:**

- ✅ All 150 tests pass
- ✅ Code coverage ≥ 90%
- ✅ Performance benchmarks within 10% of baseline
- ✅ No PII detected in code/logs (automated scan)
- ✅ 2 approvals (1 Security, 1 Engineering)
- ✅ SAST scan passes (no high/critical findings)

---

## 7. Observability & Alerting Setup

### 7.1 Prometheus Metrics

**Metric Definitions:**

```yaml
# config/prometheus-metrics.yaml

# Scrubbing operations
pii_scrub_operations_total:
  type: counter
  description: "Total PII scrubbing operations"
  labels: [pii_type, action, mode]
  
pii_scrub_duration_seconds:
  type: histogram
  description: "PII scrubbing latency"
  buckets: [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
  labels: [mode]

# Detection metrics
pii_detection_confidence_score:
  type: histogram
  description: "Confidence scores for PII detections"
  buckets: [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
  labels: [pii_type, detection_method]

pii_false_positive_rate:
  type: gauge
  description: "Estimated false positive rate"
  labels: [mode]

# Failure metrics
pii_scrub_failures_total:
  type: counter
  description: "Failed scrubbing operations"
  labels: [failure_mode]

pii_scrubber_degraded_mode:
  type: gauge
  description: "1 if degraded mode active, 0 otherwise"

# Audit metrics
pii_audit_records_created_total:
  type: counter
  description: "Audit records created"
  labels: [source_table]

# Backfill metrics
backfill_records_processed_total:
  type: counter
  description: "Legacy records backfilled"

backfill_records_failed_total:
  type: counter
  description: "Backfill failures"
  labels: [failure_reason]

backfill_progress_percent:
  type: gauge
  description: "Backfill completion percentage"
```

**Grafana Dashboard:**

```json
{
  "dashboard": {
    "title": "PII Scrubber Operations",
    "panels": [
      {
        "title": "Scrubbing Throughput",
        "targets": [
          {
            "expr": "rate(pii_scrub_operations_total[5m])",
            "legendFormat": "{{pii_type}} - {{action}}"
          }
        ]
      },
      {
        "title": "Scrubbing Latency (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, pii_scrub_duration_seconds_bucket)",
            "legendFormat": "p95"
          }
        ]
      },
      {
        "title": "False Positive Rate",
        "targets": [
          {
            "expr": "pii_false_positive_rate",
            "legendFormat": "{{mode}}"
          }
        ]
      }
    ]
  }
}
```

---

### 7.2 Alert Rules

**Alert Definitions:**

```yaml
# config/alerts/pii-scrubber-alerts.yaml

groups:
  - name: pii_scrubber_critical
    rules:
      - alert: PIIScrubberHighFailureRate
        expr: rate(pii_scrub_failures_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
          component: pii_scrubber
          runbook: docs/runbooks/pii-scrubber-alerts.md#high-failure-rate
        annotations:
          summary: "PII scrubber failure rate exceeds 5%"
          description: "{{ $value }} failures/sec in last 5 minutes"
      
      - alert: PIIDetectedInLogs
        expr: log_scrubbing_pii_detected_total > 0
        for: 1m
        labels:
          severity: critical
          component: logging
          runbook: docs/runbooks/pii-alert-response.md
        annotations:
          summary: "PII detected in application logs - SECURITY INCIDENT"
          description: "Scrubber bypass detected, immediate investigation required"
      
      - alert: PIIScrubberLatencyHigh
        expr: histogram_quantile(0.95, pii_scrub_duration_seconds_bucket) > 0.1
        for: 5m
        labels:
          severity: warning
          component: pii_scrubber
          runbook: docs/runbooks/pii-scrubber-performance.md
        annotations:
          summary: "PII scrubber p95 latency > 100ms"
          description: "Performance degradation detected (target: 50ms)"
  
  - name: pii_scrubber_warnings
    rules:
      - alert: PIIScrubberDegradedMode
        expr: pii_scrubber_degraded_mode == 1
        for: 5m
        labels:
          severity: warning
          component: pii_scrubber
          runbook: docs/runbooks/pii-scrubber-degraded-mode.md
        annotations:
          summary: "PII scrubber operating in degraded mode (regex-only)"
          description: "NER model unavailable, manual review queue growing"
      
      - alert: PIIFalsePositiveRateHigh
        expr: pii_false_positive_rate > 0.05
        for: 10m
        labels:
          severity: warning
          component: pii_scrubber
          runbook: docs/runbooks/pii-scrubber-tuning.md
        annotations:
          summary: "False positive rate exceeds 5% threshold"
          description: "Review whitelist and confidence thresholds"
```

**Alert Routing:**

```yaml
# config/alertmanager.yaml

route:
  group_by: ['alertname', 'component']
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: pagerduty
      continue: true
    
    - match:
        severity: warning
      receiver: slack
```

**PagerDuty Integration:**

```yaml
receivers:
  - name: pagerduty
    pagerduty_configs:
      - service_key: <PAGERDUTY_SERVICE_KEY>
        description: "{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}"
        details:
          runbook: "{{ .CommonAnnotations.runbook }}"
```

---

### 7.3 Audit Log Verification

**Daily Audit Verification Job:**

```bash
# scripts/verify_audit_logs.sh

#!/bin/bash

# Spec Reference: NFR-PII-003

# 1. Check audit log immutability
psql -c "
  SELECT COUNT(*) AS audit_records_modified
  FROM pii_scrub_audit
  WHERE pg_catalog.pg_try_advisory_lock(audit_id::int) = false;
"

# 2. Verify 100% audit coverage
psql -c "
  SELECT 
    (SELECT COUNT(*) FROM team_member_embeddings WHERE pii_scrubbed = TRUE) AS scrubbed_records,
    (SELECT COUNT(DISTINCT source_record_id) FROM pii_scrub_audit WHERE source_table = 'team_member') AS audited_records;
"

# 3. Check for audit record gaps
psql -c "
  SELECT team_member_id
  FROM team_member_embeddings
  WHERE pii_scrubbed = TRUE
    AND NOT EXISTS (
      SELECT 1 FROM pii_scrub_audit
      WHERE source_table = 'team_member'
        AND source_record_id = team_member_embeddings.team_member_id
    );
"

# 4. Validate audit log retention (7 years)
psql -c "
  SELECT COUNT(*) AS expired_audit_records
  FROM pii_scrub_audit
  WHERE timestamp < NOW() - INTERVAL '7 years';
"
```

**Cron Schedule:**

```cron
# Run audit verification daily at 2 AM
0 2 * * * /opt/scripts/verify_audit_logs.sh >> /var/log/pii-audit-verification.log 2>&1
```

---

### 7.4 Log Scanning Cron Jobs

**Automated PII Leak Detection:**

```python
# scripts/scan_logs_for_pii.py

"""
Daily scan for PII in application logs.

Spec Reference: NFR-PII-002 (Observability without PII leakage)
"""

import re
from datetime import datetime, timedelta

PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\+?[1-9]\d{1,14}',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b'
}

def scan_log_file(log_path: str) -> list:
    """Scan log file for PII patterns."""
    detections = []
    
    with open(log_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            for pii_type, pattern in PII_PATTERNS.items():
                if re.search(pattern, line):
                    detections.append({
                        'line_number': line_num,
                        'pii_type': pii_type,
                        'log_line': line[:100],  # First 100 chars
                        'timestamp': datetime.utcnow().isoformat()
                    })
    
    return detections

def main():
    log_files = [
        '/var/log/rag-pipeline/application.log',
        '/var/log/rag-pipeline/error.log',
        '/var/log/rag-pipeline/audit.log'
    ]
    
    all_detections = []
    for log_file in log_files:
        detections = scan_log_file(log_file)
        all_detections.extend(detections)
    
    if all_detections:
        # CRITICAL ALERT: PII detected in logs
        trigger_pagerduty_alert(
            severity='critical',
            summary=f"PII detected in logs: {len(all_detections)} instances",
            details=all_detections
        )
        
        # Log to security audit trail
        log_security_incident('PII_LEAK_IN_LOGS', all_detections)
    
    # Update Prometheus metric
    update_metric('log_scrubbing_pii_detected_total', len(all_detections))

if __name__ == '__main__':
    main()
```

**Cron Schedule:**

```cron
# Run PII leak detection daily at 3 AM
0 3 * * * python /opt/scripts/scan_logs_for_pii.py >> /var/log/pii-scan.log 2>&1
```

---

## 8. Migration Execution Plan

### 8.1 Pre-Production Backfill (Weeks 3-4, Phase 3)

**Objective:** Complete backfill of all 250,000 legacy embeddings in staging environment before production deployment.

**Implementation:**

```python
# src/repositories/team_member_repository.py

def create_embedding(self, team_member_id: str, profile_text: str) -> None:
    """
    Create embedding with PII scrubbing (always enabled in one-shot deployment).
    
    Spec Reference: Section 8.1 (Pre-Production Backfill Strategy)
    """
    # Scrub profile text
    scrub_result = self.pii_scrubber.scrub(profile_text)
    
    # Generate embedding from scrubbed text
    embedding = self.embedding_service.generate(scrub_result['text'])
    
    # Write scrubbed data (PII scrubbing is always enabled post-deployment)
    self.db.execute("""
        INSERT INTO team_member_embeddings (
            team_member_id,
            profile_text_scrubbed,     -- Scrubbed text column
            embedding,
            pii_scrubbed,              -- Always TRUE post-deployment
            scrub_metadata             -- Audit metadata
        ) VALUES (
            %(team_member_id)s,
            %(profile_text_scrubbed)s,
            %(embedding)s,
            TRUE,
            %(scrub_metadata)s
        )
    """, {
        'team_member_id': team_member_id,
        'profile_text_scrubbed': scrub_result['text'],
        'embedding': embedding,
        'scrub_metadata': scrub_result['metadata']
    })
```

**Monitoring:**

```prometheus
# Track backfill performance
backfill_latency_seconds{environment="staging"}
backfill_records_processed_total
backfill_failures_total{reason="database_error"}
```

---

### 8.2 Production Deployment (Week 5, Phase 4)

**Objective:** Deploy 100% of traffic with pre-completed backfill (zero production backfill risk).

**Backfill Script (Used in Staging for Pre-Production Validation):**

```python
# scripts/backfill_legacy_embeddings.py

"""
Backfill script for legacy embeddings (executed in staging during Phase 3).

Spec Reference: Section 8.1 (Pre-Production Backfill Strategy)

Usage:
  python backfill_legacy_embeddings.py --batch-size 1000 --dry-run
  python backfill_legacy_embeddings.py --batch-size 1000 --target 250000
"""

import argparse
import logging
from datetime import datetime
import hashlib
from tqdm import tqdm

from src.pii_scrubber import PIIScrubber
from src.database import get_db_connection

logger = logging.getLogger(__name__)

def backfill_batch(batch_size: int, dry_run: bool = False) -> dict:
    """Process one batch of legacy embeddings."""
    scrubber = PIIScrubber(mode="STRICT")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch unscrubbed records with FOR UPDATE SKIP LOCKED (avoid contention)
    cursor.execute("""
        SELECT id, team_member_id, profile_text
        FROM team_member_embeddings
        WHERE (pii_scrubbed = FALSE OR pii_scrubbed IS NULL)
        LIMIT %s
        FOR UPDATE SKIP LOCKED
    """, (batch_size,))
    
    records = cursor.fetchall()
    if not records:
        return {'processed': 0, 'failed': 0}
    
    processed = 0
    failed = 0
    
    for record in tqdm(records, desc="Backfilling"):
        try:
            # Calculate checksum of original text
            original_checksum = hashlib.sha256(
                record['profile_text'].encode()
            ).hexdigest()
            
            # Re-scrub profile text
            scrub_result = scrubber.scrub(record['profile_text'])
            
            if not dry_run:
                # Update record with scrubbed data
                cursor.execute("""
                    UPDATE team_member_embeddings
                    SET 
                        pii_scrubbed = TRUE,
                        profile_text_scrubbed = %s,
                        scrub_metadata = %s
                    WHERE id = %s
                """, (
                    scrub_result['text'],
                    {
                        'pii_detected': scrub_result['pii_detected'],
                        'rule_version': '1.0.0',
                        'scrubber_version': '1.2.3',
                        'backfill_timestamp': datetime.utcnow().isoformat(),
                        'original_checksum': original_checksum
                    },
                    record['id']
                ))
                
                conn.commit()
            
            processed += 1
        
        except Exception as e:
            logger.error(f"Backfill failed for record {record['id']}: {e}")
            failed += 1
            conn.rollback()
    
    return {'processed': processed, 'failed': failed}

def main():
    parser = argparse.ArgumentParser(description='Backfill legacy embeddings')
    parser.add_argument('--batch-size', type=int, default=1000)
    parser.add_argument('--target', type=int, default=250000)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    total_processed = 0
    total_failed = 0
    
    while total_processed < args.target:
        result = backfill_batch(args.batch_size, args.dry_run)
        
        if result['processed'] == 0:
            logger.info("No more records to backfill")
            break
        
        total_processed += result['processed']
        total_failed += result['failed']
        
        logger.info(f"Progress: {total_processed}/{args.target} processed, {total_failed} failed")
    
    logger.info(f"Backfill complete: {total_processed} processed, {total_failed} failed")

if __name__ == '__main__':
    main()
```

**Execution Plan:**

```bash
# Week 11: Dry-run validation
python scripts/backfill_legacy_embeddings.py --batch-size 1000 --dry-run --target 10000

# Week 11-14: Production backfill (10,000 records/day)
# Run daily via cron
0 1 * * * python /opt/scripts/backfill_legacy_embeddings.py --batch-size 10000 --target 10000 >> /var/log/backfill.log 2>&1
```

**Progress Tracking:**

```sql
-- Check backfill progress
SELECT 
    COUNT(*) FILTER (WHERE pii_scrubbed = TRUE) AS scrubbed_count,
    COUNT(*) FILTER (WHERE pii_scrubbed = FALSE OR pii_scrubbed IS NULL) AS unscrubbed_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE pii_scrubbed = TRUE) / COUNT(*), 2) AS progress_percent
FROM team_member_embeddings;
```

---

### 8.3 Cutover Phase (Week 13, Phase 6)

**Objective:** Switch RAG queries to only read scrubbed data, enforce database constraints.

**Query Migration:**

```sql
-- Before: Queries read unscrubbed data
SELECT team_member_id, embedding, profile_text
FROM team_member_embeddings
WHERE ...;

-- After: Queries filter for scrubbed data only
SELECT team_member_id, embedding, profile_text_scrubbed
FROM team_member_embeddings
WHERE pii_scrubbed = TRUE
AND ...;
```

**Application Code Update:**

```python
# src/repositories/rag_repository.py

def get_candidate_embeddings(self, skill_filters: list) -> list:
    """
    Retrieve candidate embeddings (scrubbed only).
    
    Spec Reference: Section 8.1 (Phase 3: Cutover)
    """
    return self.db.execute("""
        SELECT 
            team_member_id,
            embedding,
            profile_text_scrubbed,  -- Use scrubbed text only
            scrub_metadata
        FROM team_member_embeddings
        WHERE pii_scrubbed = TRUE   -- Filter for scrubbed records only
        AND ...
    """)
```

**Constraint Enforcement:**

```sql
-- Enable CHECK constraint (after backfill 100% complete)
ALTER TABLE team_member_embeddings
  ADD CONSTRAINT check_pii_scrubbed CHECK (pii_scrubbed = TRUE);

-- Test constraint
INSERT INTO team_member_embeddings (team_member_id, profile_text, pii_scrubbed)
VALUES ('TEST-001', 'test', FALSE);
-- Expected: ERROR: new row violates check constraint "check_pii_scrubbed"
```

---

### 8.4 Cleanup Phase (Weeks 14-16, Phase 7)

**Objective:** Archive legacy data, optimize indexes, decommission feature flags.

**S3 Archival Script:**

```python
# scripts/archive_legacy_embeddings.py

"""
Archive legacy unscrubbed embeddings to S3.

Spec Reference: Section 8.1 (Phase 4: Cleanup)

Retention: 7 years (encrypted in S3)
"""

import boto3
import json
from datetime import datetime

s3 = boto3.client('s3')
BUCKET = 'pii-scrubber-archives'
RETENTION_YEARS = 7

def archive_to_s3():
    """Export legacy embeddings to S3 for 7-year retention."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Export all records (including now-scrubbed ones)
    cursor.execute("""
        SELECT 
            team_member_id,
            profile_text AS unscrubbed_text,
            profile_text_scrubbed,
            scrub_metadata,
            created_at
        FROM team_member_embeddings
        WHERE created_at < NOW() - INTERVAL '90 days'  -- Only old records
    """)
    
    records = cursor.fetchall()
    
    # Upload to S3 (encrypted)
    s3.put_object(
        Bucket=BUCKET,
        Key=f'legacy-embeddings/{datetime.utcnow().strftime("%Y-%m-%d")}.json.gz',
        Body=gzip.compress(json.dumps(records).encode()),
        ServerSideEncryption='AES256',
        Metadata={
            'retention_until': (datetime.utcnow() + timedelta(days=365*RETENTION_YEARS)).isoformat()
        }
    )
    
    logger.info(f"Archived {len(records)} records to S3")

if __name__ == '__main__':
    archive_to_s3()
```

**Index Optimization:**

```sql
-- Drop old index (unscrubbed data)
DROP INDEX CONCURRENTLY IF EXISTS idx_embeddings_vector_old;

-- Keep only scrubbed index
-- (Already created in Phase 2)
```

**Feature Flag Removal:**

```python
# Remove feature flag logic from codebase
# Before:
if feature_flags.is_enabled('PII_SCRUBBER_ENABLED'):
    scrub_pii(profile_text)

# After: Scrubber always enabled (flag removed)
scrub_pii(profile_text)
```

---

### 8.5 Migration Monitoring

**Key Metrics:**

```prometheus
# Track migration progress
backfill_progress_percent{phase="backfill"}
migration_phase{phase="dual_write|backfill|cutover|cleanup"}
migration_errors_total{phase="...", error_type="..."}

# Match quality comparison (A/B test)
match_quality_score{variant="control|scrubbed"}
retrieval_latency_seconds{variant="control|scrubbed"}
```

**Dashboard:**

```json
{
  "dashboard": {
    "title": "PII Scrubber Migration",
    "panels": [
      {
        "title": "Backfill Progress",
        "targets": [{"expr": "backfill_progress_percent"}]
      },
      {
        "title": "Match Quality (A/B Test)",
        "targets": [{"expr": "match_quality_score"}]
      }
    ]
  }
}
```

---

## 9. Rollback & Safety Gates

### 9.1 Automated Rollback Triggers

**Trigger Definitions:**

| Trigger ID | Condition | Threshold | Action | Owner |
|------------|-----------|-----------|--------|-------|
| **RB-001** | PII detected in logs | > 1 instance in 24h | Immediate rollback | SRE |
| **RB-002** | Scrubber error rate | > 5% for 10+ min | Immediate rollback | SRE |
| **RB-003** | Match quality degradation | > 10% vs baseline | Immediate rollback | Product + SRE |
| **RB-004** | Customer escalations | > 5 in 7 days | Manual review → rollback | Product Owner |
| **RB-005** | False positive rate | > 5% sustained | Rollback to previous rules | ML Engineer |
| **RB-006** | Performance degradation | Latency > 150ms p95 | Rollback to previous version | SRE |

**Automated Rollback Script:**

```python
# scripts/automated_rollback.py

"""
Automated rollback trigger based on monitoring alerts.

Triggered by: PagerDuty webhook or Prometheus Alertmanager
"""

import subprocess
import logging

logger = logging.getLogger(__name__)

def trigger_rollback(reason: str, alert_data: dict):
    """Execute automated rollback procedure."""
    logger.critical(f"ROLLBACK TRIGGERED: {reason}", extra=alert_data)
    
    # Step 1: Disable feature flag (< 1 minute)
    subprocess.run([
        "kubectl", "set", "env",
        "deployment/rag-pipeline",
        "PII_SCRUBBER_ENABLED=false"
    ])
    
    # Step 2: Revert application code (< 10 minutes)
    subprocess.run([
        "kubectl", "rollout", "undo",
        "deployment/rag-pipeline"
    ])
    
    # Step 3: Update RAG queries to include legacy data (< 5 minutes)
    subprocess.run([
        "psql", "-c",
        "UPDATE rag_config SET filter_scrubbed = FALSE"
    ])
    
    # Step 4: Monitor for 24 hours
    logger.info("Rollback complete. Monitoring for 24 hours.")
    
    # Notify stakeholders
    send_slack_alert(
        channel="#incidents",
        message=f"🚨 ROLLBACK EXECUTED: {reason}\nSee runbook: docs/runbooks/pii-scrubber-rollback.md"
    )
```

---

### 9.2 Manual Rollback Steps

**Runbook:** `docs/runbooks/pii-scrubber-rollback.md`

**Step-by-Step Procedure:**

```markdown
# PII Scrubber Rollback Procedure

**Estimated Time:** < 30 minutes
**Spec Reference:** Section 13.2 (Rollback strategy)

## Prerequisites
- [ ] Kubectl access to production cluster
- [ ] PostgreSQL admin credentials
- [ ] PagerDuty incident created

## Step 1: Disable Feature Flag (< 1 minute)

```bash
# Disable scrubber for all traffic
kubectl set env deployment/rag-pipeline PII_SCRUBBER_ENABLED=false

# Verify environment variable
kubectl describe deployment/rag-pipeline | grep PII_SCRUBBER
```

## Step 2: Revert Application Code (< 10 minutes)

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/rag-pipeline

# Monitor rollout status
kubectl rollout status deployment/rag-pipeline

# Verify pods running previous version
kubectl get pods -l app=rag-pipeline -o jsonpath='{.items[*].spec.containers[*].image}'
```

## Step 3: Update Database Queries (< 5 minutes)

```sql
-- Allow RAG queries to include unscrubbed data (legacy)
UPDATE rag_config
SET filter_scrubbed = FALSE
WHERE config_key = 'pii_filter_enabled';

-- Verify configuration
SELECT * FROM rag_config WHERE config_key = 'pii_filter_enabled';
```

## Step 4: Disable Scrubber Validation Gate (< 1 minute)

```bash
# Disable validation gate (allow unscrubbed data)
kubectl set env deployment/rag-pipeline PII_SCRUBBER_REQUIRED=false
```

## Step 5: Monitor System Health (24 hours)

```bash
# Monitor error rates
kubectl logs -f deployment/rag-pipeline | grep -i "error\|pii"

# Check Prometheus metrics
curl http://prometheus:9090/api/v1/query?query=pii_scrub_operations_total

# Verify match quality restored
python scripts/check_match_quality.py --baseline
```

## Step 6: Root Cause Investigation

- [ ] Review PII scrubber logs for failure patterns
- [ ] Analyze false positive/negative samples
- [ ] Review scrubbing rules for errors
- [ ] Check NER model health
- [ ] Validate infrastructure (GPU, Redis, etc.)

## Step 7: Post-Rollback Actions

- [ ] Update stakeholders (CISO, Engineering Director)
- [ ] Document lessons learned
- [ ] Plan fix for root cause
- [ ] Re-plan migration timeline
```

---

### 9.3 Rollback Time Objective (RTO)

**Target RTO:** < 30 minutes (from trigger to full rollback)

**Breakdown:**

| Step | Duration | Description |
|------|----------|-------------|
| 1. Disable feature flag | < 1 min | Environment variable update |
| 2. Revert application code | < 10 min | Kubernetes rollout undo |
| 3. Update database queries | < 5 min | SQL configuration update |
| 4. Disable validation gate | < 1 min | Environment variable update |
| 5. Verification | < 10 min | Smoke tests, metric validation |
| **Total** | **< 30 min** | **Meets RTO requirement** |

**Success Criteria:**
- ✅ System operational within 30 minutes
- ✅ Match quality restored to baseline
- ✅ No customer-facing errors
- ✅ No data loss

---

### 9.4 Data Restoration Guarantees

**Guarantee 1: No Data Loss**

- **Dual-Write Strategy:** Both scrubbed and unscrubbed data retained during migration
- **Backfill Checksums:** Every backfilled record validated with SHA-256 checksum
- **90-Day Rollback Window:** Legacy data retained for 90 days post-cutover
- **S3 Archive:** 7-year retention of all legacy embeddings (encrypted)

**Guarantee 2: Scrubbing Reversibility**

- **Tokenization Vault:** Business-sensitive data can be detokenized by authorized users
- **Audit Trail:** All scrubbing operations logged with original detection metadata
- **Deterministic Scrubbing:** Same input always produces same output (enables re-scrubbing)

**Guarantee 3: Match Quality Restoration**

- **A/B Testing:** Continuous comparison of scrubbed vs. unscrubbed match quality
- **Baseline Metrics:** Pre-migration match quality baseline captured
- **Automated Alerts:** Alert if match quality deviates > 5% from baseline
- **Rollback Validation:** Post-rollback match quality verified within 1 hour

**Verification:**

```sql
-- Verify no data loss (row count matches)
SELECT 
    (SELECT COUNT(*) FROM team_member_embeddings) AS total_records,
    (SELECT COUNT(DISTINCT team_member_id) FROM team_member_embeddings) AS unique_members,
    (SELECT COUNT(*) FROM pii_scrub_audit) AS audit_records;

-- Verify checksum integrity
SELECT COUNT(*) AS checksum_mismatches
FROM team_member_embeddings
WHERE pii_scrubbed = TRUE
AND scrub_metadata->>'original_checksum' != 
    encode(sha256(profile_text::bytea), 'hex');
```

---

## 10. Definition of Done (DoD) per Phase

### Phase 1: Infrastructure & Core Development (Week 1) (DoD)

- [x] All stakeholders approved (CISO, DPO, Legal, Engineering)
- [ ] GPU instance provisioned and NER model loaded
- [ ] `pii_scrub_audit` table created + permissions configured
- [ ] Prometheus metrics configured, Grafana dashboards deployed
- [ ] PagerDuty integration tested (alert drill conducted)
- [ ] All FR-PII-001 through FR-PII-004 implemented
- [ ] 100 unit tests pass with ≥ 95% code coverage
- [ ] Email detection: 100% recall on 1,000-sample test set (AC-F-001)
- [ ] Phone detection: 95% recall on 1,000-sample test set (AC-F-002)
- [ ] NER detection: F1 ≥ 0.90 on 5,000-sample test set (AC-F-003)
- [ ] False positive rate ≤ 3% on skill/tech terms (AC-F-004)
- [ ] Determinism validated: 1,000 iterations produce identical output (AC-F-005)
- [ ] Idempotency validated: Re-scrubbing same input unchanged (AC-F-006)
- [ ] Hot-reload tested: Rules reload in < 5 seconds without restart (AC-F-008)
- [ ] Audit logging: 100% of operations create audit records (AC-NF-004)
- [ ] No PII in logs: Automated scan finds 0 instances (AC-NF-003)
- [ ] Performance: Scrubbing latency ≤ 50ms p95 (AC-NF-001)
- [ ] Security review completed: No high/critical SAST findings

**Exit Gate Review:** Infrastructure Lead + Security Engineer + Backend Engineers sign-off

---

### Phase 2: Integration & Testing (Week 2) (DoD)

- [ ] Node 0 (PII_Scrubber_Agent) successfully inserted before JD_Parsing_Agent
- [ ] Validation gate rejects 100% of unscrubbed data in tests
- [ ] State schema updated: `PIIScrubMetadata`, `pii_scrubbed` fields added
- [ ] Backward compatibility: Existing checkpoints deserialize without errors
- [ ] Database migration completes without locking tables (< 5 sec locks)
- [ ] Index created: `idx_embeddings_scrubbed_only` (CONCURRENTLY)
- [ ] 20 integration tests pass
- [ ] 20 compliance validation tests pass (GDPR, CCPA, ISO 27001, SOC 2)
- [ ] LangGraph execution validated end-to-end (10 test requisitions)
- [ ] Load test passed: 10,000 profiles/min sustained for 1 hour
- [ ] Circuit breaker tested: Graceful degradation on NER failure
- [ ] Graph topology diagram updated in specs/ai/graph-topology.md v1.1
- [ ] State schema documentation updated in specs/ai/state-schema.md v1.1
- [ ] CI/CD pipeline gates configured (coverage, performance, PII scan)

**Exit Gate Review:** AI Engineer + Backend Engineer + DBA sign-off

---

### Phase 3: Pre-Production Validation (Weeks 3-4) (DoD)

- [ ] Staging environment backfill 100% complete: 250,000 records processed
- [ ] 0 data loss: Row count validation passes (AC-M-003)
- [ ] 0 PII detected in backfilled records (comprehensive scan of all records)
- [ ] Checksum validation: 100% of backfilled records validated
- [ ] Backfill processing rate ≥ 10,000 records/day sustained
- [ ] Audit logs created for all backfilled records
- [ ] A/B testing in staging: Match quality within ±5% baseline (AC-M-002)
- [ ] Full regression test suite passed (100 unit + 20 integration + 20 compliance tests)
- [ ] 0 PII leaks detected in 2-week monitoring period (AC-NF-003)
- [ ] Scrubber error rate < 1% (better than 5% threshold)
- [ ] False positive rate ≤ 3% validated on random sample (AC-F-004)
- [ ] Scrubbing latency ≤ 50ms p95 (AC-NF-001)
- [ ] GPU utilization optimized (≥70% during peak load)
- [ ] Manual review queue processed: 100% of 0.70-0.84 confidence detections reviewed
- [ ] Whitelist updated: New skill terms added based on false positives
- [ ] Rollback procedure tested successfully in staging
- [ ] Blue-green deployment tested: Zero-downtime cutover validated

**Exit Gate Review:** SRE + Backend Engineering Team + Data Team sign-off

---

### Phase 4: Production Deployment (Week 5) (DoD)

- [ ] Production backfill 100% complete: 250,000 legacy records processed (AC-M-001)
- [ ] Blue-green deployment completed: 100% traffic cutover executed
- [ ] Database constraint enforced: `CHECK (pii_scrubbed = TRUE)`
- [ ] RAG queries updated: Only read `WHERE pii_scrubbed = TRUE`
- [ ] S3 archive complete: Legacy embeddings archived (encrypted, 7-year retention)
- [ ] 0 PII leaks detected in 7-day monitoring period (AC-NF-003)
- [ ] Match quality within ±5% baseline (production A/B test) (AC-M-002)
- [ ] Scrubbing latency ≤ 50ms p95 (production metrics) (AC-NF-001)
- [ ] No customer escalations in 7-day monitoring period
- [ ] All acceptance criteria met:
  - [ ] AC-F-001 through AC-F-008 (Functional)
  - [ ] AC-NF-001 through AC-NF-005 (Non-functional)
  - [ ] AC-C-001 through AC-C-005 (Compliance)
  - [ ] AC-M-001 through AC-M-004 (Migration)
- [ ] Compliance reports generated:
  - [ ] GDPR compliance report (Article 5(1)(c), Article 25)
  - [ ] CCPA compliance report (§1798.100, §1798.105)
  - [ ] ISO 27001 evidence pack (A.8.2.3, A.18.1.4)
  - [ ] SOC 2 test results (CC6.1, PI1.2)
- [ ] Security review signed off: CISO approval
- [ ] Prometheus metrics validated: All expected metrics reporting correctly
- [ ] PagerDuty alerts tested: Alert routing confirmed

**Exit Gate Review:** Engineering Director + CISO + Legal + DPO sign-off

---

### Phase 5: Post-Deployment Optimization (Week 6, Optional) (DoD)

- [ ] Vector embeddings re-indexed (optimized for scrubbed data only)
- [ ] Performance tuning completed: NER batch size optimized, GPU memory tuned
- [ ] Legacy code removed: Feature flag logic deleted from codebase
- [ ] All 5 runbooks published:
  - [ ] PII Scrubber Deployment
  - [ ] PII Scrubber Rollback
  - [ ] Backfill Execution
  - [ ] PII Alert Response
  - [ ] Re-Indexing Procedure
- [ ] All 4 ADRs published:
  - [ ] ADR-PII-001: NER Model Selection
  - [ ] ADR-PII-002: Scrubbing Actions
  - [ ] ADR-PII-003: Fail-Closed Policy
  - [ ] ADR-PII-004: Secondary Filtering
- [ ] API documentation updated (scrubbing metadata fields documented)
- [ ] SRE team trained: 100% of on-call engineers completed training
- [ ] Tabletop exercises completed:
  - [ ] Rollback procedure drill
  - [ ] PII leak response drill
- [ ] Post-implementation review completed: Retrospective documented
- [ ] KPIs measured and documented:
  - False positive rate: ≤ 3%
  - Scrubbing latency: ≤ 50ms p95
  - Match quality: ±5% baseline
  - Cache hit rate: ≥ 60%
- [ ] Future enhancements planned: Differential privacy, federated learning
- [ ] Operational handoff complete: SRE team owns production operations

**Exit Gate Review:** SRE + Documentation Team sign-off

---

## 11. Risk Register

| Risk ID | Description | Likelihood | Impact | Severity | Mitigation Strategy | Owner | Status |
|---------|-------------|------------|--------|----------|---------------------|-------|--------|
| **R-001** | NER model F1-score < 0.90 | Low | High | MEDIUM | Pre-validate on 10,000-sample corpus before deployment | ML Engineer | OPEN |
| **R-002** | False positive rate > 5% (skill terms flagged) | Medium | High | HIGH | Whitelist 500+ tech terms, manual review queue | ML Engineer | OPEN |
| **R-003** | Scrubbing latency > 100ms p95 | Medium | Medium | MEDIUM | GPU acceleration, batch processing, async queueing | Backend Eng | OPEN |
| **R-004** | Data loss during backfill | Low | Critical | HIGH | Checksums, dry-run validation, 90-day rollback window | Data Engineer | OPEN |
| **R-005** | Match quality degradation > 10% | Medium | High | HIGH | A/B testing, baseline validation, rollback plan | Product + SRE | OPEN |
| **R-006** | PII leak in logs | Medium | Critical | CRITICAL | Structured logging, daily automated scans, alerts | Security Eng | OPEN |
| **R-007** | Scrubber service outage | Low | Critical | MEDIUM | Fail-closed policy, redundant deployment, circuit breakers | SRE | OPEN |
| **R-008** | Database migration locks production | Low | High | MEDIUM | CONCURRENTLY indexes, statement timeouts, off-peak deployment | DBA | OPEN |
| **R-009** | Customer contract violations (revenue loss) | Low | Critical | HIGH | Legal review, compliance evidence pack, audit prep | Legal | OPEN |
| **R-010** | Regulatory fines (GDPR/CCPA) | Low | Critical | HIGH | Legal sign-off, compliance testing, audit trail | Legal/DPO | OPEN |

**Risk Mitigation Progress Tracking:**

```yaml
# Track risk mitigation progress
risk_mitigation_status:
  R-001:
    status: IN_PROGRESS
    mitigation_actions:
      - NER model validation on 10,000 samples (completed)
      - F1-score baseline: 0.92 (exceeds 0.90 threshold)
  
  R-002:
    status: IN_PROGRESS
    mitigation_actions:
      - Whitelist 500 tech terms (completed)
      - Manual review queue implemented (in testing)
  
  # ... more risks ...
```

---

## 12. Dependency Matrix

| Component | Depends On | Version/Spec | Critical Path? | Mitigation if Unavailable |
|-----------|-----------|--------------|----------------|---------------------------|
| **PII Scrubber** | SpaCy `en_core_web_trf` | 3.5+ | YES | Degrade to regex-only mode |
| **PII Scrubber** | PostgreSQL (audit table) | 13+ | YES | Fail-closed (reject requests) |
| **Graph Topology** | LangGraph | 0.2+ | YES | No workaround (blocking) |
| **Backfill** | Raw profile text (source system) | N/A | YES | Mark records for manual review |
| **NER Engine** | GPU (NVIDIA T4) | CUDA 11+ | NO | CPU fallback (slower) |
| **Monitoring** | Prometheus | 2.40+ | NO | Manual monitoring via logs |
| **Alerting** | PagerDuty | API v2 | NO | Email alerts (slower response) |

**Critical Path Dependencies:**

```
SpaCy NER Model → PII Scrubber → Node 0 → Graph Execution → Embedding Storage
```

**Dependency Readiness Checklist:**

- [ ] SpaCy model downloaded and validated (F1 ≥ 0.90)
- [ ] PostgreSQL audit table created and permissions set
- [ ] LangGraph library updated to 0.2+
- [ ] GPU instance provisioned (or CPU fallback tested)
- [ ] Prometheus/Grafana dashboards deployed
- [ ] PagerDuty integration tested

---

## 13. Branch-to-Spec Traceability Table

| Branch Name | Spec Section(s) | Functional Requirements | Non-Functional Requirements | Acceptance Criteria | PR Link | Status |
|-------------|----------------|------------------------|---------------------------|---------------------|---------|--------|
| **feature/pii-scrubber-core** | FR-PII-001 to FR-PII-004 | FR-PII-001, FR-PII-002, FR-PII-003, FR-PII-004 | NFR-PII-001, NFR-PII-002, NFR-PII-004 | AC-F-001 to AC-F-008 | TBD | NOT STARTED |
| **feature/pii-audit-logging** | NFR-PII-003, FR-6.3 | FR-6.3 | NFR-PII-003 | AC-NF-004 | TBD | NOT STARTED |
| **feature/pii-schema-migration** | Section 11.1, data/logical-data-model.md | N/A | N/A | AC-M-003 | TBD | NOT STARTED |
| **feature/pii-graph-topology** | Section 5.1, ai/graph-topology.md | N/A | N/A | AC-F-007 | TBD | NOT STARTED |
| **feature/pii-backfill** | Section 8.1 | N/A | N/A | AC-M-001, AC-M-002 | TBD | NOT STARTED |
| **feature/pii-observability** | NFR-PII-002 | N/A | NFR-PII-002 | AC-NF-003 | TBD | NOT STARTED |
| **feature/pii-canary-rollout** | Section 13.3 (Weeks 7-8) | N/A | NFR-PII-001 | AC-NF-001, AC-NF-002 | TBD | NOT STARTED |
| **feature/pii-ga-release** | Section 13.3 (Weeks 13-14) | All FR-PII | All NFR-PII | All AC-* | TBD | NOT STARTED |

**Traceability Verification:**

```bash
# Validate all spec references in PR descriptions
git log --grep="Spec Reference:" --oneline

# Check that all FR/NFR IDs are covered
python scripts/validate_spec_coverage.py --branch feature/pii-scrubber-core
```

---

## 14. CI/CD Enforcement Plan

### 14.1 Pre-Commit Checks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pii-scan
        name: Scan for PII in code
        entry: python scripts/scan_for_pii_in_code.py
        language: python
        pass_filenames: false
        always_run: true
      
      - id: spec-reference-check
        name: Validate spec references in commit message
        entry: python scripts/validate_commit_spec_refs.py
        language: python
        stages: [commit-msg]
      
      - id: unit-test-coverage
        name: Check unit test coverage ≥ 90%
        entry: pytest tests/unit/ --cov=src --cov-fail-under=90
        language: python
        pass_filenames: false
```

### 14.2 Pull Request Checks

```yaml
# .github/workflows/pr-checks.yml
name: PR Checks

on: [pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run flake8
        run: flake8 src/ tests/
      - name: Run black
        run: black --check src/ tests/
  
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: pytest tests/unit/ --cov=src --cov-report=xml
      - name: Check coverage threshold
        run: |
          coverage=$(grep 'line-rate' coverage.xml | sed 's/.*line-rate="\([0-9.]*\)".*/\1/')
          if (( $(echo "$coverage < 0.90" | bc -l) )); then
            echo "Coverage $coverage below 90% threshold"
            exit 1
          fi
  
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: test
      redis:
        image: redis:6
    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests
        run: pytest tests/integration/ --maxfail=3
  
  compliance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run compliance tests
        run: pytest tests/compliance/
      - name: Upload compliance evidence
        uses: actions/upload-artifact@v3
        with:
          name: compliance-evidence
          path: test-results/
  
  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run performance benchmarks
        run: pytest tests/performance/ --benchmark-only --benchmark-json=benchmark.json
      - name: Check performance regression
        run: python scripts/check_performance_regression.py --threshold 10
  
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Bandit (SAST)
        run: bandit -r src/ -ll
      - name: Run safety (dependency scan)
        run: safety check --json
  
  pii-leak-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Scan for PII in code
        run: python scripts/scan_for_pii_in_code.py --fail-on-detection
  
  spec-traceability:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate spec references in PR
        run: python scripts/validate_pr_spec_refs.py
```

### 14.3 Merge Gates

**Requirements for Merge to `main`:**

1. ✅ All CI checks pass (lint, tests, scans)
2. ✅ Code coverage ≥ 90%
3. ✅ Performance regression < 10% vs baseline
4. ✅ No PII detected in code/logs
5. ✅ No high/critical SAST findings
6. ✅ 2 approvals:
   - 1 from Security team (mandatory for all PRs)
   - 1 from Backend Engineering team
7. ✅ Spec references validated in PR description
8. ✅ Migration scripts included (if schema changes)
9. ✅ Runbook updated (if operational changes)
10. ✅ CHANGELOG updated

**Branch Protection Rules:**

```yaml
# GitHub branch protection for main
required_status_checks:
  strict: true
  contexts:
    - lint
    - unit-tests
    - integration-tests
    - compliance-tests
    - performance-tests
    - security-scan
    - pii-leak-scan
    - spec-traceability

required_pull_request_reviews:
  required_approving_review_count: 2
  dismiss_stale_reviews: true
  require_code_owner_reviews: true

required_linear_history: true
allow_force_pushes: false
allow_deletions: false
```

### 14.4 Deployment Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy PII Scrubber

on:
  push:
    branches:
      - main
    tags:
      - 'v*.*.*-phase-*'

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to staging
        run: |
          kubectl config use-context staging
          kubectl apply -f k8s/pii-scrubber/
          kubectl rollout status deployment/pii-scrubber
      
      - name: Run smoke tests
        run: pytest tests/smoke/
      
      - name: Validate deployment
        run: python scripts/validate_deployment.py --env staging
  
  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production (blue-green)
        run: |
          kubectl config use-context production
          ./scripts/blue_green_deploy.sh
      
      - name: Monitor for 10 minutes
        run: python scripts/monitor_deployment.py --duration 600
      
      - name: Validate deployment
        run: python scripts/validate_deployment.py --env production
      
      - name: Rollback on failure
        if: failure()
        run: ./scripts/rollback.sh
```

---

## 15. Next Steps & Approvals

### 15.1 Immediate Actions (Week 1)

- [ ] **Stakeholder Review:** Circulate this plan to CISO, DPO, Legal, Engineering Director
- [ ] **Resource Allocation:** Assign team (2 backend engineers, 1 ML engineer, 1 QA engineer, 1 SRE)
- [ ] **Kickoff Meeting:** Schedule implementation kickoff (all stakeholders)
- [ ] **Infrastructure Provisioning:** GPU instance, audit table
- [ ] **Dependencies Installation:** SpaCy model download and validation

### 15.2 Approval Checklist

| Role | Name | Approval Status | Date | Signature |
|------|------|----------------|------|-----------|
| **CISO** | TBD | ⏳ Pending | ________ | ________________ |
| **Data Protection Officer** | TBD | ⏳ Pending | ________ | ________________ |
| **Engineering Director** | TBD | ⏳ Pending | ________ | ________________ |
| **Legal Counsel** | TBD | ⏳ Pending | ________ | ________________ |
| **Product Owner** | TBD | ⏳ Pending | ________ | ________________ |
| **VP Engineering** | TBD | ⏳ Pending | ________ | ________________ |

### 15.3 Implementation Timeline

**Week 1:** Phase 1 (Infrastructure & Core Development)  
**Week 2:** Phase 2 (Integration & Testing)  
**Week 3-4:** Phase 3 (Pre-Production Validation - Staging Backfill)  
**Week 5:** Phase 4 (Production Deployment - One-Shot 100% Rollout)  
**Week 6 (Optional):** Phase 5 (Post-Deployment Optimization)  

**Total Duration:** 5-6 weeks (with optional Week 6 for optimization)  
**Go-Live Target:** Week 5 (100% traffic scrubbed, zero-downtime blue-green deployment)  
**Deployment Strategy:** One-shot rollout with comprehensive pre-production validation (replaces phased 8-week rollout)  

---

## 16. References

- **Change Request:** [spec.md](./spec.md)
- **Impact Summary:** [impact_summary.md](./impact_summary.md)
- **Specifications Updated:** See Section 11.1 (10 files)
- **Compliance Frameworks:**
  - GDPR: https://gdpr-info.eu/
  - CCPA: https://oag.ca.gov/privacy/ccpa
  - ISO 27001: https://www.iso.org/standard/27001
  - SOC 2: https://www.aicpa.org/soc2
- **Technical Documentation:**
  - SpaCy NER: https://spacy.io/usage/linguistic-features#named-entities
  - LangGraph: https://langchain.com/langgraph
  - PostgreSQL: https://www.postgresql.org/docs/

---

**END OF IMPLEMENTATION PLAN**

**Document History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-17 | Principal Delivery Orchestration Agent | Initial implementation plan |
| 2.0.0 | 2026-02-17 | Principal Delivery Orchestration Agent | Updated to one-shot deployment strategy (5-6 weeks vs 16 weeks) |

---

**Plan Status:** ✅ READY FOR EXECUTION  
**Next Milestone:** Phase 1 Infrastructure & Core Development (Week 1)  
**Overall Risk Level:** MEDIUM (acceptable with mitigation strategies in place)  
**Revenue Protection:** $45M ARR  
**Risk Reduction:** $7.5M annually  
**Deployment Model:** One-Shot Rollout with Pre-Production Validation  
