# Disaster Recovery Plan

## Overview

This document defines the disaster recovery (DR) strategy for the IB Job Skill Mapping System production environment.

**Purpose:** Ensure business continuity in the event of catastrophic failure or disaster.

**Scope:** All production systems, data, and infrastructure.

---

## Recovery Objectives

### Recovery Time Objective (RTO)

**Definition:** Maximum acceptable time to restore service after disaster

**Target:** < 4 hours

**Breakdown by Component:**
- **Database:** < 15 minutes (automated RDS failover)
- **Application:** < 30 minutes (redeploy to backup region)
- **Cache:** < 10 minutes (Redis cluster failover)
- **DNS/Load Balancer:** < 5 minutes (Route 53 failover)
- **Full System:** < 4 hours (complete region failover)

---

### Recovery Point Objective (RPO)

**Definition:** Maximum acceptable data loss

**Target:** < 5 minutes

**Data Protection:**
- **Database:** < 5 minutes (RDS Multi-AZ synchronous replication)
- **Audit Logs:** < 1 minute (real-time streaming to S3)
- **Application State:** < 5 minutes (Redis persistence + S3 backup)
- **Configuration:** 0 minutes (stored in Git, no loss)

---

## Disaster Scenarios

### Scenario 1: Availability Zone (AZ) Failure

**Likelihood:** Medium (several times per year)  
**Impact:** Low (automatic failover)  
**RTO:** < 5 minutes  
**RPO:** 0 minutes

**Automatic Response:**
1. **RDS Multi-AZ:** Automatic failover to standby in different AZ (< 2 minutes)
2. **EKS:** Pods automatically rescheduled to healthy nodes in other AZs
3. **ElastiCache:** Automatic promotion of replica node
4. **ALB:** Routes traffic only to healthy targets

**Manual Actions:** None (fully automated)

**Validation:**
```bash
# Verify pods distributed across AZs
kubectl get pods -n production -o wide

# Check RDS status
aws rds describe-db-instances --db-instance-identifier ib-job-skill-mapping-prod-db
```

---

### Scenario 2: Complete Region Failure

**Likelihood:** Low (once every few years)  
**Impact:** High (requires manual failover)  
**RTO:** < 4 hours  
**RPO:** < 5 minutes

**Triggers:**
- AWS region-wide outage
- Catastrophic network failure
- Natural disaster affecting data center

**Response:**
1. **Declare Disaster** (< 15 minutes)
   - Assess scope and impact
   - Decision: Failover to DR region
   - Notify stakeholders

2. **Activate DR Site** (< 2 hours)
   - Deploy infrastructure in DR region (us-west-2)
   - Restore database from latest backup
   - Update DNS to point to DR region
   - Verify application deployment

3. **Validate and Monitor** (< 1 hour)
   - Run smoke tests
   - Verify data integrity
   - Monitor system health
   - Communicate restoration

4. **Failback** (when primary region restored)
   - Sync data from DR to primary
   - Switch traffic back to primary
   - Decommission DR resources

**See Detailed Procedure:** Section "Region Failover Procedure"

---

### Scenario 3: Data Corruption or Loss

**Likelihood:** Low (rare)  
**Impact:** High (potential data loss)  
**RTO:** < 2 hours  
**RPO:** Up to 24 hours (restore from backup)

**Triggers:**
- Application bug causing data corruption
- Accidental deletion
- Security breach with data modification
- Database failure with replication corruption

**Response:**
1. **Assess Damage** (< 30 minutes)
   - Identify affected tables/records
   - Determine corruption timeframe
   - Stop writes if corruption ongoing

2. **Point-in-Time Recovery** (< 1 hour)
   - Select recovery point before corruption
   - Restore to new RDS instance
   - Validate data integrity

3. **Merge or Replace Data** (< 30 minutes)
   - If partial corruption: Export clean data, import to production
   - If complete corruption: Promote restored instance to primary

4. **Post-Recovery**
   - Identify root cause
   - Implement safeguards
   - Update procedures

