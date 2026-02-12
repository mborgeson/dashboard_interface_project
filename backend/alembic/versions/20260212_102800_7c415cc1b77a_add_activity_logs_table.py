"""add activity_logs table

Revision ID: 7c415cc1b77a
Revises: d7d1ad81d3c0
Create Date: 2026-02-12 10:28:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7c415cc1b77a"
down_revision: Union[str, None] = "d7d1ad81d3c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create activity_logs table
    op.create_table(
        "activity_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("deal_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "created",
                "updated",
                "stage_changed",
                "document_added",
                "document_removed",
                "note_added",
                "assigned",
                "unassigned",
                "price_changed",
                "viewed",
                name="activityaction",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name=op.f("fk_activity_logs_deal_id_deals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_logs")),
    )
    # Create indexes
    op.create_index(op.f("ix_activity_logs_id"), "activity_logs", ["id"], unique=False)
    op.create_index(
        op.f("ix_activity_logs_deal_id"), "activity_logs", ["deal_id"], unique=False
    )
    op.create_index(
        op.f("ix_activity_logs_user_id"), "activity_logs", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_activity_logs_action"), "activity_logs", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_activity_logs_created_at"),
        "activity_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index(op.f("ix_activity_logs_created_at"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_action"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_user_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_deal_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_id"), table_name="activity_logs")
    op.drop_table("activity_logs")
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS activityaction")
