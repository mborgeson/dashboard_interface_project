"""
Phase 4 tests: Architectural improvements.

Tests cover:
- 4.2: Property name collision detection (logging)
- 4.3: Per-file status tracking and resume support
- 4.4: MarketDataScheduler wired in lifespan

Run with: pytest tests/test_extraction/test_phase4_architecture.py -v
"""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.extraction.common import process_files
from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.base import Base
from app.models.extraction import ExtractedValue, ExtractionRun

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
# Issue 4.2: Property Name Collision Logging
# ============================================================================


class TestPropertyCollisionLogging:
    """Tests for property name collision detection and logging."""

    def test_collision_logged_when_two_files_same_property(
        self, sync_db_session: Session
    ):
        """Two files mapping to the same property_name should log a warning."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        # Both files extract to the same PROPERTY_NAME
        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.return_value = {
            "PROPERTY_NAME": "Same Property",
            "FIELD_A": 100.0,
        }

        files_to_process = [
            {"file_path": "/tmp/file_a.xlsb", "deal_name": "Deal A"},
            {"file_path": "/tmp/file_b.xlsb", "deal_name": "Deal B"},
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
            patch("app.api.v1.endpoints.extraction.common.logger") as mock_logger,
        ):
            process_files(
                sync_db_session,
                run.id,
                files_to_process,
                {},
                ExtractionRunCRUD,
                ExtractedValueCRUD,
            )

        # Verify a collision warning was logged
        mock_logger.warning.assert_called()
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "property_name_collision"
        ]
        assert len(warning_calls) == 1

    def test_no_collision_when_different_properties(self, sync_db_session: Session):
        """Different property names should not trigger a collision warning."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        call_count = 0

        def mock_extract(path):
            nonlocal call_count
            call_count += 1
            return {
                "PROPERTY_NAME": f"Unique Prop {call_count}",
                "FIELD_A": 100.0,
            }

        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.side_effect = mock_extract

        files_to_process = [
            {"file_path": "/tmp/file_a.xlsb", "deal_name": "Deal A"},
            {"file_path": "/tmp/file_b.xlsb", "deal_name": "Deal B"},
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
            patch("app.api.v1.endpoints.extraction.common.logger") as mock_logger,
        ):
            process_files(
                sync_db_session,
                run.id,
                files_to_process,
                {},
                ExtractionRunCRUD,
                ExtractedValueCRUD,
            )

        # No collision warnings
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "property_name_collision"
        ]
        assert len(warning_calls) == 0


# ============================================================================
# Issue 4.3: Per-File Status Tracking and Resume
# ============================================================================


