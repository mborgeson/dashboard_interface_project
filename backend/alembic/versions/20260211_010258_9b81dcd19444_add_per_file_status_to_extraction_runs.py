"""add per_file_status to extraction_runs

Revision ID: 9b81dcd19444
Revises: 351e79816af3
Create Date: 2026-02-11 01:02:58.444620

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b81dcd19444'
down_revision: Union[str, None] = '351e79816af3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add per_file_status JSON column for retry/resume support."""
    op.add_column('extraction_runs', sa.Column('per_file_status', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove per_file_status column."""
    op.drop_column('extraction_runs', 'per_file_status')
