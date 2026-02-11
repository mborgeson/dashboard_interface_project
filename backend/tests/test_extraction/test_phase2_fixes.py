"""
Phase 2 tests: Incomplete implementation fixes.

Tests cover:
- 2.1: property_id populated in bulk_insert when Property match exists
- 2.2: content_hash computed during SharePoint download
- 2.3: _trigger_extraction creates runs and skips when busy
- 2.4: error_category populated, extraction_triggered set in change logs

Run with: pytest tests/test_extraction/test_phase2_fixes.py -v
"""

import hashlib
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.base import Base
from app.models.extraction import ExtractedValue
from app.models.file_monitor import FileChangeLog, MonitoredFile
from app.models.property import Property
from app.services.extraction.file_monitor import (
    FileChange,
    SharePointFileMonitor,
)

# ============================================================================
# Sync Database Setup (matches existing pattern)
# ============================================================================

SYNC_TEST_DATABASE_URL = "sqlite:///:memory:"

sync_test_engine = create_engine(
    SYNC_TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

SyncTestSession = sessionmaker(
    bind=sync_test_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="function")
def sync_db_session() -> Generator[Session, None, None]:
    """Create a sync database session for tests."""
    Base.metadata.create_all(bind=sync_test_engine)
    session = SyncTestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=sync_test_engine)


# ============================================================================
# Issue 2.1: property_id populated in bulk_insert
# ============================================================================