class TestPerFileStatus:
    """Tests for per-file status tracking in extraction runs."""

    def test_per_file_status_tracked(self, sync_db_session: Session):
        """process_files should record per-file status on the run."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        def mock_extract(path):
            if "bad" in path:
                raise ValueError("corrupt file")
            return {"PROPERTY_NAME": f"Prop_{path}", "FIELD_A": 1.0}

        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.side_effect = mock_extract

        files_to_process = [
            {"file_path": "/tmp/good.xlsb", "deal_name": "Good"},
            {"file_path": "/tmp/bad.xlsb", "deal_name": "Bad"},
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
        assert updated_run.per_file_status is not None
        assert updated_run.per_file_status["/tmp/good.xlsb"]["status"] == "completed"
        assert updated_run.per_file_status["/tmp/bad.xlsb"]["status"] == "failed"
        assert "corrupt file" in updated_run.per_file_status["/tmp/bad.xlsb"]["error"]

    def test_skipped_files_tracked(self, sync_db_session: Session):
        """Files skipped by change detection should be recorded as skipped."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.return_value = {
            "PROPERTY_NAME": "Prop",
            "FIELD_A": 1.0,
        }

        files_to_process = [
            {"file_path": "/tmp/unchanged.xlsb", "deal_name": "Unchanged"},
        ]

        with (
            patch(
                "app.extraction.ExcelDataExtractor",
                return_value=mock_extractor,
            ),
            patch(
                "app.services.extraction.change_detector.should_extract_deal",
                return_value=(False, "no_changes"),
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
        assert updated_run.per_file_status is not None
        assert updated_run.per_file_status["/tmp/unchanged.xlsb"]["status"] == "skipped"

    def test_resume_skips_completed_files(self, sync_db_session: Session):
        """Resume should skip files already completed in a previous run."""
        # Create a "previous" run with per_file_status
        prev_run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")
        prev_run.per_file_status = {
            "/tmp/already_done.xlsb": {"status": "completed"},
            "/tmp/previously_failed.xlsb": {"status": "failed", "error": "old error"},
        }
        prev_run.status = "completed"
        prev_run.completed_at = datetime.now(UTC)
        sync_db_session.commit()

        # Create a new run for resume
        new_run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.return_value = {
            "PROPERTY_NAME": "Retry Prop",
            "FIELD_A": 42.0,
        }

        files_to_process = [
            {"file_path": "/tmp/already_done.xlsb", "deal_name": "Already Done"},
            {"file_path": "/tmp/previously_failed.xlsb", "deal_name": "Retry"},
            {"file_path": "/tmp/new_file.xlsb", "deal_name": "New"},
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
                new_run.id,
                files_to_process,
                {},
                ExtractionRunCRUD,
                ExtractedValueCRUD,
                resume_run_id=prev_run.id,
            )

        # Only 2 files processed (already_done was skipped)
        updated_run = ExtractionRunCRUD.get(sync_db_session, new_run.id)
        assert updated_run.files_processed == 2
        assert updated_run.per_file_status is not None
        # already_done should NOT be in per_file_status (was filtered out)
        assert "/tmp/already_done.xlsb" not in updated_run.per_file_status
        # previously_failed should be retried and completed
        assert (
            updated_run.per_file_status["/tmp/previously_failed.xlsb"]["status"]
            == "completed"
        )
        assert (
            updated_run.per_file_status["/tmp/new_file.xlsb"]["status"] == "completed"
        )

        # Verify extractor was called only for the 2 non-skipped files
        assert mock_extractor.extract_from_file.call_count == 2


# ============================================================================
# Issue 4.4: MarketDataScheduler in Lifespan
# ============================================================================


class TestMarketDataSchedulerWiring:
    """Tests for MarketDataScheduler initialization in app lifespan."""

    @pytest.mark.asyncio
    async def test_market_scheduler_starts_in_lifespan(self):
        """MarketDataScheduler.start() should be called during app startup."""
        with (
            patch("app.main.get_extraction_scheduler") as mock_extraction,
            patch("app.main.get_monitor_scheduler") as mock_monitor,
            patch("app.main.MarketDataScheduler") as MockMarketScheduler,
            patch("app.main.get_metrics_manager") as mock_metrics,
            patch("app.main.setup_logging"),
        ):
            # Configure mocks
            mock_extraction.return_value = AsyncMock()
            mock_monitor.return_value = AsyncMock()
            mock_metrics.return_value = MagicMock()

            mock_market_instance = AsyncMock()
            MockMarketScheduler.return_value = mock_market_instance

            from app.main import app, lifespan

            async with lifespan(app):
                # During startup, MarketDataScheduler.start() should have been called
                mock_market_instance.start.assert_awaited_once()

            # During shutdown, stop() should have been called
            mock_market_instance.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_market_scheduler_stops_in_lifespan(self):
        """MarketDataScheduler.stop() should be called during app shutdown."""
        with (
            patch("app.main.get_extraction_scheduler") as mock_extraction,
            patch("app.main.get_monitor_scheduler") as mock_monitor,
            patch("app.main.MarketDataScheduler") as MockMarketScheduler,
            patch("app.main.get_metrics_manager") as mock_metrics,
            patch("app.main.setup_logging"),
        ):
            mock_extraction.return_value = AsyncMock()
            mock_monitor.return_value = AsyncMock()
            mock_metrics.return_value = MagicMock()

            mock_market_instance = AsyncMock()
            MockMarketScheduler.return_value = mock_market_instance

            from app.main import app, lifespan

            async with lifespan(app):
                pass

            # After exiting the context, stop() should have been called
            mock_market_instance.stop.assert_awaited_once()
