# Deployment Runbook: Production

## Overview

This runbook provides step-by-step instructions for deploying the IB Job Skill Mapping System to production using blue-green deployment strategy.

**Target Audience:** DevOps Engineers, Tech Leads, On-Call Engineers

**Estimated Duration:** 30-45 minutes (excluding approval wait time)

**Prerequisites:**
- AWS credentials configured
- kubectl configured for EKS cluster
- GitHub access token
- Production secrets deployed to AWS Secrets Manager
- Team notified and available

---

## Pre-Deployment Checklist

### Code Readiness
- [ ] All code reviews approved
- [ ] CI/CD pipeline passing (all tests green)
- [ ] Staging deployment successful
- [ ] No known critical bugs
- [ ] Feature flags configured (if applicable)

### Database Readiness
- [ ] Migration scripts reviewed
- [ ] Migrations tested on staging
- [ ] Backward compatibility verified
- [ ] Rollback plan documented

### Team Readiness
- [ ] Tech Lead available
- [ ] DevOps Engineer available
- [ ] Product Manager notified
- [ ] On-call engineer identified
- [ ] Communication channels ready (Slack, etc.)

### Infrastructure Readiness
- [ ] AWS resources healthy (RDS, EKS, Redis, ALB)
- [ ] No ongoing AWS service issues
- [ ] Backup completed within last 24 hours
- [ ] Monitoring dashboards accessible

---

## Deployment Procedure

### Step 1: Initiate Deployment (2 minutes)

1. **Navigate to GitHub Actions**
   ```
   https://github.com/YOUR_ORG/ib-job-skill-mapping-system/actions
   ```

2. **Select Production Deployment Workflow**
   - Workflow: "Production Deployment Pipeline"
   - Click "Run workflow"

3. **Configure Deployment Parameters**
   ```
   Deployment Type: blue-green
   Environment: production
   Skip Tests: false (only true for emergencies)
   ```

4. **Start Workflow**
   - Click "Run workflow"
   - Note the run ID for reference

5. **Verify Workflow Started**
   - Check that validation job started
   - Monitor logs in real-time

**Expected Output:**
```
✓ Validation job started
✓ Version generated: abc1234-20260208-143022
```

---

### Step 2: Monitor Pre-Deployment Phase (5-10 minutes)

**Jobs Running:**
- Validate
- Test (if not skipped)
- Build

#### 2.1 Validate Job

Watch for:
- Version generation
- Breaking change detection
- Manifest validation

**Expected Duration:** 2-3 minutes

**Red Flags:**
- Breaking changes detected without migration
- Invalid Kubernetes manifests
- Missing required files

#### 2.2 Test Job

Monitor test execution:
```bash
# View test logs in GitHub Actions UI
# Look for test summary:
- Smoke tests: X passed
- Unit tests: X passed, coverage XX%
- Integration tests: X passed
```

**Expected Duration:** 5-10 minutes

**Red Flags:**
- Any test failures
- Coverage drop > 5%
- New flaky tests

#### 2.3 Build Job

Watch Docker build:
- Image build successful
- Push to ECR successful
- Vulnerability scan results

**Expected Duration:** 3-5 minutes

**Red Flags:**
- Build failures
- Critical vulnerabilities in image
- ECR push failures

**Action Items:**
- If any job fails, investigate immediately
- Fix issues and restart deployment
- Do not proceed to migration if builds fail

---

### Step 3: Database Migration (5-30 minutes)

#### 3.1 Pre-Migration Safety Check

Before migration starts, verify database health:

```bash
# Check database connections
aws rds describe-db-instances \
  --db-instance-identifier ib-job-skill-mapping-prod-db \
  --query 'DBInstances[0].DBInstanceStatus'

# Expected: "available"

# Check active connections
kubectl run psql-check --rm -it --restart=Never \
  --image=postgres:15 \
  --env="PGPASSWORD=$DB_PASSWORD" \
  -- psql -h $DB_HOST -U postgres -d ib_job_skill_mapping \
  -c "SELECT count(*) FROM pg_stat_activity WHERE state='active';"

# Expected: < 50 connections
```

#### 3.2 Monitor Migration Execution

Watch migration job logs:

```bash
# Get migration pod name
kubectl get pods -n production | grep migration

# Tail logs
kubectl logs -f migration-{run-id} -n production
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456
INFO  [alembic.runtime.migration] Adding column 'new_field' to 'requisitions'
INFO  [alembic.runtime.migration] Creating index 'idx_requisitions_new_field' CONCURRENTLY
INFO  [alembic.runtime.migration] Migration complete
```

**Expected Duration:** 5-30 minutes (depends on schema changes)

#### 3.3 Verify Migration Success

