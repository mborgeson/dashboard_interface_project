"""
Tests for SharePoint File Monitor Service.

Tests cover:
- FileChange dataclass functionality
- MonitorCheckResult properties
- SharePointFileMonitor.check_for_changes()
- SharePointFileMonitor._get_stored_state()
- SharePointFileMonitor._detect_changes()
- SharePointFileMonitor._update_stored_state()
- SharePointFileMonitor._log_changes()
- SharePointFileMonitor.get_pending_files()
- SharePointFileMonitor.mark_file_extracted()
- SharePointFileMonitor.get_recent_changes()

Run with: pytest tests/test_services/test_file_monitor.py -v
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_monitor import FileChangeLog, MonitoredFile
from app.services.extraction.file_monitor import (
    FileChange,
    MonitorCheckResult,
    SharePointFileMonitor,
    get_file_monitor,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def mock_sharepoint_client():
    """Create a mock SharePoint client."""
    client = AsyncMock()
    return client


@pytest_asyncio.fixture
async def file_monitor(db_session: AsyncSession, mock_sharepoint_client):
    """Create a file monitor instance with mocked SharePoint client."""
    monitor = SharePointFileMonitor(db_session, mock_sharepoint_client)
    return monitor


@pytest_asyncio.fixture
async def monitored_file(db_session: AsyncSession) -> MonitoredFile:
    """Create a test monitored file."""
    file = MonitoredFile(
        id=uuid4(),
        file_path="/sites/deals/DealA/UW Model vCurrent.xlsb",
        file_name="UW Model vCurrent.xlsb",
        deal_name="Deal A",
        size_bytes=1024000,
        modified_date=datetime.now(UTC) - timedelta(days=1),
        first_seen=datetime.now(UTC) - timedelta(days=7),
        last_checked=datetime.now(UTC) - timedelta(hours=2),
        is_active=True,
        extraction_pending=False,
        deal_stage="active_review",
    )
    db_session.add(file)
    await db_session.commit()
    await db_session.refresh(file)
    return file


@pytest_asyncio.fixture
async def pending_file(db_session: AsyncSession) -> MonitoredFile:
    """Create a file pending extraction."""
    file = MonitoredFile(
        id=uuid4(),
        file_path="/sites/deals/DealB/UW Model vCurrent.xlsb",
        file_name="UW Model vCurrent.xlsb",
        deal_name="Deal B",
        size_bytes=2048000,
        modified_date=datetime.now(UTC),
        first_seen=datetime.now(UTC) - timedelta(days=1),
        last_checked=datetime.now(UTC) - timedelta(hours=1),
        is_active=True,
        extraction_pending=True,
        deal_stage="under_contract",
    )
    db_session.add(file)
    await db_session.commit()
    await db_session.refresh(file)
    return file


@pytest_asyncio.fixture
async def file_change_log(db_session: AsyncSession) -> FileChangeLog:
    """Create a test file change log entry."""
    log = FileChangeLog(
        id=uuid4(),
        file_path="/sites/deals/DealC/UW Model v2.xlsb",
        file_name="UW Model v2.xlsb",
        deal_name="Deal C",
        change_type="modified",
        old_modified_date=datetime.now(UTC) - timedelta(days=2),
        new_modified_date=datetime.now(UTC),
        old_size_bytes=1000000,
        new_size_bytes=1500000,
        detected_at=datetime.now(UTC),
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    return log


# ============================================================================
# Test: FileChange Dataclass
# ============================================================================


class TestFileChange:
    """Tests for FileChange dataclass."""

    def test_create_added_change(self) -> None:
        """Creates a file added change."""
        change = FileChange(
            file_path="/sites/deals/DealA/UW Model.xlsb",
            file_name="UW Model.xlsb",
            change_type="added",
            deal_name="Deal A",
            old_modified_date=None,
            new_modified_date=datetime.now(UTC),
            new_size_bytes=1024000,
        )

        assert change.change_type == "added"
        assert change.old_modified_date is None
        assert change.new_modified_date is not None
        assert change.detected_at is not None

    def test_create_modified_change(self) -> None:
        """Creates a file modified change."""
        old_date = datetime.now(UTC) - timedelta(days=1)
        new_date = datetime.now(UTC)

        change = FileChange(
            file_path="/sites/deals/DealB/UW Model.xlsb",
            file_name="UW Model.xlsb",
            change_type="modified",
            deal_name="Deal B",
            old_modified_date=old_date,
            new_modified_date=new_date,
            old_size_bytes=1000000,
            new_size_bytes=1500000,
        )

        assert change.change_type == "modified"
        assert change.old_modified_date == old_date
        assert change.new_modified_date == new_date

    def test_create_deleted_change(self) -> None:
        """Creates a file deleted change."""
        change = FileChange(
            file_path="/sites/deals/DealC/UW Model.xlsb",
            file_name="UW Model.xlsb",
            change_type="deleted",
            deal_name="Deal C",
            old_modified_date=datetime.now(UTC) - timedelta(days=1),
            new_modified_date=None,
            old_size_bytes=1024000,
        )

        assert change.change_type == "deleted"
        assert change.new_modified_date is None

    def test_detected_at_auto_set(self) -> None:
        """Automatically sets detected_at timestamp."""
        before = datetime.now(UTC)

        change = FileChange(
            file_path="/path/file.xlsb",
            file_name="file.xlsb",
            change_type="added",
            deal_name="Deal",
            old_modified_date=None,
            new_modified_date=datetime.now(UTC),
        )

        after = datetime.now(UTC)
        assert change.detected_at >= before
        assert change.detected_at <= after

    def test_detected_at_custom(self) -> None:
        """Accepts custom detected_at timestamp."""
        custom_time = datetime(2024, 6, 15, 10, 30, 0)

        change = FileChange(
            file_path="/path/file.xlsb",
            file_name="file.xlsb",
            change_type="added",
            deal_name="Deal",
            old_modified_date=None,
            new_modified_date=datetime.now(UTC),
            detected_at=custom_time,
        )

        assert change.detected_at == custom_time


# ============================================================================
# Test: MonitorCheckResult
# ============================================================================


class TestMonitorCheckResult:
    """Tests for MonitorCheckResult dataclass."""

    def test_changes_detected_count(self) -> None:
        """Counts total changes detected."""
        changes = [
            FileChange(
                file_path="/path/a.xlsb",
                file_name="a.xlsb",
                change_type="added",
                deal_name="Deal A",
                old_modified_date=None,
                new_modified_date=datetime.now(UTC),
            ),
            FileChange(
                file_path="/path/b.xlsb",
                file_name="b.xlsb",
                change_type="modified",
                deal_name="Deal B",
                old_modified_date=datetime.now(UTC) - timedelta(days=1),
                new_modified_date=datetime.now(UTC),
            ),
        ]

        result = MonitorCheckResult(
            changes=changes,
            files_checked=10,
            folders_scanned=5,
            check_duration_seconds=1.5,
        )

        assert result.changes_detected == 2

    def test_files_added_count(self) -> None:
        """Counts files added."""
        changes = [
            FileChange(
                file_path="/path/a.xlsb",
                file_name="a.xlsb",
                change_type="added",
                deal_name="Deal A",
                old_modified_date=None,
                new_modified_date=datetime.now(UTC),
            ),
            FileChange(
                file_path="/path/b.xlsb",
                file_name="b.xlsb",
                change_type="added",
                deal_name="Deal B",
                old_modified_date=None,
                new_modified_date=datetime.now(UTC),
            ),
            FileChange(
                file_path="/path/c.xlsb",
                file_name="c.xlsb",
                change_type="modified",
                deal_name="Deal C",
                old_modified_date=datetime.now(UTC) - timedelta(days=1),
                new_modified_date=datetime.now(UTC),
            ),
        ]

        result = MonitorCheckResult(
            changes=changes,
            files_checked=15,
            folders_scanned=8,
            check_duration_seconds=2.0,
        )

        assert result.files_added == 2

    def test_files_modified_count(self) -> None:
        """Counts files modified."""
        changes = [
            FileChange(
                file_path="/path/a.xlsb",
                file_name="a.xlsb",
                change_type="modified",
                deal_name="Deal A",
                old_modified_date=datetime.now(UTC) - timedelta(days=1),
                new_modified_date=datetime.now(UTC),
            ),
        ]

        result = MonitorCheckResult(
            changes=changes,
            files_checked=10,
            folders_scanned=5,
            check_duration_seconds=1.0,
        )

        assert result.files_modified == 1

    def test_files_deleted_count(self) -> None:
        """Counts files deleted."""
        changes = [
            FileChange(
                file_path="/path/a.xlsb",
                file_name="a.xlsb",
                change_type="deleted",
                deal_name="Deal A",
                old_modified_date=datetime.now(UTC) - timedelta(days=1),
                new_modified_date=None,
            ),
            FileChange(
                file_path="/path/b.xlsb",
                file_name="b.xlsb",
                change_type="deleted",
                deal_name="Deal B",
                old_modified_date=datetime.now(UTC) - timedelta(days=2),
                new_modified_date=None,
            ),
        ]

        result = MonitorCheckResult(
            changes=changes,
            files_checked=5,
            folders_scanned=3,
            check_duration_seconds=0.5,
        )

        assert result.files_deleted == 2

    def test_empty_changes(self) -> None:
        """Handles empty changes list."""
        result = MonitorCheckResult(
            changes=[],
            files_checked=20,
            folders_scanned=10,
            check_duration_seconds=3.0,
        )

        assert result.changes_detected == 0
        assert result.files_added == 0
        assert result.files_modified == 0
        assert result.files_deleted == 0


# ============================================================================
# Test: SharePointFileMonitor._get_stored_state()
# ============================================================================


class TestGetStoredState:
    """Tests for SharePointFileMonitor._get_stored_state()."""

    @pytest.mark.asyncio
    async def test_get_stored_state_empty(
        self, file_monitor: SharePointFileMonitor
    ) -> None:
        """Returns empty dict when no files stored."""
        stored = await file_monitor._get_stored_state()

        assert stored == {}

    @pytest.mark.asyncio
    async def test_get_stored_state_with_files(
        self,
        file_monitor: SharePointFileMonitor,
        monitored_file: MonitoredFile,
    ) -> None:
        """Returns dict mapping file paths to MonitoredFile objects."""
        stored = await file_monitor._get_stored_state()

        assert monitored_file.file_path in stored
        assert stored[monitored_file.file_path].id == monitored_file.id

    @pytest.mark.asyncio
    async def test_get_stored_state_excludes_inactive(
        self,
        db_session: AsyncSession,
        file_monitor: SharePointFileMonitor,
    ) -> None:
        """Excludes inactive files from stored state."""
        # Create inactive file
        inactive = MonitoredFile(
            id=uuid4(),
            file_path="/sites/deals/Inactive/UW Model.xlsb",
            file_name="UW Model.xlsb",
            deal_name="Inactive Deal",
            size_bytes=1024000,
            modified_date=datetime.now(UTC),
            first_seen=datetime.now(UTC),
            last_checked=datetime.now(UTC),
            is_active=False,  # Inactive
            extraction_pending=False,
        )
        db_session.add(inactive)
        await db_session.commit()

        stored = await file_monitor._get_stored_state()

        assert inactive.file_path not in stored


# ============================================================================
# Test: SharePointFileMonitor._detect_changes()
# ============================================================================


class TestDetectChanges:
    """Tests for SharePointFileMonitor._detect_changes()."""

    @pytest.mark.asyncio
    async def test_detect_new_file(self, file_monitor: SharePointFileMonitor) -> None:
        """Detects new files not in stored state."""
        # Create mock SharePoint file
        current_file = MagicMock()
        current_file.path = "/sites/deals/NewDeal/UW Model.xlsb"
        current_file.name = "UW Model.xlsb"
        current_file.deal_name = "New Deal"
        current_file.modified_date = datetime.now(UTC)
        current_file.size = 1500000

        stored_files = {}  # Empty stored state

        changes = await file_monitor._detect_changes([current_file], stored_files)

        assert len(changes) == 1
        assert changes[0].change_type == "added"
        assert changes[0].file_path == current_file.path

    @pytest.mark.asyncio
    async def test_detect_deleted_file(
        self,
        file_monitor: SharePointFileMonitor,
        monitored_file: MonitoredFile,
    ) -> None:
        """Detects files deleted from SharePoint."""
        current_files = []  # No files in SharePoint
        stored_files = {monitored_file.file_path: monitored_file}

        changes = await file_monitor._detect_changes(current_files, stored_files)

        assert len(changes) == 1
        assert changes[0].change_type == "deleted"
        assert changes[0].file_path == monitored_file.file_path

    @pytest.mark.asyncio
    async def test_detect_modified_by_date(
        self,
        file_monitor: SharePointFileMonitor,
        monitored_file: MonitoredFile,
    ) -> None:
        """Detects files modified by date change."""
        # Create mock file with newer modified date
        current_file = MagicMock()
        current_file.path = monitored_file.file_path
        current_file.name = monitored_file.file_name
        current_file.deal_name = monitored_file.deal_name
        current_file.modified_date = datetime.now(UTC)  # Newer than stored
        current_file.size = monitored_file.size_bytes

        stored_files = {monitored_file.file_path: monitored_file}

        changes = await file_monitor._detect_changes([current_file], stored_files)

        assert len(changes) == 1
        assert changes[0].change_type == "modified"

    @pytest.mark.asyncio
    async def test_detect_modified_by_size(
        self,
        file_monitor: SharePointFileMonitor,
        monitored_file: MonitoredFile,
    ) -> None:
        """Detects files modified by size change."""
        # Create mock file with different size
        current_file = MagicMock()
        current_file.path = monitored_file.file_path
        current_file.name = monitored_file.file_name
        current_file.deal_name = monitored_file.deal_name
        current_file.modified_date = monitored_file.modified_date
        current_file.size = monitored_file.size_bytes + 500000  # Different size

        stored_files = {monitored_file.file_path: monitored_file}

        changes = await file_monitor._detect_changes([current_file], stored_files)

        assert len(changes) == 1
        assert changes[0].change_type == "modified"

    @pytest.mark.asyncio
    async def test_detect_no_changes(
        self,
        file_monitor: SharePointFileMonitor,
        monitored_file: MonitoredFile,
    ) -> None:
        """Detects no changes when file is unchanged."""
        # Create mock file matching stored state
        current_file = MagicMock()
        current_file.path = monitored_file.file_path
        current_file.name = monitored_file.file_name
        current_file.deal_name = monitored_file.deal_name
        current_file.modified_date = monitored_file.modified_date - timedelta(
            hours=1
        )  # Same or older
        current_file.size = monitored_file.size_bytes

        stored_files = {monitored_file.file_path: monitored_file}

        changes = await file_monitor._detect_changes([current_file], stored_files)

        assert len(changes) == 0


# ============================================================================
# Test: SharePointFileMonitor.get_pending_files()
# ============================================================================


class TestGetPendingFiles:
    """Tests for SharePointFileMonitor.get_pending_files()."""

    @pytest.mark.asyncio
    async def test_get_pending_empty(self, file_monitor: SharePointFileMonitor) -> None:
        """Returns empty list when no pending files."""
        pending = await file_monitor.get_pending_files()

        assert pending == []

    @pytest.mark.asyncio
    async def test_get_pending_with_files(
        self,
        file_monitor: SharePointFileMonitor,
        pending_file: MonitoredFile,
    ) -> None:
        """Returns list of files pending extraction."""
        pending = await file_monitor.get_pending_files()

        assert len(pending) == 1
        assert pending[0].id == pending_file.id
        assert pending[0].extraction_pending is True

    @pytest.mark.asyncio
    async def test_get_pending_excludes_non_pending(
        self,
        file_monitor: SharePointFileMonitor,
        monitored_file: MonitoredFile,
    ) -> None:
        """Excludes files not pending extraction."""
        pending = await file_monitor.get_pending_files()

        # monitored_file has extraction_pending=False
        assert all(f.id != monitored_file.id for f in pending)


# ============================================================================
# Test: SharePointFileMonitor.mark_file_extracted()
# ============================================================================


class TestMarkFileExtracted:
    """Tests for SharePointFileMonitor.mark_file_extracted()."""

    @pytest.mark.asyncio
    async def test_mark_file_extracted(
        self,
        db_session: AsyncSession,
        file_monitor: SharePointFileMonitor,
        pending_file: MonitoredFile,
    ) -> None:
        """Marks file as extracted."""
        extraction_run_id = uuid4()

        result = await file_monitor.mark_file_extracted(
            pending_file.file_path, extraction_run_id
        )

        assert result is True

        # Verify file is updated
        await db_session.refresh(pending_file)
        assert pending_file.extraction_pending is False
        assert pending_file.last_extracted is not None
        assert pending_file.extraction_run_id == extraction_run_id

    @pytest.mark.asyncio
    async def test_mark_file_extracted_not_found(
        self, file_monitor: SharePointFileMonitor
    ) -> None:
        """Returns False for non-existent file."""
        result = await file_monitor.mark_file_extracted(
            "/nonexistent/path.xlsb", uuid4()
        )

        assert result is False


# ============================================================================
# Test: SharePointFileMonitor.get_recent_changes()
# ============================================================================


class TestGetRecentChanges:
    """Tests for SharePointFileMonitor.get_recent_changes()."""

    @pytest.mark.asyncio
    async def test_get_recent_changes_empty(
        self, file_monitor: SharePointFileMonitor
    ) -> None:
        """Returns empty list when no changes logged."""
        changes = await file_monitor.get_recent_changes()

        assert changes == []

    @pytest.mark.asyncio
    async def test_get_recent_changes_with_logs(
        self,
        file_monitor: SharePointFileMonitor,
        file_change_log: FileChangeLog,
    ) -> None:
        """Returns recent file change logs."""
        changes = await file_monitor.get_recent_changes()

        assert len(changes) >= 1
        assert any(c.id == file_change_log.id for c in changes)

    @pytest.mark.asyncio
    async def test_get_recent_changes_pagination(
        self,
        db_session: AsyncSession,
        file_monitor: SharePointFileMonitor,
    ) -> None:
        """Respects limit and offset parameters."""
        # Create multiple change logs
        for i in range(5):
            log = FileChangeLog(
                id=uuid4(),
                file_path=f"/sites/deals/Deal{i}/UW Model.xlsb",
                file_name="UW Model.xlsb",
                deal_name=f"Deal {i}",
                change_type="added",
                new_modified_date=datetime.now(UTC),
                detected_at=datetime.now(UTC) - timedelta(hours=i),
            )
            db_session.add(log)
        await db_session.commit()

        # Get first 2
        first_batch = await file_monitor.get_recent_changes(limit=2)
        assert len(first_batch) == 2

        # Get next 2 with offset
        second_batch = await file_monitor.get_recent_changes(limit=2, offset=2)
        assert len(second_batch) == 2

        # Verify no overlap
        first_ids = {c.id for c in first_batch}
        second_ids = {c.id for c in second_batch}
        assert not first_ids.intersection(second_ids)


# ============================================================================
# Test: SharePointFileMonitor._log_changes()
# ============================================================================


class TestLogChanges:
    """Tests for SharePointFileMonitor._log_changes()."""

    @pytest.mark.asyncio
    async def test_log_changes_creates_entries(
        self,
        db_session: AsyncSession,
        file_monitor: SharePointFileMonitor,
    ) -> None:
        """Creates FileChangeLog entries for detected changes."""
        changes = [
            FileChange(
                file_path="/sites/deals/DealX/UW Model.xlsb",
                file_name="UW Model.xlsb",
                change_type="added",
                deal_name="Deal X",
                old_modified_date=None,
                new_modified_date=datetime.now(UTC),
                new_size_bytes=1024000,
            ),
        ]

        await file_monitor._log_changes(changes)

        # Verify log entry created
        logs = await file_monitor.get_recent_changes(limit=10)
        assert any(log.file_path == changes[0].file_path for log in logs)

    @pytest.mark.asyncio
    async def test_log_changes_empty_list(
        self, file_monitor: SharePointFileMonitor
    ) -> None:
        """Handles empty changes list gracefully."""
        await file_monitor._log_changes([])  # Should not raise


# ============================================================================
# Test: MonitoredFile.needs_extraction Property
# ============================================================================


class TestMonitoredFileNeedsExtraction:
    """Tests for MonitoredFile.needs_extraction property."""

    def test_needs_extraction_when_pending(self) -> None:
        """Returns True when extraction_pending is True."""
        file = MonitoredFile(
            id=uuid4(),
            file_path="/path/file.xlsb",
            file_name="file.xlsb",
            deal_name="Deal",
            size_bytes=1000,
            modified_date=datetime.now(UTC),
            first_seen=datetime.now(UTC),
            last_checked=datetime.now(UTC),
            is_active=True,
            extraction_pending=True,
        )

        assert file.needs_extraction is True

    def test_needs_extraction_never_extracted(self) -> None:
        """Returns True when file has never been extracted."""
        file = MonitoredFile(
            id=uuid4(),
            file_path="/path/file.xlsb",
            file_name="file.xlsb",
            deal_name="Deal",
            size_bytes=1000,
            modified_date=datetime.now(UTC),
            first_seen=datetime.now(UTC),
            last_checked=datetime.now(UTC),
            is_active=True,
            extraction_pending=False,
            last_extracted=None,  # Never extracted
        )

        assert file.needs_extraction is True

    def test_needs_extraction_modified_after_extraction(self) -> None:
        """Returns True when modified after last extraction."""
        last_extracted = datetime.now(UTC) - timedelta(days=1)
        modified_date = datetime.now(UTC)  # After last_extracted

        file = MonitoredFile(
            id=uuid4(),
            file_path="/path/file.xlsb",
            file_name="file.xlsb",
            deal_name="Deal",
            size_bytes=1000,
            modified_date=modified_date,
            first_seen=datetime.now(UTC) - timedelta(days=7),
            last_checked=datetime.now(UTC),
            is_active=True,
            extraction_pending=False,
            last_extracted=last_extracted,
        )

        assert file.needs_extraction is True

    def test_needs_extraction_up_to_date(self) -> None:
        """Returns False when file is up to date."""
        modified_date = datetime.now(UTC) - timedelta(days=2)
        last_extracted = datetime.now(UTC) - timedelta(days=1)  # After modified

        file = MonitoredFile(
            id=uuid4(),
            file_path="/path/file.xlsb",
            file_name="file.xlsb",
            deal_name="Deal",
            size_bytes=1000,
            modified_date=modified_date,
            first_seen=datetime.now(UTC) - timedelta(days=7),
            last_checked=datetime.now(UTC),
            is_active=True,
            extraction_pending=False,
            last_extracted=last_extracted,
        )

        assert file.needs_extraction is False

    def test_needs_extraction_inactive(self) -> None:
        """Returns False for inactive files."""
        file = MonitoredFile(
            id=uuid4(),
            file_path="/path/file.xlsb",
            file_name="file.xlsb",
            deal_name="Deal",
            size_bytes=1000,
            modified_date=datetime.now(UTC),
            first_seen=datetime.now(UTC),
            last_checked=datetime.now(UTC),
            is_active=False,  # Inactive
            extraction_pending=True,  # Would otherwise need extraction
        )

        assert file.needs_extraction is False


# ============================================================================
# Test: get_file_monitor() Function
# ============================================================================


class TestGetFileMonitor:
    """Tests for get_file_monitor() factory function."""

    @pytest.mark.asyncio
    async def test_get_file_monitor(self, db_session: AsyncSession) -> None:
        """Returns a SharePointFileMonitor instance."""
        monitor = await get_file_monitor(db_session)

        assert isinstance(monitor, SharePointFileMonitor)
        assert monitor.db == db_session


# ============================================================================
# Test: SharePointFileMonitor.check_for_changes() Integration
# ============================================================================


class TestCheckForChangesIntegration:
    """Integration tests for check_for_changes()."""

    @pytest.mark.asyncio
    async def test_check_for_changes_auth_error(
        self,
        file_monitor: SharePointFileMonitor,
        mock_sharepoint_client,
    ) -> None:
        """Raises SharePointAuthError on authentication failure."""
        from app.extraction.sharepoint import SharePointAuthError

        mock_sharepoint_client.find_uw_models = AsyncMock(
            side_effect=SharePointAuthError("Auth failed")
        )

        with pytest.raises(SharePointAuthError):
            await file_monitor.check_for_changes()

    @pytest.mark.asyncio
    async def test_check_for_changes_success(
        self,
        db_session: AsyncSession,
        file_monitor: SharePointFileMonitor,
        mock_sharepoint_client,
    ) -> None:
        """Successfully checks for changes."""
        # Create mock discovery result
        mock_file = MagicMock()
        mock_file.path = "/sites/deals/NewDeal/UW Model.xlsb"
        mock_file.name = "UW Model.xlsb"
        mock_file.deal_name = "New Deal"
        mock_file.deal_stage = "active_review"
        mock_file.modified_date = datetime.now(UTC)
        mock_file.size = 1500000

        mock_result = MagicMock()
        mock_result.files = [mock_file]
        mock_result.folders_scanned = 10
        mock_result.total_scanned = 50

        mock_sharepoint_client.find_uw_models = AsyncMock(return_value=mock_result)

        # Mock settings to disable auto-extraction
        with patch("app.services.extraction.file_monitor.settings") as mock_settings:
            mock_settings.AUTO_EXTRACT_ON_CHANGE = False

            result = await file_monitor.check_for_changes(auto_trigger_extraction=False)

        assert isinstance(result, MonitorCheckResult)
        assert result.files_checked == 50
        assert result.folders_scanned == 10
        # Should detect new file as added
        assert result.files_added == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
