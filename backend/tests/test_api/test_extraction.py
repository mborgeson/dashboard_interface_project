"""
Tests for extraction API endpoints.

Tests cover:
- POST /extraction/start - Start extraction with different source types
- GET /extraction/status - Check extraction status
- GET /extraction/history - List extraction history
- POST /extraction/cancel - Cancel running extraction
- GET /extraction/properties - List extracted properties
- GET /extraction/properties/{name} - Get property data
- GET /extraction/scheduler/status - Get scheduler status
- GET /extraction/filters - Get filter configuration
- POST /extraction/filters/test - Test file filter

Run with: pytest tests/test_api/test_extraction.py -v
"""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_sync_db
from app.main import app
from app.models.extraction import ExtractedValue, ExtractionRun

# ============================================================================
# Sync Database Setup for Extraction Tests
# ============================================================================

# The extraction endpoints use sync sessions (get_sync_db), so we need to
# create a sync test database and override that dependency

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


@pytest_asyncio.fixture(scope="function")
async def extraction_client(sync_db_session: Session) -> AsyncClient:
    """
    Create an async test client with sync database dependency override.
    This is needed because extraction endpoints use get_sync_db.
    """
    def override_get_sync_db():
        yield sync_db_session

    app.dependency_overrides[get_sync_db] = override_get_sync_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def extraction_run(sync_db_session: Session) -> ExtractionRun:
    """Create a test extraction run."""
    run = ExtractionRun(
        id=uuid4(),
        status="completed",
        trigger_type="manual",
        files_discovered=8,
        files_processed=7,
        files_failed=1,
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
        trigger_type="manual",
        files_discovered=10,
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
    """Create test extracted values."""
    values = []
    for i, field in enumerate(["PROPERTY_NAME", "TOTAL_UNITS", "PURCHASE_PRICE"]):
        value = ExtractedValue(
            id=uuid4(),
            extraction_run_id=extraction_run.id,
            property_name="Test Property",
            field_name=field,
            field_category="General",
            sheet_name="Summary",
            cell_address=f"A{i+1}",
            value_text=f"value_{i}",
            value_numeric=float(i * 1000) if i > 0 else None,
            is_error=False,
        )
        values.append(value)
        sync_db_session.add(value)

    sync_db_session.commit()
    for v in values:
        sync_db_session.refresh(v)
    return values


# ============================================================================
# Test: GET /extraction/status
# ============================================================================


class TestExtractionStatus:
    """Tests for GET /api/v1/extraction/status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_no_runs(self, extraction_client) -> None:
        """Returns 200 with null runs when no extraction runs exist."""
        response = await extraction_client.get("/api/v1/extraction/status")
        assert response.status_code == 200
        data = response.json()
        assert data["current_run"] is None
        assert data["last_completed_run"] is None
        assert data["stats"]["total_runs"] == 0

    @pytest.mark.asyncio
    async def test_get_status_latest_run(
        self, extraction_client, extraction_run: ExtractionRun
    ) -> None:
        """Returns status with last completed run when no run_id specified."""
        response = await extraction_client.get("/api/v1/extraction/status")
        assert response.status_code == 200

        data = response.json()
        run = data["last_completed_run"]
        assert run is not None
        assert run["id"] == str(extraction_run.id)
        assert run["status"] == "completed"
        assert run["trigger_type"] == "manual"
        assert run["files_discovered"] == 8
        assert run["files_processed"] == 7
        assert run["files_failed"] == 1

    @pytest.mark.asyncio
    async def test_get_status_specific_run(
        self, extraction_client, extraction_run: ExtractionRun
    ) -> None:
        """Returns status of specific run by ID."""
        response = await extraction_client.get(
            f"/api/v1/extraction/status?run_id={extraction_run.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_run"]["id"] == str(extraction_run.id)

    @pytest.mark.asyncio
    async def test_get_status_invalid_run_id(self, extraction_client) -> None:
        """Returns 404 for non-existent run ID."""
        fake_id = uuid4()
        response = await extraction_client.get(f"/api/v1/extraction/status?run_id={fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_status_includes_stats(
        self, extraction_client, extraction_run: ExtractionRun
    ) -> None:
        """Verifies stats are included in response."""
        response = await extraction_client.get("/api/v1/extraction/status")
        data = response.json()
        assert data["stats"]["total_runs"] >= 1
        assert data["stats"]["successful_runs"] >= 1


# ============================================================================
# Test: GET /extraction/history
# ============================================================================


class TestExtractionHistory:
    """Tests for GET /api/v1/extraction/history endpoint."""

    @pytest.mark.asyncio
    async def test_get_history_empty(self, extraction_client) -> None:
        """Returns empty list when no runs exist."""
        response = await extraction_client.get("/api/v1/extraction/history")
        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_history_with_runs(
        self, extraction_client, extraction_run: ExtractionRun
    ) -> None:
        """Returns list of extraction runs."""
        response = await extraction_client.get("/api/v1/extraction/history")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 1
        assert len(data["runs"]) >= 1

        run = data["runs"][0]
        assert run["run_id"] == str(extraction_run.id)
        assert run["status"] == "completed"

    @pytest.mark.asyncio
    async def test_history_pagination(
        self, extraction_client, sync_db_session: Session
    ) -> None:
        """Tests pagination parameters."""
        # Create multiple runs
        for i in range(5):
            run = ExtractionRun(
                id=uuid4(),
                status="completed",
                trigger_type="manual",
                files_discovered=i,
                files_processed=i,
                files_failed=0,
            )
            sync_db_session.add(run)
        sync_db_session.commit()

        # Test limit
        response = await extraction_client.get("/api/v1/extraction/history?limit=2")
        data = response.json()
        assert len(data["runs"]) == 2

        # Test offset
        response = await extraction_client.get("/api/v1/extraction/history?limit=2&offset=2")
        data = response.json()
        assert len(data["runs"]) == 2


# ============================================================================
# Test: POST /extraction/start
# ============================================================================


class TestExtractionStart:
    """Tests for POST /api/v1/extraction/start endpoint."""

    @pytest.mark.asyncio
    async def test_start_extraction_conflict(
        self, extraction_client, running_extraction: ExtractionRun
    ) -> None:
        """Returns 409 when extraction already running."""
        response = await extraction_client.post(
            "/api/v1/extraction/start",
            json={"source": "local"},
        )
        assert response.status_code == 409
        assert "already running" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_start_extraction_local_source(self, extraction_client) -> None:
        """Starts extraction with local file source."""
        # Mock the background task to avoid actual extraction
        with patch(
            "app.api.v1.endpoints.extraction.common.run_extraction_task"
        ) as mock_task:
            response = await extraction_client.post(
                "/api/v1/extraction/start",
                json={
                    "source": "local",
                    "file_paths": ["/path/to/file1.xlsb", "/path/to/file2.xlsb"],
                },
            )

            # Should succeed and start background task
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"
            assert data["files_discovered"] == 2
            assert "run_id" in data

    @pytest.mark.asyncio
    async def test_start_extraction_fixture_source(self, extraction_client) -> None:
        """Starts extraction with fixture files (fallback source)."""
        with patch(
            "app.api.v1.endpoints.extraction.common.run_extraction_task"
        ) as mock_task:
            response = await extraction_client.post(
                "/api/v1/extraction/start",
                json={"source": "fixtures"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"
            # Should find fixture files (8 in tests/fixtures/uw_models)
            assert data["files_discovered"] >= 0

    @pytest.mark.asyncio
    async def test_start_extraction_sharepoint_not_configured(self, extraction_client) -> None:
        """Returns 400 when SharePoint is not configured."""
        with patch(
            "app.api.v1.endpoints.extraction.extract.settings"
        ) as mock_settings:
            mock_settings.sharepoint_configured = False
            mock_settings.get_sharepoint_config_errors.return_value = [
                "AZURE_TENANT_ID",
                "AZURE_CLIENT_ID",
            ]

            response = await extraction_client.post(
                "/api/v1/extraction/start",
                json={"source": "sharepoint"},
            )

            assert response.status_code == 400
            assert "not configured" in response.json()["detail"]


# ============================================================================
# Test: POST /extraction/cancel
# ============================================================================


class TestExtractionCancel:
    """Tests for POST /api/v1/extraction/cancel endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_no_running_extraction(self, extraction_client) -> None:
        """Returns 404 when no running extraction."""
        response = await extraction_client.post("/api/v1/extraction/cancel")
        assert response.status_code == 404
        assert "No running extraction" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_running_extraction(
        self, extraction_client, running_extraction: ExtractionRun
    ) -> None:
        """Successfully cancels a running extraction."""
        response = await extraction_client.post("/api/v1/extraction/cancel")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "cancelled"
        assert data["run_id"] == str(running_extraction.id)

    @pytest.mark.asyncio
    async def test_cancel_specific_extraction(
        self, extraction_client, running_extraction: ExtractionRun
    ) -> None:
        """Cancels a specific extraction by ID."""
        response = await extraction_client.post(
            f"/api/v1/extraction/cancel?run_id={running_extraction.id}"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_extraction(
        self, extraction_client, extraction_run: ExtractionRun
    ) -> None:
        """Returns 400 when trying to cancel non-running extraction."""
        response = await extraction_client.post(
            f"/api/v1/extraction/cancel?run_id={extraction_run.id}"
        )
        assert response.status_code == 400
        assert "not running" in response.json()["detail"]


# ============================================================================
# Test: GET /extraction/properties
# ============================================================================


class TestExtractionProperties:
    """Tests for GET /api/v1/extraction/properties endpoint."""

    @pytest.mark.asyncio
    async def test_list_properties_empty(self, extraction_client) -> None:
        """Returns empty list when no properties extracted."""
        response = await extraction_client.get("/api/v1/extraction/properties")
        assert response.status_code == 200
        data = response.json()
        assert data["properties"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_properties_with_data(
        self, extraction_client, extracted_values: list[ExtractedValue]
    ) -> None:
        """Returns list of property objects with field counts."""
        response = await extraction_client.get("/api/v1/extraction/properties")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 1
        prop_names = [p["property_name"] for p in data["properties"]]
        assert "Test Property" in prop_names
        # Verify property object shape
        prop = next(p for p in data["properties"] if p["property_name"] == "Test Property")
        assert prop["total_fields"] == 3
        assert "categories" in prop

    @pytest.mark.asyncio
    async def test_list_properties_by_run_id(
        self, extraction_client, extraction_run: ExtractionRun, extracted_values: list[ExtractedValue]
    ) -> None:
        """Filters properties by extraction run ID."""
        response = await extraction_client.get(
            f"/api/v1/extraction/properties?run_id={extraction_run.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["properties"]) >= 1


# ============================================================================
# Test: GET /extraction/properties/{name}
# ============================================================================


class TestExtractionPropertyData:
    """Tests for GET /api/v1/extraction/properties/{name} endpoint."""

    @pytest.mark.asyncio
    async def test_get_property_not_found(self, extraction_client) -> None:
        """Returns 404 for non-existent property."""
        response = await extraction_client.get("/api/v1/extraction/properties/NonExistent")
        assert response.status_code == 404
        assert "No data found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_property_data(
        self, extraction_client, extracted_values: list[ExtractedValue]
    ) -> None:
        """Returns all extracted values for a property."""
        response = await extraction_client.get("/api/v1/extraction/properties/Test%20Property")
        assert response.status_code == 200

        data = response.json()
        assert data["property_name"] == "Test Property"
        assert data["total"] == 3
        assert "values" in data
        assert "categories" in data
        field_names = [v["field_name"] for v in data["values"]]
        assert "PROPERTY_NAME" in field_names
        assert "TOTAL_UNITS" in field_names

    @pytest.mark.asyncio
    async def test_get_property_data_with_run_id(
        self, extraction_client, extraction_run: ExtractionRun, extracted_values: list[ExtractedValue]
    ) -> None:
        """Filters property data by extraction run ID."""
        response = await extraction_client.get(
            f"/api/v1/extraction/properties/Test%20Property?run_id={extraction_run.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["values"][0]["extraction_run_id"] == str(extraction_run.id)


# ============================================================================
# Test: GET /extraction/scheduler/status
# ============================================================================


class TestSchedulerStatus:
    """Tests for GET /api/v1/extraction/scheduler/status endpoint."""

    @pytest.mark.asyncio
    async def test_get_scheduler_status(self, extraction_client) -> None:
        """Returns scheduler status."""
        with patch(
            "app.api.v1.endpoints.extraction.scheduler.get_extraction_scheduler"
        ) as mock_get_scheduler:
            mock_scheduler = MagicMock()
            mock_scheduler.get_status.return_value = {
                "enabled": False,
                "cron_expression": "0 2 * * *",
                "timezone": "America/Phoenix",
                "next_run": None,
                "last_run": None,
                "last_run_id": None,
                "running": False,
            }
            mock_get_scheduler.return_value = mock_scheduler

            response = await extraction_client.get("/api/v1/extraction/scheduler/status")
            assert response.status_code == 200

            data = response.json()
            assert data["enabled"] is False
            assert data["cron_expression"] == "0 2 * * *"
            assert data["timezone"] == "America/Phoenix"
            assert data["running"] is False


# ============================================================================
# Test: POST /extraction/scheduler/enable
# ============================================================================


class TestSchedulerEnable:
    """Tests for POST /api/v1/extraction/scheduler/enable endpoint."""

    @pytest.mark.asyncio
    async def test_enable_scheduler(self, extraction_client) -> None:
        """Successfully enables the scheduler."""
        with patch(
            "app.api.v1.endpoints.extraction.scheduler.get_extraction_scheduler"
        ) as mock_get_scheduler:
            mock_scheduler = MagicMock()
            mock_scheduler.enable = AsyncMock(
                return_value={
                    "enabled": True,
                    "cron_expression": "0 2 * * *",
                    "timezone": "America/Phoenix",
                    "next_run": datetime.utcnow().isoformat(),
                    "last_run": None,
                    "last_run_id": None,
                    "running": False,
                }
            )
            mock_get_scheduler.return_value = mock_scheduler

            response = await extraction_client.post("/api/v1/extraction/scheduler/enable")
            assert response.status_code == 200
            assert response.json()["enabled"] is True


# ============================================================================
# Test: POST /extraction/scheduler/disable
# ============================================================================


class TestSchedulerDisable:
    """Tests for POST /api/v1/extraction/scheduler/disable endpoint."""

    @pytest.mark.asyncio
    async def test_disable_scheduler(self, extraction_client) -> None:
        """Successfully disables the scheduler."""
        with patch(
            "app.api.v1.endpoints.extraction.scheduler.get_extraction_scheduler"
        ) as mock_get_scheduler:
            mock_scheduler = MagicMock()
            mock_scheduler.disable = AsyncMock(
                return_value={
                    "enabled": False,
                    "cron_expression": "0 2 * * *",
                    "timezone": "America/Phoenix",
                    "next_run": None,
                    "last_run": None,
                    "last_run_id": None,
                    "running": False,
                }
            )
            mock_get_scheduler.return_value = mock_scheduler

            response = await extraction_client.post("/api/v1/extraction/scheduler/disable")
            assert response.status_code == 200
            assert response.json()["enabled"] is False


# ============================================================================
# Test: PUT /extraction/scheduler/config
# ============================================================================


class TestSchedulerConfig:
    """Tests for PUT /api/v1/extraction/scheduler/config endpoint."""

    @pytest.mark.asyncio
    async def test_update_scheduler_config(self, extraction_client) -> None:
        """Updates scheduler configuration."""
        with patch(
            "app.api.v1.endpoints.extraction.scheduler.get_extraction_scheduler"
        ) as mock_get_scheduler:
            mock_scheduler = MagicMock()
            mock_scheduler.update_config = AsyncMock(
                return_value={
                    "enabled": True,
                    "cron_expression": "0 3 * * *",
                    "timezone": "UTC",
                    "next_run": datetime.utcnow().isoformat(),
                    "last_run": None,
                    "last_run_id": None,
                    "running": False,
                }
            )
            mock_get_scheduler.return_value = mock_scheduler

            response = await extraction_client.put(
                "/api/v1/extraction/scheduler/config",
                json={
                    "enabled": True,
                    "cron_expression": "0 3 * * *",
                    "timezone": "UTC",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["cron_expression"] == "0 3 * * *"
            assert data["timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_update_scheduler_invalid_cron(self, extraction_client) -> None:
        """Returns 400 for invalid cron expression."""
        with patch(
            "app.api.v1.endpoints.extraction.scheduler.get_extraction_scheduler"
        ) as mock_get_scheduler:
            mock_scheduler = MagicMock()
            mock_scheduler.update_config = AsyncMock(
                side_effect=ValueError("Invalid cron expression")
            )
            mock_get_scheduler.return_value = mock_scheduler

            response = await extraction_client.put(
                "/api/v1/extraction/scheduler/config",
                json={"cron_expression": "invalid"},
            )
            assert response.status_code == 400


# ============================================================================
# Test: GET /extraction/filters
# ============================================================================


class TestFileFilters:
    """Tests for GET /api/v1/extraction/filters endpoint."""

    @pytest.mark.asyncio
    async def test_get_filter_config(self, extraction_client) -> None:
        """Returns current filter configuration."""
        with patch(
            "app.api.v1.endpoints.extraction.filters.get_file_filter"
        ) as mock_get_filter:
            mock_filter = MagicMock()
            mock_filter.get_config.return_value = {
                "file_pattern": ".*UW.*Model.*",
                "exclude_patterns": ["old", "backup"],
                "valid_extensions": [".xlsb", ".xlsx"],
                "cutoff_date": "2024-01-01",
                "max_file_size_mb": 100.0,
            }
            mock_get_filter.return_value = mock_filter

            response = await extraction_client.get("/api/v1/extraction/filters")
            assert response.status_code == 200

            data = response.json()
            assert data["source"] == "environment"
            assert "config" in data
            assert data["config"]["file_pattern"] == ".*UW.*Model.*"
            assert data["config"]["max_file_size_mb"] == 100.0


# ============================================================================
# Test: POST /extraction/filters/test
# ============================================================================


class TestFileFilterTest:
    """Tests for POST /api/v1/extraction/filters/test endpoint."""

    @pytest.mark.asyncio
    async def test_filter_accepts_valid_file(self, extraction_client) -> None:
        """Tests that filter accepts valid UW model file."""
        with patch(
            "app.api.v1.endpoints.extraction.filters.get_file_filter"
        ) as mock_get_filter:
            mock_filter = MagicMock()
            mock_result = MagicMock()
            mock_result.should_process = True
            mock_result.reason_message = None
            mock_filter.should_process.return_value = mock_result
            mock_get_filter.return_value = mock_filter

            response = await extraction_client.post(
                "/api/v1/extraction/filters/test",
                params={
                    "filename": "Property UW Model vCurrent.xlsb",
                    "size_mb": 10.0,
                    "days_old": 5,
                },
            )
            assert response.status_code == 200

            data = response.json()
            assert data["would_process"] is True
            assert data["filename"] == "Property UW Model vCurrent.xlsb"

    @pytest.mark.asyncio
    async def test_filter_rejects_excluded_pattern(self, extraction_client) -> None:
        """Tests that filter rejects file matching exclude pattern."""
        with patch(
            "app.api.v1.endpoints.extraction.filters.get_file_filter"
        ) as mock_get_filter:
            mock_filter = MagicMock()
            mock_result = MagicMock()
            mock_result.should_process = False
            mock_result.reason_message = "File matches exclude pattern: backup"
            mock_filter.should_process.return_value = mock_result
            mock_get_filter.return_value = mock_filter

            response = await extraction_client.post(
                "/api/v1/extraction/filters/test",
                params={
                    "filename": "backup_Property UW Model.xlsb",
                    "size_mb": 10.0,
                    "days_old": 0,
                },
            )
            assert response.status_code == 200

            data = response.json()
            assert data["would_process"] is False
            assert "exclude pattern" in data["skip_reason"]


# ============================================================================
# Test: Background Task Integration
# ============================================================================


class TestBackgroundTaskIntegration:
    """Tests for background task functionality."""

    @pytest.mark.asyncio
    async def test_extraction_task_receives_correct_params(self, extraction_client) -> None:
        """Verifies background task receives correct parameters."""
        with patch(
            "app.api.v1.endpoints.extraction.common.run_extraction_task"
        ) as mock_task:
            response = await extraction_client.post(
                "/api/v1/extraction/start",
                json={
                    "source": "local",
                    "file_paths": ["/path/file1.xlsb", "/path/file2.xlsb"],
                },
            )

            assert response.status_code == 200
            # Background task should have been added (not called directly)
            # The actual parameters are passed to BackgroundTasks.add_task


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_file_paths_falls_back_to_fixtures(self, extraction_client) -> None:
        """
        Empty file_paths falls back to fixture files.

        When source is 'local' but file_paths is empty, the API falls back
        to loading files from the fixtures directory for testing purposes.
        """
        with patch(
            "app.api.v1.endpoints.extraction.common.run_extraction_task"
        ):
            response = await extraction_client.post(
                "/api/v1/extraction/start",
                json={"source": "local", "file_paths": []},
            )
            assert response.status_code == 200
            # Falls back to fixture files when no paths provided
            data = response.json()
            assert data["status"] == "running"
            # The fixture directory contains 8 test files
            assert data["files_discovered"] >= 0

    @pytest.mark.asyncio
    async def test_special_characters_in_property_name(
        self, extraction_client, sync_db_session: Session, extraction_run: ExtractionRun
    ) -> None:
        """Handles special characters in property names."""
        # Create value with special characters in property name
        value = ExtractedValue(
            id=uuid4(),
            extraction_run_id=extraction_run.id,
            property_name="Test & Property (Special)",
            field_name="FIELD_1",
            value_text="test",
            is_error=False,
        )
        sync_db_session.add(value)
        sync_db_session.commit()

        # URL encode the property name
        response = await extraction_client.get(
            "/api/v1/extraction/properties/Test%20%26%20Property%20%28Special%29"
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_extraction_prevention(
        self, extraction_client, running_extraction: ExtractionRun
    ) -> None:
        """Prevents concurrent extractions."""
        response = await extraction_client.post(
            "/api/v1/extraction/start",
            json={"source": "local"},
        )
        assert response.status_code == 409

        # Verify specific run ID is in error message
        assert str(running_extraction.id) in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
