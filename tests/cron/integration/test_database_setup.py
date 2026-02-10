"""Integration tests for database setup."""

import pytest
from sqlalchemy import inspect, text
from app.cron.db.engine import create_ingestion_engine, test_connection
from app.cron.db.migrations_check import (
    get_migration_info,
    validate_schema_version,
    EXPECTED_REVISION,
    EXPECTED_REVISION_SHORT,
)


@pytest.fixture(scope="module")
def integration_engine():
    """Create real database engine for integration tests."""
    engine = create_ingestion_engine(validate_schema=False)
    yield engine
    engine.dispose()


class TestDatabaseIntegration:
    """Integration tests for database setup and connectivity."""

    def test_engine_creation(self, integration_engine):
        """Test that engine can be created successfully."""
        assert integration_engine is not None
        assert integration_engine.pool is not None

    def test_connection_pooling(self, integration_engine):
        """Test that connection pooling is configured correctly."""
        # Pool should have correct settings
        pool = integration_engine.pool
        assert pool.size() == 5  # default pool_size
        assert hasattr(pool, "_max_overflow")

    def test_database_connectivity(self, integration_engine):
        """Test actual database connection."""
        result = test_connection(integration_engine)
        assert result is True, "Failed to connect to database"

    def test_schema_version_check(self, integration_engine):
        """Test migration version checking."""
        full_revision, short_version = get_migration_info(integration_engine)

        assert full_revision == EXPECTED_REVISION
        assert short_version == EXPECTED_REVISION_SHORT

    def test_schema_validation(self, integration_engine):
        """Test schema validation passes."""
        result = validate_schema_version(integration_engine, strict=True)
        assert result is True

    def test_ingestion_tables_accessible(self, integration_engine):
        """Test that ingestion tables can be queried."""
        with integration_engine.connect() as conn:
            # Should execute without error
            result = conn.execute(text("SELECT COUNT(*) FROM ingestion_batch_state"))
            count = result.scalar()
            assert count >= 0

            result = conn.execute(text("SELECT COUNT(*) FROM ingestion_audit_log"))
            count = result.scalar()
            assert count >= 0

    def test_existing_tables_accessible(self, integration_engine):
        """Test that existing tables are still accessible."""
        with integration_engine.connect() as conn:
            # Original tables should work
            conn.execute(text("SELECT COUNT(*) FROM team_member"))
            conn.execute(text("SELECT COUNT(*) FROM skill_master"))
            conn.execute(text("SELECT COUNT(*) FROM category_master"))

    def test_pool_pre_ping_works(self, integration_engine):
        """Test that pool_pre_ping detects stale connections."""
        # Get a connection
        conn1 = integration_engine.connect()
        conn1.close()

        # Get another connection (should work due to pre_ping)
        conn2 = integration_engine.connect()
        result = conn2.execute(text("SELECT 1"))
        assert result.scalar() == 1
        conn2.close()

    def test_connection_recycling(self):
        """Test that connection recycling is configured."""
        # Create engine with short recycle time for testing
        engine = create_ingestion_engine(
            validate_schema=False,
            pool_recycle=1,  # 1 second for testing
        )

        try:
            # Connection should be created and work
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            engine.dispose()

    def test_metadata_reflection(self, integration_engine):
        """Test that metadata can be reflected from database."""
        inspector = inspect(integration_engine)

        # Ingestion tables should be present
        tables = inspector.get_table_names()
        assert "ingestion_batch_state" in tables
        assert "ingestion_audit_log" in tables

        # Check ingestion_batch_state columns
        columns = {col["name"] for col in inspector.get_columns("ingestion_batch_state")}
        assert "batch_id" in columns
        assert "correlation_id" in columns
        assert "status" in columns

    def test_foreign_key_constraints(self, integration_engine):
        """Test that foreign key constraints work."""
        inspector = inspect(integration_engine)

        # Check FK from ingestion_audit_log to ingestion_batch_state
        fks = inspector.get_foreign_keys("ingestion_audit_log")
        fk = next((fk for fk in fks if fk["referred_table"] == "ingestion_batch_state"), None)

        assert fk is not None
        assert fk["constrained_columns"] == ["batch_id"]
        assert fk["referred_columns"] == ["batch_id"]

    def test_indexes_exist(self, integration_engine):
        """Test that indexes are created."""
        inspector = inspect(integration_engine)

        # Check ingestion_batch_state indexes
        indexes = {idx["name"] for idx in inspector.get_indexes("ingestion_batch_state")}
        assert "ix_ingestion_batch_state_correlation_id" in indexes
        assert "ix_ingestion_batch_state_status" in indexes

        # Check ingestion_audit_log indexes
        indexes = {idx["name"] for idx in inspector.get_indexes("ingestion_audit_log")}
        assert "ix_ingestion_audit_log_batch_id" in indexes
        assert "ix_ingestion_audit_log_correlation_id" in indexes
        assert "ix_ingestion_audit_log_timestamp" in indexes

    def test_concurrent_connections(self, integration_engine):
        """Test multiple concurrent connections."""
        connections = []

        try:
            # Open multiple connections
            for _ in range(3):
                conn = integration_engine.connect()
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
                connections.append(conn)

        finally:
            # Clean up
            for conn in connections:
                conn.close()
