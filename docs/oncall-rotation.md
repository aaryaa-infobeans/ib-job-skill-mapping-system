# On-Call Rotation Guide

## Overview

This document defines the on-call rotation system for the IB Job Skill Mapping System production environment.

**Purpose:** Ensure 24/7 coverage for production incidents while maintaining work-life balance.

---

## On-Call Schedule

### Rotation Schedule

**Primary On-Call:**
- **Duration:** 1 week (Monday 9 AM to Monday 9 AM)
- **Rotation:** Weekly rotation through engineering team
- **Minimum Pool Size:** 6 engineers

**Backup On-Call:**
- **Duration:** 1 week (same as primary)
- **Role:** Second responder if primary unavailable or needs help
- **Rotation:** Alternates with different engineer than primary

### Sample 6-Week Rotation

| Week | Primary On-Call | Backup On-Call |
|------|----------------|----------------|
| 1 | Alice | Bob |
| 2 | Charlie | Diana |
| 3 | Eve | Frank |
| 4 | Bob | Alice |
| 5 | Diana | Charlie |
| 6 | Frank | Eve |

**Schedule Tool:** PagerDuty (auto-rotation configured)

---

## On-Call Responsibilities

### Primary On-Call Engineer

**Core Duties:**
1. **Incident Response**
   - Respond to pages within 5 minutes (SEV-1/SEV-2)
   - Acknowledge alerts in PagerDuty
   - Triage and resolve incidents
   - Escalate if needed

2. **Monitoring**
   - Review dashboards daily
   - Check alert noise and false positives
   - Verify backup systems operational

3. **Communication**
   - Post updates in #incidents Slack channel
   - Update status page during incidents
   - Send stakeholder notifications (SEV-1/SEV-2)

4. **Documentation**
   - Create incident reports
   - Update runbooks if gaps found
   - Log all actions taken

5. **Handoff**
   - Conduct handoff meeting with next on-call
   - Document ongoing issues
   - Share lessons learned

**Expected Time Commitment:**
- **Business Hours:** Responsive to pages (5 min)
- **After Hours:** Phone within reach, respond within 15 min
- **Weekends:** Same as after hours

**Compensation:**
- On-call stipend: $X per week
- Overtime pay for incident response (>1 hour)
- Comp time for weekend incidents (>2 hours)

---

### Backup On-Call Engineer

**Core Duties:**
1. **Escalation Response**
   - Available if primary unreachable (>15 minutes)
   - Join war room for SEV-1 incidents
   - Provide second opinion on complex issues

2. **Support**
   - Review incident updates
   - Offer assistance if needed
   - Cover if primary takes break during long incident

**Expected Time Commitment:**
- **Business Hours:** Available if escalated
- **After Hours:** Phone accessible, respond within 30 min
- **Weekends:** Same as after hours

**Compensation:**
- On-call stipend: $Y per week (50% of primary)
- Overtime pay if actively responding

---

## On-Call Prerequisites

### Required Skills

**Technical:**
- [ ] Kubernetes basics (kubectl commands)
- [ ] AWS fundamentals (RDS, EKS, CloudWatch)
- [ ] Database troubleshooting (PostgreSQL)
- [ ] Application architecture understanding
- [ ] Git and GitHub Actions
- [ ] Linux command line

**Soft Skills:**
- [ ] Remain calm under pressure
- [ ] Clear communication
- [ ] Decision-making ability
- [ ] Time management

### Required Access

**Before First Shift:**
- [ ] AWS Console access (production read, limited write)
- [ ] kubectl access (production namespace)
- [ ] PagerDuty account configured
- [ ] Grafana access
- [ ] GitHub write access (for rollbacks)
- [ ] Slack #incidents channel
- [ ] VPN access (if working remotely)

**Test Access:**
```bash
# Verify AWS access
aws sts get-caller-identity

# Verify kubectl access
kubectl get pods -n production

# Verify Grafana access
curl -u $GRAFANA_USER:$GRAFANA_PASSWORD https://grafana.infobeans.com/api/health
```

