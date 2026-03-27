"""
Dead-letter tracking service for file extraction failures.

Provides helper functions to:
- Record extraction failures and auto-quarantine after threshold
- Record extraction successes and reset failure state
- Query quarantined files
- Retry quarantined files

A file is quarantined after QUARANTINE_THRESHOLD consecutive failures.
Quarantined files are excluded from auto-extraction and must be
manually retried via the dead-letter API.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_monitor import MonitoredFile

# Number of consecutive failures before a file is quarantined
QUARANTINE_THRESHOLD = 3


async def record_file_failure(
    db: AsyncSession,
    file_id: UUID,
    reason: str,
) -> MonitoredFile | None:
    """Record an extraction failure for a monitored file.

    Increments consecutive_failures and sets last_failure_at/reason.
    When consecutive_failures reaches QUARANTINE_THRESHOLD, the file
    is automatically quarantined.

    Args:
        db: Async database session.
        file_id: UUID of the MonitoredFile.
        reason: Human-readable failure reason.

    Returns:
        Updated MonitoredFile, or None if not found.
    """
    file = await db.get(MonitoredFile, file_id)
    if file is None:
        logger.warning("dead_letter_file_not_found", file_id=str(file_id))
        return None

    now = datetime.now(UTC)
    file.consecutive_failures += 1
    file.last_failure_at = now
    file.last_failure_reason = reason

    if file.consecutive_failures >= QUARANTINE_THRESHOLD and not file.quarantined:
        file.quarantined = True
        file.quarantined_at = now
        logger.warning(
            "file_quarantined",
            file_id=str(file_id),
            file_name=file.file_name,
            consecutive_failures=file.consecutive_failures,
            reason=reason,
        )
    else:
        logger.info(
            "file_failure_recorded",
            file_id=str(file_id),
            file_name=file.file_name,
            consecutive_failures=file.consecutive_failures,
            quarantined=file.quarantined,
        )

    await db.flush()
    return file


async def record_file_success(
    db: AsyncSession,
    file_id: UUID,
) -> MonitoredFile | None:
    """Record a successful extraction and reset failure state.

    Resets consecutive_failures to 0 and clears quarantine status
    if the file was previously quarantined.

    Args:
        db: Async database session.
        file_id: UUID of the MonitoredFile.

    Returns:
        Updated MonitoredFile, or None if not found.
    """
    file = await db.get(MonitoredFile, file_id)
    if file is None:
        logger.warning("dead_letter_file_not_found", file_id=str(file_id))
        return None

    was_quarantined = file.quarantined

    file.consecutive_failures = 0
    file.quarantined = False
    file.quarantined_at = None
    # Keep last_failure_at and last_failure_reason for audit trail

    if was_quarantined:
        logger.info(
            "file_unquarantined",
            file_id=str(file_id),
            file_name=file.file_name,
        )

    await db.flush()
    return file


async def get_quarantined_files(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[MonitoredFile], int]:
    """Get all quarantined files with pagination.

    Args:
        db: Async database session.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        Tuple of (list of quarantined MonitoredFiles, total count).
    """
    # Count total quarantined
    count_stmt = select(func.count(MonitoredFile.id)).where(
        MonitoredFile.quarantined.is_(True),
    )
    total = (await db.execute(count_stmt)).scalar_one()

    # Fetch paginated results
    stmt = (
        select(MonitoredFile)
        .where(MonitoredFile.quarantined.is_(True))
        .order_by(MonitoredFile.quarantined_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    files = list(result.scalars().all())

    return files, total


async def retry_quarantined_file(
    db: AsyncSession,
    file_id: UUID,
) -> MonitoredFile | None:
    """Reset quarantine status for a file so it can be re-extracted.

    Clears consecutive_failures, quarantined flag, and quarantined_at.
    Marks the file as pending extraction so the next extraction cycle
    picks it up.

    Args:
        db: Async database session.
        file_id: UUID of the MonitoredFile to retry.

    Returns:
        Updated MonitoredFile, or None if not found.
    """
    file = await db.get(MonitoredFile, file_id)
    if file is None:
        logger.warning("dead_letter_retry_file_not_found", file_id=str(file_id))
        return None

    file.consecutive_failures = 0
    file.quarantined = False
    file.quarantined_at = None
    file.extraction_pending = True

    logger.info(
        "dead_letter_retry",
        file_id=str(file_id),
        file_name=file.file_name,
        deal_name=file.deal_name,
    )

    await db.flush()
    return file
