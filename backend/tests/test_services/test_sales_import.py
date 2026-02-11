"""Tests for the sales_import service.

Covers helper functions, column mapping, file scanning, and import logic.
"""

import math
import os
import tempfile
from collections.abc import Generator
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.sales_data import SalesData
from app.services.sales_import import (
    COSTAR_COLUMN_MAP,
    FileImportResult,
    FullImportResult,
    _clean_currency,
    _safe_date,
    _safe_float,
    _safe_int,
    _safe_str,
    get_unimported_files,
    import_sales_file,
    scan_sales_files,
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
# 1. _clean_currency() tests
# =============================================================================


class TestCleanCurrency:
    def test_strips_dollar_sign(self):
        assert _clean_currency("$1000") == 1000.0

    def test_strips_commas(self):
        assert _clean_currency("1,500,000") == 1500000.0

    def test_strips_dollar_and_commas(self):
        assert _clean_currency("$1,234,567.89") == 1234567.89

    def test_handles_plain_number_string(self):
        assert _clean_currency("42.5") == 42.5

    def test_returns_numeric_passthrough(self):
        assert _clean_currency(100.0) == 100.0
        assert _clean_currency(0) == 0

    def test_returns_none_for_invalid_string(self):
        assert _clean_currency("N/A") is None
        assert _clean_currency("abc") is None

    def test_handles_none(self):
        assert _clean_currency(None) is None

    def test_handles_whitespace(self):
        assert _clean_currency("  $500  ") == 500.0

    def test_handles_empty_string(self):
        # Empty string after strip -> empty -> float("") raises ValueError -> None
        assert _clean_currency("") is None


# =============================================================================
# 2. _safe_str() tests
# =============================================================================


class TestSafeStr:
    def test_converts_string(self):
        assert _safe_str("hello") == "hello"

    def test_strips_whitespace(self):
        assert _safe_str("  hello  ") == "hello"

    def test_converts_number_to_string(self):
        assert _safe_str(42) == "42"

    def test_returns_none_for_nan(self):
        assert _safe_str(float("nan")) is None

    def test_returns_none_for_none(self):
        assert _safe_str(None) is None

    def test_returns_none_for_pd_nat(self):
        assert _safe_str(pd.NaT) is None

    def test_returns_none_for_empty_string(self):
        assert _safe_str("   ") is None


# =============================================================================
# 3. _safe_float() tests
# =============================================================================


class TestSafeFloat:
    def test_converts_integer(self):
        assert _safe_float(42) == 42.0

    def test_converts_float(self):
        assert _safe_float(3.14) == 3.14

    def test_converts_currency_string(self):
        assert _safe_float("$1,500.00") == 1500.0

    def test_returns_none_for_nan(self):
        assert _safe_float(float("nan")) is None

    def test_returns_none_for_numpy_nan(self):
        assert _safe_float(np.nan) is None

    def test_returns_none_for_none(self):
        assert _safe_float(None) is None

    def test_returns_none_for_inf(self):
        assert _safe_float(float("inf")) is None
        assert _safe_float(float("-inf")) is None

    def test_returns_none_for_invalid_string(self):
        assert _safe_float("not a number") is None

    def test_handles_zero(self):
        assert _safe_float(0) == 0.0

    def test_handles_negative(self):
        assert _safe_float(-123.45) == -123.45


# =============================================================================
# 4. _safe_int() tests
# =============================================================================


class TestSafeInt:
    def test_converts_integer(self):
        assert _safe_int(42) == 42

    def test_converts_float_to_int(self):
        assert _safe_int(42.9) == 42

    def test_converts_string_number(self):
        assert _safe_int("100") == 100

    def test_returns_none_for_nan(self):
        assert _safe_int(float("nan")) is None

    def test_returns_none_for_none(self):
        assert _safe_int(None) is None

    def test_returns_none_for_invalid_string(self):
        assert _safe_int("abc") is None

    def test_handles_zero(self):
        assert _safe_int(0) == 0

    def test_handles_negative(self):
        assert _safe_int(-5.7) == -5


# =============================================================================
# 5. _safe_date() tests
# =============================================================================


class TestSafeDate:
    def test_converts_datetime(self):
        dt = datetime(2024, 6, 15, 10, 30)
        assert _safe_date(dt) == date(2024, 6, 15)

    def test_converts_pd_timestamp(self):
        ts = pd.Timestamp("2024-03-01")
        assert _safe_date(ts) == date(2024, 3, 1)

    def test_converts_string_mdy(self):
        assert _safe_date("06/15/2024") == date(2024, 6, 15)

    def test_converts_string_ymd(self):
        assert _safe_date("2024-06-15") == date(2024, 6, 15)

    def test_converts_string_mdy_dash(self):
        assert _safe_date("06-15-2024") == date(2024, 6, 15)

    def test_returns_none_for_none(self):
        assert _safe_date(None) is None

    def test_returns_none_for_nan(self):
        assert _safe_date(float("nan")) is None

    def test_returns_none_for_pd_nat(self):
        assert _safe_date(pd.NaT) is None

    def test_returns_none_for_invalid_string(self):
        assert _safe_date("not-a-date") is None

    def test_strips_whitespace_from_string(self):
        assert _safe_date("  2024-01-01  ") == date(2024, 1, 1)


# =============================================================================
# 6. COSTAR_COLUMN_MAP tests
# =============================================================================


class TestCostarColumnMap:
    def test_has_expected_entry_count(self):
        """The map should have 101 entries matching all CoStar columns."""
        assert len(COSTAR_COLUMN_MAP) == 101

    def test_maps_key_columns(self):
        assert COSTAR_COLUMN_MAP["Comp ID"] == "comp_id"
        assert COSTAR_COLUMN_MAP["Sale Price"] == "sale_price"
        assert COSTAR_COLUMN_MAP["Property Name"] == "property_name"
        assert COSTAR_COLUMN_MAP["Sale Date"] == "sale_date"
        assert COSTAR_COLUMN_MAP["Number Of Units"] == "number_of_units"

    def test_all_values_are_snake_case(self):
        for db_col in COSTAR_COLUMN_MAP.values():
            assert db_col == db_col.lower(), f"Column {db_col} is not lowercase"
            assert " " not in db_col, f"Column {db_col} contains spaces"


# =============================================================================
# 7. scan_sales_files() tests
# =============================================================================


class TestScanSalesFiles:
    def test_finds_xlsx_files(self, tmp_path):
        """scan_sales_files should find .xlsx files recursively."""
        (tmp_path / "file_a.xlsx").write_bytes(b"fake")
        (tmp_path / "file_b.xlsx").write_bytes(b"fake")
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "file_c.xlsx").write_bytes(b"fake")

        files = scan_sales_files(str(tmp_path))
        assert len(files) == 3
        basenames = [os.path.basename(f) for f in files]
        assert "file_a.xlsx" in basenames
        assert "file_b.xlsx" in basenames
        assert "file_c.xlsx" in basenames

    def test_ignores_temp_excel_files(self, tmp_path):
        """scan_sales_files should skip ~$ temp lock files."""
        (tmp_path / "~$lockedfile.xlsx").write_bytes(b"fake")
        (tmp_path / "real_file.xlsx").write_bytes(b"fake")

        files = scan_sales_files(str(tmp_path))
        assert len(files) == 1
        assert os.path.basename(files[0]) == "real_file.xlsx"

    def test_ignores_non_xlsx(self, tmp_path):
        """scan_sales_files should ignore non-.xlsx files."""
        (tmp_path / "data.csv").write_bytes(b"fake")
        (tmp_path / "notes.txt").write_bytes(b"fake")
        (tmp_path / "real.xlsx").write_bytes(b"fake")

        files = scan_sales_files(str(tmp_path))
        assert len(files) == 1

    def test_empty_directory(self, tmp_path):
        files = scan_sales_files(str(tmp_path))
        assert files == []

    def test_returns_sorted(self, tmp_path):
        (tmp_path / "c.xlsx").write_bytes(b"fake")
        (tmp_path / "a.xlsx").write_bytes(b"fake")
        (tmp_path / "b.xlsx").write_bytes(b"fake")

        files = scan_sales_files(str(tmp_path))
        assert files == sorted(files)


