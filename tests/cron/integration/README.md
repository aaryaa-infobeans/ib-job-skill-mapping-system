# Integration Tests - Docker Compose Test Environment

## Overview
This document describes the Docker Compose test environment for running integration tests that require PostgreSQL.

## Quick Start

### 1. Start Test Database
```bash
docker-compose -f docker-compose.test.yml up -d
```

Wait for database to be ready (check health):
```bash
docker-compose -f docker-compose.test.yml ps
```

### 2. Run Integration Tests
```bash
# Run all ingestion integration tests
pytest tests/cron/integration/ -v

# Run specific test file
pytest tests/cron/integration/test_database_setup.py -v

# Run with coverage
pytest tests/cron/integration/ -v --cov=app.cron --cov-report=html
```

### 3. Stop and Clean Up
```bash
# Stop containers (preserves data)
docker-compose -f docker-compose.test.yml stop

# Stop and remove containers + volumes (clean slate)
docker-compose -f docker-compose.test.yml down -v
```

## Test Database Configuration

**Connection Details:**
- Host: `localhost`
- Port: `5434` (mapped from container's 5432)
- Database: `ib_job_skill_mapping_test`
- User: `postgres`
- Password: `postgres`

**Connection String:**
```
postgresql://postgres:postgres@localhost:5434/ib_job_skill_mapping_test
```

**Environment Variable:**
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5434/ib_job_skill_mapping_test"
```

## Test Categories Requiring Database

### 1. Database Setup Tests (`test_database_setup.py`)
- **Tests**: 13 tests
- **Purpose**: Validate database connectivity, schema, tables, foreign keys, indexes
- **Requires**: PostgreSQL running on port 5433

### 2. Migration Impact Tests (`test_migration_impact.py`)
- **Tests**: 8 tests
- **Purpose**: Verify database migrations don't break existing functionality
- **Requires**: PostgreSQL with migrations applied

### 3. Batch Processing Tests (`test_batch_processing.py`)
- **Tests**: 9 tests
- **Purpose**: End-to-end batch processing with database operations
- **Requires**: PostgreSQL for data persistence

### 4. UPSERT Idempotency Tests (`test_upsert_idempotency.py`)
- **Tests**: 14 tests
- **Purpose**: Validate idempotent UPSERT operations
- **Requires**: PostgreSQL with FK constraints

### 5. Shell Wrapper Tests (partial)
- **Tests**: 3 tests (database-dependent)
- **Purpose**: Test shell script execution with database
- **Requires**: PostgreSQL for connection validation

**Total**: 46 tests unblocked by Docker Compose environment

## Troubleshooting

### Port Already in Use
If port 5433 is already in use, edit `docker-compose.test.yml`:
```yaml
ports:
  - "5434:5432"  # Use different port
```

Then update test connection strings accordingly.

### Database Not Ready
If tests fail with connection errors, ensure database is healthy:
```bash
docker-compose -f docker-compose.test.yml ps
```

Look for `healthy` status. If not healthy, check logs:
```bash
docker-compose -f docker-compose.test.yml logs postgres-test
```

### Permission Errors
If you get permission errors on Windows, ensure Docker Desktop has file sharing enabled for your workspace directory.

### Clean Database State
To ensure clean state between test runs:
```bash
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d
# Wait for healthy status
pytest tests/cron/integration/
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: ib_job_skill_mapping_test
        ports:
          - 5433:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5434/ib_job_skill_mapping_test
        run: |
          pytest tests/cron/integration/ -v --tb=short
```

## Test Execution Performance

**Expected Performance:**
- Total execution time: < 30 seconds
- Database startup: ~5 seconds
- Test execution: ~25 seconds

**Actual Performance (from TASK-6.2):**
- Execution time: 27.88 seconds ✅
- Target: < 300 seconds
- Performance: 9.3% of target (excellent)

## Database Schema Management

### Applying Migrations
```bash
# Ensure test database is running
docker-compose -f docker-compose.test.yml up -d

# Apply migrations
alembic upgrade head

# Verify schema
psql postgresql://postgres:postgres@localhost:5433/ib_job_skill_mapping_test -c "\dt"
```

### Reset Schema
```bash
# Drop and recreate database
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d
alembic upgrade head
```

## Test Isolation

Each test should:
1. Use database transactions
2. Roll back after test completion
3. Not depend on other tests' data
4. Clean up test data in teardown

Example fixture:
```python
@pytest.fixture
def test_db_session():
    """Create test database session with rollback."""
    session = SessionLocal()
    
    yield session
    
    session.rollback()
    session.close()
```

## Maintenance

### Update PostgreSQL Version
Edit `docker-compose.test.yml`:
```yaml
services:
  postgres-test:
    image: postgres:16-alpine  # Update version
```

### Add Test Database Seed Data
Create `tests/fixtures/seed_data.sql` and run:
```bash
docker exec -i ib-job-skill-mapping-postgres-test psql -U postgres -d ib_job_skill_mapping_test < tests/fixtures/seed_data.sql
```

## Related Documentation
- [Phase 6 Integration Tests Report](../docs/phase-6-integration-tests-report.md)
- [Local Development Guide](../docs/runbooks/local_dev.md)
- [Phase 6 Testing Guide](../docs/phase-6-testing-guide.md)
