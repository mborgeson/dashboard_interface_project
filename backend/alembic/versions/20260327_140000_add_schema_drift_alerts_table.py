"""add schema_drift_alerts table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-27 14:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create schema_drift_alerts table for drift detection persistence."""
    op.create_table('schema_drift_alerts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('group_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('similarity_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('changed_sheets', sa.JSON(), nullable=True),
        sa.Column('missing_sheets', sa.JSON(), nullable=True),
        sa.Column('new_sheets', sa.JSON(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_schema_drift_alerts'))
    )
    op.create_index(op.f('ix_schema_drift_alerts_id'), 'schema_drift_alerts', ['id'], unique=False)
    op.create_index(op.f('ix_schema_drift_alerts_group_name'), 'schema_drift_alerts', ['group_name'], unique=False)
    op.create_index(op.f('ix_schema_drift_alerts_severity'), 'schema_drift_alerts', ['severity'], unique=False)
    op.create_index(op.f('ix_schema_drift_alerts_created_at'), 'schema_drift_alerts', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop schema_drift_alerts table."""
    op.drop_index(op.f('ix_schema_drift_alerts_created_at'), table_name='schema_drift_alerts')
    op.drop_index(op.f('ix_schema_drift_alerts_severity'), table_name='schema_drift_alerts')
    op.drop_index(op.f('ix_schema_drift_alerts_group_name'), table_name='schema_drift_alerts')
    op.drop_index(op.f('ix_schema_drift_alerts_id'), table_name='schema_drift_alerts')
    op.drop_table('schema_drift_alerts')