**See Detailed Procedure:** Section "Data Recovery Procedure"

---

### Scenario 4: Security Breach / Ransomware

**Likelihood:** Low to Medium  
**Impact:** Critical (requires immediate action)  
**RTO:** < 4 hours  
**RPO:** < 15 minutes (clean backup)

**Response:**
1. **Isolate** (< 5 minutes)
   - Disconnect affected systems
   - Revoke all API keys and secrets
   - Block external access at ALB

2. **Assess** (< 30 minutes)
   - Identify compromised systems
   - Determine attack vector
   - Check for data exfiltration
   - Engage security team

3. **Recover** (< 3 hours)
   - Restore from clean backup (before breach)
   - Rebuild compromised infrastructure
   - Rotate all secrets and credentials
   - Apply security patches

4. **Post-Incident**
   - Full security audit
   - Implement additional controls
   - Notify affected parties (GDPR compliance)

---

## Backup Strategy

### Database Backups

**Automated Daily Backups:**
- **Frequency:** Daily at 3:00 AM UTC
- **Retention:** 30 days
- **Storage:** S3 (encrypted with KMS)
- **Verification:** Weekly restore test to staging

**Point-in-Time Recovery:**
- **Enabled:** Yes (RDS automatic)
- **Retention:** 7 days
- **Granularity:** 5-minute intervals

**Backup Validation:**
```bash
# Weekly restore test (automated)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier ib-job-skill-mapping-prod-db \
  --target-db-instance-identifier ib-job-skill-mapping-restore-test \
  --restore-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)

# Run validation queries
psql -h <restore-test-endpoint> -U postgres -d ib_job_skill_mapping \
  -c "SELECT COUNT(*) FROM requisitions;"

# Delete test instance
aws rds delete-db-instance --db-instance-identifier ib-job-skill-mapping-restore-test --skip-final-snapshot
```

---

### Application State Backups

**Redis Persistence:**
- **RDB Snapshots:** Every 6 hours
- **AOF (Append-Only File):** Every second
- **Storage:** ElastiCache automatic S3 backup

**Configuration Backups:**
- **Git Repository:** All configuration in version control
- **Secrets:** AWS Secrets Manager (automatic replication to DR region)
- **Infrastructure as Code:** Terraform state in S3 with versioning

---

### Audit Log Backups

**Real-Time Streaming:**
- **Source:** CloudWatch Logs
- **Destination:** S3 (long-term storage)
- **Format:** JSON lines (gzipped)
- **Retention:** 7 years (compliance requirement)

**Backup Structure:**
```
s3://ib-job-skill-mapping-audit-logs-prod/
├── year=2026/
│   ├── month=02/
│   │   ├── day=08/
│   │   │   ├── hour=00/
│   │   │   │   ├── application-logs-00.json.gz
│   │   │   │   ├── api-gateway-logs-00.json.gz
│   │   │   │   └── ...
```

---

## DR Infrastructure

### Primary Region: us-east-1

**Production Environment:**
- VPC: 10.0.0.0/16
- 3 Availability Zones
- EKS Cluster: 3-10 nodes
- RDS Multi-AZ: Primary + Standby
- ElastiCache: 2-node cluster
- S3 Buckets: Application data, backups

---

### DR Region: us-west-2

**Standby Environment (Warm Standby):**

**Infrastructure Provisioning:**
- **Pre-Provisioned:** VPC, subnets, security groups
- **On-Demand:** EKS cluster, RDS, ElastiCache (deployed during DR activation)

**Cost Optimization:**
- Minimal resources running (VPC only = ~$0/month)
- Deploy full stack only during DR activation
- Estimated DR activation cost: ~$2,000/month during recovery

**Database Replication:**
- **Cross-Region Read Replica:** RDS replica in us-west-2
- **Replication Lag:** < 1 second
- **Promotion Time:** < 5 minutes

**Data Sync:**
- **S3 Cross-Region Replication:** Enabled for all critical buckets
- **Secrets Manager:** Automatic replication to us-west-2

---

### DR Architecture Diagram

