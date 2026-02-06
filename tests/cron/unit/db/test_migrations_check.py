"""Unit tests for database migrations_check module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.engine import Engine
from app.cron.db.migrations_check import (
    get_migration_info,
    validate_schema_version,
    SchemaMismatchError,
    EXPECTED_REVISION,
    EXPECTED_REVISION_SHORT,
)


@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine."""
    engine = Mock(spec=Engine)
    return engine


@pytest.fixture
def mock_connection():
    """Create a mock database connection."""
    conn = MagicMock()
    return conn


class TestGetMigrationInfo:
    """Test get_migration_info function."""

    def test_get_migration_info_success(self, mock_engine, mock_connection):
        """Test successful retrieval of migration info."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = "ba97cf8e4fdf"
        mock_connection.execute.return_value = mock_result
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.__exit__.return_value = None
        mock_engine.connect.return_value = mock_connection

        # Execute
        full_revision, short_version = get_migration_info(mock_engine)

        # Verify
        assert full_revision == "ba97cf8e4fdf"
        assert short_version == "0002"
        mock_connection.execute.assert_called_once()

    def test_get_migration_info_version_0001(self, mock_engine, mock_connection):
        """Test retrieval of first migration version."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = "e8a217c84204"
        mock_connection.execute.return_value = mock_result
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.__exit__.return_value = None
        mock_engine.connect.return_value = mock_connection

        # Execute
        full_revision, short_version = get_migration_info(mock_engine)

        # Verify
        assert full_revision == "e8a217c84204"
        assert short_version == "0001"

    def test_get_migration_info_unknown_version(self, mock_engine, mock_connection):
        """Test retrieval of unknown migration version."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = "unknown123"
        mock_connection.execute.return_value = mock_result
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.__exit__.return_value = None
        mock_engine.connect.return_value = mock_connection

        # Execute
        full_revision, short_version = get_migration_info(mock_engine)

        # Verify
        assert full_revision == "unknown123"
        assert short_version == "unknown"

    def test_get_migration_info_no_version_found(self, mock_engine, mock_connection):
        """Test when no version is found in alembic_version table."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = None
        mock_connection.execute.return_value = mock_result
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.__exit__.return_value = None
        mock_engine.connect.return_value = mock_connection

        # Execute & Verify
        with pytest.raises(RuntimeError, match="No version found in alembic_version table"):
            get_migration_info(mock_engine)

    def test_get_migration_info_connection_error(self, mock_engine):
        """Test handling of connection errors."""
        # Setup
        mock_engine.connect.side_effect = Exception("Connection failed")

        # Execute & Verify
        with pytest.raises(Exception, match="Connection failed"):
            get_migration_info(mock_engine)


class TestValidateSchemaVersion:
    """Test validate_schema_version function."""

    @patch("app.cron.db.migrations_check.get_migration_info")
    def test_validate_schema_version_success(self, mock_get_info, mock_engine):
        """Test successful schema validation."""
        # Setup
        mock_get_info.return_value = (EXPECTED_REVISION, EXPECTED_REVISION_SHORT)

        # Execute
        result = validate_schema_version(mock_engine, strict=True)

        # Verify
        assert result is True
        mock_get_info.assert_called_once_with(mock_engine)

    @patch("app.cron.db.migrations_check.get_migration_info")
    def test_validate_schema_version_mismatch_strict(self, mock_get_info, mock_engine):
        """Test schema validation with mismatch in strict mode."""
        # Setup
        mock_get_info.return_value = ("e8a217c84204", "0001")

        # Execute & Verify
        with pytest.raises(SchemaMismatchError) as exc_info:
            validate_schema_version(mock_engine, strict=True)

        assert "Schema version mismatch" in str(exc_info.value)
        assert EXPECTED_REVISION in str(exc_info.value)
        assert "e8a217c84204" in str(exc_info.value)

    @patch("app.cron.db.migrations_check.get_migration_info")
    def test_validate_schema_version_mismatch_non_strict(self, mock_get_info, mock_engine):
        """Test schema validation with mismatch in non-strict mode."""
        # Setup
        mock_get_info.return_value = ("e8a217c84204", "0001")

        # Execute
        result = validate_schema_version(mock_engine, strict=False)

        # Verify
        assert result is False

    @patch("app.cron.db.migrations_check.get_migration_info")
    def test_validate_schema_version_unexpected_error(self, mock_get_info, mock_engine):
        """Test handling of unexpected errors during validation."""
        # Setup
        mock_get_info.side_effect = Exception("Unexpected error")

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Failed to validate schema version"):
            validate_schema_version(mock_engine, strict=True)

    @patch("app.cron.db.migrations_check.get_migration_info")
    def test_validate_schema_version_mismatch_error_propagates(self, mock_get_info, mock_engine):
        """Test that SchemaMismatchError propagates correctly."""
        # Setup
        mock_get_info.return_value = ("wrong_version", "unknown")

        # Execute & Verify
        with pytest.raises(SchemaMismatchError):
            validate_schema_version(mock_engine, strict=True)
