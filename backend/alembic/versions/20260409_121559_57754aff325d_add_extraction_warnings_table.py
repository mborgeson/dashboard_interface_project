"""add extraction_warnings table

Revision ID: 57754aff325d
Revises: 910fe9a245a6
Create Date: 2026-04-09 12:15:59.373229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57754aff325d'
down_revision: Union[str, None] = '910fe9a245a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table('extraction_warnings',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('extraction_run_id', sa.UUID(as_uuid=False), nullable=True),
    sa.Column('property_name', sa.String(length=500), nullable=False),
    sa.Column('source_file', sa.String(length=1000), nullable=True),
    sa.Column('warning_type', sa.String(length=50), nullable=False),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('field_name', sa.String(length=200), nullable=True),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('details', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['extraction_run_id'], ['extraction_runs.id'], name=op.f('fk_extraction_warnings_extraction_run_id_extraction_runs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_extraction_warnings'))
    )
    op.create_index(op.f('ix_extraction_warnings_extraction_run_id'), 'extraction_warnings', ['extraction_run_id'], unique=False)
    op.create_index(op.f('ix_extraction_warnings_property_name'), 'extraction_warnings', ['property_name'], unique=False)
    op.create_index(op.f('ix_extraction_warnings_warning_type'), 'extraction_warnings', ['warning_type'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index(op.f('ix_extraction_warnings_warning_type'), table_name='extraction_warnings')
    op.drop_index(op.f('ix_extraction_warnings_property_name'), table_name='extraction_warnings')
    op.drop_index(op.f('ix_extraction_warnings_extraction_run_id'), table_name='extraction_warnings')
    op.drop_table('extraction_warnings')
