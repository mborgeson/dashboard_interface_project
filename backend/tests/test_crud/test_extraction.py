"""
Tests for ExtractionRun and ExtractedValue CRUD operations.

Tests cover:
- ExtractionRunCRUD.create() - Create extraction run
- ExtractionRunCRUD.get() - Get by ID
- ExtractionRunCRUD.get_latest() - Get most recent run
- ExtractionRunCRUD.get_running() - Get currently running extraction
- ExtractionRunCRUD.list_recent() - List recent extraction runs
- ExtractionRunCRUD.update_progress() - Update progress
- ExtractionRunCRUD.complete() - Mark complete
- ExtractionRunCRUD.fail() - Mark failed
- ExtractionRunCRUD.cancel() - Cancel run
- ExtractedValueCRUD.bulk_insert() - Bulk insert values
- ExtractedValueCRUD.get_by_property() - Get values for property
- ExtractedValueCRUD.get_property_summary() - Get property data as dict
- ExtractedValueCRUD.get_extraction_stats() - Get extraction statistics
- ExtractedValueCRUD.list_properties() - List properties

Run with: pytest tests/test_crud/test_extraction.py -v
"""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.base import Base
from app.models.extraction import ExtractedValue, ExtractionRun

# ============================================================================
# Sync Database Setup
# ============================================================================

