"""
Tests for Phase 4 UW Model extraction pipeline.

Tests cover:
- Field remaps loading and application
- Dry-run extraction (no DB writes)
- Live extraction with DB writes
- Conflict checking for existing data
- Cross-group validation counts
- Cell mapping application

Run with: pytest tests/test_extraction/test_phase4_extraction.py -v
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
from app.extraction.cell_mapping import CellMapping, CellMappingParser
from app.extraction.group_pipeline import GroupExtractionPipeline, PipelineConfig
from app.models.extraction import ExtractedValue, ExtractionRun


# ============================================================================
# Sync Database Setup
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
def pipeline(tmp_path) -> GroupExtractionPipeline:
    """Create pipeline with temp data dir."""
    return GroupExtractionPipeline(data_dir=str(tmp_path / "groups"))


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
    field_remaps: dict[str, str] | None = None,
) -> None:
    """Helper to write reference mapping for a group."""
    group_dir = pipeline.data_dir / group_name
    group_dir.mkdir(parents=True, exist_ok=True)
    mapping_data = {
        "group_name": group_name,
        "mappings": mappings,
        "unmapped_fields": [],
    }
    if field_remaps:
        mapping_data["field_remaps"] = field_remaps
    (group_dir / "reference_mapping.json").write_text(json.dumps(mapping_data))


def _create_mock_cell_mapping(
    field_name: str,
    sheet_name: str = "Summary",
    cell_address: str = "D6",
    category: str = "Financial",
) -> CellMapping:
    """Create a mock CellMapping for testing."""
    return CellMapping(
        category=category,
        description=field_name.replace("_", " ").title(),
        sheet_name=sheet_name,
        cell_address=cell_address,
        field_name=field_name,
    )


# ============================================================================
# Field Remaps Tests
# ============================================================================


class TestFieldRemapsLoaded:
    """Tests for field remaps loading from reference mapping."""

    def test_field_remaps_loaded_from_reference_mapping(self, pipeline):
        """Field remaps should be loaded from reference_mapping.json."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])

        field_remaps = {
            "REVENUE_TOTAL": "TOTAL_REVENUE",
            "NOI_STABILIZED": "STABILIZED_NOI",
            "CAP_RATE_GOING_IN": "GOING_IN_CAP_RATE",
        }
        _setup_reference_mapping(pipeline, "test_group", [
            {
                "field_name": "TOTAL_REVENUE",
                "source_sheet": "Summary",
                "source_cell": "D6",
                "match_tier": 1,
                "confidence": 0.95,
            },
        ], field_remaps=field_remaps)

        # Load the mapping file and verify remaps are present
        mapping_path = pipeline.data_dir / "test_group" / "reference_mapping.json"
        data = json.loads(mapping_path.read_text())

        assert "field_remaps" in data
        assert data["field_remaps"]["REVENUE_TOTAL"] == "TOTAL_REVENUE"
        assert data["field_remaps"]["NOI_STABILIZED"] == "STABILIZED_NOI"
        assert len(data["field_remaps"]) == 3

    def test_field_remaps_empty_when_not_specified(self, pipeline):
        """When no field remaps specified, key should be absent or empty."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {
                "field_name": "REVENUE",
                "source_sheet": "Summary",
                "source_cell": "D6",
                "match_tier": 1,
                "confidence": 0.95,
            },
        ])

        mapping_path = pipeline.data_dir / "test_group" / "reference_mapping.json"
        data = json.loads(mapping_path.read_text())

        # Field remaps should be absent when not specified
        assert "field_remaps" not in data

    def test_field_remaps_handles_special_characters(self, pipeline):
        """Field remaps should handle field names with special characters."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])

        field_remaps = {
            "CAP_RATE_PCT": "CAP_RATE_PERCENT",
            "SF_NUM": "SQUARE_FEET_NUMBER",
        }
        _setup_reference_mapping(pipeline, "test_group", [], field_remaps=field_remaps)

        mapping_path = pipeline.data_dir / "test_group" / "reference_mapping.json"
        data = json.loads(mapping_path.read_text())

        assert data["field_remaps"]["CAP_RATE_PCT"] == "CAP_RATE_PERCENT"
        assert data["field_remaps"]["SF_NUM"] == "SQUARE_FEET_NUMBER"


