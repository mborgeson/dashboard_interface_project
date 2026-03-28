"""
Tests for Epic 4.4: Remaining P2 Items.

Covers:
- UR-029: File locking detection (is_file_locked)
- UR-030: ETag-based version comparison
- UR-031: Content hash population (compute_content_hash / compute_content_hash_bytes)
- UR-032: Graph API rate limiting (semaphore + Retry-After)
- UR-037: XLSB workbook close after extraction
- UR-038: Fingerprint row scan limit increased to 500
- UR-039: Batch-level sum reconciliation (NOI = Revenue - OpEx)
- UR-040: Stable duplicate field name suffixes (cell-address-based)
- UR-041: Confidence score column on ExtractedValue
"""

from __future__ import annotations

import asyncio
import hashlib
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# UR-029: File locking detection
# ============================================================================
from app.extraction.sharepoint import (
    _GRAPH_API_SEMAPHORE,
    SharePointClient,
    compute_content_hash,
    compute_content_hash_bytes,
    is_file_locked,
)


class TestIsFileLocked:
    """Tests for is_file_locked() helper."""

    def test_locked_file_checkout(self) -> None:
        """File with publication.level == 'checkout' is locked."""
        metadata = {"publication": {"level": "checkout"}}
        assert is_file_locked(metadata) is True

    def test_locked_file_checkout_uppercase(self) -> None:
        """Case-insensitive check for 'Checkout'."""
        metadata = {"publication": {"level": "Checkout"}}
        assert is_file_locked(metadata) is True

    def test_published_file_not_locked(self) -> None:
        """File with publication.level == 'published' is not locked."""
        metadata = {"publication": {"level": "published"}}
        assert is_file_locked(metadata) is False

    def test_no_publication_key(self) -> None:
        """File without publication metadata is not locked."""
        metadata = {"name": "file.xlsb", "size": 12345}
        assert is_file_locked(metadata) is False

    def test_empty_publication(self) -> None:
        """File with empty publication dict is not locked."""
        metadata = {"publication": {}}
        assert is_file_locked(metadata) is False

    def test_publication_none(self) -> None:
        """File with publication=None is not locked."""
        metadata = {"publication": None}
        assert is_file_locked(metadata) is False

    def test_publication_not_dict(self) -> None:
        """File with non-dict publication is not locked."""
        metadata = {"publication": "some_string"}
        assert is_file_locked(metadata) is False


# ============================================================================
# UR-030: ETag comparison logic
# ============================================================================


class TestETagComparison:
    """Tests for ETag-based version comparison."""

    @pytest.mark.asyncio
    async def test_should_download_when_no_stored_etag(self) -> None:
        """Always download when there is no stored ETag."""
        client = SharePointClient(
            tenant_id="t",
            client_id="c",
            client_secret="s",
            site_url="https://example.sharepoint.com/sites/Test",
        )
        assert await client.should_download("path/to/file.xlsb", None) is True

    @pytest.mark.asyncio
    async def test_should_download_when_etags_differ(self) -> None:
        """Download when remote ETag differs from stored."""
        client = SharePointClient(
            tenant_id="t",
            client_id="c",
            client_secret="s",
            site_url="https://example.sharepoint.com/sites/Test",
        )
        with patch.object(
            client, "get_file_etag", new_callable=AsyncMock, return_value='"new-etag"'
        ):
            result = await client.should_download("path/to/file.xlsb", '"old-etag"')
        assert result is True

    @pytest.mark.asyncio
    async def test_skip_download_when_etags_match(self) -> None:
        """Skip download when ETags match."""
        client = SharePointClient(
            tenant_id="t",
            client_id="c",
            client_secret="s",
            site_url="https://example.sharepoint.com/sites/Test",
        )
        with patch.object(
            client, "get_file_etag", new_callable=AsyncMock, return_value='"same-etag"'
        ):
            result = await client.should_download("path/to/file.xlsb", '"same-etag"')
        assert result is False

    @pytest.mark.asyncio
    async def test_should_download_when_remote_etag_none(self) -> None:
        """Download when remote ETag is unavailable."""
        client = SharePointClient(
            tenant_id="t",
            client_id="c",
            client_secret="s",
            site_url="https://example.sharepoint.com/sites/Test",
        )
        with patch.object(
            client, "get_file_etag", new_callable=AsyncMock, return_value=None
        ):
            result = await client.should_download("path/to/file.xlsb", '"stored"')
        assert result is True


# ============================================================================
# UR-031: Content hash (SHA-256)
# ============================================================================


