# Production Monitoring & Alerting Guide

## Overview

This document describes the monitoring and alerting infrastructure for the IB Job Skill Mapping System production environment.

**Monitoring Stack:**
- **CloudWatch**: AWS-native metrics, logs, and alarms
- **Prometheus**: Time-series metrics collection and querying
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and notification
- **X-Ray**: Distributed tracing (optional)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ API Pod  │  │ API Pod  │  │ API Pod  │             │
│  │ :8080    │  │ :8080    │  │ :8080    │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │ metrics     │ metrics     │ metrics            │
└───────┼─────────────┼─────────────┼─────────────────────┘
        │             │             │
        └─────────────┴─────────────┘
                      │
        ┌─────────────▼──────────────┐
        │    Prometheus Server       │
        │    (scrapes every 15s)     │
        │    Port: 9090              │
        └─────────┬──────────────────┘
                  │
        ┌─────────▼──────────────────┐
        │    AlertManager            │
        │    (evaluates rules)       │
        │    Port: 9093              │
        └─────────┬──────────────────┘
                  │
        ┌─────────▼──────────────────┐
        │    SNS Topics              │
        │    • Critical Alerts       │
        │    • Warning Alerts        │
        └─────────┬──────────────────┘
                  │
        ┌─────────▼──────────────────┐
        │    Email / PagerDuty       │
        │    (notify team)           │
        └────────────────────────────┘

        ┌────────────────────────────┐
        │    Grafana Dashboards      │
        │    (visualize metrics)     │
        │    Port: 3000              │
        └────────────────────────────┘
```

---

## Metrics Collection

### Application Metrics

**Instrumentation Location:** `src/app/middleware/metrics.py`

**Standard Metrics:**
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Database metrics
db_connection_pool_active = Gauge(
    'db_connection_pool_active',
    'Active database connections'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# Redis metrics
redis_cache_hits_total = Counter(
    'redis_cache_hits_total',
    'Total Redis cache hits'
)

redis_cache_misses_total = Counter(
    'redis_cache_misses_total',
    'Total Redis cache misses'
)

# LLM API metrics
llm_api_requests_total = Counter(
    'llm_api_requests_total',
    'Total LLM API requests',
    ['provider', 'status']
)

# Matching engine metrics
matching_requests_total = Counter(
    'matching_requests_total',
    'Total matching requests'
)

matching_timeouts_total = Counter(
    'matching_timeouts_total',
    'Total matching timeouts'
)

matching_duration_seconds = Histogram(
    'matching_duration_seconds',
    'Matching duration',
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
)

# LangGraph metrics
langgraph_execution_total = Counter(
    'langgraph_execution_total',
    'Total LangGraph executions',
    ['graph_name', 'status']
)
```

**Metrics Endpoint:**
- URL: `/metrics`
- Format: Prometheus text format
- Authentication: Internal only (ClusterIP service)

### Infrastructure Metrics

**Collected by Prometheus:**
- Node Exporter: CPU, memory, disk, network (port 9100)
- cAdvisor: Container metrics (integrated with kubelet)
- Postgres Exporter: Database metrics (port 9187)
- Redis Exporter: Cache metrics (port 9121)

**Collected by CloudWatch:**
- RDS metrics: CPU, connections, storage, replication lag
- ElastiCache metrics: CPU, memory, evictions, hit rate
- EKS metrics: Node utilization, pod counts
- ALB metrics: Request count, latency, error rates

---

## Service Level Objectives (SLOs)

### API Availability
- **Target**: 99.5% uptime
- **Error Budget**: 0.5% (4.38 hours/year)
- **Measurement**: Success rate of API requests (non-5xx)

### API Latency
- **p95**: < 2 seconds
- **p99**: < 5 seconds
- **Measurement**: HTTP request duration histogram

### Throughput
- **Target**: > 100 requests/second
- **Measurement**: Rate of HTTP requests

### Database Performance
- **Query Latency p95**: < 500ms
- **Connection Pool**: < 80% utilization
- **Measurement**: Database query duration

