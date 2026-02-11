"""Tests for the construction_import service.

Covers helper functions, column mapping, classification inference,
pipeline status mapping, file scanning, 50-unit filter, and import logic.
"""

import os
import tempfile
from collections.abc import Generator
from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.construction import (
    ConstructionProject,
    ConstructionSourceLog,
    PipelineStatus,
    ProjectClassification,
)
from app.services.construction_import import (
    COSTAR_CONSTRUCTION_COLUMN_MAP,
    MIN_UNITS,
    FileImportResult,
    FullImportResult,
    VerificationReport,
    _clean_currency,
    _safe_bool,
    _safe_date,
    _safe_float,
    _safe_int,
    _safe_str,
    get_unimported_files,
    import_all_construction_files,
    import_construction_file,
    infer_classification,
    map_pipeline_status,
    run_verification_queries,
    scan_construction_files,
)

# =============================================================================
# Sync database setup (import service uses sync Session)
# =============================================================================

SYNC_TEST_DB_URL = "sqlite:///:memory:"

sync_engine = create_engine(
    SYNC_TEST_DB_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

SyncTestSession = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture()
def sync_db() -> Generator[Session, None, None]:
    """Create a sync database session for import service tests."""
    Base.metadata.create_all(bind=sync_engine)
    session = SyncTestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=sync_engine)


# =============================================================================
# Helper to create test Excel files with CoStar construction headers
# =============================================================================


def _make_test_excel(
    rows: list[dict],
    filepath: str,
    include_all_headers: bool = True,
) -> str:
    """Create a test Excel file with CoStar construction column headers.

    Args:
        rows: List of dicts with CoStar header names as keys.
        filepath: Full path where to write the file.
        include_all_headers: If True, include all 171 CoStar headers (empty
            for missing values). Required to pass the missing-column check.
    """
    all_headers = list(COSTAR_CONSTRUCTION_COLUMN_MAP.keys())
    if include_all_headers:
        # Build full header set — map keys plus any extras from CoStar export
        extra_headers = [
            "FEMA Map Date",
            "FEMA Map Identifier",
            "FIRM ID",
            "FIRM Panel Number",
            "Floodplain Area",
            "Building Park",
            "Closest Transit Stop Walk Time (min)",
            "Collateral Type",
            "Continent",
            "Country",
            "Fund Name",
            "Four Bedroom Asking Rent/SF",
            "Four Bedroom Asking Rent/Unit",
            "Four Bedroom Avg SF",
            "Four Bedroom Concessions %",
            "Four Bedroom Effective Rent/SF",
            "Four Bedroom Effective Rent/Unit",
            "Four Bedroom Vacancy %",
            "Four Bedroom Vacant Units",
            "One Bedroom Asking Rent/SF",
            "One Bedroom Asking Rent/Unit",
            "One Bedroom Avg SF",
            "One Bedroom Concessions %",
            "One Bedroom Effective Rent/SF",
            "One Bedroom Effective Rent/Unit",
            "One Bedroom Vacancy %",
            "One Bedroom Vacant Units",
            "Property Manager Address",
            "Property Manager City State Zip",
            "Property Manager Contact",
            "Property Manager Phone",
            "Sales Company",
            "Sales Contact",
            "Sales Contact Phone",
            "Sale Company Name",
            "Sale Company Contact",
            "Studio Asking Rent/SF",
            "Studio Asking Rent/Unit",
            "Studio Avg SF",
            "Studio Concessions %",
            "Studio Effective Rent/SF",
            "Studio Effective Rent/Unit",
            "Studio Vacancy %",
            "Studio Vacant Units",
            "Subcontinent",
            "Three Bedroom Asking Rent/SF",
            "Three Bedroom Asking Rent/Unit",
            "Three Bedroom Avg SF",
            "Three Bedroom Concessions %",
            "Three Bedroom Effective Rent/SF",
            "Three Bedroom Effective Rent/Unit",
            "Three Bedroom Vacancy %",
            "Three Bedroom Vacant Units",
            "Two Bedroom Asking Rent/SF",
            "Two Bedroom Asking Rent/Unit",
            "Two Bedroom Avg SF",
            "Two Bedroom Concessions %",
            "Two Bedroom Effective Rent/SF",
            "Two Bedroom Effective Rent/Unit",
            "Two Bedroom Vacancy %",
            "Two Bedroom Vacant Units",
            "Avg Asking/Bed",
            "Four Bedroom Asking Rent/Bed",
            "Four Bedroom Effective Rent/Bed",
            "Number of Beds",
            "One Bedroom Asking Rent/Bed",
            "One Bedroom Effective Rent/Bed",
            "Sale Company Address",
            "Sale Company City State Zip",
            "Sale Company Fax",
            "Sale Company Phone",
            "Studio Asking Rent/Bed",
            "Studio Effective Rent/Bed",
            "Three Bedroom Asking Rent/Bed",
            "Three Bedroom Effective Rent/Bed",
            "Two Bedroom Asking Rent/Bed",
            "Two Bedroom Effective Rent/Bed",
        ]
        all_headers = list(dict.fromkeys(all_headers + extra_headers))

    # Build rows — fill missing cols with None
    full_rows = []
    for r in rows:
        full_row = {h: r.get(h) for h in all_headers}
        full_rows.append(full_row)

    df = pd.DataFrame(full_rows, columns=all_headers)
    df.to_excel(filepath, index=False, engine="openpyxl")
    return filepath


