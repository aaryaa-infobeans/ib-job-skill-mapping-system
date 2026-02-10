# Operations Documentation Index

## Overview

This directory contains comprehensive operational documentation for the IB Job Skill Mapping System production environment.

---

## Quick Links

### Deployment & Operations
- **[Production Deployment Runbook](runbooks/production-deployment.md)** - Step-by-step deployment procedures
- **[Blue-Green Deployment Strategy](blue-green-deployment.md)** - Zero-downtime deployment approach
- **[Monitoring & Alerting](monitoring-alerting.md)** - System monitoring and alert configuration

### Incident Management
- **[Incident Response Procedures](runbooks/incident-response.md)** - How to respond to production incidents
- **[Service Level Agreement (SLA)](sla.md)** - Service commitments and targets
- **[On-Call Rotation Guide](oncall-rotation.md)** - On-call responsibilities and procedures

### Disaster Recovery
- **[Disaster Recovery Plan](disaster-recovery.md)** - DR strategy and failover procedures

### Local Development
- **[Local Development Setup](runbooks/local_dev.md)** - Setting up local environment

---

## Document Categories

### Runbooks

Operational procedures for common tasks:
- **[Production Deployment](runbooks/production-deployment.md)** - Deploy to production
- **[Incident Response](runbooks/incident-response.md)** - Handle incidents
- **[Local Development](runbooks/local_dev.md)** - Setup local environment

### Architecture

System architecture documentation:
- **[Architecture Overview](architecture/overview.md)** - High-level system design
- **[Blue-Green Deployment](blue-green-deployment.md)** - Deployment architecture

### Service Management

Service level commitments and procedures:
- **[Service Level Agreement](sla.md)** - 99.5% uptime SLA
- **[Monitoring & Alerting](monitoring-alerting.md)** - Observability stack
- **[Disaster Recovery](disaster-recovery.md)** - RTO < 4 hours, RPO < 5 minutes

### Team Processes

Team operational procedures:
- **[On-Call Rotation](oncall-rotation.md)** - 24/7 coverage model
- **[Incident Response](runbooks/incident-response.md)** - SEV-1 to SEV-4 handling

---

## Key Metrics

### Service Level Objectives (SLOs)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Availability** | 99.5% | Monthly uptime |
| **Latency (p95)** | < 2 seconds | API response time |
| **Latency (p99)** | < 5 seconds | API response time |
| **Throughput** | > 100 req/s | Sustained request rate |
| **Error Rate** | < 0.5% | 5xx errors + timeouts |
| **Data Durability** | 99.999% | Data loss protection |

### Recovery Objectives

| Objective | Target | Description |
|-----------|--------|-------------|
| **RTO** | < 4 hours | Recovery Time Objective |
| **RPO** | < 5 minutes | Recovery Point Objective |
| **Database Failover** | < 15 minutes | RDS Multi-AZ failover |
| **Rollback Time** | < 5 minutes | Blue-green deployment rollback |

---

## Quick Reference

### Emergency Contacts

| Role | Contact | When to Use |
|------|---------|-------------|
| **On-Call Engineer** | PagerDuty | All incidents |
| **Tech Lead** | See [Incident Response](runbooks/incident-response.md) | SEV-1, stuck on SEV-2 |
| **DevOps Lead** | See [Incident Response](runbooks/incident-response.md) | Infrastructure issues |
| **CTO** | See [Incident Response](runbooks/incident-response.md) | SEV-1 > 1 hour, security breach |

### Critical Links

- **Status Page:** https://status.infobeans.com
- **CloudWatch Dashboard:** https://console.aws.amazon.com/cloudwatch
- **Grafana:** http://grafana.infobeans.com
- **PagerDuty:** https://infobeans.pagerduty.com
- **GitHub Actions:** https://github.com/infobeans/ib-job-skill-mapping/actions

### Common Commands

