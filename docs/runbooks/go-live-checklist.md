# Production Go-Live Checklist

## Overview

This checklist ensures all prerequisites are met before deploying to production.

**Target Go-Live Date:** February 10, 2026  
**Deployment Window:** 6:00 AM - 10:00 AM UTC (off-peak hours)

---

## Phase 1: Pre-Deployment Validation (T-48 hours)

### Infrastructure Readiness

- [ ] **VPC & Networking**
  ```bash
  # Verify VPC configuration
  aws ec2 describe-vpcs --filters "Name=tag:Name,Values=ib-job-skill-mapping-prod-vpc"
  # Expected: VPC with 3 AZs, CIDR 10.0.0.0/16
  
  # Verify subnets
  aws ec2 describe-subnets --filters "Name=tag:Environment,Values=prod" | grep CidrBlock
  # Expected: 6 subnets (3 public, 3 private)
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **RDS Database**
  ```bash
  # Check database status
  aws rds describe-db-instances --db-instance-identifier ib-job-skill-mapping-prod-db
  # Expected: Status "available", Multi-AZ enabled, Engine "postgres 15"
  
  # Verify read replica
  aws rds describe-db-instances --db-instance-identifier ib-job-skill-mapping-prod-db-replica
  # Expected: Status "available", in us-west-2 (DR)
  
  # Test connectivity
  psql -h <db-endpoint> -U postgres -d ib_job_skill_mapping -c "SELECT version();"
  # Expected: PostgreSQL 15.x
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **EKS Cluster**
  ```bash
  # Check cluster status
  aws eks describe-cluster --name ib-job-skill-mapping-prod --query 'cluster.status'
  # Expected: "ACTIVE"
  
  # Check nodes
  kubectl get nodes
  # Expected: 3 nodes ready in different AZs
  
  # Check node resources
  kubectl top nodes
  # Expected: CPU < 50%, Memory < 50%
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **ElastiCache (Redis)**
  ```bash
  # Check Redis cluster status
  aws elasticache describe-cache-clusters --cache-cluster-id ib-job-skill-mapping-prod-redis
  # Expected: Status "available", 2 nodes
  
  # Test connectivity
  redis-cli -h <redis-endpoint> -p 6379 ping
  # Expected: PONG
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **Application Load Balancer**
  ```bash
  # Check ALB status
  aws elbv2 describe-load-balancers --names ib-job-skill-mapping-prod-alb
  # Expected: State "active"
  
  # Check target groups
  aws elbv2 describe-target-health --target-group-arn <target-group-arn>
  # Expected: No targets registered yet (will be added during deployment)
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **S3 Buckets**
  ```bash
  # Verify buckets exist
  aws s3 ls | grep ib-job-skill-mapping-prod
  # Expected: ib-job-skill-mapping-prod-data, ib-job-skill-mapping-audit-logs-prod
  
  # Check versioning
  aws s3api get-bucket-versioning --bucket ib-job-skill-mapping-prod-data
  # Expected: Status "Enabled"
  
  # Check encryption
  aws s3api get-bucket-encryption --bucket ib-job-skill-mapping-prod-data
  # Expected: SSE-KMS enabled
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

---

### Secrets & Configuration

- [ ] **Secrets Manager**
  ```bash
  # Verify all secrets exist
  aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `ib-job-skill-mapping/prod`)].Name'
  # Expected: database, redis, jwt, llm-api-keys, microsoft-graph
  
  # Test secret retrieval
  aws secretsmanager get-secret-value --secret-id ib-job-skill-mapping/prod/database | jq -r .SecretString
  # Expected: Valid JSON with host, port, username, password, database
  
  # Verify KMS encryption
  aws secretsmanager describe-secret --secret-id ib-job-skill-mapping/prod/database | jq -r .KmsKeyId
  # Expected: Valid KMS key ARN
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **ConfigMap Prepared**
  ```bash
  # Review ConfigMap
  cat k8s/production/deployment.yaml | grep -A 20 "kind: ConfigMap"
  # Expected: All non-sensitive configuration present
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **IRSA Configured**
  ```bash
  # Verify IAM role for service account
  aws iam get-role --role-name ib-job-skill-mapping-prod-api-role
  # Expected: Trust policy allows EKS service account
  
  # Verify policy attachments
  aws iam list-attached-role-policies --role-name ib-job-skill-mapping-prod-api-role
  # Expected: SecretsManagerReadPolicy attached
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

---

### Database Schema & Migrations

- [ ] **Schema Deployed**
  ```bash
  # Connect to database
  psql -h <db-endpoint> -U postgres -d ib_job_skill_mapping
  
  # Check tables exist
  \dt
  # Expected: 15 tables (requisitions, matches, availabilities, skills, etc.)
  
  # Check indexes
  \di
  # Expected: 25+ indexes
  
  # Check functions
  \df
  # Expected: audit trigger functions
  
  # Exit
  \q
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **Migrations Tested**
  ```bash
  # Check alembic version
  alembic current
  # Expected: head (latest version)
  
  # Verify migration history
  alembic history
  # Expected: All migrations present
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **Seed Data Loaded**
  ```bash
  # Check for reference data
  psql -h <db-endpoint> -U postgres -d ib_job_skill_mapping \
    -c "SELECT COUNT(*) FROM skills;"
  # Expected: > 0 (skill reference data)
  
  # Check audit log structure
  psql -h <db-endpoint> -U postgres -d ib_job_skill_mapping \
    -c "SELECT COUNT(*) FROM audit_logs;"
  # Expected: 0 (no production data yet, but table exists)
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

