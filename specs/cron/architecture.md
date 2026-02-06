# Nightly Batch Ingestion Service - Architecture

**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Owner:** Platform Engineering

---

## 1. Overview

The Nightly Batch Ingestion Service is a Python-based ETL pipeline that synchronizes team member skill and availability data from an external system into the `ib_job_skill_mapping` database. The service authenticates using OAuth 2.0 Client Credentials, consumes a GET-based external API, processes data in isolated batches, and persists to PostgreSQL with full transactional guarantees.

### 1.1 Design Principles

- **Idempotency**: Multiple executions with same data produce identical results
- **Batch Isolation**: Each batch is independently processed; failure of one does not affect others
- **Schema Versioning**: All schema changes managed through Alembic migrations
- **Failure Resilience**: Selective retry of failed batches only
- **Zero Trust**: No hardcoded secrets; environment-based configuration
- **Observability**: Comprehensive logging with correlation tracking

---

## 2. System Architecture

### 2.1 High-Level Components

```mermaid
graph TB
    subgraph "Scheduler"
        CRON[Cron/K8s CronJob<br/>2:00 AM IST]
    end
    
    subgraph "Ingestion Service"
        CLI[CLI Entry Point<br/>ingest_team_data.py]
        AUTH[OAuth Client<br/>Token Manager]
        API[External API Client<br/>HTTP/Retry Logic]
        VALIDATOR[Payload Validator<br/>Schema Validation]
        PROCESSOR[Batch Processor<br/>Transaction Manager]
        RETRY[Retry Manager<br/>Failure Recovery]
    end
    
    subgraph "Database Layer"
        ALEMBIC[Alembic Migration<br/>Version Control]
        DB[(PostgreSQL<br/>ib_job_skill_mapping)]
    end
    
    subgraph "External System"
        EXT_AUTH[OAuth 2.0 Server<br/>Token Endpoint]
        EXT_API[External API<br/>/team-members/skill-availability]
    end
    
    subgraph "State Management"
        BATCH_STATE[(Batch State<br/>ingestion_batch_state)]
        AUDIT[(Audit Log<br/>ingestion_audit_log)]
    end
    
    CRON --> CLI
    CLI --> AUTH
    AUTH --> EXT_AUTH
    CLI --> ALEMBIC
    ALEMBIC --> DB
    AUTH --> API
    API --> EXT_API
    API --> VALIDATOR
    VALIDATOR --> PROCESSOR
    PROCESSOR --> DB
    PROCESSOR --> BATCH_STATE
    PROCESSOR --> AUDIT
    PROCESSOR --> RETRY
    RETRY --> API
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **CLI Entry Point** | Argument parsing, orchestration, logging setup, exit codes |
| **OAuth Client** | Token acquisition, caching, refresh, secure storage |
| **External API Client** | HTTP communication, retry logic, rate limiting, correlation tracking |
| **Payload Validator** | Schema validation, business rule checks, data quality gates |
| **Batch Processor** | Transaction management, UPSERT logic, referential integrity |
| **Retry Manager** | Failure detection, exponential backoff, retry orchestration |
| **Alembic Migration** | Schema versioning, migration execution, version validation |

---

## 3. End-to-End Flow

### 3.1 Complete Ingestion Sequence

```mermaid
sequenceDiagram
    participant CRON as Cron Scheduler
    participant CLI as CLI Entry Point
    participant ALEMBIC as Alembic
    participant AUTH as OAuth Client
    participant EXT_AUTH as OAuth Server
    participant API as API Client
    participant EXT_API as External API
    participant VAL as Validator
    participant PROC as Batch Processor
    participant DB as PostgreSQL
    participant STATE as Batch State
    participant AUDIT as Audit Log
    
    CRON->>CLI: Trigger at 2:00 AM IST
    CLI->>ALEMBIC: Check schema version
    ALEMBIC->>DB: SELECT version FROM alembic_version
    
    alt Schema version mismatch
        ALEMBIC-->>CLI: Error: Schema behind expected version
        CLI-->>CRON: Exit code 2 (schema error)
    end
    
    CLI->>AUTH: Request access token
    AUTH->>EXT_AUTH: POST /oauth/token (client_credentials)
    EXT_AUTH-->>AUTH: access_token (expires_in: 3600)
    AUTH->>AUTH: Cache token with expiry
    
    CLI->>API: Fetch batch data
    API->>EXT_AUTH: Validate token (if expired, refresh)
    API->>EXT_API: GET /api/v1/team-members/skill-availability<br/>Headers: Authorization, X-Correlation-ID
    EXT_API-->>API: Batch payload (metadata + team_members[])
    
    API->>VAL: Validate payload structure
    VAL->>VAL: Check schema, required fields, data types
    
    alt Validation failure
        VAL-->>CLI: ValidationError
        CLI->>AUDIT: Log validation failure
        CLI-->>CRON: Exit code 3 (validation error)
    end
    
    VAL->>PROC: Process batches sequentially
    
    loop For each batch
        PROC->>DB: BEGIN TRANSACTION
        PROC->>STATE: Check batch_id status
        
        alt Batch already successful
            PROC->>PROC: Skip (idempotency)
        else Batch new or failed
            PROC->>DB: UPSERT skill_master
            PROC->>DB: UPSERT team_member
            PROC->>DB: UPSERT team_member_skill
            PROC->>DB: UPSERT team_member_allocation
            PROC->>DB: UPSERT skill_certification
            PROC->>STATE: Update batch status = SUCCESS
            PROC->>AUDIT: Log batch completion
            PROC->>DB: COMMIT
        end
        
        alt Batch processing error
            PROC->>DB: ROLLBACK
            PROC->>STATE: Update batch status = FAILED
            PROC->>AUDIT: Log error with stack trace
            PROC->>PROC: Continue to next batch
        end
    end
    
    PROC-->>CLI: Batch summary (success/failed counts)
    CLI->>CLI: Determine exit code
    
    alt All batches successful
        CLI-->>CRON: Exit code 0 (success)
    else Some batches failed
        CLI-->>CRON: Exit code 1 (partial failure)
    end