```bash
# Check pod status
kubectl get pods -n production

# View recent logs
kubectl logs -l app=api-gateway -n production --tail=100

# Check deployment history
kubectl rollout history deployment/api-gateway-blue -n production

# Emergency rollback
kubectl patch service api-gateway -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Scale up
kubectl scale deployment api-gateway-blue --replicas=10 -n production

# Database connections
kubectl exec -it <pod-name> -n production -- \
  psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## Maintenance Windows

**Schedule:** 2nd Saturday of each month, 2:00-6:00 AM UTC

**Duration:** Up to 4 hours

**Notification:**
- Email: 7 days in advance
- Status page: 3 days in advance
- In-app: 24 hours in advance

---

## Document Maintenance

### Review Schedule

| Document | Review Frequency | Next Review | Owner |
|----------|-----------------|-------------|--------|
| Production Deployment | Quarterly | May 8, 2026 | DevOps |
| Incident Response | Quarterly | May 8, 2026 | DevOps |
| SLA | Quarterly | June 1, 2026 | Product + DevOps |
| On-Call Rotation | Quarterly | May 8, 2026 | DevOps |
| Disaster Recovery | Quarterly | May 8, 2026 | DevOps + CTO |
| Monitoring & Alerting | Monthly | March 8, 2026 | DevOps |

### Update Process

1. **Identify Need:** Runbook gap, process improvement, incident learnings
2. **Draft Update:** Create branch, update documentation
3. **Review:** Team review via PR
4. **Approve:** Tech lead or DevOps lead approval
5. **Publish:** Merge to main, notify team in Slack
6. **Train:** Update training materials if needed

### Feedback

**Have feedback on these docs?**
- Create GitHub issue: https://github.com/infobeans/ib-job-skill-mapping/issues
- Slack: #devops channel
- Email: devops@infobeans.com

---

## Getting Started

### For New Team Members

**Week 1: Read & Understand**
1. Read [Architecture Overview](architecture/overview.md)
2. Review [SLA](sla.md) - understand commitments
3. Read [Monitoring & Alerting](monitoring-alerting.md)

**Week 2: Hands-On**
4. Setup [Local Development](runbooks/local_dev.md)
5. Shadow on-call engineer (see [On-Call Rotation](oncall-rotation.md))
6. Walk through [Production Deployment](runbooks/production-deployment.md)

**Week 3: Practice**
7. Complete [Incident Response](runbooks/incident-response.md) drill
8. Review monitoring dashboards
9. Practice rollback procedures

**Week 4: Certification**
10. Pass incident response quiz
11. Manager approval
12. Added to on-call rotation

### For On-Call Engineers

**Before First Shift:**
- [ ] Complete on-call training
- [ ] Shadow experienced on-call (1 week)
- [ ] Pass incident drill
- [ ] Verify all access (AWS, kubectl, PagerDuty, Grafana)
- [ ] Test phone notifications
- [ ] Review all runbooks
- [ ] Bookmark critical dashboards

**Essential Reading:**
- [On-Call Rotation Guide](oncall-rotation.md)
- [Incident Response Procedures](runbooks/incident-response.md)
- [Production Deployment Runbook](runbooks/production-deployment.md)

---

## Compliance & Auditing

### Standards

- **SOC 2 Type II:** Annual audit
- **GDPR:** Data protection compliance
- **ISO 27001:** Information security management

### Audit Trail

All production changes require:
- Change request (JIRA ticket)
- Peer review (GitHub PR approval)
- Approval (tech lead or DevOps lead)
- Documentation update (if procedure changed)
- Audit log entry (automatic via CloudWatch)

### Data Retention

| Data Type | Retention | Location |
|-----------|-----------|----------|
| **Audit Logs** | 7 years | S3 |
| **Database Backups** | 30 days | RDS + S3 |
| **CloudWatch Logs** | 30 days | CloudWatch + S3 |
| **Incident Reports** | 3 years | Git + Wiki |
| **Metrics** | 90 days | Prometheus + Grafana Cloud |

---

## Training Resources

### Internal Training

- **On-Call Orientation:** 2 hours, quarterly
- **Incident Response Workshop:** 2 hours, quarterly
- **DR Drill:** 4-8 hours, biannually
- **Lunch & Learn:** Monthly DevOps topics

### External Resources

- **AWS Well-Architected Framework:** https://aws.amazon.com/architecture/well-architected/
- **Google SRE Book:** https://sre.google/books/
- **Kubernetes Best Practices:** https://kubernetes.io/docs/concepts/
- **DORA Metrics:** https://cloud.google.com/blog/products/devops-sre/using-the-four-keys-to-measure-your-devops-performance

---

## Glossary

**ALB:** Application Load Balancer (AWS)  
**AZ:** Availability Zone (AWS data center)  
**DR:** Disaster Recovery  
**EKS:** Elastic Kubernetes Service (AWS)  
**HPA:** Horizontal Pod Autoscaler (Kubernetes)  
**IRSA:** IAM Roles for Service Accounts (EKS)  
**PDB:** Pod Disruption Budget (Kubernetes)  
**RDS:** Relational Database Service (AWS)  
**RPO:** Recovery Point Objective (acceptable data loss)  
**RTO:** Recovery Time Objective (acceptable downtime)  
**SEV-1:** Severity 1 incident (critical, complete outage)  
**SEV-2:** Severity 2 incident (high, major degradation)  
**SLA:** Service Level Agreement (contractual commitment)  
**SLI:** Service Level Indicator (measured metric)  
**SLO:** Service Level Objective (internal target)

---

**Last Updated:** February 8, 2026  
**Maintained By:** DevOps Team  
**Contact:** devops@infobeans.com
