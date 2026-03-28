"""add domain_warning column to extracted_values

Revision ID: a2b3c4d5e6f7
Revises: f6a7b8c9d0e1
Create Date: 2026-03-27 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add domain_warning column to extracted_values for domain validation flags."""
    op.add_column(
        'extracted_values',
        sa.Column('domain_warning', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    """Remove domain_warning column from extracted_values."""
    op.drop_column('extracted_values', 'domain_warning')
