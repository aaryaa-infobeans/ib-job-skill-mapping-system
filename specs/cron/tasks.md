# Nightly Batch Ingestion System - Task Breakdown

**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Ready for Execution  
**Source:** `/specs/cron/implementation-plan.md`

---

## 📋 Document Overview

This document provides a **granular, execution-ready task list** for implementing the Python-based nightly batch ingestion system with:

✅ Batch retry isolation by `batch_id`  
✅ Alembic-managed schema evolution  
✅ Zero regression in existing API-Gateway features  
✅ Enforced unit test coverage thresholds (≥85% overall, ≥90% critical paths)

**Quality Gates:**
- All tasks must be independently implementable
- All tasks must be objectively testable
- All tasks must provide validation evidence
- Coverage thresholds are non-negotiable
- API-Gateway regression tests mandatory

---

## 🎯 Phase Overview

| Phase | Duration | Task Count | Coverage Target |
|-------|----------|------------|-----------------|
| Phase 0 | 3 days | 6 tasks | N/A |
| Phase 1 | 5 days | 8 tasks | N/A |
| Phase 2 | 5 days | 8 tasks | ≥85% |
| Phase 3 | 7 days | 10 tasks | ≥90% |
| Phase 4 | 5 days | 7 tasks | ≥90% |
| Phase 5 | 5 days | 6 tasks | ≥85% |
| Phase 6 | 10 days | 15 tasks | ≥85% overall |
| Phase 7 | 5 days | 6 tasks | N/A |
| **Total** | **45 days** | **66 tasks** | **≥85% overall** |

---

## Phase 0: Repository & Scaffolding

**Objective:** Establish directory structure, dependency management, and test infrastructure.

---

### TASK-0.1: Create Directory Structure

**Phase:** 0  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Create all required directories per mandatory structure for ingestion service and test infrastructure.

**Files/Directories Impacted:**
```
app/cron/
├── __init__.py
├── oauth/
│   └── __init__.py
├── api/
│   └── __init__.py
├── db/
│   └── __init__.py
├── processing/
│   └── __init__.py
└── utils/
    └── __init__.py

tests/cron/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── oauth/
│   │   └── __init__.py
│   ├── api/
│   │   └── __init__.py
│   ├── db/
│   │   └── __init__.py
│   ├── processing/
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── integration/
│   └── __init__.py
└── api_gateway/
    └── regression/
        └── __init__.py

scripts/
```

**Dependencies:** None

**Acceptance Criteria:**
- [ ] All directories exist with correct hierarchy
- [ ] All `__init__.py` files present
- [ ] Python can import `app.cron` and `tests.cron` modules
- [ ] No files outside mandatory structure

**Validation Evidence:**
```bash
# Verify directory structure
tree app/cron tests/cron scripts -L 3

# Verify imports
python -c "import app.cron; import tests.cron; print('✓ Imports successful')"
```

**Definition of Done:**
- Directory structure matches specification exactly
- All imports work without errors
- PR approved with structure validation

---

### TASK-0.2: Configure Dependencies and Requirements

**Phase:** 0  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Create `requirements.txt` with pinned dependencies for ingestion service and test infrastructure.

**Files/Directories Impacted:**
```
requirements.txt
pyproject.toml
.python-version (optional)
```

**Dependencies:** TASK-0.1

**Implementation Requirements:**

**requirements.txt additions:**
```txt
# Ingestion Service Dependencies
requests==2.31.0
authlib==1.3.0

# Testing Infrastructure
pytest==7.4.4
pytest-cov==4.1.0
pytest-mock==3.12.0
responses==0.24.1
coverage[toml]==7.4.0
```

**Acceptance Criteria:**
- [ ] All dependencies installed successfully
- [ ] No version conflicts with existing packages
- [ ] `pip check` passes
- [ ] `safety check` passes (no critical vulnerabilities)
- [ ] pytest and coverage tools functional

**Validation Evidence:**
```bash
# Install dependencies
pip install -r requirements.txt

# Verify no conflicts
pip check

# Security scan
safety check

# Test pytest and coverage
pytest --version
coverage --version
```

**Definition of Done:**
- Dependencies installed without errors
- Security scan passed
- Test tools verified functional
- PR approved

---

### TASK-0.3: Implement Configuration Management

**Phase:** 0  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Create configuration module using Pydantic Settings with environment variable support.

**Files/Directories Impacted:**
```
app/cron/config.py
.env.example
```

**Dependencies:** TASK-0.2

**Implementation Requirements:**
- Pydantic Settings class with all required fields
- Environment variable loading from `.env`
- Database URL construction
- OAuth configuration
- API configuration
- Batch processing parameters
- Logging configuration

**Key Configuration Fields:**
- `db_host`, `db_port`, `db_name`, `db_user`, `db_password`
- `oauth_token_url`, `oauth_client_id`, `oauth_client_secret`
- `api_base_url`, `api_timeout`
- `external_api_endpoint` (e.g., /api/v1/team-members/skill-availability)
- `batch_size`, `max_retries`, `retry_base_delay`
- `log_level`, `log_dir`
- `dry_run`

**Acceptance Criteria:**
- [ ] Configuration loads from `.env` file
- [ ] Environment variables override defaults
- [ ] Validation errors for missing required fields
- [ ] Database URL constructed correctly
- [ ] All fields documented with descriptions
- [ ] `.env.example` created with all fields

**Validation Evidence:**
```bash
# Test configuration loading
python -c "from app.cron.config import settings; print(settings.database_url)"

# Test validation
python -c "from app.cron.config import Settings; Settings(db_password='test')"
```

**Definition of Done:**
- Configuration module working
- Unit tests pass
- `.env.example` documented
- PR approved

---

### TASK-0.4: Setup Logging Utilities

**Phase:** 0  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Create logging utilities that leverage existing `src/app/logging_config.py` with correlation ID generation.

**Files/Directories Impacted:**
```
app/cron/utils/logging.py
```

**Dependencies:** TASK-0.1

**Implementation Requirements:**
- Import existing logging configuration from `src.app.logging_config`
- Implement `generate_correlation_id()` function
- Re-export `configure_logging`, `set_correlation_id`, `get_correlation_id`
- Correlation ID format: `ING-YYYYMMDD-HHMMSS`

**Acceptance Criteria:**
- [ ] Existing logging reused from src/app/logging_config.py
- [ ] Correlation ID generator implemented
- [ ] All logs output in JSON format
- [ ] Correlation ID included in all log entries
- [ ] Unit tests verify correlation ID generation format

**Validation Evidence:**
```bash
# Test logging utilities
python -c "
from app.cron.utils.logging import generate_correlation_id, configure_logging, set_correlation_id
import logging
configure_logging('INFO')
corr_id = generate_correlation_id()
set_correlation_id(corr_id)
logger = logging.getLogger(__name__)
logger.info('Test message', extra={'test': 'value'})
print(f'✓ Correlation ID: {corr_id}')
"
```

**Definition of Done:**
- Logging utilities working
- Unit tests pass
- JSON output verified
- PR approved

---

### TASK-0.5: Setup Coverage Enforcement

**Phase:** 0  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Configure pytest-cov with coverage thresholds and reporting.

**Files/Directories Impacted:**
```
pyproject.toml
.coveragerc (or coverage config in pyproject.toml)
.github/workflows/ci.yml (if using GitHub Actions)
```

**Dependencies:** TASK-0.2

**Implementation Requirements:**

**pyproject.toml additions:**
```toml
[tool.coverage.run]
source = ["app/cron"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__init__.py"
]

[tool.coverage.report]
fail_under = 85
precision = 2
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"

[tool.coverage.xml]
output = "coverage.xml"
```

**Acceptance Criteria:**
- [ ] Coverage configuration in pyproject.toml
- [ ] Fail threshold set to 85%
- [ ] HTML and XML reports enabled
- [ ] Coverage runs successfully with pytest
- [ ] CI configured to enforce thresholds
- [ ] Coverage badge configuration ready

**Validation Evidence:**
```bash
# Run coverage
pytest tests/cron --cov=app/cron --cov-report=html --cov-report=xml --cov-report=term

# Verify threshold enforcement
pytest tests/cron --cov=app/cron --cov-fail-under=85
```

**Definition of Done:**
- Coverage tooling configured
- Thresholds enforced in CI
- Reports generated successfully
- PR approved

---

### TASK-0.6: Create API-Gateway Regression Test Baseline

**Phase:** 0  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Capture baseline behavior of existing API-Gateway endpoints for regression testing.

**Files/Directories Impacted:**
```
tests/cron/api_gateway/regression/
├── __init__.py
├── test_health_metrics_regression.py
├── test_bulk_upsert_regression.py
├── test_jd_skill_mapping_regression.py
└── baseline_responses.json
```

**Dependencies:** TASK-0.1

**Implementation Requirements:**
- Capture response shapes for all API-Gateway endpoints
- Document status codes
- Record pagination behavior
- Capture filter behavior
- Store baseline responses
- Create regression test harness
- Use actual payload structure from specs-data/team-member-skill-availability-records.json for testing

**API Endpoints to Baseline:**
- GET `/health` - Health check
- GET `/api/v1/metrics` - Metrics endpoint
- POST `/api/v1/team-members/skill-availability/bulk-upsert` - Bulk upsert team member data
- POST `/api/v1/jd-skill-mapping/` - Requisition/JD skill mapping request
- GET `/api/v1/jd-skill-mapping/{correlation_id}/matches` - Get matching results

**Acceptance Criteria:**
- [ ] All API-Gateway endpoints documented
- [ ] Baseline responses captured
- [ ] Regression tests pass against current implementation
- [ ] No false positives in regression tests
- [ ] Test harness supports before/after comparison

**Validation Evidence:**
```bash
# Run regression baseline
pytest tests/cron/api_gateway/regression/ -v --tb=short

# Generate baseline report
pytest tests/cron/api_gateway/regression/ --json-report --json-report-file=baseline.json
```

**Definition of Done:**
- Baseline captured
- Regression tests pass
- Documentation complete
- PR approved

---

## Phase 1: Database & Alembic Setup

**Objective:** Create Alembic migration 002 for batch state tables and implement version validation.

---

### TASK-1.1: Create Alembic Migration 002

**Phase:** 1  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 2 days

**Description:**  
Generate Alembic migration for `ingestion_batch_state` and `ingestion_audit_log` tables. Existing tables (category_master, skill_master, team_member, etc.) are reused from migration 001.

**Files/Directories Impacted:**
```
alembic/versions/0002_nightly_batch_ingestion_schema.py
```

**Dependencies:** TASK-0.3

**Implementation Requirements:**

**Tables to Create:**
1. **ingestion_batch_state:**
   - batch_id (VARCHAR(100) PK)
   - correlation_id (VARCHAR(50))
   - status (VARCHAR(20))
   - total_records, processed_records, failed_records (INTEGER)
   - retry_count, max_retries (INTEGER)
   - error_message (TEXT), error_category (VARCHAR(50))
   - first_attempted_at, last_retry_at, completed_at (TIMESTAMP)
   - created_at, updated_at (TIMESTAMP)
   - Indexes: correlation_id, status, created_at

2. **ingestion_audit_log:**
   - audit_id (UUID PK)
   - correlation_id (VARCHAR(50))
   - batch_id (VARCHAR(100))
   - event_type (VARCHAR(50))
   - status (VARCHAR(20))
   - error_category, error_message
   - metadata (JSONB)
   - created_at (TIMESTAMP)
   - Indexes: correlation_id, batch_id, created_at

**Acceptance Criteria:**
- [ ] Migration file generated with correct revision ID
- [ ] Both `upgrade()` and `downgrade()` implemented
- [ ] All columns match specification
- [ ] Indexes created
- [ ] No changes to existing tables
- [ ] Migration reversible (upgrade + downgrade + upgrade works)

**Validation Evidence:**
```bash
# Apply migration
alembic upgrade head

# Verify tables created
psql -h localhost -p 5433 -U postgres -d ib_job_skill_mapping -c "\d ingestion_batch_state"
psql -h localhost -p 5433 -U postgres -d ib_job_skill_mapping -c "\d ingestion_audit_log"

# Test reversibility
alembic downgrade -1
alembic upgrade head

# Verify no changes to existing tables
psql -h localhost -p 5433 -U postgres -d ib_job_skill_mapping -c "\d category_master"
```

**Definition of Done:**
- Migration applied successfully
- Tables created with correct schema
- Reversibility tested
- No impact on existing tables
- PR approved

---

### TASK-1.2: Implement Schema Version Checker

**Phase:** 1  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Create version checker module to validate Alembic version matches expected revision before ingestion runs.

**Files/Directories Impacted:**
```
app/cron/db/migrations_check.py
tests/cron/unit/db/test_migrations_check.py
```

**Dependencies:** TASK-1.1

**Implementation Requirements:**
- `EXPECTED_REVISION = "0002"` constant
- `get_expected_version()` - returns expected revision
- `get_current_version(engine)` - queries alembic_version table
- `validate_schema_version(engine)` - raises RuntimeError if mismatch
- `get_migration_info(engine)` - returns detailed migration status

