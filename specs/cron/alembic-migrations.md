# Alembic Migrations - Nightly Batch Ingestion Service

**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Owner:** Platform Engineering

---

## 1. Overview

This document defines the Alembic migration strategy for the nightly batch ingestion service. All schema changes MUST be expressed as Alembic revisions. Runtime code MUST NOT perform DDL operations.

### 1.1 Principles

- **Single Source of Truth**: Alembic migrations are the authoritative schema definition
- **Forward-Only**: No destructive downgrades in production
- **Explicit Dependencies**: Revision chains must be linear and traceable
- **Environment Isolation**: Separate configurations for local/test/prod
- **Version Enforcement**: Ingestion job fails fast if schema version mismatches

---

## 2. Alembic Project Structure

```
ib-job-skill-mapping-system/
├── alembic/
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_ingestion_state_tables.py
│   │   └── 003_add_audit_indexes.py
│   ├── env.py                      # Alembic runtime environment
│   ├── script.py.mako              # Migration template
│   └── README.md
├── alembic.ini                     # Main configuration
├── alembic-test.ini                # Test environment config
├── alembic-prod.ini                # Production config (templated)
└── src/
    └── migrations/
        ├── __init__.py
        └── version_checker.py      # Runtime version validation
```

---

## 3. Alembic Configuration

### 3.1 alembic.ini (Local Development)

```ini
[alembic]
script_location = alembic
prepend_sys_path = .

# Database URL (overridden by environment variable)
sqlalchemy.url = postgresql://user:password@localhost:5433/ib_job_skill_mapping

# Logging
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = INFO
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 3.2 env.py (Alembic Runtime)

```python
"""Alembic environment configuration."""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app.db.models.models import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def get_url():
    """Get database URL from environment or config."""
    return os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script generation)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (direct database connection)."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## 4. Migration Lifecycle

### 4.1 Creating a Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add ingestion state tables"