```

### 3.2 Retry Flow

```mermaid
sequenceDiagram
    participant USER as Operator
    participant CLI as CLI Entry Point
    participant STATE as Batch State
    participant API as API Client
    participant EXT_API as External API
    participant PROC as Batch Processor
    participant DB as PostgreSQL
    
    USER->>CLI: ./ingest_team_data.py --retry-failed
    CLI->>STATE: Query failed batches
    STATE-->>CLI: List[batch_id] where status = FAILED
    
    alt No failed batches
        CLI-->>USER: Exit code 0 (nothing to retry)
    end
    
    loop For each failed batch_id
        CLI->>API: Fetch batch by batch_id
        API->>EXT_API: GET /api/v1/team-members/skill-availability?batch_id={id}
        EXT_API-->>API: Batch payload
        
        API->>PROC: Process single batch
        PROC->>DB: BEGIN TRANSACTION
        PROC->>DB: Execute UPSERT operations
        
        alt Success
            PROC->>STATE: Update status = SUCCESS
            PROC->>DB: COMMIT
        else Still fails
            PROC->>DB: ROLLBACK
            PROC->>STATE: Increment retry_count
            PROC->>STATE: Update last_retry_at
        end
    end
    
    CLI-->>USER: Retry summary with exit code
```

---

## 4. Data Flow

### 4.1 Payload to Database Mapping

```mermaid
graph LR
    subgraph "External API Payload"
        META[metadata<br/>batch_id, total_batches]
        TM[team_members[]<br/>id, skills[], allocations[]]
    end
    
    subgraph "Database Tables"
        CAT[category_master]
        SKILL[skill_master]
        MEMBER[team_member]
        TM_SKILL[team_member_skill]
        TM_ALLOC[team_member_allocation]
        CERT[skill_certification]
    end
    
    META --> STATE[(ingestion_batch_state)]
    TM --> MEMBER
    TM --> TM_SKILL
    TM --> TM_ALLOC
    TM --> CERT
    TM_SKILL --> SKILL
    SKILL --> CAT
```

### 4.2 Processing Order (Maintains Referential Integrity)

1. **category_master** (leaf dependency)
2. **skill_master** (depends on category_master)
3. **team_member** (independent)
4. **team_member_skill** (depends on team_member + skill_master)
5. **team_member_allocation** (depends on team_member)
6. **skill_certification** (depends on team_member + skill_master)

---

## 5. Deployment Architecture

### 5.1 Deployment Options

#### Option A: Traditional Cron (VM/Bare Metal)

```
/opt/ib-ingestion/
├── venv/
├── src/
│   ├── ingest_team_data.py
│   ├── oauth_client.py
│   ├── batch_processor.py
│   └── ...
├── alembic/
├── alembic.ini
├── config/
│   └── production.env
└── logs/

