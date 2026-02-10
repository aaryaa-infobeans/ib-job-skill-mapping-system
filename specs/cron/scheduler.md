# Scheduler Configuration - Nightly Batch Ingestion Service

**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Owner:** Platform Engineering

---

## 1. Overview

This document defines the scheduling configuration for the nightly batch ingestion service. The service runs daily at 2:00 AM IST using either traditional Cron (bare metal/VM) or Kubernetes CronJob (containerized).

---

## 2. Schedule Requirements

### 2.1 Execution Time

```
Schedule: 2:00 AM IST (UTC+5:30)
Frequency: Daily
Duration: Target < 30 minutes
Max Duration: 2 hours (before next run)
```

### 2.2 Time Zone Handling

```python
# Convert IST to UTC for Cron
# 2:00 AM IST = 8:30 PM UTC (previous day)

import pytz
from datetime import datetime

IST = pytz.timezone("Asia/Kolkata")
UTC = pytz.UTC

def get_utc_cron_schedule():
    """Calculate UTC time for 2:00 AM IST."""
    ist_time = IST.localize(datetime.now().replace(hour=2, minute=0, second=0))
    utc_time = ist_time.astimezone(UTC)
    return f"{utc_time.minute} {utc_time.hour} * * *"

# Result: "30 20 * * *" (8:30 PM UTC daily)
```

---

## 3. Traditional Cron Setup

### 3.1 Crontab Configuration

```bash
# /etc/cron.d/ib-job-skill-ingestion

# Environment variables
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
PYTHONPATH=/opt/ib-job-skill-mapping-system/src

# Database credentials (sourced from secrets file)
DB_HOST=localhost
DB_PORT=5433
DB_NAME=ib_job_skill_mapping
DB_USER=postgres
DB_PASSWORD_FILE=/opt/secrets/db_password

# External API credentials
API_CLIENT_ID_FILE=/opt/secrets/api_client_id
API_CLIENT_SECRET_FILE=/opt/secrets/api_client_secret

# Logging
LOG_DIR=/var/log/ib-job-skill-ingestion
MAILTO=platform-team@company.com

# Schedule: 2:00 AM IST = 8:30 PM UTC daily
30 20 * * * app python3 /opt/ib-job-skill-mapping-system/src/app/ingest_team_data.py >> ${LOG_DIR}/ingestion-$(date +\%Y\%m\%d).log 2>&1
```

### 3.2 Installation Script

```bash
#!/bin/bash
# install_cron.sh

set -e

INSTALL_DIR=/opt/ib-job-skill-mapping-system
LOG_DIR=/var/log/ib-job-skill-ingestion
SECRETS_DIR=/opt/secrets

echo "Installing nightly batch ingestion cron job..."

# Create directories
sudo mkdir -p ${INSTALL_DIR}
sudo mkdir -p ${LOG_DIR}
sudo mkdir -p ${SECRETS_DIR}
sudo chown app:app ${LOG_DIR}
sudo chmod 750 ${LOG_DIR}

# Copy cron configuration
sudo cp cron.d/ib-job-skill-ingestion /etc/cron.d/
sudo chmod 644 /etc/cron.d/ib-job-skill-ingestion

# Validate crontab syntax
sudo crontab -l -u app

# Store secrets (replace with actual secret management)
echo "${DB_PASSWORD}" | sudo tee ${SECRETS_DIR}/db_password > /dev/null
echo "${API_CLIENT_ID}" | sudo tee ${SECRETS_DIR}/api_client_id > /dev/null
echo "${API_CLIENT_SECRET}" | sudo tee ${SECRETS_DIR}/api_client_secret > /dev/null
sudo chmod 400 ${SECRETS_DIR}/*
sudo chown app:app ${SECRETS_DIR}/*

# Test cron job manually
sudo -u app python3 ${INSTALL_DIR}/src/app/ingest_team_data.py --dry-run

echo "✓ Cron job installed successfully"
echo "Next run: $(grep 'ib-job-skill-ingestion' /etc/cron.d/ib-job-skill-ingestion | awk '{print $1, $2, $3, $4, $5}')"
```