**Acceptance Criteria:**
- [ ] Version checker correctly identifies current revision
- [ ] Raises RuntimeError when schema version mismatched
- [ ] Provides clear error message with migration command
- [ ] Unit tests cover all scenarios:
  - [ ] Version matches
  - [ ] Version mismatch
  - [ ] Database not versioned
  - [ ] Multiple heads detected
- [ ] Unit test coverage ≥90%

**Validation Evidence:**
```bash
# Test version checker
python -c "
from app.cron.db.migrations_check import validate_schema_version, get_migration_info
from app.cron.db.engine import create_db_engine
engine = create_db_engine()
validate_schema_version(engine)
print(get_migration_info(engine))
"

# Run unit tests
pytest tests/cron/unit/db/test_migrations_check.py -v --cov=app/cron/db/migrations_check
```

**Definition of Done:**
- Version checker implemented
- All unit tests pass
- Coverage ≥90%
- Integration test validates against real DB
- PR approved

---

### TASK-1.3: Implement Database Engine Factory

**Phase:** 1  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Create database engine factory with connection pooling configuration.

**Files/Directories Impacted:**
```
app/cron/db/engine.py
tests/cron/unit/db/test_engine.py
```

**Dependencies:** TASK-0.3

**Implementation Requirements:**
- `create_db_engine()` - creates SQLAlchemy engine
- Connection pool: size=5, max_overflow=10, timeout=30
- pool_pre_ping=True for connection validation
- `test_connection(engine)` - validates connectivity
- Application name: "team-data-ingestion"

**Acceptance Criteria:**
- [ ] Engine creates successfully with valid credentials
- [ ] Connection pool configured correctly
- [ ] pool_pre_ping enabled
- [ ] test_connection validates connectivity
- [ ] Invalid credentials raise appropriate errors
- [ ] Unit tests cover:
  - [ ] Successful connection
  - [ ] Connection failure
  - [ ] Pool configuration verification
- [ ] Unit test coverage ≥85%

**Validation Evidence:**
```bash
# Test engine creation
python -c "
from app.cron.db.engine import create_db_engine, test_connection
engine = create_db_engine()
test_connection(engine)
print('✓ Connection successful')
"

# Run unit tests
pytest tests/cron/unit/db/test_engine.py -v --cov=app/cron/db/engine
```

**Definition of Done:**
- Engine factory implemented
- All unit tests pass
- Coverage ≥85%
- Connection pooling verified
- PR approved

---

### TASK-1.4: Define Database Metadata

**Phase:** 1  
**Priority:** P1 (High)  
**Estimated Effort:** 0.5 days

**Description:**  
Define SQLAlchemy metadata for new batch state tables. Import existing tables from src/app/db/models.py.

**Files/Directories Impacted:**
```
app/cron/db/metadata.py
```

**Dependencies:** TASK-1.1

**Implementation Requirements:**
- Define metadata for `ingestion_batch_state`
- Define metadata for `ingestion_audit_log`
- Import existing tables from `src.app.db.models`
- Column types must match migration DDL exactly

**Acceptance Criteria:**
- [ ] Metadata matches migration schema exactly
- [ ] Tables can be reflected from database
- [ ] Column types match migration DDL
- [ ] Imports work correctly
- [ ] No duplicate table definitions

**Validation Evidence:**
```bash
# Verify metadata
python -c "
from app.cron.db.metadata import ingestion_batch_state, ingestion_audit_log
from src.app.db.models import category_master, skill_master, team_member
print('✓ Metadata definitions loaded')
print(f'Batch state columns: {[c.name for c in ingestion_batch_state.columns]}')
"
```

**Definition of Done:**
- Metadata definitions complete
- Matches migration schema
- PR approved

---

### TASK-1.5: Create Migration Impact Analysis Tests

**Phase:** 1  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Create tests to validate migration 002 has no impact on existing API-Gateway queries.

**Files/Directories Impacted:**
```
tests/cron/integration/test_migration_impact.py
```

**Dependencies:** TASK-1.1, TASK-0.6

**Implementation Requirements:**
- Query performance tests before/after migration
- Validate existing queries still work
- Check for schema drift
- Verify foreign key relationships intact
- No new constraints on existing tables

**Test Scenarios:**
- [ ] All API-Gateway queries execute successfully
- [ ] Query execution time not degraded
- [ ] No new locks on existing tables
- [ ] Foreign keys remain valid
- [ ] Existing indexes unchanged

**Acceptance Criteria:**
- [ ] All existing queries tested
- [ ] No performance degradation (< 5% variance)
- [ ] No schema drift detected
- [ ] Integration tests pass
- [ ] Test report generated

**Validation Evidence:**
```bash
# Run migration impact tests
pytest tests/cron/integration/test_migration_impact.py -v --tb=short

# Generate performance report
pytest tests/cron/integration/test_migration_impact.py --benchmark-only
```

**Definition of Done:**
- Impact analysis complete
- All tests pass
- No regression detected
- Report generated
- PR approved

---

### TASK-1.6: Unit Tests for Database Module

**Phase:** 1  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Implement comprehensive unit tests for all database module components.

**Files/Directories Impacted:**
```
tests/cron/unit/db/
├── test_migrations_check.py (from TASK-1.2)
├── test_engine.py (from TASK-1.3)
└── test_metadata.py
```

**Dependencies:** TASK-1.2, TASK-1.3, TASK-1.4

**Test Coverage Requirements:**
- migrations_check.py: ≥90%
- engine.py: ≥85%
- metadata.py: ≥80%

**Test Scenarios:**
- Version checker: match, mismatch, not versioned
- Engine: successful connection, failure, pool exhaustion
- Metadata: table reflection, column validation

**Acceptance Criteria:**
- [ ] All unit tests pass
- [ ] Coverage ≥90% for db module
- [ ] All edge cases covered
- [ ] Mock database connections where appropriate
- [ ] Tests run in < 5 seconds

**Validation Evidence:**
```bash
# Run all db unit tests with coverage
pytest tests/cron/unit/db/ -v --cov=app/cron/db --cov-report=term --cov-report=html

# Verify coverage threshold
pytest tests/cron/unit/db/ --cov=app/cron/db --cov-fail-under=90
```

**Definition of Done:**
- All unit tests implemented
- Coverage ≥90%
- All tests pass
- Coverage report generated
- PR approved

---

### TASK-1.7: Integration Tests for Database Setup

**Phase:** 1  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Create integration tests for database setup validating against real database.

**Files/Directories Impacted:**
```
tests/cron/integration/test_database_setup.py
```

**Dependencies:** TASK-1.1, TASK-1.2, TASK-1.3

**Implementation Requirements:**
- Test migration application
- Test version checking
- Test connection establishment
- Test transaction rollback
- Use test database or Docker container

**Test Scenarios:**
- [ ] Migration applies successfully
- [ ] Version checker validates correctly
- [ ] Connection pool works
- [ ] Transactions rollback properly
- [ ] Concurrent connections handled

**Acceptance Criteria:**
- [ ] Integration tests pass against real database
- [ ] Tests use isolated test database
- [ ] Cleanup after tests
- [ ] Tests can run in CI
- [ ] Tests run in < 30 seconds

**Validation Evidence:**
```bash
# Run integration tests
pytest tests/cron/integration/test_database_setup.py -v --tb=short

# Run with Docker database
docker-compose -f docker-compose.test.yml up -d postgres
pytest tests/cron/integration/test_database_setup.py -v
docker-compose -f docker-compose.test.yml down
```

**Definition of Done:**
- Integration tests implemented
- All tests pass
- Can run in CI
- PR approved

---

### TASK-1.8: Phase 1 Definition of Done Verification

**Phase:** 1  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Validate all Phase 1 acceptance criteria met before proceeding to Phase 2.

**Validation Checklist:**
- [ ] Alembic migration 002 created and tested
- [ ] Migration applied successfully (`alembic upgrade head`)
- [ ] Version checker implemented and tested
- [ ] Database engine factory working
- [ ] Metadata definitions complete
- [ ] All Phase 1 unit tests passing
- [ ] Integration test validates migration reversibility
- [ ] Coverage ≥90% for db module
- [ ] No impact on API-Gateway
- [ ] All PRs merged

**Validation Evidence:**
```bash
# Verify migration
alembic current
alembic upgrade head

# Run all Phase 1 tests
pytest tests/cron/unit/db/ tests/cron/integration/ -v --cov=app/cron/db

# Verify coverage
pytest tests/cron/unit/db/ --cov=app/cron/db --cov-report=term --cov-fail-under=90

# Run regression tests
pytest tests/cron/api_gateway/regression/ -v
```

**Definition of Done:**
- All checklist items verified
- All tests passing
- Coverage thresholds met
- Phase 1 complete gate passed

---

## Phase 2: OAuth & External API Integration

**Objective:** Implement OAuth 2.0 Client Credentials authentication and external API client with token caching.

---

### TASK-2.1: Implement OAuth Token Client

**Phase:** 2  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 2 days

**Description:**  
Create OAuth 2.0 Client Credentials client with token caching and automatic refresh.

**Files/Directories Impacted:**
```
app/cron/oauth/token_client.py
tests/cron/unit/oauth/test_token_client.py
```

**Dependencies:** TASK-0.3, TASK-0.4

**Implementation Requirements:**

**Classes:**
1. `TokenCache` - in-memory token storage
   - `is_valid()` - checks token expiration (60s buffer)
   - `store(access_token, expires_in)` - stores token

2. `OAuthClient` - OAuth client
   - `get_access_token()` - returns valid token (cached or new)
   - `_fetch_new_token()` - fetches from OAuth server
   - Token caching enabled
   - Automatic refresh on expiration

**Acceptance Criteria:**
- [ ] Token fetched successfully with valid credentials
- [ ] Token cached and reused within validity period
- [ ] Token refreshed automatically when expired
- [ ] 60-second buffer before expiration
- [ ] Authentication failures raise appropriate errors
- [ ] Unit tests cover:
  - [ ] Successful token fetch
  - [ ] Token caching
  - [ ] Token refresh
  - [ ] Authentication failure (401)
  - [ ] Network errors
  - [ ] Invalid response format
- [ ] Unit test coverage ≥90%

**Validation Evidence:**
```bash
# Run unit tests
pytest tests/cron/unit/oauth/test_token_client.py -v --cov=app/cron/oauth/token_client

# Verify coverage
pytest tests/cron/unit/oauth/test_token_client.py --cov=app/cron/oauth/token_client --cov-fail-under=90
```

**Definition of Done:**
- OAuth client implemented
- All unit tests pass
- Coverage ≥90%
- PR approved

---

### TASK-2.2: Implement External API Client

**Phase:** 2  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 2 days

**Description:**  
Create external API client with retry logic, timeout handling, and error classification.

**Files/Directories Impacted:**
```
app/cron/api/external_client.py
tests/cron/unit/api/test_external_client.py
```

**Dependencies:** TASK-2.1

**Implementation Requirements:**

**Class:** `TeamDataClient`
- `fetch_team_data()` - fetches all team member data
- `fetch_batch_by_id(batch_id)` - fetches specific batch for retry
- Session with retry strategy (3 retries, backoff factor 1)
- Status codes for retry: 429, 500, 502, 503, 504
- Timeout: configurable (default 30s)
- Authorization header with Bearer token
- Correlation ID propagation

**Acceptance Criteria:**
- [ ] API client fetches data successfully with valid token
- [ ] Automatic retries on transient errors (429, 5xx)
- [ ] Timeouts handled gracefully
- [ ] 401 errors logged (token refresh handled by OAuth client)
- [ ] Request logging includes URL and correlation ID
- [ ] Unit tests cover:
  - [ ] Successful data fetch
  - [ ] Timeout handling
  - [ ] Retry on 429
  - [ ] Retry on 5xx
  - [ ] Non-retryable errors (400, 404)
  - [ ] Token refresh triggered
  - [ ] Network errors
- [ ] Unit test coverage ≥90%

**Validation Evidence:**
```bash
# Run unit tests with mocked responses
pytest tests/cron/unit/api/test_external_client.py -v --cov=app/cron/api/external_client

# Verify coverage
pytest tests/cron/unit/api/test_external_client.py --cov=app/cron/api/external_client --cov-fail-under=90
```

**Definition of Done:**
- API client implemented
- All unit tests pass
- Coverage ≥90%
- Retry logic verified
- PR approved

---

### TASK-2.3: Create Mock API Server for Testing

**Phase:** 2  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Implement mock external API server for integration testing.

**Files/Directories Impacted:**
```
tests/cron/integration/mock_api_server.py
tests/cron/integration/test_oauth_integration.py
```

**Dependencies:** TASK-2.1, TASK-2.2

**Implementation Requirements:**

**Mock Server Endpoints:**
- `POST /oauth/token` - returns mock access token
- `GET /team-members` - returns mock team data
- `GET /team-members/batch/{batch_id}` - returns specific batch

**Mock Data:**
- At least 2 batches
- At least 5 team members
- Skills, allocations, certifications included
- Supports 401 (invalid token)
- Supports 429 (rate limiting)
- Supports 503 (server error)

**Acceptance Criteria:**
- [ ] Mock server responds to all endpoints
- [ ] Mock server handles authentication
- [ ] Mock server simulates errors
- [ ] Integration tests use mock server
- [ ] Mock server can run standalone
- [ ] Mock server documented

