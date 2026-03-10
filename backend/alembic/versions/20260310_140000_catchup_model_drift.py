"""F-018 catch-up migration for model drift since 7c415cc1b77a

Revision ID: b4c5d6e7f8a9
Revises: a3b8f1c2d4e5
Create Date: 2026-03-10 14:00:00.000000

Captures all model changes that exist in code but were never formally
migrated. Safe to run on databases where some changes were already
applied manually (all operations use IF NOT EXISTS / try-except guards).

Changes covered:
  1. deals.version column (optimistic locking)
  2. audit_logs_admin table (AuditLog model)
  3. activity_logs soft-delete columns (is_deleted, deleted_at)
  4. CHECK constraints on deals, properties, transactions
  5. Missing indexes on deals (deal_type, property_id, assigned_user_id, priority)
  6. Missing indexes on transactions (category)
  7. Missing indexes on documents (uploaded_at)
  8. Composite index ix_deals_stage_stage_order
  9. Missing created_at / is_deleted indexes on core tables
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "a3b8f1c2d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers — idempotent DDL wrappers
# ---------------------------------------------------------------------------

def _column_exists(table: str, column: str) -> bool:
    """Check whether a column already exists (PostgreSQL)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.fetchone() is not None


def _table_exists(table: str) -> bool:
    """Check whether a table already exists (PostgreSQL)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :table AND table_schema = 'public'"
        ),
        {"table": table},
    )
    return result.fetchone() is not None


def _index_exists(index_name: str) -> bool:
    """Check whether an index already exists (PostgreSQL)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = :name"
        ),
        {"name": index_name},
    )
    return result.fetchone() is not None


def _constraint_exists(constraint_name: str) -> bool:
    """Check whether a constraint already exists (PostgreSQL)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = :name"
        ),
        {"name": constraint_name},
    )
    return result.fetchone() is not None


def _check_constraint_exists(constraint_name: str) -> bool:
    """Check whether a CHECK constraint already exists (PostgreSQL)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname = :name AND contype = 'c'"
        ),
        {"name": constraint_name},
    )
    return result.fetchone() is not None


def _add_column_if_not_exists(table: str, column: sa.Column) -> None:
    if not _column_exists(table, column.name):
        op.add_column(table, column)


def _create_index_if_not_exists(
    index_name: str, table: str, columns: list[str], unique: bool = False
) -> None:
    if not _index_exists(index_name):
        op.create_index(index_name, table, columns, unique=unique)


def _create_check_constraint_if_not_exists(
    name: str, table: str, condition: str
) -> None:
    if not _check_constraint_exists(name):
        op.create_check_constraint(name, table, condition)


