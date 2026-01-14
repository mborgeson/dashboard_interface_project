"""add_reporting_models

Revision ID: 7b8c9d0e1f2a
Revises: 5a6a158ce7de
Create Date: 2026-01-13 22:00:00.000000

Wave 2: Add Report Templates, Queued Reports, and Distribution Schedules
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b8c9d0e1f2a"
down_revision: Union[str, None] = "5a6a158ce7de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - add reporting tables."""
    # Create report_templates table
    op.create_table(
        "report_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "category", sa.String(length=50), nullable=False, server_default="custom"
        ),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("export_formats", sa.JSON(), nullable=False),
        sa.Column(
            "is_default", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_by", sa.String(length=255), nullable=False, server_default="System"
        ),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_templates")),
    )
    op.create_index(
        op.f("ix_report_templates_id"), "report_templates", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_report_templates_name"), "report_templates", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_report_templates_category"),
        "report_templates",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_templates_is_default"),
        "report_templates",
        ["is_default"],
        unique=False,
    )

    # Create queued_reports table
    op.create_table(
        "queued_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="pending"
        ),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("format", sa.String(length=50), nullable=False, server_default="pdf"),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_size", sa.String(length=50), nullable=True),
        sa.Column("download_url", sa.String(length=500), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["report_templates.id"],
            name=op.f("fk_queued_reports_template_id_report_templates"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_queued_reports")),
    )
    op.create_index(
        op.f("ix_queued_reports_id"), "queued_reports", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_queued_reports_template_id"),
        "queued_reports",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_queued_reports_status"), "queued_reports", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_queued_reports_requested_at"),
        "queued_reports",
        ["requested_at"],
        unique=False,
    )

    # Create distribution_schedules table
    op.create_table(
        "distribution_schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("recipients", sa.JSON(), nullable=False),
        sa.Column("frequency", sa.String(length=50), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("time", sa.String(length=5), nullable=False),
        sa.Column("format", sa.String(length=50), nullable=False, server_default="pdf"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_sent", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_scheduled", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["report_templates.id"],
            name=op.f("fk_distribution_schedules_template_id_report_templates"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_distribution_schedules")),
    )
    op.create_index(
        op.f("ix_distribution_schedules_id"),
        "distribution_schedules",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_distribution_schedules_template_id"),
        "distribution_schedules",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_distribution_schedules_is_active"),
        "distribution_schedules",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_distribution_schedules_next_scheduled"),
        "distribution_schedules",
        ["next_scheduled"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database schema - remove reporting tables."""
    # Drop distribution_schedules
    op.drop_index(
        op.f("ix_distribution_schedules_next_scheduled"),
        table_name="distribution_schedules",
    )
    op.drop_index(
        op.f("ix_distribution_schedules_is_active"), table_name="distribution_schedules"
    )
    op.drop_index(
        op.f("ix_distribution_schedules_template_id"),
        table_name="distribution_schedules",
    )
    op.drop_index(
        op.f("ix_distribution_schedules_id"), table_name="distribution_schedules"
    )
    op.drop_table("distribution_schedules")

    # Drop queued_reports
    op.drop_index(op.f("ix_queued_reports_requested_at"), table_name="queued_reports")
    op.drop_index(op.f("ix_queued_reports_status"), table_name="queued_reports")
    op.drop_index(op.f("ix_queued_reports_template_id"), table_name="queued_reports")
    op.drop_index(op.f("ix_queued_reports_id"), table_name="queued_reports")
    op.drop_table("queued_reports")

    # Drop report_templates
    op.drop_index(op.f("ix_report_templates_is_default"), table_name="report_templates")
    op.drop_index(op.f("ix_report_templates_category"), table_name="report_templates")
    op.drop_index(op.f("ix_report_templates_name"), table_name="report_templates")
    op.drop_index(op.f("ix_report_templates_id"), table_name="report_templates")
    op.drop_table("report_templates")
