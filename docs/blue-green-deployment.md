# Blue-Green Deployment Strategy

## Overview

Blue-green deployment is a release strategy that reduces downtime and risk by running two identical production environments (blue and green). At any time, only one environment serves live production traffic.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer                          │
│                    (Kubernetes Service)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Traffic routing
                       │ (selector: version=green)
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼─────────┐          ┌────────▼────────┐
│ Green Deployment│          │ Blue Deployment │
│  (Production)   │          │   (Staging)     │
│                 │          │                 │
│ • 3 replicas    │          │ • 3 replicas    │
│ • Version: v1.2 │          │ • Version: v1.3 │
│ • Active        │          │ • Testing       │
└─────────────────┘          └─────────────────┘
        │                             │
        │                             │
        └──────────────┬──────────────┘
                       │
                  Shared Resources
                  (Database, Redis)
```

## Deployment Process

### Phase 1: Pre-Deployment (5-10 minutes)

1. **Validation**
   - Run full test suite (smoke, unit, integration)
   - Validate Kubernetes manifests
   - Check for breaking changes
   - Generate deployment version

2. **Build**
   - Build Docker image with new version
   - Push to Amazon ECR
   - Scan for vulnerabilities
   - Tag with version and `latest`

### Phase 2: Database Migration (5-30 minutes)

**Zero-Downtime Migration Strategy:**

1. **Backward-Compatible Migrations**
   - Add new columns with defaults
   - Create new tables/indexes
   - Add new constraints (non-blocking)
   - Deploy migrations before code

2. **Migration Execution**
   ```bash
   # Run migration job in Kubernetes
   kubectl run migration-{run-id} \
     --image=ECR_IMAGE:VERSION \
     --restart=Never \
     --command -- alembic upgrade head
   
   # Wait for completion
   kubectl wait --for=condition=complete job/migration-{run-id}
   ```

3. **Verification**
   - Check migration logs
   - Verify schema changes
   - Validate data integrity
   - Confirm green environment still functions

### Phase 3: Deploy Blue Environment (5-10 minutes)

1. **Update Blue Deployment**
   ```bash
   # Update image
   kubectl set image deployment/api-gateway-blue \
     api-gateway=ECR_REGISTRY/ib-job-skill-mapping:v1.3 \
     -n production
   
   # Wait for rollout
   kubectl rollout status deployment/api-gateway-blue -n production
   ```

2. **Health Checks**
   - Startup probes: 5 minutes max
   - Liveness probes: Running every 10s
   - Readiness probes: Running every 5s
   - All pods must be ready before proceeding

3. **Internal Testing**
   ```bash
   # Access blue service directly
   kubectl port-forward svc/api-gateway-blue 8080:80 -n production
   
   # Run smoke tests
   curl http://localhost:8080/health
   curl http://localhost:8080/api/v1/health
   ```

### Phase 4: Approval Gate (0-24 hours)

**Manual approval required before traffic switch**

Review checklist:
- [ ] All blue pods running and ready
- [ ] Health checks passing
- [ ] Internal smoke tests passed
- [ ] Logs show no errors
- [ ] Metrics within normal range
- [ ] Database migrations successful
- [ ] Team notified and ready

### Phase 5: Traffic Switch (1-2 minutes)

1. **Update Service Selector**
   ```bash
   # Switch traffic from green to blue
   kubectl patch service api-gateway \
     -n production \
     -p '{"spec":{"selector":{"version":"blue"}}}'
   ```

2. **Gradual Traffic Shift** (Alternative: Canary)
   ```bash
   # Option: Use weighted routing (if using Istio/App Mesh)
   # 90% green, 10% blue → 50/50 → 10% green, 90% blue → 100% blue
   ```

3. **Monitor Initial Traffic**
   - Watch for 5 minutes
   - Check error rates
   - Monitor latency
   - Verify logs
   - Check metrics dashboard

### Phase 6: Production Validation (5-10 minutes)

1. **Smoke Tests**
   ```bash
   # Run production smoke tests
   pytest tests/smoke/ --base-url=https://api.infobeans.com
   ```

2. **Metrics Validation**
   - Error rate < 0.5%
   - P95 latency < 2 seconds
   - Throughput stable
   - All health checks passing

3. **User Verification**
   - Test critical user flows
   - Verify API responses
   - Check database queries

### Phase 7: Cleanup (2-5 minutes)

1. **Scale Down Green**
   ```bash
   # Keep green running for quick rollback window (1 hour)
   # After 1 hour, scale down to 0
   kubectl scale deployment/api-gateway-green --replicas=0 -n production
   ```

2. **Prepare for Next Deployment**
   ```bash
   # Relabel blue as the new green
   kubectl label deployment/api-gateway-blue environment=green --overwrite
   kubectl label deployment/api-gateway-green environment=blue --overwrite
   ```

## Rollback Procedure

### Immediate Rollback (<5 minutes)

If issues detected during Phase 5 or 6:

```bash
# 1. Switch traffic back to green
kubectl patch service api-gateway \
  -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# 2. Verify green is serving traffic
