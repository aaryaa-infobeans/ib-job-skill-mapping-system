# PII Scrubber Production Backfill Runbook
**TASK-PII-241: Document backfill execution plan**

**Version:** 1.0.0  
**Last Updated:** 2026-02-17  
**Owner:** Data Engineering + SRE  

---

## Executive Summary

This runbook provides step-by-step instructions for executing the production backfill of 250,000 legacy records through the PII scrubber. The backfill will process 50,000 records/day over 5 days during off-peak hours (8 PM - 6 AM).

---

## Pre-Execution Checklist

### Infrastructure Validation

- [ ] **GPU Instance Ready**
  - Run: `nvidia-smi` to verify GPU availability
  - Verify CUDA 11+ installed
  - GPU utilization < 30% before backfill starts

- [ ] **Database Health**
  - Run: `scripts/validate_staging_infrastructure.py --environment=production`
  - Verify `pii_scrub_audit` table exists
  - Verify immutability triggers configured
  - Check disk space: > 100 GB free

- [ ] **Application Deployment**
  - Green environment deployed and tested
  - Health checks passing
  - Smoke tests passed (100 test requisitions)

- [ ] **Monitoring & Alerting**
  - Prometheus scraping metrics
  - Grafana dashboards available
  - PagerDuty alerts configured
  - On-call engineer assigned

### Data Preparation

- [ ] **Backup Production Data**
  ```sql
  -- Create backup table
  CREATE TABLE team_member_embeddings_backup_20260217 AS 
  SELECT * FROM team_member_embeddings WHERE pii_scrubbed = FALSE;
  
  -- Verify row count
  SELECT COUNT(*) FROM team_member_embeddings_backup_20260217;
  -- Expected: 250,000
  ```

- [ ] **Verify Data Anonymization** (if using staging data)
  - Run: `python scripts/anonymize_data.py --mode=generate --output-file=data/staging_profiles.jsonl --count=250000`
  - Verify checksums: `sha256sum data/staging_profiles.jsonl`

---

## Execution Steps

### Phase 1: Day 0 (Preparation)

**Time:** 6:00 PM - 8:00 PM  
**Duration:** 2 hours  

1. **Notify Stakeholders**
   ```
   Send notification:
   - Subject: "PII Scrubber Production Backfill Starting Tonight"
   - To: Engineering, Product, Legal, Security
   - Content: Timeline, expected impact, monitoring links
   ```

2. **Enable Monitoring**
   ```bash
   # Verify Grafana dashboards accessible
   curl -s http://grafana.company.com/api/health | jq .
   
   # Verify PagerDuty integration
   scripts/test_pagerduty_alert.sh
   ```

3. **Final Infrastructure Check**
   ```bash
   python scripts/validate_staging_infrastructure.py \
     --environment=production \
     --report-file=validation-report-pre-backfill.json
   
   # Verify PASSED status
   cat validation-report-pre-backfill.json | jq .summary.status
   ```

### Phase 2: Days 1-5 (Backfill Execution)

**Time:** 8:00 PM - 6:00 AM (off-peak)  
**Daily Target:** 50,000 records  
**Batch Size:** 1,000 records/batch  

#### Start Backfill

```bash
# Day 1: Records 1-50,000
python scripts/execute_backfill.py \
  --environment=production \
  --input-file=data/production_profiles.jsonl \
  --total-records=50000 \
  --batch-size=1000 \
  --target-per-day=50000 \
  --report-file=backfill-report-day1.json

# Day 2: Records 50,001-100,000
python scripts/execute_backfill.py \
  --environment=production \
  --input-file=data/production_profiles.jsonl \
  --total-records=100000 \
  --batch-size=1000 \
  --target-per-day=50000 \
  --resume-from=50000 \
  --report-file=backfill-report-day2.json

# Day 3: Records 100,001-150,000
python scripts/execute_backfill.py \
  --environment=production \
  --input-file=data/production_profiles.jsonl \
  --total-records=150000 \
  --batch-size=1000 \
  --target-per-day=50000 \
  --resume-from=100000 \
  --report-file=backfill-report-day3.json

# Day 4: Records 150,001-200,000
python scripts/execute_backfill.py \
  --environment=production \
  --input-file=data/production_profiles.jsonl \
  --total-records=200000 \
  --batch-size=1000 \
  --target-per-day=50000 \
  --resume-from=150000 \
  --report-file=backfill-report-day4.json

# Day 5: Records 200,001-250,000
python scripts/execute_backfill.py \
  --environment=production \
  --input-file=data/production_profiles.jsonl \
  --total-records=250000 \
  --batch-size=1000 \
  --target-per-day=50000 \
  --resume-from=200000 \
  --report-file=backfill-report-day5.json
```

