"""create feedback table

Revision ID: 937cc5c69c28
Revises: 045d300d07a8
Create Date: 2026-03-03 16:58:40.105959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '937cc5c69c28'
down_revision: Union[str, None] = '045d300d07a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create table
    op.create_table(
        'requisition_match_team_member_feedback',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column('team_member_id', sa.String(length=50), nullable=False),
        sa.Column('correlation_id', sa.String(length=100), nullable=False),
        sa.Column('reviewer_email', sa.String(length=100), nullable=False),
        sa.Column('liked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('rating', sa.SmallInteger(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
        sa.UniqueConstraint('team_member_id', 'correlation_id', 'reviewer_email', name='uq_feedback_reviewer_match')
    )
    
    # Create indexes
    op.create_index('idx_feedback_correlation_id', 'requisition_match_team_member_feedback', ['correlation_id'])
    op.create_index('idx_feedback_team_member_id', 'requisition_match_team_member_feedback', ['team_member_id'])

    # Add trigger for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_feedback_updated_at
        BEFORE UPDATE ON requisition_match_team_member_feedback
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_feedback_updated_at ON requisition_match_team_member_feedback")
    op.drop_index('idx_feedback_team_member_id', table_name='requisition_match_team_member_feedback')
    op.drop_index('idx_feedback_correlation_id', table_name='requisition_match_team_member_feedback')
    op.drop_table('requisition_match_team_member_feedback')