---

### Required Training

**Mandatory Training (Before First Shift):**
1. **On-Call Orientation** (2 hours)
   - Review runbooks and procedures
   - Walkthrough of monitoring tools
   - Practice incident response

2. **Shadow Shift** (1 week)
   - Shadow experienced on-call engineer
   - Observe incident response
   - Ask questions and take notes

3. **Incident Drill** (1 hour)
   - Simulated incident exercise
   - Practice using runbooks
   - Communication practice

4. **Tool Training**
   - PagerDuty (30 min)
   - CloudWatch/Grafana (1 hour)
   - kubectl/K8s (1 hour)
   - Rollback procedures (30 min)

**Certification:**
- [ ] Complete all training modules
- [ ] Pass incident drill successfully
- [ ] Manager approval
- [ ] Added to PagerDuty rotation

---

## Daily Routine

### Start of Shift (Monday 9 AM)

**Handoff Meeting (30 minutes):**
1. **Previous On-Call Reports:**
   - Incidents that occurred
   - Ongoing issues
   - False alarms to be fixed
   - Action items

2. **System Status Review:**
   - Check CloudWatch dashboard
   - Review Grafana system overview
   - Verify all services healthy
   - Check scheduled maintenance

3. **Q&A:**
   - Ask clarifying questions
   - Review any unclear runbooks
   - Get contact info for escalation

**Post-Handoff:**
- [ ] Review PagerDuty schedule (confirm dates)
- [ ] Test phone notifications
- [ ] Bookmark key dashboards
- [ ] Read any updated runbooks
- [ ] Post in #oncall: "On-call this week, reach me @username"

---

### Daily Check-In (15 minutes)

**Perform Daily (10 AM):**
1. **Dashboard Review:**
   ```bash
   # Quick health check
   kubectl get pods -n production
   kubectl get nodes
   kubectl top nodes
   ```

2. **Metrics Review:**
   - Availability: Target 99.5%+
   - Error rate: Target < 0.5%
   - Latency p95: Target < 2s
   - No critical alerts firing

3. **Alert Review:**
   - Check PagerDuty for suppressed alerts
   - Review false positives
   - Create tickets for alert tuning

4. **Capacity Review:**
   - Database connections: < 80
   - CPU usage: < 70%
   - Memory usage: < 80%
   - Disk space: > 20% free

**Document Issues:**
- Post in #oncall channel if concerns
- Create JIRA tickets for non-urgent issues
- Update runbooks if needed

---

### End of Shift (Next Monday 9 AM)

**Handoff Preparation (1 hour before):**
1. **Create Handoff Document:**
   ```markdown
   # On-Call Handoff - Week of [Date]
   
   ## Incidents
   - [List all incidents with severity, resolution time]
   
   ## Ongoing Issues
   - [Any unresolved problems]
   
   ## False Alarms
   - [Alerts that need tuning]
   
   ## Action Items
   - JIRA-1234: Fix alert threshold (assigned to: Alice)
   - JIRA-1235: Update runbook (assigned to: Bob)
   
   ## Notes
   - [Any other important information]
   
   ## Statistics
   - Total incidents: X
   - SEV-1: Y
   - SEV-2: Z
   - Average response time: N minutes
   - Total time spent: H hours
   ```

2. **System Check:**
   - Verify all systems healthy
   - No critical alerts
   - No ongoing incidents

3. **Handoff Meeting:**
   - Meet with next on-call engineer
   - Walk through handoff document
   - Answer questions
   - Confirm understanding

**Post-Shift:**
- [ ] Submit timesheet for overtime (if any)
- [ ] Update personal notes/lessons learned
- [ ] Provide feedback on runbooks to team
- [ ] Take rest day if multiple incidents occurred

---

## Incident Response

### When Alert Fires

**Step 1: Acknowledge (< 2 minutes)**
1. PagerDuty notification received (phone, SMS, email)
2. Open PagerDuty app or web
3. Click "Acknowledge" on incident
4. Note time and alert name