**Validation Evidence:**
```bash
# Start mock server
python tests/cron/integration/mock_api_server.py &

# Test OAuth flow
curl -X POST http://localhost:8080/oauth/token \
  -d "grant_type=client_credentials&client_id=test&client_secret=test"

# Test API endpoint
curl http://localhost:8080/team-members \
  -H "Authorization: Bearer mock_token"

# Run integration tests
pytest tests/cron/integration/test_oauth_integration.py -v
```

**Definition of Done:**
- Mock server implemented
- Integration tests pass
- Documentation complete
- PR approved

---

### TASK-2.4: Unit Tests for OAuth Module

**Phase:** 2  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Comprehensive unit tests for OAuth token client with all edge cases.

**Files/Directories Impacted:**
```
tests/cron/unit/oauth/test_token_client.py
tests/cron/unit/oauth/test_token_cache.py
```

**Dependencies:** TASK-2.1

**Test Coverage Requirements:**
- token_client.py: ≥90%
- All methods: `get_access_token`, `_fetch_new_token`
- All TokenCache methods

**Test Scenarios:**
- [ ] Token fetch successful
- [ ] Token cached correctly
- [ ] Token reused from cache
- [ ] Token refresh on expiration
- [ ] 60-second expiration buffer
- [ ] Authentication failure (401)
- [ ] Invalid credentials
- [ ] Network timeout
- [ ] Invalid response format
- [ ] Missing token in response
- [ ] Concurrent token requests

**Acceptance Criteria:**
- [ ] All test scenarios implemented
- [ ] Coverage ≥90%
- [ ] All tests pass in < 2 seconds
- [ ] Mock HTTP responses used
- [ ] No actual network calls

**Validation Evidence:**
```bash
# Run unit tests
pytest tests/cron/unit/oauth/ -v --cov=app/cron/oauth --cov-report=term

# Verify coverage threshold
pytest tests/cron/unit/oauth/ --cov=app/cron/oauth --cov-fail-under=90

# Check test execution time
pytest tests/cron/unit/oauth/ --durations=10
```

**Definition of Done:**
- All unit tests pass
- Coverage ≥90%
- Fast execution (< 2s)
- PR approved

---

### TASK-2.5: Unit Tests for API Module

**Phase:** 2  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Comprehensive unit tests for external API client with all edge cases.

**Files/Directories Impacted:**
```
tests/cron/unit/api/test_external_client.py
```

**Dependencies:** TASK-2.2

**Test Coverage Requirements:**
- external_client.py: ≥90%
- All methods: `fetch_team_data`, `fetch_batch_by_id`, `_create_session`

**Test Scenarios:**
- [ ] Successful data fetch
- [ ] Batch fetch by ID
- [ ] Timeout handling
- [ ] Retry on 429 (rate limit)
- [ ] Retry on 500, 502, 503, 504
- [ ] No retry on 400, 404
- [ ] Token included in headers
- [ ] Correlation ID in logs
- [ ] Empty response handling
- [ ] Malformed JSON
- [ ] Network errors
- [ ] Retry exhaustion

**Acceptance Criteria:**
- [ ] All test scenarios implemented
- [ ] Coverage ≥90%
- [ ] All tests pass in < 3 seconds
- [ ] Mock HTTP responses used (responses library)
- [ ] No actual network calls
- [ ] Retry logic verified

**Validation Evidence:**
```bash
# Run unit tests
pytest tests/cron/unit/api/ -v --cov=app/cron/api --cov-report=term

# Verify coverage threshold
pytest tests/cron/unit/api/ --cov=app/cron/api --cov-fail-under=90

# Verify retry behavior
pytest tests/cron/unit/api/test_external_client.py::test_retry_on_rate_limit -v
```

**Definition of Done:**
- All unit tests pass
- Coverage ≥90%
- Retry logic verified
- PR approved

---

### TASK-2.6: Integration Tests for OAuth and API

**Phase:** 2  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
End-to-end integration tests for OAuth authentication and API data fetching.

**Files/Directories Impacted:**
```
tests/cron/integration/test_oauth_integration.py
tests/cron/integration/test_api_integration.py
```

**Dependencies:** TASK-2.3

**Test Scenarios:**
- [ ] OAuth token retrieval from mock server
- [ ] Token used in API requests
- [ ] Token refresh on expiration
- [ ] API data fetch with authentication
- [ ] Batch fetch by ID
- [ ] Error handling end-to-end

**Acceptance Criteria:**
- [ ] Integration tests use mock server
- [ ] OAuth flow tested end-to-end
- [ ] API client tested end-to-end
- [ ] Token caching verified
- [ ] All tests pass
- [ ] Tests run in < 10 seconds

**Validation Evidence:**
```bash
# Start mock server and run tests
pytest tests/cron/integration/test_oauth_integration.py tests/cron/integration/test_api_integration.py -v

# Verify no real network calls
pytest tests/cron/integration/ -v --log-cli-level=DEBUG | grep -i "mock"
```

**Definition of Done:**
- Integration tests pass
- End-to-end flow verified
- Mock server used
- PR approved

---

### TASK-2.7: API-Gateway Regression After Phase 2

**Phase:** 2  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Run API-Gateway regression tests to ensure no breaking changes from Phase 2.

**Files/Directories Impacted:**
```
tests/cron/api_gateway/regression/
```

**Dependencies:** TASK-0.6, Phase 2 completion

**Validation Checklist:**
- [ ] All API-Gateway endpoints functional
- [ ] Response shapes unchanged
- [ ] Status codes match baseline
- [ ] Performance within 5% of baseline
- [ ] No new database locks
- [ ] No new dependencies affecting API

**Validation Evidence:**
```bash
# Run regression tests
pytest tests/cron/api_gateway/regression/ -v --tb=short

# Compare with baseline
pytest tests/cron/api_gateway/regression/ --json-report --json-report-file=phase2-regression.json
diff baseline.json phase2-regression.json
```

**Definition of Done:**
- All regression tests pass
- No breaking changes detected
- Performance within threshold
- Gate passed for Phase 3

---

### TASK-2.8: Phase 2 Definition of Done Verification

**Phase:** 2  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Validate all Phase 2 acceptance criteria met before proceeding to Phase 3.

**Validation Checklist:**
- [ ] OAuth client implemented with token caching
- [ ] External API client implemented with retry logic
- [ ] Mock API server created for testing
- [ ] All Phase 2 unit tests passing
- [ ] Coverage ≥90% for oauth and api modules
- [ ] Integration tests validate OAuth flow end-to-end
- [ ] Error handling tested for all failure scenarios
- [ ] API-Gateway regression tests pass
- [ ] All PRs merged

**Validation Evidence:**
```bash
# Run all Phase 2 tests
pytest tests/cron/unit/oauth/ tests/cron/unit/api/ tests/cron/integration/ -v --cov=app/cron/oauth --cov=app/cron/api

# Verify coverage
pytest tests/cron/unit/oauth/ tests/cron/unit/api/ --cov=app/cron/oauth --cov=app/cron/api --cov-fail-under=90

# Run regression tests
pytest tests/cron/api_gateway/regression/ -v
```

**Definition of Done:**
- All checklist items verified
- All tests passing
- Coverage ≥90%
- Phase 2 complete gate passed

---

## Phase 3: Batch Ingestion & Persistence

**Objective:** Implement batch processor with UPSERT logic and transaction isolation.

---

### TASK-3.1: Implement Database Repositories

**Phase:** 3  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 3 days

**Description:**  
Create repository pattern for UPSERT operations on all target tables matching actual database schema.

**Files/Directories Impacted:**
```
app/cron/db/repositories.py
tests/cron/unit/db/test_repositories.py
```

**Dependencies:** TASK-1.4, Phase 2 complete

**Implementation Requirements:**

**Classes:**
1. `TeamMemberRepository` - UPSERT operations for:
   - `upsert_category(category_name)` → category_id
   - `upsert_skill(skill_name, category_id)` → skill_id
   - `upsert_team_member(member_data)` → team_member_id
   - `upsert_team_member_skills(team_member_id, skills, category_id)`
   - `upsert_allocations(team_member_id, allocations)`
   - `upsert_certifications(team_member_id, certifications, category_id)`

2. `BatchStateRepository` - Batch state management:
   - `initialize_batch(batch_id, correlation_id, total_records)`
   - `update_batch_status(batch_id, status, ...)`
   - `get_failed_batches()` → List[Dict]
   - `audit_log(correlation_id, event_type, status, ...)`

**Schema Alignment (from actual payload structure):**
- category_master: SMALLINT GENERATED ALWAYS for category_id (from skill.category)
- skill_master: VARCHAR(50) for skill_id (from skill.skill_id), skill_name (from skill.name), category_id FK
- team_member: team_member_id, designation, profile_type, is_active (derived from team_member_status), experience_in_months, base_location, work_type (from work-mode: wfh/wfo/hybrid), profile_url (from profile)
- team_member_allocation: team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted
- team_member_skill: team_member_id, skill_id, rating, experience_in_months, is_deleted (from payload)
- skill_certification: certifications array in payload (if not empty)

**Acceptance Criteria:**
- [ ] All UPSERT methods implemented
- [ ] Natural key conflicts handled via ON CONFLICT
- [ ] Foreign key relationships maintained
- [ ] Batch state transitions recorded
- [ ] Audit logging implemented
- [ ] Unit tests cover:
  - [ ] Successful UPSERT
  - [ ] Duplicate data (idempotency)
  - [ ] Missing required fields
  - [ ] Foreign key violations
  - [ ] Batch state transitions
  - [ ] Audit log entries
- [ ] Unit test coverage ≥90%

**Validation Evidence:**
```bash
# Run unit tests
pytest tests/cron/unit/db/test_repositories.py -v --cov=app/cron/db/repositories

# Verify coverage
pytest tests/cron/unit/db/test_repositories.py --cov=app/cron/db/repositories --cov-fail-under=90
```

**Definition of Done:**
- All repositories implemented
- All unit tests pass
- Coverage ≥90%
- Schema alignment verified
- PR approved

---

### TASK-3.2: Implement Batch Processor

**Phase:** 3  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 2 days

**Description:**  
Create batch processor with transaction isolation and state management.

**Files/Directories Impacted:**
```
app/cron/processing/batch_processor.py
tests/cron/unit/processing/test_batch_processor.py
```

**Dependencies:** TASK-3.1

**Implementation Requirements:**

**Class:** `BatchProcessor`
- `process_batch(batch_id, team_members)` → bool
- `process_all_batches(payload)` → (successful, failed)
- `_mark_batch_failed(batch_id, error_message)`
- Transaction boundary per batch
- Rollback on any error
- State tracking throughout lifecycle
- Dry run mode support

**Processing Order:**
1. Initialize batch state (PENDING) using metadata.batch_id
2. Update to PROCESSING
3. Process each team_member in team_members array:
   - Extract category from each skill.category → UPSERT category_master
   - UPSERT skill_master using skill.skill_id, skill.name, category_id
   - UPSERT team_member (map work-mode → work_type, profile → profile_url, team_member_status → is_active)
   - UPSERT team_member_skill using skill.rating, skill.experience_in_months, skill.is_deleted
   - UPSERT team_member_allocation from allocations array
   - UPSERT skill_certification from skill.certifications array (if not empty)
4. Update to SUCCESS/FAILED
5. Audit log entry

**Acceptance Criteria:**
- [ ] Batch processed within single transaction
- [ ] Transaction rolled back on any error
- [ ] Batch state tracked throughout lifecycle
- [ ] All team member data persisted correctly
- [ ] Dry run mode works without DB writes
- [ ] Error classification used for failures
- [ ] Unit tests cover:
  - [ ] Successful batch processing
  - [ ] Partial failure (rollback)
  - [ ] Empty batch
  - [ ] Invalid data
  - [ ] Transaction isolation
  - [ ] State transitions
  - [ ] Dry run mode
- [ ] Unit test coverage ≥90%

**Validation Evidence:**
```bash
# Run unit tests
pytest tests/cron/unit/processing/test_batch_processor.py -v --cov=app/cron/processing/batch_processor

# Verify coverage
pytest tests/cron/unit/processing/test_batch_processor.py --cov=app/cron/processing/batch_processor --cov-fail-under=90
```

**Definition of Done:**
- Batch processor implemented
- All unit tests pass
- Coverage ≥90%
- Transaction isolation verified
- PR approved

---

### TASK-3.3: Implement Error Classifier

**Phase:** 3  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Create error classification module for retry eligibility determination.

**Files/Directories Impacted:**
```
app/cron/processing/error_classifier.py
tests/cron/unit/processing/test_error_classifier.py
```

**Dependencies:** Phase 2 complete

**Implementation Requirements:**

**Enum:** `ErrorCategory`
- Retryable: NETWORK_ERROR, API_RATE_LIMIT, DATABASE_LOCK, TEMPORARY_UNAVAILABLE
- Non-retryable: AUTHENTICATION_ERROR, AUTHORIZATION_ERROR, VALIDATION_ERROR, SCHEMA_MISMATCH, CONSTRAINT_VIOLATION
- Infrastructure: DATABASE_CONNECTION_ERROR, OUT_OF_MEMORY

**Functions:**
- `classify_error(exception)` → ErrorCategory
- `is_retryable(error_category)` → bool

