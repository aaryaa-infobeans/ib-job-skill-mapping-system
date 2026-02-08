# Incident Response Procedures

## Overview

This document defines the incident response process for the IB Job Skill Mapping System production environment.

**Purpose:** Minimize downtime, ensure rapid response to production issues, and maintain service reliability.

**Scope:** All production incidents affecting availability, performance, or data integrity.

---

## Incident Severity Levels

### SEV-1: Critical (P0)

**Definition:** Complete service outage or critical functionality unavailable

**Examples:**
- API completely down (all requests failing)
- Database unavailable
- Data loss or corruption
- Security breach or unauthorized access
- Multiple critical systems failing

**Response Time:** Immediate (< 5 minutes)

**Response Team:**
- On-call engineer (primary)
- On-call backup
- Tech lead
- DevOps lead

**Notification:**
- PagerDuty: High-urgency page
- Slack: #incidents channel (mention @here)
- Email: executives, product team

**Resolution Target:** < 1 hour

---

### SEV-2: High (P1)

**Definition:** Major functionality degraded, significant user impact

**Examples:**
- API error rate > 5%
- Latency > 10 seconds
- One critical system failing (but service operational)
- Database performance severely degraded
- External dependency failure (LLM API, Microsoft Graph)

**Response Time:** < 15 minutes

**Response Team:**
- On-call engineer (primary)
- On-call backup (if needed)

**Notification:**
- PagerDuty: High-urgency page
- Slack: #incidents channel

**Resolution Target:** < 4 hours

---

### SEV-3: Medium (P2)

**Definition:** Minor functionality degraded, limited user impact

**Examples:**
- API error rate 1-5%
- Latency 5-10 seconds
- Non-critical feature unavailable
- Cache performance degraded
- Elevated resource usage

**Response Time:** < 30 minutes during business hours

**Response Team:**
- On-call engineer

**Notification:**
- Slack: #incidents channel
- Email: engineering team

**Resolution Target:** < 24 hours

---

### SEV-4: Low (P3)

**Definition:** Minimal user impact, cosmetic issues

**Examples:**
- Minor UI issues
- Non-critical logging errors
- Performance optimization opportunities
- Documentation issues

**Response Time:** Next business day

**Response Team:**
- Assigned during sprint planning

**Notification:**
- JIRA ticket creation

**Resolution Target:** Next sprint

---

## Incident Response Workflow

### Phase 1: Detection (0-5 minutes)

**Alert Sources:**
- CloudWatch Alarms → SNS → PagerDuty/Email
- Prometheus/Grafana Alerts → AlertManager → PagerDuty
- User reports → Support → On-call
- Uptime monitoring → PagerDuty
- Manual detection → Slack #incidents

**Initial Actions:**
1. **Acknowledge Alert** (< 2 minutes)
   - Acknowledge in PagerDuty
   - Post in Slack #incidents: "Investigating [alert name]"

2. **Quick Assessment** (< 3 minutes)
   - Check CloudWatch Dashboard
   - Check Grafana System Overview
   - Verify service status: `kubectl get pods -n production`
   - Check recent deployments: `kubectl rollout history`

3. **Determine Severity**
   - Use severity definitions above
   - Update Slack with severity: "SEV-2: API latency high"

---

### Phase 2: Triage (5-15 minutes)

**Objective:** Understand scope and impact

**Actions:**

1. **Assess Impact**
   ```bash
   # Check error rate
   aws cloudwatch get-metric-statistics \
     --namespace "IB-JobSkillMapping-Prod" \
     --metric-name "ErrorRate" \
     --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 60 --statistics Average
   
   # Check affected users (estimate)
   # Review logs for error patterns
   kubectl logs -l app=api-gateway -n production --since=10m | grep ERROR | wc -l
   ```

2. **Identify Root Cause** (initial hypothesis)
   - Recent deployment? → Check rollout history
   - External dependency? → Check LLM API, Graph API status
   - Database issue? → Check RDS performance metrics
   - Infrastructure issue? → Check EKS node health

3. **Page Additional Resources** (if SEV-1 or SEV-2)
   - Tech Lead (SEV-1 only)
   - Backup on-call (if primary needs help)
   - DevOps lead (infrastructure issues)

4. **Create Incident War Room**
   - Create Slack thread in #incidents
   - Start Zoom call (for SEV-1)
   - Document actions in thread

---

### Phase 3: Mitigation (15-60 minutes)

**Objective:** Restore service as quickly as possible

**Mitigation Strategies:**

#### Strategy 1: Rollback (Fastest - 5 minutes)

**When to use:**
- Recent deployment suspected
- No data migration issues
- Blue-green deployment available