# =============================================================================
# 8. get_unimported_files() tests
# =============================================================================


class TestGetUnimportedFiles:
    def test_filters_already_imported(self, sync_db, tmp_path):
        """Files whose basename is already in the DB should be excluded."""
        (tmp_path / "already_imported.xlsx").write_bytes(b"fake")
        (tmp_path / "new_file.xlsx").write_bytes(b"fake")

        # Insert a record with source_file matching the basename
        now = datetime.now(UTC)
        record = SalesData(
            comp_id="C-100",
            source_file="already_imported.xlsx",
            created_at=now,
            updated_at=now,
        )
        sync_db.add(record)
        sync_db.commit()

        unimported = get_unimported_files(sync_db, str(tmp_path))
        basenames = [os.path.basename(f) for f in unimported]
        assert "new_file.xlsx" in basenames
        assert "already_imported.xlsx" not in basenames

    def test_all_files_new(self, sync_db, tmp_path):
        """When DB is empty, all files should be returned."""
        (tmp_path / "file1.xlsx").write_bytes(b"fake")
        (tmp_path / "file2.xlsx").write_bytes(b"fake")

        unimported = get_unimported_files(sync_db, str(tmp_path))
        assert len(unimported) == 2


# =============================================================================
# 9. import_sales_file() tests
# =============================================================================


