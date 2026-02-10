# Non-Functional Requirements - Nightly Batch Ingestion Service

**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Owner:** Platform Engineering

---

## 1. Overview

This document defines the non-functional requirements (NFRs) for the nightly batch ingestion service, including performance, security, reliability, scalability, and operational requirements.

---

## 2. Performance Requirements

### 2.1 Processing Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Total Duration** | < 30 minutes | 95th percentile for full ingestion |
| **Throughput** | ≥ 100 records/second | Per batch processor |
| **Batch Processing Time** | < 10 seconds per batch | For 100-record batches |
| **API Response Time** | < 2 seconds | External API fetch per batch |
| **Database Transaction Time** | < 5 seconds | Per batch UPSERT operation |
| **Memory Usage** | < 2 GB | Peak memory consumption |
| **CPU Usage** | < 1 CPU core | Average during processing |

### 2.2 Scalability Targets

```python
# Expected data volumes

DAILY_RECORDS = 10000          # Total records per night
BATCH_SIZE = 100                # Records per batch
TOTAL_BATCHES = 100             # Total batches per run

GROWTH_RATE = 1.20              # 20% YoY growth
EXPECTED_RECORDS_2027 = 12000   # After 1 year
EXPECTED_RECORDS_2028 = 14400   # After 2 years

# System must handle:
# - Up to 20,000 records per night (2x current volume)
# - 200 batches per run
# - Complete processing within 1 hour
```

### 2.3 Performance Benchmarks

```python
import time
from dataclasses import dataclass

@dataclass
class PerformanceBenchmark:
    """Performance benchmark results."""
    total_records: int
    total_batches: int
    total_duration_seconds: float
    records_per_second: float
    avg_batch_duration_ms: float
    
    def meets_requirements(self) -> bool:
        """Check if benchmarks meet NFRs."""
        return (
            self.total_duration_seconds < 1800 and  # < 30 minutes
            self.records_per_second >= 100 and
            self.avg_batch_duration_ms < 10000
        )


def run_performance_benchmark(record_count: int = 10000):
    """
    Run performance benchmark.
    
    Usage:
        ./benchmark.py --records 10000
    """
    start_time = time.time()
    
    batches = create_test_batches(record_count)
    
    batch_durations = []
    
    for batch in batches:
        batch_start = time.time()
        process_batch(batch["batch_id"], batch["team_members"])
        batch_duration = (time.time() - batch_start) * 1000
        batch_durations.append(batch_duration)
    
    total_duration = time.time() - start_time
    avg_batch_duration = sum(batch_durations) / len(batch_durations)
    
    benchmark = PerformanceBenchmark(
        total_records=record_count,
        total_batches=len(batches),
        total_duration_seconds=total_duration,
        records_per_second=record_count / total_duration,
        avg_batch_duration_ms=avg_batch_duration
    )
    
    print(f"Performance Benchmark Results:")
    print(f"  Total Records: {benchmark.total_records}")
    print(f"  Total Duration: {benchmark.total_duration_seconds:.2f}s")
    print(f"  Throughput: {benchmark.records_per_second:.2f} records/sec")
    print(f"  Avg Batch Duration: {benchmark.avg_batch_duration_ms:.2f}ms")
    print(f"  Meets Requirements: {benchmark.meets_requirements()}")
    
    return benchmark
```

---

## 3. Security Requirements

### 3.1 Authentication & Authorization

```python
# REQUIRED: OAuth 2.0 Client Credentials
# - Client ID and secret stored in secure secret management (Vault, AWS Secrets Manager)
# - Tokens refreshed automatically before expiration
# - No hardcoded credentials in code or config files

# REQUIRED: Database credentials
# - Separate service account with minimal privileges
# - Password stored in secure secret management
# - Connection string never logged

# REQUIRED: TLS for all network communication
# - External API: TLS 1.2+
# - Database: TLS 1.2+ with certificate validation
```

### 3.2 Secrets Management

