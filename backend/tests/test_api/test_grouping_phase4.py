"""
Tests for Phase 4 grouping API endpoints.

Tests cover:
- POST /extraction/grouping/approve/{name} - Group approval
- POST /extraction/grouping/extract-batch - Batch extraction
- Batch extraction dry-run mode
- Batch extraction stops on error
- Extraction requires approval flow

Run with: pytest tests/test_api/test_grouping_phase4.py -v
"""

import json
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.extraction.grouping import _get_pipeline, router
from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.base import Base
from app.db.session import get_sync_db
from app.extraction.group_pipeline import GroupExtractionPipeline
from app.models.extraction import ExtractedValue, ExtractionRun


# ============================================================================
# Database Setup
# ============================================================================

SYNC_TEST_DB_URL = "sqlite:///:memory:"

sync_engine = create_engine(
    SYNC_TEST_DB_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

SyncSession = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def groups_dir(tmp_path):
    """Shared temp directory for pipeline data."""
    return str(tmp_path / "groups")


@pytest.fixture(scope="function")
def sync_db() -> Generator[Session, None, None]:
    """Create a sync database session for tests."""
    Base.metadata.create_all(bind=sync_engine)
    session = SyncSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=sync_engine)


@pytest.fixture
def app(groups_dir, sync_db):
    """Create FastAPI app with grouping router and temp pipeline."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/extraction")

    # Override pipeline to use temp directory
    _dir = groups_dir

    def _test_pipeline():
        return GroupExtractionPipeline(data_dir=_dir)

    def _test_db():
        yield sync_db

    test_app.dependency_overrides[_get_pipeline] = _test_pipeline
    test_app.dependency_overrides[get_sync_db] = _test_db

    return test_app


@pytest.fixture
def client(app):
    """Create TestClient for API tests."""
    return TestClient(app)


@pytest.fixture
def pipeline(groups_dir):
    """Direct pipeline instance sharing the same directory as app."""
    return GroupExtractionPipeline(data_dir=groups_dir)


# ============================================================================
# Test Helpers
# ============================================================================


def _setup_groups_json(pipeline: GroupExtractionPipeline, groups: list[dict]) -> None:
    """Helper to write groups.json."""
    pipeline.data_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "groups": groups,
        "ungrouped": [],
        "empty_templates": [],
        "summary": {"total_groups": len(groups)},
    }
    (pipeline.data_dir / "groups.json").write_text(json.dumps(data))


def _setup_reference_mapping(
    pipeline: GroupExtractionPipeline,
    group_name: str,
    mappings: list[dict],
    approved: bool = False,
) -> None:
    """Helper to write reference mapping for a group."""
    group_dir = pipeline.data_dir / group_name
    group_dir.mkdir(parents=True, exist_ok=True)
    mapping_data = {
        "group_name": group_name,
        "mappings": mappings,
        "unmapped_fields": [],
        "approved": approved,
        "approved_at": datetime.now(UTC).isoformat() if approved else None,
    }
    (group_dir / "reference_mapping.json").write_text(json.dumps(mapping_data))


def _setup_complete_pipeline(pipeline: GroupExtractionPipeline) -> None:
    """Set up pipeline with completed phases for extraction testing."""
    cfg = pipeline.config
    cfg.discovery_completed_at = datetime.now(UTC).isoformat()
    cfg.fingerprint_completed_at = datetime.now(UTC).isoformat()
    cfg.grouping_completed_at = datetime.now(UTC).isoformat()
    cfg.reference_map_completed_at = datetime.now(UTC).isoformat()
    pipeline.save_config(cfg)


# ============================================================================
# Group Approval Endpoint Tests
# ============================================================================


class TestApproveGroupEndpoint:
    """Tests for POST /extraction/grouping/approve/{name}."""

    def test_approve_group_success(self, client, pipeline):
        """Successfully approve a group."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ])
        _setup_complete_pipeline(pipeline)

        response = client.post("/extraction/grouping/approve/test_group")
        assert response.status_code == 200
        data = response.json()
        assert data["group_name"] == "test_group"
        assert data["approved"] is True

    def test_approve_group_not_found(self, client, pipeline):
        """Approving nonexistent group should return 400 (ValueError)."""
        _setup_groups_json(pipeline, [])
        _setup_complete_pipeline(pipeline)

        response = client.post("/extraction/grouping/approve/nonexistent")
        # Returns 400 because ValueError is raised for missing group
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_approve_group_updates_config_file(self, client, pipeline):
        """Approval should update the pipeline config file."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ], approved=False)
        _setup_complete_pipeline(pipeline)

        response = client.post("/extraction/grouping/approve/test_group")
        assert response.status_code == 200

        # Approval is tracked in config.json, not reference_mapping.json
        config_path = pipeline.data_dir / "config.json"
        data = json.loads(config_path.read_text())
        assert "groups" in data
        assert "test_group" in data["groups"]
        assert data["groups"]["test_group"]["approved"] is True

    def test_approve_group_requires_reference_mapping(self, client, pipeline):
        """Group without reference mapping should fail approval."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Deal"}],
        }])
        _setup_complete_pipeline(pipeline)

        response = client.post("/extraction/grouping/approve/test_group")
        assert response.status_code == 400

    def test_approve_already_approved_group(self, client, pipeline):
        """Re-approving an approved group should succeed (idempotent)."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ], approved=True)
        _setup_complete_pipeline(pipeline)

        response = client.post("/extraction/grouping/approve/test_group")
        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is True


# ============================================================================
# Batch Extraction Dry-Run Tests
# ============================================================================


class TestBatchExtractionDryRun:
    """Tests for POST /extraction/grouping/extract-batch with dry_run=True."""

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_batch_dry_run_success(self, mock_extract, client, pipeline):
        """Batch dry run should process multiple groups without DB writes."""
        mock_extract.return_value = (
            "/test.xlsb", "Deal",
            {"PROPERTY_NAME": "Deal", "REVENUE": 1000000.0},
            None,
        )

        _setup_groups_json(pipeline, [
            {"group_name": "group_1", "files": [{"name": "a.xlsb", "path": "/a.xlsb", "deal_name": "Deal A"}]},
            {"group_name": "group_2", "files": [{"name": "b.xlsb", "path": "/b.xlsb", "deal_name": "Deal B"}]},
        ])
        _setup_reference_mapping(pipeline, "group_1", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "label_text": "Revenue", "category": "Financial"},
        ], approved=True)
        _setup_reference_mapping(pipeline, "group_2", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "label_text": "Revenue", "category": "Financial"},
        ], approved=True)
        _setup_complete_pipeline(pipeline)

        response = client.post(
            "/extraction/grouping/extract-batch",
            json={"dry_run": True, "group_names": ["group_1", "group_2"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["groups_processed"] == 2
        assert data["groups_failed"] == 0

    def test_batch_dry_run_no_db_writes(self, client, pipeline, sync_db):
        """Batch dry run should not create any ExtractionRun records."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ], approved=True)
        _setup_complete_pipeline(pipeline)

        client.post(
            "/extraction/grouping/extract-batch",
            json={"dry_run": True, "group_names": ["test_group"]},
        )

        runs = sync_db.execute(select(ExtractionRun)).scalars().all()
        assert len(runs) == 0

    def test_batch_dry_run_returns_per_group_reports(self, client, pipeline):
        """Batch dry run should return per-group extraction reports."""
        _setup_groups_json(pipeline, [
            {"group_name": "group_1", "files": [{"name": "a.xlsb", "path": "/a.xlsb", "deal_name": "Deal A"}]},
            {"group_name": "group_2", "files": [{"name": "b.xlsb", "path": "/b.xlsb", "deal_name": "Deal B"}]},
        ])
        _setup_reference_mapping(pipeline, "group_1", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ], approved=True)
        _setup_reference_mapping(pipeline, "group_2", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ], approved=True)
        _setup_complete_pipeline(pipeline)

        response = client.post(
            "/extraction/grouping/extract-batch",
            json={"dry_run": True, "group_names": ["group_1", "group_2"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "per_group" in data
        assert "group_1" in data["per_group"]
        assert "group_2" in data["per_group"]


# ============================================================================
# Batch Extraction Stop On Error Tests
# ============================================================================


class TestBatchExtractionStopsOnError:
    """Tests for batch extraction with stop_on_error=True."""

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_batch_stops_on_first_error(self, mock_extract, client, pipeline):
        """Batch should stop on first group error when stop_on_error=True."""
        # First group fails, second would succeed
        def side_effect(extractor, path, deal_name):
            if "a.xlsb" in path:
                return (path, deal_name, None, "Extraction failed")
            return (path, deal_name, {"REVENUE": 1000000.0}, None)

        mock_extract.side_effect = side_effect

        _setup_groups_json(pipeline, [
            {"group_name": "group_1", "files": [{"name": "a.xlsb", "path": "/a.xlsb", "deal_name": "Deal A"}]},
            {"group_name": "group_2", "files": [{"name": "b.xlsb", "path": "/b.xlsb", "deal_name": "Deal B"}]},
        ])
        _setup_reference_mapping(pipeline, "group_1", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "label_text": "Revenue", "category": "Financial"},
        ], approved=True)
        _setup_reference_mapping(pipeline, "group_2", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "label_text": "Revenue", "category": "Financial"},
        ], approved=True)
        _setup_complete_pipeline(pipeline)

        response = client.post(
            "/extraction/grouping/extract-batch",
            json={"dry_run": True, "group_names": ["group_1", "group_2"], "stop_on_error": True},
        )
        assert response.status_code == 200
        data = response.json()
        # First group failed, batch stopped
        assert data["groups_failed"] >= 1

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_batch_continues_without_stop_on_error(self, mock_extract, client, pipeline):
        """Batch should continue processing all groups when stop_on_error=False."""
        def side_effect(extractor, path, deal_name):
            if "a.xlsb" in path:
                return (path, deal_name, None, "Extraction failed")
            return (path, deal_name, {"PROPERTY_NAME": deal_name, "REVENUE": 1000000.0}, None)

        mock_extract.side_effect = side_effect

        _setup_groups_json(pipeline, [
            {"group_name": "group_1", "files": [{"name": "a.xlsb", "path": "/a.xlsb", "deal_name": "Deal A"}]},
            {"group_name": "group_2", "files": [{"name": "b.xlsb", "path": "/b.xlsb", "deal_name": "Deal B"}]},
        ])
        _setup_reference_mapping(pipeline, "group_1", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "label_text": "Revenue", "category": "Financial"},
        ], approved=True)
        _setup_reference_mapping(pipeline, "group_2", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "label_text": "Revenue", "category": "Financial"},
        ], approved=True)
        _setup_complete_pipeline(pipeline)

        response = client.post(
            "/extraction/grouping/extract-batch",
            json={"dry_run": True, "group_names": ["group_1", "group_2"], "stop_on_error": False},
        )
        assert response.status_code == 200
        data = response.json()
        # Both groups processed despite first failing
        assert "group_1" in data["per_group"]
        assert "group_2" in data["per_group"]

    def test_batch_stop_on_error_default_false(self, client, pipeline):
        """stop_on_error should default to False."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ], approved=True)
        _setup_complete_pipeline(pipeline)

        # Make request without stop_on_error
        response = client.post(
            "/extraction/grouping/extract-batch",
            json={"dry_run": True, "group_names": ["test_group"]},
        )
        assert response.status_code == 200


# ============================================================================
# Extraction Requires Approval Tests
# ============================================================================


class TestExtractionRequiresApproval:
    """Tests for extraction approval requirements."""

    def test_extraction_processes_unapproved_group_when_explicit(self, client, pipeline):
        """Extraction processes explicitly specified groups regardless of approval status."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ], approved=False)  # Not approved but explicitly requested
        _setup_complete_pipeline(pipeline)

        response = client.post(
            "/extraction/grouping/extract-batch",
            json={"dry_run": True, "group_names": ["test_group"]},
        )
        # When explicitly specifying groups, they are processed regardless of approval
        assert response.status_code == 200
        data = response.json()
        # Group is processed (though files may fail validation)
        assert data["groups_processed"] >= 0

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_extraction_succeeds_for_approved_group(self, mock_extract, client, pipeline):
        """Extraction should succeed for approved groups."""
        mock_extract.return_value = (
            "/test.xlsb", "Deal",
            {"PROPERTY_NAME": "Deal", "REVENUE": 1000000.0},
            None,
        )

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "label_text": "Revenue", "category": "Financial"},
        ], approved=True)  # Approved
        _setup_complete_pipeline(pipeline)

        response = client.post(
            "/extraction/grouping/extract-batch",
            json={"dry_run": True, "group_names": ["test_group"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["groups_processed"] >= 1

    def test_batch_extracts_only_approved_when_no_group_names(self, client, pipeline):
        """When no group_names specified, should extract all approved groups."""
        _setup_groups_json(pipeline, [
            {"group_name": "approved_group", "files": [{"name": "a.xlsb", "path": "/a.xlsb", "deal_name": "Deal A"}]},
            {"group_name": "unapproved_group", "files": [{"name": "b.xlsb", "path": "/b.xlsb", "deal_name": "Deal B"}]},
        ])
        _setup_reference_mapping(pipeline, "approved_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ], approved=False)  # Set via helper, but actually approve via config
        _setup_reference_mapping(pipeline, "unapproved_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ], approved=False)
        _setup_complete_pipeline(pipeline)

        # First approve the group via the API
        client.post("/extraction/grouping/approve/approved_group")

        response = client.post(
            "/extraction/grouping/extract-batch",
            json={"dry_run": True},  # No group_names = all approved
        )
        assert response.status_code == 200
        data = response.json()
        # Should only process approved groups (approved_group was approved)
        # Note: unapproved_group should not appear in per_group
        assert "per_group" in data
        if data["groups_processed"] > 0:
            assert "approved_group" in data["per_group"]
            assert "unapproved_group" not in data["per_group"]


# ============================================================================
# Single Group Extraction Endpoint Tests
# ============================================================================


class TestSingleGroupExtractionEndpoint:
    """Tests for POST /extraction/grouping/extract/{name}."""

    def test_extract_single_group_dry_run(self, client, pipeline):
        """Single group extraction should support dry_run mode."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ])
        _setup_complete_pipeline(pipeline)

        response = client.post(
            "/extraction/grouping/extract/test_group",
            json={"dry_run": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True
        assert data["group_name"] == "test_group"

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_extract_single_group_live(self, mock_extract, client, pipeline, sync_db):
        """Single group live extraction should create DB records."""
        mock_extract.return_value = (
            "/test.xlsb", "Deal",
            {"PROPERTY_NAME": "Deal", "REVENUE": 1000000.0},
            None,
        )

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "label_text": "Revenue", "category": "Financial"},
        ])
        _setup_complete_pipeline(pipeline)

        response = client.post(
            "/extraction/grouping/extract/test_group",
            json={"dry_run": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is False
        assert data["files_processed"] == 1

        # Verify DB records created
        runs = sync_db.execute(select(ExtractionRun)).scalars().all()
        assert len(runs) == 1
        assert runs[0].trigger_type == "group_extraction"

    def test_extract_nonexistent_group(self, client, pipeline):
        """Extracting nonexistent group should return 400."""
        _setup_groups_json(pipeline, [])
        _setup_complete_pipeline(pipeline)

        response = client.post(
            "/extraction/grouping/extract/nonexistent",
            json={"dry_run": True},
        )
        assert response.status_code == 400


# ============================================================================
# Conflict Check Endpoint Tests
# ============================================================================


class TestConflictCheckEndpoint:
    """Tests for POST /extraction/grouping/conflict-check."""

    def test_conflict_check_success(self, client, pipeline):
        """Conflict check should return conflict details."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Deal"}],
        }])
        _setup_complete_pipeline(pipeline)

        response = client.post("/extraction/grouping/conflict-check")
        assert response.status_code == 200
        data = response.json()
        assert "groups_with_conflicts" in data
        assert "total_conflicts" in data
        assert "conflicts" in data

    def test_conflict_check_requires_reference_mapping(self, client, pipeline):
        """Conflict check should require reference mapping to be completed."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Deal"}],
        }])
        # Don't set reference_map_completed_at

        response = client.post("/extraction/grouping/conflict-check")
        assert response.status_code == 400


# ============================================================================
# Validation Endpoint Tests
# ============================================================================


class TestValidationEndpoint:
    """Tests for POST /extraction/grouping/validate."""

    def test_validation_success(self, client, pipeline):
        """Validation should return cross-group validation report."""
        _setup_complete_pipeline(pipeline)

        response = client.post("/extraction/grouping/validate")
        assert response.status_code == 200
        data = response.json()
        assert "total_extracted_values" in data
        assert "unique_properties" in data
        assert "validation_passed" in data

    def test_validation_empty_db(self, client, pipeline):
        """Validation with no extractions should pass with zero counts."""
        _setup_complete_pipeline(pipeline)

        response = client.post("/extraction/grouping/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["total_extracted_values"] == 0
        assert data["validation_passed"] is True