**Procedure:**
```bash
# Switch traffic to green (previous version)
kubectl patch service api-gateway \
  -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Verify traffic switched
kubectl get endpoints api-gateway -n production

# Monitor metrics
# If successful, incident mitigated (proceed to Phase 4)
```

#### Strategy 2: Scale Resources (Moderate - 10 minutes)

**When to use:**
- High load causing issues
- Resource exhaustion (CPU, memory)
- Database connections maxed

**Procedure:**
```bash
# Scale up API pods
kubectl scale deployment api-gateway-blue --replicas=10 -n production

# Or scale EKS nodes
# Or scale RDS instance (requires ~15 minutes)
```

#### Strategy 3: Circuit Breaker Activation (Fast - 2 minutes)

**When to use:**
- External dependency failing
- Cascading failures

**Procedure:**
```bash
# Enable circuit breaker via feature flag
# Gracefully degrade functionality
# Serve cached responses

# Update feature flag in ConfigMap
kubectl edit configmap app-config -n production
# Set: circuit_breaker_enabled: "true"

# Restart pods to pick up config (rolling restart)
kubectl rollout restart deployment/api-gateway-blue -n production
```

#### Strategy 4: Database Failover (Moderate - 10 minutes)

**When to use:**
- Primary database unresponsive
- Read replica available

**Procedure:**
```bash
# Promote read replica to primary (AWS RDS)
aws rds promote-read-replica \
  --db-instance-identifier ib-job-skill-mapping-prod-db-replica

# Update application config with new endpoint
# (Automated via RDS multi-AZ if configured)
```

#### Strategy 5: Restart Pods (Fast - 3 minutes)

**When to use:**
- Memory leaks suspected
- Stale connections
- Unknown transient issue

**Procedure:**
```bash
# Rolling restart (zero-downtime)
kubectl rollout restart deployment/api-gateway-blue -n production

# Monitor pod startup
kubectl get pods -n production -w
```

---

### Phase 4: Verification (60-90 minutes)

**Objective:** Confirm service restored and stable

**Verification Checklist:**

1. **Service Health** (< 5 minutes)
   ```bash
   # Health check
   curl https://api.infobeans.com/health
   # Expected: {"status": "healthy"}
   
   # API smoke test
   curl -X POST https://api.infobeans.com/api/v1/auth/token \
     -H "Content-Type: application/json" \
     -d '{"grant_type": "client_credentials"}'
   # Expected: 200 OK with token
   ```

2. **Metrics Validation** (< 10 minutes)
   - Error rate < 0.5%
   - Latency p95 < 2 seconds
   - Throughput normal
   - All pods running
   - No pod restarts

3. **Extended Monitoring** (30 minutes)
   - Watch CloudWatch/Grafana dashboards
   - Monitor logs for errors
   - Check user reports
   - Verify SLO compliance

4. **Update Stakeholders**
   - Post in Slack #incidents: "Service restored, monitoring..."
   - Update PagerDuty incident: "Resolved"
   - Send status update email (for SEV-1/SEV-2)

---

### Phase 5: Resolution (Day 1-7)

**Objective:** Fix root cause, prevent recurrence

**Actions:**

1. **Root Cause Analysis** (Day 1)
   - Conduct RCA meeting (for SEV-1/SEV-2)
   - Attendees: On-call, tech lead, relevant engineers
   - Document findings in incident report

2. **Create Action Items**
   - File JIRA tickets for fixes
   - Assign owners and deadlines
   - Prioritize based on severity

3. **Implement Fixes** (Day 1-7)
   - Code changes
   - Configuration updates
   - Infrastructure improvements
   - Monitoring enhancements

4. **Update Documentation** (Day 1-3)
   - Update runbooks
   - Add new troubleshooting steps
   - Document lessons learned

5. **Conduct Post-Mortem** (Day 3-7, SEV-1/SEV-2 only)
   - Write post-mortem document
   - Share with team
   - Present findings to leadership (SEV-1 only)

---

## Communication Templates

### Initial Incident Notification (Slack)

```
🚨 **INCIDENT: SEV-2 - API Latency High**

**Status:** Investigating
**Start Time:** 2026-02-08 14:32 UTC
**Affected Service:** API Gateway
**Impact:** API response times elevated (p95: 8 seconds)
**Current Action:** Investigating database slow queries

**On-Call:** @john.doe
**War Room:** This thread

Updates will be posted here every 15 minutes.
```

### Status Update (Slack)

```
📊 **UPDATE (14:45 UTC):**

**Progress:** Mitigation in progress
**Action Taken:** 
- Identified slow query on requisitions table
- Added missing index
- Restarted database connection pool

**Current Status:**
- Latency dropping (p95: 3 seconds)
- Error rate stable (0.3%)
- Continuing to monitor

**Next Update:** 15:00 UTC
```

