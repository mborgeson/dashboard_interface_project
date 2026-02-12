"""add reminder_dismissals table

Revision ID: d7d1ad81d3c0
Revises: 6f4865487bb2
Create Date: 2026-02-12 08:14:00.808157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7d1ad81d3c0'
down_revision: Union[str, None] = '6f4865487bb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table('reminder_dismissals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_identifier', sa.String(length=255), nullable=False),
        sa.Column('dismissed_month', sa.String(length=7), nullable=False),
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_reminder_dismissals')),
        sa.UniqueConstraint('user_identifier', 'dismissed_month', name='uq_reminder_dismissal_user_month')
    )
    op.create_index('ix_reminder_dismissals_month', 'reminder_dismissals', ['dismissed_month'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index('ix_reminder_dismissals_month', table_name='reminder_dismissals')
    op.drop_table('reminder_dismissals')