**Step 2: Initial Assessment (< 3 minutes)**
1. Open CloudWatch dashboard
2. Check Grafana system overview
3. Quick pod check: `kubectl get pods -n production`
4. Determine severity (SEV-1 to SEV-4)

**Step 3: Communication (< 5 minutes)**
1. Post in #incidents Slack:
   ```
   🚨 **INCIDENT: [Severity] - [Title]**
   **Status:** Investigating
   **Impact:** [Brief description]
   **On-Call:** @your-username
   ```

2. For SEV-1: Page backup on-call and tech lead

**Step 4: Investigation (5-30 minutes)**
1. Follow relevant runbook
2. Check logs: `kubectl logs -l app=api-gateway --tail=100`
3. Identify root cause
4. Post updates every 15 minutes (SEV-1) or 30 min (SEV-2)

**Step 5: Mitigation**
1. Apply fix (rollback, restart, scale, etc.)
2. Verify resolution
3. Monitor for 30 minutes

**Step 6: Resolution**
1. Post resolution in #incidents
2. Update PagerDuty: "Resolved"
3. Create incident report (within 24 hours)

---

## Escalation

### When to Escalate

**Escalate to Backup On-Call if:**
- Unable to access systems
- Unclear on how to proceed (after 15 minutes)
- Need second opinion on risky action
- Multiple simultaneous incidents

**Escalate to Tech Lead if:**
- SEV-1 incident
- Unable to resolve SEV-2 within 1 hour
- Need approval for major change (e.g., full rollback)
- Security incident suspected

**Escalate to DevOps Lead if:**
- Infrastructure-level issue (AWS outage)
- Database failure requiring AWS support
- Network/VPC issues

**Escalate to CTO if:**
- SEV-1 lasting > 1 hour
- Data breach suspected
- Need executive decision (e.g., take service offline)

### How to Escalate

**PagerDuty:**
1. Open incident
2. Click "Escalate"
3. Select escalation policy
4. Add note explaining reason

**Phone/Slack:**
- Use emergency contact list
- Send message: "Escalating [incident] due to [reason]"
- Provide incident link and summary

---

## Tools and Resources

### Quick Links

**Dashboards:**
- CloudWatch: https://console.aws.amazon.com/cloudwatch
- Grafana: http://grafana.infobeans.com
- PagerDuty: https://infobeans.pagerduty.com

**Documentation:**
- Runbooks: https://github.com/infobeans/ib-job-skill-mapping/wiki/runbooks
- Architecture: https://github.com/infobeans/ib-job-skill-mapping/wiki/architecture
- SLA: https://github.com/infobeans/ib-job-skill-mapping/blob/main/docs/sla.md

**Communication:**
- Slack #incidents: https://infobeans.slack.com/archives/incidents
- Slack #oncall: https://infobeans.slack.com/archives/oncall
- Status Page: https://status.infobeans.com

### Command Cheat Sheet

```bash
# Check pod status
kubectl get pods -n production
kubectl describe pod <pod-name> -n production
kubectl logs -f <pod-name> -n production

# Check deployments
kubectl get deployments -n production
kubectl rollout history deployment/api-gateway-blue -n production
kubectl rollout status deployment/api-gateway-blue -n production

# Scale resources
kubectl scale deployment api-gateway-blue --replicas=5 -n production

# Check nodes
kubectl get nodes
kubectl top nodes
kubectl describe node <node-name>

# Check services
kubectl get svc -n production
kubectl get endpoints api-gateway -n production

# Rollback
kubectl patch service api-gateway -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Database check
kubectl run psql --rm -it --restart=Never \
  --image=postgres:15 \
  --env="PGPASSWORD=$DB_PASSWORD" \
  -- psql -h $DB_HOST -U postgres -d ib_job_skill_mapping \
  -c "SELECT count(*) FROM pg_stat_activity WHERE state='active';"

# Logs query
kubectl logs -l app=api-gateway -n production --since=10m | grep ERROR
```

---

## Best Practices

### Do's ✅

