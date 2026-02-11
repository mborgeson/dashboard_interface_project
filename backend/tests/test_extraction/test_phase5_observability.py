"""
Phase 5 tests: Monitoring & Observability.

Tests cover:
- 5.1: Structured extraction metrics (RunMetrics, FileMetrics)
- 5.2: File metadata persisted on ExtractionRun

Run with: pytest tests/test_extraction/test_phase5_observability.py -v
"""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.extraction.common import process_files
from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.base import Base
from app.services.extraction.metrics import FileMetrics, RunMetrics

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
# Issue 5.1: Extraction Metrics
# ============================================================================


class TestRunMetrics:
    """Tests for the RunMetrics dataclass."""

    def test_record_completed_file(self):
        """Recording a completed file should update aggregated counts."""
        metrics = RunMetrics(files_total=3)
        metrics.record_file(
            FileMetrics(
                file_path="/tmp/a.xlsb",
                deal_name="A",
                status="completed",
                values_count=10,
            )
        )
        assert metrics.files_completed == 1
        assert metrics.total_values == 10
        assert metrics.files_failed == 0

    def test_record_failed_file(self):
        """Recording a failed file should update failure count."""
        metrics = RunMetrics(files_total=2)
        metrics.record_file(
            FileMetrics(
                file_path="/tmp/b.xlsb",
                deal_name="B",
                status="failed",
                error_count=1,
                error_categories={"parse_error": 1},
            )
        )
        assert metrics.files_failed == 1
        assert metrics.total_errors == 1
        assert metrics.error_categories == {"parse_error": 1}

    def test_record_skipped_file(self):
        """Recording a skipped file should update skip count."""
        metrics = RunMetrics(files_total=1)
        metrics.record_file(
            FileMetrics(
                file_path="/tmp/c.xlsb",
                deal_name="C",
                status="skipped",
            )
        )
        assert metrics.files_skipped == 1

    def test_to_metadata_structure(self):
        """to_metadata should return a serializable dict with expected keys."""
        metrics = RunMetrics(files_total=2)
        metrics.record_file(
            FileMetrics(
                file_path="/tmp/a.xlsb",
                deal_name="A",
                status="completed",
                values_count=5,
            )
        )
        metrics.record_file(
            FileMetrics(
                file_path="/tmp/b.xlsb",
                deal_name="B",
                status="failed",
                error_count=2,
            )
        )

        md = metrics.to_metadata()
        assert md["files_total"] == 2
        assert md["files_completed"] == 1
        assert md["files_failed"] == 1
        assert md["total_values"] == 5
        assert md["total_errors"] == 2
        assert "duration_seconds" in md
        assert "throughput_fpm" in md
        assert "/tmp/a.xlsb" in md["per_file"]
        assert md["per_file"]["/tmp/a.xlsb"]["status"] == "completed"
        assert md["per_file"]["/tmp/b.xlsb"]["status"] == "failed"

    def test_error_categories_aggregated(self):
        """Error categories should aggregate across files."""
        metrics = RunMetrics(files_total=3)
        metrics.record_file(
            FileMetrics(
                file_path="/tmp/a.xlsb",
                deal_name="A",
                status="failed",
                error_categories={"parse_error": 2},
            )
        )
        metrics.record_file(
            FileMetrics(
                file_path="/tmp/b.xlsb",
                deal_name="B",
                status="failed",
                error_categories={"parse_error": 1, "type_error": 3},
            )
        )
        assert metrics.error_categories == {"parse_error": 3, "type_error": 3}


# ============================================================================
# Issue 5.2: File Metadata Persisted
# ============================================================================


class TestFileMetadataPersistence:
    """Tests for file_metadata being saved on ExtractionRun."""

    def test_file_metadata_persisted_on_complete(self, sync_db_session: Session):
        """process_files should persist file_metadata on the run."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.return_value = {
            "PROPERTY_NAME": "Test Prop",
            "FIELD_A": 100.0,
        }

        files_to_process = [
            {"file_path": "/tmp/test.xlsb", "deal_name": "Test"},
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
        assert updated_run.file_metadata is not None
        assert updated_run.file_metadata["files_total"] == 1
        assert updated_run.file_metadata["files_completed"] == 1
        assert "per_file" in updated_run.file_metadata
        assert "/tmp/test.xlsb" in updated_run.file_metadata["per_file"]

    def test_metadata_includes_per_file_stats(self, sync_db_session: Session):
        """file_metadata should include per-file value counts."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        call_count = 0

        def mock_extract(path):
            nonlocal call_count
            call_count += 1
            return {
                "PROPERTY_NAME": f"Prop {call_count}",
                "FIELD_A": 1.0,
                "FIELD_B": "text",
            }

        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.side_effect = mock_extract

        files_to_process = [
            {"file_path": "/tmp/file1.xlsb", "deal_name": "Deal 1"},
            {"file_path": "/tmp/file2.xlsb", "deal_name": "Deal 2"},
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
        md = updated_run.file_metadata
        assert md["files_total"] == 2
        assert md["total_values"] == 6  # 2 files × 3 fields each
        # Each file has 3 values (PROPERTY_NAME, FIELD_A, FIELD_B)
        file1_meta = md["per_file"]["/tmp/file1.xlsb"]
        assert file1_meta["values_count"] == 3
        assert file1_meta["status"] == "completed"

    def test_metrics_emitted_on_completion(self, sync_db_session: Session):
        """Structured metrics should be emitted via structlog on completion."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.return_value = {
            "PROPERTY_NAME": "Prop",
            "FIELD_A": 1.0,
        }

        files_to_process = [
            {"file_path": "/tmp/test.xlsb", "deal_name": "Test"},
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
            patch("app.services.extraction.metrics.logger") as mock_metrics_logger,
        ):
            process_files(
                sync_db_session,
                run.id,
                files_to_process,
                {},
                ExtractionRunCRUD,
                ExtractedValueCRUD,
            )

        # Verify extraction_run_metrics was emitted
        mock_metrics_logger.info.assert_called()
        metrics_calls = [
            c
            for c in mock_metrics_logger.info.call_args_list
            if c.args and c.args[0] == "extraction_run_metrics"
        ]
        assert len(metrics_calls) == 1
        kwargs = metrics_calls[0].kwargs
        assert kwargs["files_completed"] == 1
        assert kwargs["total_values"] == 2  # PROPERTY_NAME + FIELD_A
