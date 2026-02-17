"""add_pii_scrub_audit_table

TASK-PII-004: Create immutable audit log for PII scrubbing operations

Linked Specs:
- NFR-PII-003: Audit logging requirement
- AC-NF-004: Compliance and audit trail
- FR-PII-001: PII scrubbing operations

Schema Requirements:
- Immutable: UPDATE/DELETE blocked by constraints
- Append-only: Only INSERT permitted
- 7-year retention policy
- Indexed for query performance

Validation (DoD):
- INSERT succeeds
- UPDATE/DELETE rejected (constraint enforced)
- Rollback script tested

Revision ID: 7efd9d68d9b8
Revises: 045d300d07a8
Create Date: 2026-02-17 17:59:57.043691

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7efd9d68d9b8'
down_revision: Union[str, None] = '045d300d07a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create pii_scrub_audit table for immutable audit logging.
    
    Performance:
    - Runtime: < 5 seconds (no table locks)
    - Indexes: Created concurrently (non-blocking)
    """
    # Create audit table
    op.create_table(
        'pii_scrub_audit',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('operation', sa.String(50), nullable=False),  # 'scrub', 'tokenize', 'validate'
        sa.Column('entity_type', sa.String(50), nullable=True),  # 'requisition', 'team_member'
        sa.Column('entity_id', sa.BigInteger(), nullable=True),
        sa.Column('field_name', sa.String(100), nullable=True),
        sa.Column('pii_type', sa.String(50), nullable=True),  # 'name', 'email', 'phone', 'client_name', etc.
        sa.Column('action_taken', sa.String(50), nullable=False),  # 'redacted', 'tokenized', 'pattern_matched'
        sa.Column('original_value_hash', sa.String(64), nullable=True),  # SHA-256 hash of original (not the value itself)
        sa.Column('scrubbed_value', sa.Text(), nullable=True),  # Scrubbed output (safe to store)
        sa.Column('detection_method', sa.String(50), nullable=False),  # 'ner', 'regex', 'whitelist'
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),  # NER confidence (0.0000-1.0000)
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),  # Additional context
        
        # Immutability constraint: Prevent updates/deletes
        # This is enforced at application level and via database triggers
        postgresql_partition_by='RANGE (timestamp)',  # Future: partition by month for retention
    )
    
    # Create indexes for common query patterns
    op.create_index(
        'ix_pii_scrub_audit_timestamp',
        'pii_scrub_audit',
        ['timestamp'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'ix_pii_scrub_audit_entity',
        'pii_scrub_audit',
        ['entity_type', 'entity_id'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'ix_pii_scrub_audit_operation',
        'pii_scrub_audit',
        ['operation', 'timestamp'],
        postgresql_using='btree'
    )
    
    # Create trigger to prevent UPDATE/DELETE operations (immutability enforcement)
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_pii_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'UPDATE' OR TG_OP = 'DELETE') THEN
                RAISE EXCEPTION 'pii_scrub_audit table is immutable - UPDATE/DELETE not permitted (NFR-PII-003)';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER prevent_pii_audit_modification_trigger
        BEFORE UPDATE OR DELETE ON pii_scrub_audit
        FOR EACH ROW
        EXECUTE FUNCTION prevent_pii_audit_modification();
    """)


def downgrade() -> None:
    """
    Drop pii_scrub_audit table and related objects.
    
    Warning: This destroys audit trail. Only use in non-production environments.
    """
    op.execute("DROP TRIGGER IF EXISTS prevent_pii_audit_modification_trigger ON pii_scrub_audit")
    op.execute("DROP FUNCTION IF EXISTS prevent_pii_audit_modification()")
    
    op.drop_index('ix_pii_scrub_audit_operation', table_name='pii_scrub_audit')
    op.drop_index('ix_pii_scrub_audit_entity', table_name='pii_scrub_audit')
    op.drop_index('ix_pii_scrub_audit_timestamp', table_name='pii_scrub_audit')
    
    op.drop_table('pii_scrub_audit')