### Cache Performance
- **Hit Rate**: > 80%
- **Measurement**: Redis cache hits / (hits + misses)

### LLM Integration
- **Success Rate**: > 95%
- **Measurement**: Successful LLM API calls / total calls

### Matching Engine
- **Timeout Rate**: < 1%
- **Measurement**: Timeouts / total matching requests

---

## Alert Rules

### Critical Alerts (PagerDuty + Email)

**APIAvailabilityBelowSLO**
- **Trigger**: API availability < 99.5% for 5 minutes
- **Action**: Immediate response required
- **Runbook**: Check pod health, database connectivity, recent deployments

**APILatencyP99AboveSLO**
- **Trigger**: p99 latency > 5 seconds for 5 minutes
- **Action**: Investigate slow queries, resource constraints
- **Runbook**: Check database slow queries, Redis cache, LLM API latency

**ErrorBudgetFastBurn**
- **Trigger**: Error rate > 1% (2x SLO burn rate)
- **Action**: Immediate investigation, consider rollback
- **Runbook**: Check recent changes, error logs, external dependencies

**DatabaseConnectionsHigh**
- **Trigger**: Active connections > 80
- **Action**: Identify connection leaks, scale if needed
- **Runbook**: Check connection pool settings, query pg_stat_activity

**PodCrashLooping**
- **Trigger**: Pod in CrashLoopBackOff state
- **Action**: Check pod logs, describe pod events
- **Runbook**: Investigate startup failures, resource limits

**NodeDiskSpaceLow**
- **Trigger**: Disk space < 15%
- **Action**: Clean up logs, resize volume
- **Runbook**: Check log rotation, identify large files

### Warning Alerts (Email Only)

**APILatencyAboveSLO**
- **Trigger**: p95 latency > 2 seconds for 5 minutes
- **Action**: Monitor, investigate if persists
- **Runbook**: Check metrics dashboard, slow query logs

**APIThroughputBelowSLO**
- **Trigger**: Throughput < 100 req/s for 10 minutes
- **Action**: Verify expected traffic patterns
- **Runbook**: Check upstream services, DNS, load balancer

**ErrorBudgetSlowBurn**
- **Trigger**: Error rate > 0.833% sustained over 6 hours
- **Action**: Investigate root cause, plan remediation
- **Runbook**: Analyze error patterns, check external dependencies

**DatabaseQueryLatencyAboveSLO**
- **Trigger**: p95 query latency > 500ms for 5 minutes
- **Action**: Identify slow queries, add indexes if needed
- **Runbook**: Check pg_stat_statements, EXPLAIN ANALYZE slow queries

**RedisCacheHitRateBelowSLO**
- **Trigger**: Cache hit rate < 80% for 10 minutes
- **Action**: Review cache key patterns, TTL settings
- **Runbook**: Check cache size, eviction policy, key expiration

**LLMAPISuccessRateBelowSLO**
- **Trigger**: LLM success rate < 95% for 5 minutes
- **Action**: Check LLM API status, rate limits
- **Runbook**: Verify API keys, check provider status page

**MatchingTimeoutRateAboveSLO**
- **Trigger**: Timeout rate > 1% for 5 minutes
- **Action**: Investigate matching complexity, resource constraints
- **Runbook**: Check LangGraph execution time, LLM latency

---

## Dashboards

### System Overview Dashboard

**URL**: `http://grafana.infobeans.com/d/system-overview`

**Panels:**
1. **System Health Status** (Stat)
   - Up/Down status for all services
   - Color-coded: Green = UP, Red = DOWN

2. **Request Rate** (Stat)
   - Current requests per second
   - 5-minute average

3. **Error Rate** (Stat)
   - Current error percentage
   - Color-coded: Green < 0.5%, Yellow < 1%, Red >= 1%

4. **P95 Latency** (Stat)
   - Current p95 latency
   - Color-coded: Green < 2s, Yellow < 5s, Red >= 5s

5. **Request Rate by Endpoint** (Graph)
   - Time series of requests by endpoint and method
   - Stacked area chart