Cron entry:
0 2 * * * cd /opt/ib-ingestion && ./venv/bin/python src/ingest_team_data.py >> logs/ingestion.log 2>&1
```

#### Option B: Kubernetes CronJob (Recommended)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: team-data-ingestion
  namespace: ib-jobs
spec:
  schedule: "0 2 * * *"  # 2:00 AM IST (adjust for UTC)
  timeZone: "Asia/Kolkata"
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 5
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      backoffLimit: 0  # No retry at K8s level
      template:
        spec:
          restartPolicy: Never
          containers:
          - name: ingestion
            image: ib-ingestion:1.0.0
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: ib-db-credentials
                  key: url
            - name: OAUTH_CLIENT_ID
              valueFrom:
                secretKeyRef:
                  name: external-oauth
                  key: client_id
            - name: OAUTH_CLIENT_SECRET
              valueFrom:
                secretKeyRef:
                  name: external-oauth
                  key: client_secret
            volumeMounts:
            - name: logs
              mountPath: /app/logs
          volumes:
          - name: logs
            persistentVolumeClaim:
              claimName: ingestion-logs
```

### 5.2 Environment Configuration

```bash
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/ib_job_skill_mapping

# OAuth 2.0
OAUTH_TOKEN_URL=https://external-system.example.com/oauth/token
OAUTH_CLIENT_ID=ib-ingestion-client
OAUTH_CLIENT_SECRET=<vault-managed>
OAUTH_SCOPE=read:team-data

# External API
EXTERNAL_API_BASE_URL=https://external-system.example.com
EXTERNAL_API_TIMEOUT=30

# Batch Processing
BATCH_SIZE=100
MAX_RETRIES=3
RETRY_BACKOFF_MULTIPLIER=2
INITIAL_RETRY_DELAY=60

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 6. State Management

### 6.1 Batch State Table Schema

```sql
CREATE TABLE ingestion_batch_state (
    batch_id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'PROCESSING', 'SUCCESS', 'FAILED')),
    total_records INTEGER NOT NULL,
    processed_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    first_attempted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_retry_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    correlation_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_batch_state_status ON ingestion_batch_state(status);
CREATE INDEX idx_batch_state_correlation ON ingestion_batch_state(correlation_id);
```

### 6.2 Audit Log Table Schema

```sql
CREATE TABLE ingestion_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    batch_id VARCHAR(50),
    operation VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    table_name VARCHAR(100),
    records_affected INTEGER,
    execution_time_ms INTEGER,
    error_details JSONB,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_batch_id ON ingestion_audit_log(batch_id);
CREATE INDEX idx_audit_created_at ON ingestion_audit_log(created_at DESC);
```

---

## 7. Error Handling Strategy

### 7.1 Error Classification

| Error Type | Action | Exit Code | Retry Eligible |
|------------|--------|-----------|----------------|
| **Schema Version Mismatch** | Fail fast | 2 | No - Manual migration required |
| **OAuth Authentication Failure** | Fail fast | 4 | Yes - After credential fix |
| **API Network Timeout** | Retry with backoff | 5 | Yes |
| **Validation Error** | Log and skip batch | 3 | No - Data quality issue |
| **Database Constraint Violation** | Rollback batch | 1 | Yes - After data fix |
| **Unexpected Exception** | Rollback and log | 1 | Yes |

### 7.2 Exit Code Convention

```python
EXIT_SUCCESS = 0           # All batches processed successfully
EXIT_PARTIAL_FAILURE = 1   # Some batches failed (retryable)
EXIT_SCHEMA_ERROR = 2      # Alembic version mismatch
EXIT_VALIDATION_ERROR = 3  # Payload validation failure
EXIT_AUTH_ERROR = 4        # OAuth authentication failure
EXIT_API_ERROR = 5         # External API unreachable
```

---

## 8. Observability

### 8.1 Logging Requirements

**Structured JSON Logging Format:**

```json
{
  "timestamp": "2026-02-06T02:00:15.123Z",
  "level": "INFO",
  "service": "team-data-ingestion",
  "correlation_id": "INGEST-20260206-001",
  "batch_id": "BATCH-2026-02-06-01",
  "operation": "batch_processing",
  "message": "Batch processed successfully",
  "metadata": {
    "records_processed": 150,
    "duration_ms": 2345,
    "tables_updated": ["team_member", "team_member_skill"]
  }
}
```

### 8.2 Metrics to Capture

- Total batches fetched
- Batches processed (success/failure)
- Records processed per batch
- API response time
- Database transaction time
- OAuth token refresh count
- Retry attempts per batch

### 8.3 Alerting Thresholds

- **Critical**: All batches failed
- **Warning**: >20% batch failure rate
- **Info**: Schema version drift detected
- **Info**: OAuth token refresh required

---

## 9. Security Considerations

### 9.1 Secret Management

- **Local Development**: `.env` file (git-ignored)
- **Test/Staging**: Kubernetes Secrets
- **Production**: HashiCorp Vault / AWS Secrets Manager

### 9.2 Network Security

- External API calls over HTTPS only
- Certificate validation enforced
- OAuth token transmitted in `Authorization` header only
- Database connection uses TLS 1.2+

### 9.3 Least Privilege

```sql
-- Ingestion service database user permissions
CREATE USER ingestion_service WITH PASSWORD '<vault-managed>';