```yaml
# Kubernetes Secrets (sealed secrets in production)

apiVersion: v1
kind: Secret
metadata:
  name: ingestion-secrets
  namespace: ib-job-skill-mapping
type: Opaque
data:
  # Base64 encoded values (use SealedSecrets in production)
  db-password: <BASE64_ENCODED>
  api-client-id: <BASE64_ENCODED>
  api-client-secret: <BASE64_ENCODED>
```

```python
# Secret loading from environment variables

import os

def load_secrets():
    """Load secrets from environment or secret files."""
    
    # Database credentials
    DB_PASSWORD = os.getenv("DB_PASSWORD") or read_secret_file("/run/secrets/db_password")
    
    # API credentials
    API_CLIENT_ID = os.getenv("API_CLIENT_ID") or read_secret_file("/run/secrets/api_client_id")
    API_CLIENT_SECRET = os.getenv("API_CLIENT_SECRET") or read_secret_file("/run/secrets/api_client_secret")
    
    # Validate secrets loaded
    assert DB_PASSWORD, "DB_PASSWORD not found"
    assert API_CLIENT_ID, "API_CLIENT_ID not found"
    assert API_CLIENT_SECRET, "API_CLIENT_SECRET not found"
    
    return {
        "db_password": DB_PASSWORD,
        "api_client_id": API_CLIENT_ID,
        "api_client_secret": API_CLIENT_SECRET
    }


def read_secret_file(path: str) -> str:
    """Read secret from file (Docker/Kubernetes secret mount)."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
```

### 3.3 Data Security

| Requirement | Implementation |
|-------------|----------------|
| **Encryption at Rest** | Database encryption enabled (PostgreSQL Transparent Data Encryption) |
| **Encryption in Transit** | TLS 1.2+ for all network communication |
| **PII Handling** | No PII logged; email/name hashed in audit logs |
| **Access Control** | Service account with INSERT/UPDATE only (no DELETE) |
| **Secret Rotation** | Secrets rotated every 90 days |
| **Audit Trail** | All ingestion events logged with correlation ID |

### 3.4 Security Checklist

```python
def security_validation():
    """Pre-run security validation."""
    
    checks = {
        "No hardcoded secrets": check_no_hardcoded_secrets(),
        "TLS enabled": check_tls_enabled(),
        "Certificate validation": check_cert_validation(),
        "Secrets loaded": check_secrets_loaded(),
        "Least privilege DB user": check_db_privileges()
    }
    
    for check, result in checks.items():
        if not result:
            raise SecurityError(f"Security check failed: {check}")
    
    return True


def check_no_hardcoded_secrets() -> bool:
    """Verify no hardcoded secrets in codebase."""
    # Automated check in CI/CD pipeline (truffleHog, GitGuardian)
    return True


def check_tls_enabled() -> bool:
    """Verify TLS is enforced for database and API."""
    # Check database connection string
    if not db_url.startswith("postgresql://") or "sslmode=require" not in db_url:
        return False
    
    # Check API client TLS
    if not api_client.verify_ssl:
        return False
    
    return True
```

---

## 4. Reliability Requirements

### 4.1 Availability Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Success Rate** | ≥ 99.5% | Monthly basis (max 1 failure per 30 days) |
| **Recovery Time** | < 4 hours | From failure detection to resolution |
| **Data Loss** | Zero tolerance | All batches must eventually succeed or be flagged for manual review |

### 4.2 Failure Handling

```python
class FailureHandling:
    """Failure handling strategy."""
    
    MAX_RETRIES = 3
    BACKOFF_BASE_SECONDS = 60
    
    def handle_failure(self, batch_id: str, error: Exception):
        """
        Handle batch processing failure.
        
        Strategy:
        1. Classify error (retryable vs fatal)
        2. Log error with full context
        3. Update batch state
        4. Send alert if critical
        5. Schedule retry if eligible
        """
        error_category = classify_error(error)
        
        # Log error
        logger.error(
            f"Batch processing failed: {batch_id}",
            error_category=error_category.value,
            exception=str(error),
            stack_trace=traceback.format_exc()
        )
        
        # Update batch state
        with engine.begin() as conn:
            update_batch_state(
                conn,
                batch_id,
                status="FAILED",
                error_message=str(error),
                error_category=error_category.value
            )
        
        # Send alert for critical errors
        if error_category in [ErrorCategory.AUTHENTICATION_ERROR, ErrorCategory.SCHEMA_MISMATCH]:
            send_slack_notification(
                correlation_id,
                f"Critical error in batch {batch_id}: {error_category.value}",
                severity="error"
            )
        
        # Schedule retry if eligible
        if is_retryable(error_category):
            retry_count = get_retry_count(batch_id)
            if retry_count < self.MAX_RETRIES:
                delay = self.BACKOFF_BASE_SECONDS * (2 ** retry_count)
                schedule_retry(batch_id, delay)
```

