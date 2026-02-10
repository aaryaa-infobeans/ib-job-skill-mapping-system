# Service Level Agreement (SLA)

## Overview

This document defines the Service Level Agreement for the IB Job Skill Mapping System production environment.

**Effective Date:** March 1, 2026  
**Review Period:** Quarterly  
**Owner:** DevOps Team / Product Management

---

## Service Description

**Service Name:** IB Job Skill Mapping System  
**Service Type:** Cloud-based API platform for job requisition matching  

**Core Functionality:**
- Job requisition submission and processing
- AI-powered skill matching and scoring
- Team member availability management
- Microsoft Graph integration for skill data
- Real-time matching recommendations

**Service Hours:** 24/7/365

---

## Service Level Objectives (SLOs)

### 1. Availability

**Definition:** Percentage of time the service is operational and accessible

**Target:** 99.5% monthly uptime

**Measurement:**
```
Availability = (Total Minutes - Downtime Minutes) / Total Minutes × 100
```

**Downtime Definition:**
- HTTP 5xx error rate > 50% for > 1 minute
- Complete service unavailability
- Planned maintenance excluded (with advance notice)

**Monitoring:** CloudWatch synthetic monitoring + health check endpoints

**Monthly Allowance:**
- 99.5% = 21.6 minutes downtime per month
- 99.5% = 4.38 hours downtime per year

**Measurement Period:** Calendar month (UTC)

---

### 2. API Response Time

**Definition:** Time from request received to response sent

**Targets:**
- **p50 (Median):** < 500 milliseconds
- **p95:** < 2 seconds
- **p99:** < 5 seconds

**Measurement:**
- Measured at application layer (not including network latency)
- Excludes requests > 30 seconds (counted as timeouts)
- Applies to all API endpoints except batch operations

**Monitoring:** Prometheus histogram metrics, CloudWatch custom metrics

---

### 3. Throughput

**Definition:** Number of requests the system can handle

**Target:** ≥ 100 requests per second sustained

**Peak Capacity:** 500 requests per second burst (5 minutes)

**Measurement:**
- Measured as successful requests per second
- Averaged over 5-minute intervals
- Excludes requests rejected due to rate limiting

**Monitoring:** Prometheus counter metrics

---

### 4. Error Rate

**Definition:** Percentage of requests resulting in errors

**Target:** < 0.5% (99.5% success rate)

**Error Definition:**
- HTTP 5xx responses
- Timeouts (> 30 seconds)
- Internal application errors

**Exclusions:**
- HTTP 4xx responses (client errors)
- Rate limit rejections (429)
- Authentication failures (401)

**Measurement:**
```
Error Rate = (5xx Responses + Timeouts) / Total Requests × 100
```

**Monitoring:** CloudWatch alarms, Prometheus alert rules

---

### 5. Data Durability

**Definition:** Protection against data loss

**Target:** 99.999% durability (five 9s)

**Scope:**
- Job requisitions and matches
- Team member availability data
- Skill mappings and scores
- Audit logs

**Protection Mechanisms:**
- RDS Multi-AZ automatic failover
- Automated daily backups (retained 30 days)
- Point-in-time recovery (up to 7 days)
- S3 backup storage (11 9s durability)

**Recovery Point Objective (RPO):** < 5 minutes  
**Recovery Time Objective (RTO):** < 15 minutes

---

### 6. Data Processing Time

**Definition:** Time from requisition submission to match results available

**Targets:**
- **Synchronous Match:** < 30 seconds (p95)
- **Async Match (Simple):** < 2 minutes (p95)
- **Async Match (Complex):** < 5 minutes (p95)

**Measurement:** LangGraph execution duration metrics

**Exclusions:**
- Bulk operations (separate SLA)
- External API delays (Microsoft Graph, LLM providers)

---

## Service Level Indicators (SLIs)

### Measurement Methods

**1. Synthetic Monitoring**
- Health check every 1 minute from 5 global locations
- Full API workflow test every 5 minutes
- Uptime measurement: successful checks / total checks

**2. Real User Monitoring**
- Request success rate from actual traffic
- Latency percentiles from application metrics
- Error rates from server logs

