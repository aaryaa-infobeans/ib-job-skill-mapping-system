"""
Audit Logger - NFR-PII-003, TASK-PII-004

Implements immutable audit logging for PII scrubbing operations.

Requirements:
- Append-only: Only INSERT operations permitted
- Immutable: UPDATE/DELETE blocked by database triggers
- 7-year retention policy
- Queryable for compliance audits

Linked Specs:
- NFR-PII-003: Audit logging requirement
- AC-NF-004: Compliance and audit trail
- TASK-PII-004: pii_scrub_audit table implementation
"""

import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class PIIAuditLogger:
    """Immutable audit logger for PII scrubbing operations."""
    
    def __init__(self, db_session: Session, enabled: bool = True):
        """
        Initialize audit logger.
        
        Args:
            db_session: SQLAlchemy database session
            enabled: Enable/disable audit logging (default: True)
        """
        self.db_session = db_session
        self.enabled = enabled
    
    def log_scrub_operation(
        self,
        operation: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        field_name: Optional[str] = None,
        pii_type: Optional[str] = None,
        action_taken: str = "unknown",
        original_value: Optional[str] = None,
        scrubbed_value: Optional[str] = None,
        detection_method: str = "unknown",
        confidence_score: Optional[float] = None,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log PII scrubbing operation to immutable audit table.
        
        Args:
            operation: Operation type ('scrub', 'tokenize', 'validate')
            entity_type: Entity type ('requisition', 'team_member')
            entity_id: Entity primary key
            field_name: Field name that was scrubbed
            pii_type: PII type ('name', 'email', 'phone', 'client_name', etc.)
            action_taken: Action taken ('redacted', 'tokenized', 'pattern_matched')
            original_value: Original value (will be hashed, not stored directly)
            scrubbed_value: Scrubbed output (safe to store)
            detection_method: Detection method ('ner', 'regex', 'whitelist')
            confidence_score: NER confidence score (0.0-1.0)
            user_id: User who triggered the operation
            session_id: Session identifier
            metadata: Additional context (JSON)
        
        Returns:
            True if logged successfully, False otherwise
        
        Security:
        - Original value is hashed with SHA-256 (not stored in plaintext)
        - Only scrubbed value is stored
        - Immutability enforced by database trigger
        
        Performance:
        - Async queueing can be added for high-throughput scenarios
        - Current implementation is synchronous
        """
        if not self.enabled:
            logger.debug("Audit logging disabled, skipping log entry")
            return True
        
        try:
            # Hash original value (never store PII in audit log)
            original_value_hash = None
            if original_value:
                original_value_hash = hashlib.sha256(
                    original_value.encode('utf-8')
                ).hexdigest()
            
            # Insert audit record (raw SQL for performance)
            insert_sql = text("""
                INSERT INTO pii_scrub_audit (
                    timestamp,
                    operation,
                    entity_type,
                    entity_id,
                    field_name,
                    pii_type,
                    action_taken,
                    original_value_hash,
                    scrubbed_value,
                    detection_method,
                    confidence_score,
                    user_id,
                    session_id,
                    metadata
                ) VALUES (
                    NOW(),
                    :operation,
                    :entity_type,
                    :entity_id,
                    :field_name,
                    :pii_type,
                    :action_taken,
                    :original_value_hash,
                    :scrubbed_value,
                    :detection_method,
                    :confidence_score,
                    :user_id,
                    :session_id,
                    :metadata
                )
            """)
            
            import json
            self.db_session.execute(insert_sql, {
                'operation': operation,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'field_name': field_name,
                'pii_type': pii_type,
                'action_taken': action_taken,
                'original_value_hash': original_value_hash,
                'scrubbed_value': scrubbed_value,
                'detection_method': detection_method,
                'confidence_score': confidence_score,
                'user_id': user_id,
                'session_id': session_id,
                'metadata': json.dumps(metadata) if metadata else None
            })
            
            # Commit immediately for audit trail integrity
            self.db_session.commit()
            
            logger.debug(
                "Audit log: operation=%s, entity=%s/%s, pii_type=%s, action=%s",
                operation, entity_type, entity_id, pii_type, action_taken
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            try:
                self.db_session.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback session: {rollback_error}")
            # Don't fail the main operation if audit logging fails
            # But log the error for investigation
            return False
    
    def log_tokenization(
        self,
        original_value: str,
        token: str,
        token_type: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> bool:
        """
        Log tokenization operation.
        
        Args:
            original_value: Original value (will be hashed)
            token: Generated token
            token_type: Token type ('CLIENT', 'PROJECT')
            entity_type: Entity type
            entity_id: Entity ID
        
        Returns:
            True if logged successfully
        """
        return self.log_scrub_operation(
            operation='tokenize',
            entity_type=entity_type,
            entity_id=entity_id,
            pii_type=token_type.lower() + '_name',
            action_taken='tokenized',
            original_value=original_value,
            scrubbed_value=token,
            detection_method='deterministic_hash',
            confidence_score=1.0,
            metadata={'token_type': token_type}
        )
    
    def log_redaction(
        self,
        original_value: str,
        redacted_value: str,
        pii_type: str,
        detection_method: str,
        confidence_score: Optional[float] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        field_name: Optional[str] = None
    ) -> bool:
        """
        Log redaction operation.
        
        Args:
            original_value: Original value (will be hashed)
            redacted_value: Redacted output (e.g., "[REDACTED]")
            pii_type: PII type ('name', 'email', 'phone')
            detection_method: Detection method ('ner', 'regex')
            confidence_score: Detection confidence
            entity_type: Entity type
            entity_id: Entity ID
            field_name: Field name
        
        Returns:
            True if logged successfully
        """
        return self.log_scrub_operation(
            operation='scrub',
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            pii_type=pii_type,
            action_taken='redacted',
            original_value=original_value,
            scrubbed_value=redacted_value,
            detection_method=detection_method,
            confidence_score=confidence_score
        )
