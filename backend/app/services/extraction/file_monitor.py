"""
SharePoint File Monitor Service

Provides polling-based monitoring of SharePoint for file changes:
- Detects new UW model files added to deal folders
- Detects modifications to existing UW model files
- Detects deleted files
- Optionally triggers extraction when changes are detected

Uses a database-backed state store to track file metadata between checks.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.extraction.sharepoint import (
    SharePointAuthError,
    SharePointClient,
    SharePointFile,
)
from app.models.file_monitor import FileChangeLog, MonitoredFile


@dataclass
class FileChange:
    """Represents a detected file change."""

    file_path: str
    file_name: str
    change_type: Literal["added", "modified", "deleted"]
    deal_name: str
    old_modified_date: datetime | None
    new_modified_date: datetime | None
    old_size_bytes: int | None = None
    new_size_bytes: int | None = None
    detected_at: datetime | None = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()


@dataclass
class MonitorCheckResult:
    """Result of a monitoring check."""

    changes: list[FileChange]
    files_checked: int
    folders_scanned: int
    check_duration_seconds: float
    extraction_triggered: bool = False
    extraction_run_id: UUID | None = None

    @property
    def changes_detected(self) -> int:
        return len(self.changes)

    @property
    def files_added(self) -> int:
        return sum(1 for c in self.changes if c.change_type == "added")

    @property
    def files_modified(self) -> int:
        return sum(1 for c in self.changes if c.change_type == "modified")

    @property
    def files_deleted(self) -> int:
        return sum(1 for c in self.changes if c.change_type == "deleted")


class SharePointFileMonitor:
    """
    Monitor SharePoint for file changes using polling.

    Compares current SharePoint state against stored state to detect:
    - New files (not in database)
    - Modified files (modified_date or size changed)
    - Deleted files (in database but not in SharePoint)
    """

    def __init__(
        self,
        db: AsyncSession,
        sharepoint_client: SharePointClient | None = None,
    ):
        """
        Initialize the file monitor.

        Args:
            db: Async database session
            sharepoint_client: Optional SharePointClient instance. If None,
                creates a new client using application settings.
        """
        self.db = db
        self.client = sharepoint_client or SharePointClient()
        self.logger = structlog.get_logger().bind(component="FileMonitor")

    async def check_for_changes(
        self,
        auto_trigger_extraction: bool = True,
    ) -> MonitorCheckResult:
        """
        Compare current SharePoint state against stored state.

        Performs a complete scan of SharePoint deal folders and compares
        against the database to detect changes.

        Args:
            auto_trigger_extraction: Whether to automatically trigger
                extraction for changed files (if enabled in settings)

        Returns:
            MonitorCheckResult with detected changes and statistics
        """
        import time

        start_time = time.time()
        changes: list[FileChange] = []

        self.logger.info("file_monitor_check_started")

        try:
            # Get current files from SharePoint
            discovery_result = await self.client.find_uw_models()
            current_files = discovery_result.files

            self.logger.info(
                "sharepoint_files_discovered",
                count=len(current_files),
                folders_scanned=discovery_result.folders_scanned,
            )

            # Get stored file states from database
            stored_files = await self._get_stored_state()

            self.logger.info(
                "stored_state_loaded",
                count=len(stored_files),
            )

            # Detect changes
            changes = await self._detect_changes(current_files, stored_files)

            self.logger.info(
                "changes_detected",
                total=len(changes),
                added=sum(1 for c in changes if c.change_type == "added"),
                modified=sum(1 for c in changes if c.change_type == "modified"),
                deleted=sum(1 for c in changes if c.change_type == "deleted"),
            )

            # Update stored state with current files
            await self._update_stored_state(current_files)

            # Log changes to audit trail
            await self._log_changes(changes)

            # Calculate duration
            duration = time.time() - start_time

            result = MonitorCheckResult(
                changes=changes,
                files_checked=discovery_result.total_scanned,
                folders_scanned=discovery_result.folders_scanned,
                check_duration_seconds=round(duration, 2),
            )

            # Trigger extraction if configured and changes detected
            if (
                changes
                and auto_trigger_extraction
                and getattr(settings, "AUTO_EXTRACT_ON_CHANGE", True)
            ):
                extraction_run_id = await self._trigger_extraction(changes)
                result.extraction_triggered = extraction_run_id is not None
                result.extraction_run_id = extraction_run_id

            self.logger.info(
                "file_monitor_check_completed",
                changes_detected=len(changes),
                duration_seconds=result.check_duration_seconds,
                extraction_triggered=result.extraction_triggered,
            )

            return result

        except SharePointAuthError as e:
            self.logger.error("sharepoint_auth_failed", error=str(e))
            raise
        except Exception as e:
            self.logger.exception("file_monitor_check_failed", error=str(e))
            raise

    async def _get_stored_state(self) -> dict[str, MonitoredFile]:
        """
        Get stored file states from database.

        Returns:
            Dictionary mapping file_path to MonitoredFile objects
        """
        stmt = select(MonitoredFile).where(MonitoredFile.is_active.is_(True))
        result = await self.db.execute(stmt)
        files = result.scalars().all()

        return {f.file_path: f for f in files}

    async def _detect_changes(
        self,
        current_files: list[SharePointFile],
        stored_files: dict[str, MonitoredFile],
    ) -> list[FileChange]:
        """
        Detect changes between current and stored state.

        Args:
            current_files: List of files currently in SharePoint
            stored_files: Dict of stored MonitoredFile records by path

        Returns:
            List of detected FileChange objects
        """
        changes: list[FileChange] = []
        current_paths = {f.path for f in current_files}
        stored_paths = set(stored_files.keys())

        # New files (in SharePoint but not in database)
        for file in current_files:
            if file.path not in stored_paths:
                changes.append(
                    FileChange(
                        file_path=file.path,
                        file_name=file.name,
                        change_type="added",
                        deal_name=file.deal_name,
                        old_modified_date=None,
                        new_modified_date=file.modified_date,
                        old_size_bytes=None,
                        new_size_bytes=file.size,
                    )
                )
                self.logger.debug(
                    "new_file_detected",
                    file=file.name,
                    deal=file.deal_name,
                )

        # Deleted files (in database but not in SharePoint)
        for path in stored_paths - current_paths:
            stored = stored_files[path]
            changes.append(
                FileChange(
                    file_path=path,
                    file_name=stored.file_name,
                    change_type="deleted",
                    deal_name=stored.deal_name,
                    old_modified_date=stored.modified_date,
                    new_modified_date=None,
                    old_size_bytes=stored.size_bytes,
                    new_size_bytes=None,
                )
            )
            self.logger.debug(
                "deleted_file_detected",
                file=stored.file_name,
                deal=stored.deal_name,
            )

        # Modified files (in both, but metadata changed)
        for file in current_files:
            if file.path in stored_paths:
                stored = stored_files[file.path]

                # Check if file has been modified
                # Compare modified_date and size
                if (
                    file.modified_date > stored.modified_date
                    or file.size != stored.size_bytes
                ):
                    changes.append(
                        FileChange(
                            file_path=file.path,
                            file_name=file.name,
                            change_type="modified",
                            deal_name=file.deal_name,
                            old_modified_date=stored.modified_date,
                            new_modified_date=file.modified_date,
                            old_size_bytes=stored.size_bytes,
                            new_size_bytes=file.size,
                        )
                    )
                    self.logger.debug(
                        "modified_file_detected",
                        file=file.name,
                        deal=file.deal_name,
                        old_date=stored.modified_date.isoformat(),
                        new_date=file.modified_date.isoformat(),
                    )

        return changes

    async def _update_stored_state(
        self,
        files: list[SharePointFile],
    ) -> None:
        """
        Update database with current file states.

        Creates new MonitoredFile records for new files and updates
        existing records with current metadata.

        Args:
            files: List of SharePointFile objects from discovery
        """
        now = datetime.utcnow()
        current_paths = {f.path for f in files}

        # Get existing records
        stored_files = await self._get_stored_state()

        # Update existing and create new records
        for file in files:
            if file.path in stored_files:
                # Update existing record
                existing = stored_files[file.path]
                existing.file_name = file.name
                existing.deal_name = file.deal_name
                existing.size_bytes = file.size
                existing.modified_date = file.modified_date
                existing.last_checked = now
                existing.deal_stage = file.deal_stage
                existing.is_active = True

                # Mark for extraction if modified
                if file.modified_date > (existing.last_extracted or datetime.min):
                    existing.extraction_pending = True
            else:
                # Create new record
                new_file = MonitoredFile(
                    file_path=file.path,
                    file_name=file.name,
                    deal_name=file.deal_name,
                    size_bytes=file.size,
                    modified_date=file.modified_date,
                    first_seen=now,
                    last_checked=now,
                    is_active=True,
                    extraction_pending=True,  # New files need extraction
                    deal_stage=file.deal_stage,
                )
                self.db.add(new_file)

        # Mark deleted files as inactive
        for path, stored in stored_files.items():
            if path not in current_paths:
                stored.is_active = False
                stored.last_checked = now

        await self.db.commit()
        self.logger.debug("stored_state_updated", file_count=len(files))

    async def _log_changes(self, changes: list[FileChange]) -> None:
        """
        Log detected changes to the audit trail.

        Args:
            changes: List of detected FileChange objects
        """
        for change in changes:
            log_entry = FileChangeLog(
                file_path=change.file_path,
                file_name=change.file_name,
                deal_name=change.deal_name,
                change_type=change.change_type,
                old_modified_date=change.old_modified_date,
                new_modified_date=change.new_modified_date,
                old_size_bytes=change.old_size_bytes,
                new_size_bytes=change.new_size_bytes,
                detected_at=change.detected_at or datetime.utcnow(),
            )
            self.db.add(log_entry)

        if changes:
            await self.db.commit()
            self.logger.debug("changes_logged", count=len(changes))

    async def _trigger_extraction(
        self,
        changes: list[FileChange],
    ) -> UUID | None:
        """
        Trigger extraction for changed files.

        Only triggers for added or modified files (not deleted).

        Args:
            changes: List of detected changes

        Returns:
            Extraction run ID if triggered, None otherwise
        """
        # Filter to added/modified files only
        extractable = [c for c in changes if c.change_type in ("added", "modified")]

        if not extractable:
            return None

        self.logger.info(
            "triggering_extraction",
            file_count=len(extractable),
        )

        try:
            # Import here to avoid circular imports
            from app.crud.extraction import ExtractionRunCRUD  # noqa: F401

            # Note: Actual extraction triggering would integrate with
            # the extraction API/scheduler here

            # For now, we mark files as pending extraction
            # The scheduled extraction will pick them up
            file_paths = [c.file_path for c in extractable]
            stmt = (
                update(MonitoredFile)
                .where(MonitoredFile.file_path.in_(file_paths))
                .values(extraction_pending=True)
            )
            await self.db.execute(stmt)
            await self.db.commit()

            self.logger.info(
                "files_marked_for_extraction",
                count=len(file_paths),
            )

            # Note: Full integration would call the extraction service here
            # For now, return None to indicate extraction is pending
            return None

        except Exception as e:
            self.logger.error("extraction_trigger_failed", error=str(e))
            return None

    async def get_pending_files(self) -> list[MonitoredFile]:
        """
        Get files that are pending extraction.

        Returns:
            List of MonitoredFile objects with extraction_pending=True
        """
        stmt = select(MonitoredFile).where(
            MonitoredFile.extraction_pending.is_(True),
            MonitoredFile.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_file_extracted(
        self,
        file_path: str,
        extraction_run_id: UUID,
    ) -> bool:
        """
        Mark a file as having been extracted.

        Args:
            file_path: Path to the extracted file
            extraction_run_id: ID of the extraction run

        Returns:
            True if file was found and updated
        """
        stmt = (
            update(MonitoredFile)
            .where(MonitoredFile.file_path == file_path)
            .values(
                extraction_pending=False,
                last_extracted=datetime.utcnow(),
                extraction_run_id=extraction_run_id,
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.rowcount > 0

    async def get_recent_changes(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FileChangeLog]:
        """
        Get recent file change log entries.

        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip

        Returns:
            List of FileChangeLog entries, newest first
        """
        stmt = (
            select(FileChangeLog)
            .order_by(FileChangeLog.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


# Singleton instance and getter
_file_monitor: SharePointFileMonitor | None = None


async def get_file_monitor(db: AsyncSession) -> SharePointFileMonitor:
    """Get file monitor instance with provided database session."""
    return SharePointFileMonitor(db)