class TestContentHash:
    """Tests for compute_content_hash and compute_content_hash_bytes."""

    def test_compute_content_hash_bytes_consistent(self) -> None:
        """Same content produces same hash."""
        data = b"test content for hashing"
        hash1 = compute_content_hash_bytes(data)
        hash2 = compute_content_hash_bytes(data)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest is 64 chars

    def test_compute_content_hash_bytes_correct(self) -> None:
        """Hash matches hashlib.sha256 directly."""
        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        assert compute_content_hash_bytes(data) == expected

    def test_compute_content_hash_bytes_different_content(self) -> None:
        """Different content produces different hash."""
        hash1 = compute_content_hash_bytes(b"content_a")
        hash2 = compute_content_hash_bytes(b"content_b")
        assert hash1 != hash2

    def test_compute_content_hash_file(self) -> None:
        """compute_content_hash reads file and produces correct hash."""
        content = b"file content for testing sha256"
        expected = hashlib.sha256(content).hexdigest()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsb") as f:
            f.write(content)
            f.flush()
            tmp_path = Path(f.name)

        try:
            result = compute_content_hash(tmp_path)
            assert result == expected
        finally:
            tmp_path.unlink()

    def test_compute_content_hash_empty_file(self) -> None:
        """Empty file produces the well-known empty SHA-256 hash."""
        expected = hashlib.sha256(b"").hexdigest()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp_path = Path(f.name)

        try:
            result = compute_content_hash(tmp_path)
            assert result == expected
        finally:
            tmp_path.unlink()


# ============================================================================
# UR-032: Rate limiting semaphore
# ============================================================================


class TestRateLimiting:
    """Tests for Graph API semaphore and Retry-After handling."""

    def test_semaphore_initial_value(self) -> None:
        """Module-level semaphore allows 10 concurrent requests."""
        assert _GRAPH_API_SEMAPHORE._value == 10

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self) -> None:
        """Verify the semaphore actually limits concurrent tasks."""
        max_concurrent = 0
        current_count = 0
        lock = asyncio.Lock()

        async def tracked_task() -> None:
            nonlocal max_concurrent, current_count
            async with _GRAPH_API_SEMAPHORE:
                async with lock:
                    current_count += 1
                    if current_count > max_concurrent:
                        max_concurrent = current_count
                await asyncio.sleep(0.01)
                async with lock:
                    current_count -= 1

        # Launch 20 tasks — only 10 should run concurrently
        tasks = [asyncio.create_task(tracked_task()) for _ in range(20)]
        await asyncio.gather(*tasks)

        assert max_concurrent <= 10


# ============================================================================
# UR-037: XLSB workbook close
# ============================================================================


class TestWorkbookClose:
    """Tests for proper workbook closing after extraction."""

    def test_xlsb_workbook_close_called(self) -> None:
        """Verify close() is called on XLSB workbooks after extraction."""
        from app.extraction.extractor import ExcelDataExtractor

        extractor = ExcelDataExtractor(cell_mappings={})

        # Mock the workbook loader to return a mock with close()
        mock_wb = MagicMock()
        mock_wb.sheets = []
        mock_wb.close = MagicMock()
        # Ensure no _cache_stats attribute exists (avoids MagicMock comparison issues)
        del mock_wb._cache_stats

        with patch.object(extractor, "_load_xlsb", return_value=mock_wb):
            with patch.object(extractor, "validate_file", return_value=(True, None)):
                extractor.extract_from_file("test.xlsb", b"fake_content")

        mock_wb.close.assert_called_once()

    def test_xlsx_workbook_close_called(self) -> None:
        """Verify close() is called on XLSX workbooks after extraction."""
        from app.extraction.extractor import ExcelDataExtractor

        extractor = ExcelDataExtractor(cell_mappings={})

        mock_wb = MagicMock()
        mock_wb.sheetnames = []
        mock_wb.close = MagicMock()

        with patch.object(extractor, "_load_xlsx", return_value=mock_wb):
            with patch.object(extractor, "validate_file", return_value=(True, None)):
                extractor.extract_from_file("test.xlsx", b"fake_content")

        mock_wb.close.assert_called_once()


# ============================================================================
# UR-038: Fingerprint row scan limit = 500
# ============================================================================


class TestFingerprintRowLimit:
    """Tests that fingerprint row scanning limit is 500."""

    def test_xlsb_scan_limit_500(self) -> None:
        """Verify the xlsb fingerprinter stops at 500 rows."""
        import inspect

        from app.extraction.fingerprint import _fingerprint_xlsb

        source = inspect.getsource(_fingerprint_xlsb)
        assert "row_idx > 500" in source

    def test_xlsx_scan_limit_500(self) -> None:
        """Verify the xlsx fingerprinter stops at 500 rows."""
        import inspect

        from app.extraction.fingerprint import _fingerprint_xlsx

        source = inspect.getsource(_fingerprint_xlsx)
        assert "row_idx > 500" in source