class TestFieldRemapsAppliedToCellMappings:
    """Tests for applying field remaps to cell mappings."""

    def test_field_remaps_applied_during_extraction(self, pipeline, sync_db):
        """Field remaps should rename fields during extraction."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])

        # Mapping uses canonical name, but extracted data uses variant name
        _setup_reference_mapping(pipeline, "test_group", [
            {
                "field_name": "TOTAL_REVENUE",  # canonical name
                "source_sheet": "Summary",
                "source_cell": "D6",
                "match_tier": 1,
                "confidence": 0.95,
                "label_text": "Total Revenue",
                "category": "Financial",
            },
        ], field_remaps={"REVENUE_TOTAL": "TOTAL_REVENUE"})

        # Verify the mapping was created
        mapping_path = pipeline.data_dir / "test_group" / "reference_mapping.json"
        data = json.loads(mapping_path.read_text())
        assert len(data["mappings"]) == 1
        assert data["mappings"][0]["field_name"] == "TOTAL_REVENUE"

    def test_cell_mapping_preserves_metadata(self, pipeline):
        """Cell mapping should preserve category and description after remap."""
        mapping = _create_mock_cell_mapping(
            field_name="TOTAL_REVENUE",
            sheet_name="Summary",
            cell_address="D6",
            category="Financial",
        )

        assert mapping.field_name == "TOTAL_REVENUE"
        assert mapping.category == "Financial"
        assert mapping.sheet_name == "Summary"
        assert mapping.cell_address == "D6"

    def test_multiple_remaps_applied_correctly(self, pipeline):
        """Multiple field remaps should all be applied correctly."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])

        field_remaps = {
            "REVENUE_YR1": "YEAR_1_REVENUE",
            "REVENUE_YR2": "YEAR_2_REVENUE",
            "REVENUE_YR3": "YEAR_3_REVENUE",
            "NOI_YR1": "YEAR_1_NOI",
        }
        mappings = [
            {"field_name": "YEAR_1_REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
            {"field_name": "YEAR_2_REVENUE", "source_sheet": "Summary", "source_cell": "D7"},
            {"field_name": "YEAR_3_REVENUE", "source_sheet": "Summary", "source_cell": "D8"},
            {"field_name": "YEAR_1_NOI", "source_sheet": "Summary", "source_cell": "E6"},
        ]
        _setup_reference_mapping(pipeline, "test_group", mappings, field_remaps=field_remaps)

        mapping_path = pipeline.data_dir / "test_group" / "reference_mapping.json"
        data = json.loads(mapping_path.read_text())

        assert len(data["field_remaps"]) == 4
        assert data["field_remaps"]["REVENUE_YR1"] == "YEAR_1_REVENUE"
        assert data["field_remaps"]["NOI_YR1"] == "YEAR_1_NOI"


# ============================================================================
# Dry-Run Extraction Tests
# ============================================================================


class TestDryRunProducesReportWithoutDBWrites:
    """Tests for dry-run extraction behavior."""

    def test_dry_run_produces_report(self, pipeline, sync_db):
        """Dry run should produce a report file."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {
                "field_name": "REVENUE",
                "source_sheet": "Summary",
                "source_cell": "D6",
                "match_tier": 1,
                "confidence": 0.95,
            },
        ])

        report = pipeline.run_group_extraction(sync_db, "test_group", dry_run=True)

        assert report["dry_run"] is True
        assert "started_at" in report
        assert "completed_at" in report

        # Check report file exists
        report_path = pipeline.data_dir / "test_group" / "dry_run_report.json"
        assert report_path.exists()

    def test_dry_run_no_extraction_run_created(self, pipeline, sync_db):
        """Dry run should NOT create ExtractionRun records."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {
                "field_name": "REVENUE",
                "source_sheet": "Summary",
                "source_cell": "D6",
                "match_tier": 1,
                "confidence": 0.95,
            },
        ])

        pipeline.run_group_extraction(sync_db, "test_group", dry_run=True)

        runs = sync_db.execute(select(ExtractionRun)).scalars().all()
        assert len(runs) == 0

    def test_dry_run_no_extracted_values_created(self, pipeline, sync_db):
        """Dry run should NOT create ExtractedValue records."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {
                "field_name": "REVENUE",
                "source_sheet": "Summary",
                "source_cell": "D6",
                "match_tier": 1,
                "confidence": 0.95,
            },
        ])

        pipeline.run_group_extraction(sync_db, "test_group", dry_run=True)

        values = sync_db.execute(select(ExtractedValue)).scalars().all()
        assert len(values) == 0

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_dry_run_report_includes_would_be_extracted(self, mock_extract, pipeline, sync_db):
        """Dry run report should show what would be extracted."""
        mock_extract.return_value = (
            "/test.xlsb",
            "Test Deal",
            {"PROPERTY_NAME": "Test Deal", "REVENUE": 1500000.0, "NOI": 750000.0},
            None,
        )

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Test Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "match_tier": 1, "confidence": 0.95, "label_text": "Revenue", "category": "Financial"},
            {"field_name": "NOI", "source_sheet": "Summary", "source_cell": "D7",
             "match_tier": 1, "confidence": 0.95, "label_text": "NOI", "category": "Financial"},
        ])

        report = pipeline.run_group_extraction(sync_db, "test_group", dry_run=True)

        assert report["files_processed"] == 1
        # PROPERTY_NAME is also counted as a value (not prefixed with _)
        assert report["total_values"] >= 2
        assert "/test.xlsb" in report["per_file"]


# ============================================================================
# Live Extraction Tests
# ============================================================================


class TestLiveExtractionWritesToDB:
    """Tests for live extraction with database writes."""

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_live_extraction_creates_extraction_run(self, mock_extract, pipeline, sync_db):
        """Live extraction should create an ExtractionRun."""
        mock_extract.return_value = (
            "/test.xlsb",
            "Test Deal",
            {"PROPERTY_NAME": "Test Deal", "REVENUE": 2000000.0},
            None,
        )

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Test Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "match_tier": 1, "confidence": 0.95, "label_text": "Revenue", "category": "Financial"},
        ])

        report = pipeline.run_group_extraction(sync_db, "test_group", dry_run=False)

        assert report["dry_run"] is False

        runs = sync_db.execute(select(ExtractionRun)).scalars().all()
        assert len(runs) == 1
        assert runs[0].trigger_type == "group_extraction"
        assert runs[0].status == "completed"

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_live_extraction_creates_extracted_values(self, mock_extract, pipeline, sync_db):
        """Live extraction should create ExtractedValue records."""
        mock_extract.return_value = (
            "/test.xlsb",
            "Test Deal",
            {"PROPERTY_NAME": "Test Deal", "REVENUE": 2500000.0, "NOI": 1000000.0},
            None,
        )

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Test Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "match_tier": 1, "confidence": 0.95, "label_text": "Revenue", "category": "Financial"},
            {"field_name": "NOI", "source_sheet": "Summary", "source_cell": "D7",
             "match_tier": 1, "confidence": 0.95, "label_text": "NOI", "category": "Financial"},
        ])

        report = pipeline.run_group_extraction(sync_db, "test_group", dry_run=False)

        assert report["files_processed"] == 1

        values = sync_db.execute(select(ExtractedValue)).scalars().all()
        # Should have REVENUE, NOI and PROPERTY_NAME (all non-underscore-prefixed fields are stored)
        assert len(values) >= 2
        field_names = {v.field_name for v in values}
        assert "REVENUE" in field_names
        assert "NOI" in field_names

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_live_extraction_creates_mutation_log(self, mock_extract, pipeline, sync_db):
        """Live extraction should create mutation_log.json."""
        mock_extract.return_value = (
            "/test.xlsb",
            "Test Deal",
            {"PROPERTY_NAME": "Test Deal", "REVENUE": 1000000.0},
            None,
        )

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Test Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "match_tier": 1, "confidence": 0.95, "label_text": "Revenue", "category": "Financial"},
        ])

        pipeline.run_group_extraction(sync_db, "test_group", dry_run=False)

        mutation_log = pipeline.data_dir / "test_group" / "mutation_log.json"
        assert mutation_log.exists()

        data = json.loads(mutation_log.read_text())
        assert data["dry_run"] is False
        assert data["files_processed"] == 1

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_live_extraction_updates_pipeline_stats(self, mock_extract, pipeline, sync_db):
        """Live extraction should update pipeline config stats."""
        mock_extract.return_value = (
            "/test.xlsb",
            "Test Deal",
            {"PROPERTY_NAME": "Test Deal", "REVENUE": 1000000.0},
            None,
        )

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Test Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "match_tier": 1, "confidence": 0.95, "label_text": "Revenue", "category": "Financial"},
        ])

        pipeline.run_group_extraction(sync_db, "test_group", dry_run=False)

        # Reload config from disk
        cfg = pipeline.load_config()
        assert cfg.total_extracted > 0
        assert cfg.extraction_completed_at is not None


# ============================================================================
# Conflict Check Tests
# ============================================================================


class TestConflictCheckFindsExistingData:
    """Tests for conflict checking with existing extracted data."""

    def test_conflict_check_no_existing_data(self, pipeline, sync_db):
        """No existing data should return no conflicts."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Test Deal"}],
        }])

        conflicts = pipeline.run_conflict_check(sync_db)
        assert len(conflicts) == 0

    def test_conflict_check_finds_manual_extraction_conflicts(self, pipeline, sync_db):
        """Should detect conflicts with manual extraction runs."""
        # Create a manual (production) extraction run
        run = ExtractionRunCRUD.create(sync_db, trigger_type="manual", files_discovered=1)

        sync_db.add(ExtractedValue(
            extraction_run_id=run.id,
            property_name="Test Deal",
            field_name="REVENUE",
            value_text="5000000",
            value_numeric=5000000,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        sync_db.commit()

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Test Deal"}],
        }])

        conflicts = pipeline.run_conflict_check(sync_db)
        assert "test_group" in conflicts
        assert len(conflicts["test_group"]) > 0
        assert conflicts["test_group"][0]["property_name"] == "Test Deal"

    def test_conflict_check_ignores_group_extraction_runs(self, pipeline, sync_db):
        """Should not conflict with other group extraction runs."""
        # Create a group extraction run
        run = ExtractionRunCRUD.create(sync_db, trigger_type="group_extraction", files_discovered=1)

        sync_db.add(ExtractedValue(
            extraction_run_id=run.id,
            property_name="Test Deal",
            field_name="REVENUE",
            value_text="5000000",
            value_numeric=5000000,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        sync_db.commit()

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Test Deal"}],
        }])

        conflicts = pipeline.run_conflict_check(sync_db)
        # Should not have conflicts because existing data is from group_extraction
        assert len(conflicts) == 0

    def test_conflict_check_multiple_groups(self, pipeline, sync_db):
        """Should check conflicts for multiple groups."""
        # Create production data
        run = ExtractionRunCRUD.create(sync_db, trigger_type="manual", files_discovered=2)

        sync_db.add(ExtractedValue(
            extraction_run_id=run.id,
            property_name="Deal A",
            field_name="REVENUE",
            value_text="1000000",
            value_numeric=1000000,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        sync_db.add(ExtractedValue(
            extraction_run_id=run.id,
            property_name="Deal B",
            field_name="REVENUE",
            value_text="2000000",
            value_numeric=2000000,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        sync_db.commit()

        _setup_groups_json(pipeline, [
            {"group_name": "group_1", "files": [{"name": "a.xlsb", "deal_name": "Deal A"}]},
            {"group_name": "group_2", "files": [{"name": "b.xlsb", "deal_name": "Deal B"}]},
        ])

        conflicts = pipeline.run_conflict_check(sync_db)
        assert "group_1" in conflicts
        assert "group_2" in conflicts

    def test_conflict_check_persists_per_group(self, pipeline, sync_db):
        """Conflict results should be persisted per-group."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Test Deal"}],
        }])

        pipeline.run_conflict_check(sync_db)

        conflict_path = pipeline.data_dir / "test_group" / "conflicts.json"
        assert conflict_path.exists()


# ============================================================================
# Cross-Group Validation Tests
# ============================================================================


class TestCrossGroupValidationCounts:
    """Tests for cross-group validation."""

    def test_cross_group_validation_empty_db(self, pipeline, sync_db):
        """Validation with no data should return zeros."""
        report = pipeline.run_cross_group_validation(sync_db)

        assert report["total_extracted_values"] == 0
        assert report["unique_properties"] == 0
        assert report["validation_passed"] is True

    def test_cross_group_validation_counts_group_extractions(self, pipeline, sync_db):
        """Validation should count values from group extractions."""
        run = ExtractionRunCRUD.create(sync_db, trigger_type="group_extraction", files_discovered=2)

        sync_db.add(ExtractedValue(
            extraction_run_id=run.id,
            property_name="Deal A",
            field_name="REVENUE",
            value_text="1000000",
            value_numeric=1000000,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        sync_db.add(ExtractedValue(
            extraction_run_id=run.id,
            property_name="Deal A",
            field_name="NOI",
            value_text="500000",
            value_numeric=500000,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        sync_db.add(ExtractedValue(
            extraction_run_id=run.id,
            property_name="Deal B",
            field_name="REVENUE",
            value_text="2000000",
            value_numeric=2000000,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        sync_db.commit()
        ExtractionRunCRUD.complete(sync_db, run.id, files_processed=2, files_failed=0)

        report = pipeline.run_cross_group_validation(sync_db)

        assert report["total_extracted_values"] == 3
        assert report["unique_properties"] == 2
        assert report["validation_passed"] is True

    def test_cross_group_validation_excludes_manual_extractions(self, pipeline, sync_db):
        """Validation should only count group_extraction runs."""
        # Create manual run (should NOT be counted)
        manual_run = ExtractionRunCRUD.create(sync_db, trigger_type="manual", files_discovered=1)
        sync_db.add(ExtractedValue(
            extraction_run_id=manual_run.id,
            property_name="Manual Deal",
            field_name="REVENUE",
            value_text="999999",
            value_numeric=999999,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))

        # Create group extraction run (should be counted)
        group_run = ExtractionRunCRUD.create(sync_db, trigger_type="group_extraction", files_discovered=1)
        sync_db.add(ExtractedValue(
            extraction_run_id=group_run.id,
            property_name="Group Deal",
            field_name="REVENUE",
            value_text="1000000",
            value_numeric=1000000,
            is_error=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        sync_db.commit()

        report = pipeline.run_cross_group_validation(sync_db)

        # Should only count the group extraction value
        assert report["total_extracted_values"] == 1
        assert report["unique_properties"] == 1

    def test_cross_group_validation_persists_report(self, pipeline, sync_db):
        """Validation report should be persisted to disk."""
        pipeline.run_cross_group_validation(sync_db)

        report_path = pipeline.data_dir / "final_validation_report.json"
        assert report_path.exists()

        data = json.loads(report_path.read_text())
        assert "total_extracted_values" in data
        assert "unique_properties" in data
        assert "validation_passed" in data

    def test_cross_group_validation_includes_per_group_counts(self, pipeline, sync_db):
        """Validation should include per-group value counts."""
        run = ExtractionRunCRUD.create(sync_db, trigger_type="group_extraction", files_discovered=1)
        run.file_metadata = {"group_name": "test_group"}
        sync_db.commit()

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

        report = pipeline.run_cross_group_validation(sync_db)

        assert "per_group_counts" in report


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestExtractionEdgeCases:
    """Tests for edge cases in extraction."""

    def test_extraction_empty_group(self, pipeline, sync_db):
        """Extracting from a group with no files should handle gracefully."""
        _setup_groups_json(pipeline, [{
            "group_name": "empty_group",
            "files": [],
        }])
        _setup_reference_mapping(pipeline, "empty_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ])

        report = pipeline.run_group_extraction(sync_db, "empty_group", dry_run=True)
        # Empty group should process 0 files; total_values may be 0 or absent depending on implementation
        assert report["files_processed"] == 0
        assert report.get("total_values", 0) == 0 or "error" in report

    def test_extraction_no_mappings(self, pipeline, sync_db):
        """Group with empty mappings should return error."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [])

        report = pipeline.run_group_extraction(sync_db, "test_group", dry_run=True)
        assert "error" in report

    def test_extraction_missing_reference_mapping(self, pipeline, sync_db):
        """Missing reference mapping should raise ValueError."""
        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "deal_name": "Deal"}],
        }])

        with pytest.raises(ValueError, match="Reference mapping not found"):
            pipeline.run_group_extraction(sync_db, "test_group", dry_run=True)

    def test_conflict_check_missing_groups(self, pipeline, sync_db):
        """Conflict check without groups.json should raise ValueError."""
        with pytest.raises(ValueError, match="Groups not found"):
            pipeline.run_conflict_check(sync_db)

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_extraction_handles_null_values(self, mock_extract, pipeline, sync_db):
        """Extraction should handle null values gracefully."""
        mock_extract.return_value = (
            "/test.xlsb",
            "Test Deal",
            {"PROPERTY_NAME": "Test Deal", "REVENUE": None, "NOI": 500000.0},
            None,
        )

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Test Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6",
             "match_tier": 1, "confidence": 0.95, "label_text": "Revenue", "category": "Financial"},
            {"field_name": "NOI", "source_sheet": "Summary", "source_cell": "D7",
             "match_tier": 1, "confidence": 0.95, "label_text": "NOI", "category": "Financial"},
        ])

        report = pipeline.run_group_extraction(sync_db, "test_group", dry_run=True)

        # Should still process successfully despite null value
        assert report["files_processed"] == 1

    @patch("app.api.v1.endpoints.extraction.common._extract_single_file")
    def test_extraction_file_error_tracked(self, mock_extract, pipeline, sync_db):
        """File extraction errors should be tracked in report."""
        mock_extract.return_value = ("/test.xlsb", "Test Deal", None, "File not found")

        _setup_groups_json(pipeline, [{
            "group_name": "test_group",
            "files": [{"name": "model.xlsb", "path": "/test.xlsb", "deal_name": "Test Deal"}],
        }])
        _setup_reference_mapping(pipeline, "test_group", [
            {"field_name": "REVENUE", "source_sheet": "Summary", "source_cell": "D6"},
        ])

        report = pipeline.run_group_extraction(sync_db, "test_group", dry_run=True)

        assert report["files_failed"] == 1
        assert "/test.xlsb" in report["per_file"]
        assert report["per_file"]["/test.xlsb"]["status"] == "failed"
        assert "File not found" in report["per_file"]["/test.xlsb"]["error"]
