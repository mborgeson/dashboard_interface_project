"""
SharePoint File Monitor Service

Provides polling-based monitoring of SharePoint for file changes:
- Detects new UW model files added to deal folders
- Detects modifications to existing UW model files
- Detects deleted files
- Optionally triggers extraction when changes are detected
- Delta query support for incremental sync (when enabled)

Uses a database-backed state store to track file metadata between checks.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from loguru import logger
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.config import settings
from app.extraction.sharepoint import (
    SharePointAuthError,
    SharePointClient,
    SharePointFile,
)
from app.models.file_monitor import FileChangeLog, MonitoredFile

if TYPE_CHECKING:
    from app.extraction.sharepoint import DeltaChange


def _ensure_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (assume UTC if naive).

    SQLite strips timezone info, so datetimes read back from the test DB
    are naive even when stored as aware.  PostgreSQL with DateTime(timezone=True)
    always returns aware datetimes, so this is a no-op in production.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


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
            self.detected_at = datetime.now(UTC)


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
        self.logger = logger.bind(component="FileMonitor")

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

            # Trigger extraction BEFORE logging so we can record the run_id
            extraction_run_id = None
            extraction_triggered = False
            if (
                changes
                and auto_trigger_extraction
                and getattr(settings, "AUTO_EXTRACT_ON_CHANGE", True)
            ):
                extraction_run_id = await self._trigger_extraction(changes)
                extraction_triggered = extraction_run_id is not None

            # Log changes to audit trail (with extraction info)
            await self._log_changes(
                changes,
                extraction_triggered=extraction_triggered,
                extraction_run_id=extraction_run_id,
            )

            # Calculate duration
            duration = time.time() - start_time

            result = MonitorCheckResult(
                changes=changes,
                files_checked=discovery_result.total_scanned,
                folders_scanned=discovery_result.folders_scanned,
                check_duration_seconds=round(duration, 2),
                extraction_triggered=extraction_triggered,
                extraction_run_id=extraction_run_id,
            )

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

    async def check_for_changes_delta(
        self,
        auto_trigger_extraction: bool = True,
    ) -> MonitorCheckResult:
        """Check for file changes using Microsoft Graph delta queries.

        Uses delta tokens for incremental sync instead of full folder
        listing. Falls back to a full scan if the token has expired
        (HTTP 410 Gone) or if no token exists yet.

        Args:
            auto_trigger_extraction: Whether to automatically trigger
                extraction for changed files (if enabled in settings).

        Returns:
            MonitorCheckResult with detected changes and statistics.
        """
        import time

        from app.crud.delta_token import DeltaTokenCRUD

        start_time = time.time()
        changes: list[FileChange] = []

        self.logger.info("delta_check_started")

        try:
            drive_id = await self.client._get_drive_id()

            # Look up existing delta token
            existing_token = await DeltaTokenCRUD.get_by_drive_id(self.db, drive_id)
            token_value = existing_token.delta_token if existing_token else None

            try:
                delta_result = await self.client.get_delta_changes(
                    drive_id=drive_id,
                    delta_token=token_value,
                )
            except Exception as exc:
                # Check for HTTP 410 Gone — token expired
                status_code = getattr(exc, "status", None)
                if status_code == 410:
                    self.logger.warning(
                        "delta_token_expired",
                        drive_id=drive_id,
                    )
                    await DeltaTokenCRUD.clear_token(self.db, drive_id)
                    await self.db.commit()
                    # Fall back to full scan
                    return await self.check_for_changes(
                        auto_trigger_extraction=auto_trigger_extraction,
                    )
                raise

            # Convert delta changes to FileChange objects
            for delta_change in delta_result.changes:
                file_change = self._delta_change_to_file_change(delta_change)
                if file_change is not None:
                    changes.append(file_change)

            # Persist the new delta token
            if delta_result.new_delta_token:
                await DeltaTokenCRUD.upsert_token(
                    self.db, drive_id, delta_result.new_delta_token
                )
                await self.db.commit()

            # Trigger extraction BEFORE logging so we can record the run_id
            extraction_run_id = None
            extraction_triggered = False
            if (
                changes
                and auto_trigger_extraction
                and getattr(settings, "AUTO_EXTRACT_ON_CHANGE", True)
            ):
                extraction_run_id = await self._trigger_extraction(changes)
                extraction_triggered = extraction_run_id is not None

            # Log changes to audit trail
            await self._log_changes(
                changes,
                extraction_triggered=extraction_triggered,
                extraction_run_id=extraction_run_id,
            )

            duration = time.time() - start_time

            result = MonitorCheckResult(
                changes=changes,
                files_checked=len(delta_result.changes),
                folders_scanned=0,
                check_duration_seconds=round(duration, 2),
                extraction_triggered=extraction_triggered,
                extraction_run_id=extraction_run_id,
            )

            self.logger.info(
                "delta_check_completed",
                changes_detected=len(changes),
                is_full_sync=delta_result.is_full_sync,
                duration_seconds=result.check_duration_seconds,
                extraction_triggered=result.extraction_triggered,
            )

            return result

        except SharePointAuthError as e:
            self.logger.error("sharepoint_auth_failed", error=str(e))
            raise
        except Exception as e:
            self.logger.exception("delta_check_failed", error=str(e))
            raise

    @staticmethod
    def _delta_change_to_file_change(
        delta_change: DeltaChange,
    ) -> FileChange | None:
        """Convert a DeltaChange from the Graph API to a FileChange.

        Args:
            delta_change: A change item from the delta query.

        Returns:
            FileChange if the item is a file change we care about,
            None if it should be skipped (e.g., folder changes).
        """

        # Skip folder-level changes
        if delta_change.is_folder:
            return None

        # Map delta change types to FileChange types
        change_type_map: dict[str, Literal["added", "modified", "deleted"]] = {
            "created": "added",
            "modified": "modified",
            "deleted": "deleted",
        }

        change_type = change_type_map.get(delta_change.change_type)
        if change_type is None:
            return None

        # Infer deal name from path (e.g., "Deals/Stage/DealName/file.xlsb")
        parts = delta_change.path.split("/")
        deal_name = parts[2] if len(parts) > 2 else "Unknown"

        return FileChange(
            file_path=delta_change.path,
            file_name=delta_change.name,
            change_type=change_type,
            deal_name=deal_name,
            old_modified_date=None,
            new_modified_date=delta_change.modified_date,
            old_size_bytes=None,
            new_size_bytes=delta_change.size,
        )

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
                    _ensure_aware(file.modified_date)
                    > _ensure_aware(stored.modified_date)
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
        now = datetime.now(UTC)
        current_paths = {f.path for f in files}

        # Get existing records
        stored_files = await self._get_stored_state()

        # Track stage changes for deal sync
        stage_changes: list[tuple[str, str]] = []  # (deal_name, new_stage)

        # Update existing and create new records
        for file in files:
            if file.path in stored_files:
                # Update existing record
                existing = stored_files[file.path]
                # Detect folder move (deal_stage changed)
                if file.deal_stage and existing.deal_stage != file.deal_stage:
                    self.logger.info(
                        "deal_stage_changed",
                        deal=file.deal_name,
                        old_stage=existing.deal_stage,
                        new_stage=file.deal_stage,
                    )
                    stage_changes.append((file.deal_name, file.deal_stage))
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

        # Mark deleted files as inactive and track deals that lost files
        deleted_deal_names: set[str] = set()
        for path, stored in stored_files.items():
            if path not in current_paths:
                stored.is_active = False
                stored.last_checked = now
                deleted_deal_names.add(stored.deal_name)

        await self.db.commit()
        self.logger.debug("stored_state_updated", file_count=len(files))

        # Sync deal stages when files move between stage folders
        if stage_changes:
            await self._sync_deal_stages(stage_changes)

        # Deletion policy: mark deals DEAD when ALL their files are removed
        if deleted_deal_names:
            await self._apply_deletion_policy(deleted_deal_names, current_paths, files)

    async def _sync_deal_stages(
        self,
        stage_changes: list[tuple[str, str]],
    ) -> int:
        """
        Update Deal records when their files move between stage folders.

        When the file monitor detects that a file's folder path has changed
        (e.g., from "1) Initial UW and Review" to "0) Dead Deals"), this
        method updates the corresponding Deal's stage in the database.

        Creates a StageChangeLog audit entry for every transition via the
        central ``change_deal_stage()`` function.

        Emits WebSocket notifications for stage changes:
        - Individual ``stage_changed`` events for small batches
        - A single ``batch_stage_changed`` event when the number of
          changes exceeds ``STAGE_SYNC_BATCH_THRESHOLD``

        Args:
            stage_changes: List of (deal_name, new_stage_str) tuples

        Returns:
            Number of deals updated
        """
        from app.models.deal import Deal, DealStage
        from app.models.stage_change_log import StageChangeSource
        from app.services.stage_mapping import change_deal_stage

        # Parse and validate all stage changes first, filtering out invalid stages
        valid_changes: list[tuple[str, DealStage]] = []
        for deal_name, new_stage_str in stage_changes:
            try:
                target_stage = DealStage(new_stage_str)
                valid_changes.append((deal_name, target_stage))
            except ValueError:
                self.logger.warning(
                    "invalid_deal_stage_from_folder",
                    deal=deal_name,
                    stage=new_stage_str,
                )

        if not valid_changes:
            return 0

        # Batch-fetch all relevant deals in a single query (N+1 optimization)
        deal_names = list({name for name, _ in valid_changes})
        name_conditions = []
        for name in deal_names:
            name_conditions.append(func.lower(Deal.name) == func.lower(name))
            name_conditions.append(func.lower(Deal.name).like(func.lower(name) + " (%"))

        stmt = select(Deal).where(
            or_(*name_conditions),
            Deal.is_deleted.is_(False),
        )
        result = await self.db.execute(stmt)
        all_deals = list(result.scalars().all())

        # Build a lookup: lowercase deal name -> list of Deal objects
        deals_by_name: dict[str, list[Deal]] = {}
        for deal in all_deals:
            deal_name_lower = deal.name.lower()
            deals_by_name.setdefault(deal_name_lower, []).append(deal)
            # Also index by the base name (before parenthetical suffix)
            if " (" in deal.name:
                base_name = deal.name.split(" (")[0].lower()
                deals_by_name.setdefault(base_name, []).append(deal)

        # Apply stage changes using the pre-fetched deals
        updated = 0
        stage_change_details: list[dict[str, object]] = []

        for deal_name, target_stage in valid_changes:
            matching_deals = deals_by_name.get(deal_name.lower(), [])
            for deal in matching_deals:
                if deal.stage != target_stage:
                    old_stage = deal.stage
                    await change_deal_stage(
                        db=self.db,
                        deal=deal,
                        new_stage=target_stage,
                        source=StageChangeSource.SHAREPOINT_SYNC,
                        reason=f"File moved to folder for stage '{target_stage.value}'",
                    )
                    updated += 1
                    stage_change_details.append(
                        {
                            "deal_id": deal.id,
                            "deal_name": deal.name,
                            "old_stage": old_stage.value if old_stage else None,
                            "new_stage": target_stage.value,
                        }
                    )

        if updated:
            await self.db.commit()
            self.logger.info("deal_stages_synced", count=updated)

        # Fire-and-forget WebSocket notifications
        if stage_change_details:
            await self._emit_stage_change_notifications(stage_change_details)

        return updated

    async def _emit_stage_change_notifications(
        self,
        changes: list[dict[str, object]],
    ) -> None:
        """Emit WebSocket notifications for stage changes.

        Sends individual ``stage_changed`` events when the number of changes
        is at or below ``STAGE_SYNC_BATCH_THRESHOLD``.  For larger batches a
        single ``batch_stage_changed`` event is sent instead, preventing
        notification spam during bulk folder moves.

        Args:
            changes: List of dicts with deal_id, deal_name, old_stage,
                     new_stage for each changed deal.
        """
        from app.services.websocket_manager import get_connection_manager

        try:
            manager = get_connection_manager()
            batch_threshold = getattr(settings, "STAGE_SYNC_BATCH_THRESHOLD", 5)

            if len(changes) > batch_threshold:
                # Batch notification
                await manager.send_to_channel(
                    "deals",
                    {
                        "type": "batch_stage_changed",
                        "count": len(changes),
                        "deals": [
                            {
                                "deal_id": c["deal_id"],
                                "deal_name": c["deal_name"],
                                "old_stage": c["old_stage"],
                                "new_stage": c["new_stage"],
                            }
                            for c in changes
                        ],
                        "source": "sharepoint_sync",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
                self.logger.info(
                    "batch_stage_change_notification_sent",
                    count=len(changes),
                )
            else:
                # Individual notifications
                for change in changes:
                    await manager.notify_deal_update(
                        deal_id=int(str(change["deal_id"])),
                        action="stage_changed",
                        data={
                            "deal_name": change["deal_name"],
                            "old_stage": change["old_stage"],
                            "new_stage": change["new_stage"],
                            "source": "sharepoint_sync",
                        },
                    )
                self.logger.debug(
                    "individual_stage_change_notifications_sent",
                    count=len(changes),
                )
        except Exception:
            # Fire-and-forget — never block the sync on notification failures
            self.logger.opt(exception=True).warning(
                "stage_change_notification_failed",
                count=len(changes),
            )

    async def _apply_deletion_policy(
        self,
        deleted_deal_names: set[str],
        current_paths: set[str],
        current_files: list[SharePointFile],
    ) -> None:
        """Apply deletion policy when files are removed from SharePoint.

        When ALL files for a deal have been removed (none remain in
        ``current_files``), the deal is marked as DEAD — unless:
        - ``STAGE_SYNC_DELETE_POLICY`` is ``"ignore"``
        - ``STAGE_SYNC_PROTECT_CLOSED`` is True and the deal is CLOSED

        Args:
            deleted_deal_names: Set of deal names that had files removed.
            current_paths: Set of file paths still present in SharePoint.
            current_files: List of SharePointFile objects from discovery.
        """
        from app.models.deal import Deal, DealStage
        from app.models.stage_change_log import StageChangeSource
        from app.services.stage_mapping import change_deal_stage

        policy = getattr(settings, "STAGE_SYNC_DELETE_POLICY", "mark_dead")
        if policy != "mark_dead":
            return

        protect_closed = getattr(settings, "STAGE_SYNC_PROTECT_CLOSED", True)

        # Build set of deal names that still have at least one active file
        active_deal_names = {f.deal_name for f in current_files}

        # Deals with ALL files removed
        fully_removed = deleted_deal_names - active_deal_names

        if not fully_removed:
            return

        for deal_name in fully_removed:
            stmt = select(Deal).where(
                or_(
                    func.lower(Deal.name) == func.lower(deal_name),
                    func.lower(Deal.name).like(func.lower(deal_name) + " (%"),
                ),
                Deal.is_deleted.is_(False),
            )
            result = await self.db.execute(stmt)
            deals = list(result.scalars().all())

            for deal in deals:
                # Protect CLOSED deals
                if protect_closed and deal.stage == DealStage.CLOSED:
                    self.logger.info(
                        "deletion_policy_skipped_closed",
                        deal_id=deal.id,
                        deal_name=deal.name,
                    )
                    continue

                if deal.stage == DealStage.DEAD:
                    continue  # Already dead

                old_stage = deal.stage
                await change_deal_stage(
                    db=self.db,
                    deal=deal,
                    new_stage=DealStage.DEAD,
                    source=StageChangeSource.SHAREPOINT_SYNC,
                    reason="All files removed from SharePoint",
                )
                self.logger.info(
                    "deletion_policy_marked_dead",
                    deal_id=deal.id,
                    deal_name=deal.name,
                    old_stage=old_stage.value if old_stage else None,
                )

        await self.db.commit()

    async def _log_changes(
        self,
        changes: list[FileChange],
        extraction_triggered: bool = False,
        extraction_run_id: UUID | None = None,
    ) -> None:
        """
        Log detected changes to the audit trail.

        Args:
            changes: List of detected FileChange objects
            extraction_triggered: Whether extraction was triggered for these changes
            extraction_run_id: ID of the triggered extraction run (if any)
        """
        for change in changes:
            # Only set extraction fields on added/modified (not deleted)
            triggered = extraction_triggered and change.change_type in (
                "added",
                "modified",
            )
            run_id = extraction_run_id if triggered else None

            log_entry = FileChangeLog(
                file_path=change.file_path,
                file_name=change.file_name,
                deal_name=change.deal_name,
                change_type=change.change_type,
                old_modified_date=change.old_modified_date,
                new_modified_date=change.new_modified_date,
                old_size_bytes=change.old_size_bytes,
                new_size_bytes=change.new_size_bytes,
                detected_at=change.detected_at or datetime.now(UTC),
                extraction_triggered=triggered,
                extraction_run_id=run_id,
            )
            self.db.add(log_entry)

        if changes:
            await self.db.commit()
            self.logger.debug("changes_logged", count=len(changes))

    def _create_extraction_run_sync(self, files_discovered: int) -> UUID | None:
        """
        Create an extraction run using sync CRUD operations.

        Intended to be called via asyncio.to_thread() so blocking DB calls
        don't conflict with the running event loop.

        Args:
            files_discovered: Number of extractable files detected

        Returns:
            Extraction run UUID if created, None if a run is already active
        """
        from app.crud.extraction import ExtractionRunCRUD
        from app.db.session import SessionLocal

        sync_db = SessionLocal()
        try:
            running = ExtractionRunCRUD.get_running(sync_db)
            if running:
                self.logger.info(
                    "extraction_skipped_already_running",
                    running_run_id=str(running.id),
                )
                return None

            run = ExtractionRunCRUD.create(
                sync_db,
                trigger_type="file_monitor",
                files_discovered=files_discovered,
            )
            return run.id
        finally:
            sync_db.close()

    async def _trigger_extraction(
        self,
        changes: list[FileChange],
    ) -> UUID | None:
        """
        Trigger extraction for changed files.

        Only triggers for added or modified files (not deleted).
        Skips if an extraction is already running.

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
            # Delegate sync CRUD calls to a worker thread to avoid
            # "This event loop is already running" RuntimeError.
            run_id = await asyncio.to_thread(
                self._create_extraction_run_sync, len(extractable)
            )

            if run_id is None:
                return None

            # Mark files as pending extraction
            file_paths = [c.file_path for c in extractable]
            stmt = (
                update(MonitoredFile)
                .where(MonitoredFile.file_path.in_(file_paths))
                .values(extraction_pending=True)
            )
            await self.db.execute(stmt)
            await self.db.commit()

            self.logger.info(
                "extraction_triggered",
                run_id=str(run_id),
                file_count=len(file_paths),
            )

            return run_id

        except Exception as e:
            self.logger.error("extraction_trigger_failed", error=str(e))
            return None

    async def get_pending_files(self) -> list[MonitoredFile]:
        """
        Get files that are pending extraction.

        Excludes quarantined files — those must be retried explicitly
        via the dead-letter API.

        Returns:
            List of MonitoredFile objects with extraction_pending=True
        """
        stmt = select(MonitoredFile).where(
            MonitoredFile.extraction_pending.is_(True),
            MonitoredFile.is_active.is_(True),
            MonitoredFile.quarantined.is_(False),
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
                last_extracted=datetime.now(UTC),
                extraction_run_id=extraction_run_id,
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.rowcount > 0  # type: ignore[attr-defined]

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
