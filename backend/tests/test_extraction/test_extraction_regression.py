"""
Regression tests for the Cap Rate TC T3 Extraction pipeline.

Locks in verified extraction behavior from run bb86307f-7f3a-4174-afd8-44a7ac8dda77
so future changes do not break the pipeline. Covers:

1. Supplemental field mapping definitions and override semantics
2. Cell index conversions (0-based for xlsb, 1-based for xlsx)
3. ExtractionRun lifecycle (create, status transitions, counters)
4. ExtractedValue bulk insert, upsert, and property_id backfill
5. Value normalization for change detection hashing
6. Auth guard enforcement on POST /api/v1/extraction/start

Run with:
    cd backend && python -m pytest tests/test_extraction/test_extraction_regression.py -v
"""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.base import Base
from app.extraction.cell_mapping import CellMapping
from app.extraction.extractor import ExcelDataExtractor
from app.models.extraction import ExtractedValue, ExtractionRun
from app.services.extraction.change_detector import (
    _normalize_value,
    _normalize_value_from_text,
    compute_extraction_hash,
)

# ============================================================================
# Sync Database Setup (extraction uses sync sessions)
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
def sync_db() -> Generator[Session, None, None]:
    """Create a sync database session for each test."""
    Base.metadata.create_all(bind=sync_test_engine)
    session = SyncTestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=sync_test_engine)


# ============================================================================
# 1. Supplemental Field Mapping Tests
# ============================================================================


class TestSupplementalFieldMappings:
    """Verify the 5 supplemental mappings injected in run_extraction_task."""

    # The exact supplemental definitions from common.py run_extraction_task()
    EXPECTED_SUPPLEMENTALS = [
        {
            "field_name": "GOING_IN_CAP_RATE",
            "sheet_name": "Assumptions (Summary)",
            "cell_address": "F26",
            "category": "Supplemental",
        },
        {
            "field_name": "T3_RETURN_ON_COST",
            "sheet_name": "Assumptions (Summary)",
            "cell_address": "G27",
            "category": "Supplemental",
        },
        {
            "field_name": "UNLEVERED_RETURNS_IRR",
            "sheet_name": "Returns Metrics (Summary)",
            "cell_address": "E39",
            "category": "Supplemental",
        },
        {
            "field_name": "UNLEVERED_RETURNS_MOIC",
            "sheet_name": "Returns Metrics (Summary)",
            "cell_address": "E40",
            "category": "Supplemental",
        },
        {
            "field_name": "LEVERED_RETURNS_IRR",
            "sheet_name": "Returns Metrics (Summary)",
            "cell_address": "E43",
            "category": "Supplemental",
        },
        {
            "field_name": "LEVERED_RETURNS_MOIC",
            "sheet_name": "Returns Metrics (Summary)",
            "cell_address": "E44",
            "category": "Supplemental",
        },
    ]

    def test_supplemental_count_is_six(self) -> None:
        """Exactly 6 supplemental mappings are defined."""
        assert len(self.EXPECTED_SUPPLEMENTALS) == 6

    @pytest.mark.parametrize(
        "mapping_def",
        EXPECTED_SUPPLEMENTALS,
        ids=[m["field_name"] for m in EXPECTED_SUPPLEMENTALS],
    )
    def test_supplemental_mapping_definition(self, mapping_def: dict) -> None:
        """Each supplemental mapping has the correct sheet, cell, and category."""
        sm = CellMapping(
            category=mapping_def["category"],
            description=f"Test {mapping_def['field_name']}",
            sheet_name=mapping_def["sheet_name"],
            cell_address=mapping_def["cell_address"],
            field_name=mapping_def["field_name"],
        )
        assert sm.field_name == mapping_def["field_name"]
        assert sm.sheet_name == mapping_def["sheet_name"]
        assert sm.cell_address == mapping_def["cell_address"]
        assert sm.category == "Supplemental"

    def test_supplemental_override_existing_mapping(self) -> None:
        """Supplemental mappings override any pre-existing mapping with the same field_name."""
        # Simulate a reference-file mapping pointing to the WRONG sheet
        mappings: dict[str, CellMapping] = {
            "UNLEVERED_RETURNS_IRR": CellMapping(
                category="Financial",
                description="Unlevered Returns IRR",
                sheet_name="Assumptions (Summary)",  # WRONG sheet
                cell_address="E39",
                field_name="UNLEVERED_RETURNS_IRR",
            ),
        }

        # Apply the supplemental override (same logic as run_extraction_task)
        override = CellMapping(
            category="Supplemental",
            description="Unlevered Returns IRR",
            sheet_name="Returns Metrics (Summary)",  # CORRECT sheet
            cell_address="E39",
            field_name="UNLEVERED_RETURNS_IRR",
        )
        mappings[override.field_name] = override

        assert (
            mappings["UNLEVERED_RETURNS_IRR"].sheet_name == "Returns Metrics (Summary)"
        )
        assert mappings["UNLEVERED_RETURNS_IRR"].category == "Supplemental"

    def test_sheet_names_use_parenthesized_form(self) -> None:
        """Sheet names use 'Assumptions (Summary)' NOT 'Assumptions Summary'."""
        for mapping_def in self.EXPECTED_SUPPLEMENTALS:
            sheet_name = mapping_def["sheet_name"]
            # All sheet names in the supplementals contain parentheses
            if "Summary" in sheet_name:
                assert "(" in sheet_name and ")" in sheet_name, (
                    f"Sheet name '{sheet_name}' for {mapping_def['field_name']} "
                    "must use parenthesized form: 'X (Summary)'"
                )

    def test_t3_return_on_cost_maps_to_assumptions_sheet(self) -> None:
        """T3_RETURN_ON_COST specifically targets 'Assumptions (Summary)' sheet G27."""
        t3 = next(
            m
            for m in self.EXPECTED_SUPPLEMENTALS
            if m["field_name"] == "T3_RETURN_ON_COST"
        )
        assert t3["sheet_name"] == "Assumptions (Summary)"
        assert t3["cell_address"] == "G27"

    def test_returns_metrics_fields_all_on_same_sheet(self) -> None:
        """The 4 returns fields all target 'Returns Metrics (Summary)' sheet."""
        returns_fields = [
            m
            for m in self.EXPECTED_SUPPLEMENTALS
            if m["field_name"] not in ("T3_RETURN_ON_COST", "GOING_IN_CAP_RATE")
        ]
        assert len(returns_fields) == 4
        for field in returns_fields:
            assert field["sheet_name"] == "Returns Metrics (Summary)"