# =============================================================================
# 1. _safe_bool() tests
# =============================================================================


class TestSafeBool:
    def test_yes_string(self):
        assert _safe_bool("Yes") is True

    def test_no_string(self):
        assert _safe_bool("No") is False

    def test_true_bool(self):
        assert _safe_bool(True) is True

    def test_false_bool(self):
        assert _safe_bool(False) is False

    def test_none(self):
        assert _safe_bool(None) is False

    def test_nan(self):
        assert _safe_bool(float("nan")) is False

    def test_y_string(self):
        assert _safe_bool("y") is True

    def test_one_string(self):
        assert _safe_bool("1") is True

    def test_arbitrary_string(self):
        assert _safe_bool("maybe") is False


# =============================================================================
# 2. infer_classification() tests
# =============================================================================


class TestInferClassification:
    def test_condo(self):
        row = {"is_condo": True, "rent_type": "Market", "affordable_type": None}
        assert infer_classification(row) == ProjectClassification.CONV_CONDO

    def test_lihtc_from_affordable_type(self):
        row = {
            "is_condo": False,
            "rent_type": "Market",
            "affordable_type": "Rent Restricted",
        }
        assert infer_classification(row) == ProjectClassification.LIHTC

    def test_lihtc_from_rent_type(self):
        row = {"is_condo": False, "rent_type": "Affordable", "affordable_type": None}
        assert infer_classification(row) == ProjectClassification.LIHTC

    def test_workforce(self):
        row = {
            "is_condo": False,
            "rent_type": "Market/Affordable",
            "affordable_type": None,
        }
        assert infer_classification(row) == ProjectClassification.WORKFORCE

    def test_default_conv_mr(self):
        row = {"is_condo": False, "rent_type": "Market", "affordable_type": None}
        assert infer_classification(row) == ProjectClassification.CONV_MR

    def test_condo_overrides_affordable(self):
        """Condo check has higher priority than affordable check."""
        row = {
            "is_condo": True,
            "rent_type": "Affordable",
            "affordable_type": "Rent Restricted",
        }
        assert infer_classification(row) == ProjectClassification.CONV_CONDO

    def test_missing_fields_default(self):
        """All missing fields should default to CONV_MR."""
        assert infer_classification({}) == ProjectClassification.CONV_MR


# =============================================================================
# 3. map_pipeline_status() tests
# =============================================================================


class TestMapPipelineStatus:
    def test_proposed(self):
        assert map_pipeline_status(None, "Proposed") == PipelineStatus.PROPOSED

    def test_final_planning(self):
        assert (
            map_pipeline_status("Final Planning", None) == PipelineStatus.FINAL_PLANNING
        )

    def test_under_construction(self):
        assert (
            map_pipeline_status(None, "Under Construction")
            == PipelineStatus.UNDER_CONSTRUCTION
        )

    def test_existing_maps_to_delivered(self):
        assert map_pipeline_status("Existing", None) == PipelineStatus.DELIVERED

    def test_permitted(self):
        assert map_pipeline_status("Permitted", None) == PipelineStatus.PERMITTED

    def test_constr_status_preferred(self):
        """constr_status takes precedence over building_status."""
        assert (
            map_pipeline_status("Proposed", "Under Construction")
            == PipelineStatus.UNDER_CONSTRUCTION
        )

    def test_none_defaults_proposed(self):
        assert map_pipeline_status(None, None) == PipelineStatus.PROPOSED

    def test_unknown_value_defaults_proposed(self):
        assert map_pipeline_status("SomeUnknown", None) == PipelineStatus.PROPOSED

    def test_case_insensitive(self):
        assert (
            map_pipeline_status("UNDER CONSTRUCTION", None)
            == PipelineStatus.UNDER_CONSTRUCTION
        )


