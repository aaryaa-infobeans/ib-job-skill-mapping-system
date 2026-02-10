# Error Handling & Observability - Nightly Batch Ingestion Service

**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Owner:** Platform Engineering

---

## 1. Overview

This document defines the error taxonomy, logging strategy, and observability framework for the nightly batch ingestion service.

---

## 2. Error Taxonomy

### 2.1 Error Categories

```python
from enum import Enum

class ErrorCategory(Enum):
    """Error classification for ingestion service."""
    
    # Retryable errors (transient)
    NETWORK_ERROR = "network_error"           # Timeout, connection refused
    API_RATE_LIMIT = "api_rate_limit"        # 429 Too Many Requests
    DATABASE_LOCK = "database_lock"           # Lock wait timeout
    TEMPORARY_UNAVAILABLE = "temporary_unavailable"  # 503 Service Unavailable
    
    # Non-retryable errors (permanent)
    AUTHENTICATION_ERROR = "authentication_error"  # 401 Unauthorized
    AUTHORIZATION_ERROR = "authorization_error"    # 403 Forbidden
    VALIDATION_ERROR = "validation_error"          # Invalid payload
    SCHEMA_MISMATCH = "schema_mismatch"           # Alembic version mismatch
    CONSTRAINT_VIOLATION = "constraint_violation"  # Foreign key violation
    
    # Infrastructure errors
    DATABASE_CONNECTION_ERROR = "database_connection_error"
    OUT_OF_MEMORY = "out_of_memory"
    DISK_FULL = "disk_full"


def classify_error(exception: Exception) -> ErrorCategory:
    """
    Classify exception into error category.
    
    Returns:
        ErrorCategory enum value
    """
    import requests
    from sqlalchemy.exc import OperationalError, IntegrityError
    
    # Network/API errors
    if isinstance(exception, requests.Timeout):
        return ErrorCategory.NETWORK_ERROR
    elif isinstance(exception, requests.ConnectionError):
        return ErrorCategory.NETWORK_ERROR
    elif isinstance(exception, requests.HTTPError):
        if exception.response.status_code == 429:
            return ErrorCategory.API_RATE_LIMIT
        elif exception.response.status_code == 401:
            return ErrorCategory.AUTHENTICATION_ERROR
        elif exception.response.status_code == 403:
            return ErrorCategory.AUTHORIZATION_ERROR
        elif exception.response.status_code == 503:
            return ErrorCategory.TEMPORARY_UNAVAILABLE
    
    # Database errors
    elif isinstance(exception, OperationalError):
        if "lock wait timeout" in str(exception).lower():
            return ErrorCategory.DATABASE_LOCK
        else:
            return ErrorCategory.DATABASE_CONNECTION_ERROR
    elif isinstance(exception, IntegrityError):
        return ErrorCategory.CONSTRAINT_VIOLATION
    
    # Validation errors
    elif isinstance(exception, ValueError):
        return ErrorCategory.VALIDATION_ERROR
    
    # Default: treat as temporary for retry
    return ErrorCategory.TEMPORARY_UNAVAILABLE


def is_retryable(error_category: ErrorCategory) -> bool:
    """Determine if error is retryable."""
    retryable_errors = {
        ErrorCategory.NETWORK_ERROR,
        ErrorCategory.API_RATE_LIMIT,
        ErrorCategory.DATABASE_LOCK,
        ErrorCategory.TEMPORARY_UNAVAILABLE
    }
    return error_category in retryable_errors
```

### 2.2 Exit Codes

```python
class ExitCode:
    """Exit codes for ingestion script."""
    
    SUCCESS = 0                  # All batches processed successfully
    PARTIAL_SUCCESS = 1          # Some batches failed (retryable)
    FATAL_ERROR = 2              # Non-retryable error occurred
    SCHEMA_VERSION_MISMATCH = 3  # Alembic version mismatch
    AUTHENTICATION_FAILED = 4    # OAuth authentication failed
    VALIDATION_FAILED = 5        # Payload validation failed


import sys

def exit_with_code(code: int, message: str):
    """Exit script with appropriate code."""
    print(f"Exit Code {code}: {message}")
    sys.exit(code)


# Usage
if not oauth_client.authenticate():
    exit_with_code(ExitCode.AUTHENTICATION_FAILED, "OAuth authentication failed")
```

---

