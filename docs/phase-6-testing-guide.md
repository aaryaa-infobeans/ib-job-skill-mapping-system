# Phase 6: Performance & Scalability Testing Guide

This guide covers all testing procedures for Phase 6: Hardening & Scale Readiness.

## Overview

Phase 6 validates the system's operational readiness through:
1. **Performance Testing** - Load and stress tests to validate latency targets
2. **Scalability Testing** - Validate system handles 5x production data volume
3. **Reliability Testing** - Verify idempotent retry behavior

## Prerequisites

### Software Requirements

- **k6** (Load testing tool)
  - macOS: `brew install k6`
  - Windows: `choco install k6`
  - Linux: `sudo apt-get install k6`

- **Python 3.10+** (For data generation and reliability tests)
  ```bash
  pip install sqlalchemy psycopg2-binary jose requests
  ```

### Authentication

Generate a JWT token for API authentication:

```python
from jose import jwt
from datetime import datetime, timedelta

payload = {
    "sub": "test-client",
    "scopes": ["read", "write"],
    "exp": datetime.utcnow() + timedelta(hours=24)
}

token = jwt.encode(payload, "your-secret-key", algorithm="HS256")
print(f"JWT Token: {token}")
```

## Task 6.1: Performance Test Suite

### Smoke Test (Quick Validation)

Run before larger tests to verify system is functional:

```bash
export BASE_URL=http://localhost:8000
export AUTH_TOKEN="your-jwt-token"

k6 run performance-tests/smoke-test.js
```

**Expected Results:**
- ✅ All endpoints return 200 status
- ✅ P95 latency < 3 seconds
- ✅ No failures

### Load Test (Realistic Traffic)

Simulates realistic production load:

```bash
k6 run performance-tests/load-test.js
```

**Load Profile:**
- Ramp-up: 10 → 50 → 100 concurrent users over ~6 minutes
- Duration: ~7 minutes total
- Endpoints: FR-1 (requisitions), FR-2 (matches), FR-3 (bulk upsert)

**Success Criteria (NFR-1.1, NFR-1.2, NFR-1.3):**
- ✅ P95 latency < 2 seconds
- ✅ P99 latency < 5 seconds
- ✅ Error rate < 5%
- ✅ Throughput ≥ 100 requests/second

### Stress Test (Breaking Point)

Identifies system limits:

```bash
k6 run performance-tests/stress-test.js
```

**Load Profile:**
- Aggressive ramp: 100 → 400 users over 30 minutes
- Purpose: Find breaking points and bottlenecks
- More lenient thresholds to capture degradation

**Expected Observations:**
- System handles 100-200 VUs without issues
- Degradation starts around 300+ VUs
- Identify bottlenecks (DB connections, memory, CPU)

### Generate HTML Reports

```bash
k6 run --out json=results.json performance-tests/load-test.js
k6 run --summary-export=summary.json performance-tests/load-test.js
```

Then use k6 Cloud or custom visualization.

## Task 6.2: Performance Test Execution

### Pre-Test Checklist

1. ✅ System is running in production-like environment
2. ✅ Database is warmed up (run smoke test)
3. ✅ No other load on system
4. ✅ Monitoring tools active (Prometheus, Grafana)
5. ✅ Sufficient database connections available

### Test Execution Procedure

**Step 1: Baseline (Smoke Test)**
```bash
# Verify system health
k6 run performance-tests/smoke-test.js
```

**Step 2: Load Test**
```bash
# Run realistic load test
k6 run --out json=load-test-results.json performance-tests/load-test.js
```

**Step 3: Cool Down**
```bash
# Wait 5 minutes for system to stabilize
sleep 300
```

**Step 4: Stress Test**
```bash
# Run stress test to find limits
k6 run --out json=stress-test-results.json performance-tests/stress-test.js
```

**Step 5: Analyze Results**

Review metrics:
- `http_req_duration` - Request latency (p95, p99)
- `http_req_failed` - Error rate
- `http_reqs` - Throughput
- Custom metrics: `requisitionLatency`, `matchesLatency`, `bulkUpsertLatency`

### Results Interpretation

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| P95 Latency | < 2s | 2-3s | > 3s |
| P99 Latency | < 5s | 5-8s | > 8s |
| Error Rate | < 1% | 1-5% | > 5% |
| Throughput | ≥ 100 req/s | 50-100 req/s | < 50 req/s |

## Task 6.3: Scalability Testing

### Step 1: Generate Test Data (5x Scale)

Generate 5x production data volume:

```bash
# Generate to SQL file
python scripts/generate_test_data.py --scale 5 --output test_data_5x.sql

# Review file size and record counts
wc -l test_data_5x.sql

# Load to database
psql -U user -d dbname -f test_data_5x.sql
```

**Generated Data (5x Scale):**
- Team Members: 2,500
- Allocations: ~5,000
- Requisitions: 5,000

**Or load directly:**
```bash
python scripts/generate_test_data.py \
  --scale 5 \
  --database postgresql://user:password@localhost:5432/dbname
```

### Step 2: Run Performance Tests on Scaled Data

```bash
# Smoke test with 5x data
k6 run performance-tests/smoke-test.js

# Load test with 5x data
k6 run performance-tests/load-test.js

# Compare results to baseline
```

### Step 3: Validate Performance Targets

Verify system still meets NFR targets with 5x data:
- ✅ P95 latency < 2 seconds
- ✅ P99 latency < 5 seconds
- ✅ Error rate < 1%

### Step 4: Cleanup Test Data

