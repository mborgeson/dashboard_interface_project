"""
Reconciliation service for comparing SharePoint folder contents with database state.

Produces a report identifying:
- Files present in SharePoint but not tracked in the database
- Files tracked in the database but no longer present in SharePoint
- Files where extraction data is stale (file modified after last extraction)

Works gracefully when SharePoint is unavailable, reporting database state only.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.reconciliation import (
    ExtractionStaleness,
    FileDiscrepancy,
    ReconciliationHistoryItem,
    ReconciliationReport,
)

# In-memory store for reconciliation history (most recent first).
# In production this would be persisted to a database table, but for now
# we keep the last N reports in memory for simplicity.
_MAX_HISTORY = 50
_report_history: list[ReconciliationReport] = []


async def run_reconciliation(
    db: AsyncSession,
) -> ReconciliationReport:
    """Run a full reconciliation between SharePoint and database.

    Fetches the current file list from SharePoint (if available) and
    compares it against the ``MonitoredFile`` table in the database.

    Args:
        db: Async database session.

    Returns:
        A ``ReconciliationReport`` with all discrepancies.
    """
    start = time.monotonic()
    report_id = str(uuid.uuid4())[:12]

    # Get database state
    db_files = await _get_database_files(db)
    db_paths = {f["file_path"] for f in db_files}

    # Try to get SharePoint state
    sp_files: list[dict[str, Any]] = []
    sp_available = False
    error: str | None = None

    try:
        sp_files = await _get_sharepoint_files()
        sp_available = True
    except Exception as exc:
        error = f"SharePoint unavailable: {exc!s}"
        logger.warning("reconciliation_sharepoint_unavailable", error=error)

    sp_paths = {f["file_path"] for f in sp_files}
    sp_lookup = {f["file_path"]: f for f in sp_files}
    db_lookup = {f["file_path"]: f for f in db_files}

    # Files in SharePoint but not in DB
    sharepoint_only: list[FileDiscrepancy] = []
    for path in sp_paths - db_paths:
        sp_file = sp_lookup[path]
        sharepoint_only.append(
            FileDiscrepancy(
                file_path=path,
                file_name=sp_file["file_name"],
                deal_name=sp_file["deal_name"],
                location="sharepoint_only",
                last_modified=sp_file.get("modified_date"),
                size_bytes=sp_file.get("size"),
            )
        )

    # Files in DB but not in SharePoint
    database_only: list[FileDiscrepancy] = []
    if sp_available:
        for path in db_paths - sp_paths:
            db_file = db_lookup[path]
            database_only.append(
                FileDiscrepancy(
                    file_path=path,
                    file_name=db_file["file_name"],
                    deal_name=db_file["deal_name"],
                    location="database_only",
                    last_modified=db_file.get("modified_date"),
                    size_bytes=db_file.get("size_bytes"),
                )
            )

    # Stale extractions (file modified after last extraction)
    stale: list[ExtractionStaleness] = []
    for path in db_paths & sp_paths:
        db_file = db_lookup[path]
        sp_file = sp_lookup[path]
        last_extracted = db_file.get("last_extracted")
        file_modified = sp_file.get("modified_date")

        if file_modified and (last_extracted is None or file_modified > last_extracted):
            hours = None
            if last_extracted is not None and file_modified is not None:
                delta = file_modified - last_extracted
                hours = round(delta.total_seconds() / 3600, 1)
            stale.append(
                ExtractionStaleness(
                    file_path=path,
                    file_name=db_file["file_name"],
                    deal_name=db_file["deal_name"],
                    file_modified_date=file_modified,
                    last_extracted=last_extracted,
                    hours_stale=hours,
                )
            )

    files_in_sync = len(db_paths & sp_paths) - len(stale)
    duration = round(time.monotonic() - start, 2)

    report = ReconciliationReport(
        report_id=report_id,
        generated_at=datetime.now(UTC),
        duration_seconds=duration,
        total_sharepoint_files=len(sp_files),
        total_database_files=len(db_files),
        files_in_sync=max(files_in_sync, 0),
        sharepoint_only=sharepoint_only,
        database_only=database_only,
        stale_extractions=stale,
        sharepoint_available=sp_available,
        error=error,
    )

    # Store in history
    _report_history.insert(0, report)
    if len(_report_history) > _MAX_HISTORY:
        _report_history.pop()

    logger.info(
        "reconciliation_completed",
        report_id=report_id,
        sp_files=len(sp_files),
        db_files=len(db_files),
        sp_only=len(sharepoint_only),
        db_only=len(database_only),
        stale=len(stale),
        duration=duration,
    )

    return report


async def _get_database_files(db: AsyncSession) -> list[dict[str, Any]]:
    """Fetch all active monitored files from the database."""
    from sqlalchemy import select

    from app.models.file_monitor import MonitoredFile

    stmt = select(MonitoredFile).where(MonitoredFile.is_active.is_(True))
    result = await db.execute(stmt)
    files = result.scalars().all()

    return [
        {
            "file_path": f.file_path,
            "file_name": f.file_name,
            "deal_name": f.deal_name,
            "modified_date": f.modified_date,
            "size_bytes": f.size_bytes,
            "last_extracted": f.last_extracted,
        }
        for f in files
    ]


async def _get_sharepoint_files() -> list[dict[str, Any]]:
    """Fetch current file listing from SharePoint."""
    from app.core.config import settings
    from app.extraction.sharepoint import SharePointClient

    if not settings.sharepoint_configured:
        raise ConnectionError("SharePoint credentials not configured")

    async with SharePointClient() as client:
        discovery = await client.find_uw_models()
        return [
            {
                "file_path": f.path,
                "file_name": f.name,
                "deal_name": f.deal_name,
                "modified_date": f.modified_date,
                "size": f.size,
            }
            for f in discovery.files
        ]


def get_latest_report() -> ReconciliationReport | None:
    """Get the most recent reconciliation report, or None if none exist."""
    if _report_history:
        return _report_history[0]
    return None


def get_report_history(
    limit: int = 20,
    offset: int = 0,
) -> list[ReconciliationHistoryItem]:
    """Get abbreviated reconciliation report history.

    Args:
        limit: Maximum number of items to return.
        offset: Number of items to skip.

    Returns:
        List of ``ReconciliationHistoryItem`` summaries.
    """
    items: list[ReconciliationHistoryItem] = []
    for report in _report_history[offset : offset + limit]:
        items.append(
            ReconciliationHistoryItem(
                report_id=report.report_id,
                generated_at=report.generated_at,
                total_sharepoint_files=report.total_sharepoint_files,
                total_database_files=report.total_database_files,
                files_in_sync=report.files_in_sync,
                sharepoint_only_count=len(report.sharepoint_only),
                database_only_count=len(report.database_only),
                stale_extraction_count=len(report.stale_extractions),
                sharepoint_available=report.sharepoint_available,
                error=report.error,
            )
        )
    return items


def clear_history() -> None:
    """Clear all stored reconciliation reports (for testing)."""
    _report_history.clear()