---

### Monitoring & Alerting

- [ ] **CloudWatch Alarms Active**
  ```bash
  # Check alarms exist
  aws cloudwatch describe-alarms --alarm-name-prefix "ib-job-skill-mapping-prod" | jq -r '.MetricAlarms[].AlarmName'
  # Expected: 25 alarms listed
  
  # Check no alarms in ALARM state
  aws cloudwatch describe-alarms --state-value ALARM | jq -r '.MetricAlarms[].AlarmName'
  # Expected: Empty (no alarms firing)
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **SNS Topics Configured**
  ```bash
  # Check SNS topics
  aws sns list-topics | grep ib-job-skill-mapping-prod
  # Expected: critical-alerts and warning-alerts topics
  
  # Verify subscriptions
  aws sns list-subscriptions-by-topic --topic-arn <critical-alerts-topic-arn>
  # Expected: Email subscriptions confirmed
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **Prometheus Deployed**
  ```bash
  # Check Prometheus pod
  kubectl get pods -n monitoring -l app=prometheus
  # Expected: 1/1 Running
  
  # Check Prometheus targets
  curl http://prometheus.monitoring.svc.cluster.local:9090/api/v1/targets | jq '.data.activeTargets | length'
  # Expected: > 0 targets
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **Grafana Dashboard Accessible**
  ```bash
  # Access Grafana
  # URL: http://grafana.infobeans.com
  # Login with admin credentials
  # Navigate to "IB Job Skill Mapping - System Overview"
  # Verify all panels load
  ```
  **Dashboard URL:** http://grafana.infobeans.com/d/system-overview  
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **Log Aggregation Working**
  ```bash
  # Check CloudWatch log groups
  aws logs describe-log-groups --log-group-name-prefix "/aws/ib-job-skill-mapping/prod"
  # Expected: 4 log groups (application, api-gateway, ai-agents, database)
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

---

### Security & Access

- [ ] **WAF Rules Configured (if applicable)**
  ```bash
  # Check WAF web ACL
  aws wafv2 list-web-acls --scope REGIONAL --region us-east-1
  # Expected: WAF ACL for ALB (optional)
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **Security Groups Validated**
  ```bash
  # Check ALB security group
  aws ec2 describe-security-groups --group-ids <alb-sg-id>
  # Expected: Ingress 443 from 0.0.0.0/0, egress to EKS nodes
  
  # Check EKS node security group
  aws ec2 describe-security-groups --group-ids <eks-node-sg-id>
  # Expected: Ingress from ALB SG, egress to RDS and Redis
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **IAM Roles & Policies Reviewed**
  ```bash
  # List IAM roles for production
  aws iam list-roles | jq -r '.Roles[] | select(.RoleName | contains("ib-job-skill-mapping-prod")) | .RoleName'
  # Expected: API role, EKS node role, etc.
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **SSL/TLS Certificate Valid**
  ```bash
  # Check ACM certificate
  aws acm list-certificates --region us-east-1
  # Expected: Certificate for *.infobeans.com or api.infobeans.com
  
  # Verify expiration
  aws acm describe-certificate --certificate-arn <cert-arn> | jq -r '.Certificate.NotAfter'
  # Expected: > 30 days in future
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

---

### Application Artifacts