**3. Infrastructure Monitoring**
- Database availability and performance
- Cache availability and hit rate
- EKS cluster health and node availability

---

## Service Credits

### Credit Calculation

If monthly availability falls below 99.5%, customers are eligible for service credits:

| Monthly Availability | Service Credit |
|---------------------|----------------|
| 99.0% - 99.5%      | 10% of monthly fee |
| 98.0% - 99.0%      | 25% of monthly fee |
| < 98.0%            | 50% of monthly fee |

**Example Calculation:**
- Target: 99.5% (21.6 minutes downtime/month)
- Actual: 99.2% (34.6 minutes downtime/month)
- Result: 10% service credit

### Credit Exclusions

Service credits do NOT apply to downtime caused by:

1. **Scheduled Maintenance**
   - With 7+ days notice
   - During designated maintenance windows
   - Limited to 4 hours per month

2. **Customer Actions**
   - Incorrect API usage
   - Rate limit violations
   - Invalid authentication

3. **External Dependencies**
   - Microsoft Graph API outages
   - LLM provider (OpenAI, Anthropic) outages
   - AWS regional outages
   - Internet connectivity issues

4. **Force Majeure**
   - Natural disasters
   - Acts of terrorism
   - Government actions

5. **Security Incidents**
   - DDoS attacks
   - Unauthorized access attempts
   - Required security patches

### Credit Request Process

1. **Submit Request:**
   - Email: sla-claims@infobeans.com
   - Within 30 days of the incident
   - Include: Date, time, impact description

2. **Investigation:**
   - DevOps reviews monitoring data
   - Calculates actual downtime
   - Determines credit eligibility

3. **Resolution:**
   - Response within 10 business days
   - Credit applied to next invoice
   - Or refund if no future service

---

## Support Levels

### Standard Support (Included)

**Availability:** Business hours (9 AM - 5 PM local time, Monday-Friday)

**Response Times:**
- **SEV-1 (Critical):** 1 hour
- **SEV-2 (High):** 4 hours
- **SEV-3 (Medium):** 1 business day
- **SEV-4 (Low):** 3 business days

**Channels:**
- Email: support@infobeans.com
- Support portal: https://support.infobeans.com
- Slack: #support channel (for internal teams)

### Premium Support (Optional)

**Availability:** 24/7/365

**Response Times:**
- **SEV-1 (Critical):** 15 minutes
- **SEV-2 (High):** 1 hour
- **SEV-3 (Medium):** 4 hours
- **SEV-4 (Low):** 1 business day

**Additional Benefits:**
- Dedicated support engineer
- Direct phone line
- Proactive monitoring reviews
- Quarterly business reviews

**Channels:**
- All standard channels
- Direct phone: +1-555-PREMIUM
- Dedicated Slack channel

---

## Maintenance and Updates

### Planned Maintenance

**Schedule:** 2nd Saturday of each month, 2:00-6:00 AM UTC

**Maximum Duration:** 4 hours per month

**Notification:**
- Email: 7 days in advance
- Status page: 3 days in advance
- In-app notification: 24 hours in advance

**During Maintenance:**
- Service may be unavailable or degraded
- Read-only mode may be enabled
- Status page updated in real-time

### Emergency Maintenance

**Definition:** Unplanned maintenance for critical security or stability issues

**Notification:**
- Email and status page: As soon as possible
- Target: 1 hour advance notice (when safe)

**Impact:** Excluded from SLA calculations if duration < 1 hour

---

## Capacity Planning

### Current Capacity

**API Gateway:**
- 3-10 pods (auto-scaling)
- 100-500 requests/second capacity

**Database:**
- RDS db.r6g.xlarge (Multi-AZ)
- 100 max connections
- Auto-storage scaling to 1 TB

**Cache:**
- ElastiCache 2-node cluster
- 12 GB memory
- 50,000 ops/second capacity

### Scaling Triggers

**Automatic Scaling:**
- API pods: > 70% CPU or > 80% memory
- Database: > 80% storage
- Cache: > 75% memory

**Manual Scaling:**
- Anticipated traffic spikes
- Bulk operations scheduled
- New customer onboarding

### Capacity Review

**Frequency:** Monthly
**Participants:** DevOps, Product, Engineering
**Focus:** Usage trends, growth projections, optimization opportunities