```
Primary Region (us-east-1)              DR Region (us-west-2)
┌─────────────────────────┐           ┌─────────────────────────┐
│                         │           │                         │
│   Route 53 (Active)     │──────────▶│   Route 53 (Standby)    │
│   Health Check          │           │   Health Check          │
│         │               │           │         │               │
│         ▼               │           │         ▼               │
│   ┌──────────────┐      │           │   ┌──────────────┐      │
│   │ ALB (Active) │      │           │   │ ALB (Standby)│      │
│   └──────┬───────┘      │           │   └──────┬───────┘      │
│          │              │           │          │              │
│   ┌──────▼───────┐      │           │   ┌──────▼───────┐      │
│   │ EKS Cluster  │      │           │   │ EKS Cluster  │      │
│   │ (3-10 nodes) │      │           │   │  (Standby)   │      │
│   └──────┬───────┘      │           │   └──────┬───────┘      │
│          │              │           │          │              │
│   ┌──────▼───────┐      │    ┌──────┼──────────┼──────┐      │
│   │ RDS Primary  │──────┼────│──────▶ RDS Replica      │      │
│   │  (Multi-AZ)  │      │    │      │  (Read Replica)  │      │
│   └──────────────┘      │    │      └──────────────────┘      │
│                         │    │                                │
│   ┌──────────────┐      │    │      ┌──────────────┐         │
│   │ ElastiCache  │      │    │      │ ElastiCache  │         │
│   │  (Active)    │      │    │      │  (Standby)   │         │
│   └──────────────┘      │    │      └──────────────┘         │
│                         │    │                                │
│   ┌──────────────┐      │    │      ┌──────────────┐         │
│   │ S3 Buckets   │──────┼────│─────▶│ S3 Buckets   │         │
│   │ (Replication)│      │    │      │ (Replica)    │         │
│   └──────────────┘      │    │      └──────────────┘         │
│                         │    │                                │
└─────────────────────────┘    └────────────────────────────────┘
```

---

## Region Failover Procedure

### Phase 1: Decision and Declaration (< 15 minutes)

**Trigger Conditions:**
- Complete region outage confirmed (> 30 minutes)
- AWS Status Dashboard indicates extended outage
- SLA breach imminent (> 1 hour downtime)

**Decision Makers:**
- CTO (primary authority)
- DevOps Lead (technical assessment)
- On-Call Engineer (situation report)

**Actions:**
1. **Assess Situation:**
   ```bash
   # Check AWS Service Health
   aws health describe-events --filter eventTypeCategories=issue --region us-east-1
   
   # Check RDS replication lag
   aws cloudwatch get-metric-statistics \
     --namespace AWS/RDS \
     --metric-name ReplicaLag \
     --dimensions Name=DBInstanceIdentifier,Value=ib-job-skill-mapping-prod-db-replica \
     --start-time $(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 60 --statistics Average --region us-west-2
   ```

2. **Declare DR Activation:**
   - Conference bridge: Start Zoom call
   - War room: Create #dr-failover Slack channel
   - Status page: Post "Major Outage - DR Activation in Progress"
   - Stakeholders: Email executives and customers

3. **Assign Roles:**
   - **DR Lead:** Coordinates overall failover
   - **Database:** Promotes RDS replica
   - **Infrastructure:** Deploys DR resources
   - **Application:** Verifies deployment and configuration
   - **Communication:** Updates stakeholders

---

### Phase 2: Activate DR Site (< 2 hours)

**Step 1: Promote RDS Replica (< 10 minutes)**

**Database Lead Actions:**
```bash
# 1. Stop application writes (set service to read-only mode)
kubectl scale deployment api-gateway-blue --replicas=0 -n production

# 2. Verify replication lag is minimal
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=ib-job-skill-mapping-prod-db-replica \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Maximum --region us-west-2

# Expected: < 5 seconds lag

# 3. Promote replica to standalone
aws rds promote-read-replica \
  --db-instance-identifier ib-job-skill-mapping-prod-db-replica \
  --region us-west-2

# 4. Wait for promotion (takes ~5 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier ib-job-skill-mapping-prod-db-replica \
  --region us-west-2

# 5. Update DNS CNAME for database endpoint (if used)
# Or note new endpoint for application configuration

# 6. Enable automated backups on promoted instance
aws rds modify-db-instance \
  --db-instance-identifier ib-job-skill-mapping-prod-db-replica \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00" \
  --region us-west-2
```