### Resolution Notification (Slack)

```
✅ **RESOLVED: SEV-2 - API Latency High**

**Resolution Time:** 14:52 UTC (20 minutes)
**Root Cause:** Missing index on requisitions.updated_at
**Mitigation:** Added index, restarted connection pool
**Impact:** Elevated latency for 20 minutes, no requests failed

**Action Items:**
- JIRA-1234: Add index to staging/dev environments
- JIRA-1235: Review all table indexes for optimization
- JIRA-1236: Update deployment checklist to verify indexes

**Post-Mortem:** Not required (SEV-3 or lower)

Thank you to @john.doe for quick response! 🎉
```

### Stakeholder Email (SEV-1/SEV-2)

```
Subject: [RESOLVED] Production Incident - API Latency Issue

Dear Team,

This email provides an update on the production incident that occurred today.

SUMMARY:
- Incident: API latency elevated above SLA
- Severity: SEV-2 (High)
- Start Time: 2026-02-08 14:32 UTC
- Resolution Time: 2026-02-08 14:52 UTC
- Duration: 20 minutes

IMPACT:
- API response times temporarily elevated (p95: 8 seconds vs SLA: 2 seconds)
- No data loss or security issues
- No user requests failed
- Estimated affected users: < 50

ROOT CAUSE:
- Missing database index on frequently queried column
- Recent data growth caused query performance degradation

RESOLUTION:
- Added missing index to database
- Restarted database connection pool
- Verified service restored to normal performance

PREVENTION:
- Reviewing all database indexes for optimization
- Adding index verification to deployment checklist
- Implementing proactive slow query monitoring

ACTION ITEMS:
- JIRA-1234: Add index to staging/dev (Owner: John Doe, Due: Feb 9)
- JIRA-1235: Full index review (Owner: Jane Smith, Due: Feb 15)
- JIRA-1236: Update deployment process (Owner: DevOps, Due: Feb 12)

Please contact devops@infobeans.com with any questions.

Best regards,
DevOps Team
```

---

## Escalation Matrix

### Level 1: On-Call Engineer
- **Responsibility:** First responder, triage, initial mitigation
- **Contact:** Via PagerDuty rotation
- **Escalates to:** Level 2 if unable to resolve in 30 minutes (SEV-1) or 2 hours (SEV-2)

### Level 2: On-Call Backup + Tech Lead
- **Responsibility:** Additional expertise, decision-making authority
- **Contact:** Via PagerDuty escalation policy
- **Escalates to:** Level 3 if unable to resolve in 1 hour (SEV-1)

### Level 3: DevOps Lead + CTO
- **Responsibility:** Executive decision-making, resource allocation
- **Contact:** Direct phone call
- **Authority:** Authorize emergency procedures (e.g., full rollback, AWS support engagement)

### External Escalation
- **AWS Support:** For infrastructure issues (RDS, EKS, networking)
- **Microsoft Support:** For Graph API issues
- **OpenAI/Anthropic Support:** For LLM API issues
- **PagerDuty Support:** For alerting/notification issues

---

## Tools and Access

### Required Access
- **AWS Console:** Read access minimum, admin for on-call
- **kubectl:** Production namespace access via RBAC
- **Grafana:** View and edit dashboards
- **PagerDuty:** Acknowledge, escalate incidents
- **GitHub:** Trigger rollback workflows
- **Slack:** #incidents channel

### Quick Links
- **CloudWatch Dashboard:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=ib-job-skill-mapping-prod-dashboard
- **Grafana System Overview:** http://grafana.infobeans.com/d/system-overview
- **PagerDuty:** https://infobeans.pagerduty.com
- **GitHub Actions:** https://github.com/infobeans/ib-job-skill-mapping/actions
- **Runbooks:** https://github.com/infobeans/ib-job-skill-mapping/wiki/runbooks

### Emergency Contacts
- **On-Call Primary:** See PagerDuty schedule
- **On-Call Backup:** See PagerDuty schedule
- **Tech Lead:** John Doe (john.doe@infobeans.com, +1-555-0101)
- **DevOps Lead:** Jane Smith (jane.smith@infobeans.com, +1-555-0102)
- **CTO:** Bob Johnson (bob.johnson@infobeans.com, +1-555-0100)

---

## Common Incident Scenarios

### Scenario 1: API Completely Down

**Symptoms:** All API requests returning 5xx or timing out