## 3. Logging Strategy

### 3.1 Structured Logging

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """JSON structured logger for ingestion service."""
    
    def __init__(self, name: str, correlation_id: str):
        self.logger = logging.getLogger(name)
        self.correlation_id = correlation_id
    
    def _log(self, level: str, message: str, **kwargs):
        """Log structured message."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "correlation_id": self.correlation_id,
            "service": "team-data-ingestion",
            "message": message,
            **kwargs
        }
        self.logger.log(
            getattr(logging, level.upper()),
            json.dumps(log_entry)
        )
    
    def info(self, message: str, **kwargs):
        self._log("info", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("error", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("warning", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log("debug", message, **kwargs)


# Usage
logger = StructuredLogger("ingestion", correlation_id="ING-20260206-001")

logger.info(
    "Starting batch processing",
    batch_id="BATCH-001",
    total_records=150
)

logger.error(
    "Batch processing failed",
    batch_id="BATCH-001",
    error_category="network_error",
    retry_count=2,
    exception=str(exception)
)
```

### 3.2 Log Levels

```python
# Configure logging based on environment
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(message)s',  # Structured logger handles formatting
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"/var/log/ingestion/ingestion-{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
```

### 3.3 Key Log Events

```python
def log_ingestion_start(logger, correlation_id: str):
    """Log ingestion start event."""
    logger.info(
        "Ingestion started",
        event="ingestion_start",
        correlation_id=correlation_id
    )


def log_batch_processing(logger, batch_id: str, status: str, **kwargs):
    """Log batch processing event."""
    logger.info(
        f"Batch {status}",
        event="batch_processing",
        batch_id=batch_id,
        status=status,
        **kwargs
    )


def log_oauth_token_refresh(logger, expires_in: int):
    """Log OAuth token refresh."""
    logger.debug(
        "OAuth token refreshed",
        event="oauth_token_refresh",
        expires_in_seconds=expires_in
    )


def log_retry_attempt(logger, batch_id: str, retry_count: int, delay: int):
    """Log retry attempt."""
    logger.warning(
        "Retrying batch processing",
        event="batch_retry",
        batch_id=batch_id,
        retry_count=retry_count,
        delay_seconds=delay
    )


def log_ingestion_complete(logger, summary: dict):
    """Log ingestion completion."""
    logger.info(
        "Ingestion completed",
        event="ingestion_complete",
        **summary
    )
```

---

## 4. Audit Logging

### 4.1 Audit Log Schema

```sql
CREATE TABLE ingestion_audit_log (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id VARCHAR(50) NOT NULL,
    batch_id VARCHAR(100),
    event_type VARCHAR(50) NOT NULL,  -- 'ingestion_start', 'batch_success', 'batch_failed', etc.
    status VARCHAR(20) NOT NULL,      -- 'success', 'failed', 'retrying'
    error_category VARCHAR(50),
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_correlation_id (correlation_id),
    INDEX idx_batch_id (batch_id),
    INDEX idx_created_at (created_at)
);
```

### 4.2 Audit Logging Implementation

```python
from sqlalchemy import insert

def audit_log(
    conn,
    correlation_id: str,
    event_type: str,
    status: str,
    batch_id: str = None,
    error_category: str = None,
    error_message: str = None,
    metadata: dict = None
):
    """Insert audit log entry."""
    stmt = insert(ingestion_audit_log).values(
        correlation_id=correlation_id,
        batch_id=batch_id,
        event_type=event_type,
        status=status,
        error_category=error_category,
        error_message=error_message,
        metadata=metadata
    )
    conn.execute(stmt)


# Usage
with engine.begin() as conn:
    audit_log(
        conn,
        correlation_id="ING-20260206-001",
        event_type="batch_success",
        status="success",
        batch_id="BATCH-001",
        metadata={
            "records_processed": 150,
            "duration_ms": 5432
        }
    )
```

---

## 5. Metrics and Observability

### 5.1 Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Counters
ingestion_runs_total = Counter(
    "ingestion_runs_total",
    "Total number of ingestion runs",
    ["status"]
)

batches_processed_total = Counter(
    "batches_processed_total",
    "Total number of batches processed",
    ["status"]
)

records_processed_total = Counter(
    "records_processed_total",
    "Total number of records processed",
    ["table_name"]
)

api_requests_total = Counter(
    "api_requests_total",
    "Total number of external API requests",
    ["endpoint", "status_code"]
)

errors_total = Counter(
    "errors_total",
    "Total number of errors",
    ["error_category"]
)

# Histograms
ingestion_duration_seconds = Histogram(
    "ingestion_duration_seconds",
    "Duration of full ingestion run in seconds"
)

batch_duration_seconds = Histogram(
    "batch_duration_seconds",
    "Duration of batch processing in seconds"
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "Duration of external API requests in seconds",
    ["endpoint"]
)

# Gauges
ingestion_last_success_timestamp = Gauge(
    "ingestion_last_success_timestamp",
    "Timestamp of last successful ingestion"
)

pending_batches = Gauge(
    "pending_batches",
    "Number of pending batches"
)

failed_batches = Gauge(
    "failed_batches",
    "Number of failed batches awaiting retry"
)


# Usage
class InstrumentedIngestion:
    """Ingestion with Prometheus instrumentation."""
    
    def run(self):
        start_time = time.time()
        
        try:
            # Process batches
            for batch in self.get_batches():
                self.process_batch(batch)
                batches_processed_total.labels(status="success").inc()
            
            # Mark success
            ingestion_runs_total.labels(status="success").inc()
            ingestion_last_success_timestamp.set(time.time())
            
        except Exception as e:
            ingestion_runs_total.labels(status="failure").inc()
            errors_total.labels(error_category=classify_error(e).value).inc()
            raise
        
        finally:
            duration = time.time() - start_time
            ingestion_duration_seconds.observe(duration)


# Start metrics server
start_http_server(8000)  # Expose metrics on :8000/metrics
```

### 5.2 OpenTelemetry Tracing

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Configure tracer
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-agent",
    agent_port=6831
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

tracer = trace.get_tracer(__name__)


def process_batch_with_tracing(batch_id: str, team_members: list):
    """Process batch with distributed tracing."""
    with tracer.start_as_current_span("process_batch") as span:
        span.set_attribute("batch_id", batch_id)
        span.set_attribute("record_count", len(team_members))
        
        try:
            with tracer.start_as_current_span("database_transaction"):
                with engine.begin() as conn:
                    for member in team_members:
                        with tracer.start_as_current_span("upsert_team_member"):
                            upsert_team_member(conn, member)
            
            span.set_attribute("status", "success")
        
        except Exception as e:
            span.set_attribute("status", "failed")
            span.record_exception(e)
            raise
```

---

## 6. Alerting

### 6.1 Alert Definitions

```yaml
# Prometheus AlertManager rules

groups:
  - name: ingestion_alerts
    interval: 1m
    rules:
      - alert: IngestionJobFailed
        expr: ingestion_runs_total{status="failure"} > 0
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Nightly ingestion job failed"
          description: "Ingestion job failed with {{ $value }} failures"
          runbook_url: "https://wiki.company.com/runbooks/ingestion-failure"
      
      - alert: HighBatchFailureRate
        expr: rate(batches_processed_total{status="failed"}[5m]) > 0.2
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High batch failure rate detected"
          description: "{{ $value | humanizePercentage }} of batches are failing"
      
      - alert: IngestionNotRun
        expr: time() - ingestion_last_success_timestamp > 86400
        for: 1h
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Ingestion has not run successfully in 24 hours"
          description: "Last successful run was {{ $value | humanizeDuration }} ago"
      
      - alert: OAuthAuthenticationFailed
        expr: errors_total{error_category="authentication_error"} > 0
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "OAuth authentication failed"
          description: "Unable to authenticate with external API"
      
      - alert: DatabaseSchemaVersionMismatch
        expr: errors_total{error_category="schema_mismatch"} > 0
        for: 1m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Database schema version mismatch"
          description: "Alembic version mismatch detected - run migrations"
```

### 6.2 Alert Routing

```yaml
# AlertManager configuration

route:
  receiver: 'platform-team'
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true
    
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'platform-team'
    email_configs:
      - to: 'platform-team@company.com'
  
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<PAGERDUTY_SERVICE_KEY>'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
  
  - name: 'slack'
    slack_configs:
      - api_url: '<SLACK_WEBHOOK_URL>'
        channel: '#platform-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.description }}'
```

---

## 7. Health Checks

### 7.1 Pre-Run Health Checks

```python
def pre_run_health_checks() -> bool:
    """
    Perform health checks before ingestion.
    
    Returns:
        True if all checks pass, False otherwise
    """
    checks = {
        "database_connection": check_database_connection(),
        "schema_version": check_schema_version(),
        "external_api": check_external_api(),
        "oauth_authentication": check_oauth_authentication(),
        "disk_space": check_disk_space()
    }
    
    for check_name, result in checks.items():
        if not result:
            logger.error(f"Health check failed: {check_name}")
            return False
        logger.info(f"Health check passed: {check_name}")
    
    return True


def check_database_connection() -> bool:
    """Verify database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def check_schema_version() -> bool:
    """Verify Alembic schema version."""
    from version_checker import get_expected_version, get_current_version
    
    expected = get_expected_version()
    current = get_current_version(engine)
    
    if current != expected:
        logger.error(f"Schema version mismatch: expected {expected}, got {current}")
        return False
    
    return True


