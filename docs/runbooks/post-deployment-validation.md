# Post-Deployment Validation Guide

## Overview

This guide provides comprehensive validation steps to verify production deployment success.

**Timeframe:** Execute immediately after deployment and continue for 24 hours

---

## Immediate Validation (First Hour)

### Service Health

**1. Health Check Endpoint**
```bash
# Test health endpoint
curl https://api.infobeans.com/health
# Expected: {"status": "healthy", "timestamp": "...", "version": "v1.0.0"}

# From multiple locations
for location in us eu asia; do
  echo "Testing from $location:"
  curl https://api.infobeans.com/health -w "\nTime: %{time_total}s\n"
done
```

**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________  
**Time:** ___________

---

**2. Readiness Check**
```bash
# Test readiness endpoint
curl https://api.infobeans.com/ready
# Expected: {"status": "ready", "checks": {"database": "ok", "cache": "ok"}}
```

**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________  
**Time:** ___________

---

### Pod Status

**3. Verify Pod Deployment**
```bash
# Check all pods running
kubectl get pods -n production -l app=api-gateway

# Expected output:
# NAME                              READY   STATUS    RESTARTS   AGE
# api-gateway-blue-xxxxxxxxx-xxxxx  1/1     Running   0          5m
# api-gateway-blue-xxxxxxxxx-xxxxx  1/1     Running   0          5m
# api-gateway-blue-xxxxxxxxx-xxxxx  1/1     Running   0          5m

# Verify pod distribution across AZs
kubectl get pods -n production -l app=api-gateway -o wide | grep -E "NODE|api-gateway"
# Expected: Pods distributed across different nodes in different AZs
```

**Pod Count:** ___________  
**All Running:** ⬜ Yes ⬜ No  
**AZ Distribution:** ⬜ Good ⬜ Needs Review  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

**4. Check Pod Logs**
```bash
# Check logs for errors
kubectl logs -l app=api-gateway -n production --tail=100 | grep -i error
# Expected: No critical errors

# Check startup messages
kubectl logs -l app=api-gateway -n production --tail=50 | grep -E "started|ready|listening"
# Expected: "Application started successfully on port 8080"
```

**Errors Found:** ⬜ None ⬜ Minor ⬜ Critical  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

### Service Configuration

**5. Verify Service Endpoints**
```bash
# Check service
kubectl get svc api-gateway -n production

# Expected output:
# NAME          TYPE           CLUSTER-IP      EXTERNAL-IP     PORT(S)        AGE
# api-gateway   LoadBalancer   10.0.xxx.xxx    <alb-dns>       443:xxxxx/TCP  5m

# Verify endpoints
kubectl get endpoints api-gateway -n production
# Expected: 3 endpoints (one for each pod)

# Check service selector
kubectl get svc api-gateway -n production -o jsonpath='{.spec.selector}'
# Expected: {"app":"api-gateway","version":"blue"}
```

**Service Type:** ___________  
**Endpoints Count:** ___________  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

### Database Connectivity

**6. Test Database Connection**
```bash
# From within a pod
kubectl exec -it <pod-name> -n production -- \
  python -c "import os; import psycopg2; \
  conn = psycopg2.connect(os.environ['DATABASE_URL']); \
  print('Connected:', conn.status == 1); \
  conn.close()"
# Expected: Connected: True

# Check active connections
kubectl exec -it <pod-name> -n production -- \
  psql $DATABASE_URL -c "SELECT count(*) as active_connections \
  FROM pg_stat_activity WHERE state = 'active';"
# Expected: < 80 connections
```

**Connection:** ⬜ Success ⬜ Failure  
**Active Connections:** ___________  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

**7. Verify Database Schema**
```bash
# Check table count
kubectl exec -it <pod-name> -n production -- \
  psql $DATABASE_URL -c "SELECT count(*) FROM information_schema.tables \
  WHERE table_schema = 'public';"
# Expected: 15 tables

# Check recent data
kubectl exec -it <pod-name> -n production -- \
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM requisitions; \
  SELECT COUNT(*) FROM availabilities;"
# Expected: Counts as expected (0 if fresh deployment)
```

**Table Count:** ___________  
**Data Present:** ⬜ Yes ⬜ No  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

### Cache Connectivity

**8. Test Redis Connection**
```bash
# From within a pod
kubectl exec -it <pod-name> -n production -- \
  python -c "import os; import redis; \
  r = redis.from_url(os.environ['REDIS_URL']); \
  print('PING:', r.ping())"
# Expected: PING: True

# Check Redis info
kubectl exec -it <pod-name> -n production -- \
  redis-cli -h $REDIS_HOST -p $REDIS_PORT info server
# Expected: Redis server info displayed
```