**Acceptance Criteria:**
- [ ] All common error types classified correctly
- [ ] Retryable vs non-retryable errors distinguished
- [ ] Network errors → NETWORK_ERROR
- [ ] HTTP 429 → API_RATE_LIMIT
- [ ] HTTP 401 → AUTHENTICATION_ERROR
- [ ] HTTP 503 → TEMPORARY_UNAVAILABLE
- [ ] IntegrityError → CONSTRAINT_VIOLATION
- [ ] OperationalError → DATABASE_CONNECTION_ERROR
- [ ] Unit tests cover:
  - [ ] All error categories
  - [ ] Each exception type
  - [ ] Retry eligibility logic
  - [ ] Unknown errors (default handling)
- [ ] Unit test coverage ≥95%

**Validation Evidence:**
```bash
# Run unit tests
pytest tests/cron/unit/processing/test_error_classifier.py -v --cov=app/cron/processing/error_classifier

# Verify coverage
pytest tests/cron/unit/processing/test_error_classifier.py --cov=app/cron/processing/error_classifier --cov-fail-under=95
```

**Definition of Done:**
- Error classifier implemented
- All unit tests pass
- Coverage ≥95%
- All error types classified
- PR approved

---

### TASK-3.4: Integration Tests for Batch Processing

**Phase:** 3  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 2 days

**Description:**  
End-to-end integration tests for batch processing with real database.

**Files/Directories Impacted:**
```
tests/cron/integration/test_batch_processing.py
```

**Dependencies:** TASK-3.1, TASK-3.2, TASK-3.3

**Test Scenarios:**
- [ ] Successful batch processing end-to-end
- [ ] Multiple batches processed sequentially
- [ ] Transaction rollback on error
- [ ] Idempotency (same batch processed twice)
- [ ] Partial data handling
- [ ] Category and skill creation
- [ ] Foreign key relationships
- [ ] Batch state tracking
- [ ] Audit log entries

**Acceptance Criteria:**
- [ ] All integration tests pass
- [ ] Uses test database
- [ ] Cleanup after tests
- [ ] Idempotency verified
- [ ] Transaction isolation verified
- [ ] Tests run in < 60 seconds

**Validation Evidence:**
```bash
# Run integration tests
pytest tests/cron/integration/test_batch_processing.py -v --tb=short

# Verify idempotency
pytest tests/cron/integration/test_batch_processing.py::test_idempotency -v

# Check database state
psql -h localhost -p 5433 -U postgres -d ib_job_skill_mapping_test -c "SELECT * FROM ingestion_batch_state;"
```

**Definition of Done:**
- All integration tests pass
- Idempotency verified
- Transaction isolation verified
- PR approved

---

### TASK-3.5: Unit Tests for Processing Module

**Phase:** 3  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 2 days

**Description:**  
Comprehensive unit tests for batch processor and error classifier.

**Files/Directories Impacted:**
```
tests/cron/unit/processing/
├── test_batch_processor.py (from TASK-3.2)
└── test_error_classifier.py (from TASK-3.3)
```

**Dependencies:** TASK-3.2, TASK-3.3

**Test Coverage Requirements:**
- batch_processor.py: ≥90%
- error_classifier.py: ≥95%

**Test Scenarios:**
- [ ] Batch processor: all methods covered
- [ ] Error classifier: all error types covered
- [ ] Mock database connections
- [ ] Mock repository calls
- [ ] Transaction behavior simulated
- [ ] State transitions verified
- [ ] Error handling paths

**Acceptance Criteria:**
- [ ] All unit tests pass
- [ ] Coverage ≥90% for batch_processor
- [ ] Coverage ≥95% for error_classifier
- [ ] Fast execution (< 5 seconds)
- [ ] No database calls (mocked)

**Validation Evidence:**
```bash
# Run all processing unit tests
pytest tests/cron/unit/processing/ -v --cov=app/cron/processing --cov-report=term

# Verify coverage thresholds
pytest tests/cron/unit/processing/test_batch_processor.py --cov=app/cron/processing/batch_processor --cov-fail-under=90
pytest tests/cron/unit/processing/test_error_classifier.py --cov=app/cron/processing/error_classifier --cov-fail-under=95
```

**Definition of Done:**
- All unit tests pass
- Coverage thresholds met
- Fast execution
- PR approved

---

### TASK-3.6: Validate UPSERT Idempotency

**Phase:** 3  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Create specific tests to validate UPSERT idempotency for all tables.

**Files/Directories Impacted:**
```
tests/cron/integration/test_upsert_idempotency.py
```

**Dependencies:** TASK-3.1, TASK-3.2

**Test Scenarios:**
- [ ] Same category inserted twice → same ID
- [ ] Same skill inserted twice → same ID
- [ ] Same team member inserted twice → data updated
- [ ] Same skill for team member twice → data updated
- [ ] Same allocation twice → data updated
- [ ] Same certification twice → no duplicates
- [ ] Full batch processed twice → identical state

**Acceptance Criteria:**
- [ ] All idempotency tests pass
- [ ] No duplicate records created
- [ ] Natural keys respected
- [ ] UPSERT behavior verified for all tables
- [ ] Foreign key relationships maintained

**Validation Evidence:**
```bash
# Run idempotency tests
pytest tests/cron/integration/test_upsert_idempotency.py -v --tb=short

# Verify no duplicates
psql -h localhost -p 5433 -U postgres -d ib_job_skill_mapping_test -c "
SELECT skill_name, COUNT(*) FROM skill_master GROUP BY skill_name HAVING COUNT(*) > 1;
"
```

**Definition of Done:**
- All idempotency tests pass
- No duplicates in database
- UPSERT verified for all tables
- PR approved

---

### TASK-3.7: Data Validation and Transformation Tests

**Phase:** 3  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Test data validation and transformation logic (e.g., skill_id generation from skill_name).

**Files/Directories Impacted:**
```
tests/cron/unit/db/test_data_transformations.py
```

**Dependencies:** TASK-3.1

**Test Scenarios:**
- [ ] skill_id generated from skill_name correctly
- [ ] Special characters handled in skill_id
- [ ] Long skill names truncated to 50 chars
- [ ] Category names normalized
- [ ] Optional fields handled correctly
- [ ] work_type enum validation
- [ ] Date format handling

**Acceptance Criteria:**
- [ ] All transformation tests pass
- [ ] Edge cases covered
- [ ] Special characters handled
- [ ] Truncation tested
- [ ] NULL handling verified

**Validation Evidence:**
```bash
# Run transformation tests
pytest tests/cron/unit/db/test_data_transformations.py -v
```

**Definition of Done:**
- All transformation tests pass
- Edge cases covered
- PR approved

---

### TASK-3.8: API-Gateway Regression After Phase 3

**Phase:** 3  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Run API-Gateway regression tests after batch processing implementation.

**Files/Directories Impacted:**
```
tests/cron/api_gateway/regression/
```

**Dependencies:** Phase 3 completion

**Validation Checklist:**
- [ ] All API-Gateway endpoints functional after batch insert
- [ ] Data from ingestion queryable via API
- [ ] No performance degradation
- [ ] Foreign key relationships intact
- [ ] No data corruption

**Test Scenarios:**
- [ ] Health endpoint still works after ingestion
- [ ] Metrics endpoint still works after ingestion
- [ ] Bulk upsert endpoint still works after ingestion
- [ ] JD skill mapping (requisition) endpoint unaffected
- [ ] Matches retrieval endpoint unaffected
- [ ] Data from ingestion queryable via existing APIs

**Validation Evidence:**
```bash
# Insert test data via batch processor
pytest tests/cron/integration/test_batch_processing.py::test_successful_batch -v

# Run regression tests
pytest tests/cron/api_gateway/regression/ -v --tb=short

# Verify data queryable via bulk upsert endpoint
curl -X POST http://localhost:8001/api/v1/team-members/skill-availability/bulk-upsert \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

**Definition of Done:**
- All regression tests pass
- Data queryable via API
- No performance degradation
- Gate passed for Phase 4

---

### TASK-3.9: Phase 3 Coverage Report

**Phase:** 3  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Generate coverage report for Phase 3 modules and verify thresholds.

**Modules to Report:**
- app/cron/db/repositories.py
- app/cron/processing/batch_processor.py
- app/cron/processing/error_classifier.py

**Coverage Targets:**
- repositories.py: ≥90%
- batch_processor.py: ≥90%
- error_classifier.py: ≥95%
- Overall Phase 3: ≥90%

**Validation Evidence:**
```bash
# Generate coverage report
pytest tests/cron/unit/db/test_repositories.py tests/cron/unit/processing/ \
  --cov=app/cron/db/repositories \
  --cov=app/cron/processing \
  --cov-report=html \
  --cov-report=term \
  --cov-report=xml

# Verify thresholds
pytest tests/cron/unit/db/test_repositories.py --cov=app/cron/db/repositories --cov-fail-under=90
pytest tests/cron/unit/processing/ --cov=app/cron/processing --cov-fail-under=90

# View HTML report
open htmlcov/index.html
```

**Definition of Done:**
- Coverage report generated
- All thresholds met
- Report archived
- Gate passed

---

### TASK-3.10: Phase 3 Definition of Done Verification

**Phase:** 3  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Validate all Phase 3 acceptance criteria met before proceeding to Phase 4.

**Validation Checklist:**
- [ ] Database repositories implemented for all tables
- [ ] Batch processor with transaction isolation complete
- [ ] Error classifier implemented
- [ ] UPSERT logic working correctly
- [ ] Batch state tracked throughout lifecycle
- [ ] Dry run mode functional
- [ ] All Phase 3 unit tests passing
- [ ] Coverage ≥90% for critical modules
- [ ] Integration tests validate end-to-end batch processing
- [ ] Idempotency validated (same batch twice = same result)
- [ ] API-Gateway regression tests pass
- [ ] All PRs merged

**Validation Evidence:**
```bash
# Run all Phase 3 tests
pytest tests/cron/unit/db/test_repositories.py tests/cron/unit/processing/ tests/cron/integration/test_batch_processing.py -v

# Verify coverage
pytest tests/cron/unit/db/test_repositories.py tests/cron/unit/processing/ \
  --cov=app/cron/db/repositories --cov=app/cron/processing --cov-fail-under=90

# Run regression tests
pytest tests/cron/api_gateway/regression/ -v
```

**Definition of Done:**
- All checklist items verified
- All tests passing
- Coverage ≥90%
- Phase 3 complete gate passed

---

## Phase 4: Batch Retry & Failure Isolation

**Objective:** Implement retry manager with exponential backoff and selective batch retry.

---

### TASK-4.1: Implement Retry Manager

**Phase:** 4  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 2 days

**Description:**  
Create retry manager with exponential backoff and retry eligibility checks.

**Files/Directories Impacted:**
```
app/cron/processing/retry_manager.py
tests/cron/unit/processing/test_retry_manager.py
```

**Dependencies:** Phase 3 complete

**Implementation Requirements:**

**Class:** `RetryManager`
- `calculate_retry_delay(retry_count)` → int (seconds)
- `should_retry_batch(batch)` → bool
- `retry_failed_batches()` → (successful, failed)
- `_mark_batch_abandoned(batch_id)`

**Retry Logic:**
- Exponential backoff: base_delay * 2^(retry_count - 1)
- Default delays: 60s, 120s, 240s
- Max retries: 3 (configurable)
- Only retryable error categories
- Batch state: FAILED → PROCESSING → SUCCESS/FAILED/ABANDONED

**Acceptance Criteria:**
- [ ] Retry manager identifies failed batches correctly
- [ ] Exponential backoff calculated correctly
- [ ] Only retryable errors trigger retry
- [ ] Max retries enforced
- [ ] Batches marked as ABANDONED after max retries
- [ ] Successful batches not retried
- [ ] Unit tests cover:
  - [ ] Retry delay calculation
  - [ ] Retry eligibility logic
  - [ ] Successful retry
  - [ ] Failed retry
  - [ ] Max retries exceeded
  - [ ] Non-retryable errors skipped
  - [ ] Batch abandonment
- [ ] Unit test coverage ≥90%

**Validation Evidence:**
```bash
# Run unit tests
pytest tests/cron/unit/processing/test_retry_manager.py -v --cov=app/cron/processing/retry_manager

