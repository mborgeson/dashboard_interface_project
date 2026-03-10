"""F-042 add CHECK constraints for VARCHAR enum columns

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-03-10 15:00:00.000000

Adds DB-level CHECK constraints on VARCHAR columns that use Python StrEnum
but lack database enforcement:

  1. construction_projects.pipeline_status — PipelineStatus enum
  2. construction_projects.primary_classification — ProjectClassification enum
  3. transactions.type — TransactionType enum
  4. documents.type — DocumentType enum
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers — idempotent DDL
# ---------------------------------------------------------------------------

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


def _create_check_constraint_if_not_exists(
    name: str, table: str, condition: str
) -> None:
    if not _check_constraint_exists(name):
        op.create_check_constraint(name, table, condition)


# ---------------------------------------------------------------------------
# Enum values (from model StrEnums)
# ---------------------------------------------------------------------------

# construction.PipelineStatus
PIPELINE_STATUS_VALUES = [
    "proposed",
    "final_planning",
    "permitted",
    "under_construction",
    "delivered",
]

# construction.ProjectClassification
PROJECT_CLASSIFICATION_VALUES = [
    "CONV_MR",
    "CONV_CONDO",
    "BTR",
    "LIHTC",
    "AGE_55",
    "WORKFORCE",
    "MIXED_USE",
    "CONVERSION",
]

# transaction.TransactionType
TRANSACTION_TYPE_VALUES = [
    "acquisition",
    "disposition",
    "capital_improvement",
    "refinance",
    "distribution",
]

# document.DocumentType
DOCUMENT_TYPE_VALUES = [
    "lease",
    "financial",
    "legal",
    "due_diligence",
    "photo",
    "other",
]


def _in_list_sql(column: str, values: list[str]) -> str:
    """Build a SQL IN expression for CHECK constraint."""
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


# ---------------------------------------------------------------------------
# Constraint definitions
# ---------------------------------------------------------------------------

CONSTRAINTS = [
    (
        "ck_construction_projects_pipeline_status_enum",
        "construction_projects",
        _in_list_sql("pipeline_status", PIPELINE_STATUS_VALUES),
    ),
    (
        "ck_construction_projects_primary_classification_enum",
        "construction_projects",
        _in_list_sql("primary_classification", PROJECT_CLASSIFICATION_VALUES),
    ),
    (
        "ck_transactions_type_enum",
        "transactions",
        _in_list_sql("type", TRANSACTION_TYPE_VALUES),
    ),
    (
        "ck_documents_type_enum",
        "documents",
        _in_list_sql("type", DOCUMENT_TYPE_VALUES),
    ),
]


# ---------------------------------------------------------------------------
# UPGRADE
# ---------------------------------------------------------------------------

def upgrade() -> None:
    for name, table, condition in CONSTRAINTS:
        _create_check_constraint_if_not_exists(name, table, condition)


# ---------------------------------------------------------------------------
# DOWNGRADE
# ---------------------------------------------------------------------------

def downgrade() -> None:
    for name, table, _condition in reversed(CONSTRAINTS):
        op.drop_constraint(name, table, type_="check")