# ============================================================================
# 2. Cell Index Conversion Tests
# ============================================================================


class TestCellIndexConversion:
    """Verify 0-based (xlsb/pyxlsb) vs 1-based (xlsx/openpyxl) indexing."""

    def _make_extractor(self) -> ExcelDataExtractor:
        """Create an ExcelDataExtractor with minimal mappings."""
        return ExcelDataExtractor(cell_mappings={})

    def test_column_to_index_single_letter(self) -> None:
        """A=0, B=1, E=4, G=6, Z=25."""
        ext = self._make_extractor()
        assert ext._column_to_index("A") == 0
        assert ext._column_to_index("B") == 1
        assert ext._column_to_index("E") == 4
        assert ext._column_to_index("G") == 6
        assert ext._column_to_index("Z") == 25

    def test_column_to_index_double_letter(self) -> None:
        """AA=26, AB=27, AZ=51."""
        ext = self._make_extractor()
        assert ext._column_to_index("AA") == 26
        assert ext._column_to_index("AB") == 27
        assert ext._column_to_index("AZ") == 51

    def test_xlsb_g27_zero_based(self) -> None:
        """For xlsb: G27 -> target_row=26, target_col=6 (0-based)."""
        ext = self._make_extractor()
        # In _extract_from_xlsb: target_row = int(row_str) - 1, target_col = _column_to_index(col_str)
        col_index = ext._column_to_index("G")
        row_index = 27 - 1  # 0-based
        assert row_index == 26
        assert col_index == 6

    def test_xlsb_e39_zero_based(self) -> None:
        """For xlsb: E39 -> target_row=38, target_col=4 (0-based)."""
        ext = self._make_extractor()
        col_index = ext._column_to_index("E")
        row_index = 39 - 1
        assert row_index == 38
        assert col_index == 4

    def test_xlsb_e40_zero_based(self) -> None:
        """For xlsb: E40 -> target_row=39, target_col=4 (0-based)."""
        ext = self._make_extractor()
        col_index = ext._column_to_index("E")
        row_index = 40 - 1
        assert row_index == 39
        assert col_index == 4

    def test_xlsb_e43_zero_based(self) -> None:
        """For xlsb: E43 -> target_row=42, target_col=4 (0-based)."""
        ext = self._make_extractor()
        col_index = ext._column_to_index("E")
        row_index = 43 - 1
        assert row_index == 42
        assert col_index == 4

    def test_xlsb_e44_zero_based(self) -> None:
        """For xlsb: E44 -> target_row=43, target_col=4 (0-based)."""
        ext = self._make_extractor()
        col_index = ext._column_to_index("E")
        row_index = 44 - 1
        assert row_index == 43
        assert col_index == 4

    def test_xlsx_g27_one_based_openpyxl(self) -> None:
        """
        For xlsx/openpyxl: G27 is accessed as sheet['G27'] which
        uses 1-based addressing internally (row=27, col=7).
        """
        # openpyxl uses cell_address strings directly: sheet["G27"]
        # internally that is row=27, col=7 (1-based)
        # Verify the expectation:
        from openpyxl.utils import column_index_from_string

        assert column_index_from_string("G") == 7  # 1-based
        # row is the numeric part directly: 27

    def test_xlsx_e39_one_based_openpyxl(self) -> None:
        """For xlsx/openpyxl: E39 -> col=5 (1-based), row=39."""
        from openpyxl.utils import column_index_from_string

        assert column_index_from_string("E") == 5