**Verification:**
```bash
# Connect to promoted database
psql -h <new-primary-endpoint> -U postgres -d ib_job_skill_mapping

# Verify data integrity
SELECT COUNT(*) FROM requisitions;
SELECT COUNT(*) FROM matches;
SELECT MAX(created_at) FROM requisitions;

# Exit psql
\q
```

---

**Step 2: Deploy Infrastructure (< 30 minutes)**

**Infrastructure Lead Actions:**
```bash
# 1. Switch to DR region
export AWS_REGION=us-west-2
export AWS_DEFAULT_REGION=us-west-2

# 2. Navigate to DR Terraform directory
cd infra/terraform/dr

# 3. Initialize Terraform
terraform init

# 4. Review plan (ensure correct region)
terraform plan -out=dr-activation.tfplan

# 5. Apply infrastructure
terraform apply dr-activation.tfplan
# This creates:
# - EKS cluster (10-15 minutes)
# - ElastiCache cluster (5 minutes)
# - ALB (2 minutes)
# - Security groups, IAM roles, etc.

# 6. Configure kubectl for DR cluster
aws eks update-kubeconfig \
  --region us-west-2 \
  --name ib-job-skill-mapping-dr-cluster

# 7. Verify cluster
kubectl get nodes
kubectl get namespaces
```

**Expected Output:**
- 3 nodes ready
- production namespace exists

---

**Step 3: Update Configuration (< 15 minutes)**

**Application Lead Actions:**
```bash
# 1. Retrieve secrets from DR region (auto-replicated)
aws secretsmanager list-secrets --region us-west-2 --output table

# 2. Update database endpoint in ConfigMap
kubectl create configmap app-config \
  --from-literal=database_host=<new-primary-endpoint> \
  --from-literal=database_port=5432 \
  --from-literal=redis_host=<dr-redis-endpoint> \
  --from-literal=redis_port=6379 \
  --from-literal=environment=production-dr \
  -n production \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Create ServiceAccount with IRSA for Secrets Manager
kubectl apply -f k8s/dr/service-account.yaml -n production

# 4. Verify secrets accessible
kubectl run test-secrets --rm -it --restart=Never \
  --image=amazon/aws-cli \
  --serviceaccount=api-service-account \
  -- secretsmanager get-secret-value \
  --secret-id ib-job-skill-mapping/prod/database \
  --region us-west-2
```

---

**Step 4: Deploy Application (< 30 minutes)**

**Application Lead Actions:**
```bash
# 1. Deploy Kubernetes manifests
kubectl apply -f k8s/dr/namespace.yaml
kubectl apply -f k8s/dr/deployment.yaml
kubectl apply -f k8s/dr/service.yaml
kubectl apply -f k8s/dr/hpa.yaml
kubectl apply -f k8s/dr/pdb.yaml

# 2. Wait for pods to be ready
kubectl wait --for=condition=ready pod \
  -l app=api-gateway \
  -n production \
  --timeout=300s

# 3. Check pod status
kubectl get pods -n production -o wide

# Expected: 3/3 pods running

# 4. Check logs
kubectl logs -l app=api-gateway -n production --tail=20

# Look for:
# - "Application started successfully"
# - "Database connection established"
# - "Redis connection established"
# - No errors

# 5. Internal smoke test
kubectl run curl --rm -it --restart=Never --image=curlimages/curl \
  -- curl -s http://api-gateway.production.svc.cluster.local:8080/health

# Expected: {"status": "healthy"}
```

---

**Step 5: Update DNS (< 10 minutes)**

