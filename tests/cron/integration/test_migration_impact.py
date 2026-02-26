"""Migration impact analysis tests for Phase 1."""

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
import os


@pytest.fixture(scope="module")
def db_engine() -> Engine:
    """Create test database engine."""
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "password")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "job_skill_mapping")

    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(db_url)
    yield engine
    engine.dispose()


class TestMigrationImpactAnalysis:
    """Validate migration 002 has no negative impact on existing functionality."""

    def test_all_original_tables_exist(self, db_engine: Engine):
        """Verify all tables from migration 001 still exist."""
        inspector = inspect(db_engine)
        tables = set(inspector.get_table_names())

        # Original tables from e8a217c84204_initial_schema.py
        expected_tables = {
            "auth_clients",
            "auth_access_tokens",
            "requisition_status_master",
            "requisition_requests",
            "requisition_detail",
            "category_master",
            "skill_master",
            "team_member",
            "team_member_allocation",
            "team_member_skill",
            "team_member_team_member_skill_certification",
            "langgraph_checkpoints",
            "alembic_version",
        }

        missing_tables = expected_tables - tables
        assert not missing_tables, f"Missing tables after migration: {missing_tables}"

    def test_new_ingestion_tables_exist(self, db_engine: Engine):
        """Verify new ingestion tables were created."""
        inspector = inspect(db_engine)
        tables = set(inspector.get_table_names())

        new_tables = {"ingestion_batch_state", "ingestion_audit_log"}
        missing_tables = new_tables - tables
        assert not missing_tables, f"New tables not created: {missing_tables}"

    def test_ingestion_batch_state_schema(self, db_engine: Engine):
        """Verify ingestion_batch_state has correct schema."""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("ingestion_batch_state")}

        # Required columns
        expected_columns = {
            "batch_id",
            "correlation_id",
            "status",
            "total_records",
            "processed_records",
            "failed_records",
            "started_at",
            "completed_at",
            "error_message",
            "metadata",
        }

        actual_columns = set(columns.keys())
        assert expected_columns == actual_columns, f"Column mismatch: expected {expected_columns}, got {actual_columns}"

        # Verify primary key
        pk = inspector.get_pk_constraint("ingestion_batch_state")
        assert pk["constrained_columns"] == ["batch_id"], "Primary key should be batch_id"

        # Verify indexes
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("ingestion_batch_state")}
        assert "ix_ingestion_batch_state_correlation_id" in indexes
        assert "ix_ingestion_batch_state_status" in indexes

    def test_ingestion_audit_log_schema(self, db_engine: Engine):
        """Verify ingestion_audit_log has correct schema."""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("ingestion_audit_log")}

        # Required columns
        expected_columns = {
            "id",
            "batch_id",
            "correlation_id",
            "event_type",
            "event_details",
            "timestamp",
            "severity",
            "source",
        }

        actual_columns = set(columns.keys())
        assert expected_columns == actual_columns

        # Verify primary key
        pk = inspector.get_pk_constraint("ingestion_audit_log")
        assert pk["constrained_columns"] == ["id"]

        # Verify foreign key
        fks = inspector.get_foreign_keys("ingestion_audit_log")
        assert len(fks) == 1
        assert fks[0]["referred_table"] == "ingestion_batch_state"
        assert fks[0]["constrained_columns"] == ["batch_id"]

        # Verify indexes
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("ingestion_audit_log")}
        assert "ix_ingestion_audit_log_batch_id" in indexes
        assert "ix_ingestion_audit_log_correlation_id" in indexes
        assert "ix_ingestion_audit_log_timestamp" in indexes

    def test_no_schema_drift_in_existing_tables(self, db_engine: Engine):
        """Verify existing tables weren't modified."""
        inspector = inspect(db_engine)

        # Check critical table schemas unchanged
        # team_member table
        tm_columns = {col["name"] for col in inspector.get_columns("team_member")}
        expected_tm_columns = {
            "team_member_id",
            "designation",
            "profile_type",
            "is_active",
            "experience_in_months",
            "base_location",
            "work_type",
            "profile_url",
            "created_at",
        }
        assert tm_columns == expected_tm_columns, "team_member schema changed"

        # skill_master table
        sm_columns = {col["name"] for col in inspector.get_columns("skill_master")}
        expected_sm_columns = {"skill_id", "skill_name", "category_id", "created_at"}
        assert sm_columns == expected_sm_columns, "skill_master schema changed"

    def test_existing_table_queries_work(self, db_engine: Engine):
        """Verify existing tables can be queried without errors."""
        with db_engine.connect() as conn:
            # Should execute without error
            conn.execute(text("SELECT COUNT(*) FROM team_member"))
            conn.execute(text("SELECT COUNT(*) FROM skill_master"))
            conn.execute(text("SELECT COUNT(*) FROM category_master"))
            conn.execute(text("SELECT COUNT(*) FROM requisition_requests"))

    def test_migration_version_updated(self, db_engine: Engine):
        """Verify alembic version is updated to 002."""
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()

            assert version == "ba97cf8e4fdf", f"Expected version ba97cf8e4fdf, got {version}"
