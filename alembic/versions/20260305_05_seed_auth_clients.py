"""Seed auth_clients with default development client

Revision ID: 20260305_05
Revises: 20260305_04
Create Date: 2026-03-05 12:00:00.000000

Inserts the default auth client (id=1, client_code='test-client') required
by requisition_requests.auth_client_id FK in local/dev environments.
Operation is idempotent via ON CONFLICT DO NOTHING.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260305_05"
down_revision: Union[str, None] = "20260305_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# SHA-256 of "test-secret" — placeholder hash for dev/test only
_TEST_SECRET_HASH = "9caf06bb4436cdbfa20af9121a626bc1093c4f54b31c0fa937957856135345b6"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO auth_clients (id, client_name, client_code, client_secret_hash, auth_type, is_active)
            VALUES (1, 'Test Client', 'test-client', :secret_hash, 'OAUTH', true)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(secret_hash=_TEST_SECRET_HASH)
    )
    # Advance the sequence past 1 so auto-increment inserts don't collide
    op.execute("SELECT setval('auth_clients_id_seq', GREATEST(1, (SELECT MAX(id) FROM auth_clients)))")


def downgrade() -> None:
    op.execute("DELETE FROM auth_clients WHERE client_code = 'test-client'")
