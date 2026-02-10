"""Unit tests for database metadata module."""

import pytest
from app.cron.db.metadata import (
    metadata,
    ingestion_batch_state,
    ingestion_audit_log,
    team_member,
    skill_master,
    category_master,
)


class TestMetadata:
    """Test metadata object and table definitions."""

    def test_metadata_object_exists(self):
        """Test metadata object is properly instantiated."""
        assert metadata is not None
        assert len(metadata.tables) > 0

    def test_ingestion_batch_state_table(self):
        """Test ingestion_batch_state table definition."""
        table = ingestion_batch_state

        # Verify table name
        assert table.name == "ingestion_batch_state"

        # Verify columns exist
        column_names = {col.name for col in table.columns}
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
        assert column_names == expected_columns

        # Verify primary key
        pk_columns = {col.name for col in table.primary_key.columns}
        assert pk_columns == {"batch_id"}

        # Verify column properties
        assert table.c.batch_id.nullable is False
        assert table.c.correlation_id.nullable is False
        assert table.c.status.nullable is False
        assert table.c.total_records.nullable is True
        assert table.c.completed_at.nullable is True

    def test_ingestion_audit_log_table(self):
        """Test ingestion_audit_log table definition."""
        table = ingestion_audit_log

        # Verify table name
        assert table.name == "ingestion_audit_log"

        # Verify columns exist
        column_names = {col.name for col in table.columns}
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
        assert column_names == expected_columns

        # Verify primary key
        pk_columns = {col.name for col in table.primary_key.columns}
        assert pk_columns == {"id"}

        # Verify foreign key
        foreign_keys = list(table.foreign_keys)
        assert len(foreign_keys) == 1
        fk = foreign_keys[0]
        assert fk.column.table.name == "ingestion_batch_state"
        assert fk.column.name == "batch_id"

        # Verify column properties
        assert table.c.id.nullable is False
        assert table.c.batch_id.nullable is False
        assert table.c.event_type.nullable is False
        assert table.c.event_details.nullable is True

    def test_existing_tables_imported(self):
        """Test that existing tables are properly imported."""
        # Verify team_member table
        assert team_member.name == "team_member"
        assert "team_member_id" in {col.name for col in team_member.columns}

        # Verify skill_master table
        assert skill_master.name == "skill_master"
        assert "skill_id" in {col.name for col in skill_master.columns}

        # Verify category_master table
        assert category_master.name == "category_master"
        assert "category_id" in {col.name for col in category_master.columns}

    def test_team_member_table_structure(self):
        """Test team_member table has expected structure."""
        table = team_member

        expected_columns = {
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

        column_names = {col.name for col in table.columns}
        assert column_names == expected_columns

        # Verify primary key
        pk_columns = {col.name for col in table.primary_key.columns}
        assert pk_columns == {"team_member_id"}

    def test_skill_master_foreign_key(self):
        """Test skill_master has foreign key to category_master."""
        table = skill_master

        foreign_keys = list(table.foreign_keys)
        assert len(foreign_keys) == 1

        fk = foreign_keys[0]
        assert fk.column.table.name == "category_master"
        assert fk.column.name == "category_id"

    def test_all_tables_in_metadata(self):
        """Test all expected tables are registered in metadata."""
        table_names = set(metadata.tables.keys())

        # Check ingestion tables
        assert "ingestion_batch_state" in table_names
        assert "ingestion_audit_log" in table_names

        # Check existing tables
        assert "team_member" in table_names
        assert "skill_master" in table_names
        assert "category_master" in table_names
        assert "team_member_skill" in table_names
        assert "team_member_allocation" in table_names

    def test_metadata_can_generate_ddl(self):
        """Test metadata can generate DDL statements."""
        from sqlalchemy.schema import CreateTable

        # Should be able to generate CREATE statements
        for table_name in ["ingestion_batch_state", "ingestion_audit_log"]:
            table = metadata.tables[table_name]
            ddl = CreateTable(table)
            ddl_str = str(ddl.compile())

            assert "CREATE TABLE" in ddl_str
            assert table_name in ddl_str
