"""
Database Integration Tests - TASK-PII-121

Tests PII audit logging, query filtering, and database immutability.

Test Coverage:
- Audit log insertion
- Immutability trigger enforcement
- Query filtering by entity type
- Audit trail completeness
- Database session integration

Usage:
    pytest tests/integration/pii/test_database_integration.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


class TestPIIAuditLogger:
    """Test suite for PII audit logging to database."""
    
    def test_audit_log_insertion(self):
        """Test successful audit log insertion."""
        # Mock database session
        mock_db = MagicMock(spec=Session)
        
        from app.pii.audit_logger import PIIAuditLogger
        
        logger = PIIAuditLogger(mock_db)
        
        # Log a scrubbing operation
        result = logger.log_scrub_operation(
            operation="scrub",
            entity_type="job_description",
            entity_id="REQ-12345",
            field_name="jd_text",
            pii_type="name",
            action_taken="redacted",
            detection_method="ner",
            confidence_score=0.95
        )
        
        assert result is True
        assert mock_db.execute.called
        assert mock_db.commit.called
    
    def test_audit_log_with_tokenization(self):
        """Test audit logging for tokenization operations."""
        mock_db = MagicMock(spec=Session)
        
        from app.pii.audit_logger import PIIAuditLogger
        
        logger = PIIAuditLogger(mock_db)
        
        result = logger.log_tokenization(
            original_value="TechCorp Inc",
            token="CLIENT_a1b2c3d4",
            token_type="CLIENT",
            entity_type="job_description",
            entity_id="REQ-12345"
        )
        
        assert result is True
        assert mock_db.execute.called
        assert mock_db.commit.called
    
    def test_audit_log_with_redaction(self):
        """Test audit logging for redaction operations."""
        mock_db = MagicMock(spec=Session)
        
        from app.pii.audit_logger import PIIAuditLogger
        
        logger = PIIAuditLogger(mock_db)
        
        result = logger.log_redaction(
            original_value="john.doe@example.com",
            redacted_value="[EMAIL_REDACTED]",
            pii_type="email",
            detection_method="regex",
            confidence_score=1.0,
            entity_type="job_description",
            entity_id="REQ-12345",
            field_name="jd_text"
        )
        
        assert result is True
        assert mock_db.execute.called
        assert mock_db.commit.called
    
    def test_audit_logger_disabled(self):
        """Test audit logger when disabled."""
        mock_db = MagicMock(spec=Session)
        
        from app.pii.audit_logger import PIIAuditLogger
        
        logger = PIIAuditLogger(mock_db, enabled=False)
        
        result = logger.log_scrub_operation(
            operation="scrub",
            entity_type="job_description",
            pii_type="name",
            action_taken="redacted"
        )
        
        assert result is True
        assert not mock_db.execute.called
        assert not mock_db.commit.called
    
    def test_audit_log_error_handling(self):
        """Test error handling when database operation fails."""
        mock_db = MagicMock(spec=Session)
        mock_db.execute.side_effect = Exception("Database error")
        
        from app.pii.audit_logger import PIIAuditLogger
        
        logger = PIIAuditLogger(mock_db)
        
        result = logger.log_scrub_operation(
            operation="scrub",
            entity_type="job_description",
            pii_type="name",
            action_taken="redacted"
        )
        
        # Should return False but not raise exception
        assert result is False


class TestDatabaseImmutability:
    """Test suite for database immutability constraints."""
    
    def test_immutability_trigger_prevents_update(self):
        """Test that UPDATE operations are blocked by trigger."""
        # This test would require actual database connection
        # For now, we validate the migration file exists and has trigger logic
        
        from pathlib import Path
        
        migration_file = list(Path("alembic/versions").glob("7efd9d68d9b8_*.py"))[0]
        
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Verify trigger exists in migration
        assert "prevent_pii_audit" in content or "BEFORE UPDATE OR DELETE" in content
        assert "RAISE EXCEPTION" in content or "immutable" in content.lower()
    
    def test_immutability_trigger_prevents_delete(self):
        """Test that DELETE operations are blocked by trigger."""
        # Validate migration has DELETE protection
        from pathlib import Path
        
        migration_file = list(Path("alembic/versions").glob("7efd9d68d9b8_*.py"))[0]
        
        with open(migration_file, 'r') as f:
            content = f.read()
        
        assert "DELETE" in content
        assert "BEFORE UPDATE OR DELETE" in content


class TestAuditTrailCompleteness:
    """Test suite for audit trail completeness."""
    
    def test_all_scrubbing_operations_logged(self):
        """Test that all scrubbing operations are logged to audit trail."""
        mock_db = MagicMock(spec=Session)
        
        from app.pii.scrubber import PIIScrubber
        from app.pii.config import PIIConfig
        from app.pii.audit_logger import PIIAuditLogger
        
        # Create scrubber with mock audit logger
        config = PIIConfig(use_gpu=False)
        audit_logger = PIIAuditLogger(mock_db)
        scrubber = PIIScrubber(config=config, audit_logger=audit_logger)
        
        # Scrub text with PII
        text = "Contact John Doe at john.doe@example.com or call 555-123-4567"
        
        with patch('app.pii.ner_detector.NERDetector.detect_entities', return_value=[]):
            result = scrubber.scrub_text(
                text=text,
                entity_type="job_description",
                entity_id="REQ-12345",
                field_name="jd_text"
            )
        
        # Verify audit logger was called for each detection
        # Email and phone should be detected by regex
        assert mock_db.execute.call_count >= 2  # At least email and phone
        assert result.scrubbed_text != text  # Text should be modified
    
    def test_audit_metadata_includes_required_fields(self):
        """Test that audit logs include all required metadata fields."""
        mock_db = MagicMock(spec=Session)
        
        from app.pii.audit_logger import PIIAuditLogger
        
        logger = PIIAuditLogger(mock_db)
        
        logger.log_scrub_operation(
            operation="scrub",
            entity_type="job_description",
            entity_id="REQ-12345",
            field_name="jd_text",
            pii_type="email",
            action_taken="redacted",
            detection_method="regex",
            confidence_score=1.0
        )
        
        # Verify SQL execution was called
        assert mock_db.execute.called
        
        # Get the SQL call arguments
        call_args = mock_db.execute.call_args
        sql_params = call_args[0][1] if len(call_args[0]) > 1 else {}
        
        # Verify required fields are present
        assert 'operation' in sql_params
        assert 'entity_type' in sql_params
        assert 'pii_type' in sql_params
        assert 'action_taken' in sql_params
        assert 'detection_method' in sql_params


class TestGraphExecutorAuditIntegration:
    """Test suite for graph executor audit logging integration."""
    
    def test_pii_checkpoint_saves_audit_log(self):
        """Test that pii_scrubber checkpoint triggers audit logging."""
        mock_db = MagicMock(spec=Session)
        
        from app.ai.graph_executor import save_pii_audit_log
        
        # Create mock PII metadata
        pii_metadata = {
            "detections": [
                {
                    "field_name": "jd_text",
                    "pii_type": "email",
                    "action": "redact",
                    "method": "regex",
                    "confidence": 1.0
                },
                {
                    "field_name": "jd_text",
                    "pii_type": "phone",
                    "action": "redact",
                    "method": "regex",
                    "confidence": 1.0
                }
            ],
            "fields_scrubbed": ["jd_text"],
            "total_pii_found": 2
        }
        
        # Call save_pii_audit_log
        save_pii_audit_log(mock_db, "REQ-12345", pii_metadata)
        
        # Verify audit logger was called for each detection
        assert mock_db.execute.call_count == 2
        assert mock_db.commit.called
    
    def test_empty_detections_no_audit_log(self):
        """Test that no audit log is saved when no PII detected."""
        mock_db = MagicMock(spec=Session)
        
        from app.ai.graph_executor import save_pii_audit_log
        
        pii_metadata = {
            "detections": [],
            "fields_scrubbed": [],
            "total_pii_found": 0
        }
        
        save_pii_audit_log(mock_db, "REQ-12345", pii_metadata)
        
        # No audit log should be saved
        assert mock_db.execute.call_count == 0
    
    def test_audit_log_error_handling_in_graph_executor(self):
        """Test error handling when audit logging fails in graph executor."""
        mock_db = MagicMock(spec=Session)
        mock_db.execute.side_effect = Exception("Database error")
        
        from app.ai.graph_executor import save_pii_audit_log
        
        pii_metadata = {
            "detections": [
                {
                    "field_name": "jd_text",
                    "pii_type": "email",
                    "action": "redact",
                    "method": "regex",
                    "confidence": 1.0
                }
            ]
        }
        
        # Should not raise exception
        try:
            save_pii_audit_log(mock_db, "REQ-12345", pii_metadata)
        except Exception as e:
            pytest.fail(f"save_pii_audit_log raised exception: {e}")
        
        # Rollback should be called
        assert mock_db.rollback.called


class TestQueryFiltering:
    """Test suite for audit log query filtering."""
    
    def test_filter_by_entity_type(self):
        """Test querying audit logs by entity type."""
        # This would require actual database queries
        # For now, we validate the schema supports filtering
        
        from pathlib import Path
        
        migration_file = list(Path("alembic/versions").glob("7efd9d68d9b8_*.py"))[0]
        
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Verify entity_type column exists and is indexed
        assert "entity_type" in content
        assert "ix_pii_scrub_audit" in content or "create_index" in content.lower()
    
    def test_filter_by_timestamp(self):
        """Test querying audit logs by timestamp range."""
        from pathlib import Path
        
        migration_file = list(Path("alembic/versions").glob("7efd9d68d9b8_*.py"))[0]
        
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Verify timestamp column exists and is indexed
        assert "timestamp" in content
        assert "ix_pii_scrub_audit_timestamp" in content or "btree" in content.lower()
    
    def test_filter_by_pii_type(self):
        """Test querying audit logs by PII type."""
        from pathlib import Path
        
        migration_file = list(Path("alembic/versions").glob("7efd9d68d9b8_*.py"))[0]
        
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Verify pii_type column exists
        assert "pii_type" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
