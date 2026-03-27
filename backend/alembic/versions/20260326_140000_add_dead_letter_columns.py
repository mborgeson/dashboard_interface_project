"""add dead-letter tracking columns to monitored_files

Revision ID: d4e5f6a7b8c9
Revises: 6f11406b0556
Create Date: 2026-03-26 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = '6f11406b0556'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dead-letter / quarantine columns to monitored_files."""
    op.add_column(
        'monitored_files',
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'monitored_files',
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'monitored_files',
        sa.Column('last_failure_reason', sa.Text(), nullable=True),
    )
    op.add_column(
        'monitored_files',
        sa.Column('quarantined', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'monitored_files',
        sa.Column('quarantined_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'idx_monitored_files_quarantined',
        'monitored_files',
        ['quarantined', 'is_active'],
    )


def downgrade() -> None:
    """Remove dead-letter / quarantine columns from monitored_files."""
    op.drop_index('idx_monitored_files_quarantined', table_name='monitored_files')
    op.drop_column('monitored_files', 'quarantined_at')
    op.drop_column('monitored_files', 'quarantined')
    op.drop_column('monitored_files', 'last_failure_reason')
    op.drop_column('monitored_files', 'last_failure_at')
    op.drop_column('monitored_files', 'consecutive_failures')