# Create empty migration for manual SQL
alembic revision -m "Add custom index for batch queries"
```

### 4.2 Migration Template Structure

```python
"""Add ingestion state tables

Revision ID: 002_add_ingestion_state
Revises: 001_initial_schema
Create Date: 2026-02-06 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '002_add_ingestion_state'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema to this revision."""
    # Forward migration logic
    op.create_table(
        'ingestion_batch_state',
        sa.Column('batch_id', sa.String(50), primary_key=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('total_records', sa.Integer(), nullable=False),
        sa.Column('processed_records', sa.Integer(), server_default='0'),
        sa.Column('failed_records', sa.Integer(), server_default='0'),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('max_retries', sa.Integer(), server_default='3'),
        sa.Column('first_attempted_at', sa.TIMESTAMP(), server_default=sa.text('NOW()')),
        sa.Column('last_retry_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('NOW()')),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'SUCCESS', 'FAILED')",
            name='ck_batch_state_status'
        )
    )
    
    op.create_index('idx_batch_state_status', 'ingestion_batch_state', ['status'])
    op.create_index('idx_batch_state_correlation', 'ingestion_batch_state', ['correlation_id'])
    
    # Trigger for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_batch_state_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER trg_batch_state_updated_at
        BEFORE UPDATE ON ingestion_batch_state
        FOR EACH ROW
        EXECUTE FUNCTION update_batch_state_timestamp();
    """)


def downgrade() -> None:
    """Downgrade schema from this revision."""
    # Reverse migration (NOT executed in production)
    op.execute("DROP TRIGGER IF EXISTS trg_batch_state_updated_at ON ingestion_batch_state")
    op.execute("DROP FUNCTION IF EXISTS update_batch_state_timestamp")
    op.drop_index('idx_batch_state_correlation', 'ingestion_batch_state')
    op.drop_index('idx_batch_state_status', 'ingestion_batch_state')
    op.drop_table('ingestion_batch_state')
```

### 4.3 Applying Migrations

```bash
# Show current version
alembic current

# Show migration history
alembic history --verbose

# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade 002_add_ingestion_state

# Downgrade (dev/test only - NEVER in production)
alembic downgrade -1

# Show pending migrations
alembic show head
```

---

## 5. Version Validation in Runtime Code

### 5.1 Version Checker Module

**File:** `src/migrations/version_checker.py`

```python
"""Alembic version validation for ingestion service."""

import sys
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.app.settings import settings


class SchemaVersionError(Exception):
    """Raised when schema version does not match expected version."""
    pass


def get_current_revision(database_url: str) -> Optional[str]:
    """
    Query the current Alembic revision from the database.
    
    Args:
        database_url: PostgreSQL connection string
        
    Returns:
        Current revision ID or None if alembic_version table doesn't exist
        
    Raises:
        SchemaVersionError: If version table exists but is empty
    """
    engine = create_engine(database_url, echo=False)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            
            if row is None:
                raise SchemaVersionError(
                    "alembic_version table exists but contains no revision. "
                    "Run 'alembic stamp head' to initialize."
                )
            
            return row[0]
    except Exception as e:
        if "relation \"alembic_version\" does not exist" in str(e):
            return None
        raise SchemaVersionError(f"Failed to query schema version: {e}")
    finally:
        engine.dispose()


def validate_schema_version(
    database_url: str,
    expected_revision: str,
    allow_newer: bool = False
) -> None:
    """
    Validate that database schema matches expected Alembic revision.
    
    Args:
        database_url: PostgreSQL connection string
        expected_revision: Expected Alembic revision ID (e.g., '002_add_ingestion_state')
        allow_newer: If True, allow database to be ahead of expected revision
        
    Raises:
        SchemaVersionError: If version validation fails
        
    Example:
        >>> validate_schema_version(
        ...     "postgresql://localhost/ib_job_skill_mapping",
        ...     "002_add_ingestion_state",
        ...     allow_newer=True
        ... )
    """
    current = get_current_revision(database_url)
    
    if current is None:
        raise SchemaVersionError(
            "Database schema is not under Alembic version control. "
            "Run 'alembic upgrade head' to initialize schema."
        )
    
    if current == expected_revision:
        print(f"✓ Schema version validated: {current}")
        return
    
    if allow_newer:
        # Check if current is ahead (simplified check - proper solution requires migration graph traversal)
        print(f"⚠ Warning: Database schema ({current}) is newer than expected ({expected_revision})")
        print("  Proceeding with allow_newer=True")
        return
    
    raise SchemaVersionError(
        f"Schema version mismatch!\n"
        f"  Expected: {expected_revision}\n"
        f"  Current:  {current}\n"
        f"  Action:   Run 'alembic upgrade {expected_revision}' to update schema"
    )


def get_expected_revision() -> str:
    """
    Get the expected Alembic revision for this codebase version.
    
    This should be updated whenever a new migration is deployed.
    
    Returns:
        Expected revision ID
    """
    # TODO: This could be read from a VERSION file or environment variable
    # For now, hardcoded to the latest required revision for ingestion service
    return "002_add_ingestion_state"


if __name__ == "__main__":
    """CLI for manual schema version checking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Alembic schema version")
    parser.add_argument("--database-url", default=settings.database_url, help="Database connection URL")
    parser.add_argument("--expected", default=get_expected_revision(), help="Expected revision ID")
    parser.add_argument("--allow-newer", action="store_true", help="Allow database to be ahead")
    
    args = parser.parse_args()
    
    try:
        validate_schema_version(args.database_url, args.expected, args.allow_newer)
        print("Schema validation passed!")
        sys.exit(0)
    except SchemaVersionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
```

### 5.2 Integration in Ingestion Service

**File:** `src/ingest_team_data.py`

```python
"""Main entry point for nightly team data ingestion."""

import sys
from src.migrations.version_checker import validate_schema_version, SchemaVersionError
from src.app.settings import settings

def main():
    """Main ingestion workflow."""
    try:
        # STEP 1: Validate schema version BEFORE any processing
        print("Validating database schema version...")
        validate_schema_version(
            database_url=settings.database_url,
            expected_revision="002_add_ingestion_state",
            allow_newer=False  # Strict validation in production
        )
        
        # STEP 2: Proceed with ingestion
        # ... rest of ingestion logic ...
        
    except SchemaVersionError as e:
        print(f"FATAL: Schema version mismatch - {e}", file=sys.stderr)
        sys.exit(2)  # Exit code 2 = schema error
    except Exception as e:
        print(f"FATAL: Unexpected error - {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 6. Migration Strategy by Environment

### 6.1 Local Development

```bash
# Initial setup
alembic upgrade head

# After model changes
alembic revision --autogenerate -m "Description of change"
alembic upgrade head

# Testing rollback
alembic downgrade -1
alembic upgrade head
```

### 6.2 Test Environment

```bash
# Use test-specific config
export DATABASE_URL=postgresql://test_user:password@test-db:5432/ib_test
alembic -c alembic-test.ini upgrade head

# Run tests
pytest tests/integration/test_ingestion.py
```

### 6.3 Production Deployment

```bash
# Pre-deployment validation
alembic check  # Verify no pending autogenerate changes

# Backup database
pg_dump -h prod-db -U admin ib_job_skill_mapping > backup_$(date +%Y%m%d_%H%M%S).sql

# Apply migrations (manual approval required)
alembic -c alembic-prod.ini upgrade head

# Verify version
alembic -c alembic-prod.ini current

# Deploy application code
kubectl apply -f k8s/ingestion-cronjob.yaml
```

---

## 7. Required Migrations for Ingestion Service

### 7.1 Migration 001: Initial Schema (Existing)

**Revision ID:** `001_initial_schema` (or `e8a217c84204_initial_schema`)  
**Status:** Already applied

- Core tables: `team_member`, `skill_master`, `category_master`, etc.
- Foreign key relationships
- Indexes for performance

### 7.2 Migration 002: Add Ingestion State Tables (NEW)

**Revision ID:** `002_add_ingestion_state`  
**Depends On:** `001_initial_schema`

**Tables to Create:**

1. **ingestion_batch_state**

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
   ```

2. **ingestion_audit_log**

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
   ```

**Indexes:**

```sql
CREATE INDEX idx_batch_state_status ON ingestion_batch_state(status);
CREATE INDEX idx_batch_state_correlation ON ingestion_batch_state(correlation_id);
CREATE INDEX idx_audit_batch_id ON ingestion_audit_log(batch_id);
CREATE INDEX idx_audit_created_at ON ingestion_audit_log(created_at DESC);
```

**Generate Command:**

```bash
alembic revision -m "Add ingestion state and audit tables"
# Edit the generated file in alembic/versions/
alembic upgrade head
```

### 7.3 Migration 003: Add Performance Indexes (FUTURE)

**Revision ID:** `003_add_performance_indexes`  
**Depends On:** `002_add_ingestion_state`

```sql
-- Composite indexes for common queries
CREATE INDEX idx_team_member_skill_composite 
ON team_member_skill(team_member_id, skill_id, rating DESC);

CREATE INDEX idx_team_member_allocation_dates 
ON team_member_allocation(team_member_id, end_date DESC);

-- Partial index for active team members
CREATE INDEX idx_team_member_active 
ON team_member(team_member_id) WHERE is_active = TRUE;
```

---

## 8. Migration Testing Strategy

### 8.1 Pre-Merge Checklist

- [ ] Migration applies cleanly on empty database
- [ ] Migration applies on database with existing data
- [ ] Downgrade works correctly (for non-production migrations)
- [ ] No data loss on upgrade
- [ ] Foreign key constraints preserved
- [ ] Indexes created with expected explain plans
- [ ] Migration runs in < 60 seconds on production-size data

### 8.2 Automated Testing

```python
# tests/integration/test_migrations.py

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

@pytest.fixture
def alembic_config():
    """Alembic configuration for tests."""
    config = Config("alembic-test.ini")
    return config

def test_upgrade_head(alembic_config, test_db_url):
    """Test upgrading to head revision."""
    engine = create_engine(test_db_url)
    
    # Run migrations
    command.upgrade(alembic_config, "head")
    
    # Verify tables exist
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    assert "ingestion_batch_state" in tables
    assert "ingestion_audit_log" in tables
    
def test_downgrade_upgrade_cycle(alembic_config):
    """Test downgrade and re-upgrade."""
    command.upgrade(alembic_config, "002")
    command.downgrade(alembic_config, "001")
    command.upgrade(alembic_config, "002")
    # Should complete without errors

def test_migration_idempotency(alembic_config):
    """Test running same migration twice."""
    command.upgrade(alembic_config, "head")
    # Re-running should be no-op
    command.upgrade(alembic_config, "head")
```

---

## 9. Troubleshooting

### 9.1 Common Issues

#### Issue: "Can't locate revision identified by 'xxx'"

**Cause:** Migration file missing or Alembic can't find it  
**Fix:**

```bash
# Regenerate migration if lost
alembic revision -m "Recreate missing migration"

# Or stamp database to skip it
alembic stamp xxx
```

#### Issue: "Multiple head revisions present"

**Cause:** Branched migration history (multiple developers created migrations simultaneously)  
**Fix:**

```bash
# Merge branches
alembic merge -m "Merge migration branches" head1 head2

# Apply merged migration
alembic upgrade head
```

#### Issue: "Table already exists"

**Cause:** Manual schema changes made outside Alembic  
**Fix:**

```bash
# Stamp database to current state without executing migrations
alembic stamp head

# Or create migration with IF NOT EXISTS checks
op.execute("""
    CREATE TABLE IF NOT EXISTS my_table (...);
""")
```

### 9.2 Recovery Procedures

#### Recovery: Database Schema Corrupted

```bash
# 1. Restore from backup
psql -h prod-db -U admin ib_job_skill_mapping < backup_20260205.sql

# 2. Verify Alembic version
alembic current

# 3. Re-apply missing migrations if needed
alembic upgrade head
```

#### Recovery: Ingestion Job Fails on Version Check

```bash
# 1. Check current database version
alembic -c alembic-prod.ini current

# 2. Check expected version in code
grep "expected_revision" src/migrations/version_checker.py

# 3. Apply missing migrations
alembic -c alembic-prod.ini upgrade <expected_revision>

# 4. Re-run ingestion job
./src/ingest_team_data.py
```

---

## 10. Best Practices

### 10.1 Migration Development

1. **One Logical Change Per Migration**: Don't mix table creation with index optimization
2. **Test on Production-Size Data**: Verify performance impact before deployment
3. **Use Explicit Naming**: `002_add_ingestion_state` > `002_abcd1234`
4. **Add Comments**: Explain WHY, not just WHAT
5. **Include Rollback Path**: Even if not executed in prod, document how to reverse

### 10.2 Deployment Protocol

1. **Review Migration SQL**: Inspect generated SQL before applying
2. **Backup Before Upgrade**: Always have a restoration path
3. **Apply in Maintenance Window**: For large tables, avoid peak hours
4. **Monitor During Execution**: Watch for locks and query times
5. **Validate After Upgrade**: Run smoke tests to verify functionality

### 10.3 Code Review Checklist

- [ ] Migration has clear, descriptive name
- [ ] `upgrade()` and `downgrade()` both implemented
- [ ] SQL tested on development database
- [ ] Indexes added for new foreign keys
- [ ] Check constraints documented
- [ ] No hardcoded values (use config/env)
- [ ] Migration runs in acceptable time (<5 min)

---

## 11. Appendix: Full Migration Example

**File:** `alembic/versions/002_add_ingestion_state_tables.py`

```python
"""Add ingestion state and audit tables

Revision ID: 002_add_ingestion_state
Revises: e8a217c84204
Create Date: 2026-02-06 10:00:00.000000

Purpose:
    Create tables required for nightly batch ingestion service:
    - ingestion_batch_state: Track batch processing status and retries
    - ingestion_audit_log: Audit trail for all ingestion operations

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '002_add_ingestion_state'
down_revision = 'e8a217c84204'  # Initial schema migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ingestion state and audit tables."""
    
    # Table: ingestion_batch_state
    op.create_table(
        'ingestion_batch_state',
        sa.Column('batch_id', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('total_records', sa.Integer(), nullable=False),
        sa.Column('processed_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('first_attempted_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_retry_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('batch_id', name='pk_ingestion_batch_state'),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'SUCCESS', 'FAILED')",
            name='ck_batch_state_status'
        )
    )
    
    # Indexes for ingestion_batch_state
    op.create_index('idx_batch_state_status', 'ingestion_batch_state', ['status'])
    op.create_index('idx_batch_state_correlation', 'ingestion_batch_state', ['correlation_id'])
    
    # Trigger to auto-update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_batch_state_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER trg_batch_state_updated_at
        BEFORE UPDATE ON ingestion_batch_state
        FOR EACH ROW
        EXECUTE FUNCTION update_batch_state_timestamp();
    """)
    
    # Table: ingestion_audit_log
    op.create_table(
        'ingestion_audit_log',
        sa.Column('audit_id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('batch_id', sa.String(50), nullable=True),
        sa.Column('operation', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('table_name', sa.String(100), nullable=True),
        sa.Column('records_affected', sa.Integer(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('audit_id', name='pk_ingestion_audit_log')
    )
    
    # Indexes for ingestion_audit_log
    op.create_index('idx_audit_batch_id', 'ingestion_audit_log', ['batch_id'])
    op.create_index('idx_audit_created_at', 'ingestion_audit_log', ['created_at'], postgresql_using='btree')
    
    # Add comment to tables for documentation
    op.execute("""
        COMMENT ON TABLE ingestion_batch_state IS 
        'Tracks state and retry information for each batch processed by nightly ingestion service';
        
        COMMENT ON TABLE ingestion_audit_log IS 
        'Audit trail of all ingestion operations with timing and error details';
    """)


def downgrade() -> None:
    """Drop ingestion state and audit tables."""
    
    # Drop audit log table and indexes
    op.drop_index('idx_audit_created_at', 'ingestion_audit_log')
    op.drop_index('idx_audit_batch_id', 'ingestion_audit_log')
    op.drop_table('ingestion_audit_log')
    
    # Drop batch state trigger, function, indexes, and table
    op.execute("DROP TRIGGER IF EXISTS trg_batch_state_updated_at ON ingestion_batch_state")
    op.execute("DROP FUNCTION IF EXISTS update_batch_state_timestamp")
    op.drop_index('idx_batch_state_correlation', 'ingestion_batch_state')
    op.drop_index('idx_batch_state_status', 'ingestion_batch_state')
    op.drop_table('ingestion_batch_state')
```

---

## 12. Definition of Done

- [ ] Alembic project structure created
- [ ] Migration 002 (ingestion state tables) created and tested
- [ ] Version checker module implemented and tested
- [ ] Integration with ingestion service CLI complete
- [ ] Environment-specific configs (dev/test/prod) defined
- [ ] Migration testing strategy documented
- [ ] Runbook for production deployment created
- [ ] Team training on Alembic workflow completed

---

**Document Status:** Ready for Implementation  
**Next Steps:** Create Migration 002 and integrate version checker into ingestion service