### 3.3 Log Rotation

```bash
# /etc/logrotate.d/ib-job-skill-ingestion

/var/log/ib-job-skill-ingestion/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0640 app app
}
```

---

## 4. Kubernetes CronJob (Recommended)

### 4.1 CronJob Manifest

```yaml
# k8s/cronjob-ingestion.yaml

apiVersion: batch/v1
kind: CronJob
metadata:
  name: team-data-ingestion
  namespace: ib-job-skill-mapping
  labels:
    app: team-data-ingestion
    version: v1.0.0
spec:
  # Schedule: 2:00 AM IST = 8:30 PM UTC
  schedule: "30 20 * * *"
  timeZone: "UTC"  # Explicitly set to UTC
  
  # Concurrency control
  concurrencyPolicy: Forbid  # Prevent overlapping runs
  
  # History limits
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 5
  
  # Job deadline
  startingDeadlineSeconds: 300  # Start within 5 minutes of schedule
  
  jobTemplate:
    metadata:
      labels:
        app: team-data-ingestion
    spec:
      # Job timeout
      activeDeadlineSeconds: 7200  # 2 hours max
      
      # Retry policy
      backoffLimit: 0  # No automatic retries (handled by batch processor)
      
      template:
        metadata:
          labels:
            app: team-data-ingestion
        spec:
          restartPolicy: Never
          
          serviceAccountName: team-data-ingestion-sa
          
          # Security context
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            fsGroup: 1000
          
          containers:
          - name: ingestion
            image: company-registry.io/ib-job-skill-mapping/ingestion:v1.0.0
            imagePullPolicy: IfNotPresent
            
            command:
              - python3
              - /app/ingest_team_data.py
            
            env:
              # Database configuration
              - name: DB_HOST
                valueFrom:
                  secretKeyRef:
                    name: postgres-secret
                    key: host
              - name: DB_PORT
                valueFrom:
                  secretKeyRef:
                    name: postgres-secret
                    key: port
              - name: DB_NAME
                valueFrom:
                  secretKeyRef:
                    name: postgres-secret
                    key: database
              - name: DB_USER
                valueFrom:
                  secretKeyRef:
                    name: postgres-secret
                    key: username
              - name: DB_PASSWORD
                valueFrom:
                  secretKeyRef:
                    name: postgres-secret
                    key: password
              
              # External API configuration
              - name: API_BASE_URL
                valueFrom:
                  configMapKeyRef:
                    name: ingestion-config
                    key: api_base_url
              - name: API_CLIENT_ID
                valueFrom:
                  secretKeyRef:
                    name: external-api-secret
                    key: client_id
              - name: API_CLIENT_SECRET
                valueFrom:
                  secretKeyRef:
                    name: external-api-secret
                    key: client_secret
              
              # Application configuration
              - name: LOG_LEVEL
                value: "INFO"
              - name: MAX_RETRIES
                value: "3"
              - name: BATCH_SIZE
                value: "100"
            
            resources:
              requests:
                memory: "512Mi"
                cpu: "500m"
              limits:
                memory: "2Gi"
                cpu: "1000m"
            
            # Health checks (liveness probe not needed for CronJob)
            # Readiness probe not applicable
            
            volumeMounts:
              - name: logs
                mountPath: /var/log/ingestion
          
          volumes:
            - name: logs
              emptyDir: {}
          
          # Image pull secrets
          imagePullSecrets:
            - name: company-registry-credentials

---
# Service Account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: team-data-ingestion-sa
  namespace: ib-job-skill-mapping

---
# Role for database access
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: team-data-ingestion-role
  namespace: ib-job-skill-mapping
rules:
  - apiGroups: [""]
    resources: ["secrets", "configmaps"]
    verbs: ["get", "list"]

---
# Role binding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: team-data-ingestion-rolebinding
  namespace: ib-job-skill-mapping
subjects:
  - kind: ServiceAccount
    name: team-data-ingestion-sa
    namespace: ib-job-skill-mapping
roleRef:
  kind: Role
  name: team-data-ingestion-role
  apiGroup: rbac.authorization.k8s.io
```

