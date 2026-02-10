"""Align DealStage enum to 6-stage model

Revision ID: a1b2c3d4e5f6
Revises: 8e6fdd43a452
Create Date: 2026-02-04 12:00:00.000000

Migrates from 8-stage (lead, initial_review, underwriting, due_diligence,
loi_submitted, under_contract, closed, dead) to 6-stage
(dead, initial_review, active_review, under_contract, closed, realized).
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "8e6fdd43a452"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Step 1: Drop default and convert column to text so we can freely update values
    op.execute("ALTER TABLE deals ALTER COLUMN stage DROP DEFAULT")
    op.execute("ALTER TABLE deals ALTER COLUMN stage TYPE text USING stage::text")

    # Step 2: Normalize to lowercase (DB may have uppercase values like 'DEAD')
    op.execute("UPDATE deals SET stage = LOWER(stage)")

    # Step 3: Migrate existing data to new stage names (now text, no enum constraint)
    op.execute("UPDATE deals SET stage = 'initial_review' WHERE stage = 'lead'")
    op.execute("UPDATE deals SET stage = 'active_review' WHERE stage = 'underwriting'")
    op.execute(
        "UPDATE deals SET stage = 'under_contract' WHERE stage IN ('due_diligence', 'loi_submitted')"
    )

    # Step 4: Drop old enum, create new one, cast column back
    op.execute("DROP TYPE dealstage")
    op.execute(
        "CREATE TYPE dealstage AS ENUM "
        "('dead', 'initial_review', 'active_review', 'under_contract', 'closed', 'realized')"
    )
    op.execute(
        "ALTER TABLE deals ALTER COLUMN stage TYPE dealstage USING stage::dealstage"
    )

    # Step 4: Set new default
    op.execute(
        "ALTER TABLE deals ALTER COLUMN stage SET DEFAULT 'initial_review'::dealstage"
    )


def downgrade() -> None:
    # Step 1: Drop default and convert to text
    op.execute("ALTER TABLE deals ALTER COLUMN stage DROP DEFAULT")
    op.execute("ALTER TABLE deals ALTER COLUMN stage TYPE text USING stage::text")

    # Step 2: Migrate data back to old stage names
    op.execute("UPDATE deals SET stage = 'lead' WHERE stage = 'initial_review'")
    op.execute("UPDATE deals SET stage = 'underwriting' WHERE stage = 'active_review'")
    # Note: 'realized' has no old equivalent, map to 'closed'
    op.execute("UPDATE deals SET stage = 'closed' WHERE stage = 'realized'")

    # Step 3: Drop new enum, recreate old one, cast back
    op.execute("DROP TYPE dealstage")
    op.execute(
        "CREATE TYPE dealstage AS ENUM "
        "('lead', 'initial_review', 'underwriting', 'due_diligence', "
        "'loi_submitted', 'under_contract', 'closed', 'dead')"
    )
    op.execute(
        "ALTER TABLE deals ALTER COLUMN stage TYPE dealstage USING stage::dealstage"
    )
    op.execute("ALTER TABLE deals ALTER COLUMN stage SET DEFAULT 'lead'::dealstage")
