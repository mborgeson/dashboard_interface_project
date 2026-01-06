"""Add monitored_files and file_change_logs tables

Revision ID: a1b2c3d4e5f6
Revises: 896670eb4597
Create Date: 2026-01-06 07:04:31.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '896670eb4597'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create monitored_files table
    op.create_table(
        'monitored_files',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('deal_name', sa.String(length=255), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('modified_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_checked', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_extracted', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('extraction_pending', sa.Boolean(), nullable=False, default=False),
        sa.Column('extraction_run_id', sa.UUID(), nullable=True),
        sa.Column('deal_stage', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['extraction_run_id'],
            ['extraction_runs.id'],
            name=op.f('fk_monitored_files_extraction_run_id_extraction_runs'),
            ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_monitored_files')),
        sa.UniqueConstraint('file_path', name=op.f('uq_monitored_files_file_path'))
    )
    op.create_index(op.f('ix_monitored_files_id'), 'monitored_files', ['id'], unique=False)
    op.create_index(op.f('ix_monitored_files_file_path'), 'monitored_files', ['file_path'], unique=True)
    op.create_index(op.f('ix_monitored_files_deal_name'), 'monitored_files', ['deal_name'], unique=False)
    op.create_index(op.f('ix_monitored_files_extraction_run_id'), 'monitored_files', ['extraction_run_id'], unique=False)
    op.create_index('idx_monitored_files_deal', 'monitored_files', ['deal_name', 'is_active'], unique=False)
    op.create_index('idx_monitored_files_pending', 'monitored_files', ['extraction_pending', 'is_active'], unique=False)

    # Create file_change_logs table
    op.create_table(
        'file_change_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('deal_name', sa.String(length=255), nullable=False),
        sa.Column('change_type', sa.String(length=20), nullable=False),
        sa.Column('old_modified_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('new_modified_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('old_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('new_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('monitored_file_id', sa.UUID(), nullable=True),
        sa.Column('extraction_triggered', sa.Boolean(), nullable=False, default=False),
        sa.Column('extraction_run_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['monitored_file_id'],
            ['monitored_files.id'],
            name=op.f('fk_file_change_logs_monitored_file_id_monitored_files'),
            ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['extraction_run_id'],
            ['extraction_runs.id'],
            name=op.f('fk_file_change_logs_extraction_run_id_extraction_runs'),
            ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_file_change_logs'))
    )
    op.create_index(op.f('ix_file_change_logs_id'), 'file_change_logs', ['id'], unique=False)
    op.create_index(op.f('ix_file_change_logs_file_path'), 'file_change_logs', ['file_path'], unique=False)
    op.create_index(op.f('ix_file_change_logs_deal_name'), 'file_change_logs', ['deal_name'], unique=False)
    op.create_index(op.f('ix_file_change_logs_change_type'), 'file_change_logs', ['change_type'], unique=False)
    op.create_index(op.f('ix_file_change_logs_monitored_file_id'), 'file_change_logs', ['monitored_file_id'], unique=False)
    op.create_index('idx_file_change_logs_detected', 'file_change_logs', ['detected_at'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop file_change_logs table
    op.drop_index('idx_file_change_logs_detected', table_name='file_change_logs')
    op.drop_index(op.f('ix_file_change_logs_monitored_file_id'), table_name='file_change_logs')
    op.drop_index(op.f('ix_file_change_logs_change_type'), table_name='file_change_logs')
    op.drop_index(op.f('ix_file_change_logs_deal_name'), table_name='file_change_logs')
    op.drop_index(op.f('ix_file_change_logs_file_path'), table_name='file_change_logs')
    op.drop_index(op.f('ix_file_change_logs_id'), table_name='file_change_logs')
    op.drop_table('file_change_logs')

    # Drop monitored_files table
    op.drop_index('idx_monitored_files_pending', table_name='monitored_files')
    op.drop_index('idx_monitored_files_deal', table_name='monitored_files')
    op.drop_index(op.f('ix_monitored_files_extraction_run_id'), table_name='monitored_files')
    op.drop_index(op.f('ix_monitored_files_deal_name'), table_name='monitored_files')
    op.drop_index(op.f('ix_monitored_files_file_path'), table_name='monitored_files')
    op.drop_index(op.f('ix_monitored_files_id'), table_name='monitored_files')
    op.drop_table('monitored_files')