```bash
# Check migration completion
kubectl wait --for=condition=complete \
  --timeout=600s \
  pod/migration-{run-id} \
  -n production

# Verify schema changes (example)
kubectl exec -it $(kubectl get pod -l app=api-gateway-green -n production -o jsonpath='{.items[0].metadata.name}') \
  -n production \
  -- python -c "
from app.db import engine
from sqlalchemy import inspect
inspector = inspect(engine)
columns = inspector.get_columns('requisitions')
print([c['name'] for c in columns])
"
```

**Red Flags:**
- Migration timeout (> 30 minutes)
- Lock timeout errors
- Constraint violation errors
- Out of memory errors

**Rollback Decision Point:**
If migration fails:
1. Do NOT proceed to deployment
2. Investigate migration failure
3. Fix migration script
4. Test on staging
5. Restart deployment

---

### Step 4: Blue Environment Deployment (5-10 minutes)

#### 4.1 Monitor Blue Deployment

Watch deployment progress:

```bash
# Watch deployment status
kubectl get deployment api-gateway-blue -n production -w

# Expected progression:
# READY: 0/3  → 1/3 → 2/3 → 3/3
```

#### 4.2 Check Pod Health

```bash
# Get pod status
kubectl get pods -l app=api-gateway,version=blue -n production

# Expected output:
# NAME                                 READY   STATUS    RESTARTS   AGE
# api-gateway-blue-xxxxxxxxxx-xxxxx    1/1     Running   0          2m
# api-gateway-blue-xxxxxxxxxx-xxxxx    1/1     Running   0          2m
# api-gateway-blue-xxxxxxxxxx-xxxxx    1/1     Running   0          2m

# Check logs for errors
kubectl logs -l app=api-gateway,version=blue -n production --tail=50
```

#### 4.3 Internal Health Check

Test blue environment directly (before traffic switch):

```bash
# Port forward to blue service
kubectl port-forward svc/api-gateway-blue 8080:80 -n production &

# Wait for port forward to establish
sleep 5

# Health check
curl -f http://localhost:8080/health
# Expected: {"status": "healthy", "version": "abc1234-20260208-143022"}

# API health check
curl -f http://localhost:8080/api/v1/health
# Expected: {"status": "ok", "database": "connected", "redis": "connected"}

# Smoke test critical endpoint
curl -X POST http://localhost:8080/api/v1/requisitions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d @tests/fixtures/sample_requisition.json

# Expected: 200 OK with requisition ID

# Kill port forward
kill %1
```

**Expected Duration:** 5-10 minutes

**Red Flags:**
- Pods stuck in `CrashLoopBackOff`
- Health checks failing
- Database connection errors
- Secrets Manager access errors
- High error rate in logs

**Troubleshooting:**

If pods not starting:
```bash
# Describe pod for events
kubectl describe pod -l app=api-gateway,version=blue -n production

# Common issues:
# - Image pull error → Check ECR permissions
# - Secrets access denied → Check IAM role annotations
# - Database connection failure → Check security groups
# - OOMKilled → Increase memory limits
```

---

### Step 5: Approval Gate (0-24 hours)

#### 5.1 Review Deployment Readiness

Before approving traffic switch, verify:

**Blue Environment Health:**
```bash
# All pods running and ready
kubectl get pods -l app=api-gateway,version=blue -n production

# Check HPA status
kubectl get hpa api-gateway-blue -n production

# Verify secrets access working
kubectl logs -l app=api-gateway,version=blue -n production | grep -i "secret"
# Should see successful secret retrieval logs
```

**Metrics Review:**
```bash
# Check blue environment metrics (5 minute window)
aws cloudwatch get-metric-statistics \
  --namespace "IB-JobSkillMapping-Prod" \
  --metric-name "HealthCheckStatus" \
  --dimensions Name=Environment,Value=blue \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average

# Expected: Average = 1.0 (100% healthy)
```

**Log Review:**
```bash
# Check for errors in last 10 minutes
kubectl logs -l app=api-gateway,version=blue -n production --since=10m | grep -i error

# Expected: No critical errors
```

#### 5.2 Approve Deployment

1. **Navigate to Approval Screen**
   ```
   https://github.com/YOUR_ORG/ib-job-skill-mapping-system/actions/runs/{run-id}
   ```

2. **Click "Review deployments"**

3. **Select Environment**
   - Environment: `production-approval`

4. **Review Checklist:**
   - [ ] All blue pods running (3/3 ready)
   - [ ] Health checks passing for 5+ minutes
   - [ ] No errors in logs
   - [ ] Internal smoke tests passed
   - [ ] Team available for monitoring
   - [ ] Rollback plan confirmed

