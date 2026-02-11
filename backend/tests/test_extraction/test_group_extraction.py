"""
Tests for Phase 4: Group extraction, conflict checking, and validation.

Tests cover:
- Conflict check with existing extracted data
- ExtractionRun creation with trigger_type="group_extraction"
- Dry-run extraction (no DB writes)
- Live extraction with DB writes
- Cross-group validation
- Report generation

Run with: pytest tests/test_extraction/test_group_extraction.py -v
"""

import json
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.base import Base
from app.extraction.group_pipeline import GroupExtractionPipeline, PipelineConfig
from app.models.extraction import ExtractedValue, ExtractionRun

# ============================================================================
# Sync Database Setup (matches existing test pattern)
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
def pipeline(tmp_path):
    """Create pipeline with temp data dir."""
    return GroupExtractionPipeline(data_dir=str(tmp_path / "groups"))


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


def _setup_reference_mapping(pipeline: GroupExtractionPipeline, group_name: str, mappings: list[dict]) -> None:
    """Helper to write reference mapping for a group."""
    group_dir = pipeline.data_dir / group_name
    group_dir.mkdir(parents=True, exist_ok=True)
    (group_dir / "reference_mapping.json").write_text(json.dumps({
        "group_name": group_name,
        "mappings": mappings,
        "unmapped_fields": [],
    }))