# ============================================================================
# UR-039: NOI reconciliation checks
# ============================================================================
from app.extraction.reconciliation_checks import (
    ReconciliationResult,
    check_noi_reconciliation,
    run_reconciliation_checks,
)


class TestNOIReconciliation:
    """Tests for check_noi_reconciliation and run_reconciliation_checks."""

    def test_noi_passes_when_correct(self) -> None:
        """NOI = Revenue - Expenses passes check."""
        data = {
            "TOTAL_REVENUE": 1_000_000.0,
            "TOTAL_EXPENSES": 400_000.0,
            "NOI": 600_000.0,
        }
        result = check_noi_reconciliation(data, property_name="Test Property")
        assert result is not None
        assert result.passed is True
        assert result.check_name == "noi_equals_revenue_minus_expenses"

    def test_noi_fails_when_incorrect(self) -> None:
        """NOI != Revenue - Expenses fails check."""
        data = {
            "TOTAL_REVENUE": 1_000_000.0,
            "TOTAL_EXPENSES": 400_000.0,
            "NOI": 500_000.0,  # Should be 600K
        }
        result = check_noi_reconciliation(data, property_name="Test Property")
        assert result is not None
        assert result.passed is False
        assert result.difference == 100_000.0

    def test_noi_within_tolerance(self) -> None:
        """Difference within 5% tolerance passes."""
        data = {
            "TOTAL_REVENUE": 1_000_000.0,
            "TOTAL_EXPENSES": 400_000.0,
            "NOI": 585_000.0,  # 2.5% off from 600K
        }
        result = check_noi_reconciliation(data, property_name="Test Property")
        assert result is not None
        assert result.passed is True

    def test_noi_returns_none_missing_revenue(self) -> None:
        """Returns None when revenue is missing."""
        data = {"TOTAL_EXPENSES": 400_000.0, "NOI": 600_000.0}
        result = check_noi_reconciliation(data, property_name="Test Property")
        assert result is None

    def test_noi_returns_none_missing_expenses(self) -> None:
        """Returns None when expenses is missing."""
        data = {"TOTAL_REVENUE": 1_000_000.0, "NOI": 600_000.0}
        result = check_noi_reconciliation(data, property_name="Test Property")
        assert result is None

    def test_noi_returns_none_missing_noi(self) -> None:
        """Returns None when NOI is missing."""
        data = {"TOTAL_REVENUE": 1_000_000.0, "TOTAL_EXPENSES": 400_000.0}
        result = check_noi_reconciliation(data, property_name="Test Property")
        assert result is None

    def test_noi_uses_effective_gross_income_fallback(self) -> None:
        """Uses EFFECTIVE_GROSS_INCOME when TOTAL_REVENUE is absent."""
        data = {
            "EFFECTIVE_GROSS_INCOME": 1_000_000.0,
            "TOTAL_EXPENSES": 400_000.0,
            "NOI": 600_000.0,
        }
        result = check_noi_reconciliation(data, property_name="Test Property")
        assert result is not None
        assert result.passed is True

    def test_noi_uses_noi_year_1_fallback(self) -> None:
        """Uses NOI_YEAR_1 when NOI is absent."""
        data = {
            "TOTAL_REVENUE": 1_000_000.0,
            "TOTAL_EXPENSES": 400_000.0,
            "NOI_YEAR_1": 600_000.0,
        }
        result = check_noi_reconciliation(data, property_name="Test Property")
        assert result is not None
        assert result.passed is True

    def test_noi_custom_tolerance(self) -> None:
        """Custom tolerance of 10% changes pass/fail boundary."""
        data = {
            "TOTAL_REVENUE": 1_000_000.0,
            "TOTAL_EXPENSES": 400_000.0,
            "NOI": 550_000.0,  # ~8.3% off from 600K
        }
        # 5% tolerance → fail
        result_strict = check_noi_reconciliation(data, tolerance=0.05)
        assert result_strict is not None
        assert result_strict.passed is False

        # 10% tolerance → pass
        result_lenient = check_noi_reconciliation(data, tolerance=0.10)
        assert result_lenient is not None
        assert result_lenient.passed is True

    def test_noi_negative_values(self) -> None:
        """Handles negative NOI correctly."""
        data = {
            "TOTAL_REVENUE": 300_000.0,
            "TOTAL_EXPENSES": 400_000.0,
            "NOI": -100_000.0,
        }
        result = check_noi_reconciliation(data, property_name="Loss Property")
        assert result is not None
        assert result.passed is True

    def test_noi_string_values_coerced(self) -> None:
        """String numeric values are safely coerced."""
        data = {
            "TOTAL_REVENUE": "1000000",
            "TOTAL_EXPENSES": "400000",
            "NOI": "600000",
        }
        result = check_noi_reconciliation(data, property_name="Test")
        assert result is not None
        assert result.passed is True


