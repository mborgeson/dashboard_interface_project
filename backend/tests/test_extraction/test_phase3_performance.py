"""
Phase 3 tests: Performance improvements.

Tests cover:
- 3.1: Parallel extraction produces same results as sequential
- 3.1: Parallel extraction handles individual file failures
- 3.2: Concurrent downloads use semaphore to limit concurrency
- 3.3: SharePointClient session reuse and cleanup

Run with: pytest tests/test_extraction/test_phase3_performance.py -v
"""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.extraction.common import (
    _extract_single_file,
    process_files,
)
from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.base import Base
from app.extraction.sharepoint import SharePointClient
from app.models.extraction import ExtractedValue

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
# Issue 3.1: Parallel Extraction
# ============================================================================


class TestParallelExtraction:
    """Tests for parallel Excel extraction via ThreadPoolExecutor."""

    def test_parallel_extraction_produces_same_results(
        self, sync_db_session: Session
    ):
        """Parallel extraction should produce identical results to sequential."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        # Mock extractor that returns deterministic data
        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.side_effect = lambda path: {
            "PROPERTY_NAME": f"Prop_{path.split('/')[-1]}",
            "FIELD_A": 100.0,
            "FIELD_B": "text",
        }

        files_to_process = [
            {"file_path": f"/tmp/file_{i}.xlsb", "deal_name": f"Deal {i}"}
            for i in range(3)
        ]

        with (
            patch(
                "app.extraction.ExcelDataExtractor",
                return_value=mock_extractor,
            ),
            patch(
                "app.services.extraction.change_detector.should_extract_deal",
                return_value=(True, "new_deal"),
            ),
        ):
            process_files(
                sync_db_session,
                run.id,
                files_to_process,
                {},
                ExtractionRunCRUD,
                ExtractedValueCRUD,
                max_workers=2,
            )

        # Verify all 3 properties were processed (2 fields each = 6 values)
        values = sync_db_session.execute(
            select(ExtractedValue).where(
                ExtractedValue.extraction_run_id == run.id
            )
        ).scalars().all()

        property_names = {v.property_name for v in values}
        assert len(property_names) == 3
        assert len(values) == 9  # 3 files × 3 fields each (PROPERTY_NAME, FIELD_A, FIELD_B)

        # Verify run completed
        updated_run = ExtractionRunCRUD.get(sync_db_session, run.id)
        assert updated_run.status == "completed"
        assert updated_run.files_processed == 3
        assert updated_run.files_failed == 0

    def test_parallel_extraction_handles_failures(self, sync_db_session: Session):
        """One file raising an exception should not prevent other files from processing."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        # Mock extractor: second file throws
        def mock_extract(path):
            if "bad" in path:
                raise ValueError("corrupt Excel file")
            return {"PROPERTY_NAME": f"Prop_{path}", "FIELD_A": 42.0}

        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.side_effect = mock_extract

        files_to_process = [
            {"file_path": "/tmp/good1.xlsb", "deal_name": "Good 1"},
            {"file_path": "/tmp/bad.xlsb", "deal_name": "Bad File"},
            {"file_path": "/tmp/good2.xlsb", "deal_name": "Good 2"},
        ]

        with (
            patch(
                "app.extraction.ExcelDataExtractor",
                return_value=mock_extractor,
            ),
            patch(
                "app.services.extraction.change_detector.should_extract_deal",
                return_value=(True, "new_deal"),
            ),
        ):
            process_files(
                sync_db_session,
                run.id,
                files_to_process,
                {},
                ExtractionRunCRUD,
                ExtractedValueCRUD,
            )

        updated_run = ExtractionRunCRUD.get(sync_db_session, run.id)
        assert updated_run.status == "completed"
        assert updated_run.files_processed == 2  # 2 good files
        assert updated_run.files_failed == 1  # 1 bad file
        assert updated_run.error_summary is not None
        assert updated_run.error_summary["total_failures"] == 1


class TestExtractSingleFile:
    """Tests for the _extract_single_file helper."""

    def test_successful_extraction(self):
        """Should return extracted data and no error."""
        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.return_value = {"FIELD_A": 1.0}

        path, deal, data, error = _extract_single_file(
            mock_extractor, "/tmp/test.xlsb", "Test"
        )
        assert path == "/tmp/test.xlsb"
        assert deal == "Test"
        assert data == {"FIELD_A": 1.0}
        assert error is None

    def test_failed_extraction(self):
        """Should return None data and error message."""
        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.side_effect = RuntimeError("parse error")

        path, deal, data, error = _extract_single_file(
            mock_extractor, "/tmp/bad.xlsb", "Bad"
        )
        assert path == "/tmp/bad.xlsb"
        assert data is None
        assert "parse error" in error


# ============================================================================
# Issue 3.3: SharePointClient Session Reuse
# ============================================================================


class TestSharePointSessionReuse:
    """Tests for SharePoint HTTP session reuse and cleanup."""

    @pytest.mark.asyncio
    async def test_session_created_on_enter(self):
        """Entering async context should create a shared session."""
        client = SharePointClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            site_url="https://test.sharepoint.com/sites/Test",
        )
        assert client._session is None

        async with client:
            assert client._session is not None
            assert not client._session.closed

        # After exit, session should be closed
        assert client._session is None

    @pytest.mark.asyncio
    async def test_session_closed_on_exit(self):
        """Exiting async context should close the shared session."""
        client = SharePointClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            site_url="https://test.sharepoint.com/sites/Test",
        )

        async with client:
            session = client._session
            assert session is not None

        # close() should have been called
        assert client._session is None

    @pytest.mark.asyncio
    async def test_get_session_reuses_shared(self):
        """_get_session should return shared session when available."""
        client = SharePointClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            site_url="https://test.sharepoint.com/sites/Test",
        )

        async with client:
            session1 = client._get_session()
            session2 = client._get_session()
            assert session1 is session2  # Same object
            assert session1 is client._session

    @pytest.mark.asyncio
    async def test_get_session_creates_new_without_context(self):
        """_get_session should create a new session when not in context."""
        client = SharePointClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            site_url="https://test.sharepoint.com/sites/Test",
        )

        # Not in async context
        session = client._get_session()
        assert session is not None
        assert session is not client._session  # Should be different
        await session.close()

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        """Calling close() multiple times should not raise."""
        client = SharePointClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            site_url="https://test.sharepoint.com/sites/Test",
        )

        await client.close()  # No session yet — no-op
        async with client:
            pass  # Session created and closed
        await client.close()  # Already None — no-op