5. **Approve**
   - Add comment: "Approved by [Your Name] - All checks passed"
   - Click "Approve and deploy"

**Rejection Criteria:**
- Any pod not ready
- Health check failures
- Errors in logs
- Metrics anomalies
- Team unavailable

---

### Step 6: Traffic Switch (1-2 minutes)

#### 6.1 Monitor Traffic Switch

Watch service update:

```bash
# Watch service selector change
kubectl get svc api-gateway -n production -o yaml -w

# You'll see selector change from:
#   selector:
#     app: api-gateway
#     version: green
# To:
#   selector:
#     app: api-gateway
#     version: blue
```

#### 6.2 Verify Traffic Routing

```bash
# Check service endpoints
kubectl get endpoints api-gateway -n production

# Endpoints should now point to blue pods
# Compare IPs with:
kubectl get pods -l app=api-gateway,version=blue -n production -o wide
```

#### 6.3 Immediate Monitoring (5 minutes)

Critical period - watch closely:

```bash
# Monitor logs from blue pods receiving traffic
kubectl logs -f -l app=api-gateway,version=blue -n production

# In another terminal, watch error rate
watch -n 5 'kubectl logs --since=1m -l app=api-gateway,version=blue -n production | grep -c ERROR'

# Expected: 0 or very low error count
```

**Monitor CloudWatch:**
```bash
# Real-time error rate
aws cloudwatch get-metric-statistics \
  --namespace "IB-JobSkillMapping-Prod" \
  --metric-name "ErrorCount" \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum

# Expected: Low error count (< 5 per minute)
```

**Red Flags:**
- Sudden spike in errors (> 10% increase)
- Health checks failing
- Latency increase > 50%
- Database connection errors
- 5XX responses increasing

**IMMEDIATE ROLLBACK IF:**
- Error rate > 5%
- P95 latency > 10 seconds
- Health checks < 50% passing
- Database errors spiking

---

### Step 7: Production Smoke Tests (5-10 minutes)

#### 7.1 Automated Smoke Tests

GitHub Actions will run automated smoke tests:

```bash
# Monitor smoke test job
# Watch for:
- Health check: PASSED
- Authentication: PASSED
- Create requisition: PASSED
- Match requisition: PASSED
- Skill availability: PASSED
```

#### 7.2 Manual Verification

Perform manual checks on critical flows:

```bash
# 1. Health check
curl https://api.infobeans.com/health
# Expected: {"status": "healthy"}

# 2. Authentication
curl -X POST https://api.infobeans.com/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"grant_type": "client_credentials"}'
# Expected: 200 OK with access token

# 3. Create requisition (with token from above)
curl -X POST https://api.infobeans.com/api/v1/requisitions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "requisition_id": "TEST-'$(date +%s)'",
    "title": "Senior Python Developer",
    "description": "5+ years Python experience",
    "required_skills": ["Python", "FastAPI", "PostgreSQL"]
  }'
# Expected: 202 Accepted with correlation_id

# 4. Check requisition status
curl https://api.infobeans.com/api/v1/requisitions/TEST-{timestamp}/matches \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with matches
```

#### 7.3 Metrics Validation

Verify production metrics are within acceptable ranges:

```bash
# Error rate (last 10 minutes)
aws cloudwatch get-metric-statistics \
  --namespace "IB-JobSkillMapping-Prod" \
  --metric-name "ErrorRate" \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Expected: < 0.5%

# Latency (p95)
aws cloudwatch get-metric-statistics \
  --namespace "IB-JobSkillMapping-Prod" \
  --metric-name "RequestDuration" \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --extended-statistics p95

# Expected: < 2000ms (2 seconds)

# Throughput
aws cloudwatch get-metric-statistics \
  --namespace "IB-JobSkillMapping-Prod" \
  --metric-name "RequestCount" \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Expected: > 500 requests (depends on traffic)
```

---

### Step 8: Extended Monitoring (30-60 minutes)

#### 8.1 Continuous Monitoring

Monitor for at least 30 minutes after traffic switch:

**Dashboard Checklist:**
- [ ] Error rate stable (< 0.5%)
- [ ] Latency within SLA (p95 < 2s)
- [ ] Throughput normal
- [ ] CPU usage stable (< 70%)
- [ ] Memory usage stable (< 80%)
- [ ] Database connections normal (< 50)
- [ ] Redis hit rate > 80%
- [ ] No pod restarts

**Log Monitoring:**
```bash
# Watch for errors
kubectl logs -f -l app=api-gateway,version=blue -n production | grep -i error

# Expected: No critical errors
```

**Database Monitoring:**
```bash
# Check slow queries
aws rds describe-events \
  --source-identifier ib-job-skill-mapping-prod-db \
  --duration 60 \
  --source-type db-instance

# Expected: No performance issues
```