### 4.3 Data Integrity

```python
def validate_data_integrity():
    """
    Validate data integrity after ingestion.
    
    Checks:
    - Referential integrity (foreign keys valid)
    - No orphaned records
    - Record counts match expected
    - No duplicate records (beyond natural key UPSERTs)
    """
    with engine.connect() as conn:
        # Check referential integrity
        orphaned_skills = conn.execute("""
            SELECT COUNT(*) FROM team_member_skill tms
            LEFT JOIN team_member tm ON tms.team_member_id = tm.team_member_id
            WHERE tm.team_member_id IS NULL
        """).scalar()
        
        if orphaned_skills > 0:
            raise DataIntegrityError(f"Found {orphaned_skills} orphaned skills")
        
        # Check record counts
        expected_members = get_expected_member_count()
        actual_members = conn.execute("SELECT COUNT(*) FROM team_member").scalar()
        
        if abs(actual_members - expected_members) > expected_members * 0.1:  # 10% tolerance
            raise DataIntegrityError(
                f"Record count mismatch: expected ~{expected_members}, got {actual_members}"
            )
        
        logger.info("Data integrity validation passed")
```

---

## 5. Operational Requirements

### 5.1 Monitoring and Observability

```python
# REQUIRED: Metrics collection
# - Prometheus metrics exposed on :8000/metrics
# - Key metrics: ingestion_runs_total, batch_duration_seconds, errors_total

# REQUIRED: Structured logging
# - JSON format for log aggregation (ELK, Splunk)
# - Correlation ID for request tracing
# - Log level: INFO (production), DEBUG (troubleshooting)

# REQUIRED: Distributed tracing (optional but recommended)
# - OpenTelemetry spans for batch processing
# - Jaeger/Zipkin for trace visualization

# REQUIRED: Health checks
# - Pre-run health checks (database, API, schema version)
# - Exit codes for failure classification
```

### 5.2 Alerting Requirements

```yaml
# REQUIRED: Critical alerts (PagerDuty)
- Ingestion job failed completely
- OAuth authentication failed
- Database schema version mismatch
- No successful run in 24 hours

# REQUIRED: Warning alerts (Slack)
- Batch failure rate > 20%
- Processing duration > 45 minutes
- Retry attempts exceeded for batch

# OPTIONAL: Info alerts (Email)
- Ingestion completed successfully
- Partial success (some batches failed)
```

### 5.3 Runbook Requirements

```markdown
# Runbook: Nightly Batch Ingestion Failure

## Symptoms
- Alert: "Ingestion job failed"
- No records updated in last 24 hours
- Batch state shows FAILED status

## Investigation Steps
1. Check recent logs:
   ```bash
   kubectl logs -n ib-job-skill-mapping -l app=team-data-ingestion --tail=200
   ```

2. Query failed batches:
   ```sql
   SELECT * FROM ingestion_batch_state 
   WHERE status = 'FAILED' 
   ORDER BY first_attempted_at DESC 
   LIMIT 10;
   ```

3. Check error category:
   - AUTHENTICATION_ERROR → Verify API credentials
   - SCHEMA_MISMATCH → Run Alembic migrations
   - NETWORK_ERROR → Retry failed batches

## Resolution Steps
1. For authentication errors:
   ```bash
   # Verify secrets
   kubectl get secret external-api-secret -n ib-job-skill-mapping -o yaml
   
   # Update if needed
   kubectl create secret generic external-api-secret --from-literal=client_id=NEW_ID --dry-run=client -o yaml | kubectl apply -f -
   ```

2. For schema mismatch:
   ```bash
   # Run migrations
   alembic upgrade head
   ```

3. Retry failed batches:
   ```bash
   # Kubernetes
   kubectl create job --from=cronjob/team-data-ingestion retry-failed-$(date +%Y%m%d-%H%M%S) -n ib-job-skill-mapping
   
   # Traditional
   python3 /opt/ib-job-skill-mapping-system/src/app/ingest_team_data.py --retry-failed
   ```

## Escalation
- If resolution steps fail, escalate to Platform Engineering on-call
- Slack: #platform-oncall
- PagerDuty: Platform Engineering service
```