**Connection:** ⬜ Success ⬜ Failure  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

### API Functional Tests

**9. Run Smoke Tests**
```bash
# Execute smoke test script
cd scripts
./smoke-test-production.sh

# Or with explicit credentials
API_BASE_URL=https://api.infobeans.com \
CLIENT_ID=$CLIENT_ID \
CLIENT_SECRET=$CLIENT_SECRET \
./smoke-test-production.sh
```

**Tests Run:** ___________  
**Tests Passed:** ___________  
**Tests Failed:** ___________  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

**10. Manual API Test - Authentication**
```bash
# Get access token
curl -X POST https://api.infobeans.com/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "'$CLIENT_ID'",
    "client_secret": "'$CLIENT_SECRET'"
  }'
# Expected: {"access_token": "...", "token_type": "Bearer", "expires_in": 3600}
```

**Token Obtained:** ⬜ Yes ⬜ No  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

**11. Manual API Test - Create Requisition**
```bash
# Create test requisition
curl -X POST https://api.infobeans.com/api/v1/requisitions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Post-Deployment Test",
    "description": "Testing production deployment",
    "skills_required": ["Python", "FastAPI"],
    "urgency_level": "low",
    "team_size": 1,
    "location": "Remote"
  }'
# Expected: {"requisition_id": "...", "status": "pending"}
```

**Requisition Created:** ⬜ Yes ⬜ No  
**Requisition ID:** ___________  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

**12. Manual API Test - Get Requisition**
```bash
# Retrieve requisition
curl https://api.infobeans.com/api/v1/requisitions/$REQUISITION_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# Expected: Full requisition details returned
```

**Requisition Retrieved:** ⬜ Yes ⬜ No  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

### Monitoring & Metrics

**13. CloudWatch Dashboard**
```bash
# Open CloudWatch dashboard
# URL: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=ib-job-skill-mapping-prod-dashboard

# Verify widgets:
# - API Request Rate: > 0 requests/second
# - Error Rate: < 0.5%
# - Latency (p95): < 2 seconds
# - Database Connections: < 80
# - CPU Utilization: < 70%
```

**Dashboard Accessible:** ⬜ Yes ⬜ No  
**All Widgets Loading:** ⬜ Yes ⬜ No  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

**14. Grafana Dashboard**
```bash
# Open Grafana dashboard
# URL: http://grafana.infobeans.com/d/system-overview

# Verify panels:
# - System Health: Green/Healthy
# - Request Rate: > 0 req/s
# - Error Rate: < 0.5%
# - P95 Latency: < 2s
# - All 14 panels displaying data
```

**Dashboard Accessible:** ⬜ Yes ⬜ No  
**All Panels Loading:** ⬜ Yes ⬜ No  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

**15. Prometheus Metrics**
```bash
# Check Prometheus targets
curl http://prometheus.infobeans.com/api/v1/targets | jq '.data.activeTargets[] | {job: .job, health: .health}'
# Expected: All targets "up"

# Query request rate
curl 'http://prometheus.infobeans.com/api/v1/query?query=rate(http_requests_total[5m])' | jq '.data.result'
# Expected: Data returned
```

**Targets Up:** _____ / _____  
**Metrics Flowing:** ⬜ Yes ⬜ No  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

**16. Check for Alarms**
```bash
# Check CloudWatch alarms
aws cloudwatch describe-alarms --state-value ALARM
# Expected: No alarms in ALARM state

# Check PagerDuty
# URL: https://infobeans.pagerduty.com
# Expected: No open incidents
```

**Alarms Firing:** ___________  
**PagerDuty Incidents:** ___________  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

### Security Validation

**17. SSL/TLS Certificate**
```bash
# Verify SSL certificate
echo | openssl s_client -connect api.infobeans.com:443 -servername api.infobeans.com 2>/dev/null | openssl x509 -noout -dates
# Expected: Valid dates (not expired)

# Check certificate details
curl -vI https://api.infobeans.com 2>&1 | grep "SSL certificate verify"
# Expected: SSL certificate verify ok
```

**Certificate Valid:** ⬜ Yes ⬜ No  
**Expiry Date:** ___________  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

**18. Security Headers**
```bash
# Check security headers
curl -I https://api.infobeans.com
# Expected headers:
# - Strict-Transport-Security: max-age=31536000
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: DENY
```

**Security Headers Present:** ⬜ Yes ⬜ No  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

