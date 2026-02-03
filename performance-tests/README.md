# Performance Testing Guide

This directory contains performance and load testing scripts for the IB Job Skill Mapping System using k6.

## Prerequisites

### Install k6

**macOS:**
```bash
brew install k6
```

**Windows:**
```powershell
choco install k6
# Or download from https://k6.io/docs/getting-started/installation/
```

**Linux:**
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### Generate Authentication Token

For testing, generate a valid JWT token or use the test token:

```python
# Generate test token (Python)
from jose import jwt
import time

payload = {
    "sub": "test-client",
    "client_id": "test-client",
    "iat": int(time.time()),
    "exp": int(time.time()) + 7200,  # 2 hours
}
token = jwt.encode(payload, "test-secret", algorithm="HS256")
print(token)
```

## Test Suites

### 1. Smoke Test
Quick validation that all endpoints are functional.

**Duration:** ~30 seconds  
**VUs:** 1  
**Purpose:** Verify basic functionality before running larger tests

```bash
k6 run performance-tests/smoke-test.js
```

**With custom settings:**
```bash
BASE_URL=https://staging.example.com \
AUTH_TOKEN=your-jwt-token \
k6 run performance-tests/smoke-test.js
```

### 2. Load Test
Simulates realistic traffic patterns with gradual ramp-up.

**Duration:** ~6 minutes  
**VUs:** 10 → 100 (gradual increase)  
**Purpose:** Measure performance under realistic load

```bash
k6 run performance-tests/load-test.js
```

**Custom VUs and duration:**
```bash
k6 run --vus 50 --duration 5m performance-tests/load-test.js
```

**With environment variables:**
```bash
BASE_URL=http://localhost:8000 \
AUTH_TOKEN=eyJhbGc... \
k6 run performance-tests/load-test.js
```

### 3. Stress Test
Pushes system to limits to identify breaking points.

**Duration:** ~30 minutes  
**VUs:** 100 → 400 (aggressive increase)  
**Purpose:** Find system limits and breaking points

```bash
k6 run performance-tests/stress-test.js
```

## Performance Targets

As defined in [specs/non-functional/nfr-performance.md](../specs/non-functional/nfr-performance.md):

| Metric | Target | Spec Reference |
|--------|--------|----------------|
| **P95 Latency** | < 2 seconds | NFR-1.1 |
| **P99 Latency** | < 5 seconds | NFR-1.2 |
| **Throughput** | ≥ 100 concurrent requests | NFR-1.3 |
| **Error Rate** | < 1% under normal load | NFR-3.1 |

## Interpreting Results

### Key Metrics

```
http_req_duration......: avg=150ms min=50ms med=120ms max=2s p(95)=450ms p(99)=800ms
http_req_failed........: 0.5% ✓ 5 ✗ 995
http_reqs..............: 1000 total (16.67/s)
vus....................: 50
```

**Good Indicators:**
- ✅ P95 < 2000ms
- ✅ P99 < 5000ms  
- ✅ Error rate < 1%
- ✅ No HTTP 5xx errors

**Warning Signs:**
- ⚠️ P95 approaching 2000ms
- ⚠️ Error rate 1-5%
- ⚠️ Increasing latency over time

**Critical Issues:**
- ❌ P95 > 2000ms or P99 > 5000ms
- ❌ Error rate > 5%
- ❌ HTTP 5xx errors
- ❌ Request timeouts

### Output Formats

**HTML Report:**
```bash
k6 run --out html=report.html performance-tests/load-test.js
```

**JSON Export:**
```bash
k6 run --out json=results.json performance-tests/load-test.js
```

**InfluxDB (for Grafana):**
```bash
k6 run --out influxdb=http://localhost:8086/k6 performance-tests/load-test.js
```

## Running Against Different Environments

### Local Development
```bash
BASE_URL=http://localhost:8000 k6 run performance-tests/smoke-test.js
```

### Staging
```bash
BASE_URL=https://staging-api.example.com \
AUTH_TOKEN=$(cat staging-token.txt) \
k6 run performance-tests/load-test.js
```

### Production (Use with Caution!)
```bash
# ⚠️ Only run smoke tests against production
# ⚠️ Coordinate with ops team first
BASE_URL=https://api.example.com \
AUTH_TOKEN=$(cat prod-token.txt) \
k6 run --vus 5 --duration 1m performance-tests/smoke-test.js
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM
  workflow_dispatch:

jobs:
  performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6
      
      - name: Run smoke test
        env:
          BASE_URL: ${{ secrets.STAGING_URL }}
          AUTH_TOKEN: ${{ secrets.STAGING_TOKEN }}
        run: k6 run performance-tests/smoke-test.js
      
      - name: Run load test
        env:
          BASE_URL: ${{ secrets.STAGING_URL }}
          AUTH_TOKEN: ${{ secrets.STAGING_TOKEN }}
        run: k6 run --vus 20 --duration 2m performance-tests/load-test.js
```

## Troubleshooting

### High Latency
1. Check database query performance
2. Review application logs for slow endpoints
3. Monitor resource utilization (CPU, memory, DB connections)
4. Consider database indexing

### High Error Rate
1. Check application logs for exceptions
2. Verify authentication tokens are valid
3. Ensure database connections are available
4. Review rate limiting configuration

### Connection Errors
1. Verify BASE_URL is accessible
2. Check network connectivity
3. Ensure firewall rules allow traffic
4. Verify SSL/TLS certificates (if HTTPS)

### Memory Issues
1. Reduce VUs or duration
2. Add think time between requests
3. Run tests on machine with more resources
4. Use distributed k6 execution

## Best Practices

1. **Start Small:** Run smoke tests before load tests
2. **Baseline First:** Establish performance baseline before changes
3. **Isolate Variables:** Test one change at a time
4. **Monitor Resources:** Watch CPU, memory, DB during tests
5. **Test Realistically:** Use realistic data and scenarios
6. **Off-Peak Testing:** Run stress tests during off-peak hours
7. **Document Results:** Keep record of performance over time
8. **Alert on Degradation:** Set up alerts for performance regression

## References

- [k6 Documentation](https://k6.io/docs/)
- [NFR-1: Performance Requirements](../specs/non-functional/nfr-performance.md)
- [NFR-2: Scalability Requirements](../specs/non-functional/nfr-scalability.md)
- [NFR-3: Reliability Requirements](../specs/non-functional/nfr-reliability-availability.md)