class TestConflictCheck:
    """Tests for Phase 4.1 conflict checking."""

    def test_conflict_check_no_existing_data(self, pipeline, sync_db):
        """No existing data → no conflicts."""
        _setup_groups_json(pipeline, [{
            "group_name": "group_1",
            "files": [{"name": "model.xlsb", "deal_name": "Test Deal"}],
        }])

        conflicts = pipeline.run_conflict_check(sync_db)
        assert len(conflicts) == 0

    def test_conflict_check_with_existing_data(self, pipeline, sync_db):
        """Existing production data for same property → conflict."""
        # Create a production extraction run
        run = ExtractionRunCRUD.create(sync_db, trigger_type="manual", files_discovered=1)

        # Insert some extracted values
        sync_db.add(ExtractedValue(
            extraction_run_id=run.id,
            property_name="Test Deal",
            field_name="REVENUE",
            value_text="1000000",
            value_numeric=1000000,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        sync_db.commit()

        _setup_groups_json(pipeline, [{
            "group_name": "group_1",
            "files": [{"name": "model.xlsb", "deal_name": "Test Deal"}],
        }])

        conflicts = pipeline.run_conflict_check(sync_db)
        assert "group_1" in conflicts
        assert len(conflicts["group_1"]) > 0

    def test_conflict_check_persists_results(self, pipeline, sync_db):
        """Conflict results should be persisted per-group."""
        _setup_groups_json(pipeline, [{
            "group_name": "group_1",
            "files": [{"name": "model.xlsb", "deal_name": "Test Deal"}],
        }])

        pipeline.run_conflict_check(sync_db)
        conflict_path = pipeline.data_dir / "group_1" / "conflicts.json"
        assert conflict_path.exists()

    def test_conflict_check_requires_groups(self, pipeline, sync_db):
        """Should raise if groups.json doesn't exist."""
        with pytest.raises(ValueError, match="Groups not found"):
            pipeline.run_conflict_check(sync_db)


class TestGroupExtraction:
    """Tests for Phase 4.2 group extraction."""

    def test_extraction_requires_reference_mapping(self, pipeline, sync_db):
        """Should raise if reference mapping not found."""
        _setup_groups_json(pipeline, [{
            "group_name": "group_1",
            "files": [{"name": "model.xlsb", "deal_name": "Deal"}],
        }])

        with pytest.raises(ValueError, match="Reference mapping not found"):
            pipeline.run_group_extraction(sync_db, "group_1", dry_run=True)

    def test_dry_run_no_db_writes(self, pipeline, sync_db):
        """Dry run should not create ExtractionRun or ExtractedValues."""
        _setup_groups_json(pipeline, [{
            "group_name": "group_1",
            "files": [{"name": "model.xlsb", "path": "/nonexistent.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "group_1", [{
            "field_name": "REVENUE",
            "source_sheet": "Summary",
            "source_cell": "D6",
            "match_tier": 1,
            "confidence": 0.95,
        }])

        report = pipeline.run_group_extraction(sync_db, "group_1", dry_run=True)
        assert report["dry_run"] is True

        # No extraction runs should be created
        runs = sync_db.execute(select(ExtractionRun)).scalars().all()
        assert len(runs) == 0

    def test_dry_run_report_persisted(self, pipeline, sync_db):
        """Dry run report should be saved to disk."""
        _setup_groups_json(pipeline, [{
            "group_name": "group_1",
            "files": [{"name": "model.xlsb", "path": "/nonexistent.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "group_1", [{
            "field_name": "REVENUE",
            "source_sheet": "Summary",
            "source_cell": "D6",
            "match_tier": 1,
            "confidence": 0.95,
        }])

        pipeline.run_group_extraction(sync_db, "group_1", dry_run=True)
        report_path = pipeline.data_dir / "group_1" / "dry_run_report.json"
        assert report_path.exists()

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_live_extraction_creates_run(self, mock_extract, pipeline, sync_db):
        """Live extraction should create an ExtractionRun."""
        mock_extract.return_value = (
            "/test.xlsb", "Deal",
            {"PROPERTY_NAME": "Deal", "REVENUE": 1000000.0},
            None,
        )

        _setup_groups_json(pipeline, [{
            "group_name": "group_1",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "group_1", [{
            "field_name": "REVENUE",
            "source_sheet": "Summary",
            "source_cell": "D6",
            "match_tier": 1,
            "confidence": 0.95,
            "label_text": "Revenue",
            "category": "Financial",
        }])

        report = pipeline.run_group_extraction(sync_db, "group_1", dry_run=False)
        assert report["dry_run"] is False
        assert report["files_processed"] == 1

        # Check ExtractionRun was created
        runs = sync_db.execute(select(ExtractionRun)).scalars().all()
        assert len(runs) == 1
        assert runs[0].trigger_type == "group_extraction"
        assert runs[0].status == "completed"

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_extraction_handles_file_errors(self, mock_extract, pipeline, sync_db):
        """Files that fail extraction should be tracked."""
        mock_extract.return_value = ("/test.xlsb", "Deal", None, "File not found")

        _setup_groups_json(pipeline, [{
            "group_name": "group_1",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "group_1", [{
            "field_name": "REVENUE",
            "source_sheet": "Summary",
            "source_cell": "D6",
            "match_tier": 1,
            "confidence": 0.95,
        }])

        report = pipeline.run_group_extraction(sync_db, "group_1", dry_run=True)
        assert report["files_failed"] == 1
        assert "/test.xlsb" in report["per_file"]
        assert report["per_file"]["/test.xlsb"]["status"] == "failed"

    def test_extraction_empty_mappings(self, pipeline, sync_db):
        """Group with no mappings should return error."""
        _setup_groups_json(pipeline, [{
            "group_name": "group_1",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "group_1", [])

        report = pipeline.run_group_extraction(sync_db, "group_1", dry_run=True)
        assert "error" in report

    def test_extraction_nonexistent_group(self, pipeline, sync_db):
        """Extracting from nonexistent group should raise."""
        _setup_groups_json(pipeline, [])

        with pytest.raises(ValueError, match="Reference mapping not found"):
            pipeline.run_group_extraction(sync_db, "nonexistent", dry_run=True)


class TestCrossGroupValidation:
    """Tests for Phase 4.3 cross-group validation."""

    def test_validation_no_extractions(self, pipeline, sync_db):
        """Validation with no group extractions should return zeros."""
        report = pipeline.run_cross_group_validation(sync_db)
        assert report["total_extracted_values"] == 0
        assert report["unique_properties"] == 0
        assert report["validation_passed"] is True

    def test_validation_report_persisted(self, pipeline, sync_db):
        """Validation report should be saved to disk."""
        pipeline.run_cross_group_validation(sync_db)
        report_path = pipeline.data_dir / "final_validation_report.json"
        assert report_path.exists()

    def test_validation_with_extraction_data(self, pipeline, sync_db):
        """Validation should count group extraction values."""
        # Create a group extraction run
        run = ExtractionRunCRUD.create(sync_db, trigger_type="group_extraction", files_discovered=1)

        sync_db.add(ExtractedValue(
            extraction_run_id=run.id,
            property_name="Deal A",
            field_name="REVENUE",
            value_text="500000",
            value_numeric=500000,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        sync_db.commit()

        # Complete the run
        ExtractionRunCRUD.complete(sync_db, run.id, files_processed=1, files_failed=0)

        report = pipeline.run_cross_group_validation(sync_db)
        assert report["total_extracted_values"] == 1
        assert report["unique_properties"] == 1


class TestMutationLog:
    """Tests for extraction mutation logging."""

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_live_extraction_creates_mutation_log(self, mock_extract, pipeline, sync_db):
        """Live extraction should write mutation_log.json."""
        mock_extract.return_value = (
            "/test.xlsb", "Deal",
            {"PROPERTY_NAME": "Deal", "REVENUE": 500000.0},
            None,
        )

        _setup_groups_json(pipeline, [{
            "group_name": "group_1",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "group_1", [{
            "field_name": "REVENUE",
            "source_sheet": "Summary",
            "source_cell": "D6",
            "match_tier": 1,
            "confidence": 0.95,
            "label_text": "Revenue",
            "category": "Financial",
        }])

        pipeline.run_group_extraction(sync_db, "group_1", dry_run=False)
        mutation_log = pipeline.data_dir / "group_1" / "mutation_log.json"
        assert mutation_log.exists()
        data = json.loads(mutation_log.read_text())
        assert data["dry_run"] is False
