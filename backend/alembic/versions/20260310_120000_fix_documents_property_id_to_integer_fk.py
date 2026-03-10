"""fix documents property_id to integer FK

Revision ID: a3b8f1c2d4e5
Revises: 7c415cc1b77a
Create Date: 2026-03-10 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b8f1c2d4e5"
down_revision: Union[str, None] = "7c415cc1b77a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing index on property_id
    op.drop_index("ix_documents_property_id", table_name="documents")

    # Change property_id from VARCHAR(50) to INTEGER
    # Step 1: Add a temporary integer column
    op.add_column("documents", sa.Column("property_id_new", sa.Integer(), nullable=True))

    # Step 2: Migrate data - cast valid integer strings, set NULL for non-integer values
    op.execute(
        """
        UPDATE documents
        SET property_id_new = CASE
            WHEN property_id ~ '^[0-9]+$' THEN property_id::INTEGER
            ELSE NULL
        END
        """
    )

    # Step 3: Drop the old column
    op.drop_column("documents", "property_id")

    # Step 4: Rename the new column
    op.alter_column("documents", "property_id_new", new_column_name="property_id")

    # Step 5: Add the foreign key constraint
    op.create_foreign_key(
        "fk_documents_property_id_properties",
        "documents",
        "properties",
        ["property_id"],
        ["id"],
    )

    # Step 6: Recreate the index
    op.create_index("ix_documents_property_id", "documents", ["property_id"])


def downgrade() -> None:
    # Drop FK constraint
    op.drop_constraint("fk_documents_property_id_properties", "documents", type_="foreignkey")

    # Drop the index
    op.drop_index("ix_documents_property_id", table_name="documents")

    # Change property_id back from INTEGER to VARCHAR(50)
    op.add_column("documents", sa.Column("property_id_old", sa.String(50), nullable=True))

    op.execute(
        """
        UPDATE documents
        SET property_id_old = property_id::VARCHAR
        WHERE property_id IS NOT NULL
        """
    )

    op.drop_column("documents", "property_id")
    op.alter_column("documents", "property_id_old", new_column_name="property_id")

    # Recreate the index
    op.create_index("ix_documents_property_id", "documents", ["property_id"])
