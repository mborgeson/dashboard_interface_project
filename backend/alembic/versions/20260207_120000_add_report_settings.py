"""Add report_settings table

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-02-07 12:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "company_name",
            sa.String(length=255),
            server_default="B&R Capital",
            nullable=False,
        ),
        sa.Column("company_logo", sa.String(length=1024), nullable=True),
        sa.Column(
            "primary_color",
            sa.String(length=20),
            server_default="#1e40af",
            nullable=False,
        ),
        sa.Column(
            "secondary_color",
            sa.String(length=20),
            server_default="#059669",
            nullable=False,
        ),
        sa.Column(
            "default_font",
            sa.String(length=100),
            server_default="Inter",
            nullable=False,
        ),
        sa.Column(
            "default_page_size",
            sa.String(length=10),
            server_default="letter",
            nullable=False,
        ),
        sa.Column(
            "default_orientation",
            sa.String(length=10),
            server_default="portrait",
            nullable=False,
        ),
        sa.Column(
            "include_page_numbers",
            sa.Boolean(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "include_table_of_contents",
            sa.Boolean(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "include_timestamp",
            sa.Boolean(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "footer_text",
            sa.String(length=500),
            server_default="Confidential - For Internal Use Only",
            nullable=False,
        ),
        sa.Column(
            "header_text",
            sa.String(length=500),
            server_default="B&R Capital Real Estate Analytics",
            nullable=False,
        ),
        sa.Column("watermark_text", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_settings")),
    )

    # Seed the singleton defaults row
    op.execute("INSERT INTO report_settings (id) VALUES (1)")


def downgrade() -> None:
    op.drop_table("report_settings")