6. **Response Time Percentiles** (Graph)
   - p50, p95, p99 latency over time
   - Line chart

7. **Database Connection Pool** (Graph)
   - Active, idle, and max connections
   - Line chart

8. **Redis Cache Performance** (Graph)
   - Cache hits and misses over time
   - Stacked area chart

9. **CPU Usage by Container** (Graph)
   - CPU percentage for each pod
   - Line chart

10. **Memory Usage by Container** (Graph)
    - Memory in MB for each pod
    - Line chart

11. **LLM API Call Rate** (Graph)
    - Requests per second by provider
    - Line chart

12. **LLM API Error Rate** (Graph)
    - Error percentage by provider
    - Line chart

13. **Matching Engine Performance** (Graph)
    - Matching requests and timeouts
    - Line chart

14. **Matching Duration Distribution** (Heatmap)
    - Distribution of matching durations
    - Heatmap visualization

### Database Dashboard

**URL**: `http://grafana.infobeans.com/d/database`

**Panels:**
- Connection count
- Query latency (p50, p95, p99)
- Slow queries (> 1 second)
- Lock wait time
- Replication lag
- Cache hit ratio
- Transaction rate

### Redis Dashboard

**URL**: `http://grafana.infobeans.com/d/redis`

**Panels:**
- Operations per second
- Hit rate percentage
- Evictions
- Memory usage
- Connection count
- Keyspace analysis

### LangGraph Dashboard

**URL**: `http://grafana.infobeans.com/d/langgraph`

**Panels:**
- Graph execution rate
- Execution duration by graph
- Failure rate by graph
- Agent invocation count
- Checkpoint save/load time
- Token usage by LLM provider

---

## Log Aggregation

### CloudWatch Log Groups

**Application Logs:**
- Path: `/aws/ib-job-skill-mapping/prod/application`
- Retention: 30 days
- Format: JSON with structured fields

**API Gateway Logs:**
- Path: `/aws/ib-job-skill-mapping/prod/api-gateway`
- Retention: 30 days
- Fields: timestamp, method, path, status, duration, user_id

**AI Agent Logs:**
- Path: `/aws/ib-job-skill-mapping/prod/ai-agents`
- Retention: 30 days
- Fields: timestamp, graph_name, agent_name, execution_id, status

**Database Logs:**
- Path: `/aws/rds/instance/ib-job-skill-mapping-prod-db/postgresql`
- Retention: 30 days
- Includes: Slow queries, errors, connections

### Log Queries

**Find errors in last hour:**
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

**Slow API requests (> 2 seconds):**
```
fields @timestamp, method, path, duration
| filter duration > 2000
| sort duration desc
| limit 50
```

**Authentication failures:**
```
fields @timestamp, user_id, ip_address, @message
| filter status = 401
| stats count() by user_id
| sort count desc
```

**LLM API errors:**
```
fields @timestamp, provider, error_message
| filter component = "LLMIntegration" and level = "ERROR"
| stats count() by provider, error_message
```

---

## Alert Configuration

### SNS Topics

**Critical Alerts:**
- Topic: `ib-job-skill-mapping-prod-critical-alerts`
- Subscribers:
  - devops@infobeans.com
  - on-call@infobeans.com
  - PagerDuty integration

**Warning Alerts:**
- Topic: `ib-job-skill-mapping-prod-warning-alerts`
- Subscribers:
  - devops@infobeans.com
  - tech-leads@infobeans.com

### Alert Workflow

1. **Alert Triggered**
   - Prometheus evaluates rule every 30 seconds
   - Condition met for specified duration (5m, 10m, etc.)
   - Alert state: PENDING → FIRING

2. **Notification Sent**
   - AlertManager routes alert to SNS topic
   - SNS sends email to subscribers
   - PagerDuty creates incident (critical only)

3. **Acknowledgment**
   - On-call engineer acknowledges in PagerDuty
   - Investigation begins
   - Updates posted in Slack #incidents

4. **Resolution**
   - Root cause identified and fixed
   - Alert state: FIRING → RESOLVED
   - Resolution notification sent
   - Post-mortem scheduled (if critical)

