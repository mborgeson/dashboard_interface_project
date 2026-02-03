"""add_property_latitude_longitude_building_type_financial_data

Revision ID: 8e6fdd43a452
Revises: 7b8c9d0e1f2a
Create Date: 2026-02-02 15:19:12.728012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e6fdd43a452'
down_revision: Union[str, None] = '7b8c9d0e1f2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add latitude, longitude, building_type, and financial_data columns to properties."""
    op.add_column('properties', sa.Column('latitude', sa.Numeric(precision=10, scale=6), nullable=True))
    op.add_column('properties', sa.Column('longitude', sa.Numeric(precision=10, scale=6), nullable=True))
    op.add_column('properties', sa.Column('building_type', sa.String(length=50), nullable=True))
    op.add_column('properties', sa.Column('financial_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove latitude, longitude, building_type, and financial_data columns from properties."""
    op.drop_column('properties', 'financial_data')
    op.drop_column('properties', 'building_type')
    op.drop_column('properties', 'longitude')
    op.drop_column('properties', 'latitude')