kubectl get endpoints api-gateway -n production

# 3. Check green health
curl https://api.infobeans.com/health

# 4. Notify team
echo "ROLLBACK EXECUTED - Green environment serving traffic"
```

### Delayed Rollback (after cleanup)

If issues detected after green is scaled down:

```bash
# 1. Scale up green deployment
kubectl scale deployment/api-gateway-green --replicas=3 -n production

# 2. Wait for pods to be ready
kubectl rollout status deployment/api-gateway-green -n production

# 3. Switch traffic to green
kubectl patch service api-gateway \
  -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# 4. Scale down blue
kubectl scale deployment/api-gateway-blue --replicas=0 -n production
```

### Database Rollback

**Only if absolutely necessary** (migrations are designed to be forward-compatible):

```bash
# Run rollback migration
kubectl run migration-rollback-{run-id} \
  --image=ECR_IMAGE:PREVIOUS_VERSION \
  --restart=Never \
  --command -- alembic downgrade -1

# WARNING: May cause data loss
# Only use if migration broke production
```

## Zero-Downtime Database Migrations

### Migration Strategy

**Expand-Contract Pattern:**

1. **Expand Phase** (before code deployment)
   - Add new columns/tables
   - Create indexes (CONCURRENTLY in PostgreSQL)
   - Add new constraints (if non-blocking)
   - Dual-write to old and new schema

2. **Migrate Phase** (during deployment)
   - New code uses new schema
   - Old code continues using old schema
   - Both schemas coexist

3. **Contract Phase** (after deployment succeeds)
   - Remove old columns/tables (next deployment)
   - Drop old indexes
   - Remove old constraints

### Example: Renaming a Column

**Deployment 1: Expand**
```sql
-- Add new column
ALTER TABLE team_members ADD COLUMN email_address VARCHAR(255);

-- Dual-write trigger (temporary)
CREATE OR REPLACE FUNCTION sync_email()
RETURNS TRIGGER AS $$
BEGIN
  NEW.email_address := NEW.email;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_email_trigger
  BEFORE INSERT OR UPDATE ON team_members
  FOR EACH ROW EXECUTE FUNCTION sync_email();
```

**Application Code:**
```python
# Write to both columns
team_member.email = new_email
team_member.email_address = new_email
```

**Deployment 2: Migrate**
```sql
-- Backfill existing data
UPDATE team_members SET email_address = email WHERE email_address IS NULL;
```

**Deployment 3: Contract**
```sql
-- Drop old column
ALTER TABLE team_members DROP COLUMN email;

-- Drop trigger
DROP TRIGGER sync_email_trigger ON team_members;
DROP FUNCTION sync_email();
```

### Safe Migration Practices

**✅ Safe Operations:**
- Adding nullable columns
- Adding tables
- Creating indexes CONCURRENTLY
- Adding check constraints as NOT VALID, then VALIDATE
- Increasing VARCHAR length
- Adding enum values (PostgreSQL)

**❌ Dangerous Operations:**
- Dropping columns (use 3-phase approach)
- Renaming columns (use 3-phase approach)
- Changing column types
- Adding NOT NULL constraints directly
- Creating non-concurrent indexes

### Migration Testing

```bash
# Test migration on staging
kubectl run migration-test \
  --image=ECR_IMAGE:VERSION \
  --env="DATABASE_URL=${STAGING_DB_URL}" \
  --command -- alembic upgrade head

# Test rollback
kubectl run migration-rollback-test \
  --image=ECR_IMAGE:VERSION \
  --env="DATABASE_URL=${STAGING_DB_URL}" \
  --command -- alembic downgrade -1

# Verify both succeed before production deployment
```

## Approval Gates

### Pre-Traffic-Switch Approval

**Approvers:** Tech Lead, DevOps Engineer, Product Manager

**Checklist:**
- [ ] All automated tests passed
- [ ] Blue environment deployed successfully
- [ ] Health checks passing for 5+ minutes
- [ ] Logs show no errors or warnings
- [ ] Database migrations successful
- [ ] Team available for monitoring
- [ ] Rollback plan confirmed

**How to Approve:**
```bash
# GitHub Actions workflow will pause at approval step
# Navigate to: https://github.com/ORG/REPO/actions
# Click on deployment run
# Click "Review deployments"
# Select "production-approval" environment
# Click "Approve and deploy"
```

### Post-Deployment Approval

After traffic switch, monitor for 1 hour before scaling down green.

**Auto-rollback if:**
- Error rate > 1%
- P95 latency > 5 seconds
- Health checks failing
- Database errors increasing

## Monitoring During Deployment

### Key Metrics to Watch

1. **Error Rate**
   ```
   Target: < 0.5%
   Alert: > 1%
   Critical: > 5%
   ```

2. **Latency**
   ```
   P50: < 500ms
   P95: < 2000ms
   P99: < 5000ms
   ```

3. **Throughput**
   ```
   Target: 100+ req/s
   Alert: < 50 req/s
   ```

4. **Health Checks**
   ```
   Target: 100% passing
   Alert: < 90% passing
   ```

### CloudWatch Queries

```bash
# Error rate
aws cloudwatch get-metric-statistics \
  --namespace "IB-JobSkillMapping-Prod" \
  --metric-name "ErrorCount" \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum

# Latency
aws cloudwatch get-metric-statistics \
  --namespace "IB-JobSkillMapping-Prod" \
  --metric-name "RequestDuration" \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average \
  --extended-statistics p95,p99
```

## Troubleshooting

### Issue: Blue Pods Not Starting

**Symptoms:**
- Pods stuck in `CrashLoopBackOff`
- Startup probes failing

**Resolution:**
```bash
# Check pod logs
kubectl logs -l version=blue -n production --tail=100

# Describe pod for events
kubectl describe pod -l version=blue -n production

# Common issues:
# - Database connection failure → Check security groups
# - Secrets Manager access denied → Check IAM role
# - Image pull failure → Check ECR permissions
```

### Issue: Traffic Switch Causes Errors

**Symptoms:**
- Error rate spikes after traffic switch
- 5XX responses increasing

**Resolution:**
```bash
# Immediate rollback
kubectl patch service api-gateway \
  -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Investigate blue logs
kubectl logs -l version=blue -n production --since=5m
```

### Issue: Migration Fails

**Symptoms:**
- Migration job fails
- Schema changes incomplete

**Resolution:**
```bash
# Check migration logs
kubectl logs migration-{run-id} -n production

# If safe, rerun migration
kubectl delete pod migration-{run-id} -n production
# Redeploy migration job

# If unsafe, abort deployment and investigate
```

## Best Practices

### ✅ Do's

- **Always test migrations** on staging first
- **Keep migrations backward-compatible** with previous version
- **Monitor closely** for first 30 minutes after traffic switch
- **Have team available** during deployments
- **Use feature flags** for large changes
- **Deploy during low-traffic windows** when possible
- **Keep rollback plan ready** and tested
- **Document any manual steps** required

### ❌ Don'ts

- **Don't deploy breaking changes** without migration strategy
- **Don't skip approval gates** under time pressure
- **Don't deploy on Fridays** (unless emergency)
- **Don't scale down green immediately** after traffic switch
- **Don't make schema changes** without backward compatibility
- **Don't deploy multiple services** simultaneously
- **Don't ignore warning signs** in metrics

## Emergency Procedures

### Emergency Rollback

```bash
#!/bin/bash
# emergency-rollback.sh

echo "EMERGENCY ROLLBACK INITIATED"

# Switch traffic immediately
kubectl patch service api-gateway \
  -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

echo "Traffic switched to green"

# Notify team
# Send Slack alert, PagerDuty incident

echo "Rollback complete. Monitor green environment."
```

### Emergency Hotfix

If critical bug needs immediate fix:

```bash
# 1. Create hotfix branch
git checkout -b hotfix/critical-bug main

# 2. Fix bug, commit, push

# 3. Trigger emergency deployment
gh workflow run deploy-production.yml \
  -f deployment_type=rolling \
  -f skip_tests=true \
  -f environment=production

# WARNING: Only use for critical production issues
# skip_tests should rarely be used
```

## Deployment Checklist

### Pre-Deployment
- [ ] Code review completed
- [ ] All tests passing in CI
- [ ] Staging deployment successful
- [ ] Database migrations tested
- [ ] Rollback plan documented
- [ ] Team notified of deployment
- [ ] On-call engineer identified

### During Deployment
- [ ] Monitor GitHub Actions workflow
- [ ] Watch CloudWatch metrics
- [ ] Check application logs
- [ ] Verify health checks
- [ ] Test critical endpoints
- [ ] Approve traffic switch

### Post-Deployment
- [ ] Smoke tests passed
- [ ] Metrics within acceptable range
- [ ] User verification complete
- [ ] Team notified of success
- [ ] Documentation updated
- [ ] Postmortem (if issues occurred)

## References

- [Kubernetes Blue-Green Deployments](https://kubernetes.io/blog/2018/04/30/zero-downtime-deployment-kubernetes-jenkins/)
- [Database Migration Best Practices](https://www.braintreepayments.com/blog/safe-operations-for-high-volume-postgresql/)
- [Expand-Contract Pattern](https://martinfowler.com/bliki/ParallelChange.html)