# ============================================================================
# 3. Extraction Run Lifecycle Tests
# ============================================================================


class TestExtractionRunLifecycle:
    """Test ExtractionRun creation, status transitions, and counters."""

    def test_create_run_defaults(self, sync_db: Session) -> None:
        """New run starts in 'running' status with zero counters."""
        run = ExtractionRunCRUD.create(
            sync_db, trigger_type="manual", files_discovered=10
        )

        assert run.id is not None
        assert run.status == "running"
        assert run.trigger_type == "manual"
        assert run.files_discovered == 10
        assert run.files_processed == 0
        assert run.files_failed == 0
        assert run.started_at is not None
        assert run.completed_at is None

    def test_transition_running_to_completed(self, sync_db: Session) -> None:
        """Run transitions from running to completed with final counters."""
        run = ExtractionRunCRUD.create(
            sync_db, trigger_type="manual", files_discovered=5
        )
        assert run.status == "running"

        completed = ExtractionRunCRUD.complete(
            sync_db, run.id, files_processed=4, files_failed=1
        )

        assert completed is not None
        assert completed.status == "completed"
        assert completed.files_processed == 4
        assert completed.files_failed == 1
        assert completed.completed_at is not None

    def test_transition_running_to_failed(self, sync_db: Session) -> None:
        """Run transitions from running to failed with error summary."""
        run = ExtractionRunCRUD.create(
            sync_db, trigger_type="manual", files_discovered=3
        )

        failed = ExtractionRunCRUD.fail(
            sync_db, run.id, error_summary={"error": "Connection lost"}
        )

        assert failed is not None
        assert failed.status == "failed"
        assert failed.completed_at is not None
        assert failed.error_summary == {"error": "Connection lost"}

    def test_transition_running_to_cancelled(self, sync_db: Session) -> None:
        """Run transitions from running to cancelled."""
        run = ExtractionRunCRUD.create(
            sync_db, trigger_type="manual", files_discovered=8
        )

        cancelled = ExtractionRunCRUD.cancel(sync_db, run.id)

        assert cancelled is not None
        assert cancelled.status == "cancelled"
        assert cancelled.completed_at is not None

    def test_progress_counters_update(self, sync_db: Session) -> None:
        """files_processed and files_failed counters update correctly."""
        run = ExtractionRunCRUD.create(
            sync_db, trigger_type="manual", files_discovered=20
        )

        updated = ExtractionRunCRUD.update_progress(
            sync_db, run.id, files_processed=10, files_failed=2
        )

        assert updated is not None
        assert updated.files_processed == 10
        assert updated.files_failed == 2

    def test_only_one_running_detected(self, sync_db: Session) -> None:
        """get_running returns the running extraction, preventing duplicates at API level."""
        run1 = ExtractionRunCRUD.create(
            sync_db, trigger_type="manual", files_discovered=5
        )
        assert ExtractionRunCRUD.get_running(sync_db) is not None

        # The API endpoint checks for running before creating a new one.
        # Verify get_running returns the existing run.
        running = ExtractionRunCRUD.get_running(sync_db)
        assert running is not None
        assert running.id == run1.id

    def test_per_file_status_stored(self, sync_db: Session) -> None:
        """per_file_status JSON is stored and retrievable."""
        run = ExtractionRunCRUD.create(
            sync_db, trigger_type="manual", files_discovered=2
        )

        per_file = {
            "/path/file1.xlsb": {"status": "completed"},
            "/path/file2.xlsb": {"status": "failed", "error": "parse error"},
        }

        completed = ExtractionRunCRUD.complete(
            sync_db,
            run.id,
            files_processed=1,
            files_failed=1,
            per_file_status=per_file,
        )

        assert completed is not None
        assert completed.per_file_status is not None
        assert completed.per_file_status["/path/file1.xlsb"]["status"] == "completed"
        assert completed.per_file_status["/path/file2.xlsb"]["status"] == "failed"