#### 8.2 User Feedback

Monitor support channels:
- Check Slack for user reports
- Review support tickets
- Monitor APM alerts

---

### Step 9: Cleanup (2-5 minutes)

#### 9.1 Scale Down Green Environment

After 1 hour of stable blue operation:

```bash
# Scale green to 0
kubectl scale deployment api-gateway-green --replicas=0 -n production

# Verify
kubectl get deployment api-gateway-green -n production
# Expected: READY 0/0
```

#### 9.2 Relabel Environments

Prepare for next deployment:

```bash
# Label blue as new green (for next deployment)
kubectl label deployment api-gateway-blue environment=green --overwrite -n production

# Label old green as blue
kubectl label deployment api-gateway-green environment=blue --overwrite -n production
```

#### 9.3 Update Documentation

- [ ] Update deployment log with version number
- [ ] Document any issues encountered
- [ ] Update runbook if procedures changed
- [ ] Share deployment summary with team

---

## Rollback Procedure

### Immediate Rollback (< 5 minutes)

If critical issues detected during or after traffic switch:

```bash
# 1. Switch traffic back to green
kubectl patch service api-gateway \
  -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

echo "✓ Traffic switched to green"

# 2. Verify green is serving traffic
kubectl get endpoints api-gateway -n production

# 3. Test production endpoint
curl https://api.infobeans.com/health
# Expected: {"status": "healthy", "version": "previous-version"}

# 4. Scale up green if needed
kubectl scale deployment api-gateway-green --replicas=3 -n production
kubectl rollout status deployment/api-gateway-green -n production

# 5. Monitor green environment
kubectl logs -f -l app=api-gateway,version=green -n production
```

### Delayed Rollback (after cleanup)

If green was already scaled down:

```bash
# 1. Scale up green
kubectl scale deployment api-gateway-green --replicas=3 -n production

# 2. Wait for pods
kubectl wait --for=condition=ready \
  --timeout=300s \
  pod -l app=api-gateway,version=green \
  -n production

# 3. Switch traffic
kubectl patch service api-gateway \
  -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# 4. Scale down blue
kubectl scale deployment api-gateway-blue --replicas=0 -n production
```

### Database Rollback

**WARNING: Only use if absolutely necessary**

```bash
# Get previous migration version
kubectl run alembic-current --rm -it --restart=Never \
  --image=ECR_IMAGE:PREVIOUS_VERSION \
  --command -- alembic current

# Rollback one version
kubectl run migration-rollback --rm -it --restart=Never \
  --image=ECR_IMAGE:PREVIOUS_VERSION \
  --env="DATABASE_URL=$DB_URL" \
  --command -- alembic downgrade -1

# WARNING: May cause data loss
# Only use if migration broke production
```

---

## Post-Deployment

### Immediate (Day 0)

- [ ] Monitor metrics for 4 hours
- [ ] Review logs for any warnings
- [ ] Verify all integrations working
- [ ] Confirm scheduled jobs running
- [ ] Update team on deployment success

### Short-term (Day 1-7)

- [ ] Monitor error rates daily
- [ ] Check performance metrics
- [ ] Review user feedback
- [ ] Verify database performance
- [ ] Check cost metrics

### Long-term (Week 2+)

- [ ] Review deployment retrospective
- [ ] Update runbook based on lessons learned
- [ ] Optimize resource usage if needed
- [ ] Plan next deployment

---

## Emergency Contacts

**On-Call Rotation:**
- Primary: [On-Call Engineer]
- Secondary: [Backup Engineer]
- Escalation: [Tech Lead]

**Communication Channels:**
- Slack: #prod-deployments
- PagerDuty: IB Job Skill Mapping - Production
- Email: devops@infobeans.com

**AWS Support:**
- Support Plan: Business
- Case Priority: High (production down)

---

## Appendix

### Useful Commands

```bash
# Get current production version
kubectl get deployment api-gateway-green -n production \
  -o jsonpath='{.spec.template.spec.containers[0].image}'

# Check all pod statuses
kubectl get pods -n production -l app=api-gateway

# Get recent events
kubectl get events -n production --sort-by='.lastTimestamp' | tail -20

# Check HPA status
kubectl get hpa -n production

# View pod resource usage
kubectl top pods -n production -l app=api-gateway

# Execute command in pod
kubectl exec -it POD_NAME -n production -- bash
```

### Deployment History

| Date | Version | Deployed By | Duration | Issues |
|------|---------|-------------|----------|--------|
| 2026-02-08 | v1.0.0 | Initial | - | - |

---

**Document Version:** 1.0  
**Last Updated:** February 8, 2026  
**Next Review:** March 8, 2026
