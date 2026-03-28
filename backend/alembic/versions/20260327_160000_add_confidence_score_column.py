"""add confidence_score and etag columns

Revision ID: b2c3d4e5f6a7
Revises: a2b3c4d5e6f7
Create Date: 2026-03-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add confidence_score to extracted_values (UR-041) and etag to monitored_files (UR-030)."""
    op.add_column(
        'extracted_values',
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),
    )
    op.add_column(
        'monitored_files',
        sa.Column('etag', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Remove confidence_score and etag columns."""
    op.drop_column('monitored_files', 'etag')
    op.drop_column('extracted_values', 'confidence_score')