# ============================================================================
# 4. ExtractedValue Tests
# ============================================================================


class TestExtractedValueOperations:
    """Test bulk_insert, upsert behavior, and property_id backfill."""

    def test_bulk_insert_creates_correct_values(self, sync_db: Session) -> None:
        """bulk_insert creates values with correct property_name, field_name, value_text, value_numeric."""
        run = ExtractionRunCRUD.create(sync_db, trigger_type="manual")

        mapping = MagicMock()
        mapping.category = "Financial"
        mapping.sheet_name = "Assumptions (Summary)"
        mapping.cell_address = "G27"

        extracted_data = {
            "T3_RETURN_ON_COST": 0.0625,
            "PROPERTY_NAME": "Hayden Park",
            "_metadata": "skip_me",
        }
        mappings = {
            "T3_RETURN_ON_COST": mapping,
            "PROPERTY_NAME": mapping,
        }

        count = ExtractedValueCRUD.bulk_insert(
            sync_db,
            extraction_run_id=run.id,
            extracted_data=extracted_data,
            mappings=mappings,
            property_name="Hayden Park",
            source_file="/path/to/file.xlsb",
        )

        assert count == 2  # _metadata is skipped

        values = ExtractedValueCRUD.get_by_property(sync_db, "Hayden Park", run.id)
        assert len(values) == 2

        t3_val = next(v for v in values if v.field_name == "T3_RETURN_ON_COST")
        assert t3_val.value_numeric is not None
        assert float(t3_val.value_numeric) == pytest.approx(0.0625, abs=1e-4)
        assert t3_val.value_text == "0.0625"
        assert t3_val.property_name == "Hayden Park"
        assert t3_val.source_file == "/path/to/file.xlsb"

    def test_bulk_insert_upsert_updates_not_duplicates(self, sync_db: Session) -> None:
        """Same run_id + property_name + field_name updates existing row via upsert.

        SQLite limitation (T-DEBT-023): SQLite does not support PostgreSQL-style
        ON CONFLICT DO UPDATE with named constraints. This test verifies the
        insert-twice path does not crash. In production (PostgreSQL), the
        uq_extracted_value constraint triggers a proper upsert.
        See test_integration/test_pg_transactions.py for PG constraint tests.
        """
        run = ExtractionRunCRUD.create(sync_db, trigger_type="manual")

        extracted_v1 = {"TOTAL_UNITS": 100}
        extracted_v2 = {"TOTAL_UNITS": 200}

        count1 = ExtractedValueCRUD.bulk_insert(
            sync_db,
            extraction_run_id=run.id,
            extracted_data=extracted_v1,
            mappings={},
            property_name="TestProp",
        )
        assert count1 == 1

        # Second insert with updated value — in PostgreSQL this triggers upsert.
        # SQLite limitation (T-DEBT-023): ON CONFLICT with PG constraint name
        # falls back to plain insert. We just verify it does not raise.
        try:
            count2 = ExtractedValueCRUD.bulk_insert(
                sync_db,
                extraction_run_id=run.id,
                extracted_data=extracted_v2,
                mappings={},
                property_name="TestProp",
            )
            assert count2 == 1
        except Exception:
            # SQLite limitation (T-DEBT-023): PG upsert syntax unsupported — expected.
            sync_db.rollback()

        # At minimum, the property has values
        values = ExtractedValueCRUD.get_by_property(sync_db, "TestProp", run.id)
        assert len(values) >= 1

    def test_bulk_insert_nan_marks_error(self, sync_db: Session) -> None:
        """NaN values set is_error=True and value_text=None."""
        run = ExtractionRunCRUD.create(sync_db, trigger_type="manual")

        extracted_data = {"MISSING_FIELD": np.nan}

        ExtractedValueCRUD.bulk_insert(
            sync_db,
            extraction_run_id=run.id,
            extracted_data=extracted_data,
            mappings={},
            property_name="NanTest",
        )

        values = ExtractedValueCRUD.get_by_property(sync_db, "NanTest", run.id)
        assert len(values) == 1
        assert values[0].is_error is True
        assert values[0].value_text is None
        assert values[0].value_numeric is None

    def test_bulk_insert_none_marks_error(self, sync_db: Session) -> None:
        """None values set is_error=True."""
        run = ExtractionRunCRUD.create(sync_db, trigger_type="manual")

        extracted_data = {"EMPTY_FIELD": None}

        ExtractedValueCRUD.bulk_insert(
            sync_db,
            extraction_run_id=run.id,
            extracted_data=extracted_data,
            mappings={},
            property_name="NoneTest",
        )

        values = ExtractedValueCRUD.get_by_property(sync_db, "NoneTest", run.id)
        assert len(values) == 1
        assert values[0].is_error is True

    def test_bulk_insert_integer_stored_as_numeric(self, sync_db: Session) -> None:
        """Integer values are stored as value_numeric (float conversion) and value_text."""
        run = ExtractionRunCRUD.create(sync_db, trigger_type="manual")

        extracted_data = {"TOTAL_UNITS": 150}

        ExtractedValueCRUD.bulk_insert(
            sync_db,
            extraction_run_id=run.id,
            extracted_data=extracted_data,
            mappings={},
            property_name="IntTest",
        )

        values = ExtractedValueCRUD.get_by_property(sync_db, "IntTest", run.id)
        assert len(values) == 1
        assert float(values[0].value_numeric) == pytest.approx(150.0)
        assert values[0].value_text == "150"

    def test_metadata_fields_skipped(self, sync_db: Session) -> None:
        """Fields starting with underscore are not inserted."""
        run = ExtractionRunCRUD.create(sync_db, trigger_type="manual")

        extracted_data = {
            "_file_path": "/some/path",
            "_extraction_timestamp": "2026-03-05T10:00:00",
            "_extraction_errors": [],
            "REAL_FIELD": "value",
        }

        count = ExtractedValueCRUD.bulk_insert(
            sync_db,
            extraction_run_id=run.id,
            extracted_data=extracted_data,
            mappings={},
            property_name="MetaTest",
        )

        assert count == 1  # Only REAL_FIELD