- **Acknowledge alerts within 5 minutes**
- **Communicate early and often** (status updates)
- **Follow runbooks** (don't improvise)
- **Ask for help** if unsure (within 15 minutes)
- **Document actions** taken
- **Take breaks** during long incidents
- **Test changes** in staging first (if time permits)
- **Verify resolution** before closing incident

### Don'ts ❌

- **Don't ignore alerts** (even false positives - fix them)
- **Don't make risky changes** without approval (SEV-1)
- **Don't skip communication** (keep stakeholders informed)
- **Don't forget to update status page**
- **Don't work exhausted** (escalate if needed)
- **Don't blame others** (focus on resolution)
- **Don't skip post-incident reports**

---

## Work-Life Balance

### Boundaries

**During On-Call Week:**
- **Business Hours:** Normal work, responsive to pages
- **After Hours:** Phone within reach, respond within 15 min
- **Sleep:** Aim for 7-8 hours, escalate if incident lasts past midnight
- **Weekends:** Light activities, stay near phone

**Coverage for Personal Events:**
- Swap shifts with teammate (coordinate via PagerDuty)
- Use backup on-call for short periods (< 4 hours)
- Request schedule change 2+ weeks in advance

### Self-Care

**During Incidents:**
- Take short breaks if incident > 2 hours
- Eat and stay hydrated
- Ask backup to monitor while you take 15-minute break

**After Difficult Shift:**
- Request comp day if multiple SEV-1 incidents
- Debrief with manager
- Share lessons learned with team

**Burnout Prevention:**
- Maximum 1 week per 6 weeks on-call
- No consecutive weeks
- Opt-out if experiencing burnout (talk to manager)

---

## Feedback and Improvement

### Weekly Retrospective

**Every Friday (end of week):**
- Review incidents handled
- Identify runbook gaps
- Suggest alert improvements
- Share lessons learned

**Post to #oncall:**
```
📊 On-Call Week Summary:
- Incidents: X (SEV-1: Y, SEV-2: Z)
- Avg Response Time: N minutes
- Lessons Learned: [brief notes]
- Runbook Updates: JIRA-XXXX
- Alert Improvements: JIRA-YYYY
```

### Rotation Feedback

**Monthly On-Call Sync (all on-call engineers):**
- Share experiences
- Discuss challenging incidents
- Propose process improvements
- Update documentation

**Annual Review:**
- Compensation review
- Rotation size adjustment
- Tool improvements
- Training updates

---

## FAQ

**Q: What if I miss a page?**
A: Backup on-call automatically paged after 15 minutes. Respond ASAP and explain in handoff.

**Q: Can I swap shifts?**
A: Yes, coordinate with another engineer and update in PagerDuty. Must be approved 48 hours in advance.

**Q: What if I'm sick during my shift?**
A: Notify manager immediately. Backup becomes primary, another engineer becomes backup.

**Q: Can I travel during on-call?**
A: Yes, if you have reliable internet and phone. Notify team of timezone. Consider swapping if international.

**Q: What if multiple alerts fire simultaneously?**
A: Triage by severity (SEV-1 first). Page backup to handle secondary incidents.

**Q: Do I get compensated for incident response?**
A: Yes. On-call stipend + overtime pay (if > 1 hour response) + comp time (if weekend > 2 hours).

**Q: What if I don't know how to fix an issue?**
A: Follow runbook. If stuck after 15 minutes, escalate. Don't guess.

**Q: Can I opt out of on-call?**
A: Temporarily yes (with reason). Long-term opt-out discuss with manager.

---

## Contact Information

**On-Call Coordinator:** oncall@infobeans.com  
**PagerDuty Admin:** pagerduty-admin@infobeans.com  
**Manager (On-Call Questions):** [Your Manager]  
**Tech Lead:** [Tech Lead Name]  
**DevOps Lead:** [DevOps Lead Name]

**Emergency Escalation:** See Incident Response procedures

---

**Document Version:** 1.0  
**Last Updated:** February 8, 2026  
**Next Review:** May 8, 2026  
**Owner:** DevOps Team
