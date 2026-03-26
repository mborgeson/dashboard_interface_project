"""
Unified stage mapping — single source of truth for folder -> deal stage resolution.

All folder-to-stage logic lives here. Other modules must import from this module
instead of defining their own mappings.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.deal import DealStage

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.stage_change_log import StageChangeLog, StageChangeSource

# ── Canonical folder -> DealStage mapping ──────────────────────────────────
# Keys are the exact SharePoint folder names (numbered prefix included).
FOLDER_TO_STAGE: dict[str, DealStage] = {
    "0) Dead Deals": DealStage.DEAD,
    "1) Initial UW and Review": DealStage.INITIAL_REVIEW,
    "2) Active UW and Review": DealStage.ACTIVE_REVIEW,
    "3) Deals Under Contract": DealStage.UNDER_CONTRACT,
    "4) Closed Deals": DealStage.CLOSED,
    "5) Realized Deals": DealStage.REALIZED,
}

# Reverse mapping: DealStage -> canonical folder name
STAGE_TO_FOLDER: dict[DealStage, str] = {v: k for k, v in FOLDER_TO_STAGE.items()}

# Flat string mapping for backward compatibility (folder name -> stage value string)
STAGE_FOLDER_MAP: dict[str, str] = {k: v.value for k, v in FOLDER_TO_STAGE.items()}


def resolve_stage(folder_path: str) -> DealStage | None:
    """Resolve a folder path to a DealStage using path-component matching.

    Splits the path on '/' and checks each component against the canonical
    folder names. This avoids substring-match ambiguity (e.g., a deal named
    "Dead Creek Apartments" won't match the "dead" stage).

    Args:
        folder_path: Full or partial folder path, e.g.
            "Deals/1) Initial UW and Review/The Clubhouse"

    Returns:
        The matching DealStage, or None if no canonical folder is found.
    """
    # Normalise path separators (Windows backslash -> forward slash)
    normalised = folder_path.replace("\\", "/")
    components = [c.strip() for c in normalised.split("/") if c.strip()]

    for component in components:
        # Exact match against canonical folder names (case-insensitive)
        for folder_name, stage in FOLDER_TO_STAGE.items():
            if component.lower() == folder_name.lower():
                return stage

    return None


async def change_deal_stage(
    db: AsyncSession,
    deal: Deal,
    new_stage: DealStage,
    source: StageChangeSource,
    changed_by_user_id: int | None = None,
    reason: str | None = None,
) -> StageChangeLog:
    """Record a deal stage transition and update the deal.

    Sets ``deal.stage``, ``deal.stage_updated_at``, and creates a
    ``StageChangeLog`` audit record.  The caller is responsible for
    committing the transaction.

    Args:
        db: Async database session (caller manages commit).
        deal: The Deal ORM instance to update.
        new_stage: Target DealStage.
        source: How the change was triggered (e.g. SHAREPOINT_SYNC).
        changed_by_user_id: FK to users.id, nullable for automated sources.
        reason: Optional human-readable reason for the change.

    Returns:
        The newly created StageChangeLog entry.
    """
    from app.models.stage_change_log import StageChangeLog

    old_stage = deal.stage

    # Update the deal
    deal.stage = new_stage
    deal.stage_updated_at = datetime.now(UTC)

    # Create audit log entry
    log_entry = StageChangeLog(
        deal_id=deal.id,
        old_stage=old_stage.value if old_stage else None,
        new_stage=new_stage.value,
        source=source,
        changed_by_user_id=changed_by_user_id,
        reason=reason,
        created_at=datetime.now(UTC),
    )
    db.add(log_entry)
    await db.flush()

    logger.info(
        "deal_stage_changed",
        deal_id=deal.id,
        old_stage=old_stage.value if old_stage else None,
        new_stage=new_stage.value,
        source=source.value if hasattr(source, "value") else str(source),
        changed_by_user_id=changed_by_user_id,
    )

    return log_entry


def change_deal_stage_sync(
    db: Session,
    deal: Deal,
    new_stage: DealStage,
    source: StageChangeSource,
    changed_by_user_id: int | None = None,
    reason: str | None = None,
) -> StageChangeLog:
    """Synchronous variant of ``change_deal_stage`` for non-async callers.

    Same behaviour as the async version but uses a synchronous Session.
    The caller is responsible for committing the transaction.
    """
    from app.models.stage_change_log import StageChangeLog

    old_stage = deal.stage

    deal.stage = new_stage
    deal.stage_updated_at = datetime.now(UTC)

    log_entry = StageChangeLog(
        deal_id=deal.id,
        old_stage=old_stage.value if old_stage else None,
        new_stage=new_stage.value,
        source=source,
        changed_by_user_id=changed_by_user_id,
        reason=reason,
        created_at=datetime.now(UTC),
    )
    db.add(log_entry)
    db.flush()

    logger.info(
        "deal_stage_changed",
        deal_id=deal.id,
        old_stage=old_stage.value if old_stage else None,
        new_stage=new_stage.value,
        source=source.value if hasattr(source, "value") else str(source),
        changed_by_user_id=changed_by_user_id,
    )

    return log_entry