# Verify coverage
pytest tests/cron/unit/processing/test_retry_manager.py --cov=app/cron/processing/retry_manager --cov-fail-under=90
```

**Definition of Done:**
- Retry manager implemented
- All unit tests pass
- Coverage ≥90%
- Exponential backoff verified
- PR approved

---

### TASK-4.2: Implement CLI Entry Point with Retry Flag

**Phase:** 4  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 2 days

**Description:**  
Create main CLI entry point with `--retry-failed` flag and pre-run health checks.

**Files/Directories Impacted:**
```
app/cron/main.py
tests/cron/unit/test_main.py
```

**Dependencies:** TASK-4.1

**Implementation Requirements:**

**CLI Arguments:**
- `--retry-failed` - Retry failed batches only
- `--dry-run` - Dry run mode
- `--log-level` - Logging level (DEBUG, INFO, WARNING, ERROR)

**Functions:**
- `parse_args()` - Parse command line arguments
- `pre_run_checks(engine, logger)` - Pre-flight health checks
- `run_ingestion(logger, correlation_id)` - Run new ingestion
- `run_retry(logger, correlation_id)` - Retry failed batches
- `main()` - Main entry point

**Exit Codes:**
- 0: SUCCESS
- 1: PARTIAL_SUCCESS (some batches failed)
- 2: FATAL_ERROR
- 3: SCHEMA_VERSION_MISMATCH
- 4: AUTHENTICATION_FAILED

**Pre-Run Checks:**
- Database connection
- Schema version validation
- OAuth authentication

**Acceptance Criteria:**
- [ ] CLI supports all required flags
- [ ] Pre-run health checks execute
- [ ] Exit codes match specification
- [ ] Correlation ID generated and set
- [ ] Logging configured correctly
- [ ] Unit tests cover:
  - [ ] Argument parsing
  - [ ] Pre-run checks (success/failure)
  - [ ] Run ingestion path
  - [ ] Run retry path
  - [ ] Dry run mode
  - [ ] Exit codes
- [ ] Unit test coverage ≥85%

**Validation Evidence:**
```bash
# Test CLI help
python -m app.cron.main --help

# Test dry run
python -m app.cron.main --dry-run --log-level DEBUG

# Test retry flag
python -m app.cron.main --retry-failed

# Run unit tests
pytest tests/cron/unit/test_main.py -v --cov=app/cron/main --cov-fail-under=85
```

**Definition of Done:**
- CLI entry point implemented
- All unit tests pass
- Coverage ≥85%
- Manual execution tested
- PR approved

---

### TASK-4.3: Integration Tests for Retry Flow

**Phase:** 4  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 2 days

**Description:**  
End-to-end integration tests for batch retry scenarios.

**Files/Directories Impacted:**
```
tests/cron/integration/test_retry_flow.py
```

**Dependencies:** TASK-4.1, TASK-4.2

**Test Scenarios:**
- [ ] Batch fails on first attempt, succeeds on retry
- [ ] Batch fails multiple times, reaches max retries
- [ ] Successful batches not retried
- [ ] Exponential backoff delays observed
- [ ] Non-retryable errors not retried
- [ ] Batch marked ABANDONED after max retries
- [ ] Retry isolation (batch_id specific)
- [ ] State transitions tracked correctly

**Acceptance Criteria:**
- [ ] All integration tests pass
- [ ] Retry flow validated end-to-end
- [ ] Batch isolation verified
- [ ] No reprocessing of successful batches
- [ ] Tests run in < 120 seconds

**Validation Evidence:**
```bash
# Run retry flow tests
pytest tests/cron/integration/test_retry_flow.py -v --tb=short

# Verify batch isolation
pytest tests/cron/integration/test_retry_flow.py::test_batch_isolation -v

# Check database state
psql -h localhost -p 5433 -U postgres -d ib_job_skill_mapping_test -c "
SELECT batch_id, status, retry_count FROM ingestion_batch_state;
"
```

**Definition of Done:**
- All integration tests pass
- Retry flow verified
- Batch isolation verified
- PR approved

---

### TASK-4.4: Unit Tests for Retry Module

**Phase:** 4  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Comprehensive unit tests for retry manager with all edge cases.

**Files/Directories Impacted:**
```
tests/cron/unit/processing/test_retry_manager.py (from TASK-4.1)
```

**Dependencies:** TASK-4.1

**Test Coverage Requirements:**
- retry_manager.py: ≥90%
- All methods covered
- All retry scenarios

**Test Scenarios:**
- [ ] Exponential backoff calculation (60s, 120s, 240s)
- [ ] Retry eligibility based on error category
- [ ] Retry eligibility based on retry count
- [ ] Successful retry updates state
- [ ] Failed retry increments count
- [ ] Max retries triggers abandonment
- [ ] API client called for batch refetch
- [ ] Batch processor called for retry
- [ ] State transitions recorded
- [ ] Audit log entries created

**Acceptance Criteria:**
- [ ] All unit tests pass
- [ ] Coverage ≥90%
- [ ] Fast execution (< 3 seconds)
- [ ] Mock dependencies
- [ ] No database calls

**Validation Evidence:**
```bash
# Run unit tests
pytest tests/cron/unit/processing/test_retry_manager.py -v --cov=app/cron/processing/retry_manager --cov-report=term

# Verify coverage
pytest tests/cron/unit/processing/test_retry_manager.py --cov=app/cron/processing/retry_manager --cov-fail-under=90

# Check execution time
pytest tests/cron/unit/processing/test_retry_manager.py --durations=10
```

**Definition of Done:**
- All unit tests pass
- Coverage ≥90%
- Fast execution
- PR approved

---

### TASK-4.5: Simulate Failure and Retry Scenarios

**Phase:** 4  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Create tests that simulate various failure scenarios and validate retry behavior.

**Files/Directories Impacted:**
```
tests/cron/integration/test_failure_scenarios.py
```

**Dependencies:** TASK-4.3

**Test Scenarios:**
- [ ] Network timeout during API call → retry succeeds
- [ ] Database connection lost → retry succeeds
- [ ] API rate limit (429) → retry succeeds
- [ ] Authentication failure (401) → no retry
- [ ] Validation error → no retry
- [ ] Constraint violation → no retry
- [ ] Partial batch failure → rollback + retry
- [ ] All retries exhausted → abandoned

**Acceptance Criteria:**
- [ ] All failure scenarios tested
- [ ] Retry behavior correct for each scenario
- [ ] Non-retryable errors not retried
- [ ] State transitions correct
- [ ] Tests can run in CI

**Validation Evidence:**
```bash
# Run failure scenario tests
pytest tests/cron/integration/test_failure_scenarios.py -v --tb=short

# Verify abandoned batches
pytest tests/cron/integration/test_failure_scenarios.py::test_max_retries_exhausted -v
```

**Definition of Done:**
- All failure scenarios tested
- Retry behavior validated
- PR approved

---

### TASK-4.6: API-Gateway Regression After Phase 4

**Phase:** 4  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Run API-Gateway regression tests after retry implementation.

**Files/Directories Impacted:**
```
tests/cron/api_gateway/regression/
```

**Dependencies:** Phase 4 completion

**Validation Checklist:**
- [ ] API-Gateway endpoints functional
- [ ] No impact from retry logic
- [ ] No database locks from retries
- [ ] Performance unchanged

**Validation Evidence:**
```bash
# Run regression tests
pytest tests/cron/api_gateway/regression/ -v --tb=short

# Compare with baseline
pytest tests/cron/api_gateway/regression/ --json-report --json-report-file=phase4-regression.json
```

**Definition of Done:**
- All regression tests pass
- No impact detected
- Gate passed for Phase 5

---

### TASK-4.7: Phase 4 Definition of Done Verification

**Phase:** 4  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Validate all Phase 4 acceptance criteria met before proceeding to Phase 5.

**Validation Checklist:**
- [ ] Retry manager implemented with exponential backoff
- [ ] CLI supports `--retry-failed` flag
- [ ] Max retries enforced (3 attempts)
- [ ] Batches marked as ABANDONED after max retries
- [ ] Only failed batches retried
- [ ] All Phase 4 unit tests passing
- [ ] Coverage ≥90% for retry_manager
- [ ] Integration tests validate retry scenarios
- [ ] Manual retry tested end-to-end
- [ ] API-Gateway regression tests pass
- [ ] All PRs merged

**Validation Evidence:**
```bash
# Run all Phase 4 tests
pytest tests/cron/unit/processing/test_retry_manager.py tests/cron/unit/test_main.py tests/cron/integration/test_retry_flow.py -v

# Verify coverage
pytest tests/cron/unit/processing/test_retry_manager.py --cov=app/cron/processing/retry_manager --cov-fail-under=90

# Test manual retry
python -m app.cron.main --retry-failed --dry-run

# Run regression tests
pytest tests/cron/api_gateway/regression/ -v
```

**Definition of Done:**
- All checklist items verified
- All tests passing
- Coverage ≥90%
- Phase 4 complete gate passed

---

## Phase 5: Scheduling & Runtime Execution

**Objective:** Configure scheduler and create operational scripts for production execution.

---

### TASK-5.1: Create Shell Wrapper Script

**Phase:** 5  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Create bash script to invoke Python ingestion with environment loading and logging.

**Files/Directories Impacted:**
```
scripts/run_ingestion.sh
tests/cron/integration/test_shell_wrapper.py
```

**Dependencies:** TASK-4.2

**Implementation Requirements:**
- Load environment variables from `.env`
- Set up log directory
- Generate timestamped log file
- Invoke Python with arguments
- Capture exit code
- Log execution start/end

**Script Features:**
- Configurable LOG_DIR
- Configurable PYTHON_BIN
- Argument forwarding to Python
- Error handling
- Executable permissions

**Acceptance Criteria:**
- [ ] Script loads environment variables
- [ ] Script logs output to dated log file
- [ ] Script propagates exit code
- [ ] Script accepts CLI arguments
- [ ] Script handles missing .env gracefully
- [ ] Script tested with various arguments
- [ ] Integration tests verify script execution

**Validation Evidence:**
```bash
# Test script execution
./scripts/run_ingestion.sh --dry-run

# Test with retry flag
./scripts/run_ingestion.sh --retry-failed --log-level DEBUG

# Verify exit code propagation
./scripts/run_ingestion.sh --dry-run
echo $?

# Run integration tests
pytest tests/cron/integration/test_shell_wrapper.py -v
```

**Definition of Done:**
- Shell script created
- Integration tests pass
- Manual execution tested
- PR approved

---

### TASK-5.2: Create Cron Configuration

**Phase:** 5  
**Priority:** P1 (High)  
**Estimated Effort:** 0.5 days

**Description:**  
Create crontab configuration for 2:00 AM IST (8:30 PM UTC) daily execution.

**Files/Directories Impacted:**
```
deployment/cron.d/ib-job-skill-ingestion
deployment/install_cron.sh
```

**Dependencies:** TASK-5.1

**Implementation Requirements:**

**Crontab Entry:**
```
30 20 * * * app /opt/ib-job-skill-mapping-system/scripts/run_ingestion.sh
```

**Installation Script:**
- Create log directory with correct permissions
- Copy cron configuration
- Validate crontab syntax
- Test dry run

**Acceptance Criteria:**
- [ ] Crontab configured for 2:00 AM IST
- [ ] Installation script creates log directory
- [ ] Installation script validates configuration
- [ ] Dry run tested
- [ ] Documentation updated

**Validation Evidence:**
```bash
# Run installation script
sudo ./deployment/install_cron.sh

# Verify crontab installed
sudo crontab -l -u app | grep ib-job-skill-ingestion

# Test dry run
sudo -u app /opt/ib-job-skill-mapping-system/scripts/run_ingestion.sh --dry-run
```

**Definition of Done:**
- Crontab configuration created
- Installation script created
- Dry run tested
- Documentation complete
- PR approved

---

### TASK-5.3: Create Kubernetes CronJob Manifest

**Phase:** 5  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Create Kubernetes CronJob YAML for containerized deployment.

**Files/Directories Impacted:**
```
deployment/k8s/cronjob-ingestion.yaml
deployment/k8s/secrets.yaml
deployment/k8s/configmap.yaml
deployment/k8s/serviceaccount.yaml
```

**Dependencies:** TASK-5.1

**Implementation Requirements:**

**CronJob Configuration:**
- Schedule: `"30 20 * * *"` (8:30 PM UTC)
- Concurrency Policy: `Forbid`
- Resources: 512Mi-2Gi memory, 0.5-1 CPU
- Restart Policy: OnFailure
- Secrets: postgres-secret, external-api-secret
- Service Account: team-data-ingestion-sa

**RBAC:**
- ServiceAccount for ingestion
- Role for secret access
- RoleBinding

**Acceptance Criteria:**
- [ ] CronJob manifest valid YAML
- [ ] Secrets configured correctly
- [ ] Resource limits appropriate
- [ ] RBAC configured
- [ ] Concurrency policy prevents overlaps
- [ ] Manifest tested on staging cluster

**Validation Evidence:**
```bash
# Validate manifest
kubectl apply -f deployment/k8s/ --dry-run=client

# Deploy to staging
kubectl apply -f deployment/k8s/ -n ib-job-skill-mapping-staging

# Manually trigger CronJob
kubectl create job --from=cronjob/team-data-ingestion manual-test -n ib-job-skill-mapping-staging

# View logs
kubectl logs -n ib-job-skill-mapping-staging -l app=team-data-ingestion --tail=100
```

**Definition of Done:**
- CronJob manifest created
- RBAC configured
- Staging deployment successful
- PR approved

---

### TASK-5.4: Configure Log Rotation

**Phase:** 5  
**Priority:** P2 (Medium)  
**Estimated Effort:** 0.5 days

**Description:**  
Set up log rotation for ingestion logs.

**Files/Directories Impacted:**
```
deployment/logrotate.d/ib-job-skill-ingestion
```

**Dependencies:** TASK-5.2

**Implementation Requirements:**
- Daily rotation
- Retain 30 days
- Compress old logs
- Create new files with correct permissions
- Post-rotate notification

**Acceptance Criteria:**
- [ ] Log rotation configured
- [ ] Logs retained for 30 days
- [ ] Old logs compressed
- [ ] Rotation tested
- [ ] Permissions correct

**Validation Evidence:**
```bash
# Test log rotation
sudo logrotate -f /etc/logrotate.d/ib-job-skill-ingestion