#### Monitor Progress (Every Hour)

```bash
# Check current batch progress
tail -f backfill_checkpoint_production.json

# Check database row count
psql -c "SELECT COUNT(*) FROM team_member_embeddings WHERE pii_scrubbed = TRUE;"

# Check error rate
psql -c "SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN pii_scrubbed = FALSE THEN 1 ELSE 0 END) as remaining,
  ROUND(100.0 * SUM(CASE WHEN pii_scrubbed = TRUE THEN 1 ELSE 0 END) / COUNT(*), 2) as progress_pct
FROM team_member_embeddings;"

# Check Grafana dashboard
open http://grafana.company.com/d/pii-scrubber-backfill
```

#### Recovery from Interruption

If backfill is interrupted:

```bash
# Check last checkpoint
cat backfill_checkpoint_production.json | jq .position

# Resume from checkpoint
python scripts/execute_backfill.py \
  --environment=production \
  --input-file=data/production_profiles.jsonl \
  --total-records=250000 \
  --batch-size=1000 \
  --target-per-day=50000 \
  --resume-from=<CHECKPOINT_POSITION> \
  --report-file=backfill-report-recovery.json
```

### Phase 3: Day 6 (Validation)

**Time:** 9:00 AM - 5:00 PM  
**Duration:** Full day  

#### 1. Verify Completion

```sql
-- Expected: 0 unscrubbed records
SELECT COUNT(*) FROM team_member_embeddings WHERE pii_scrubbed = FALSE;

-- Expected: 250,000 scrubbed records
SELECT COUNT(*) FROM team_member_embeddings WHERE pii_scrubbed = TRUE;

-- Expected: 250,000 audit records
SELECT COUNT(*) FROM pii_scrub_audit;
```

#### 2. Checksum Validation

```bash
python scripts/execute_backfill.py \
  --environment=production \
  --input-file=data/production_profiles.jsonl \
  --total-records=250000 \
  --validate-checksums-only
```

**Expected:** 100% checksum validation passes

#### 3. PII Leak Scan

```bash
# Scan backfilled data (10,000 sample)
python scripts/scan_pii_leaks.py \
  --scan-data=data/production_profiles.jsonl \
  --sample-size=10000 \
  --report-file=pii-leak-scan-production.json

# Verify 0 PII instances detected
cat pii-leak-scan-production.json | jq .total_leaks
```

**Expected:** 0 PII instances detected

#### 4. Audit Log Validation

```sql
-- Verify 1:1 mapping
SELECT 
  (SELECT COUNT(*) FROM team_member_embeddings WHERE pii_scrubbed = TRUE) as scrubbed_count,
  (SELECT COUNT(*) FROM pii_scrub_audit) as audit_count,
  CASE 
    WHEN (SELECT COUNT(*) FROM team_member_embeddings WHERE pii_scrubbed = TRUE) = 
         (SELECT COUNT(*) FROM pii_scrub_audit)
    THEN 'PASSED'
    ELSE 'FAILED'
  END as validation_status;
```

**Expected:** validation_status = 'PASSED'

---

## Rollback Procedure

**TASK-PII-243: Test rollback procedure**

**Trigger Criteria:**
- Error rate > 5% for any batch
- PII leak detected in scrubbed data
- Checksum validation fails for > 1% of records
- Critical production incident

**Rollback Steps:**

### 1. Stop Backfill

```bash
# Send SIGTERM to backfill process
ps aux | grep execute_backfill
kill -TERM <PID>

# Verify checkpoint saved
cat backfill_checkpoint_production.json
```

### 2. Switch Traffic to Blue

```bash
# Switch load balancer to blue environment
python scripts/deploy_staging.py --rollback

# Verify traffic routing
curl -s http://load-balancer/health | jq .environment
# Expected: "blue"
```

### 3. Restore Database State (if needed)

```sql
-- Option 1: Revert scrubbed records (keep audit log)
UPDATE team_member_embeddings 
SET pii_scrubbed = FALSE, pii_scrub_metadata = NULL
WHERE id IN (SELECT id FROM backfill_checkpoint_production);

-- Option 2: Full restore from backup
TRUNCATE team_member_embeddings;
INSERT INTO team_member_embeddings 
SELECT * FROM team_member_embeddings_backup_20260217;
```