```bash
# Dry run (preview what will be deleted)
python scripts/cleanup_test_data.py \
  --database postgresql://user:password@localhost:5432/dbname \
  --metadata scale_test \
  --dry-run

# Execute cleanup
python scripts/cleanup_test_data.py \
  --database postgresql://user:password@localhost:5432/dbname \
  --metadata scale_test
```

## Task 6.4: Idempotent Retry Testing

### Test Idempotent Retry Behavior

Validates that retrying failed bulk operations doesn't create duplicates:

```bash
python tests/test_idempotent_retry.py \
  --base-url http://localhost:8000 \
  --auth-token "your-jwt-token"
```

**Test Scenarios:**

1. **Insert Idempotency** - Same record inserted multiple times
2. **Update Idempotency** - Same update applied multiple times  
3. **Partial Failure Retry** - Retry after some records succeeded
4. **Concurrent Upsert** - Multiple concurrent requests for same key
5. **Allocation Idempotency** - Nested allocation data handling

**Success Criteria:**
- ✅ No duplicate team_member_id created
- ✅ Retried updates don't create new records
- ✅ Concurrent requests handled safely
- ✅ Allocations don't duplicate on retry

### Manual Verification

1. **Check Database Counts:**
```sql
-- Count test records
SELECT COUNT(*) FROM team_members 
WHERE team_member_id LIKE 'TEST-IDEM-%';

-- Should match expected count (no duplicates)
```

2. **Check Audit Trail:**
```sql
-- Review operations for test records
SELECT * FROM audit_log 
WHERE entity_id LIKE 'TEST-IDEM-%'
ORDER BY timestamp DESC;
```

## Performance Monitoring During Tests

### Database Metrics

Monitor during load tests:

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Slow queries
SELECT pid, now() - query_start as duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;

-- Cache hit ratio
SELECT 
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_ratio
FROM pg_statio_user_tables;
```

### Application Metrics

Monitor via `/api/v1/metrics` endpoint:

```bash
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  http://localhost:8000/api/v1/metrics
```

Key metrics:
- `http_requests_total` - Request count
- `http_request_duration_seconds` - Latency histogram
- `active_requests` - Current load
- `db_connection_pool_size` - Database connections

## Troubleshooting

### High Latency (P95 > 2s)

**Possible Causes:**
- Database connection pool exhausted
- Slow queries (missing indexes)
- Network latency
- AI agent processing time

**Solutions:**
```bash
# Check database indexes
psql -U user -d dbname -c "\d+ team_members"

# Monitor connection pool
# Check app logs for "pool exhausted" messages

# Add indexes if needed
CREATE INDEX CONCURRENTLY idx_team_members_skills 
ON team_members USING GIN(primary_skills);
```

### High Error Rate (> 5%)

**Possible Causes:**
- Timeouts (30s default)
- Database deadlocks
- Memory exhaustion
- Invalid test data

**Solutions:**
```bash
# Check error logs
grep "ERROR" logs/app.log | tail -20

# Check database locks
SELECT * FROM pg_locks WHERE NOT granted;

# Monitor memory usage
free -h
docker stats  # if containerized
```

### Connection Errors

```bash
# Check if service is running
curl http://localhost:8000/health

# Check database connectivity
psql -U user -d dbname -c "SELECT 1"

# Check connection limits
psql -U user -d dbname -c "SHOW max_connections"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Phase 6 Performance Tests

on:
  push:
    branches: [main, phase-6-*]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  performance-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Install k6
        run: |
          sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run migrations
        run: |
          alembic upgrade head
      
      - name: Start application
        run: |
          uvicorn src.main:app --host 0.0.0.0 --port 8000 &
          sleep 10
      
      - name: Smoke Test
        run: |
          export BASE_URL=http://localhost:8000
          export AUTH_TOKEN="${{ secrets.TEST_JWT_TOKEN }}"
          k6 run performance-tests/smoke-test.js
      
      - name: Load Test
        run: |
          k6 run --out json=load-results.json performance-tests/load-test.js
      
      - name: Idempotent Retry Tests
        run: |
          python tests/test_idempotent_retry.py \
            --base-url http://localhost:8000 \
            --auth-token "${{ secrets.TEST_JWT_TOKEN }}"
      
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: load-results.json
```

## Success Criteria Summary

### NFR-1: Performance

- ✅ **NFR-1.1**: P95 latency < 2 seconds under 100 concurrent requests
- ✅ **NFR-1.2**: P99 latency < 5 seconds under peak load
- ✅ **NFR-1.3**: Throughput ≥ 100 requests/second

### NFR-2: Scalability

- ✅ Handles 5x production data volume (2,500 team members, 5,000 requisitions)
- ✅ Linear performance degradation up to 200 concurrent users
- ✅ Graceful degradation beyond capacity

### NFR-3: Reliability

- ✅ Idempotent retry behavior verified for bulk operations
- ✅ No duplicate data on retry
- ✅ Concurrent requests handled safely
- ✅ Error rate < 1% under normal load

## References

- [NFR-1: Performance](../specs/non-functional/nfr-performance.md)
- [NFR-2: Scalability](../specs/non-functional/nfr-scalability.md)
- [NFR-3: Reliability](../specs/non-functional/nfr-reliability-availability.md)
- [Idempotency Rules](../specs/data/idempotency-rules.md)
- [k6 Documentation](https://k6.io/docs/)

## Next Steps

After completing Phase 6:
1. Review and analyze all test results
2. Document any performance bottlenecks found
3. Update architecture if needed to meet targets
4. Prepare for production deployment (Phase 7)
