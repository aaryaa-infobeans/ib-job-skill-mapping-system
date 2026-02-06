"""Unit tests for database engine module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.engine import Engine
from app.cron.db.engine import (
    create_ingestion_engine,
    get_engine,
    test_connection,
    dispose_engine,
    _engine,
)
from app.cron.db.migrations_check import SchemaMismatchError


@pytest.fixture(autouse=True)
def reset_global_engine():
    """Reset global engine before each test."""
    import app.cron.db.engine as engine_module
    engine_module._engine = None
    yield
    engine_module._engine = None


class TestCreateIngestionEngine:
    """Test create_ingestion_engine function."""

    @patch("app.cron.db.engine.validate_schema_version")
    @patch("app.cron.db.engine.create_engine")
    def test_create_ingestion_engine_success(self, mock_create_engine, mock_validate):
        """Test successful engine creation with default parameters."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Execute
        result = create_ingestion_engine()

        # Verify
        assert result == mock_engine
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args

        # Verify pool settings
        assert call_args.kwargs["pool_size"] == 5
        assert call_args.kwargs["max_overflow"] == 10
        assert call_args.kwargs["pool_pre_ping"] is True
        assert call_args.kwargs["pool_recycle"] == 3600

        mock_validate.assert_called_once_with(mock_engine, strict=True)

    @patch("app.cron.db.engine.validate_schema_version")
    @patch("app.cron.db.engine.create_engine")
    def test_create_ingestion_engine_custom_pool_settings(self, mock_create_engine, mock_validate):
        """Test engine creation with custom pool settings."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Execute
        result = create_ingestion_engine(
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=False,
            pool_recycle=7200,
        )

        # Verify
        call_args = mock_create_engine.call_args
        assert call_args.kwargs["pool_size"] == 10
        assert call_args.kwargs["max_overflow"] == 20
        assert call_args.kwargs["pool_pre_ping"] is False
        assert call_args.kwargs["pool_recycle"] == 7200

    @patch("app.cron.db.engine.validate_schema_version")
    @patch("app.cron.db.engine.create_engine")
    def test_create_ingestion_engine_skip_validation(self, mock_create_engine, mock_validate):
        """Test engine creation without schema validation."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Execute
        result = create_ingestion_engine(validate_schema=False)

        # Verify
        assert result == mock_engine
        mock_validate.assert_not_called()

    @patch("app.cron.db.engine.validate_schema_version")
    @patch("app.cron.db.engine.create_engine")
    def test_create_ingestion_engine_validation_failure(self, mock_create_engine, mock_validate):
        """Test engine creation with schema validation failure."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine
        mock_validate.side_effect = SchemaMismatchError("Schema mismatch")

        # Execute & Verify
        with pytest.raises(SchemaMismatchError):
            create_ingestion_engine()

    @patch("app.cron.db.engine.create_engine")
    def test_create_ingestion_engine_creation_failure(self, mock_create_engine):
        """Test handling of engine creation failure."""
        # Setup
        mock_create_engine.side_effect = Exception("Connection refused")

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Failed to create database engine"):
            create_ingestion_engine(validate_schema=False)


class TestGetEngine:
    """Test get_engine function."""

    @patch("app.cron.db.engine.create_ingestion_engine")
    def test_get_engine_creates_new_engine(self, mock_create):
        """Test get_engine creates new engine when none exists."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_create.return_value = mock_engine

        # Execute
        result = get_engine()

        # Verify
        assert result == mock_engine
        mock_create.assert_called_once()

    @patch("app.cron.db.engine.create_ingestion_engine")
    def test_get_engine_returns_existing_engine(self, mock_create):
        """Test get_engine returns existing engine."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_create.return_value = mock_engine

        # Execute
        result1 = get_engine()
        result2 = get_engine()

        # Verify
        assert result1 == result2
        mock_create.assert_called_once()  # Should only create once

    @patch("app.cron.db.engine.create_ingestion_engine")
    def test_get_engine_recreate(self, mock_create):
        """Test get_engine with recreate=True."""
        # Setup
        mock_engine1 = Mock(spec=Engine)
        mock_engine2 = Mock(spec=Engine)
        mock_create.side_effect = [mock_engine1, mock_engine2]

        # Execute
        result1 = get_engine()
        result2 = get_engine(recreate=True)

        # Verify
        assert result1 != result2
        assert mock_create.call_count == 2
        mock_engine1.dispose.assert_called_once()


class TestTestConnection:
    """Test test_connection function."""

    @patch("app.cron.db.engine.get_engine")
    def test_connection_success(self, mock_get_engine):
        """Test successful database connection test."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1

        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_engine.connect.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        # Execute
        result = test_connection()

        # Verify
        assert result is True
        mock_conn.execute.assert_called_once()

    @patch("app.cron.db.engine.get_engine")
    def test_connection_with_provided_engine(self, mock_get_engine):
        """Test connection test with provided engine."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1

        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_engine.connect.return_value = mock_conn

        # Execute
        result = test_connection(mock_engine)

        # Verify
        assert result is True
        mock_get_engine.assert_not_called()  # Should not call get_engine

    @patch("app.cron.db.engine.get_engine")
    def test_connection_unexpected_value(self, mock_get_engine):
        """Test connection test with unexpected return value."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 999  # Wrong value

        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_engine.connect.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        # Execute
        result = test_connection()

        # Verify
        assert result is False

    @patch("app.cron.db.engine.get_engine")
    def test_connection_failure(self, mock_get_engine):
        """Test connection test with connection failure."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_engine.connect.side_effect = Exception("Connection failed")
        mock_get_engine.return_value = mock_engine

        # Execute
        result = test_connection()

        # Verify
        assert result is False


class TestDisposeEngine:
    """Test dispose_engine function."""

    @patch("app.cron.db.engine.create_ingestion_engine")
    def test_dispose_engine_success(self, mock_create):
        """Test successful engine disposal."""
        # Setup
        mock_engine = Mock(spec=Engine)
        mock_create.return_value = mock_engine

        # Create engine first
        get_engine()

        # Execute
        dispose_engine()

        # Verify
        mock_engine.dispose.assert_called_once()

    def test_dispose_engine_no_engine(self):
        """Test dispose_engine when no engine exists."""
        # Execute (should not raise error)
        dispose_engine()
