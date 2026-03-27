"""
Tests for dead-letter (quarantine) tracking system.

Tests cover:
- Quarantine lifecycle: 1st failure, 2nd failure, 3rd failure -> quarantined
- Reset on successful extraction after failures
- Quarantined files excluded from auto-extraction queries
- GET /extraction/dead-letter endpoint (auth, pagination)
- POST /extraction/dead-letter/{id}/retry endpoint (auth, resets quarantine)
- Retry on non-quarantined file (resets failure count)
- Failure reason stored correctly
- MonitoredFile.needs_extraction excludes quarantined files

Run with: pytest tests/test_dead_letter.py -v
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_monitor import MonitoredFile
from app.services.extraction.dead_letter import (
    QUARANTINE_THRESHOLD,
    get_quarantined_files,
    record_file_failure,
    record_file_success,
    retry_quarantined_file,
)


# ============================================================================
# Test Fixtures
# ============================================================================


def _make_monitored_file(
    *,
    file_name: str = "UW Model vCurrent.xlsb",
    deal_name: str = "Test Deal",
    file_path: str | None = None,
    is_active: bool = True,
    extraction_pending: bool = False,
    consecutive_failures: int = 0,
    quarantined: bool = False,
    quarantined_at: datetime | None = None,
    last_failure_at: datetime | None = None,
    last_failure_reason: str | None = None,
) -> MonitoredFile:
    """Create a MonitoredFile instance for testing."""
    now = datetime.now(UTC)
    return MonitoredFile(
        id=uuid4(),
        file_path=file_path or f"/sites/deals/{deal_name}/{file_name}",
        file_name=file_name,
        deal_name=deal_name,
        size_bytes=1024000,
        modified_date=now - timedelta(hours=2),
        first_seen=now - timedelta(days=7),
        last_checked=now - timedelta(hours=1),
        is_active=is_active,
        extraction_pending=extraction_pending,
        deal_stage="active_review",
        consecutive_failures=consecutive_failures,
        quarantined=quarantined,
        quarantined_at=quarantined_at,
        last_failure_at=last_failure_at,
        last_failure_reason=last_failure_reason,
        # Explicit timestamps for SQLite compatibility
        created_at=now,
        updated_at=now,
    )


@pytest_asyncio.fixture
async def healthy_file(db_session: AsyncSession) -> MonitoredFile:
    """A file with no failures."""
    file = _make_monitored_file(deal_name="Healthy Deal")
    db_session.add(file)
    await db_session.commit()
    await db_session.refresh(file)
    return file


@pytest_asyncio.fixture
async def failing_file(db_session: AsyncSession) -> MonitoredFile:
    """A file with 2 consecutive failures (not yet quarantined)."""
    file = _make_monitored_file(
        deal_name="Failing Deal",
        consecutive_failures=2,
        last_failure_at=datetime.now(UTC) - timedelta(hours=1),
        last_failure_reason="Corrupt XLSB format",
    )
    db_session.add(file)
    await db_session.commit()
    await db_session.refresh(file)
    return file


@pytest_asyncio.fixture
async def quarantined_file(db_session: AsyncSession) -> MonitoredFile:
    """A file that has been quarantined."""
    now = datetime.now(UTC)
    file = _make_monitored_file(
        deal_name="Quarantined Deal",
        consecutive_failures=3,
        quarantined=True,
        quarantined_at=now - timedelta(hours=6),
        last_failure_at=now - timedelta(hours=6),
        last_failure_reason="Sheet 'Assumptions (Summary)' not found",
        extraction_pending=True,
    )
    db_session.add(file)
    await db_session.commit()
    await db_session.refresh(file)
    return file


@pytest_asyncio.fixture
async def multiple_quarantined(db_session: AsyncSession) -> list[MonitoredFile]:
    """Create multiple quarantined files for pagination tests."""
    files = []
    now = datetime.now(UTC)
    for i in range(5):
        file = _make_monitored_file(
            deal_name=f"Quarantined Deal {i}",
            file_path=f"/sites/deals/Deal{i}/UW Model vCurrent.xlsb",
            consecutive_failures=3 + i,
            quarantined=True,
            quarantined_at=now - timedelta(hours=i),
            last_failure_at=now - timedelta(hours=i),
            last_failure_reason=f"Error #{i}",
        )
        db_session.add(file)
        files.append(file)
    await db_session.commit()
    for f in files:
        await db_session.refresh(f)
    return files


# ============================================================================
# Service Layer Tests: Quarantine Lifecycle
# ============================================================================


class TestRecordFileFailure:
    """Tests for record_file_failure()."""

    async def test_first_failure_increments_count(
        self, db_session: AsyncSession, healthy_file: MonitoredFile
    ):
        """First failure sets consecutive_failures to 1."""
        result = await record_file_failure(
            db_session, healthy_file.id, "Connection timeout"
        )
        assert result is not None
        assert result.consecutive_failures == 1
        assert result.last_failure_reason == "Connection timeout"
        assert result.last_failure_at is not None
        assert result.quarantined is False

    async def test_second_failure_increments_count(
        self, db_session: AsyncSession, failing_file: MonitoredFile
    ):
        """Second consecutive failure goes from 2 to 3 and triggers quarantine."""
        # failing_file starts at 2 consecutive failures
        assert failing_file.consecutive_failures == 2

        result = await record_file_failure(
            db_session, failing_file.id, "Sheet not found"
        )
        assert result is not None
        assert result.consecutive_failures == 3
        assert result.last_failure_reason == "Sheet not found"
        assert result.quarantined is True
        assert result.quarantined_at is not None

    async def test_failure_on_already_quarantined_increments_but_no_double_quarantine(
        self, db_session: AsyncSession, quarantined_file: MonitoredFile
    ):
        """Failure on already-quarantined file increments count but keeps quarantine."""
        original_quarantined_at = quarantined_file.quarantined_at
        result = await record_file_failure(
            db_session, quarantined_file.id, "Still broken"
        )
        assert result is not None
        assert result.consecutive_failures == 4
        assert result.quarantined is True
        # quarantined_at should NOT be updated (already quarantined)
        assert result.quarantined_at == original_quarantined_at

    async def test_failure_stores_reason_correctly(
        self, db_session: AsyncSession, healthy_file: MonitoredFile
    ):
        """Failure reason is stored and retrievable."""
        long_reason = "openpyxl.utils.exceptions.InvalidFileException: Cannot open corrupt file '/path/to/file.xlsb'"
        result = await record_file_failure(db_session, healthy_file.id, long_reason)
        assert result is not None
        assert result.last_failure_reason == long_reason

    async def test_failure_nonexistent_file_returns_none(
        self, db_session: AsyncSession
    ):
        """Recording failure for a nonexistent file returns None."""
        result = await record_file_failure(
            db_session, uuid4(), "Some error"
        )
        assert result is None

    async def test_quarantine_threshold_is_three(self):
        """Verify the quarantine threshold constant is 3."""
        assert QUARANTINE_THRESHOLD == 3

    async def test_full_lifecycle_to_quarantine(
        self, db_session: AsyncSession, healthy_file: MonitoredFile
    ):
        """Walk through the full lifecycle: 0 -> 1 -> 2 -> 3 (quarantined)."""
        # Failure 1
        result = await record_file_failure(
            db_session, healthy_file.id, "Error 1"
        )
        assert result is not None
        assert result.consecutive_failures == 1
        assert result.quarantined is False

        # Failure 2
        result = await record_file_failure(
            db_session, healthy_file.id, "Error 2"
        )
        assert result is not None
        assert result.consecutive_failures == 2
        assert result.quarantined is False

        # Failure 3 -> quarantined
        result = await record_file_failure(
            db_session, healthy_file.id, "Error 3"
        )
        assert result is not None
        assert result.consecutive_failures == 3
        assert result.quarantined is True
        assert result.quarantined_at is not None
        assert result.last_failure_reason == "Error 3"


class TestRecordFileSuccess:
    """Tests for record_file_success()."""

    async def test_success_resets_failure_count(
        self, db_session: AsyncSession, failing_file: MonitoredFile
    ):
        """Success resets consecutive_failures to 0."""
        assert failing_file.consecutive_failures == 2
        result = await record_file_success(db_session, failing_file.id)
        assert result is not None
        assert result.consecutive_failures == 0
        assert result.quarantined is False

    async def test_success_unquarantines_file(
        self, db_session: AsyncSession, quarantined_file: MonitoredFile
    ):
        """Success on a quarantined file clears quarantine."""
        assert quarantined_file.quarantined is True
        result = await record_file_success(db_session, quarantined_file.id)
        assert result is not None
        assert result.consecutive_failures == 0
        assert result.quarantined is False
        assert result.quarantined_at is None

    async def test_success_preserves_failure_audit_trail(
        self, db_session: AsyncSession, failing_file: MonitoredFile
    ):
        """Success keeps last_failure_at/reason for audit trail."""
        original_failure_at = failing_file.last_failure_at
        original_reason = failing_file.last_failure_reason
        result = await record_file_success(db_session, failing_file.id)
        assert result is not None
        assert result.last_failure_at == original_failure_at
        assert result.last_failure_reason == original_reason

    async def test_success_on_healthy_file_is_noop(
        self, db_session: AsyncSession, healthy_file: MonitoredFile
    ):
        """Success on a file with no failures is a safe no-op."""
        result = await record_file_success(db_session, healthy_file.id)
        assert result is not None
        assert result.consecutive_failures == 0
        assert result.quarantined is False

    async def test_success_nonexistent_file_returns_none(
        self, db_session: AsyncSession
    ):
        """Recording success for a nonexistent file returns None."""
        result = await record_file_success(db_session, uuid4())
        assert result is None


class TestGetQuarantinedFiles:
    """Tests for get_quarantined_files()."""

    async def test_returns_only_quarantined(
        self,
        db_session: AsyncSession,
        healthy_file: MonitoredFile,
        quarantined_file: MonitoredFile,
    ):
        """Only quarantined files are returned."""
        files, total = await get_quarantined_files(db_session)
        assert total == 1
        assert len(files) == 1
        assert files[0].id == quarantined_file.id

    async def test_empty_when_no_quarantined(
        self, db_session: AsyncSession, healthy_file: MonitoredFile
    ):
        """Returns empty list when no files are quarantined."""
        files, total = await get_quarantined_files(db_session)
        assert total == 0
        assert len(files) == 0

    async def test_pagination_skip(
        self, db_session: AsyncSession, multiple_quarantined: list[MonitoredFile]
    ):
        """Skip parameter works correctly."""
        files, total = await get_quarantined_files(db_session, skip=2, limit=10)
        assert total == 5
        assert len(files) == 3

    async def test_pagination_limit(
        self, db_session: AsyncSession, multiple_quarantined: list[MonitoredFile]
    ):
        """Limit parameter works correctly."""
        files, total = await get_quarantined_files(db_session, skip=0, limit=2)
        assert total == 5
        assert len(files) == 2


class TestRetryQuarantinedFile:
    """Tests for retry_quarantined_file()."""

    async def test_retry_resets_quarantine(
        self, db_session: AsyncSession, quarantined_file: MonitoredFile
    ):
        """Retry clears quarantine and marks pending."""
        result = await retry_quarantined_file(db_session, quarantined_file.id)
        assert result is not None
        assert result.consecutive_failures == 0
        assert result.quarantined is False
        assert result.quarantined_at is None
        assert result.extraction_pending is True

    async def test_retry_on_non_quarantined_file(
        self, db_session: AsyncSession, failing_file: MonitoredFile
    ):
        """Retry on non-quarantined file resets failures and marks pending."""
        result = await retry_quarantined_file(db_session, failing_file.id)
        assert result is not None
        assert result.consecutive_failures == 0
        assert result.quarantined is False
        assert result.extraction_pending is True

    async def test_retry_nonexistent_returns_none(
        self, db_session: AsyncSession
    ):
        """Retry on nonexistent file returns None."""
        result = await retry_quarantined_file(db_session, uuid4())
        assert result is None


# ============================================================================
# Model Tests: needs_extraction property
# ============================================================================


class TestNeedsExtractionProperty:
    """Tests for MonitoredFile.needs_extraction with quarantine."""

    async def test_quarantined_file_does_not_need_extraction(
        self, quarantined_file: MonitoredFile
    ):
        """Quarantined files should not need extraction."""
        assert quarantined_file.quarantined is True
        assert quarantined_file.needs_extraction is False

    async def test_active_pending_file_needs_extraction(
        self, db_session: AsyncSession
    ):
        """Active, pending, non-quarantined file needs extraction."""
        file = _make_monitored_file(
            deal_name="Pending Deal",
            extraction_pending=True,
            quarantined=False,
        )
        db_session.add(file)
        await db_session.commit()
        assert file.needs_extraction is True

    async def test_inactive_file_does_not_need_extraction(
        self, db_session: AsyncSession
    ):
        """Inactive file should not need extraction."""
        file = _make_monitored_file(
            deal_name="Inactive Deal",
            is_active=False,
            extraction_pending=True,
        )
        db_session.add(file)
        await db_session.commit()
        assert file.needs_extraction is False


# ============================================================================
# CRUD Integration: Quarantined Excluded from Pending
# ============================================================================


class TestQuarantinedExcludedFromPending:
    """Verify quarantined files are excluded from pending extraction queries."""

    async def test_crud_get_pending_excludes_quarantined(
        self,
        db_session: AsyncSession,
        quarantined_file: MonitoredFile,
    ):
        """Quarantined file with extraction_pending=True is excluded from pending list."""
        from app.crud.file_monitor import MonitoredFileCRUD

        # quarantined_file has extraction_pending=True
        assert quarantined_file.extraction_pending is True
        assert quarantined_file.quarantined is True

        pending = await MonitoredFileCRUD.get_pending_extraction(db_session)
        quarantined_ids = {f.id for f in pending if f.quarantined}
        assert len(quarantined_ids) == 0

    async def test_non_quarantined_pending_included(
        self,
        db_session: AsyncSession,
        quarantined_file: MonitoredFile,
    ):
        """Non-quarantined pending file IS included in pending list."""
        from app.crud.file_monitor import MonitoredFileCRUD

        # Create a non-quarantined pending file
        pending_file = _make_monitored_file(
            deal_name="Pending Normal",
            extraction_pending=True,
            quarantined=False,
        )
        db_session.add(pending_file)
        await db_session.commit()

        pending = await MonitoredFileCRUD.get_pending_extraction(db_session)
        assert any(f.id == pending_file.id for f in pending)

    async def test_file_monitor_get_pending_excludes_quarantined(
        self,
        db_session: AsyncSession,
        quarantined_file: MonitoredFile,
    ):
        """SharePointFileMonitor.get_pending_files excludes quarantined."""
        from unittest.mock import AsyncMock

        from app.services.extraction.file_monitor import SharePointFileMonitor

        monitor = SharePointFileMonitor(db_session, AsyncMock())
        pending = await monitor.get_pending_files()
        quarantined_ids = {f.id for f in pending if f.quarantined}
        assert len(quarantined_ids) == 0


# ============================================================================
# API Endpoint Tests
# ============================================================================


class TestDeadLetterListEndpoint:
    """Tests for GET /api/v1/extraction/dead-letter."""

    async def test_list_requires_auth(
        self, client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/extraction/dead-letter")
        assert response.status_code == 401

    async def test_list_forbidden_for_viewer(
        self,
        client: AsyncClient,
        viewer_auth_headers: dict,
        quarantined_file: MonitoredFile,
    ):
        """Viewer role is denied access (require_analyst)."""
        response = await client.get(
            "/api/v1/extraction/dead-letter",
            headers=viewer_auth_headers,
        )
        assert response.status_code == 403

    async def test_list_returns_quarantined_files(
        self,
        client: AsyncClient,
        auth_headers: dict,
        quarantined_file: MonitoredFile,
    ):
        """Analyst can list quarantined files."""
        response = await client.get(
            "/api/v1/extraction/dead-letter",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["file_name"] == quarantined_file.file_name
        assert item["deal_name"] == quarantined_file.deal_name
        assert item["consecutive_failures"] == quarantined_file.consecutive_failures
        assert item["last_failure_reason"] == quarantined_file.last_failure_reason

    async def test_list_empty_when_no_quarantined(
        self,
        client: AsyncClient,
        auth_headers: dict,
        healthy_file: MonitoredFile,
    ):
        """Returns empty list when no quarantined files exist."""
        response = await client.get(
            "/api/v1/extraction/dead-letter",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    async def test_list_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        multiple_quarantined: list[MonitoredFile],
    ):
        """Pagination works with skip and limit."""
        response = await client.get(
            "/api/v1/extraction/dead-letter?skip=0&limit=2",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["has_more"] is True
        assert data["skip"] == 0
        assert data["limit"] == 2

    async def test_list_pagination_last_page(
        self,
        client: AsyncClient,
        auth_headers: dict,
        multiple_quarantined: list[MonitoredFile],
    ):
        """Last page has has_more=False."""
        response = await client.get(
            "/api/v1/extraction/dead-letter?skip=4&limit=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 1
        assert data["has_more"] is False


class TestDeadLetterRetryEndpoint:
    """Tests for POST /api/v1/extraction/dead-letter/{id}/retry."""

    async def test_retry_requires_auth(
        self, client: AsyncClient, quarantined_file: MonitoredFile
    ):
        """Unauthenticated request returns 401."""
        response = await client.post(
            f"/api/v1/extraction/dead-letter/{quarantined_file.id}/retry"
        )
        assert response.status_code == 401

    async def test_retry_requires_manager(
        self,
        client: AsyncClient,
        auth_headers: dict,
        quarantined_file: MonitoredFile,
    ):
        """Analyst (non-manager) is denied retry access."""
        response = await client.post(
            f"/api/v1/extraction/dead-letter/{quarantined_file.id}/retry",
            headers=auth_headers,
        )
        assert response.status_code == 403

    async def test_retry_succeeds_for_manager(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
        quarantined_file: MonitoredFile,
    ):
        """Manager can retry a quarantined file."""
        response = await client.post(
            f"/api/v1/extraction/dead-letter/{quarantined_file.id}/retry",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["file_name"] == quarantined_file.file_name
        assert data["deal_name"] == quarantined_file.deal_name
        assert data["extraction_pending"] is True
        assert "quarantine reset" in data["message"].lower()

    async def test_retry_nonexistent_returns_404(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Retry on nonexistent file returns 404."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/extraction/dead-letter/{fake_id}/retry",
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    async def test_retry_then_verify_no_longer_quarantined(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
        auth_headers: dict,
        quarantined_file: MonitoredFile,
    ):
        """After retry, file no longer appears in dead-letter list."""
        # Retry the file
        retry_response = await client.post(
            f"/api/v1/extraction/dead-letter/{quarantined_file.id}/retry",
            headers=admin_auth_headers,
        )
        assert retry_response.status_code == 200

        # Verify it's gone from the list
        list_response = await client.get(
            "/api/v1/extraction/dead-letter",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["total"] == 0

    async def test_retry_non_quarantined_file_resets_failures(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
        failing_file: MonitoredFile,
    ):
        """Retry on a non-quarantined file still resets failure count."""
        response = await client.post(
            f"/api/v1/extraction/dead-letter/{failing_file.id}/retry",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["extraction_pending"] is True