### Performance Validation

**19. Response Time Test**
```bash
# Test response times (10 requests)
for i in {1..10}; do
  curl -w "Request $i: %{time_total}s\n" -o /dev/null -s https://api.infobeans.com/health
done

# Expected: All < 1 second
```

**Average Response Time:** ___________  
**All < 1s:** ⬜ Yes ⬜ No  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

**20. Load Test (Light)**
```bash
# Run light load test (optional, if k6 available)
k6 run performance-tests/smoke-test.js

# Or use Apache Bench
ab -n 100 -c 10 https://api.infobeans.com/health
# Expected: 100% success, average time < 1s
```

**Success Rate:** ___________  
**Average Time:** ___________  
**Status:** ⬜ Pass ⬜ Fail  
**Verified By:** ___________

---

## Extended Monitoring (24 Hours)

### Hour 1-4

**21. Continuous Monitoring Checklist**

**Every 30 Minutes:**
- [ ] Check CloudWatch dashboard - no alarms
- [ ] Review Grafana dashboard - metrics stable
- [ ] Check error logs: `kubectl logs -l app=api-gateway --tail=50 | grep ERROR`
- [ ] Verify pod restarts: `kubectl get pods -n production` (RESTARTS should be 0)

**Notes:**
___________________________________________
___________________________________________

---

### Hour 4-8

**22. Mid-Day Review**

- [ ] Error rate stable (< 0.5%)
- [ ] Latency within SLO (p95 < 2s)
- [ ] No pod crashes or restarts
- [ ] Database performance normal
- [ ] Cache hit rate acceptable (> 80%)
- [ ] No user-reported issues

**Issues Identified:**
___________________________________________
___________________________________________

**Actions Taken:**
___________________________________________
___________________________________________

---

### Hour 8-24

**23. End-of-Day Review**

**Metrics Summary (24 Hours):**

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Availability | 99.5% | ____% | ⬜ |
| Error Rate | < 0.5% | ____% | ⬜ |
| Latency (p95) | < 2s | ____s | ⬜ |
| Latency (p99) | < 5s | ____s | ⬜ |
| Throughput | Baseline | ____ req/s | ⬜ |
| Incidents | 0 | _____ | ⬜ |

**Status:** ⬜ Pass ⬜ Fail  
**Reviewed By:** ___________  
**Time:** ___________

---

## Stakeholder Communication

**24. Status Updates**

**Initial Update (1 hour post-deployment):**
```
Subject: Production Deployment - Initial Status

Team,

Production deployment completed successfully at [TIME].

Current Status:
✅ All systems operational
✅ Health checks passing
✅ Smoke tests successful
✅ Monitoring active

Metrics (first hour):
- Availability: 100%
- Error Rate: 0.0%
- Average Latency: XXXms

Continuing 24-hour monitoring.

DevOps Team
```

**Sent:** ⬜ Yes ⬜ No  
**Time:** ___________

---

**Mid-Day Update (8 hours post-deployment):**
```
Subject: Production Deployment - 8-Hour Update

Team,

Production system continues to operate normally.

Metrics (8 hours):
- Availability: XX.X%
- Error Rate: X.X%
- Average Latency: XXXms
- Total Requests: XXXXX

No issues reported.

DevOps Team
```

**Sent:** ⬜ Yes ⬜ No  
**Time:** ___________

---

**Final Update (24 hours post-deployment):**
```
Subject: Production Deployment - 24-Hour Success

Team,

Production deployment validation complete after 24 hours.

Summary:
✅ 24-hour availability: XX.X%
✅ Error rate: X.X% (within SLO)
✅ Performance: p95 latency XXXms (within SLO)
✅ Zero critical incidents
✅ XX,XXX requests processed successfully

Deployment officially closed. Normal operations resumed.

Thank you for your support.

DevOps Team
```

**Sent:** ⬜ Yes ⬜ No  
**Time:** ___________

---

## Final Sign-Off

**Deployment Validation Complete:** ⬜ Yes ⬜ No

**Overall Status:** ⬜ Success ⬜ Success with Issues ⬜ Failure

**Issues Summary:**
___________________________________________
___________________________________________
___________________________________________

**Actions Required:**
___________________________________________
___________________________________________
___________________________________________

---

**Sign-Off:**

| Role | Name | Signature | Date/Time |
|------|------|-----------|-----------|
| DevOps Lead | | | |
| Tech Lead | | | |
| On-Call Engineer | | | |

---

**Document Version:** 1.0  
**Last Updated:** February 8, 2026  
**Owner:** DevOps Team