# The extraction CRUD uses sync sessions, so we create a sync test database
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
    """Create a sync database session for extraction tests."""
    # Create all tables
    Base.metadata.create_all(bind=sync_test_engine)

    session = SyncTestSession()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=sync_test_engine)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def extraction_run(sync_db_session: Session) -> ExtractionRun:
    """Create a completed test extraction run."""
    run = ExtractionRun(
        id=uuid4(),
        status="completed",
        trigger_type="manual",
        files_discovered=10,
        files_processed=8,
        files_failed=2,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    sync_db_session.add(run)
    sync_db_session.commit()
    sync_db_session.refresh(run)
    return run


@pytest.fixture
def running_extraction(sync_db_session: Session) -> ExtractionRun:
    """Create a running extraction run."""
    run = ExtractionRun(
        id=uuid4(),
        status="running",
        trigger_type="scheduled",
        files_discovered=15,
        files_processed=5,
        files_failed=0,
        started_at=datetime.utcnow(),
    )
    sync_db_session.add(run)
    sync_db_session.commit()
    sync_db_session.refresh(run)
    return run


@pytest.fixture
def extracted_values(
    sync_db_session: Session, extraction_run: ExtractionRun
) -> list[ExtractedValue]:
    """Create test extracted values for a property."""
    values = []
    fields = [
        ("PROPERTY_NAME", "Test Property 123", None, None),
        ("TOTAL_UNITS", "100", 100.0, None),
        ("PURCHASE_PRICE", "5000000.00", 5000000.0, None),
        ("ACQUISITION_DATE", "2024-01-15", None, datetime(2024, 1, 15)),
    ]

    for field_name, text_val, num_val, date_val in fields:
        value = ExtractedValue(
            id=uuid4(),
            extraction_run_id=extraction_run.id,
            property_name="Test Property 123",
            field_name=field_name,
            field_category="General",
            sheet_name="Summary",
            cell_address=f"B{len(values)+1}",
            value_text=text_val,
            value_numeric=num_val,
            value_date=date_val,
            is_error=False,
            source_file="/path/to/file.xlsb",
        )
        values.append(value)
        sync_db_session.add(value)

    sync_db_session.commit()
    for v in values:
        sync_db_session.refresh(v)
    return values


# ============================================================================
# Test: ExtractionRunCRUD.create()
# ============================================================================


class TestExtractionRunCreate:
    """Tests for ExtractionRunCRUD.create()."""

    def test_create_manual_extraction(self, sync_db_session: Session) -> None:
        """Creates a manual extraction run with defaults."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        assert run.id is not None
        assert run.status == "running"
        assert run.trigger_type == "manual"
        assert run.files_discovered == 0
        assert run.files_processed == 0
        assert run.files_failed == 0
        assert run.started_at is not None
        assert run.completed_at is None

    def test_create_scheduled_extraction(self, sync_db_session: Session) -> None:
        """Creates a scheduled extraction run."""
        run = ExtractionRunCRUD.create(
            sync_db_session, trigger_type="scheduled", files_discovered=25
        )

        assert run.trigger_type == "scheduled"
        assert run.files_discovered == 25

    def test_create_extraction_with_files(self, sync_db_session: Session) -> None:
        """Creates extraction run with initial file count."""
        run = ExtractionRunCRUD.create(
            sync_db_session, trigger_type="manual", files_discovered=10
        )

        assert run.files_discovered == 10


# ============================================================================
# Test: ExtractionRunCRUD.get()
# ============================================================================


class TestExtractionRunGet:
    """Tests for ExtractionRunCRUD.get()."""

    def test_get_by_id(
        self, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Gets extraction run by ID."""
        found = ExtractionRunCRUD.get(sync_db_session, extraction_run.id)

        assert found is not None
        assert found.id == extraction_run.id
        assert found.status == "completed"

    def test_get_not_found(self, sync_db_session: Session) -> None:
        """Returns None for non-existent run ID."""
        fake_id = uuid4()
        found = ExtractionRunCRUD.get(sync_db_session, fake_id)

        assert found is None


# ============================================================================
# Test: ExtractionRunCRUD.get_latest()
# ============================================================================


class TestExtractionRunGetLatest:
    """Tests for ExtractionRunCRUD.get_latest()."""

    def test_get_latest_no_runs(self, sync_db_session: Session) -> None:
        """Returns None when no runs exist."""
        latest = ExtractionRunCRUD.get_latest(sync_db_session)

        assert latest is None

    def test_get_latest_single_run(
        self, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Returns the only run when one exists."""
        latest = ExtractionRunCRUD.get_latest(sync_db_session)

        assert latest is not None
        assert latest.id == extraction_run.id

    def test_get_latest_multiple_runs(self, sync_db_session: Session) -> None:
        """Returns most recent run when multiple exist."""
        # Create older run
        old_run = ExtractionRun(
            id=uuid4(),
            status="completed",
            trigger_type="manual",
            started_at=datetime(2024, 1, 1, 10, 0, 0),
        )
        sync_db_session.add(old_run)

        # Create newer run
        new_run = ExtractionRun(
            id=uuid4(),
            status="completed",
            trigger_type="manual",
            started_at=datetime(2024, 12, 15, 14, 30, 0),
        )
        sync_db_session.add(new_run)
        sync_db_session.commit()

        latest = ExtractionRunCRUD.get_latest(sync_db_session)

        assert latest is not None
        assert latest.id == new_run.id


# ============================================================================
# Test: ExtractionRunCRUD.get_running()
# ============================================================================


class TestExtractionRunGetRunning:
    """Tests for ExtractionRunCRUD.get_running()."""

    def test_get_running_none(self, sync_db_session: Session) -> None:
        """Returns None when no extraction is running."""
        running = ExtractionRunCRUD.get_running(sync_db_session)

        assert running is None

    def test_get_running_with_completed(
        self, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Returns None when only completed runs exist."""
        running = ExtractionRunCRUD.get_running(sync_db_session)

        assert running is None

    def test_get_running_with_active(
        self, sync_db_session: Session, running_extraction: ExtractionRun
    ) -> None:
        """Returns running extraction when one exists."""
        running = ExtractionRunCRUD.get_running(sync_db_session)

        assert running is not None
        assert running.id == running_extraction.id
        assert running.status == "running"


# ============================================================================
# Test: ExtractionRunCRUD.list_recent()
# ============================================================================


class TestExtractionRunListRecent:
    """Tests for ExtractionRunCRUD.list_recent()."""

    def test_list_recent_empty(self, sync_db_session: Session) -> None:
        """Returns empty list when no runs exist."""
        runs = ExtractionRunCRUD.list_recent(sync_db_session)

        assert runs == []

    def test_list_recent_with_runs(
        self, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Returns list of recent runs."""
        runs = ExtractionRunCRUD.list_recent(sync_db_session)

        assert len(runs) >= 1
        assert runs[0].id == extraction_run.id

    def test_list_recent_pagination(self, sync_db_session: Session) -> None:
        """Respects limit and offset parameters."""
        # Create 5 runs
        for i in range(5):
            run = ExtractionRun(
                id=uuid4(),
                status="completed",
                trigger_type="manual",
                files_discovered=i,
                started_at=datetime(2024, 1, i + 1, 10, 0, 0),
            )
            sync_db_session.add(run)
        sync_db_session.commit()

        # Get first 2
        first_batch = ExtractionRunCRUD.list_recent(sync_db_session, limit=2)
        assert len(first_batch) == 2

        # Get next 2 with offset
        second_batch = ExtractionRunCRUD.list_recent(sync_db_session, limit=2, offset=2)
        assert len(second_batch) == 2

        # Verify no overlap
        first_ids = {r.id for r in first_batch}
        second_ids = {r.id for r in second_batch}
        assert not first_ids.intersection(second_ids)


# ============================================================================
# Test: ExtractionRunCRUD.update_progress()
# ============================================================================


class TestExtractionRunUpdateProgress:
    """Tests for ExtractionRunCRUD.update_progress()."""

    def test_update_progress(
        self, sync_db_session: Session, running_extraction: ExtractionRun
    ) -> None:
        """Updates progress counts."""
        updated = ExtractionRunCRUD.update_progress(
            sync_db_session,
            running_extraction.id,
            files_processed=10,
            files_failed=2,
        )

        assert updated is not None
        assert updated.files_processed == 10
        assert updated.files_failed == 2

    def test_update_progress_not_found(self, sync_db_session: Session) -> None:
        """Returns None for non-existent run."""
        fake_id = uuid4()
        updated = ExtractionRunCRUD.update_progress(
            sync_db_session, fake_id, files_processed=5
        )

        assert updated is None


# ============================================================================
# Test: ExtractionRunCRUD.complete()
# ============================================================================


class TestExtractionRunComplete:
    """Tests for ExtractionRunCRUD.complete()."""

    def test_complete_extraction(
        self, sync_db_session: Session, running_extraction: ExtractionRun
    ) -> None:
        """Marks extraction as completed."""
        completed = ExtractionRunCRUD.complete(
            sync_db_session,
            running_extraction.id,
            files_processed=15,
            files_failed=0,
        )

        assert completed is not None
        assert completed.status == "completed"
        assert completed.completed_at is not None
        assert completed.files_processed == 15
        assert completed.files_failed == 0

    def test_complete_with_errors(
        self, sync_db_session: Session, running_extraction: ExtractionRun
    ) -> None:
        """Marks extraction as completed with error summary."""
        error_summary = {
            "failed_files": ["file1.xlsb", "file2.xlsb"],
            "error_types": {"parse_error": 2},
        }

        completed = ExtractionRunCRUD.complete(
            sync_db_session,
            running_extraction.id,
            files_processed=13,
            files_failed=2,
            error_summary=error_summary,
        )

        assert completed is not None
        assert completed.error_summary == error_summary

    def test_complete_not_found(self, sync_db_session: Session) -> None:
        """Returns None for non-existent run."""
        fake_id = uuid4()
        completed = ExtractionRunCRUD.complete(
            sync_db_session, fake_id, files_processed=0, files_failed=0
        )

        assert completed is None


# ============================================================================
# Test: ExtractionRunCRUD.fail()
# ============================================================================


class TestExtractionRunFail:
    """Tests for ExtractionRunCRUD.fail()."""

    def test_fail_extraction(
        self, sync_db_session: Session, running_extraction: ExtractionRun
    ) -> None:
        """Marks extraction as failed."""
        failed = ExtractionRunCRUD.fail(sync_db_session, running_extraction.id)

        assert failed is not None
        assert failed.status == "failed"
        assert failed.completed_at is not None

    def test_fail_with_error_summary(
        self, sync_db_session: Session, running_extraction: ExtractionRun
    ) -> None:
        """Marks extraction as failed with error summary."""
        error_summary = {"reason": "Connection timeout", "code": "TIMEOUT"}

        failed = ExtractionRunCRUD.fail(
            sync_db_session, running_extraction.id, error_summary=error_summary
        )

        assert failed is not None
        assert failed.error_summary == error_summary


# ============================================================================
# Test: ExtractionRunCRUD.cancel()
# ============================================================================


class TestExtractionRunCancel:
    """Tests for ExtractionRunCRUD.cancel()."""

    def test_cancel_running_extraction(
        self, sync_db_session: Session, running_extraction: ExtractionRun
    ) -> None:
        """Cancels a running extraction."""
        cancelled = ExtractionRunCRUD.cancel(sync_db_session, running_extraction.id)

        assert cancelled is not None
        assert cancelled.status == "cancelled"
        assert cancelled.completed_at is not None

    def test_cancel_completed_extraction(
        self, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Does not cancel a completed extraction."""
        cancelled = ExtractionRunCRUD.cancel(sync_db_session, extraction_run.id)

        # Should return the run but not change status since it's not running
        assert cancelled is not None
        assert cancelled.status == "completed"  # Status unchanged

    def test_cancel_not_found(self, sync_db_session: Session) -> None:
        """Returns None for non-existent run."""
        fake_id = uuid4()
        cancelled = ExtractionRunCRUD.cancel(sync_db_session, fake_id)

        assert cancelled is None


# ============================================================================
# Test: ExtractedValueCRUD.bulk_insert()
# ============================================================================


class TestExtractedValueBulkInsert:
    """Tests for ExtractedValueCRUD.bulk_insert()."""

    def test_bulk_insert_basic(
        self, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Bulk inserts extracted values."""
        extracted_data = {
            "PROPERTY_NAME": "New Property",
            "TOTAL_UNITS": 150,
            "PURCHASE_PRICE": 7500000.0,
        }

        # Create mock mappings
        mock_mapping = MagicMock()
        mock_mapping.category = "General"
        mock_mapping.sheet_name = "Summary"
        mock_mapping.cell_address = "B5"

        mappings = {
            "PROPERTY_NAME": mock_mapping,
            "TOTAL_UNITS": mock_mapping,
            "PURCHASE_PRICE": mock_mapping,
        }

        count = ExtractedValueCRUD.bulk_insert(
            sync_db_session,
            extraction_run_id=extraction_run.id,
            extracted_data=extracted_data,
            mappings=mappings,
            property_name="New Property",
            source_file="/path/to/newfile.xlsb",
        )

        assert count == 3

        # Verify values were inserted
        values = ExtractedValueCRUD.get_by_property(
            sync_db_session, "New Property", extraction_run.id
        )
        assert len(values) == 3

    def test_bulk_insert_skips_metadata_fields(
        self, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Skips fields starting with underscore."""
        extracted_data = {
            "_metadata": "should be skipped",
            "_version": 1,
            "PROPERTY_NAME": "Test Property",
        }

        count = ExtractedValueCRUD.bulk_insert(
            sync_db_session,
            extraction_run_id=extraction_run.id,
            extracted_data=extracted_data,
            mappings={},
            property_name="Test Property",
        )

        assert count == 1  # Only PROPERTY_NAME

    def test_bulk_insert_handles_none_values(
        self, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Handles None values gracefully."""
        extracted_data = {
            "PROPERTY_NAME": "Test",
            "MISSING_VALUE": None,
        }

        count = ExtractedValueCRUD.bulk_insert(
            sync_db_session,
            extraction_run_id=extraction_run.id,
            extracted_data=extracted_data,
            mappings={},
            property_name="Test",
        )

        assert count == 2

        # Verify error flag is set for None value
        values = ExtractedValueCRUD.get_by_property(
            sync_db_session, "Test", extraction_run.id
        )
        missing_val = next(v for v in values if v.field_name == "MISSING_VALUE")
        assert missing_val.is_error is True

    def test_bulk_insert_handles_datetime(
        self, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Handles datetime values correctly."""
        test_date = datetime(2024, 6, 15, 10, 30, 0)
        extracted_data = {
            "ACQUISITION_DATE": test_date,
        }

        count = ExtractedValueCRUD.bulk_insert(
            sync_db_session,
            extraction_run_id=extraction_run.id,
            extracted_data=extracted_data,
            mappings={},
            property_name="DateTest",
        )

        assert count == 1

        values = ExtractedValueCRUD.get_by_property(
            sync_db_session, "DateTest", extraction_run.id
        )
        assert len(values) == 1
        # value_date is a Date column, so only the date portion is stored
        from datetime import date

        assert values[0].value_date == date(2024, 6, 15)


# ============================================================================
# Test: ExtractedValueCRUD.get_by_property()
# ============================================================================


class TestExtractedValueGetByProperty:
    """Tests for ExtractedValueCRUD.get_by_property()."""

    def test_get_by_property_empty(self, sync_db_session: Session) -> None:
        """Returns empty list for non-existent property."""
        values = ExtractedValueCRUD.get_by_property(sync_db_session, "NonExistent")

        assert values == []

    def test_get_by_property_with_data(
        self,
        sync_db_session: Session,
        extraction_run: ExtractionRun,
        extracted_values: list[ExtractedValue],
    ) -> None:
        """Returns values for existing property."""
        values = ExtractedValueCRUD.get_by_property(
            sync_db_session, "Test Property 123"
        )

        assert len(values) == 4
        for v in values:
            assert v.property_name == "Test Property 123"

    def test_get_by_property_with_run_id(
        self,
        sync_db_session: Session,
        extraction_run: ExtractionRun,
        extracted_values: list[ExtractedValue],
    ) -> None:
        """Filters by extraction run ID."""
        values = ExtractedValueCRUD.get_by_property(
            sync_db_session, "Test Property 123", extraction_run.id
        )

        assert len(values) == 4
        for v in values:
            assert v.extraction_run_id == extraction_run.id


# ============================================================================
# Test: ExtractedValueCRUD.get_property_summary()
# ============================================================================


class TestExtractedValueGetPropertySummary:
    """Tests for ExtractedValueCRUD.get_property_summary()."""

    def test_get_property_summary_empty(self, sync_db_session: Session) -> None:
        """Returns empty dict for non-existent property."""
        summary = ExtractedValueCRUD.get_property_summary(
            sync_db_session, "NonExistent"
        )

        assert summary == {}

    def test_get_property_summary_with_data(
        self,
        sync_db_session: Session,
        extraction_run: ExtractionRun,
        extracted_values: list[ExtractedValue],
    ) -> None:
        """Returns field name to value mapping."""
        summary = ExtractedValueCRUD.get_property_summary(
            sync_db_session, "Test Property 123"
        )

        assert "PROPERTY_NAME" in summary
        assert "TOTAL_UNITS" in summary
        assert "PURCHASE_PRICE" in summary


# ============================================================================
# Test: ExtractedValueCRUD.get_extraction_stats()
# ============================================================================


class TestExtractedValueGetExtractionStats:
    """Tests for ExtractedValueCRUD.get_extraction_stats()."""

    def test_get_extraction_stats_empty(
        self, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Returns zero stats for empty extraction."""
        # Use the extraction_run fixture but don't add values
        stats = ExtractedValueCRUD.get_extraction_stats(
            sync_db_session, extraction_run.id
        )

        assert stats["total_values"] == 0
        assert stats["error_count"] == 0
        assert stats["success_count"] == 0
        assert stats["success_rate"] == 0
        assert stats["unique_properties"] == 0

    def test_get_extraction_stats_with_data(
        self,
        sync_db_session: Session,
        extraction_run: ExtractionRun,
        extracted_values: list[ExtractedValue],
    ) -> None:
        """Returns accurate stats with data."""
        stats = ExtractedValueCRUD.get_extraction_stats(
            sync_db_session, extraction_run.id
        )

        assert stats["total_values"] == 4
        assert stats["error_count"] == 0
        assert stats["success_count"] == 4
        assert stats["success_rate"] == 100.0
        assert stats["unique_properties"] == 1


# ============================================================================
# Test: ExtractedValueCRUD.list_properties()
# ============================================================================


class TestExtractedValueListProperties:
    """Tests for ExtractedValueCRUD.list_properties()."""

    def test_list_properties_empty(self, sync_db_session: Session) -> None:
        """Returns empty list when no properties exist."""
        properties = ExtractedValueCRUD.list_properties(sync_db_session)

        assert properties == []

    def test_list_properties_with_data(
        self,
        sync_db_session: Session,
        extraction_run: ExtractionRun,
        extracted_values: list[ExtractedValue],
    ) -> None:
        """Returns list of unique property names."""
        properties = ExtractedValueCRUD.list_properties(sync_db_session)

        assert "Test Property 123" in properties

    def test_list_properties_with_run_id(
        self,
        sync_db_session: Session,
        extraction_run: ExtractionRun,
        extracted_values: list[ExtractedValue],
    ) -> None:
        """Filters by extraction run ID."""
        properties = ExtractedValueCRUD.list_properties(
            sync_db_session, extraction_run.id
        )

        assert len(properties) == 1
        assert properties[0] == "Test Property 123"

    def test_list_properties_multiple(self, sync_db_session: Session) -> None:
        """Returns multiple unique property names."""
        # Create extraction run
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        # Add values for multiple properties
        for prop_name in ["Property A", "Property B", "Property C"]:
            value = ExtractedValue(
                id=uuid4(),
                extraction_run_id=run.id,
                property_name=prop_name,
                field_name="FIELD_1",
                value_text="test",
                is_error=False,
            )
            sync_db_session.add(value)
        sync_db_session.commit()

        properties = ExtractedValueCRUD.list_properties(sync_db_session, run.id)

        assert len(properties) == 3
        assert "Property A" in properties
        assert "Property B" in properties
        assert "Property C" in properties


# ============================================================================
# Test: ExtractionRun Properties
# ============================================================================


class TestExtractionRunProperties:
    """Tests for ExtractionRun model properties."""

    def test_duration_seconds_calculated(self, sync_db_session: Session) -> None:
        """Calculates duration when completed."""
        run = ExtractionRun(
            id=uuid4(),
            status="completed",
            trigger_type="manual",
            started_at=datetime(2024, 1, 1, 10, 0, 0),
            completed_at=datetime(2024, 1, 1, 10, 5, 30),
        )
        sync_db_session.add(run)
        sync_db_session.commit()

        assert run.duration_seconds == 330.0  # 5 minutes 30 seconds

    def test_duration_seconds_none_when_running(self, sync_db_session: Session) -> None:
        """Returns None when not completed."""
        run = ExtractionRun(
            id=uuid4(),
            status="running",
            trigger_type="manual",
            started_at=datetime.utcnow(),
        )
        sync_db_session.add(run)
        sync_db_session.commit()

        assert run.duration_seconds is None

    def test_success_rate_calculated(self, sync_db_session: Session) -> None:
        """Calculates success rate correctly."""
        run = ExtractionRun(
            id=uuid4(),
            status="completed",
            trigger_type="manual",
            files_processed=8,
            files_failed=2,
        )
        sync_db_session.add(run)
        sync_db_session.commit()

        assert run.success_rate == 80.0  # 8 / (8+2) * 100

    def test_success_rate_none_when_empty(self, sync_db_session: Session) -> None:
        """Returns None when no files processed."""
        run = ExtractionRun(
            id=uuid4(),
            status="completed",
            trigger_type="manual",
            files_processed=0,
            files_failed=0,
        )
        sync_db_session.add(run)
        sync_db_session.commit()

        assert run.success_rate is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
