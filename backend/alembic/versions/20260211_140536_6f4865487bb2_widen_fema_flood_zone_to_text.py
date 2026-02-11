"""widen fema_flood_zone to text

Revision ID: 6f4865487bb2
Revises: 2f2093cc37a2
Create Date: 2026-02-11 14:05:36.104969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f4865487bb2'
down_revision: Union[str, None] = '2f2093cc37a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen fema_flood_zone from varchar(100) to text."""
    op.alter_column(
        'construction_projects',
        'fema_flood_zone',
        existing_type=sa.VARCHAR(length=100),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert fema_flood_zone back to varchar(100)."""
    op.alter_column(
        'construction_projects',
        'fema_flood_zone',
        existing_type=sa.Text(),
        type_=sa.VARCHAR(length=100),
        existing_nullable=True,
    )