GRANT CONNECT ON DATABASE ib_job_skill_mapping TO ingestion_service;
GRANT USAGE ON SCHEMA public TO ingestion_service;

GRANT SELECT, INSERT, UPDATE ON TABLE category_master TO ingestion_service;
GRANT SELECT, INSERT, UPDATE ON TABLE skill_master TO ingestion_service;
GRANT SELECT, INSERT, UPDATE ON TABLE team_member TO ingestion_service;
GRANT SELECT, INSERT, UPDATE ON TABLE team_member_skill TO ingestion_service;
GRANT SELECT, INSERT, UPDATE ON TABLE team_member_allocation TO ingestion_service;
GRANT SELECT, INSERT, UPDATE ON TABLE skill_certification TO ingestion_service;

GRANT SELECT, INSERT, UPDATE ON TABLE ingestion_batch_state TO ingestion_service;
GRANT INSERT ON TABLE ingestion_audit_log TO ingestion_service;

GRANT SELECT ON TABLE alembic_version TO ingestion_service;
```

---

## 10. Assumptions & Constraints

### 10.1 Assumptions

1. External API supports filtering by `batch_id` for retry scenarios
2. OAuth token endpoint is rate-limited but allows reasonable refresh frequency
3. Database has sufficient connection pool capacity for ingestion jobs
4. Payload schema is versioned and backward-compatible
5. External system guarantees batch ordering is not required
6. Clock synchronization (NTP) ensures accurate scheduling

### 10.2 Technical Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| GET-based bulk data API | Non-idempotent HTTP semantic | Document as legacy constraint; request POST in future |
| Single database connection | Limits parallelism | Use connection pooling; process batches sequentially |
| Cron scheduling precision | ±1 minute variance | Acceptable for nightly job; consider distributed scheduler if sub-minute precision needed |
| OAuth token expiry (3600s) | Service must handle mid-run refresh | Implement token expiry check before each API call |

### 10.3 Design Trade-offs

| Decision | Rationale | Alternative Considered |
|----------|-----------|------------------------|
| Sequential batch processing | Simplifies transaction management and failure isolation | Parallel processing (rejected due to connection pool limits) |
| SQLAlchemy Core over ORM | Performance for bulk operations | SQLAlchemy ORM (rejected due to overhead) |
| Single-threaded execution | Avoids concurrency complexity | Async/multi-threading (deferred to v2.0 if needed) |
| Alembic version check before run | Fail fast on schema drift | Skip check (rejected - too risky) |

---

## 11. Performance Targets

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Batch Processing Time** | < 5 minutes per 1000 records | Execution time logging |
| **API Response Time** | < 2 seconds per batch | HTTP client metrics |
| **Database Transaction Time** | < 500ms per batch | PostgreSQL query logs |
| **End-to-End Job Duration** | < 30 minutes for typical nightly load | Cron job duration monitoring |
| **Memory Footprint** | < 512 MB peak | Container resource limits |

---

## 12. Testing Strategy

### 12.1 Test Levels

1. **Unit Tests**: OAuth client, validator, batch processor logic
2. **Integration Tests**: Database UPSERT operations with test fixtures
3. **E2E Tests**: Mock external API, run full ingestion flow
4. **Chaos Tests**: Simulate network failures, database deadlocks, partial batch failures

### 12.2 Test Data Requirements

- Sample payload with 3 batches (success case)
- Payload with duplicate records (idempotency test)
- Payload with missing required fields (validation test)
- Payload with foreign key violations (referential integrity test)

---

## 13. Definition of Done (DoD)

- [ ] All specification documents completed and reviewed
- [ ] Alembic migrations for state tables created and tested
- [ ] OAuth client implementation with token caching
- [ ] External API client with retry logic
- [ ] Batch processor with UPSERT operations
- [ ] Unit tests with >80% coverage
- [ ] Integration tests with real PostgreSQL instance
- [ ] CLI accepts `--dry-run`, `--batch-id`, `--retry-failed`
- [ ] Logging outputs structured JSON
- [ ] Exit codes follow documented convention
- [ ] Kubernetes CronJob manifest validated
- [ ] Runbook created for operations team
- [ ] Security review completed

---

## 14. References

- [OAuth 2.0 Client Credentials Grant (RFC 6749)](https://tools.ietf.org/html/rfc6749#section-4.4)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL UPSERT (ON CONFLICT)](https://www.postgresql.org/docs/current/sql-insert.html)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [Kubernetes CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)

---

**Document Status:** Ready for Implementation  
**Next Steps:** Review with Platform Engineering and Security teams