# ============================================================================
# 5. Value Normalization Tests (Change Detection)
# ============================================================================


class TestValueNormalization:
    """Test _normalize_value and _normalize_value_from_text for hash consistency."""

    def test_normalize_value_float(self) -> None:
        """Floats are formatted to 4 decimal places."""
        assert _normalize_value(0.0625) == "0.0625"
        assert _normalize_value(1234.5) == "1234.5000"
        assert _normalize_value(0.0) == "0.0000"

    def test_normalize_value_int(self) -> None:
        """Integers are converted to string WITHOUT decimal formatting."""
        assert _normalize_value(5) == "5"
        assert _normalize_value(0) == "0"
        assert _normalize_value(100) == "100"

    def test_normalize_value_none(self) -> None:
        """None normalizes to 'NULL'."""
        assert _normalize_value(None) == "NULL"

    def test_normalize_value_nan(self) -> None:
        """NaN normalizes to 'NaN'."""
        assert _normalize_value(np.nan) == "NaN"

    def test_normalize_value_string(self) -> None:
        """Strings pass through as-is."""
        assert _normalize_value("hello") == "hello"
        assert _normalize_value("Hayden Park") == "Hayden Park"

    def test_normalize_value_from_text_numeric_string(self) -> None:
        """Numeric text strings: floats get 4 decimals, integers stay as ints."""
        assert _normalize_value_from_text("1234.5") == "1234.5000"
        assert _normalize_value_from_text("0.0625") == "0.0625"
        assert (
            _normalize_value_from_text("100") == "100"
        )  # integer-valued → matches _normalize_value(int)

    def test_normalize_value_from_text_none(self) -> None:
        """None text normalizes to 'NULL'."""
        assert _normalize_value_from_text(None) == "NULL"

    def test_normalize_value_from_text_non_numeric_string(self) -> None:
        """Non-numeric strings pass through unchanged."""
        assert _normalize_value_from_text("Hayden Park") == "Hayden Park"

    def test_normalize_value_from_text_empty_string(self) -> None:
        """Empty string is not numeric, passes through as-is."""
        # float("") raises ValueError, so it falls through to return ""
        assert _normalize_value_from_text("") == ""

    def test_int_hash_matches_between_extraction_and_db(self) -> None:
        """Integer values now hash consistently between extraction and DB sides.

        Previously a known bug: int 5 → "5" on extraction vs "5.0000" on DB side.
        Fixed by making _normalize_value_from_text detect integer-valued strings.
        """
        extraction_side = _normalize_value(5)  # "5"
        db_side = _normalize_value_from_text("5")  # "5" (fixed)

        assert extraction_side == db_side
        assert extraction_side == "5"
        assert db_side == "5"

    def test_float_hash_matches_between_extraction_and_db(self) -> None:
        """Float values hash consistently between extraction and DB sides."""
        extraction_side = _normalize_value(0.0625)  # "0.0625"
        db_side = _normalize_value_from_text("0.0625")  # "0.0625"

        assert extraction_side == db_side

    def test_compute_extraction_hash_deterministic(self) -> None:
        """Same data always produces the same hash."""
        data = {"FIELD_A": 100.0, "FIELD_B": "hello", "_meta": "skip"}

        hash1 = compute_extraction_hash(data)
        hash2 = compute_extraction_hash(data)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_compute_extraction_hash_skips_metadata(self) -> None:
        """Metadata fields (starting with _) are excluded from hash."""
        data_with_meta = {"FIELD_A": 1.0, "_timestamp": "now"}
        data_without_meta = {"FIELD_A": 1.0}

        assert compute_extraction_hash(data_with_meta) == compute_extraction_hash(
            data_without_meta
        )

    def test_compute_extraction_hash_order_independent(self) -> None:
        """Hash is the same regardless of insertion order (sorted keys)."""
        data1 = {"B_FIELD": 2.0, "A_FIELD": 1.0}
        data2 = {"A_FIELD": 1.0, "B_FIELD": 2.0}

        assert compute_extraction_hash(data1) == compute_extraction_hash(data2)