---

## 6. Maintainability Requirements

### 6.1 Code Quality

```python
# REQUIRED: Code standards
# - Python 3.11+ type hints
# - Docstrings for all public functions
# - Pylint score ≥ 8.0
# - Unit test coverage ≥ 80%
# - Integration test coverage ≥ 60%

# REQUIRED: Dependency management
# - All dependencies pinned in pyproject.toml
# - Security scanning (Snyk, Safety)
# - Monthly dependency updates

# REQUIRED: Documentation
# - README with setup instructions
# - Architecture diagrams
# - API documentation (external API client)
# - Database schema documentation
```

### 6.2 Testing Requirements

```python
def test_full_ingestion_workflow():
    """End-to-end integration test."""
    # Setup test database
    test_engine = create_test_database()
    
    # Run Alembic migrations
    run_alembic_upgrade(test_engine)
    
    # Mock external API
    with mock_external_api():
        # Run ingestion
        result = run_ingestion(test_engine)
        
        # Assertions
        assert result.exit_code == ExitCode.SUCCESS
        assert result.total_batches == 10
        assert result.successful_batches == 10
        assert result.failed_batches == 0
        
        # Verify data
        with test_engine.connect() as conn:
            member_count = conn.execute("SELECT COUNT(*) FROM team_member").scalar()
            assert member_count == 1000
    
    # Cleanup
    drop_test_database(test_engine)


def test_retry_mechanism():
    """Test retry logic for failed batches."""
    # Simulate batch failure
    batch_id = "TEST-BATCH-001"
    simulate_batch_failure(batch_id, error_category=ErrorCategory.NETWORK_ERROR)
    
    # Verify batch state
    state = get_batch_state(batch_id)
    assert state["status"] == "FAILED"
    assert state["retry_count"] == 0
    
    # Run retry
    retry_failed_batches()
    
    # Verify retry attempted
    state = get_batch_state(batch_id)
    assert state["retry_count"] == 1
    
    # Verify exponential backoff
    assert calculate_retry_delay(1) == 60
    assert calculate_retry_delay(2) == 120
    assert calculate_retry_delay(3) == 240


def test_idempotency():
    """Test that processing same batch twice produces identical result."""
    batch_id = "TEST-BATCH-002"
    payload = generate_test_payload()
    
    # Process first time
    process_batch(batch_id, payload["team_members"])
    snapshot1 = get_database_snapshot()
    
    # Process second time
    process_batch(batch_id, payload["team_members"])
    snapshot2 = get_database_snapshot()
    
    # Verify identical state
    assert snapshot1 == snapshot2
```

### 6.3 Versioning and Deployment

```yaml
# Semantic versioning: MAJOR.MINOR.PATCH

# MAJOR: Breaking changes (schema changes, API contract changes)
# MINOR: New features (new fields, optional parameters)
# PATCH: Bug fixes, performance improvements

# Deployment strategy:
# 1. Run migrations (alembic upgrade head)
# 2. Deploy new CronJob image
# 3. Validate with dry-run
# 4. Monitor first scheduled run
# 5. Rollback procedure documented
```

---

## 7. Compliance and Audit

### 7.1 Audit Requirements

```python
# REQUIRED: Audit trail
# - Every ingestion run logged with correlation ID
# - Batch state tracked in database
# - All errors logged with full context
# - Audit log retention: 90 days minimum

# REQUIRED: Compliance
# - GDPR: PII handling documented
# - SOC 2: Access controls enforced
# - Data retention policy: 90 days for audit logs, indefinite for business data
```