class TestRunReconciliationChecks:
    """Tests for run_reconciliation_checks (orchestrator)."""

    def test_returns_empty_when_insufficient_data(self) -> None:
        """Returns empty list when no check can be performed."""
        results = run_reconciliation_checks({}, property_name="Test")
        assert results == []

    def test_returns_noi_result_when_data_present(self) -> None:
        """Returns NOI check result when data is present."""
        data = {
            "TOTAL_REVENUE": 1_000_000.0,
            "TOTAL_EXPENSES": 400_000.0,
            "NOI": 600_000.0,
        }
        results = run_reconciliation_checks(data, property_name="Test")
        assert len(results) == 1
        assert results[0].check_name == "noi_equals_revenue_minus_expenses"
        assert results[0].passed is True

    def test_result_dataclass_fields(self) -> None:
        """ReconciliationResult has all expected fields."""
        r = ReconciliationResult(
            property_name="Test",
            check_name="test_check",
            expected_value=100.0,
            actual_value=105.0,
            difference=5.0,
            tolerance=0.05,
            passed=True,
        )
        assert r.property_name == "Test"
        assert r.check_name == "test_check"
        assert r.expected_value == 100.0
        assert r.actual_value == 105.0
        assert r.difference == 5.0
        assert r.tolerance == 0.05
        assert r.passed is True


# ============================================================================
# UR-040: Duplicate field name suffixes (cell-address-based)
# ============================================================================


class TestDuplicateFieldNameSuffix:
    """Tests for cell-address-based duplicate field naming."""

    def test_duplicate_names_get_cell_address_suffix(self) -> None:
        """Duplicate field names are suffixed with cell address, not counter."""
        from unittest.mock import MagicMock

        import pandas as pd

        from app.extraction.cell_mapping import CellMappingParser

        # Create a mock parser with a reference file
        parser = CellMappingParser("/fake/path.xlsx")

        # Simulate a DataFrame with duplicate descriptions
        data = {
            "A": [None, None, None],
            "B": ["Revenue", "Revenue", "Revenue"],  # category
            "C": ["NOI", "NOI", "Unique Field"],  # description (duplicated)
            "D": ["Summary", "Cash Flow", "Summary"],  # sheet
            "E": [None, None, None],
            "F": [None, None, None],
            "G": ["B15", "D20", "E5"],  # cell address
        }
        df = pd.DataFrame(data)

        with patch("pandas.read_excel", return_value=df):
            with patch.object(Path, "exists", return_value=True):
                mappings = parser.load_mappings()

        # The "NOI" field should appear twice, suffixed with cell address
        field_names = list(mappings.keys())
        assert "NOI_B15" in field_names
        assert "NOI_D20" in field_names
        assert "UNIQUE_FIELD" in field_names

    def test_unique_fields_not_suffixed(self) -> None:
        """Fields with unique names are not suffixed."""
        import pandas as pd

        from app.extraction.cell_mapping import CellMappingParser

        parser = CellMappingParser("/fake/path.xlsx")

        data = {
            "A": [None, None],
            "B": ["Revenue", "Expenses"],
            "C": ["TOTAL_REVENUE", "TOTAL_EXPENSES"],
            "D": ["Summary", "Summary"],
            "E": [None, None],
            "F": [None, None],
            "G": ["B10", "B20"],
        }
        df = pd.DataFrame(data)

        with patch("pandas.read_excel", return_value=df):
            with patch.object(Path, "exists", return_value=True):
                mappings = parser.load_mappings()

        field_names = list(mappings.keys())
        assert "TOTAL_REVENUE" in field_names
        assert "TOTAL_EXPENSES" in field_names


# ============================================================================
# UR-041: Confidence score column
# ============================================================================


