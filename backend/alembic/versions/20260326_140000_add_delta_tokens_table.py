"""add delta_tokens table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-26 14:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create delta_tokens table for incremental SharePoint sync."""
    op.create_table('delta_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('drive_id', sa.String(length=255), nullable=False),
        sa.Column('delta_token', sa.Text(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_delta_tokens'))
    )
    op.create_index(op.f('ix_delta_tokens_drive_id'), 'delta_tokens', ['drive_id'], unique=True)
    op.create_index(op.f('ix_delta_tokens_id'), 'delta_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_delta_tokens_created_at'), 'delta_tokens', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop delta_tokens table."""
    op.drop_index(op.f('ix_delta_tokens_created_at'), table_name='delta_tokens')
    op.drop_index(op.f('ix_delta_tokens_id'), table_name='delta_tokens')
    op.drop_index(op.f('ix_delta_tokens_drive_id'), table_name='delta_tokens')
    op.drop_table('delta_tokens')