# =============================================================================
# 4. scan_construction_files() tests
# =============================================================================


class TestScanConstructionFiles:
    def test_finds_xlsx_files(self, tmp_path):
        (tmp_path / "file1.xlsx").touch()
        (tmp_path / "file2.xlsx").touch()
        (tmp_path / "not_excel.csv").touch()
        files = scan_construction_files(str(tmp_path))
        assert len(files) == 2

    def test_skips_temp_files(self, tmp_path):
        (tmp_path / "~$temp.xlsx").touch()
        (tmp_path / "good.xlsx").touch()
        files = scan_construction_files(str(tmp_path))
        assert len(files) == 1
        assert "good.xlsx" in files[0]

    def test_finds_nested_files(self, tmp_path):
        sub = tmp_path / "Phoenix"
        sub.mkdir()
        (sub / "export.xlsx").touch()
        files = scan_construction_files(str(tmp_path))
        assert len(files) == 1

    def test_empty_directory(self, tmp_path):
        files = scan_construction_files(str(tmp_path))
        assert files == []

    def test_finds_xlsb_and_xlsm(self, tmp_path):
        (tmp_path / "file.xlsb").touch()
        (tmp_path / "file.xlsm").touch()
        files = scan_construction_files(str(tmp_path))
        assert len(files) == 2


# =============================================================================
# 5. Import with 50-unit filter tests
# =============================================================================