### 7.2 Audit Log Retention

```sql
-- Archive old audit logs

CREATE TABLE ingestion_audit_log_archive (
    LIKE ingestion_audit_log INCLUDING ALL
);

-- Archive logs older than 90 days
INSERT INTO ingestion_audit_log_archive
SELECT * FROM ingestion_audit_log
WHERE created_at < CURRENT_DATE - INTERVAL '90 days';

-- Delete archived logs
DELETE FROM ingestion_audit_log
WHERE created_at < CURRENT_DATE - INTERVAL '90 days';
```

---

## 8. Disaster Recovery

### 8.1 Backup and Recovery

```bash
# Database backup before migration
pg_dump -h localhost -p 5433 -U postgres -d ib_job_skill_mapping > backup_$(date +%Y%m%d).sql

# Point-in-time recovery
# - Daily automated backups
# - Retention: 30 days
# - RTO (Recovery Time Objective): 4 hours
# - RPO (Recovery Point Objective): 24 hours (last successful ingestion)
```

### 8.2 Rollback Procedure

```bash
# Rollback CronJob deployment
kubectl rollout undo cronjob/team-data-ingestion -n ib-job-skill-mapping

# Rollback database migration
alembic downgrade -1

# Verify rollback
kubectl get cronjob team-data-ingestion -n ib-job-skill-mapping -o yaml
alembic current
```

---

## 9. Capacity Planning

### 9.1 Resource Projections

| Year | Records/Night | Duration (min) | Memory (GB) | CPU (cores) | Storage (GB/month) |
|------|---------------|----------------|-------------|-------------|-------------------|
| 2026 | 10,000 | 25 | 1.5 | 0.8 | 50 |
| 2027 | 12,000 | 30 | 1.8 | 0.9 | 60 |
| 2028 | 14,400 | 36 | 2.0 | 1.0 | 72 |
| 2029 | 17,280 | 43 | 2.5 | 1.2 | 86 |

### 9.2 Scaling Strategy

```python
# Current design handles up to 20,000 records/night
# If exceeding capacity:
# 1. Increase Kubernetes resource limits
# 2. Optimize batch size (tune to database capabilities)
# 3. Enable parallel batch processing (future enhancement)
# 4. Consider sharding by team/department (major refactor)
```

---

## 10. Definition of Done

- [ ] Performance benchmarks meet targets (< 30 min, 100 records/sec)
- [ ] Security validation passed (no hardcoded secrets, TLS enabled)
- [ ] Reliability targets documented (99.5% success rate)
- [ ] Monitoring and alerting configured
- [ ] Runbook created and tested
- [ ] Unit test coverage ≥ 80%
- [ ] Integration tests passing
- [ ] Documentation complete (README, architecture, API docs)
- [ ] Disaster recovery procedure tested
- [ ] Capacity planning reviewed and approved

---

**Document Status:** Ready for Review  
**Next Steps:** Review NFRs with stakeholders and obtain sign-off before implementation

---

## Appendix: Service Level Agreement (SLA)

```yaml
# SLA for Nightly Batch Ingestion Service

Availability:
  Target: 99.5% (monthly)
  Measurement: Successful completion rate
  Penalty: None (internal service)

Performance:
  Target: < 30 minutes (95th percentile)
  Measurement: End-to-end duration
  Penalty: None (internal service)

Data Freshness:
  Target: Data available by 3:00 AM IST daily
  Measurement: Last successful ingestion timestamp
  Escalation: Platform on-call if not complete by 6:00 AM IST

Support:
  Hours: 24/7 (PagerDuty for critical alerts)
  Response Time: < 15 minutes (critical), < 2 hours (warning)
  Resolution Time: < 4 hours (critical), < 1 business day (warning)
```

---

**Approval:**
- Platform Engineering Lead: ___________________ Date: ___________
- Data Engineering Lead: ___________________ Date: ___________
- Security Lead: ___________________ Date: ___________