class TestBulkInsertPropertyId:
    """Tests for property_id resolution in ExtractedValueCRUD.bulk_insert()."""

    def test_bulk_insert_sets_property_id_when_match(self, sync_db_session: Session):
        """bulk_insert should set property_id when a matching Property exists."""
        # Create a Property record
        prop = Property(
            name="Test Property",
            property_type="multifamily",
            address="123 Test St",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
        )
        sync_db_session.add(prop)
        sync_db_session.commit()
        sync_db_session.refresh(prop)

        # Create an extraction run
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        # bulk_insert with property_name matching the Property.name
        extracted_data = {"FIELD_A": 100.0, "FIELD_B": "text value"}
        ExtractedValueCRUD.bulk_insert(
            sync_db_session,
            run.id,
            extracted_data,
            {},
            "Test Property",
        )

        # Verify property_id was set
        values = sync_db_session.execute(
            select(ExtractedValue).where(
                ExtractedValue.extraction_run_id == run.id
            )
        ).scalars().all()

        assert len(values) == 2
        for v in values:
            assert v.property_id == prop.id

    def test_bulk_insert_null_property_id_when_no_match(
        self, sync_db_session: Session
    ):
        """bulk_insert should leave property_id NULL when no Property match."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        extracted_data = {"FIELD_A": 42.0}
        ExtractedValueCRUD.bulk_insert(
            sync_db_session,
            run.id,
            extracted_data,
            {},
            "NonExistent Property",
        )

        values = sync_db_session.execute(
            select(ExtractedValue).where(
                ExtractedValue.extraction_run_id == run.id
            )
        ).scalars().all()

        assert len(values) == 1
        assert values[0].property_id is None


# ============================================================================
# Issue 2.2: content_hash computed during download
# ============================================================================


class TestContentHash:
    """Tests for content hash computation during SharePoint file download."""

    @pytest.mark.asyncio
    async def test_content_hash_computed_on_download(self, tmp_path):
        """download_sharepoint_file should return content hash as second element."""
        from app.api.v1.endpoints.extraction.common import download_sharepoint_file

        # Create a mock client and file
        mock_content = b"test file content for hashing"
        expected_hash = hashlib.sha256(mock_content).hexdigest()

        mock_client = AsyncMock()
        mock_client.download_file.return_value = mock_content

        mock_file = MagicMock()
        mock_file.name = "test_file.xlsb"
        mock_file.deal_name = "Test Deal"

        result = await download_sharepoint_file(
            mock_client, mock_file, str(tmp_path)
        )

        # Should return a tuple (path, hash)
        assert isinstance(result, tuple)
        assert len(result) == 2
        local_path, content_hash = result
        assert content_hash == expected_hash
        assert local_path.endswith("test_file.xlsb")


# ============================================================================
# Issue 2.3: _trigger_extraction creates runs
# ============================================================================


class TestTriggerExtraction:
    """Tests for SharePointFileMonitor._trigger_extraction()."""

    @pytest.mark.asyncio
    async def test_trigger_extraction_creates_run(self, db_session: AsyncSession):
        """_trigger_extraction should create an ExtractionRun with trigger_type='file_monitor'."""
        mock_client = AsyncMock()
        monitor = SharePointFileMonitor(db_session, mock_client)

        changes = [
            FileChange(
                file_path="/sites/deals/DealA/UW.xlsb",
                file_name="UW.xlsb",
                change_type="added",
                deal_name="Deal A",
                old_modified_date=None,
                new_modified_date=datetime.now(UTC),
            ),
        ]

        # Mock the sync session and CRUD — lazily imported inside the method
        mock_sync_db = MagicMock()
        mock_run = MagicMock()
        mock_run.id = uuid4()

        with (
            patch(
                "app.db.session.SessionLocal",
                return_value=mock_sync_db,
            ),
            patch(
                "app.crud.extraction.ExtractionRunCRUD.get_running",
                return_value=None,
            ),
            patch(
                "app.crud.extraction.ExtractionRunCRUD.create",
                return_value=mock_run,
            ) as mock_create,
        ):
            run_id = await monitor._trigger_extraction(changes)

        assert run_id == mock_run.id
        mock_create.assert_called_once_with(
            mock_sync_db,
            trigger_type="file_monitor",
            files_discovered=1,
        )

    @pytest.mark.asyncio
    async def test_trigger_extraction_skips_when_running(
        self, db_session: AsyncSession
    ):
        """_trigger_extraction should return None if an extraction is already running."""
        mock_client = AsyncMock()
        monitor = SharePointFileMonitor(db_session, mock_client)

        changes = [
            FileChange(
                file_path="/sites/deals/DealA/UW.xlsb",
                file_name="UW.xlsb",
                change_type="modified",
                deal_name="Deal A",
                old_modified_date=datetime.now(UTC) - timedelta(days=1),
                new_modified_date=datetime.now(UTC),
            ),
        ]

        mock_sync_db = MagicMock()
        mock_running = MagicMock()
        mock_running.id = uuid4()

        with (
            patch(
                "app.db.session.SessionLocal",
                return_value=mock_sync_db,
            ),
            patch(
                "app.crud.extraction.ExtractionRunCRUD.get_running",
                return_value=mock_running,
            ),
            patch(
                "app.crud.extraction.ExtractionRunCRUD.create",
            ) as mock_create,
        ):
            run_id = await monitor._trigger_extraction(changes)

        assert run_id is None
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_extraction_skips_deleted_only(
        self, db_session: AsyncSession
    ):
        """_trigger_extraction should return None when only deleted changes exist."""
        mock_client = AsyncMock()
        monitor = SharePointFileMonitor(db_session, mock_client)

        changes = [
            FileChange(
                file_path="/sites/deals/DealA/UW.xlsb",
                file_name="UW.xlsb",
                change_type="deleted",
                deal_name="Deal A",
                old_modified_date=datetime.now(UTC) - timedelta(days=1),
                new_modified_date=None,
            ),
        ]

        run_id = await monitor._trigger_extraction(changes)
        assert run_id is None


# ============================================================================
# Issue 2.4: error_category populated and extraction_triggered in change logs
# ============================================================================


class TestErrorCategory:
    """Tests for error_category population in bulk_insert."""

    def test_error_category_populated(self, sync_db_session: Session):
        """bulk_insert should set error_category when provided for error fields."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        extracted_data = {
            "GOOD_FIELD": 42.0,
            "BAD_FIELD": float("nan"),  # NaN → is_error=True
        }
        error_categories = {"BAD_FIELD": "missing_sheet"}

        ExtractedValueCRUD.bulk_insert(
            sync_db_session,
            run.id,
            extracted_data,
            {},
            "test_prop",
            error_categories=error_categories,
        )

        values = sync_db_session.execute(
            select(ExtractedValue).where(
                ExtractedValue.extraction_run_id == run.id
            )
        ).scalars().all()

        by_name = {v.field_name: v for v in values}
        assert by_name["BAD_FIELD"].is_error is True
        assert by_name["BAD_FIELD"].error_category == "missing_sheet"
        assert by_name["GOOD_FIELD"].is_error is False
        assert by_name["GOOD_FIELD"].error_category is None

    def test_error_category_not_set_for_non_errors(self, sync_db_session: Session):
        """error_category should be None even if field is in dict but value is not an error."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        extracted_data = {"FIELD_A": 100.0}
        # Providing error_categories for a non-error field should have no effect
        error_categories = {"FIELD_A": "formula_error"}

        ExtractedValueCRUD.bulk_insert(
            sync_db_session,
            run.id,
            extracted_data,
            {},
            "test_prop",
            error_categories=error_categories,
        )

        values = sync_db_session.execute(
            select(ExtractedValue).where(
                ExtractedValue.extraction_run_id == run.id
            )
        ).scalars().all()

        assert len(values) == 1
        assert values[0].is_error is False
        assert values[0].error_category is None


class TestExtractionTriggeredInChangeLog:
    """Tests for extraction_triggered field in FileChangeLog entries."""

    @pytest.mark.asyncio
    async def test_extraction_triggered_set_in_change_log(
        self, db_session: AsyncSession
    ):
        """_log_changes should set extraction_triggered and run_id on add/modify entries."""
        mock_client = AsyncMock()
        monitor = SharePointFileMonitor(db_session, mock_client)

        run_id = uuid4()
        changes = [
            FileChange(
                file_path="/sites/deals/DealA/UW.xlsb",
                file_name="UW.xlsb",
                change_type="added",
                deal_name="Deal A",
                old_modified_date=None,
                new_modified_date=datetime.now(UTC),
            ),
            FileChange(
                file_path="/sites/deals/DealB/UW.xlsb",
                file_name="UW.xlsb",
                change_type="deleted",
                deal_name="Deal B",
                old_modified_date=datetime.now(UTC) - timedelta(days=1),
                new_modified_date=None,
            ),
        ]

        await monitor._log_changes(
            changes,
            extraction_triggered=True,
            extraction_run_id=run_id,
        )

        logs = (
            await db_session.execute(
                select(FileChangeLog).order_by(FileChangeLog.file_path)
            )
        ).scalars().all()

        assert len(logs) == 2

        # Added file should have extraction_triggered=True
        added_log = next(l for l in logs if l.change_type == "added")
        assert added_log.extraction_triggered is True
        assert added_log.extraction_run_id == run_id

        # Deleted file should have extraction_triggered=False
        deleted_log = next(l for l in logs if l.change_type == "deleted")
        assert deleted_log.extraction_triggered is False
        assert deleted_log.extraction_run_id is None