# ---------------------------------------------------------------------------
# UPGRADE
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. deals.version — optimistic locking column
    # ------------------------------------------------------------------
    _add_column_if_not_exists(
        "deals",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    # ------------------------------------------------------------------
    # 2. audit_logs_admin table (AuditLog model)
    # ------------------------------------------------------------------
    if not _table_exists("audit_logs_admin"):
        op.create_table(
            "audit_logs_admin",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("user_email", sa.String(length=255), nullable=False),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("resource_type", sa.String(length=100), nullable=False),
            sa.Column("resource_id", sa.String(length=255), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.String(length=500), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs_admin")),
        )
        op.create_index(
            op.f("ix_audit_logs_admin_id"),
            "audit_logs_admin",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_audit_logs_admin_timestamp"),
            "audit_logs_admin",
            ["timestamp"],
            unique=False,
        )
        op.create_index(
            op.f("ix_audit_logs_admin_user_id"),
            "audit_logs_admin",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_audit_logs_admin_action"),
            "audit_logs_admin",
            ["action"],
            unique=False,
        )
        op.create_index(
            op.f("ix_audit_logs_admin_resource_type"),
            "audit_logs_admin",
            ["resource_type"],
            unique=False,
        )

    # ------------------------------------------------------------------
    # 3. activity_logs soft-delete columns (SoftDeleteMixin on ActivityLog)
    # ------------------------------------------------------------------
    _add_column_if_not_exists(
        "activity_logs",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    _add_column_if_not_exists(
        "activity_logs",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    _create_index_if_not_exists(
        "ix_activity_logs_is_deleted", "activity_logs", ["is_deleted"]
    )

    # ------------------------------------------------------------------
    # 4. CHECK constraints on deals
    # ------------------------------------------------------------------
    _create_check_constraint_if_not_exists(
        "ck_deals_asking_price_non_negative", "deals", "asking_price >= 0"
    )
    _create_check_constraint_if_not_exists(
        "ck_deals_offer_price_non_negative", "deals", "offer_price >= 0"
    )
    _create_check_constraint_if_not_exists(
        "ck_deals_final_price_non_negative", "deals", "final_price >= 0"
    )
    _create_check_constraint_if_not_exists(
        "ck_deals_projected_irr_range",
        "deals",
        "projected_irr >= -100 AND projected_irr <= 999",
    )
    _create_check_constraint_if_not_exists(
        "ck_deals_projected_coc_range", "deals", "projected_coc >= -100"
    )
    _create_check_constraint_if_not_exists(
        "ck_deals_equity_multiple_non_negative",
        "deals",
        "projected_equity_multiple >= 0",
    )
    _create_check_constraint_if_not_exists(
        "ck_deals_hold_period_positive", "deals", "hold_period_years > 0"
    )
    _create_check_constraint_if_not_exists(
        "ck_deals_deal_score_range",
        "deals",
        "deal_score >= 0 AND deal_score <= 100",
    )

    # ------------------------------------------------------------------
    # 5. CHECK constraints on properties
    # ------------------------------------------------------------------
    _create_check_constraint_if_not_exists(
        "ck_properties_purchase_price_non_negative",
        "properties",
        "purchase_price >= 0",
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_current_value_non_negative",
        "properties",
        "current_value >= 0",
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_total_units_positive", "properties", "total_units > 0"
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_total_sf_positive", "properties", "total_sf > 0"
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_stories_positive", "properties", "stories > 0"
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_year_built_range",
        "properties",
        "year_built >= 1800 AND year_built <= 2100",
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_year_renovated_range",
        "properties",
        "year_renovated >= 1800 AND year_renovated <= 2100",
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_cap_rate_range",
        "properties",
        "cap_rate >= 0 AND cap_rate <= 100",
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_occupancy_rate_range",
        "properties",
        "occupancy_rate >= 0 AND occupancy_rate <= 100",
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_avg_rent_per_unit_non_negative",
        "properties",
        "avg_rent_per_unit >= 0",
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_avg_rent_per_sf_non_negative",
        "properties",
        "avg_rent_per_sf >= 0",
    )
    _create_check_constraint_if_not_exists(
        "ck_properties_parking_spaces_non_negative",
        "properties",
        "parking_spaces >= 0",
    )

    # ------------------------------------------------------------------
    # 6. CHECK constraint on transactions
    # ------------------------------------------------------------------
    _create_check_constraint_if_not_exists(
        "ck_transactions_amount_non_negative", "transactions", "amount >= 0"
    )

    # ------------------------------------------------------------------
    # 7. Missing indexes on deals
    # ------------------------------------------------------------------
    _create_index_if_not_exists(
        "ix_deals_deal_type", "deals", ["deal_type"]
    )
    _create_index_if_not_exists(
        "ix_deals_property_id", "deals", ["property_id"]
    )
    _create_index_if_not_exists(
        "ix_deals_assigned_user_id", "deals", ["assigned_user_id"]
    )
    _create_index_if_not_exists(
        "ix_deals_priority", "deals", ["priority"]
    )
    # Composite index for Kanban board ordering
    _create_index_if_not_exists(
        "ix_deals_stage_stage_order", "deals", ["stage", "stage_order"]
    )
    # TimestampMixin index
    _create_index_if_not_exists(
        "ix_deals_created_at", "deals", ["created_at"]
    )
    # SoftDeleteMixin index
    _create_index_if_not_exists(
        "ix_deals_is_deleted", "deals", ["is_deleted"]
    )

    # ------------------------------------------------------------------
    # 8. Missing indexes on transactions
    # ------------------------------------------------------------------
    _create_index_if_not_exists(
        "ix_transactions_category", "transactions", ["category"]
    )
    # TimestampMixin index
    _create_index_if_not_exists(
        "ix_transactions_created_at", "transactions", ["created_at"]
    )
    # SoftDeleteMixin index
    _create_index_if_not_exists(
        "ix_transactions_is_deleted", "transactions", ["is_deleted"]
    )

    # ------------------------------------------------------------------
    # 9. Missing indexes on documents
    # ------------------------------------------------------------------
    _create_index_if_not_exists(
        "ix_documents_uploaded_at", "documents", ["uploaded_at"]
    )
    # TimestampMixin index
    _create_index_if_not_exists(
        "ix_documents_created_at", "documents", ["created_at"]
    )
    # SoftDeleteMixin index
    _create_index_if_not_exists(
        "ix_documents_is_deleted", "documents", ["is_deleted"]
    )

    # ------------------------------------------------------------------
    # 10. Missing indexes on properties
    # ------------------------------------------------------------------
    # TimestampMixin index
    _create_index_if_not_exists(
        "ix_properties_created_at", "properties", ["created_at"]
    )
    # SoftDeleteMixin index
    _create_index_if_not_exists(
        "ix_properties_is_deleted", "properties", ["is_deleted"]
    )

    # ------------------------------------------------------------------
    # 11. Missing indexes on users
    # ------------------------------------------------------------------
    # SoftDeleteMixin index
    _create_index_if_not_exists(
        "ix_users_is_deleted", "users", ["is_deleted"]
    )


# ---------------------------------------------------------------------------
# DOWNGRADE
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # 11. users indexes
    op.drop_index("ix_users_is_deleted", table_name="users", if_exists=True)

    # 10. properties indexes
    op.drop_index("ix_properties_is_deleted", table_name="properties", if_exists=True)
    op.drop_index("ix_properties_created_at", table_name="properties", if_exists=True)

    # 9. documents indexes
    op.drop_index("ix_documents_is_deleted", table_name="documents", if_exists=True)
    op.drop_index("ix_documents_created_at", table_name="documents", if_exists=True)
    op.drop_index("ix_documents_uploaded_at", table_name="documents", if_exists=True)

    # 8. transactions indexes
    op.drop_index(
        "ix_transactions_is_deleted", table_name="transactions", if_exists=True
    )
    op.drop_index(
        "ix_transactions_created_at", table_name="transactions", if_exists=True
    )
    op.drop_index(
        "ix_transactions_category", table_name="transactions", if_exists=True
    )

    # 7. deals indexes
    op.drop_index("ix_deals_is_deleted", table_name="deals", if_exists=True)
    op.drop_index("ix_deals_created_at", table_name="deals", if_exists=True)
    op.drop_index("ix_deals_stage_stage_order", table_name="deals", if_exists=True)
    op.drop_index("ix_deals_priority", table_name="deals", if_exists=True)
    op.drop_index("ix_deals_assigned_user_id", table_name="deals", if_exists=True)
    op.drop_index("ix_deals_property_id", table_name="deals", if_exists=True)
    op.drop_index("ix_deals_deal_type", table_name="deals", if_exists=True)

    # 6. transactions CHECK constraint
    op.drop_constraint(
        "ck_transactions_amount_non_negative", "transactions", type_="check"
    )

    # 5. properties CHECK constraints
    op.drop_constraint(
        "ck_properties_parking_spaces_non_negative", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_avg_rent_per_sf_non_negative", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_avg_rent_per_unit_non_negative", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_occupancy_rate_range", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_cap_rate_range", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_year_renovated_range", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_year_built_range", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_stories_positive", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_total_sf_positive", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_total_units_positive", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_current_value_non_negative", "properties", type_="check"
    )
    op.drop_constraint(
        "ck_properties_purchase_price_non_negative", "properties", type_="check"
    )

    # 4. deals CHECK constraints
    op.drop_constraint(
        "ck_deals_deal_score_range", "deals", type_="check"
    )
    op.drop_constraint(
        "ck_deals_hold_period_positive", "deals", type_="check"
    )
    op.drop_constraint(
        "ck_deals_equity_multiple_non_negative", "deals", type_="check"
    )
    op.drop_constraint(
        "ck_deals_projected_coc_range", "deals", type_="check"
    )
    op.drop_constraint(
        "ck_deals_projected_irr_range", "deals", type_="check"
    )
    op.drop_constraint(
        "ck_deals_final_price_non_negative", "deals", type_="check"
    )
    op.drop_constraint(
        "ck_deals_offer_price_non_negative", "deals", type_="check"
    )
    op.drop_constraint(
        "ck_deals_asking_price_non_negative", "deals", type_="check"
    )

    # 3. activity_logs soft-delete columns
    op.drop_index(
        "ix_activity_logs_is_deleted", table_name="activity_logs", if_exists=True
    )
    op.drop_column("activity_logs", "deleted_at")
    op.drop_column("activity_logs", "is_deleted")

    # 2. audit_logs_admin table
    op.drop_index(
        op.f("ix_audit_logs_admin_resource_type"),
        table_name="audit_logs_admin",
        if_exists=True,
    )
    op.drop_index(
        op.f("ix_audit_logs_admin_action"),
        table_name="audit_logs_admin",
        if_exists=True,
    )
    op.drop_index(
        op.f("ix_audit_logs_admin_user_id"),
        table_name="audit_logs_admin",
        if_exists=True,
    )
    op.drop_index(
        op.f("ix_audit_logs_admin_timestamp"),
        table_name="audit_logs_admin",
        if_exists=True,
    )
    op.drop_index(
        op.f("ix_audit_logs_admin_id"),
        table_name="audit_logs_admin",
        if_exists=True,
    )
    op.drop_table("audit_logs_admin")

    # 1. deals.version column
    op.drop_column("deals", "version")