### 4.2 Secrets Management

```yaml
# k8s/secrets.yaml (sealed secrets in production)

---
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: ib-job-skill-mapping
type: Opaque
stringData:
  host: "postgres.database.svc.cluster.local"
  port: "5432"
  database: "ib_job_skill_mapping"
  username: "ingestion_user"
  password: "REPLACE_WITH_SEALED_SECRET"

---
apiVersion: v1
kind: Secret
metadata:
  name: external-api-secret
  namespace: ib-job-skill-mapping
type: Opaque
stringData:
  client_id: "REPLACE_WITH_SEALED_SECRET"
  client_secret: "REPLACE_WITH_SEALED_SECRET"
```

### 4.3 ConfigMap

```yaml
# k8s/configmap.yaml

apiVersion: v1
kind: ConfigMap
metadata:
  name: ingestion-config
  namespace: ib-job-skill-mapping
data:
  api_base_url: "https://api.external-system.com"
  token_endpoint: "https://auth.external-system.com/oauth/token"
  max_retries: "3"
  batch_size: "100"
  timeout_seconds: "30"
```

### 4.4 Deployment Script

```bash
#!/bin/bash
# deploy_cronjob.sh

set -e

NAMESPACE=ib-job-skill-mapping
KUBE_CONTEXT=production-cluster

echo "Deploying team-data-ingestion CronJob..."

# Set context
kubectl config use-context ${KUBE_CONTEXT}

# Create namespace if not exists
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Apply secrets (use sealed secrets in production)
kubectl apply -f k8s/secrets.yaml

# Apply configmap
kubectl apply -f k8s/configmap.yaml

# Apply CronJob
kubectl apply -f k8s/cronjob-ingestion.yaml

# Verify deployment
kubectl get cronjob -n ${NAMESPACE}
kubectl describe cronjob team-data-ingestion -n ${NAMESPACE}

echo "✓ CronJob deployed successfully"
echo "Next scheduled run:"
kubectl get cronjob team-data-ingestion -n ${NAMESPACE} -o jsonpath='{.spec.schedule}'
```

---

## 5. Manual Execution

### 5.1 Traditional Cron - Manual Run

```bash
# Run as cron user
sudo -u app python3 /opt/ib-job-skill-mapping-system/src/app/ingest_team_data.py

# Dry run (validation only)
sudo -u app python3 /opt/ib-job-skill-mapping-system/src/app/ingest_team_data.py --dry-run

# Retry failed batches only
sudo -u app python3 /opt/ib-job-skill-mapping-system/src/app/ingest_team_data.py --retry-failed
```

### 5.2 Kubernetes - Manual Job Creation

```bash
# Create Job from CronJob immediately
kubectl create job --from=cronjob/team-data-ingestion manual-ingestion-$(date +%Y%m%d-%H%M%S) -n ib-job-skill-mapping

# Watch job progress
kubectl get jobs -n ib-job-skill-mapping -w

# View logs
kubectl logs -n ib-job-skill-mapping -l app=team-data-ingestion --tail=100 -f

# Retry failed batches (create job with flag)
kubectl create job --from=cronjob/team-data-ingestion retry-failed-$(date +%Y%m%d-%H%M%S) -n ib-job-skill-mapping
kubectl set env job/retry-failed-* RETRY_FAILED=true -n ib-job-skill-mapping
```

---

## 6. Monitoring and Alerts

### 6.1 CronJob Monitoring

```yaml
# Prometheus ServiceMonitor (if using Prometheus Operator)

apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: team-data-ingestion-monitor
  namespace: ib-job-skill-mapping
spec:
  selector:
    matchLabels:
      app: team-data-ingestion
  endpoints:
    - port: metrics
      interval: 30s
```

### 6.2 Alert Rules

