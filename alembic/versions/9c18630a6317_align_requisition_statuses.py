"""align_requisition_statuses

Revision ID: 9c18630a6317
Revises: f1aefa807bca
Create Date: 2026-02-09 21:23:50.008012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c18630a6317'
down_revision: Union[str, None] = 'f1aefa807bca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename existing status_keys to avoid unique constraint violations during update
    op.execute("UPDATE requisition_status_master SET status_key = 'OLD_' || status_key")
    
    # 2. Update existing status records to match code intent:
    # ID 1: RECEIVED
    op.execute("UPDATE requisition_status_master SET status_key = 'RECEIVED', status_message = 'Request received and queued for processing' WHERE status_id = 1")
    
    # ID 2: PROCESSING
    op.execute("UPDATE requisition_status_master SET status_key = 'PROCESSING', status_message = 'AI pipeline is processing the request' WHERE status_id = 2")
    
    # ID 3: Change from COMPLETED to MATCHING (Move existing requests to 4 first)
    op.execute("UPDATE requisition_requests SET status = 4 WHERE status = 3")
    op.execute("UPDATE requisition_status_master SET status_key = 'MATCHING', status_message = 'AI pipeline is finding skill matches' WHERE status_id = 3")
    
    # ID 4: Change from FAILED to COMPLETED (Code already uses 4 for COMPLETED)
    op.execute("UPDATE requisition_status_master SET status_key = 'COMPLETED', status_message = 'Request processed successfully' WHERE status_id = 4")
    
    # ID 5: Change from CANCELLED to FAILED (Code already uses 5 for FAILED)
    op.execute("UPDATE requisition_status_master SET status_key = 'FAILED', status_message = 'Request processing failed' WHERE status_id = 5")
    
    # 3. Add CANCELLED as ID 6
    op.execute("INSERT INTO requisition_status_master (status_id, status_key, status_message) VALUES (6, 'CANCELLED', 'Request was cancelled')")


def downgrade() -> None:
    # 1. Rename to temporary
    op.execute("UPDATE requisition_status_master SET status_key = 'NEW_' || status_key")
    
    # 2. Remove ID 6
    op.execute("DELETE FROM requisition_status_master WHERE status_id = 6")
    
    # 3. Revert meanings:
    # ID 5: FAILED -> CANCELLED
    op.execute("UPDATE requisition_status_master SET status_key = 'CANCELLED', status_message = 'Request was cancelled' WHERE status_id = 5")
    
    # ID 4: COMPLETED -> FAILED
    op.execute("UPDATE requisition_status_master SET status_key = 'FAILED', status_message = 'Request processing failed' WHERE status_id = 4")
    
    # ID 3: MATCHING -> COMPLETED (Move requests back if they were moved?)
    # This is tricky because we can't easily track which 4s were originally 3s.
    # But 3 was likely not used much.
    op.execute("UPDATE requisition_status_master SET status_key = 'COMPLETED', status_message = 'Request processed successfully' WHERE status_id = 3")
    
    # ID 1 & 2: Restore keys
    op.execute("UPDATE requisition_status_master SET status_key = 'RECEIVED' WHERE status_id = 1")
    op.execute("UPDATE requisition_status_master SET status_key = 'PROCESSING' WHERE status_id = 2")