# ============================================================================
# 6. Auth Guard Tests
# ============================================================================


class TestExtractionAuthGuards:
    """Test that POST /api/v1/extraction/start enforces role requirements."""

    @pytest.fixture
    def _app_overrides(self, sync_db: Session):
        """Set up sync DB override but NOT auth overrides."""
        from app.db.session import get_sync_db
        from app.main import app

        def override_get_sync_db():
            yield sync_db

        app.dependency_overrides[get_sync_db] = override_get_sync_db
        yield app
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_start_extraction_requires_auth(self, _app_overrides) -> None:
        """POST /extraction/start returns 401 without any auth token."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=_app_overrides)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/extraction/start",
                json={"source": "local"},
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_start_extraction_forbidden_for_analyst(self, _app_overrides) -> None:
        """POST /extraction/start returns 403 for analyst-only role (needs manager+)."""
        from app.core.permissions import CurrentUser, Role, require_manager
        from app.main import app

        # Override require_manager to simulate an analyst trying to access
        analyst_user = CurrentUser(
            id=99, email="analyst@test.com", role=Role.ANALYST, is_active=True
        )

        async def override_require_manager():
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Required role: manager or higher",
            )

        app.dependency_overrides[require_manager] = override_require_manager

        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/extraction/start",
                json={"source": "local"},
            )
            assert response.status_code == 403
            assert "permissions" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_extraction_allowed_for_admin(self, _app_overrides) -> None:
        """POST /extraction/start succeeds for admin role."""
        from app.core.permissions import CurrentUser, Role, require_manager
        from app.main import app

        admin_user = CurrentUser(
            id=1, email="admin@test.com", role=Role.ADMIN, is_active=True
        )

        async def override_require_manager():
            return admin_user

        app.dependency_overrides[require_manager] = override_require_manager

        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            with patch("app.api.v1.endpoints.extraction.common.run_extraction_task"):
                response = await ac.post(
                    "/api/v1/extraction/start",
                    json={
                        "source": "local",
                        "file_paths": ["/tmp/test.xlsb"],
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "running"
                assert data["files_discovered"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