def check_external_api() -> bool:
    """Verify external API is reachable."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/health",
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"External API unreachable: {e}")
        return False


def check_oauth_authentication() -> bool:
    """Verify OAuth authentication works."""
    try:
        oauth_client = OAuthClient(client_id, client_secret)
        return oauth_client.authenticate()
    except Exception as e:
        logger.error(f"OAuth authentication failed: {e}")
        return False


def check_disk_space(min_free_gb: int = 10) -> bool:
    """Verify sufficient disk space."""
    import shutil
    
    stat = shutil.disk_usage("/var/log/ingestion")
    free_gb = stat.free / (1024**3)
    
    if free_gb < min_free_gb:
        logger.error(f"Insufficient disk space: {free_gb:.2f} GB free")
        return False
    
    return True
```

---

## 8. Error Notifications

### 8.1 Email Notifications

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_error_notification(
    correlation_id: str,
    error_summary: dict,
    recipient: str = "platform-team@company.com"
):
    """Send email notification on critical error."""
    
    msg = MIMEMultipart()
    msg["From"] = "noreply@company.com"
    msg["To"] = recipient
    msg["Subject"] = f"[CRITICAL] Ingestion Job Failed - {correlation_id}"
    
    body = f"""
    Nightly batch ingestion job failed.
    
    Correlation ID: {correlation_id}
    Timestamp: {datetime.utcnow().isoformat()}
    
    Summary:
    - Total batches: {error_summary['total_batches']}
    - Failed batches: {error_summary['failed_batches']}
    - Error category: {error_summary['error_category']}
    - Error message: {error_summary['error_message']}
    
    Action required:
    1. Review logs: /var/log/ingestion/{correlation_id}.log
    2. Check batch state: SELECT * FROM ingestion_batch_state WHERE correlation_id = '{correlation_id}'
    3. Retry failed batches: ./ingest_team_data.py --retry-failed
    
    Runbook: https://wiki.company.com/runbooks/ingestion-failure
    """
    
    msg.attach(MIMEText(body, "plain"))
    
    with smtplib.SMTP("smtp.company.com", 587) as server:
        server.starttls()
        server.send_message(msg)
```

### 8.2 Slack Notifications

```python
import requests

def send_slack_notification(correlation_id: str, message: str, severity: str):
    """Send Slack notification."""
    
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    color = {
        "info": "#36a64f",
        "warning": "#ff9900",
        "error": "#ff0000"
    }.get(severity, "#808080")
    
    payload = {
        "attachments": [{
            "color": color,
            "title": f"Ingestion Job Alert [{severity.upper()}]",
            "text": message,
            "fields": [
                {"title": "Correlation ID", "value": correlation_id, "short": True},
                {"title": "Timestamp", "value": datetime.utcnow().isoformat(), "short": True}
            ]
        }]
    }
    
    requests.post(webhook_url, json=payload)
```

---

## 9. Definition of Done

- [ ] Error taxonomy defined and implemented
- [ ] Structured logging with JSON format
- [ ] Audit logging to database
- [ ] Prometheus metrics exposed
- [ ] OpenTelemetry tracing configured
- [ ] Alert rules deployed
- [ ] Health checks implemented
- [ ] Error notifications (email/Slack)
- [ ] Monitoring dashboard created
- [ ] Runbook for common errors

---

**Document Status:** Ready for Implementation  
**Next Steps:** Implement structured logging and Prometheus metrics
