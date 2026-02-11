"""add file_metadata to extraction_runs

Revision ID: b1e88c02306b
Revises: 9b81dcd19444
Create Date: 2026-02-11 01:07:32.183367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1e88c02306b'
down_revision: Union[str, None] = '9b81dcd19444'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add file_metadata JSON column for per-file extraction statistics."""
    op.add_column('extraction_runs', sa.Column('file_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove file_metadata column."""
    op.drop_column('extraction_runs', 'file_metadata')