**Infrastructure Lead Actions:**
```bash
# 1. Get DR region ALB endpoint
aws elbv2 describe-load-balancers \
  --region us-west-2 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `ib-job-skill-mapping-dr`)].DNSName' \
  --output text

# 2. Update Route 53 record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.infobeans.com",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "<dr-alb-endpoint>"}]
      }
    }]
  }'

# 3. Wait for DNS propagation (5-10 minutes)
# Check from multiple locations
dig api.infobeans.com +short

# 4. Verify health check passes
aws route53 get-health-check-status --health-check-id <health-check-id>
```

**DNS Propagation Note:**
- TTL set to 60 seconds for quick propagation
- Some clients may cache for longer
- Use Route 53 health checks to auto-failover if configured

---

### Phase 3: Validation (< 1 hour)

**Smoke Tests:**
```bash
# 1. Health check
curl https://api.infobeans.com/health
# Expected: {"status": "healthy"}

# 2. Authentication
curl -X POST https://api.infobeans.com/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"grant_type": "client_credentials", "client_id": "test", "client_secret": "test"}' \
  -v
# Expected: 200 OK with access token

# 3. Submit test requisition
curl -X POST https://api.infobeans.com/api/v1/requisitions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "DR Test", "skills_required": ["Python"], "urgency_level": "medium"}' \
  -v
# Expected: 202 Accepted with requisition_id

# 4. Check requisition status
curl https://api.infobeans.com/api/v1/requisitions/<requisition-id> \
  -H "Authorization: Bearer <token>" \
  -v
# Expected: 200 OK with requisition details

# 5. Verify metrics
curl https://api.infobeans.com/metrics \
  -H "Authorization: Bearer <token>" | grep http_requests_total
# Expected: Metrics being collected
```

**Data Integrity Checks:**
```bash
# Connect to DR database
psql -h <dr-primary-endpoint> -U postgres -d ib_job_skill_mapping

# Check record counts match expected
SELECT 
  (SELECT COUNT(*) FROM requisitions) as requisitions,
  (SELECT COUNT(*) FROM matches) as matches,
  (SELECT COUNT(*) FROM availabilities) as availabilities,
  (SELECT COUNT(*) FROM audit_logs) as audit_logs;

# Compare to pre-DR snapshot (from monitoring)

# Check recent data exists
SELECT id, title, created_at 
FROM requisitions 
ORDER BY created_at DESC 
LIMIT 5;

# Verify no data loss (latest record should be within RPO)
\q
```

**Monitoring:**
```bash
# Check CloudWatch alarms in DR region
aws cloudwatch describe-alarms \
  --state-value ALARM \
  --region us-west-2

# Expected: No critical alarms

# Check pod health
kubectl get pods -n production
kubectl top pods -n production
kubectl top nodes

# Expected: All pods running, normal resource usage
```

---

### Phase 4: Communication (Throughout)

**Status Page Updates:**
- **T+0:** "Major Outage - Primary region unavailable. DR activation in progress."
- **T+30m:** "DR site deployment ongoing. ETA: 90 minutes."
- **T+90m:** "DR site active. Running validation tests."
- **T+120m:** "Service restored via DR site. Monitoring closely."

**Stakeholder Emails:**

**Initial Notification:**
```
Subject: [CRITICAL] Production Outage - DR Activation in Progress

Team,

We are experiencing a complete outage of our primary AWS region (us-east-1) 
due to [reason]. We have activated our disaster recovery plan and are 
failing over to our DR region (us-west-2).

Current Status: DR activation in progress
Estimated Restoration: 2 hours
Impact: Complete service unavailable
Data Loss: None expected (RPO < 5 minutes)

Next Update: In 30 minutes

Status Page: https://status.infobeans.com
War Room: #dr-failover on Slack

DevOps Team
```

**Restoration Notification:**
```
Subject: [RESOLVED] Service Restored via DR Site

Team,

Service has been successfully restored via our DR site in us-west-2.

Resolution Time: 2 hours 15 minutes
Data Loss: None (verified)
Current Status: Operational via DR region

We will continue monitoring closely and will failback to the primary 
region once AWS confirms full restoration.

Next Steps:
- Monitor DR site for 24 hours
- Plan failback to primary region
- Post-mortem scheduled for [date]

Thank you for your patience.

DevOps Team
```