class TestImportConstructionFile:
    def test_imports_above_min_units(self, sync_db, tmp_path):
        """Projects with >= 50 units should be imported."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "100",
                    "Property Name": "Big Project",
                    "Number Of Units": 200,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                    "City": "Phoenix",
                    "State": "AZ",
                    "Latitude": 33.45,
                    "Longitude": -112.07,
                },
            ],
            filepath,
        )
        result = import_construction_file(sync_db, filepath)
        assert result.rows_imported == 1
        assert result.rows_skipped_under_min == 0

        # Verify in DB
        project = sync_db.query(ConstructionProject).first()
        assert project is not None
        assert project.number_of_units == 200
        assert project.project_name == "Big Project"
        assert project.pipeline_status == "proposed"
        assert project.primary_classification == "CONV_MR"

    def test_skips_below_min_units(self, sync_db, tmp_path):
        """Projects with < 50 units should be skipped."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "101",
                    "Property Name": "Small Project",
                    "Number Of Units": 30,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
            ],
            filepath,
        )
        result = import_construction_file(sync_db, filepath)
        assert result.rows_imported == 0
        assert result.rows_skipped_under_min == 1

    def test_skips_null_units(self, sync_db, tmp_path):
        """Projects with null units should be skipped."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "102",
                    "Property Name": "No Units",
                    "Number Of Units": None,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
            ],
            filepath,
        )
        result = import_construction_file(sync_db, filepath)
        assert result.rows_imported == 0
        assert result.rows_skipped_no_units == 1

    def test_classification_inference_condo(self, sync_db, tmp_path):
        """Condo projects should be classified as CONV_CONDO."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "200",
                    "Property Name": "Condo Tower",
                    "Number Of Units": 100,
                    "Building Status": "Under Construction",
                    "Constr Status": "Under Construction",
                    "Condo": "Yes",
                    "Rent Type": "Market",
                },
            ],
            filepath,
        )
        result = import_construction_file(sync_db, filepath)
        assert result.rows_imported == 1

        project = sync_db.query(ConstructionProject).first()
        assert project.primary_classification == "CONV_CONDO"
        assert project.is_condo is True

    def test_classification_inference_lihtc(self, sync_db, tmp_path):
        """Affordable projects should be classified as LIHTC."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "201",
                    "Property Name": "Affordable Housing",
                    "Number Of Units": 80,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Affordable",
                    "Affordable Type": "Rent Restricted",
                },
            ],
            filepath,
        )
        result = import_construction_file(sync_db, filepath)
        assert result.rows_imported == 1

        project = sync_db.query(ConstructionProject).first()
        assert project.primary_classification == "LIHTC"

    def test_classification_inference_workforce(self, sync_db, tmp_path):
        """Market/Affordable should be classified as WORKFORCE."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "202",
                    "Property Name": "Workforce Housing",
                    "Number Of Units": 150,
                    "Building Status": "Final Planning",
                    "Constr Status": "Final Planning",
                    "Condo": "No",
                    "Rent Type": "Market/Affordable",
                },
            ],
            filepath,
        )
        result = import_construction_file(sync_db, filepath)
        assert result.rows_imported == 1

        project = sync_db.query(ConstructionProject).first()
        assert project.primary_classification == "WORKFORCE"
        assert project.pipeline_status == "final_planning"

    def test_upsert_updates_existing(self, sync_db, tmp_path):
        """Re-importing the same file should update existing records."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "300",
                    "Property Name": "Original Name",
                    "Number Of Units": 100,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
            ],
            filepath,
        )
        result1 = import_construction_file(sync_db, filepath)
        assert result1.rows_imported == 1

        # Re-import with updated name
        _make_test_excel(
            [
                {
                    "PropertyID": "300",
                    "Property Name": "Updated Name",
                    "Number Of Units": 120,
                    "Building Status": "Under Construction",
                    "Constr Status": "Under Construction",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
            ],
            filepath,
        )
        result2 = import_construction_file(sync_db, filepath)
        assert result2.rows_updated == 1
        assert result2.rows_imported == 0

        project = sync_db.query(ConstructionProject).first()
        assert project.project_name == "Updated Name"
        assert project.number_of_units == 120
        assert project.pipeline_status == "under_construction"

    def test_missing_property_id_gets_placeholder(self, sync_db, tmp_path):
        """Rows without PropertyID get a generated placeholder."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "Property Name": "No ID Project",
                    "Number Of Units": 75,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
            ],
            filepath,
        )
        result = import_construction_file(sync_db, filepath)
        assert result.rows_imported == 1

        project = sync_db.query(ConstructionProject).first()
        assert project.costar_property_id.startswith("UNKNOWN-")

    def test_source_log_created(self, sync_db, tmp_path):
        """Import should create a source log entry."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "400",
                    "Property Name": "Log Test",
                    "Number Of Units": 100,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
            ],
            filepath,
        )
        import_construction_file(sync_db, filepath)

        log = sync_db.query(ConstructionSourceLog).first()
        assert log is not None
        assert log.source_name == "costar_construction"
        assert log.fetch_type == "excel_import"
        assert log.records_inserted == 1
        assert log.success is True

    def test_mixed_rows_filtered_correctly(self, sync_db, tmp_path):
        """Mix of qualifying and non-qualifying rows."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "500",
                    "Property Name": "Big",
                    "Number Of Units": 200,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
                {
                    "PropertyID": "501",
                    "Property Name": "Small",
                    "Number Of Units": 20,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
                {
                    "PropertyID": "502",
                    "Property Name": "Medium",
                    "Number Of Units": 50,
                    "Building Status": "Under Construction",
                    "Constr Status": "Under Construction",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
                {
                    "PropertyID": "503",
                    "Property Name": "Null Units",
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
            ],
            filepath,
        )
        result = import_construction_file(sync_db, filepath)
        assert result.rows_imported == 2  # 200 and 50
        assert result.rows_skipped_under_min == 1  # 20
        assert result.rows_skipped_no_units == 1  # null

    def test_float_columns_parsed(self, sync_db, tmp_path):
        """Float columns like lat/lon, asking rent should parse correctly."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "600",
                    "Property Name": "Float Test",
                    "Number Of Units": 100,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                    "Latitude": 33.4484,
                    "Longitude": -112.074,
                    "Avg Asking/Unit": 1850.50,
                    "Vacancy %": 5.2,
                    "Land Area (AC)": 8.75,
                },
            ],
            filepath,
        )
        result = import_construction_file(sync_db, filepath)
        assert result.rows_imported == 1

        project = sync_db.query(ConstructionProject).first()
        assert project.latitude == pytest.approx(33.4484)
        assert project.longitude == pytest.approx(-112.074)
        assert project.avg_asking_per_unit == pytest.approx(1850.50)
        assert project.vacancy_pct == pytest.approx(5.2)
        assert project.land_area_ac == pytest.approx(8.75)


# =============================================================================
# 6. import_all_construction_files() tests
# =============================================================================


class TestImportAllConstructionFiles:
    def test_imports_multiple_files(self, sync_db, tmp_path):
        """Should import all Excel files in directory."""
        for i in range(3):
            _make_test_excel(
                [
                    {
                        "PropertyID": str(700 + i),
                        "Property Name": f"Project {i}",
                        "Number Of Units": 100 + i * 50,
                        "Building Status": "Proposed",
                        "Constr Status": "Proposed",
                        "Condo": "No",
                        "Rent Type": "Market",
                    },
                ],
                str(tmp_path / f"file_{i}.xlsx"),
            )

        result = import_all_construction_files(sync_db, str(tmp_path))
        assert result.files_processed == 3
        assert result.total_rows_imported == 3
        assert result.total_rows_skipped == 0

    def test_empty_directory(self, sync_db, tmp_path):
        """Should handle empty directory gracefully."""
        result = import_all_construction_files(sync_db, str(tmp_path))
        assert result.files_processed == 0
        assert result.total_rows_imported == 0


# =============================================================================
# 7. get_unimported_files() tests
# =============================================================================


class TestGetUnimportedFiles:
    def test_all_unimported(self, sync_db, tmp_path):
        """All files should be unimported initially."""
        (tmp_path / "file1.xlsx").touch()
        (tmp_path / "file2.xlsx").touch()
        unimported = get_unimported_files(sync_db, str(tmp_path))
        assert len(unimported) == 2

    def test_some_imported(self, sync_db, tmp_path):
        """Already imported files should be excluded."""
        filepath = str(tmp_path / "imported.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "800",
                    "Property Name": "Already Imported",
                    "Number Of Units": 100,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                },
            ],
            filepath,
        )
        import_construction_file(sync_db, filepath)

        # Add a new file
        (tmp_path / "new.xlsx").touch()

        unimported = get_unimported_files(sync_db, str(tmp_path))
        assert len(unimported) == 1
        assert "new.xlsx" in unimported[0]


# =============================================================================
# 8. run_verification_queries() tests
# =============================================================================


class TestVerificationQueries:
    def test_verification_with_data(self, sync_db, tmp_path):
        """Verification should return correct summary stats."""
        filepath = str(tmp_path / "test.xlsx")
        _make_test_excel(
            [
                {
                    "PropertyID": "900",
                    "Property Name": "Project A",
                    "Number Of Units": 100,
                    "Building Status": "Proposed",
                    "Constr Status": "Proposed",
                    "Condo": "No",
                    "Rent Type": "Market",
                    "City": "Phoenix",
                    "Submarket Cluster": "Central Phoenix",
                },
                {
                    "PropertyID": "901",
                    "Property Name": "Project B",
                    "Number Of Units": 200,
                    "Building Status": "Under Construction",
                    "Constr Status": "Under Construction",
                    "Condo": "No",
                    "Rent Type": "Affordable",
                    "City": "Tempe",
                    "Submarket Cluster": "Tempe/Mesa",
                },
            ],
            filepath,
        )
        import_construction_file(sync_db, filepath)

        report = run_verification_queries(sync_db)
        assert report.total_rows == 2
        assert "proposed" in report.rows_per_status
        assert "under_construction" in report.rows_per_status
        assert "CONV_MR" in report.rows_per_classification
        assert "LIHTC" in report.rows_per_classification
        assert report.unit_range == (100, 200)
        assert "Phoenix" in report.cities
        assert "Tempe" in report.cities

    def test_verification_empty_db(self, sync_db):
        """Verification should handle empty database."""
        report = run_verification_queries(sync_db)
        assert report.total_rows == 0
        assert report.rows_per_status == {}
        assert report.rows_per_classification == {}


# =============================================================================
# 9. Column mapping completeness test
# =============================================================================


class TestColumnMapping:
    def test_all_mapped_columns_exist_on_model(self):
        """Every DB column in the mapping must be a valid ConstructionProject attribute."""
        model_columns = {
            c.name for c in ConstructionProject.__table__.columns
        }
        for excel_col, db_col in COSTAR_CONSTRUCTION_COLUMN_MAP.items():
            assert db_col in model_columns, (
                f"Mapped column '{db_col}' (from '{excel_col}') not found on "
                f"ConstructionProject model"
            )

    def test_min_units_constant(self):
        """MIN_UNITS should be 50."""
        assert MIN_UNITS == 50