### Alert Grouping

Alerts are grouped by:
- **Severity**: critical, warning, info
- **Component**: api, database, redis, llm, matching
- **Environment**: production (all prod alerts)

**Grouping Window**: 5 minutes
- Multiple similar alerts grouped into one notification
- Reduces alert fatigue

**Repeat Interval**: 4 hours
- Re-send alert if still firing after 4 hours
- Ensures alerts aren't forgotten

---

## Runbooks

### API Availability Below SLO

**Symptoms:**
- High 5xx error rate
- Pods not responding to requests
- Health checks failing

**Investigation Steps:**
1. Check pod status: `kubectl get pods -n production`
2. View recent logs: `kubectl logs -l app=api-gateway --tail=100`
3. Check recent deployments: `kubectl rollout history deployment/api-gateway-blue`
4. Verify database connectivity: Check RDS status in AWS Console
5. Check Redis connectivity: Verify ElastiCache cluster status

**Resolution:**
- If pods crashing: Check OOM, resource limits
- If database issue: Scale RDS, check slow queries
- If recent deployment: Rollback using blue-green procedure
- If external dependency: Enable circuit breaker, degrade gracefully

### Database Query Latency High

**Symptoms:**
- API latency increased
- Database CPU high
- Connection pool exhausted

**Investigation Steps:**
1. Check active queries: 
   ```sql
   SELECT pid, now() - query_start AS duration, query, state
   FROM pg_stat_activity
   WHERE state = 'active'
   ORDER BY duration DESC;
   ```

2. Check slow queries (last hour):
   ```sql
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   WHERE mean_time > 1000
   ORDER BY total_time DESC
   LIMIT 10;
   ```

3. Check table bloat:
   ```sql
   SELECT schemaname, tablename, 
          pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
   LIMIT 10;
   ```

**Resolution:**
- Add missing indexes
- Optimize slow queries
- Run VACUUM ANALYZE if bloat detected
- Scale RDS instance if sustained high load
- Add read replica for read-heavy queries

### Redis Cache Hit Rate Low

**Symptoms:**
- Increased database load
- Higher API latency
- Cache misses spiking

**Investigation Steps:**
1. Check cache stats:
   ```bash
   redis-cli --cluster-mode INFO stats
   ```

2. Check keyspace:
   ```bash
   redis-cli --cluster-mode INFO keyspace
   ```

3. Check evictions:
   ```bash
   redis-cli --cluster-mode INFO stats | grep evicted_keys
   ```

**Resolution:**
- Increase Redis memory if evictions high
- Review TTL settings (may be too short)
- Check for cache stampede (many misses for same key)
- Implement cache warming for common queries
- Consider LRU policy adjustment

---

## Cost Optimization

### CloudWatch Costs

**Log Ingestion:** $0.50 per GB
- Expected: ~100 GB/month = $50/month
- Optimization: Reduce retention, filter verbose logs

**Metrics:** $0.30 per metric/month
- Expected: ~200 custom metrics = $60/month
- Optimization: Use metric math, aggregate where possible

**Alarms:** $0.10 per alarm/month
- Expected: 30 alarms = $3/month

**Total CloudWatch:** ~$113/month

### Prometheus/Grafana

**EKS Nodes:** Included in cluster cost
**Storage:** ~10 GB for 15-day retention
**Cost:** Minimal (part of EKS overhead)

**Total Monitoring Cost:** ~$115/month

---

## Maintenance

### Weekly Tasks
- [ ] Review alert noise (false positives)
- [ ] Check log retention and volume
- [ ] Verify backup configurations
- [ ] Review dashboard usage

### Monthly Tasks
- [ ] Analyze SLO compliance
- [ ] Review and update runbooks
- [ ] Optimize alert thresholds
- [ ] Capacity planning review

### Quarterly Tasks
- [ ] Review monitoring costs
- [ ] Update SLO targets
- [ ] Team training on new features
- [ ] Audit access controls

---

## References

- [CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [SLO/SLA Guide](https://sre.google/sre-book/service-level-objectives/)