### 4. Remove Database Constraint

```sql
-- Disable constraint temporarily
ALTER TABLE team_member_embeddings 
DROP CONSTRAINT IF EXISTS team_member_embeddings_pii_scrubbed_check;
```

### 5. Verify Rollback

```bash
# Run smoke tests on blue environment
python scripts/test_match_quality.py \
  --requisition-count=100 \
  --report-file=rollback-validation.json

# Verify all checks pass
cat rollback-validation.json | jq .all_checks_passed
```

**Rollback Completion Time:** < 30 minutes (TASK-PII-243 target)

---

## Post-Execution Validation

### 1. Match Quality Validation

```bash
python scripts/test_match_quality.py \
  --requisition-count=10000 \
  --manual-review-size=1000 \
  --total-processed=250000 \
  --failed-count=0 \
  --report-file=match-quality-validation.json
```

**Success Criteria:**
- Match quality within ±5% baseline
- p95 latency ≤ 200ms
- False positive rate ≤ 3%
- Error rate < 1%

### 2. Performance Validation

```bash
python scripts/run_performance_benchmark.py \
  --target-rpm=10000 \
  --duration-hours=0.5 \
  --latency-target-ms=50 \
  --report-file=performance-validation.json
```

**Success Criteria:**
- p95 latency ≤ 50ms at production load
- Sustained throughput ≥ 10,000 req/min

### 3. Security Validation

```bash
# PII leak scan
python scripts/scan_pii_leaks.py \
  --scan-logs=/var/log/app \
  --scan-metrics=http://localhost:8000/metrics \
  --scan-code=src/app \
  --report-file=security-validation.json
```

**Success Criteria:**
- 0 PII leaks in logs
- 0 PII leaks in metrics
- 0 hardcoded PII in code

---

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Backfill Progress**
   - `pii_backfill_progress_total` (gauge)
   - `pii_backfill_batch_duration_seconds` (histogram)

2. **Error Rate**
   - `pii_scrubbing_errors_total` (counter)
   - Alert: > 5% error rate for 10 minutes

3. **Latency**
   - `pii_scrubbing_latency_seconds` (histogram)
   - Alert: p95 > 75ms for 5 minutes

4. **PII Leaks**
   - `pii_leak_detections_total` (counter)
   - Alert: Any detection triggers immediate page

5. **Database Health**
   - `database_connections_active` (gauge)
   - `database_query_duration_seconds` (histogram)

### Dashboard Links

- **Backfill Progress:** `http://grafana.company.com/d/pii-scrubber-backfill`
- **System Health:** `http://grafana.company.com/d/pii-scrubber-health`
- **Performance:** `http://grafana.company.com/d/pii-scrubber-performance`

---

## Stakeholder Communication

### Daily Status Updates

**Template:**

```
Subject: PII Scrubber Backfill - Day X Status

Progress:
- Records processed: X / 250,000 (Y%)
- Success rate: Z%
- Error rate: A%
- Current p95 latency: Bms

Issues:
- [None] or [List of issues]

Next Steps:
- Continue backfill Day X+1 (8 PM - 6 AM)

Monitoring:
- Dashboard: http://grafana.company.com/d/pii-scrubber-backfill
```

### Completion Notification

```
Subject: PII Scrubber Backfill - COMPLETE

Summary:
- Total records processed: 250,000
- Success rate: 100%
- Duration: 5 days
- PII leaks detected: 0
- Validation status: PASSED

Next Steps:
- Enable database constraint (Day 6, 2 PM)
- Update RAG queries to filter scrubbed data
- Extended monitoring (48 hours)

Production Cutover:
- Scheduled: Day 7, 10 AM
- Traffic switch: Blue → Green (100%)
```

---

## Appendix

### Contact Information

- **On-Call Engineer:** <pagerduty-schedule>
- **Data Engineering Lead:** <email>
- **SRE Lead:** <email>
- **Engineering Director:** <email>

### Related Documents

- [PII Scrubber Specification](../specs/change-request/CR_PII_scrubber.md)
- [Deployment Runbook](../docs/deployment-runbook.md)
- [Rollback Procedure](../docs/rollback-procedure.md)
- [Phase 3 Validation Report](../docs/phase-3-validation-report.md)

### Escalation Path

1. **Level 1:** On-call engineer (PagerDuty)
2. **Level 2:** SRE Lead + Data Engineering Lead
3. **Level 3:** Engineering Director
4. **Level 4:** CTO

---

**Document Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-17 | System | Initial runbook |
