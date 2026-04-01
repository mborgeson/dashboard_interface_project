"""
Tests for Delta Query Support (Epic 2.2 — UR-010).

Covers:
- DeltaToken model creation
- CRUD operations (get_by_drive_id, upsert_token, clear_token)
- SharePointClient.get_delta_changes() with mocked Graph API
- FileMonitor.check_for_changes_delta() integration
- Token expiry fallback (HTTP 410)
- Pagination of delta results
- Deleted file handling
- Config flag defaults

Run with: pytest tests/test_extraction/test_delta_query.py -v
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ExtractionSettings, Settings
from app.crud.delta_token import DeltaTokenCRUD
from app.extraction.sharepoint import (
    DeltaChange,
    DeltaQueryResult,
    SharePointClient,
)
from app.models.delta_token import DeltaToken
from app.services.extraction.file_monitor import (
    FileChange,
    MonitorCheckResult,
    SharePointFileMonitor,
)

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def delta_token(db_session: AsyncSession) -> DeltaToken:
    """Create a test delta token."""
    now = datetime.now(UTC)
    token = DeltaToken(
        drive_id="test-drive-001",
        delta_token="initial-token-abc123",
        last_sync_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(token)
    await db_session.commit()
    await db_session.refresh(token)
    return token


@pytest.fixture
def mock_sharepoint_client() -> SharePointClient:
    """Create SharePoint client with mock settings."""
    mock_settings = MagicMock()
    mock_settings.AZURE_TENANT_ID = "test-tenant"
    mock_settings.AZURE_CLIENT_ID = "test-client"
    mock_settings.AZURE_CLIENT_SECRET = "test-secret"
    mock_settings.SHAREPOINT_SITE_URL = "https://test.sharepoint.com/sites/Test"
    mock_settings.SHAREPOINT_DEALS_FOLDER = "Deals"
    mock_settings.SHAREPOINT_LIBRARY = "Real Estate"

    with patch("app.extraction.sharepoint.settings", mock_settings):
        return SharePointClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
            site_url="https://test.sharepoint.com/sites/Test",
        )


# ── DeltaToken Model Tests ─────────────────────────────────────────────────


class TestDeltaTokenModel:
    """Tests for the DeltaToken SQLAlchemy model."""

    async def test_create_delta_token(self, db_session: AsyncSession) -> None:
        """Verify DeltaToken can be created and persisted."""
        now = datetime.now(UTC)
        token = DeltaToken(
            drive_id="drive-123",
            delta_token="token-value-xyz",
            last_sync_at=now,
            created_at=now,
            updated_at=now,
        )
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)

        assert token.id is not None
        assert token.drive_id == "drive-123"
        assert token.delta_token == "token-value-xyz"

    async def test_delta_token_repr(self, delta_token: DeltaToken) -> None:
        """Verify DeltaToken repr format."""
        result = repr(delta_token)
        assert "test-drive-001" in result

    async def test_drive_id_unique_constraint(
        self, db_session: AsyncSession, delta_token: DeltaToken
    ) -> None:
        """Verify drive_id uniqueness is enforced."""
        now = datetime.now(UTC)
        duplicate = DeltaToken(
            drive_id="test-drive-001",  # Same as fixture
            delta_token="another-token",
            last_sync_at=now,
            created_at=now,
            updated_at=now,
        )
        db_session.add(duplicate)

        with pytest.raises(  # noqa: B017
            Exception,  # IntegrityError — SQLite raises generic exception
        ):
            await db_session.commit()

    async def test_delta_token_timestamps(self, db_session: AsyncSession) -> None:
        """Verify created_at and updated_at are set correctly."""
        now = datetime.now(UTC)
        token = DeltaToken(
            drive_id="drive-timestamps",
            delta_token="token-ts",
            last_sync_at=now,
            created_at=now,
            updated_at=now,
        )
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)

        assert token.created_at is not None
        assert token.updated_at is not None


# ── CRUD Tests ──────────────────────────────────────────────────────────────


class TestDeltaTokenCRUD:
    """Tests for DeltaTokenCRUD operations."""

    async def test_get_by_drive_id_found(
        self, db_session: AsyncSession, delta_token: DeltaToken
    ) -> None:
        """Verify get_by_drive_id returns existing token."""
        result = await DeltaTokenCRUD.get_by_drive_id(db_session, "test-drive-001")
        assert result is not None
        assert result.drive_id == "test-drive-001"
        assert result.delta_token == "initial-token-abc123"

    async def test_get_by_drive_id_not_found(self, db_session: AsyncSession) -> None:
        """Verify get_by_drive_id returns None for missing drive."""
        result = await DeltaTokenCRUD.get_by_drive_id(db_session, "nonexistent-drive")
        assert result is None

    async def test_upsert_token_create(self, db_session: AsyncSession) -> None:
        """Verify upsert_token creates a new record when none exists."""
        result = await DeltaTokenCRUD.upsert_token(
            db_session, "new-drive-999", "brand-new-token"
        )
        await db_session.commit()

        assert result.drive_id == "new-drive-999"
        assert result.delta_token == "brand-new-token"
        assert result.last_sync_at is not None

        # Verify in database
        fetched = await DeltaTokenCRUD.get_by_drive_id(db_session, "new-drive-999")
        assert fetched is not None
        assert fetched.delta_token == "brand-new-token"

    async def test_upsert_token_update(
        self, db_session: AsyncSession, delta_token: DeltaToken
    ) -> None:
        """Verify upsert_token updates existing record."""
        original_token = delta_token.delta_token
        result = await DeltaTokenCRUD.upsert_token(
            db_session, "test-drive-001", "updated-token-xyz"
        )
        await db_session.commit()

        assert result.drive_id == "test-drive-001"
        assert result.delta_token == "updated-token-xyz"
        assert result.delta_token != original_token

    async def test_upsert_token_updates_last_sync_at(
        self, db_session: AsyncSession, delta_token: DeltaToken
    ) -> None:
        """Verify upsert updates the last_sync_at timestamp."""
        old_sync = delta_token.last_sync_at

        result = await DeltaTokenCRUD.upsert_token(
            db_session, "test-drive-001", "newer-token"
        )
        await db_session.commit()

        # last_sync_at should be updated (or at least not earlier)
        assert result.last_sync_at is not None
        # In SQLite test, timestamps lose tzinfo — compare naively
        assert result.last_sync_at.replace(tzinfo=None) >= old_sync.replace(tzinfo=None)

    async def test_clear_token_existing(
        self, db_session: AsyncSession, delta_token: DeltaToken
    ) -> None:
        """Verify clear_token deletes an existing token."""
        result = await DeltaTokenCRUD.clear_token(db_session, "test-drive-001")
        await db_session.commit()

        assert result is True

        # Verify deleted
        fetched = await DeltaTokenCRUD.get_by_drive_id(db_session, "test-drive-001")
        assert fetched is None

    async def test_clear_token_nonexistent(self, db_session: AsyncSession) -> None:
        """Verify clear_token returns False for missing drive."""
        result = await DeltaTokenCRUD.clear_token(db_session, "no-such-drive")
        await db_session.commit()
        assert result is False

    async def test_upsert_then_clear_then_upsert(
        self, db_session: AsyncSession
    ) -> None:
        """Verify full lifecycle: create -> clear -> recreate."""
        # Create
        await DeltaTokenCRUD.upsert_token(db_session, "lifecycle-drive", "token-v1")
        await db_session.commit()

        # Clear
        cleared = await DeltaTokenCRUD.clear_token(db_session, "lifecycle-drive")
        await db_session.commit()
        assert cleared is True

        # Recreate
        result = await DeltaTokenCRUD.upsert_token(
            db_session, "lifecycle-drive", "token-v2"
        )
        await db_session.commit()

        assert result.delta_token == "token-v2"


# ── SharePointClient Delta Query Tests ──────────────────────────────────────


class TestSharePointDeltaChanges:
    """Tests for SharePointClient.get_delta_changes()."""

    async def test_initial_sync_no_token(
        self, mock_sharepoint_client: SharePointClient
    ) -> None:
        """Verify initial sync (no token) performs full enumeration."""
        mock_response = {
            "value": [
                {
                    "id": "item-1",
                    "name": "UW Model vCurrent.xlsb",
                    "file": {"mimeType": "application/octet-stream"},
                    "size": 5000000,
                    "lastModifiedDateTime": "2025-01-15T10:00:00Z",
                    "createdDateTime": "2025-01-15T10:00:00Z",
                    "parentReference": {
                        "path": "/drives/drv-1/root:/Deals/Stage1/DealA"
                    },
                },
            ],
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/drives/drv-1/root/delta?token=new-token-001",
        }

        with (
            patch.object(
                mock_sharepoint_client,
                "_get_drive_id",
                return_value="drv-1",
            ),
            patch.object(
                mock_sharepoint_client,
                "_make_request",
                return_value=mock_response,
            ),
        ):
            result = await mock_sharepoint_client.get_delta_changes(
                drive_id="drv-1", delta_token=None
            )

        assert result.is_full_sync is True
        assert result.new_delta_token == "new-token-001"
        assert len(result.changes) == 1
        assert result.changes[0].change_type == "created"
        assert result.changes[0].name == "UW Model vCurrent.xlsb"

    async def test_incremental_sync_with_token(
        self, mock_sharepoint_client: SharePointClient
    ) -> None:
        """Verify incremental sync uses the provided token."""
        mock_response = {
            "value": [
                {
                    "id": "item-2",
                    "name": "Updated Model.xlsb",
                    "file": {"mimeType": "application/octet-stream"},
                    "size": 6000000,
                    "lastModifiedDateTime": "2025-02-01T14:00:00Z",
                    "createdDateTime": "2025-01-01T10:00:00Z",
                    "parentReference": {
                        "path": "/drives/drv-1/root:/Deals/Stage2/DealB"
                    },
                },
            ],
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/drives/drv-1/root/delta?token=new-token-002",
        }

        with (
            patch.object(
                mock_sharepoint_client,
                "_get_drive_id",
                return_value="drv-1",
            ),
            patch.object(
                mock_sharepoint_client,
                "_make_request",
                return_value=mock_response,
            ) as mock_req,
        ):
            result = await mock_sharepoint_client.get_delta_changes(
                drive_id="drv-1", delta_token="existing-token"
            )

        # Token should be appended to endpoint
        called_endpoint = mock_req.call_args[0][1]
        assert "token=existing-token" in called_endpoint

        assert result.is_full_sync is False
        assert result.new_delta_token == "new-token-002"
        assert len(result.changes) == 1
        assert result.changes[0].change_type == "modified"

    async def test_deleted_files_handling(
        self, mock_sharepoint_client: SharePointClient
    ) -> None:
        """Verify deleted items are correctly identified."""
        mock_response = {
            "value": [
                {
                    "id": "item-deleted",
                    "name": "Removed.xlsb",
                    "deleted": {"state": "deleted"},
                    "parentReference": {
                        "path": "/drives/drv-1/root:/Deals/Stage1/DealC"
                    },
                },
            ],
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/drives/drv-1/root/delta?token=after-delete",
        }

        with (
            patch.object(
                mock_sharepoint_client,
                "_get_drive_id",
                return_value="drv-1",
            ),
            patch.object(
                mock_sharepoint_client,
                "_make_request",
                return_value=mock_response,
            ),
        ):
            result = await mock_sharepoint_client.get_delta_changes(
                drive_id="drv-1", delta_token="some-token"
            )

        assert len(result.changes) == 1
        assert result.changes[0].change_type == "deleted"
        assert result.changes[0].name == "Removed.xlsb"

    async def test_pagination_next_link(
        self, mock_sharepoint_client: SharePointClient
    ) -> None:
        """Verify pagination via @odata.nextLink is followed."""
        page1 = {
            "value": [
                {
                    "id": "item-p1",
                    "name": "File1.xlsb",
                    "file": {},
                    "size": 1000,
                    "lastModifiedDateTime": "2025-01-01T10:00:00Z",
                    "createdDateTime": "2025-01-01T10:00:00Z",
                    "parentReference": {"path": "/drives/drv-1/root:/Deals/S/D"},
                },
            ],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/drives/drv-1/root/delta?$skiptoken=page2",
        }
        page2 = {
            "value": [
                {
                    "id": "item-p2",
                    "name": "File2.xlsb",
                    "file": {},
                    "size": 2000,
                    "lastModifiedDateTime": "2025-01-02T10:00:00Z",
                    "createdDateTime": "2025-01-02T10:00:00Z",
                    "parentReference": {"path": "/drives/drv-1/root:/Deals/S/D"},
                },
            ],
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/drives/drv-1/root/delta?token=final-token",
        }

        call_count = 0

        async def mock_make_request(method, endpoint, **kwargs):
            nonlocal call_count
            call_count += 1
            return page1

        # Mock the first call (non-paginated)
        # and the second call (paginated via full URL)
        mock_session = AsyncMock()
        mock_json_resp = AsyncMock(return_value=page2)
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = mock_json_resp

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context)
        mock_session.closed = True  # Force new session path

        with (
            patch.object(
                mock_sharepoint_client,
                "_get_drive_id",
                return_value="drv-1",
            ),
            patch.object(
                mock_sharepoint_client,
                "_make_request",
                side_effect=mock_make_request,
            ),
            patch.object(
                mock_sharepoint_client,
                "_get_access_token",
                return_value="test-token",
            ),
            patch.object(
                mock_sharepoint_client,
                "_get_session",
                return_value=mock_session,
            ),
        ):
            # Set _session to None so owns_session is True for cleanup
            mock_sharepoint_client._session = None
            result = await mock_sharepoint_client.get_delta_changes(drive_id="drv-1")

        assert len(result.changes) == 2
        assert result.new_delta_token == "final-token"
        assert result.changes[0].name == "File1.xlsb"
        assert result.changes[1].name == "File2.xlsb"

    async def test_folder_changes_skipped(
        self, mock_sharepoint_client: SharePointClient
    ) -> None:
        """Verify folder items are skipped in delta results."""
        mock_response = {
            "value": [
                {
                    "id": "folder-1",
                    "name": "SomeFolder",
                    "folder": {"childCount": 5},
                    "parentReference": {"path": "/drives/drv-1/root:/Deals"},
                },
                {
                    "id": "file-1",
                    "name": "Actual.xlsb",
                    "file": {},
                    "size": 3000,
                    "lastModifiedDateTime": "2025-03-01T10:00:00Z",
                    "createdDateTime": "2025-03-01T10:00:00Z",
                    "parentReference": {"path": "/drives/drv-1/root:/Deals/S/D"},
                },
            ],
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/drives/drv-1/root/delta?token=skip-folders",
        }

        with (
            patch.object(
                mock_sharepoint_client,
                "_get_drive_id",
                return_value="drv-1",
            ),
            patch.object(
                mock_sharepoint_client,
                "_make_request",
                return_value=mock_response,
            ),
        ):
            result = await mock_sharepoint_client.get_delta_changes(drive_id="drv-1")

        # Only the file should be in changes, not the folder
        assert len(result.changes) == 1
        assert result.changes[0].name == "Actual.xlsb"

    async def test_empty_delta_response(
        self, mock_sharepoint_client: SharePointClient
    ) -> None:
        """Verify handling of no changes since last sync."""
        mock_response = {
            "value": [],
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/drives/drv-1/root/delta?token=same-token",
        }

        with (
            patch.object(
                mock_sharepoint_client,
                "_get_drive_id",
                return_value="drv-1",
            ),
            patch.object(
                mock_sharepoint_client,
                "_make_request",
                return_value=mock_response,
            ),
        ):
            result = await mock_sharepoint_client.get_delta_changes(
                drive_id="drv-1", delta_token="current-token"
            )

        assert len(result.changes) == 0
        assert result.new_delta_token == "same-token"


# ── SharePointClient Helper Tests ───────────────────────────────────────────


class TestSharePointDeltaHelpers:
    """Tests for SharePointClient delta helper methods."""

    def test_extract_token_from_delta_link(self) -> None:
        """Verify token extraction from deltaLink URL."""
        link = (
            "https://graph.microsoft.com/v1.0/drives/drv-1/root/delta?token=abc123xyz"
        )
        token = SharePointClient._extract_token_from_delta_link(link)
        assert token == "abc123xyz"

    def test_extract_token_from_delta_link_no_token(self) -> None:
        """Verify None when deltaLink has no token param."""
        link = "https://graph.microsoft.com/v1.0/drives/drv-1/root/delta"
        token = SharePointClient._extract_token_from_delta_link(link)
        assert token is None

    def test_extract_item_path_with_parent_ref(self) -> None:
        """Verify path extraction from item with parentReference."""
        item = {
            "name": "Model.xlsb",
            "parentReference": {"path": "/drives/drv-1/root:/Deals/Stage/DealName"},
        }
        path = SharePointClient._extract_item_path(item)
        assert path == "Deals/Stage/DealName/Model.xlsb"

    def test_extract_item_path_no_parent(self) -> None:
        """Verify path extraction when parentReference is empty."""
        item = {"name": "RootFile.xlsb", "parentReference": {}}
        path = SharePointClient._extract_item_path(item)
        assert path == "RootFile.xlsb"

    def test_parse_delta_item_deleted(
        self, mock_sharepoint_client: SharePointClient
    ) -> None:
        """Verify parsing of a deleted item."""
        item = {
            "id": "del-1",
            "name": "Deleted.xlsb",
            "deleted": {"state": "deleted"},
            "parentReference": {"path": "/drives/d/root:/Deals/S/D"},
        }
        change = mock_sharepoint_client._parse_delta_item(item)
        assert change is not None
        assert change.change_type == "deleted"

    def test_parse_delta_item_folder_skipped(
        self, mock_sharepoint_client: SharePointClient
    ) -> None:
        """Verify folder items return None."""
        item = {
            "id": "folder-1",
            "name": "SomeFolder",
            "folder": {"childCount": 3},
            "parentReference": {"path": "/drives/d/root:/Deals"},
        }
        change = mock_sharepoint_client._parse_delta_item(item)
        assert change is None

    def test_parse_delta_item_created(
        self, mock_sharepoint_client: SharePointClient
    ) -> None:
        """Verify parsing of a newly created file."""
        item = {
            "id": "new-1",
            "name": "New.xlsb",
            "file": {},
            "size": 4000,
            "lastModifiedDateTime": "2025-06-01T12:00:00Z",
            "createdDateTime": "2025-06-01T12:00:00Z",
            "parentReference": {"path": "/drives/d/root:/Deals/S/D"},
        }
        change = mock_sharepoint_client._parse_delta_item(item)
        assert change is not None
        assert change.change_type == "created"
        assert change.size == 4000

    def test_parse_delta_item_modified(
        self, mock_sharepoint_client: SharePointClient
    ) -> None:
        """Verify parsing of a modified file (different create/modify times)."""
        item = {
            "id": "mod-1",
            "name": "Modified.xlsb",
            "file": {},
            "size": 5000,
            "lastModifiedDateTime": "2025-07-01T12:00:00Z",
            "createdDateTime": "2025-06-01T12:00:00Z",
            "parentReference": {"path": "/drives/d/root:/Deals/S/D"},
        }
        change = mock_sharepoint_client._parse_delta_item(item)
        assert change is not None
        assert change.change_type == "modified"


# ── FileMonitor Delta Integration Tests ─────────────────────────────────────


class TestFileMonitorDelta:
    """Tests for FileMonitor.check_for_changes_delta()."""

    async def test_initial_sync_full_scan(self, db_session: AsyncSession) -> None:
        """Verify initial delta check (no token) does full enumeration and stores token."""
        mock_client = AsyncMock(spec=SharePointClient)
        mock_client._get_drive_id = AsyncMock(return_value="drv-test")
        mock_client.get_delta_changes = AsyncMock(
            return_value=DeltaQueryResult(
                changes=[
                    DeltaChange(
                        item_id="f1",
                        name="NewFile.xlsb",
                        path="Deals/Stage/DealX/NewFile.xlsb",
                        change_type="created",
                        size=1000,
                        modified_date=datetime(2025, 1, 1, tzinfo=UTC),
                    ),
                ],
                new_delta_token="first-token",
                is_full_sync=True,
            )
        )

        monitor = SharePointFileMonitor(db=db_session, sharepoint_client=mock_client)

        with patch.object(monitor, "_trigger_extraction", return_value=None):
            result = await monitor.check_for_changes_delta(
                auto_trigger_extraction=False,
            )

        assert isinstance(result, MonitorCheckResult)
        assert result.changes_detected == 1
        assert result.changes[0].change_type == "added"

        # Verify token was stored
        stored = await DeltaTokenCRUD.get_by_drive_id(db_session, "drv-test")
        assert stored is not None
        assert stored.delta_token == "first-token"

    async def test_incremental_sync_uses_existing_token(
        self, db_session: AsyncSession, delta_token: DeltaToken
    ) -> None:
        """Verify delta check uses existing token for incremental query."""
        mock_client = AsyncMock(spec=SharePointClient)
        mock_client._get_drive_id = AsyncMock(return_value="test-drive-001")
        mock_client.get_delta_changes = AsyncMock(
            return_value=DeltaQueryResult(
                changes=[
                    DeltaChange(
                        item_id="f2",
                        name="Updated.xlsb",
                        path="Deals/Stage/DealY/Updated.xlsb",
                        change_type="modified",
                        size=2000,
                        modified_date=datetime(2025, 2, 1, tzinfo=UTC),
                    ),
                ],
                new_delta_token="updated-token",
                is_full_sync=False,
            )
        )

        monitor = SharePointFileMonitor(db=db_session, sharepoint_client=mock_client)

        with patch.object(monitor, "_trigger_extraction", return_value=None):
            result = await monitor.check_for_changes_delta(
                auto_trigger_extraction=False,
            )

        # Verify token was passed to get_delta_changes
        mock_client.get_delta_changes.assert_called_once_with(
            drive_id="test-drive-001",
            delta_token="initial-token-abc123",
        )

        assert result.changes_detected == 1
        assert result.changes[0].change_type == "modified"

        # Verify token was updated
        stored = await DeltaTokenCRUD.get_by_drive_id(db_session, "test-drive-001")
        assert stored is not None
        assert stored.delta_token == "updated-token"

    async def test_token_expiry_fallback_to_full_scan(
        self, db_session: AsyncSession, delta_token: DeltaToken
    ) -> None:
        """Verify HTTP 410 (Gone) clears token and falls back to full scan."""
        mock_client = AsyncMock(spec=SharePointClient)
        mock_client._get_drive_id = AsyncMock(return_value="test-drive-001")

        # Simulate 410 Gone error
        gone_error = Exception("Gone")
        gone_error.status = 410  # type: ignore[attr-defined]
        mock_client.get_delta_changes = AsyncMock(side_effect=gone_error)

        monitor = SharePointFileMonitor(db=db_session, sharepoint_client=mock_client)

        # Mock the fallback full scan
        mock_full_result = MonitorCheckResult(
            changes=[],
            files_checked=10,
            folders_scanned=5,
            check_duration_seconds=1.0,
        )

        with patch.object(
            monitor,
            "check_for_changes",
            return_value=mock_full_result,
        ) as mock_full:
            fallback_result = await monitor.check_for_changes_delta()

        # Full scan should have been called
        mock_full.assert_called_once_with(auto_trigger_extraction=True)
        assert fallback_result is mock_full_result

        # Token should be cleared
        stored = await DeltaTokenCRUD.get_by_drive_id(db_session, "test-drive-001")
        assert stored is None

    async def test_deleted_files_in_delta(self, db_session: AsyncSession) -> None:
        """Verify deleted files from delta query are tracked."""
        mock_client = AsyncMock(spec=SharePointClient)
        mock_client._get_drive_id = AsyncMock(return_value="drv-del")
        mock_client.get_delta_changes = AsyncMock(
            return_value=DeltaQueryResult(
                changes=[
                    DeltaChange(
                        item_id="del-1",
                        name="Removed.xlsb",
                        path="Deals/Stage/DealZ/Removed.xlsb",
                        change_type="deleted",
                    ),
                ],
                new_delta_token="post-delete-token",
                is_full_sync=False,
            )
        )

        monitor = SharePointFileMonitor(db=db_session, sharepoint_client=mock_client)

        with patch.object(monitor, "_trigger_extraction", return_value=None):
            result = await monitor.check_for_changes_delta(
                auto_trigger_extraction=False,
            )

        assert result.changes_detected == 1
        assert result.changes[0].change_type == "deleted"
        assert result.changes[0].file_name == "Removed.xlsb"

    async def test_no_changes_delta(self, db_session: AsyncSession) -> None:
        """Verify empty delta result produces no changes."""
        mock_client = AsyncMock(spec=SharePointClient)
        mock_client._get_drive_id = AsyncMock(return_value="drv-empty")
        mock_client.get_delta_changes = AsyncMock(
            return_value=DeltaQueryResult(
                changes=[],
                new_delta_token="no-change-token",
                is_full_sync=False,
            )
        )

        monitor = SharePointFileMonitor(db=db_session, sharepoint_client=mock_client)

        result = await monitor.check_for_changes_delta(
            auto_trigger_extraction=False,
        )

        assert result.changes_detected == 0
        assert result.extraction_triggered is False


# ── Delta Change Conversion Tests ───────────────────────────────────────────


class TestDeltaChangeConversion:
    """Tests for FileMonitor._delta_change_to_file_change()."""

    def test_created_to_added(self) -> None:
        """Verify 'created' maps to 'added'."""
        delta = DeltaChange(
            item_id="c1",
            name="New.xlsb",
            path="Deals/Stage/Deal/New.xlsb",
            change_type="created",
            size=500,
            modified_date=datetime(2025, 1, 1, tzinfo=UTC),
        )
        result = SharePointFileMonitor._delta_change_to_file_change(delta)
        assert result is not None
        assert result.change_type == "added"
        assert result.file_name == "New.xlsb"
        assert result.new_size_bytes == 500

    def test_modified_maps(self) -> None:
        """Verify 'modified' maps to 'modified'."""
        delta = DeltaChange(
            item_id="m1",
            name="Mod.xlsb",
            path="Deals/Stage/Deal/Mod.xlsb",
            change_type="modified",
            size=600,
            modified_date=datetime(2025, 2, 1, tzinfo=UTC),
        )
        result = SharePointFileMonitor._delta_change_to_file_change(delta)
        assert result is not None
        assert result.change_type == "modified"

    def test_deleted_maps(self) -> None:
        """Verify 'deleted' maps to 'deleted'."""
        delta = DeltaChange(
            item_id="d1",
            name="Del.xlsb",
            path="Deals/Stage/Deal/Del.xlsb",
            change_type="deleted",
        )
        result = SharePointFileMonitor._delta_change_to_file_change(delta)
        assert result is not None
        assert result.change_type == "deleted"

    def test_folder_skipped(self) -> None:
        """Verify folder delta changes return None."""
        delta = DeltaChange(
            item_id="f1",
            name="SomeFolder",
            path="Deals/Stage/SomeFolder",
            change_type="created",
            is_folder=True,
        )
        result = SharePointFileMonitor._delta_change_to_file_change(delta)
        assert result is None

    def test_deal_name_from_path(self) -> None:
        """Verify deal name is extracted from path components."""
        delta = DeltaChange(
            item_id="p1",
            name="File.xlsb",
            path="Deals/Stage/MyDealName/File.xlsb",
            change_type="created",
            size=100,
        )
        result = SharePointFileMonitor._delta_change_to_file_change(delta)
        assert result is not None
        assert result.deal_name == "MyDealName"

    def test_short_path_unknown_deal(self) -> None:
        """Verify short paths fall back to 'Unknown' deal name."""
        delta = DeltaChange(
            item_id="s1",
            name="File.xlsb",
            path="File.xlsb",
            change_type="created",
            size=100,
        )
        result = SharePointFileMonitor._delta_change_to_file_change(delta)
        assert result is not None
        assert result.deal_name == "Unknown"


# ── Config Tests ────────────────────────────────────────────────────────────


class TestDeltaQueryConfig:
    """Tests for delta query configuration settings."""

    def test_delta_query_disabled_by_default(self) -> None:
        """Verify DELTA_QUERY_ENABLED defaults to False."""
        extraction = ExtractionSettings()
        assert extraction.DELTA_QUERY_ENABLED is False

    def test_delta_reconciliation_cron_default(self) -> None:
        """Verify DELTA_RECONCILIATION_CRON defaults to 3 AM daily."""
        extraction = ExtractionSettings()
        assert extraction.DELTA_RECONCILIATION_CRON == "0 3 * * *"

    def test_delta_query_can_be_enabled(self) -> None:
        """Verify DELTA_QUERY_ENABLED can be set to True."""
        with patch.dict("os.environ", {"DELTA_QUERY_ENABLED": "true"}, clear=False):
            extraction = ExtractionSettings()
            assert extraction.DELTA_QUERY_ENABLED is True

    def test_delta_reconciliation_cron_customizable(self) -> None:
        """Verify reconciliation cron can be overridden."""
        with patch.dict(
            "os.environ",
            {"DELTA_RECONCILIATION_CRON": "0 4 * * 0"},
            clear=False,
        ):
            extraction = ExtractionSettings()
            assert extraction.DELTA_RECONCILIATION_CRON == "0 4 * * 0"


# ── DeltaChange / DeltaQueryResult Dataclass Tests ──────────────────────────


class TestDeltaDataclasses:
    """Tests for DeltaChange and DeltaQueryResult dataclasses."""

    def test_delta_change_defaults(self) -> None:
        """Verify DeltaChange default values."""
        change = DeltaChange(
            item_id="x1",
            name="test.xlsb",
            path="test.xlsb",
            change_type="created",
        )
        assert change.size is None
        assert change.modified_date is None
        assert change.is_folder is False

    def test_delta_query_result_defaults(self) -> None:
        """Verify DeltaQueryResult default values."""
        result = DeltaQueryResult()
        assert result.changes == []
        assert result.new_delta_token is None
        assert result.is_full_sync is False

    def test_delta_query_result_with_data(self) -> None:
        """Verify DeltaQueryResult with populated data."""
        changes = [
            DeltaChange(
                item_id="a1",
                name="f.xlsb",
                path="p/f.xlsb",
                change_type="modified",
                size=100,
            ),
        ]
        result = DeltaQueryResult(
            changes=changes,
            new_delta_token="token-abc",
            is_full_sync=True,
        )
        assert len(result.changes) == 1
        assert result.new_delta_token == "token-abc"
        assert result.is_full_sync is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