**Immediate Actions:**
1. Check pod status: `kubectl get pods -n production`
2. If pods down: Check recent deployments, consider rollback
3. If pods up: Check ALB health, DNS resolution
4. Check database connectivity
5. If unsure: Rollback to last known good version

**Typical Resolution Time:** 5-15 minutes (with rollback)

---

### Scenario 2: High Error Rate (5-20%)

**Symptoms:** Elevated 5xx responses, users reporting errors

**Immediate Actions:**
1. Check error logs: `kubectl logs -l app=api-gateway --tail=100`
2. Identify error pattern (database, LLM API, specific endpoint)
3. If database: Check slow queries, connections
4. If LLM API: Enable circuit breaker
5. If specific endpoint: Disable endpoint temporarily

**Typical Resolution Time:** 15-45 minutes

---

### Scenario 3: Database Connection Exhaustion

**Symptoms:** "Too many connections" errors in logs

**Immediate Actions:**
1. Check active connections in RDS
2. Identify connection leaks in application
3. Restart pods to reset connection pools
4. Scale RDS if needed
5. Investigate and fix connection leak

**Typical Resolution Time:** 10-30 minutes

---

### Scenario 4: Memory Leak / Pod OOMKilled

**Symptoms:** Pods restarting with OOMKilled status

**Immediate Actions:**
1. Check pod resource usage: `kubectl top pods -n production`
2. Increase memory limits temporarily
3. Restart pods more frequently
4. Profile application for memory leak
5. Deploy fix

**Typical Resolution Time:** 30 minutes (mitigation), days (permanent fix)

---

## Post-Incident Activities

### Incident Report Template

**File:** `docs/incidents/YYYY-MM-DD-incident-summary.md`

```markdown
# Incident Report: [Title]

**Date:** 2026-02-08
**Severity:** SEV-2
**Duration:** 20 minutes
**Affected Services:** API Gateway, Database

## Summary
Brief description of what happened and impact.

## Timeline (UTC)
- 14:32 - Alert fired: API latency high
- 14:34 - On-call acknowledged, began investigation
- 14:38 - Root cause identified: missing index
- 14:42 - Mitigation started: adding index
- 14:48 - Index created, connection pool restarted
- 14:52 - Service verified restored, incident resolved

## Root Cause
Detailed explanation of what caused the incident.

## Impact
- User Impact: < 50 users experienced slow responses
- Duration: 20 minutes
- Data Loss: None
- SLO Impact: Availability unaffected, latency SLO breached

## Resolution
What was done to resolve the incident.

## Lessons Learned
### What Went Well
- Quick detection via CloudWatch alarm
- Clear runbook guidance
- Fast mitigation with database index

### What Could Be Improved
- Index should have been added proactively
- Staging environment didn't catch this issue
- No alerting for slow queries

### Action Items
- [ ] JIRA-1234: Add index to all environments
- [ ] JIRA-1235: Review all indexes
- [ ] JIRA-1236: Add slow query alerting
- [ ] JIRA-1237: Improve staging data volume to match prod

## Prevention
How to prevent this from happening again.
```

### Post-Mortem Meeting (SEV-1/SEV-2)

**When:** Within 3 business days of incident
**Duration:** 60 minutes
**Attendees:** On-call, tech lead, relevant engineers, stakeholders

**Agenda:**
1. Incident timeline review (10 min)
2. Root cause analysis (20 min)
3. What went well (10 min)
4. What could be improved (10 min)
5. Action items review (10 min)

**Output:** Action items assigned with owners and deadlines

---

## Maintenance Windows

### Scheduled Maintenance

**When:** Every 2nd Saturday of the month, 2:00-6:00 AM UTC
**Purpose:** Infrastructure updates, database maintenance, dependency upgrades

**Notification:**
- Email to stakeholders: 7 days in advance
- Status page update: 3 days in advance
- Slack announcement: 1 day in advance

**Procedure:**
1. Create maintenance window in PagerDuty (suppress alerts)
2. Post status page update: "Scheduled Maintenance"
3. Execute maintenance tasks
4. Verify service restored
5. Close maintenance window
6. Post completion update

---

## Training and Preparedness

### On-Call Training

**Required for all on-call engineers:**
- Review all runbooks
- Complete incident response training
- Shadow experienced on-call engineer
- Conduct at least one practice incident drill

### Practice Drills

**Frequency:** Quarterly
**Format:** Simulated incidents with time pressure
**Scenarios:**
- API complete outage
- Database failure
- Security incident
- External dependency failure

**Objectives:**
- Test runbook accuracy
- Verify tool access
- Practice communication
- Identify gaps in procedures

---

**Document Version:** 1.0  
**Last Updated:** February 8, 2026  
**Next Review:** May 8, 2026  
**Owner:** DevOps Team