# Verify old logs compressed
ls -lh /var/log/ib-job-skill-ingestion/*.gz

# Check permissions
ls -l /var/log/ib-job-skill-ingestion/
```

**Definition of Done:**
- Log rotation configured
- Testing successful
- PR approved

---

### TASK-5.5: Unit Tests for Main Entry Point

**Phase:** 5  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Comprehensive unit tests for main.py CLI entry point.

**Files/Directories Impacted:**
```
tests/cron/unit/test_main.py (from TASK-4.2)
```

**Dependencies:** TASK-4.2

**Test Coverage Requirements:**
- main.py: ≥85%
- All functions covered
- All execution paths

**Test Scenarios:**
- [ ] Argument parsing for all flags
- [ ] Pre-run checks success
- [ ] Pre-run checks failure (DB, schema, auth)
- [ ] Run ingestion path
- [ ] Run retry path
- [ ] Dry run mode
- [ ] Exit code SUCCESS
- [ ] Exit code PARTIAL_SUCCESS
- [ ] Exit code FATAL_ERROR
- [ ] Exit code SCHEMA_VERSION_MISMATCH
- [ ] Exit code AUTHENTICATION_FAILED
- [ ] Correlation ID generation
- [ ] Logging configuration

**Acceptance Criteria:**
- [ ] All unit tests pass
- [ ] Coverage ≥85%
- [ ] All exit codes tested
- [ ] Fast execution (< 5 seconds)
- [ ] Mock all dependencies

**Validation Evidence:**
```bash
# Run unit tests
pytest tests/cron/unit/test_main.py -v --cov=app/cron/main --cov-report=term

# Verify coverage
pytest tests/cron/unit/test_main.py --cov=app/cron/main --cov-fail-under=85

# Check execution time
pytest tests/cron/unit/test_main.py --durations=10
```

**Definition of Done:**
- All unit tests pass
- Coverage ≥85%
- All paths tested
- PR approved

---

### TASK-5.6: Phase 5 Definition of Done Verification

**Phase:** 5  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Validate all Phase 5 acceptance criteria met before proceeding to Phase 6.

**Validation Checklist:**
- [ ] Shell wrapper script created and tested
- [ ] Crontab configured for 2:00 AM IST
- [ ] Kubernetes CronJob manifest created
- [ ] Log rotation configured
- [ ] Manual execution tested end-to-end
- [ ] Dry run tested
- [ ] Cron execution simulated
- [ ] Unit tests for main.py pass with ≥85% coverage
- [ ] Documentation updated
- [ ] All PRs merged

**Validation Evidence:**
```bash
# Test shell script
./scripts/run_ingestion.sh --dry-run

# Test CLI directly
python -m app.cron.main --dry-run

# Run unit tests
pytest tests/cron/unit/test_main.py -v --cov=app/cron/main --cov-fail-under=85

# Verify crontab
cat deployment/cron.d/ib-job-skill-ingestion

# Verify K8s manifest
kubectl apply -f deployment/k8s/ --dry-run=client
```

**Definition of Done:**
- All checklist items verified
- All tests passing
- Deployment artifacts ready
- Phase 5 complete gate passed

---

## Phase 6: Testing, Coverage & Validation (EXTENDED)

**Objective:** Comprehensive testing, coverage enforcement, and regression validation.

---

### TASK-6.1: Overall Unit Test Coverage Report

**Phase:** 6  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Generate comprehensive unit test coverage report for entire ingestion service.

**Modules to Report:**
- app/cron/config.py
- app/cron/main.py
- app/cron/utils/logging.py
- app/cron/oauth/token_client.py
- app/cron/api/external_client.py
- app/cron/db/*.py
- app/cron/processing/*.py

**Coverage Targets:**
- Overall: ≥85%
- Critical paths (processing, retry, db): ≥90%
- oauth, api: ≥90%
- config, logging, main: ≥85%

**Deliverables:**
- HTML coverage report
- XML coverage report (for CI)
- Terminal coverage summary
- Coverage badge metrics

**Validation Evidence:**
```bash
# Generate comprehensive coverage report
pytest tests/cron/unit/ \
  --cov=app/cron \
  --cov-report=html \
  --cov-report=xml \
  --cov-report=term \
  --cov-report=json

# Verify overall threshold
pytest tests/cron/unit/ --cov=app/cron --cov-fail-under=85

# Verify critical path thresholds
pytest tests/cron/unit/processing/ tests/cron/unit/db/ \
  --cov=app/cron/processing \
  --cov=app/cron/db \
  --cov-fail-under=90

# View HTML report
open htmlcov/index.html
```

**Acceptance Criteria:**
- [ ] Overall coverage ≥85%
- [ ] Critical paths ≥90%
- [ ] All reports generated
- [ ] Coverage badge updated
- [ ] Report archived

**Definition of Done:**
- Coverage report generated
- Thresholds met
- Reports archived
- Badge updated
- Gate passed

---

### TASK-6.2: Integration Test Suite Consolidation

**Phase:** 6  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Consolidate all integration tests and ensure comprehensive end-to-end coverage.

**Integration Tests to Consolidate:**
- Database setup (TASK-1.7)
- OAuth integration (TASK-2.6)
- API integration (TASK-2.6)
- Batch processing (TASK-3.4)
- UPSERT idempotency (TASK-3.6)
- Retry flow (TASK-4.3)
- Failure scenarios (TASK-4.5)
- Shell wrapper (TASK-5.1)

**Test Organization:**
```
tests/cron/integration/
├── __init__.py
├── conftest.py
├── mock_api_server.py
├── test_database_setup.py
├── test_oauth_integration.py
├── test_api_integration.py
├── test_batch_processing.py
├── test_upsert_idempotency.py
├── test_retry_flow.py
├── test_failure_scenarios.py
└── test_shell_wrapper.py
```

**Acceptance Criteria:**
- [ ] All integration tests consolidated
- [ ] Shared fixtures in conftest.py
- [ ] Test database setup automated
- [ ] All tests pass sequentially
- [ ] All tests pass in parallel (where safe)
- [ ] Tests run in < 300 seconds total
- [ ] Cleanup after each test

**Validation Evidence:**
```bash
# Run all integration tests sequentially
pytest tests/cron/integration/ -v --tb=short

# Run in parallel
pytest tests/cron/integration/ -v -n auto

# Measure execution time
pytest tests/cron/integration/ --durations=0

# Verify cleanup
pytest tests/cron/integration/ -v
psql -h localhost -p 5433 -U postgres -d ib_job_skill_mapping_test -c "\dt"
```

**Definition of Done:**
- All integration tests consolidated
- All tests pass
- Execution time acceptable
- PR approved

---

### TASK-6.3: API-Gateway Regression Test Suite

**Phase:** 6  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 2 days

**Description:**  
Comprehensive API-Gateway regression test suite to ensure zero breaking changes.

**Files/Directories Impacted:**
```
tests/cron/api_gateway/regression/
├── __init__.py
├── conftest.py
├── baseline_responses.json
├── test_health_metrics_regression.py
├── test_bulk_upsert_regression.py
├── test_jd_skill_mapping_regression.py
└── test_performance_regression.py
```

**Dependencies:** TASK-0.6

**Test Categories:**

1. **Functional Regression:**
   - GET `/health` - health check response shape and status codes
   - GET `/api/v1/metrics` - metrics availability and format
   - POST `/api/v1/team-members/skill-availability/bulk-upsert` - bulk upsert behavior
   - POST `/api/v1/jd-skill-mapping/` - requisition submission response shape
   - GET `/api/v1/jd-skill-mapping/{correlation_id}/matches` - matches retrieval behavior

2. **Performance Regression:**
   - Response time < baseline + 10%
   - Database query count unchanged
   - No N+1 query issues

3. **Data Integrity Regression:**
   - Query results before/after ingestion
   - Foreign key relationships
   - No data corruption

**Test Execution Scenarios:**
- [ ] Baseline (before any ingestion) - capture from test_api.py results
- [ ] After single batch ingestion via nightly job
- [ ] After multiple batch ingestion via nightly job
- [ ] Verify bulk-upsert endpoint unaffected by batch ingestion
- [ ] Verify JD skill mapping endpoint unaffected by batch ingestion
- [ ] Verify matches retrieval endpoint unaffected by batch ingestion

**Acceptance Criteria:**
- [ ] All regression tests pass
- [ ] No breaking changes detected
- [ ] Response shapes match baseline
- [ ] Status codes match baseline
- [ ] Performance within 10% of baseline
- [ ] Data integrity maintained
- [ ] Test report generated with comparison

**Validation Evidence:**
```bash
# Capture baseline
pytest tests/cron/api_gateway/regression/ --baseline

# Run after ingestion
pytest tests/cron/integration/test_batch_processing.py::test_successful_batch -v
pytest tests/cron/api_gateway/regression/ --compare-baseline

# Generate comparison report
pytest tests/cron/api_gateway/regression/ --json-report --json-report-file=regression-report.json

# View diff
python scripts/compare_regression_results.py baseline.json regression-report.json
```

**Definition of Done:**
- Regression suite complete
- All tests pass
- No breaking changes
- Report generated
- Gate passed

---

### TASK-6.4: Performance Benchmark Tests

**Phase:** 6  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Create performance benchmark tests to validate NFRs.

**Files/Directories Impacted:**
```
tests/cron/performance/
├── __init__.py
├── test_batch_throughput.py
└── test_memory_usage.py
```

**Performance Targets:**
- 10,000 records ingested in < 30 minutes
- Throughput ≥ 100 records/second
- Memory usage < 2 GB peak
- Database connection pool not exhausted

**Test Scenarios:**
- [ ] 100 record batch - measure time and memory
- [ ] 1,000 record batch - measure time and memory
- [ ] 10,000 record batch - measure time and memory
- [ ] Concurrent batch processing (if applicable)
- [ ] Memory profiling

**Acceptance Criteria:**
- [ ] All benchmarks meet NFRs
- [ ] 10,000 records in < 30 minutes
- [ ] Throughput ≥ 100 records/second
- [ ] Memory < 2 GB
- [ ] Benchmark report generated

**Validation Evidence:**
```bash
# Run performance benchmarks
pytest tests/cron/performance/ -v --benchmark-only

# Generate benchmark report
pytest tests/cron/performance/ --benchmark-json=benchmark-results.json

# Memory profiling
python -m memory_profiler tests/cron/performance/test_memory_usage.py
```

**Definition of Done:**
- Benchmarks meet NFRs
- Report generated
- PR approved

---

### TASK-6.5: End-to-End Smoke Tests

**Phase:** 6  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Create end-to-end smoke tests for critical happy paths.

**Files/Directories Impacted:**
```
tests/cron/smoke/
├── __init__.py
└── test_smoke.py
```

**Smoke Test Scenarios:**
- [ ] Fresh ingestion with 100 records succeeds
- [ ] Retry of failed batch succeeds
- [ ] Dry run completes without errors
- [ ] API-Gateway queries work after ingestion
- [ ] Schema version check passes
- [ ] OAuth authentication succeeds

**Acceptance Criteria:**
- [ ] All smoke tests pass
- [ ] Tests run in < 60 seconds
- [ ] Tests can run in any environment
- [ ] Tests validate critical paths only
- [ ] Tests suitable for CI smoke test stage

**Validation Evidence:**
```bash
# Run smoke tests
pytest tests/cron/smoke/ -v --tb=short

# Measure execution time
pytest tests/cron/smoke/ --durations=0

# Run in CI
pytest tests/cron/smoke/ -v --maxfail=1
```

**Definition of Done:**
- Smoke tests pass
- Fast execution
- CI-ready
- PR approved

---

### TASK-6.6: Coverage Enforcement in CI

**Phase:** 6  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Configure CI pipeline to enforce coverage thresholds and fail on violations.

**Files/Directories Impacted:**
```
.github/workflows/ci.yml (or equivalent CI config)
pyproject.toml (coverage config)
```

**Dependencies:** TASK-0.5, TASK-6.1

**CI Pipeline Stages:**
1. Lint & Type Check
2. Unit Tests with Coverage
3. Coverage Threshold Enforcement
4. Integration Tests
5. Smoke Tests
6. Regression Tests
7. Performance Benchmarks (optional)

**Coverage Enforcement:**
- Overall: ≥85%
- Critical modules: ≥90%
- Fail build if thresholds not met
- Generate coverage reports as artifacts
- Update coverage badge

**Acceptance Criteria:**
- [ ] CI pipeline configured
- [ ] Coverage thresholds enforced
- [ ] Build fails if coverage below threshold
- [ ] Coverage reports uploaded as artifacts
- [ ] Coverage badge updated automatically
- [ ] All stages pass

**Validation Evidence:**
```bash
# Run CI locally (if possible)
act push # or equivalent

# Verify coverage enforcement
pytest tests/cron/unit/ --cov=app/cron --cov-fail-under=85
echo $? # Should be 0 if passed, non-zero if failed

# Check CI configuration
cat .github/workflows/ci.yml | grep coverage
```

**Definition of Done:**
- CI configured
- Coverage enforced
- All stages pass
- PR approved

---

### TASK-6.7: Test Data Generators

**Phase:** 6  
**Priority:** P2 (Medium)  
**Estimated Effort:** 1 day

**Description:**  
Create test data generators for various scenarios.

**Files/Directories Impacted:**
```
tests/cron/fixtures/
├── __init__.py
├── data_generator.py
└── sample_payloads.json
```

**Generator Functions:**
- `generate_team_member()` - random team member matching actual payload structure
- `generate_batch()` - batch with metadata and team_members array
- `generate_full_payload()` - complete API response matching specs-data/team-member-skill-availability-records.json
- `generate_minimal_payload()` - minimal required fields per actual structure
- `generate_invalid_payload()` - for error testing

**Sample Structure Reference:**
```json
{
  "metadata": {
    "batch_id": "sync_2026_01_19_049",
    "timestamp": "2026-01-19T02:00:00Z",
    "total_records": 49,
    "source_system": "EAGLE_v1",
    "schema_version": "1.1"
  },
  "team_members": [{
    "team_member_id": "EMP_1001",
    "team_member_status": "active",
    "profile_type": "developer",
    "experience_in_months": 30,
    "designation": "Software Engineer",
    "base_location": "Bangalore",
    "work-mode": "wfh",
    "profile": "https://...",
    "skills": [{
      "skill_id": "SKILL_001",
      "name": "Python",
      "category": "Primary",
      "rating": 4,
      "experience_in_months": 18,
      "certifications": [],
      "is_deleted": false
    }],
    "allocations": [{
      "project_id": "PRJ-1201",
      "allocation_percentage": 100,
      "start_date": "2025-10-01",
      "end_date": null,
      "billable": true,
      "is_deleted": false
    }]
  }]
}
```

**Acceptance Criteria:**
- [ ] Generators create valid data
- [ ] Generators support parameterization
- [ ] Sample payloads included
- [ ] Documentation for usage

**Validation Evidence:**
```bash
# Test generators
python -c "
from tests.cron.fixtures.data_generator import generate_batch
batch = generate_batch(num_members=10)
print(f'Generated batch with {len(batch[\"team_members\"])} members')
"
```

**Definition of Done:**
- Generators implemented
- Documentation complete
- PR approved

---

### TASK-6.8: Test Documentation

**Phase:** 6  
**Priority:** P2 (Medium)  
**Estimated Effort:** 1 day

**Description:**  
Create comprehensive test documentation.

**Files/Directories Impacted:**
```
docs/testing/
├── unit-testing-guide.md
├── integration-testing-guide.md
├── regression-testing-guide.md
└── coverage-requirements.md
```

**Documentation Content:**
- Unit testing guidelines
- Integration testing guidelines
- Regression testing process
- Coverage requirements and enforcement
- How to run tests locally
- How to run tests in CI
- How to add new tests
- Test data management
- Mocking strategies

**Acceptance Criteria:**
- [ ] All testing guides complete
- [ ] Coverage requirements documented
- [ ] Examples included
- [ ] Reviewed by team

**Definition of Done:**
- Documentation complete
- Review approved
- PR merged

---

### TASK-6.9: Mutation Testing (Optional Advanced)

**Phase:** 6  
**Priority:** P3 (Low)  
**Estimated Effort:** 2 days

**Description:**  
Implement mutation testing to validate test quality.

**Files/Directories Impacted:**
```
.mutmut-config
tests/cron/mutation/
```

**Implementation:**
- Use `mutmut` or similar tool
- Run mutation tests on critical modules
- Target mutation score ≥ 70%

**Acceptance Criteria:**
- [ ] Mutation testing configured
- [ ] Critical modules tested
- [ ] Mutation score ≥ 70%
- [ ] Report generated

**Validation Evidence:**
```bash
# Run mutation tests
mutmut run --paths-to-mutate=app/cron/processing

# View results
mutmut show
mutmut html
```

**Definition of Done:**
- Mutation testing configured (if implemented)
- Results documented
- Optional gate

---

### TASK-6.10: API-Gateway Regression Report

**Phase:** 6  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 0.5 days

**Description:**  
Generate comprehensive API-Gateway regression report for Phase 6.

**Dependencies:** TASK-6.3

**Report Contents:**
- All endpoints tested
- Response shape comparison
- Status code comparison
- Performance comparison
- Data integrity validation
- Before/after ingestion comparison

**Acceptance Criteria:**
- [ ] Report generated
- [ ] No breaking changes found
- [ ] Performance within threshold
- [ ] Data integrity maintained

**Validation Evidence:**
```bash
# Generate regression report
pytest tests/cron/api_gateway/regression/ --html=regression-report.html

# View report
open regression-report.html
```

**Definition of Done:**
- Report generated
- No breaking changes
- Gate passed

---

### TASK-6.11: Security Testing

**Phase:** 6  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Run security scans and vulnerability tests.

**Files/Directories Impacted:**
```
tests/cron/security/
├── test_secrets_exposure.py
└── test_sql_injection.py
```

**Security Checks:**
- [ ] No hardcoded credentials in code
- [ ] No secrets in logs
- [ ] SQL injection prevention (parameterized queries)
- [ ] Dependency vulnerability scan
- [ ] SAST (Static Application Security Testing)

**Acceptance Criteria:**
- [ ] No hardcoded credentials found
- [ ] No secrets in logs
- [ ] No SQL injection vulnerabilities
- [ ] No high/critical vulnerabilities in dependencies
- [ ] SAST scan passes

**Validation Evidence:**
```bash
# Scan for secrets
git secrets --scan

# Dependency vulnerability scan
safety check

# SAST scan
bandit -r app/cron

# SQL injection tests
pytest tests/cron/security/test_sql_injection.py -v
```

**Definition of Done:**
- All security checks pass
- No critical vulnerabilities
- PR approved

---

### TASK-6.12: Load Testing (Optional)

**Phase:** 6  
**Priority:** P3 (Low)  
**Estimated Effort:** 2 days

**Description:**  
Perform load testing to validate system under high load.

**Files/Directories Impacted:**
```
tests/cron/load/
├── test_concurrent_batches.py
└── test_large_payloads.py
```

**Load Test Scenarios:**
- [ ] 50,000 records in single payload
- [ ] 10 concurrent batches
- [ ] Sustained load for 1 hour
- [ ] Database connection pool saturation

**Acceptance Criteria:**
- [ ] System handles large payloads
- [ ] No connection pool exhaustion
- [ ] No memory leaks
- [ ] Performance degradation < 20%

**Validation Evidence:**
```bash
# Run load tests
pytest tests/cron/load/ -v --tb=short

# Monitor during load test
watch -n 1 'psql -h localhost -p 5433 -U postgres -c "SELECT count(*) FROM pg_stat_activity;"'
```

**Definition of Done:**
- Load tests pass (if implemented)
- System stable under load
- Optional gate

---

### TASK-6.13: Test Failure Analysis

**Phase:** 6  
**Priority:** P2 (Medium)  
**Estimated Effort:** 1 day

**Description:**  
Analyze and document common test failure patterns and debugging strategies.

**Files/Directories Impacted:**
```
docs/testing/test-failure-analysis.md
```

**Content:**
- Common test failure patterns
- Debugging strategies
- Log analysis techniques
- How to reproduce failures
- Flaky test identification

**Acceptance Criteria:**
- [ ] Common failures documented
- [ ] Debugging guide complete
- [ ] Examples included

**Definition of Done:**
- Documentation complete
- PR merged

---

### TASK-6.14: CI/CD Pipeline Validation

**Phase:** 6  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Validate entire CI/CD pipeline from commit to deployment.

**Pipeline Stages to Validate:**
1. Lint & Type Check
2. Unit Tests with Coverage
3. Integration Tests
4. Regression Tests
5. Security Scans
6. Build Docker Image
7. Deploy to Staging
8. Smoke Tests on Staging
9. Performance Tests
10. Deploy to Production (manual gate)

**Acceptance Criteria:**
- [ ] All pipeline stages pass
- [ ] Coverage thresholds enforced
- [ ] Regression tests pass
- [ ] Security scans pass
- [ ] Staging deployment successful
- [ ] Smoke tests on staging pass
- [ ] Production deployment blocked until manual approval

**Validation Evidence:**
```bash
# Trigger full pipeline
git push origin main

# Monitor pipeline
# Check CI/CD dashboard

# Verify staging deployment
kubectl get pods -n ib-job-skill-mapping-staging

# Run smoke tests on staging
pytest tests/cron/smoke/ --base-url=https://staging.example.com -v
```

**Definition of Done:**
- Full pipeline validated
- All stages pass
- Gate passed

---

### TASK-6.15: Phase 6 Definition of Done Verification

**Phase:** 6  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Validate all Phase 6 acceptance criteria met before proceeding to Phase 7.

**Validation Checklist:**
- [ ] Overall unit test coverage ≥85%
- [ ] Critical path coverage ≥90%
- [ ] All integration tests pass
- [ ] API-Gateway regression tests pass (zero breaking changes)
- [ ] Performance benchmarks meet NFRs
- [ ] Smoke tests pass
- [ ] Coverage enforced in CI
- [ ] Security scans pass
- [ ] Test documentation complete
- [ ] CI/CD pipeline validated
- [ ] All PRs merged

**Comprehensive Test Run:**
```bash
# 1. Run all unit tests with coverage
pytest tests/cron/unit/ -v --cov=app/cron --cov-report=html --cov-report=term --cov-fail-under=85

# 2. Run all integration tests
pytest tests/cron/integration/ -v --tb=short

# 3. Run API-Gateway regression tests
pytest tests/cron/api_gateway/regression/ -v --compare-baseline

# 4. Run smoke tests
pytest tests/cron/smoke/ -v

# 5. Run performance benchmarks
pytest tests/cron/performance/ -v --benchmark-only

# 6. Run security scans
safety check
bandit -r app/cron
```

**Coverage Report:**
```bash
# Generate final coverage report
pytest tests/cron/unit/ --cov=app/cron --cov-report=html

# Verify critical path coverage
pytest tests/cron/unit/processing/ tests/cron/unit/db/ \
  --cov=app/cron/processing --cov=app/cron/db --cov-fail-under=90
```

**Acceptance Criteria:**
- [ ] All tests pass
- [ ] Coverage thresholds met
- [ ] Zero API-Gateway regressions
- [ ] Performance meets NFRs
- [ ] Security scans clean
- [ ] CI/CD pipeline green

**Definition of Done:**
- All checklist items verified
- All tests passing
- All thresholds met
- Phase 6 complete gate passed
- Ready for Phase 7

---

## Phase 7: Operational Readiness

**Objective:** Finalize operational procedures, monitoring, and production readiness.

---

### TASK-7.1: Implement Prometheus Metrics

**Phase:** 7  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Add Prometheus metrics collection for monitoring.

**Files/Directories Impacted:**
```
app/cron/utils/metrics.py
tests/cron/unit/utils/test_metrics.py
```

**Dependencies:** Phase 6 complete

**Metrics to Implement:**
- Counters: `ingestion_runs_total`, `batches_processed_total`, `records_processed_total`, `errors_total`
- Histograms: `ingestion_duration_seconds`, `batch_duration_seconds`
- Gauges: `ingestion_last_success_timestamp`, `failed_batches`

**Acceptance Criteria:**
- [ ] Metrics exposed on :8000/metrics
- [ ] All key metrics implemented
- [ ] Metrics incremented correctly
- [ ] Unit tests verify metrics
- [ ] Prometheus scrapes successfully

**Validation Evidence:**
```bash
# Start metrics server
python -m app.cron.main --dry-run &

# Scrape metrics
curl http://localhost:8000/metrics

# Run unit tests
pytest tests/cron/unit/utils/test_metrics.py -v
```

**Definition of Done:**
- Metrics implemented
- All tests pass
- Prometheus integration verified
- PR approved

---

### TASK-7.2: Configure Alert Rules

**Phase:** 7  
**Priority:** P1 (High)  
**Estimated Effort:** 1 day

**Description:**  
Create Prometheus alert rules and AlertManager configuration.

**Files/Directories Impacted:**
```
deployment/prometheus/alert-rules.yaml
deployment/alertmanager/config.yaml
```

**Dependencies:** TASK-7.1

**Alert Rules:**
- **IngestionJobFailed** (critical) - Complete failure
- **HighBatchFailureRate** (warning) - >20% batch failures
- **IngestionNotRun** (critical) - No success in 24 hours
- **OAuthAuthenticationFailed** (critical) - Auth failures
- **DatabaseSchemaVersionMismatch** (critical) - Schema mismatch

**AlertManager Integrations:**
- PagerDuty for critical alerts
- Slack for warnings

**Acceptance Criteria:**
- [ ] Alert rules valid YAML
- [ ] Alerts trigger correctly in test scenarios
- [ ] PagerDuty integration configured
- [ ] Slack integration configured
- [ ] Alert documentation complete

**Validation Evidence:**
```bash
# Validate alert rules
promtool check rules deployment/prometheus/alert-rules.yaml

# Test alert triggering
# (simulate failure condition)

# Verify alert received
# Check PagerDuty and Slack
```

**Definition of Done:**
- Alert rules configured
- Integrations working
- Documentation complete
- PR approved

---

### TASK-7.3: Create Operational Runbook

**Phase:** 7  
**Priority:** P1 (High)  
**Estimated Effort:** 2 days

**Description:**  
Create comprehensive operational runbook for troubleshooting.

**Files/Directories Impacted:**
```
docs/runbooks/nightly-ingestion.md
```

**Dependencies:** All previous phases

**Runbook Sections:**
1. Overview
2. Common Issues
3. Investigation Steps
4. Resolution Procedures
5. Escalation Paths
6. Maintenance Procedures

**Common Issues to Cover:**
- Authentication failures (OAuth)
- Batch failures
- Schema version mismatch
- Database connection issues
- API rate limiting
- Retry exhaustion

**Acceptance Criteria:**
- [ ] Runbook covers all common failure scenarios
- [ ] Step-by-step resolution procedures
- [ ] Escalation paths defined
- [ ] Log analysis examples included
- [ ] Reviewed by operations team

**Definition of Done:**
- Runbook complete
- Operations team review approved
- PR merged

---

### TASK-7.4: Production Readiness Checklist

**Phase:** 7  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Complete production readiness checklist and obtain approvals.

**Files/Directories Impacted:**
```
docs/production-readiness-checklist.md
```

**Dependencies:** All previous phases

**Checklist Categories:**

**Security:**
- [ ] No hardcoded credentials
- [ ] Secrets in secure vault
- [ ] TLS enabled
- [ ] Least privilege DB user
- [ ] Security scan passed

**Reliability:**
- [ ] All unit tests passing (≥85% coverage)
- [ ] All integration tests passing
- [ ] Performance benchmarks met
- [ ] Alembic migrations tested
- [ ] Idempotency validated
- [ ] Retry logic tested

**Monitoring:**
- [ ] Prometheus metrics exposed
- [ ] Alert rules configured
- [ ] PagerDuty integration tested
- [ ] Dashboards created

**Operations:**
- [ ] Runbook completed
- [ ] Deployment documentation complete
- [ ] Rollback procedure documented
- [ ] DR plan documented
- [ ] On-call rotation defined

**Testing:**
- [ ] Unit test coverage ≥85%
- [ ] Critical path coverage ≥90%
- [ ] API-Gateway regression tests pass
- [ ] Zero breaking changes
- [ ] Performance tests pass

**Compliance:**
- [ ] Audit logging implemented
- [ ] Data retention policy defined
- [ ] Access controls enforced

**Acceptance Criteria:**
- [ ] All checklist items completed
- [ ] Approvals obtained:
  - [ ] Tech Lead
  - [ ] Security Team
  - [ ] Operations Team
  - [ ] Product Owner

**Definition of Done:**
- All checklist items verified
- All approvals obtained
- System production-ready

---

### TASK-7.5: Rollback Procedure Validation

**Phase:** 7  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Document and validate rollback procedures.

**Files/Directories Impacted:**
```
docs/runbooks/rollback-procedure.md
tests/cron/integration/test_rollback.py
```

**Dependencies:** TASK-7.4

**Rollback Scenarios:**
1. Application rollback (previous version)
2. Database migration rollback (downgrade)
3. Configuration rollback
4. Emergency disable (stop cron job)

**Rollback Steps:**
1. Stop cron job / K8s CronJob
2. Rollback application deployment
3. Rollback Alembic migration (if needed)
4. Verify system state
5. Re-enable cron job
6. Monitor closely

**Acceptance Criteria:**
- [ ] Rollback procedure documented
- [ ] Rollback tested on staging
- [ ] Migration downgrade tested
- [ ] Emergency disable tested
- [ ] Recovery time < 30 minutes

**Validation Evidence:**
```bash
# Test application rollback
kubectl rollout undo deployment/team-data-ingestion -n ib-job-skill-mapping-staging

# Test migration rollback
alembic downgrade -1

# Test cron disable
kubectl patch cronjob/team-data-ingestion -p '{"spec": {"suspend": true}}'

# Test recovery
alembic upgrade head
kubectl patch cronjob/team-data-ingestion -p '{"spec": {"suspend": false}}'
```

**Definition of Done:**
- Rollback procedure documented
- Rollback tested successfully
- Recovery time validated
- PR approved

---

### TASK-7.6: Phase 7 Definition of Done Verification

**Phase:** 7  
**Priority:** P0 (Blocking)  
**Estimated Effort:** 1 day

**Description:**  
Final validation before production deployment.

**Validation Checklist:**
- [ ] Prometheus metrics implemented
- [ ] Alert rules configured and tested
- [ ] Operational runbook complete
- [ ] Production readiness checklist complete
- [ ] All approvals obtained
- [ ] Rollback procedure validated
- [ ] All documentation complete
- [ ] All PRs merged

**Final Validation Commands:**
```bash
# 1. Run full test suite
pytest tests/cron/ -v --cov=app/cron --cov-report=html --cov-report=term

# 2. Verify coverage thresholds
pytest tests/cron/unit/ --cov=app/cron --cov-fail-under=85
pytest tests/cron/unit/processing/ tests/cron/unit/db/ --cov=app/cron/processing --cov=app/cron/db --cov-fail-under=90

# 3. Run API-Gateway regression tests
pytest tests/cron/api_gateway/regression/ -v --compare-baseline

# 4. Run smoke tests
pytest tests/cron/smoke/ -v

# 5. Verify security scans
safety check
bandit -r app/cron

# 6. Verify metrics
curl http://localhost:8000/metrics

# 7. Test rollback on staging
# (follow rollback procedure)

# 8. Verify all documentation exists
ls -l docs/runbooks/
ls -l docs/testing/
ls -l deployment/
```

**Final Approval Gates:**
- [ ] Tech Lead sign-off
- [ ] Security Team sign-off
- [ ] Operations Team sign-off
- [ ] Product Owner sign-off

**Acceptance Criteria:**
- [ ] All tests passing
- [ ] All coverage thresholds met
- [ ] Zero API-Gateway regressions
- [ ] All documentation complete
- [ ] All approvals obtained
- [ ] Production deployment approved

**Definition of Done:**
- All checklist items verified
- All approvals obtained
- Ready for production deployment
- Project complete

---

## 🎯 Appendix: Task Summary by Phase

### Phase 0: Repository & Scaffolding (6 tasks)
- TASK-0.1: Create Directory Structure
- TASK-0.2: Configure Dependencies and Requirements
- TASK-0.3: Implement Configuration Management
- TASK-0.4: Setup Logging Utilities
- TASK-0.5: Setup Coverage Enforcement
- TASK-0.6: Create API-Gateway Regression Test Baseline

### Phase 1: Database & Alembic Setup (8 tasks)
- TASK-1.1: Create Alembic Migration 002
- TASK-1.2: Implement Schema Version Checker
- TASK-1.3: Implement Database Engine Factory
- TASK-1.4: Define Database Metadata
- TASK-1.5: Create Migration Impact Analysis Tests
- TASK-1.6: Unit Tests for Database Module
- TASK-1.7: Integration Tests for Database Setup
- TASK-1.8: Phase 1 Definition of Done Verification

### Phase 2: OAuth & External API Integration (8 tasks)
- TASK-2.1: Implement OAuth Token Client
- TASK-2.2: Implement External API Client
- TASK-2.3: Create Mock API Server for Testing
- TASK-2.4: Unit Tests for OAuth Module
- TASK-2.5: Unit Tests for API Module
- TASK-2.6: Integration Tests for OAuth and API
- TASK-2.7: API-Gateway Regression After Phase 2
- TASK-2.8: Phase 2 Definition of Done Verification

### Phase 3: Batch Ingestion & Persistence (10 tasks)
- TASK-3.1: Implement Database Repositories
- TASK-3.2: Implement Batch Processor
- TASK-3.3: Implement Error Classifier
- TASK-3.4: Integration Tests for Batch Processing
- TASK-3.5: Unit Tests for Processing Module
- TASK-3.6: Validate UPSERT Idempotency
- TASK-3.7: Data Validation and Transformation Tests
- TASK-3.8: API-Gateway Regression After Phase 3
- TASK-3.9: Phase 3 Coverage Report
- TASK-3.10: Phase 3 Definition of Done Verification

### Phase 4: Batch Retry & Failure Isolation (7 tasks)
- TASK-4.1: Implement Retry Manager
- TASK-4.2: Implement CLI Entry Point with Retry Flag
- TASK-4.3: Integration Tests for Retry Flow
- TASK-4.4: Unit Tests for Retry Module
- TASK-4.5: Simulate Failure and Retry Scenarios
- TASK-4.6: API-Gateway Regression After Phase 4
- TASK-4.7: Phase 4 Definition of Done Verification

### Phase 5: Scheduling & Runtime Execution (6 tasks)
- TASK-5.1: Create Shell Wrapper Script
- TASK-5.2: Create Cron Configuration
- TASK-5.3: Create Kubernetes CronJob Manifest
- TASK-5.4: Configure Log Rotation
- TASK-5.5: Unit Tests for Main Entry Point
- TASK-5.6: Phase 5 Definition of Done Verification

### Phase 6: Testing, Coverage & Validation (15 tasks)
- TASK-6.1: Overall Unit Test Coverage Report
- TASK-6.2: Integration Test Suite Consolidation
- TASK-6.3: API-Gateway Regression Test Suite
- TASK-6.4: Performance Benchmark Tests
- TASK-6.5: End-to-End Smoke Tests
- TASK-6.6: Coverage Enforcement in CI
- TASK-6.7: Test Data Generators
- TASK-6.8: Test Documentation
- TASK-6.9: Mutation Testing (Optional)
- TASK-6.10: API-Gateway Regression Report
- TASK-6.11: Security Testing
- TASK-6.12: Load Testing (Optional)
- TASK-6.13: Test Failure Analysis
- TASK-6.14: CI/CD Pipeline Validation
- TASK-6.15: Phase 6 Definition of Done Verification

### Phase 7: Operational Readiness (6 tasks)
- TASK-7.1: Implement Prometheus Metrics
- TASK-7.2: Configure Alert Rules
- TASK-7.3: Create Operational Runbook
- TASK-7.4: Production Readiness Checklist
- TASK-7.5: Rollback Procedure Validation
- TASK-7.6: Phase 7 Definition of Done Verification

---

## 📊 Coverage Requirements Summary

| Module | Coverage Target | Priority |
|--------|----------------|----------|
| **app/cron/processing/** | ≥90% | P0 Critical |
| **app/cron/db/repositories.py** | ≥90% | P0 Critical |
| **app/cron/oauth/token_client.py** | ≥90% | P0 High |
| **app/cron/api/external_client.py** | ≥90% | P0 High |
| **app/cron/processing/error_classifier.py** | ≥95% | P0 High |
| **app/cron/main.py** | ≥85% | P0 High |
| **app/cron/config.py** | ≥85% | P1 Medium |
| **app/cron/db/engine.py** | ≥85% | P1 Medium |
| **Overall** | ≥85% | P0 Critical |

---

## ✅ Quality Gates

| Phase | Gate Name | Criteria | Blocking? |
|-------|-----------|----------|-----------|
| Phase 0 | Foundation Gate | All directories created, dependencies installed, coverage setup | YES |
| Phase 1 | Database Gate | Migration applied, version checker working, coverage ≥90% | YES |
| Phase 2 | Integration Gate | OAuth + API working, unit tests pass, coverage ≥90%, no API regression | YES |
| Phase 3 | Persistence Gate | UPSERT working, idempotency validated, coverage ≥90%, no API regression | YES |
| Phase 4 | Retry Gate | Retry manager working, batch isolation validated, coverage ≥90%, no API regression | YES |
| Phase 5 | Deployment Gate | CLI working, scripts ready, coverage ≥85%, manual execution tested | YES |
| Phase 6 | Quality Gate | All tests pass, coverage ≥85% overall / ≥90% critical, zero API regressions, security scans clean | YES |
| Phase 7 | Production Gate | All approvals obtained, runbook complete, rollback validated | YES |

---

## 🚀 Success Criteria

**Technical Metrics:**
- ✅ Unit test coverage ≥85% overall
- ✅ Critical path coverage ≥90%
- ✅ All integration tests passing
- ✅ Zero API-Gateway regressions
- ✅ Performance benchmarks met (<30 min for 10k records)
- ✅ Security scans clean

**Operational Metrics:**
- ✅ Runbook complete and approved
- ✅ Monitoring and alerting configured
- ✅ Rollback procedure validated
- ✅ Production readiness checklist complete
- ✅ All approvals obtained

**Delivery Metrics:**
- ✅ All 66 tasks completed
- ✅ All PRs merged
- ✅ Documentation complete
- ✅ CI/CD pipeline green

---

## 📋 Conversion to Tickets

This task list is designed for direct conversion to:
- **GitHub Issues**: Each task → one issue with labels (phase, priority, type)
- **Jira Tickets**: Each task → one ticket with story points and acceptance criteria
- **Azure DevOps**: Each task → one work item with test plan

**Suggested Labels:**
- Phase: `phase-0` through `phase-7`
- Priority: `P0-blocking`, `P1-high`, `P2-medium`, `P3-low`
- Type: `implementation`, `testing`, `documentation`, `infrastructure`
- Coverage: `coverage-critical`, `coverage-high`
- Regression: `regression-test`, `api-gateway-regression`

---

**END OF TASK BREAKDOWN**