---

## Monitoring and Reporting

### Real-Time Monitoring

**Public Status Page:** https://status.infobeans.com
- Current system status
- Incident history
- Scheduled maintenance

**Update Frequency:**
- Green status: Every 1 minute
- Incident: Real-time updates
- Maintenance: Every 30 minutes

### SLA Reports

**Monthly SLA Report:**
- Delivered: 5th business day of each month
- Contains:
  * Availability percentage
  * Performance metrics (p50, p95, p99)
  * Incident summary
  * Service credits (if applicable)
  * Comparison to previous month

**Available via:**
- Email to stakeholders
- Customer dashboard
- On request

### Metrics Dashboard

**Customer Dashboard:** https://dashboard.infobeans.com

**Real-Time Metrics:**
- Current system status
- Request rate and latency
- Error rate
- Recent incidents
- Upcoming maintenance

**Historical Data:** 90 days retained

---

## Roles and Responsibilities

### Service Provider (InfoBeans)

**Responsibilities:**
- Maintain service availability per SLA
- Monitor system health 24/7
- Respond to incidents within target times
- Perform scheduled maintenance
- Provide monthly SLA reports
- Process service credit requests

### Customer

**Responsibilities:**
- Use APIs according to documentation
- Report incidents promptly
- Provide valid authentication
- Maintain reasonable request rates
- Update applications for deprecated features

---

## Incident Communication

### Communication Channels

**Status Page:** https://status.infobeans.com
- Subscribe for email/SMS notifications
- RSS feed available

**Email Notifications:**
- Incident start
- Status updates (every 30 minutes)
- Incident resolution
- Post-mortem (for major incidents)

**Slack (Internal):**
- #incidents channel
- Real-time updates
- War room for critical incidents

### Incident Updates

**Frequency:**
- **SEV-1:** Every 15 minutes until resolved
- **SEV-2:** Every 30 minutes until resolved
- **SEV-3:** Every 2 hours until resolved

**Content:**
- Current status
- Actions taken
- Next steps
- Estimated resolution time (if known)

---

## SLA Review and Updates

### Review Schedule

**Quarterly Review:**
- Actual performance vs targets
- Customer feedback
- Industry benchmarks
- Adjustment recommendations

**Annual Review:**
- Comprehensive SLA revision
- New targets based on improvements
- Service offering updates

### Amendment Process

1. **Proposal:** DevOps/Product proposes changes
2. **Review:** Stakeholder review (2 weeks)
3. **Approval:** Leadership approval required
4. **Notification:** 30 days advance notice to customers
5. **Effective:** Changes take effect on specified date

### Version History

| Version | Date | Changes | Approved By |
|---------|------|---------|-------------|
| 1.0 | 2026-03-01 | Initial SLA | CTO |

---

## Compliance and Auditing

### Compliance Standards

- **SOC 2 Type II:** Annual audit
- **GDPR:** Data protection compliance
- **ISO 27001:** Information security management

### Audit Process

**Internal Audits:** Quarterly
- SLA metric accuracy
- Monitoring effectiveness
- Incident response adherence

**External Audits:** Annual
- Third-party verification
- Compliance certification
- Report provided to customers

---

## Definitions

**Availability:** Percentage of time service is accessible and functional

**Downtime:** Period when service is unavailable to users (>1 minute)

**Maintenance Window:** Scheduled period for updates and maintenance

**Incident:** Unplanned interruption or degradation of service

**Error Rate:** Percentage of requests resulting in 5xx errors or timeouts

**Latency:** Time from request receipt to response delivery

**p50/p95/p99:** 50th/95th/99th percentile of latency distribution

**Monthly Uptime:** Availability calculated over calendar month

---

## Contact Information

**SLA Questions:** sla@infobeans.com  
**Service Credits:** sla-claims@infobeans.com  
**Support:** support@infobeans.com  
**Status Page:** https://status.infobeans.com  

**Emergency Contact:** +1-555-SUPPORT (Premium support only)

---

**Document Version:** 1.0  
**Effective Date:** March 1, 2026  
**Next Review:** June 1, 2026  
**Owner:** Product Management & DevOps