---

## Failback Procedure

**When:** Primary region (us-east-1) fully restored and confirmed stable for 24 hours

**RTO for Failback:** < 4 hours (non-urgent, during maintenance window)

### Step 1: Prepare Primary Region (< 1 hour)

```bash
# 1. Verify primary region health
aws health describe-events --filter eventTypeCategories=issue --region us-east-1
# Expected: No active issues

# 2. Restore RDS primary
# Option A: Promote original instance if recovered
# Option B: Create new primary from DR replica

# Create cross-region read replica from DR primary
aws rds create-db-instance-read-replica \
  --db-instance-identifier ib-job-skill-mapping-prod-db-new \
  --source-db-instance-identifier ib-job-skill-mapping-prod-db-replica \
  --source-region us-west-2 \
  --region us-east-1

# Wait for replication catchup (check replication lag)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=ib-job-skill-mapping-prod-db-new \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Average --region us-east-1

# When lag < 1 second, promote to standalone
aws rds promote-read-replica \
  --db-instance-identifier ib-job-skill-mapping-prod-db-new \
  --region us-east-1

# 3. Redeploy EKS and infrastructure
cd infra/terraform/prod
terraform init
terraform plan
terraform apply
```

---

### Step 2: Sync Data (< 30 minutes)

```bash
# 1. Stop writes to DR region (maintenance mode)
kubectl scale deployment api-gateway-blue --replicas=0 -n production

# 2. Final database sync already complete (via replication)

# 3. Sync S3 data
aws s3 sync s3://ib-job-skill-mapping-dr/ s3://ib-job-skill-mapping-prod/ --region us-west-2

# 4. Verify data integrity
# Connect to new primary
psql -h <new-primary-us-east-1> -U postgres -d ib_job_skill_mapping
SELECT COUNT(*) FROM requisitions;
# Compare to DR count
\q
```

---

### Step 3: Switch Traffic (< 30 minutes)

```bash
# 1. Deploy application to primary region
kubectl config use-context ib-job-skill-mapping-prod
kubectl apply -f k8s/production/deployment.yaml

# 2. Wait for pods ready
kubectl wait --for=condition=ready pod -l app=api-gateway -n production --timeout=300s

# 3. Smoke test internal
kubectl run curl --rm -it --restart=Never --image=curlimages/curl \
  -- curl -s http://api-gateway.production.svc.cluster.local:8080/health

# 4. Update Route 53 to primary region ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.infobeans.com",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "<primary-alb-endpoint>"}]
      }
    }]
  }'

# 5. Wait for DNS propagation
dig api.infobeans.com +short

# 6. External smoke test
curl https://api.infobeans.com/health
```

---

### Step 4: Decommission DR (< 30 minutes)

```bash
# 1. Scale down DR deployments
kubectl scale deployment api-gateway-blue --replicas=0 -n production --context=dr-cluster

# 2. Demote DR database to read replica (optional, for future DR)
aws rds create-db-instance-read-replica \
  --db-instance-identifier ib-job-skill-mapping-prod-db-replica \
  --source-db-instance-identifier ib-job-skill-mapping-prod-db-new \
  --source-region us-east-1 \
  --region us-west-2

# 3. Destroy DR infrastructure (retain VPC and replica)
cd infra/terraform/dr
terraform destroy -target=module.eks -target=module.alb -target=module.elasticache

# 4. Update status page
# "Failback complete. Service operating normally from primary region."
```

---

## Testing and Drills

### Disaster Recovery Drills

**Frequency:** Twice per year (every 6 months)

**Types of Drills:**

**1. Tabletop Exercise (2 hours)**
- Walkthrough of DR scenarios
- Role assignments
- Communication practice
- No actual failover

**2. Partial Failover Drill (4 hours)**
- Deploy DR infrastructure
- Restore database to DR
- Test application in DR
- Do NOT switch DNS (no customer impact)

