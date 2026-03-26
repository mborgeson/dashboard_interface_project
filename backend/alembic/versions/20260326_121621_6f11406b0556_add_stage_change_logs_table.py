"""add stage_change_logs table

Revision ID: 6f11406b0556
Revises: 152c800e6789
Create Date: 2026-03-26 12:16:21.913615

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f11406b0556'
down_revision: Union[str, None] = '152c800e6789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create stage_change_logs audit table."""
    op.create_table('stage_change_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('deal_id', sa.Integer(), nullable=False),
        sa.Column('old_stage', sa.String(length=50), nullable=True),
        sa.Column('new_stage', sa.String(length=50), nullable=False),
        sa.Column('source', sa.Enum('sharepoint_sync', 'user_kanban', 'extraction_sync', 'manual_override', name='stagechangesource', native_enum=False), nullable=False),
        sa.Column('changed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], name=op.f('fk_stage_change_logs_changed_by_user_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], name=op.f('fk_stage_change_logs_deal_id_deals'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_stage_change_logs'))
    )
    op.create_index(op.f('ix_stage_change_logs_changed_by_user_id'), 'stage_change_logs', ['changed_by_user_id'], unique=False)
    op.create_index(op.f('ix_stage_change_logs_created_at'), 'stage_change_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_stage_change_logs_deal_id'), 'stage_change_logs', ['deal_id'], unique=False)
    op.create_index(op.f('ix_stage_change_logs_id'), 'stage_change_logs', ['id'], unique=False)


def downgrade() -> None:
    """Drop stage_change_logs table."""
    op.drop_index(op.f('ix_stage_change_logs_id'), table_name='stage_change_logs')
    op.drop_index(op.f('ix_stage_change_logs_deal_id'), table_name='stage_change_logs')
    op.drop_index(op.f('ix_stage_change_logs_created_at'), table_name='stage_change_logs')
    op.drop_index(op.f('ix_stage_change_logs_changed_by_user_id'), table_name='stage_change_logs')
    op.drop_table('stage_change_logs')