- [ ] **Docker Image Built & Pushed**
  ```bash
  # Check ECR repository
  aws ecr describe-repositories --repository-names ib-job-skill-mapping
  # Expected: Repository exists
  
  # List images
  aws ecr list-images --repository-name ib-job-skill-mapping
  # Expected: At least one image with tag "v1.0.0" or "latest"
  
  # Inspect image
  aws ecr batch-get-image --repository-name ib-job-skill-mapping --image-ids imageTag=v1.0.0 | jq -r '.images[0].imageManifest' | jq -r '.config.digest'
  # Expected: Valid SHA256 digest
  ```
  **Image Tag:** ___________  
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **Kubernetes Manifests Validated**
  ```bash
  # Dry-run apply
  kubectl apply -f k8s/production/ --dry-run=client
  # Expected: No errors
  
  # Validate YAML
  kubeval k8s/production/*.yaml
  # Expected: All manifests valid
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

---

### External Dependencies

- [ ] **Microsoft Graph API Access**
  ```bash
  # Test Graph API connectivity
  curl -X POST https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token \
    -d "client_id=<client-id>&client_secret=<client-secret>&grant_type=client_credentials&scope=https://graph.microsoft.com/.default"
  # Expected: 200 OK with access token
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **OpenAI API Access**
  ```bash
  # Test OpenAI API
  curl https://api.openai.com/v1/models \
    -H "Authorization: Bearer <openai-api-key>"
  # Expected: 200 OK with model list
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

- [ ] **Anthropic API Access**
  ```bash
  # Test Anthropic API
  curl https://api.anthropic.com/v1/models \
    -H "x-api-key: <anthropic-api-key>" \
    -H "anthropic-version: 2023-06-01"
  # Expected: 200 OK with model list
  ```
  **Status:** ___________  
  **Verified By:** ___________  
  **Date/Time:** ___________

---

### Team Readiness

- [ ] **On-Call Schedule Set**
  - Primary On-Call: ___________
  - Backup On-Call: ___________
  - PagerDuty schedule configured: [ ] Yes [ ] No
  **Status:** ___________  
  **Verified By:** ___________

- [ ] **Runbooks Reviewed**
  - [ ] Production Deployment Runbook
  - [ ] Incident Response Procedures
  - [ ] Disaster Recovery Plan
  **Reviewed By:** ___________  
  **Date:** ___________

- [ ] **Access Verified**
  - [ ] AWS Console (all team members)
  - [ ] kubectl access (all team members)
  - [ ] PagerDuty (on-call engineers)
  - [ ] Grafana (all team members)
  **Verified By:** ___________  
  **Date:** ___________

- [ ] **Training Completed**
  - [ ] On-call training (on-call engineers)
  - [ ] Incident response drill
  - [ ] Deployment walkthrough
  **Completed:** ___________  
  **Date:** ___________

---

### Communication

- [ ] **Stakeholders Notified**
  - [ ] Email to executives (go-live date/time)
  - [ ] Email to customers (scheduled maintenance)
  - [ ] Status page announcement (7 days advance)
  - [ ] Slack announcement (#general, #engineering)
  **Sent By:** ___________  
  **Date:** ___________

- [ ] **War Room Established**
  - Slack channel: #production-golive
  - Zoom link: ___________
  - Participants: DevOps, Tech Lead, On-Call, Product
  **Created By:** ___________  
  **Date:** ___________

---

## Phase 2: Deployment Day (T-0)

### Pre-Deployment (6:00 AM UTC)

- [ ] **Team Assembled**
  - [ ] DevOps Lead
  - [ ] Tech Lead
  - [ ] On-Call Engineer (Primary)
  - [ ] On-Call Engineer (Backup)
  - [ ] Product Manager (optional)
  **Assembled At:** ___________

- [ ] **Final System Check**
  ```bash
  # No critical alarms
  aws cloudwatch describe-alarms --state-value ALARM
  # Expected: Empty
  
  # Database accessible
  psql -h <db-endpoint> -U postgres -d ib_job_skill_mapping -c "SELECT 1;"
  # Expected: 1
  
  # EKS nodes healthy
  kubectl get nodes
  # Expected: All Ready
  ```
  **Status:** ___________  
  **Time:** ___________

- [ ] **Status Page Updated**
  - Posted: "Scheduled deployment in progress"
  **Posted By:** ___________  
  **Time:** ___________

---

### Deployment Execution (6:15 AM - 8:00 AM UTC)

See: [Production Deployment Runbook](production-deployment.md) for detailed steps

- [ ] **Step 1: Trigger GitHub Actions Workflow**
  - Workflow: `.github/workflows/deploy-production.yml`
  - Branch: `main`
  - Tag: `v1.0.0`
  **Triggered By:** ___________  
  **Time:** ___________  
  **Run URL:** ___________

- [ ] **Step 2: Monitor Validation & Testing**
  - Validate job: ✅
  - Test jobs (smoke, unit, integration): ✅
  - Build job: ✅
  **Completed:** ___________

- [ ] **Step 3: Database Migration**
  - Migration safety check: ✅
  - Migration executed: ✅
  - Verification passed: ✅
  **Completed:** ___________

- [ ] **Step 4: Deploy Blue Environment**
  - Pods deployed: ✅ (3/3 running)
  - Health checks passing: ✅
  - Logs clear of errors: ✅
  **Completed:** ___________

- [ ] **Step 5: Approval Gate**
  - Readiness review completed
  - Approved by: ___________
  - Time: ___________

- [ ] **Step 6: Traffic Switch**
  - Service selector updated to blue
  - Traffic flowing to blue: ✅
  - No 5xx errors: ✅
  **Completed:** ___________

- [ ] **Step 7: Production Smoke Tests**
  - Health check: ✅
  - Authentication: ✅
  - Requisition submission: ✅
  - All tests passed: ✅
  **Completed:** ___________

---

### Post-Deployment Validation (8:00 AM - 9:00 AM UTC)

- [ ] **Metrics Review**
  ```bash
  # Check error rate
  # Expected: < 0.5%
  
  # Check latency
  # Expected: p95 < 2s
  
  # Check throughput
  # Expected: Baseline established
  ```
  **Status:** ___________  
  **Time:** ___________

- [ ] **Manual Testing**
  - [ ] Submit requisition via API
  - [ ] Verify match results returned
  - [ ] Update availability
  - [ ] Check audit logs
  **Tested By:** ___________  
  **Time:** ___________

- [ ] **Monitoring Dashboard Check**
  - [ ] CloudWatch dashboard - all green
  - [ ] Grafana dashboard - metrics flowing
  - [ ] No critical alerts firing
  **Verified By:** ___________  
  **Time:** ___________

- [ ] **Status Page Updated**
  - Posted: "Deployment complete, monitoring"
  **Posted By:** ___________  
  **Time:** ___________

---

## Phase 3: Extended Monitoring (8 hours)

- [ ] **Hour 1-4 Monitoring**
  - Error rate stable: ___________
  - Latency within SLO: ___________
  - No pod restarts: ___________
  - Database performance normal: ___________

- [ ] **Hour 4-8 Monitoring**
  - Continued stability: ___________
  - User feedback: ___________
  - Performance baseline captured: ___________

- [ ] **Status Page Updated**
  - Posted: "Deployment successful, operating normally"
  **Posted By:** ___________  
  **Time:** ___________

---

## Phase 4: 24-Hour Review (Next Day)

- [ ] **Metrics Review**
  - 24-hour uptime: ___________%
  - Average latency: ___________
  - Total requests: ___________
  - Error count: ___________

- [ ] **Stakeholder Communication**
  - [ ] Email to executives (success)
  - [ ] Email to customers (completion)
  - [ ] Team Slack message
  **Sent By:** ___________  
  **Date:** ___________

- [ ] **Deployment Retrospective Scheduled**
  - Date: ___________
  - Time: ___________
  - Attendees: DevOps, Tech Lead, Engineering Team

---

## Rollback Criteria

**Immediate Rollback if:**
- [ ] Error rate > 5% for > 5 minutes
- [ ] Latency p95 > 10 seconds for > 5 minutes
- [ ] Critical functionality unavailable
- [ ] Database corruption detected
- [ ] Security breach suspected

**Rollback Procedure:** See [Production Deployment Runbook](production-deployment.md) Section: Emergency Rollback

**Rollback Decision Maker:** Tech Lead or DevOps Lead

---

## Go/No-Go Decision

**Date:** ___________  
**Time:** ___________

### Go/No-Go Criteria

| Criteria | Status | Notes |
|----------|--------|-------|
| All infrastructure provisioned | [ ] Go [ ] No-Go | |
| All secrets configured | [ ] Go [ ] No-Go | |
| Monitoring active | [ ] Go [ ] No-Go | |
| Team ready | [ ] Go [ ] No-Go | |
| No critical blockers | [ ] Go [ ] No-Go | |

### Decision

**Final Decision:** [ ] GO [ ] NO-GO

**Decided By:** ___________  
**Title:** ___________  
**Signature:** ___________  
**Date/Time:** ___________

---

## Sign-Off

### Deployment Team

| Role | Name | Signature | Date |
|------|------|-----------|------|
| DevOps Lead | | | |
| Tech Lead | | | |
| On-Call (Primary) | | | |
| Product Manager | | | |

### Executive Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| CTO | | | |

---

**Document Version:** 1.0  
**Last Updated:** February 8, 2026  
**Next Review:** After go-live (February 11, 2026)