**3. Full Failover Drill (8 hours, annual)**
- Complete failover to DR region
- Switch DNS to DR
- Run production traffic for 1 hour
- Failback to primary

**Schedule:**
- Q1: Tabletop exercise
- Q2: Partial failover drill
- Q3: Tabletop exercise
- Q4: Full failover drill

---

### Backup Restore Testing

**Database Restore Test:**
```bash
# Weekly automated test
# Restore latest backup to staging
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier ib-job-skill-mapping-restore-test \
  --db-snapshot-identifier <latest-snapshot> \
  --region us-east-1

# Wait for restore
aws rds wait db-instance-available \
  --db-instance-identifier ib-job-skill-mapping-restore-test

# Run validation queries
psql -h <restore-test-endpoint> -U postgres -d ib_job_skill_mapping -f scripts/validate_restore.sql

# Expected output: All validations pass

# Delete test instance
aws rds delete-db-instance \
  --db-instance-identifier ib-job-skill-mapping-restore-test \
  --skip-final-snapshot
```

**Validation Script (scripts/validate_restore.sql):**
```sql
-- Check table existence
SELECT COUNT(*) as table_count 
FROM information_schema.tables 
WHERE table_schema = 'public';
-- Expected: 15 tables

-- Check recent data
SELECT MAX(created_at) as latest_requisition FROM requisitions;
-- Expected: Within last 24 hours

-- Check data integrity
SELECT COUNT(*) FROM requisitions WHERE title IS NULL;
-- Expected: 0

-- Check indexes
SELECT COUNT(*) as index_count 
FROM pg_indexes 
WHERE schemaname = 'public';
-- Expected: 25 indexes

\echo 'Restore validation complete'
```

---

## Contact Information

**DR Coordinator:** dr-coordinator@infobeans.com  
**CTO (DR Authority):** cto@infobeans.com, +1-555-0100  
**DevOps Lead:** devops-lead@infobeans.com, +1-555-0102  
**On-Call Engineer:** See PagerDuty schedule  

**External Contacts:**
- **AWS Support (Enterprise):** +1-800-AWS-SUPPORT
- **AWS TAM (Technical Account Manager):** [TAM Name], [TAM Email]

---

## Document Control

**Version:** 1.0  
**Last Updated:** February 8, 2026  
**Next Review:** May 8, 2026  
**Last DR Drill:** TBD (schedule Q2 2026)  
**Last Backup Restore Test:** TBD (weekly automated)  
**Owner:** DevOps Team / CTO

---

## Appendix A: Pre-Flight Checklist

**Before DR Activation:**
- [ ] Confirm region outage (AWS Status Dashboard)
- [ ] Check RDS replication lag < 5 seconds
- [ ] Verify S3 cross-region replication up-to-date
- [ ] Confirm DR infrastructure Terraform state valid
- [ ] Assemble DR team (Slack #dr-failover)
- [ ] Start conference bridge
- [ ] Notify stakeholders (status page, email)
- [ ] Obtain CTO approval for failover

**After DR Activation:**
- [ ] Service restored and validated
- [ ] Data integrity confirmed
- [ ] Monitoring active in DR region
- [ ] Stakeholders notified
- [ ] Incident report created
- [ ] Post-mortem scheduled
- [ ] Lessons learned documented

---

## Appendix B: Emergency Contacts

| Role | Name | Email | Phone | Backup |
|------|------|-------|-------|--------|
| CTO | Bob Johnson | bob.johnson@infobeans.com | +1-555-0100 | - |
| DevOps Lead | Jane Smith | jane.smith@infobeans.com | +1-555-0102 | +1-555-0103 |
| Tech Lead | John Doe | john.doe@infobeans.com | +1-555-0101 | +1-555-0104 |
| On-Call | See PagerDuty | - | - | - |
| AWS TAM | [TAM Name] | [tam@amazon.com] | [TAM Phone] | - |
| Product Lead | [Name] | [email] | [phone] | - |

---

**END OF DOCUMENT**