def _make_test_excel(filepath: str, rows: list[dict], include_all_headers: bool = True):
    """Helper: create a real .xlsx file with CoStar-like headers.

    Args:
        filepath: Path to write the .xlsx file.
        rows: List of dicts using CoStar header names as keys.
        include_all_headers: If True (default), include all 101 CoStar headers
            with None values for missing columns, so the import service does not
            skip the file due to >10 missing columns.
    """
    if include_all_headers:
        # Ensure every row has all 101 CoStar headers (missing ones get None)
        full_rows = []
        for row in rows:
            full_row = dict.fromkeys(COSTAR_COLUMN_MAP)
            full_row.update(row)
            full_rows.append(full_row)
        df = pd.DataFrame(full_rows)
    else:
        df = pd.DataFrame(rows)
    df.to_excel(filepath, index=False, engine="openpyxl")


class TestImportSalesFile:
    def test_imports_rows(self, sync_db, tmp_path):
        """Test that rows are imported into the database."""
        filepath = str(tmp_path / "sales.xlsx")
        _make_test_excel(
            filepath,
            [
                {
                    "Property Name": "Apt A",
                    "Comp ID": "C-001",
                    "Sale Price": 5000000,
                    "Number Of Units": 50,
                    "Sale Date": "2024-01-15",
                },
                {
                    "Property Name": "Apt B",
                    "Comp ID": "C-002",
                    "Sale Price": 8000000,
                    "Number Of Units": 80,
                    "Sale Date": "2024-02-20",
                },
            ],
        )

        result = import_sales_file(sync_db, filepath, market="Phoenix")

        assert isinstance(result, FileImportResult)
        assert result.rows_imported == 2
        assert result.rows_updated == 0
        assert result.rows_with_null_comp_id == 0
        assert result.errors == []

        # Verify in DB
        all_records = sync_db.query(SalesData).all()
        assert len(all_records) == 2

    def test_handles_null_comp_id(self, sync_db, tmp_path):
        """Rows with null Comp ID get a placeholder."""
        filepath = str(tmp_path / "null_comp.xlsx")
        _make_test_excel(
            filepath,
            [
                {
                    "Property Name": "No Comp",
                    "Comp ID": None,
                    "Sale Price": 3000000,
                },
            ],
        )

        result = import_sales_file(sync_db, filepath, market="Phoenix")

        assert result.rows_with_null_comp_id == 1
        assert result.rows_imported == 1

        record = sync_db.query(SalesData).first()
        assert record.comp_id.startswith("UNKNOWN-")

    def test_upsert_updates_existing(self, sync_db, tmp_path):
        """Importing the same file twice should update, not duplicate."""
        filepath = str(tmp_path / "upsert_test.xlsx")
        _make_test_excel(
            filepath,
            [
                {
                    "Property Name": "Original Name",
                    "Comp ID": "C-UPS",
                    "Sale Price": 5000000,
                },
            ],
        )

        # First import
        result1 = import_sales_file(sync_db, filepath, market="Phoenix")
        assert result1.rows_imported == 1
        assert result1.rows_updated == 0

        # Modify the file to have updated property name
        _make_test_excel(
            filepath,
            [
                {
                    "Property Name": "Updated Name",
                    "Comp ID": "C-UPS",
                    "Sale Price": 6000000,
                },
            ],
        )

        # Second import
        result2 = import_sales_file(sync_db, filepath, market="Phoenix")
        assert result2.rows_imported == 0
        assert result2.rows_updated == 1

        # Only 1 record in DB
        all_records = sync_db.query(SalesData).all()
        assert len(all_records) == 1
        assert all_records[0].property_name == "Updated Name"

    def test_sets_market_and_source_file(self, sync_db, tmp_path):
        """Imported records should have market and source_file metadata."""
        filepath = str(tmp_path / "meta_test.xlsx")
        _make_test_excel(
            filepath,
            [
                {"Comp ID": "C-META", "Property Name": "Meta Apt"},
            ],
        )

        import_sales_file(sync_db, filepath, market="Tucson")

        record = sync_db.query(SalesData).first()
        assert record.market == "Tucson"
        assert record.source_file == "meta_test.xlsx"
        assert record.imported_at is not None

    def test_handles_within_file_duplicate_comp_ids(self, sync_db, tmp_path):
        """Duplicate comp_ids within a single file get suffixed."""
        filepath = str(tmp_path / "dup_comp.xlsx")
        _make_test_excel(
            filepath,
            [
                {"Comp ID": "C-DUP", "Property Name": "Apt 1"},
                {"Comp ID": "C-DUP", "Property Name": "Apt 2"},
            ],
        )

        result = import_sales_file(sync_db, filepath, market="Phoenix")
        assert result.rows_imported == 2

        records = sync_db.query(SalesData).order_by(SalesData.id).all()
        comp_ids = [r.comp_id for r in records]
        assert "C-DUP" in comp_ids
        assert "C-DUP-dup2" in comp_ids

    def test_warnings_on_missing_columns(self, sync_db, tmp_path):
        """File with some missing columns (<=10) should warn but still import."""
        filepath = str(tmp_path / "partial.xlsx")
        # Build a row with all but 5 CoStar headers to trigger warnings but not errors
        all_headers = list(COSTAR_COLUMN_MAP.keys())
        # Remove 5 columns to trigger warning but not "too many missing" error
        removed = all_headers[-5:]
        included = dict.fromkeys(all_headers[:-5])
        included["Comp ID"] = "C-PART"
        included["Property Name"] = "Partial Data"
        _make_test_excel(filepath, [included], include_all_headers=False)

        result = import_sales_file(sync_db, filepath, market="Phoenix")
        # Should have warnings about the 5 missing columns but still import
        assert result.rows_imported == 1
        assert len(result.warnings) > 0
        assert any("Missing columns" in w for w in result.warnings)

    def test_skips_file_when_too_many_columns_missing(self, sync_db, tmp_path):
        """File with >10 missing columns should be skipped entirely."""
        filepath = str(tmp_path / "very_sparse.xlsx")
        _make_test_excel(
            filepath,
            [
                {"Comp ID": "C-SKIP", "Property Name": "Sparse Data"},
            ],
            include_all_headers=False,
        )

        result = import_sales_file(sync_db, filepath, market="Phoenix")
        assert result.rows_imported == 0
        assert len(result.errors) > 0
        assert any("Too many missing columns" in e for e in result.errors)