```yaml
# PrometheusRule

apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: team-data-ingestion-alerts
  namespace: ib-job-skill-mapping
spec:
  groups:
    - name: ingestion_alerts
      interval: 1m
      rules:
        - alert: IngestionJobFailed
          expr: kube_job_status_failed{job_name=~"team-data-ingestion.*"} > 0
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Team data ingestion job failed"
            description: "CronJob {{ $labels.job_name }} has failed"
        
        - alert: IngestionJobNotRun
          expr: time() - kube_cronjob_status_last_schedule_time{cronjob="team-data-ingestion"} > 86400
          for: 1h
          labels:
            severity: warning
          annotations:
            summary: "Team data ingestion job has not run in 24 hours"
            description: "CronJob team-data-ingestion last ran {{ $value | humanizeDuration }} ago"
        
        - alert: IngestionJobTooLong
          expr: time() - kube_job_status_start_time{job_name=~"team-data-ingestion.*"} > 7200
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Team data ingestion job running too long"
            description: "Job {{ $labels.job_name }} has been running for {{ $value | humanizeDuration }}"
```

### 6.3 Dashboard Metrics

```python
# Metrics to track

from prometheus_client import Counter, Histogram, Gauge

ingestion_runs_total = Counter(
    "ingestion_runs_total",
    "Total number of ingestion runs",
    ["status"]  # success, failure
)

ingestion_duration_seconds = Histogram(
    "ingestion_duration_seconds",
    "Duration of ingestion run in seconds"
)

ingestion_batches_total = Counter(
    "ingestion_batches_total",
    "Total number of batches processed",
    ["status"]  # success, failed, abandoned
)

ingestion_records_total = Counter(
    "ingestion_records_total",
    "Total number of records processed"
)

ingestion_last_success_timestamp = Gauge(
    "ingestion_last_success_timestamp",
    "Timestamp of last successful ingestion"
)
```

---

## 7. Troubleshooting

### 7.1 Cron Not Running

```bash
# Check cron service status
sudo systemctl status cron

# Check cron logs
sudo grep CRON /var/log/syslog | tail -50

# Verify crontab syntax
sudo crontab -l -u app

# Test script manually
sudo -u app /bin/bash -c "source /etc/environment && python3 /opt/ib-job-skill-mapping-system/src/app/ingest_team_data.py --dry-run"
```

### 7.2 Kubernetes CronJob Issues

```bash
# Check CronJob configuration
kubectl get cronjob team-data-ingestion -n ib-job-skill-mapping -o yaml

# List recent jobs
kubectl get jobs -n ib-job-skill-mapping --sort-by=.status.startTime

# Check failed job logs
kubectl logs -n ib-job-skill-mapping -l app=team-data-ingestion --tail=200

# Describe failed job
kubectl describe job <job-name> -n ib-job-skill-mapping

# Check secrets
kubectl get secret postgres-secret -n ib-job-skill-mapping -o jsonpath='{.data}' | jq

# Force schedule
kubectl patch cronjob team-data-ingestion -n ib-job-skill-mapping -p '{"spec":{"schedule":"*/5 * * * *"}}'
```

### 7.3 Common Issues

| Issue | Diagnosis | Resolution |
|-------|-----------|------------|
| Job not scheduled | Check schedule syntax | Verify cron expression |
| Concurrency violation | Multiple jobs running | Set `concurrencyPolicy: Forbid` |
| Job timeout | Exceeds activeDeadlineSeconds | Increase limit or optimize processing |
| Permission denied | Secret access denied | Check ServiceAccount RBAC |
| OOM killed | Memory limit exceeded | Increase resources.limits.memory |

---

## 8. Definition of Done

- [ ] Cron schedule configured for 2:00 AM IST
- [ ] Kubernetes CronJob manifest created
- [ ] Secrets management implemented
- [ ] Log rotation configured
- [ ] Manual execution tested
- [ ] Monitoring dashboards created
- [ ] Alert rules deployed
- [ ] Runbook for troubleshooting
- [ ] Disaster recovery procedure documented

---

**Document Status:** Ready for Deployment  
**Next Steps:** Deploy CronJob to Kubernetes cluster and validate schedule
