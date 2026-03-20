"""fix deal stages: only 8 in initial_review, rest to dead

Data-only migration. Corrects deal stage assignments:
- Keeps 5 specific deals in initial_review (the ones confirmed by the user
  that are in the DB; 3 others need extraction first)
- Moves all other initial_review deals to dead (they were bulk-imported
  with a hardcoded default and never triaged)
- Sets stage_updated_at on all updated deals

Revision ID: 152c800e6789
Revises: 739ad67dd4dd
Create Date: 2026-03-18 12:56:45.058207

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '152c800e6789'
down_revision: Union[str, None] = '739ad67dd4dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The 5 deals the user confirmed should stay in initial_review.
# Matched by deal ID (from DB audit). The other 3 the user named
# (Charleston Row Townhomes, Villas at Vesta View, Zon on 50 Townhomes)
# are not yet in the database and will be created correctly when extracted.
KEEP_INITIAL_REVIEW_IDS = [
    361,  # Broadstone 7th Street (Phoenix, AZ)
    387,  # Galleria Palms (Tempe, AZ)
    375,  # Hayden Park (Scottsdale, AZ)
    378,  # Park on Bell (Phoenix, AZ)
    391,  # Tides on East Cactus (Phoenix, AZ)
]


def upgrade() -> None:
    # Move all initial_review deals to dead, EXCEPT the 5 that should stay
    ids_list = ", ".join(str(i) for i in KEEP_INITIAL_REVIEW_IDS)
    op.execute(
        f"""
        UPDATE deals
        SET stage = 'dead',
            stage_updated_at = NOW(),
            updated_at = NOW()
        WHERE stage = 'initial_review'
          AND is_deleted = false
          AND id NOT IN ({ids_list})
        """
    )


def downgrade() -> None:
    # Revert: set all dead deals that were updated by this migration back
    # to initial_review. This is approximate — we can't perfectly distinguish
    # deals that were already dead before the migration.
    ids_list = ", ".join(str(i) for i in KEEP_INITIAL_REVIEW_IDS)
    op.execute(
        f"""
        UPDATE deals
        SET stage = 'initial_review',
            stage_updated_at = NULL,
            updated_at = NOW()
        WHERE stage = 'dead'
          AND is_deleted = false
          AND id NOT IN ({ids_list})
          AND stage_updated_at IS NOT NULL
        """
    )