class TestConfidenceScoreModel:
    """Tests for confidence_score on ExtractedValue model."""

    def test_extracted_value_has_confidence_score(self) -> None:
        """ExtractedValue model has confidence_score column."""
        from app.models.extraction import ExtractedValue

        assert hasattr(ExtractedValue, "confidence_score")

    def test_confidence_score_nullable(self) -> None:
        """confidence_score allows None (nullable)."""
        from app.models.extraction import ExtractedValue

        col = ExtractedValue.__table__.columns["confidence_score"]
        assert col.nullable is True

    def test_confidence_score_numeric_type(self) -> None:
        """confidence_score is Numeric(5, 4)."""
        from sqlalchemy import Numeric

        from app.models.extraction import ExtractedValue

        col = ExtractedValue.__table__.columns["confidence_score"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 5
        assert col.type.scale == 4


class TestConfidenceScoreBulkInsert:
    """Tests for confidence_score population in bulk_insert."""

    def test_bulk_insert_accepts_confidence_scores(self) -> None:
        """bulk_insert signature includes confidence_scores parameter."""
        import inspect

        from app.crud.extraction import ExtractedValueCRUD

        sig = inspect.signature(ExtractedValueCRUD.bulk_insert)
        assert "confidence_scores" in sig.parameters

    def test_bulk_insert_includes_confidence_in_values(self) -> None:
        """confidence_score is included in the values dict when provided."""
        from unittest.mock import MagicMock, patch

        from app.crud.extraction import ExtractedValueCRUD

        mock_db = MagicMock()
        # Mock the property lookup
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        extracted_data = {"PURCHASE_PRICE": 1_000_000.0}
        mappings = {
            "PURCHASE_PRICE": MagicMock(
                category="Acquisition",
                sheet_name="Summary",
                cell_address="B10",
            )
        }
        confidence_scores = {"PURCHASE_PRICE": 0.95}

        # Capture what gets passed to the insert statement
        with patch("app.crud.extraction.insert") as mock_insert:
            mock_stmt = MagicMock()
            mock_insert.return_value = mock_stmt
            mock_stmt.values.return_value = mock_stmt
            mock_stmt.on_conflict_do_update.return_value = mock_stmt
            mock_stmt.excluded = MagicMock()

            ExtractedValueCRUD.bulk_insert(
                db=mock_db,
                extraction_run_id=MagicMock(),
                extracted_data=extracted_data,
                mappings=mappings,
                property_name="Test Property",
                source_file="test.xlsb",
                confidence_scores=confidence_scores,
            )

            # Verify values() was called with confidence_score
            call_args = mock_stmt.values.call_args
            values_list = call_args[0][0]
            assert values_list[0]["confidence_score"] == 0.95


# ============================================================================
# UR-030: MonitoredFile etag field
# ============================================================================


class TestMonitoredFileEtag:
    """Tests for etag field on MonitoredFile model."""

    def test_monitored_file_has_etag(self) -> None:
        """MonitoredFile model has etag column."""
        from app.models.file_monitor import MonitoredFile

        assert hasattr(MonitoredFile, "etag")

    def test_etag_nullable(self) -> None:
        """etag column is nullable."""
        from app.models.file_monitor import MonitoredFile

        col = MonitoredFile.__table__.columns["etag"]
        assert col.nullable is True


# ============================================================================
# UR-029: File locking in _process_file_item
# ============================================================================


class TestProcessFileItemLocking:
    """Tests for file locking detection in _process_file_item."""

    def test_locked_file_skipped_in_discovery(self) -> None:
        """Locked files are added to skipped list during discovery."""
        from app.extraction.sharepoint import DiscoveryResult, SharePointClient

        client = SharePointClient(
            tenant_id="t",
            client_id="c",
            client_secret="s",
            site_url="https://example.sharepoint.com/sites/Test",
        )
        result = DiscoveryResult()

        locked_item = {
            "name": "UW Model - Test.xlsb",
            "size": 50000,
            "lastModifiedDateTime": "2026-03-27T10:00:00Z",
            "file": {},
            "publication": {"level": "checkout"},
        }

        client._process_file_item(
            item=locked_item,
            folder_path="Deals/Test",
            deal_name="Test Deal",
            deal_stage="initial_review",
            result=result,
            use_filter=False,
        )

        assert result.total_scanned == 1
        assert len(result.skipped) == 1
        assert result.skipped[0].skip_reason == "file_locked_checkout"
        assert len(result.files) == 0


# ============================================================================
# Alembic migration validation
# ============================================================================


class TestAlembicMigration:
    """Verify the Alembic migration file structure."""

    def test_migration_revision_chain(self) -> None:
        """Migration has correct revision chain."""
        import importlib.util

        migration_path = (
            Path(__file__).parent.parent
            / "alembic"
            / "versions"
            / "20260327_160000_add_confidence_score_column.py"
        )
        assert migration_path.exists(), f"Migration not found: {migration_path}"

        spec = importlib.util.spec_from_file_location("migration", migration_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.revision == "b2c3d4e5f6a7"
        assert module.down_revision == "a2b3c4d5e6f7"
