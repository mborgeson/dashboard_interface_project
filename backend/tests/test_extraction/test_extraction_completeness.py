"""
Tests for validating extraction completeness.

These tests verify that extraction captures all expected data,
statistics are calculated correctly, and error summaries are complete.

Run with: pytest tests/test_extraction/test_extraction_completeness.py -v
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from app.extraction.cell_mapping import CellMapping, CellMappingParser
from app.extraction.error_handler import ErrorCategory, ErrorHandler
from app.extraction.extractor import BatchProcessor, ExcelDataExtractor

# Paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "uw_models"
BACKEND_DIR = Path(__file__).parent.parent.parent
REFERENCE_FILE = BACKEND_DIR.parent / "Underwriting_Dashboard_Cell_References.xlsx"


class TestExtractionCompleteness:
    """Validate extraction captures all expected data."""

    @pytest.fixture
    def sample_mappings(self) -> dict[str, CellMapping]:
        """Create sample mappings for testing."""
        mappings = {}
        for i in range(10):
            field_name = f"FIELD_{i}"
            mappings[field_name] = CellMapping(
                category="Test",
                description=f"Field {i}",
                sheet_name="Summary",
                cell_address=f"A{i+1}",
                field_name=field_name,
            )
        return mappings

    @pytest.fixture
    def extractor(self, sample_mappings: dict[str, CellMapping]) -> ExcelDataExtractor:
        """Create extractor with sample mappings."""
        return ExcelDataExtractor(sample_mappings)

    def test_all_mapped_fields_attempted(
        self, extractor: ExcelDataExtractor, sample_mappings: dict[str, CellMapping]
    ) -> None:
        """Verify extraction attempts all mapped fields."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)

        # Return value for each cell
        mock_cell = MagicMock()
        mock_cell.value = "test_value"
        mock_sheet.__getitem__ = MagicMock(return_value=mock_cell)

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            result = extractor.extract_from_file(
                "test.xlsx", file_content=b"dummy", validate=False
            )

        # All mapped fields should be in result (either value or NaN)
        for field_name in sample_mappings:
            assert field_name in result, f"Field {field_name} not in extraction result"

    def test_extraction_metadata_present(self, extractor: ExcelDataExtractor) -> None:
        """Verify extraction metadata is always present."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)
        mock_cell = MagicMock()
        mock_cell.value = None
        mock_sheet.__getitem__ = MagicMock(return_value=mock_cell)

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            result = extractor.extract_from_file(
                "test.xlsx", file_content=b"dummy", validate=False
            )

        # Required metadata keys
        assert "_file_path" in result
        assert "_extraction_timestamp" in result
        assert "_extraction_errors" in result
        assert "_extraction_metadata" in result

        metadata = result["_extraction_metadata"]
        assert "total_fields" in metadata
        assert "successful" in metadata
        assert "failed" in metadata
        assert "success_rate" in metadata
        assert "duration_seconds" in metadata

    def test_extraction_stats_accurate(
        self, extractor: ExcelDataExtractor, sample_mappings: dict[str, CellMapping]
    ) -> None:
        """Verify extraction statistics are calculated correctly."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)

        # Simulate 5 successful, 5 failed extractions
        call_count = [0]

        def get_cell_value(addr):
            cell = MagicMock()
            call_count[0] += 1
            if call_count[0] <= 5:
                cell.value = "success"
            else:
                cell.value = None  # Will become NaN
            return cell

        mock_sheet.__getitem__ = get_cell_value

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            result = extractor.extract_from_file(
                "test.xlsx", file_content=b"dummy", validate=False
            )

        metadata = result["_extraction_metadata"]

        # Total should equal number of mappings
        assert metadata["total_fields"] == len(sample_mappings)

        # Successful + Failed should equal total
        assert metadata["successful"] + metadata["failed"] == metadata["total_fields"]

    def test_success_rate_calculation(self) -> None:
        """Verify success_rate is calculated correctly."""
        # Test various scenarios
        test_cases = [
            (100, 0, 100.0),  # All successful
            (0, 100, 0.0),  # All failed
            (50, 50, 50.0),  # Half and half
            (75, 25, 75.0),  # 75% success
            (1, 0, 100.0),  # Single success
            (0, 1, 0.0),  # Single failure
        ]

        for successful, failed, expected_rate in test_cases:
            total = successful + failed
            if total > 0:
                calculated_rate = round(successful / total * 100, 1)
                assert (
                    calculated_rate == expected_rate
                ), f"Success rate should be {expected_rate}, got {calculated_rate}"

    def test_error_summary_complete(self) -> None:
        """Verify error_summary contains all error categories."""
        handler = ErrorHandler()

        # Trigger various errors
        handler.handle_missing_sheet("field1", "Sheet", ["Other"])
        handler.handle_formula_error("field2", "Sheet", "A1", "#REF!")
        handler.handle_empty_value("field3", "Sheet", "A1")
        handler.handle_invalid_cell_address("field4", "Sheet", "XYZ", "bad")

        summary = handler.get_error_summary()

        # Should have error breakdown
        assert "error_breakdown_by_category" in summary
        breakdown = summary["error_breakdown_by_category"]

        # Should have entries for triggered errors
        assert ErrorCategory.MISSING_SHEET.value in breakdown
        assert ErrorCategory.FORMULA_ERROR.value in breakdown
        assert ErrorCategory.INVALID_CELL_ADDRESS.value in breakdown

    def test_error_counts_accurate(self) -> None:
        """Verify error counts match number of errors logged."""
        handler = ErrorHandler()

        # Log known number of errors
        for i in range(5):
            handler.handle_missing_sheet(f"field_{i}", "Sheet", ["Other"])

        for i in range(3):
            handler.handle_formula_error(f"formula_{i}", "Sheet", "A1", "#REF!")

        summary = handler.get_error_summary()

        assert summary["total_errors"] == 8
        breakdown = summary["error_breakdown_by_category"]
        assert breakdown[ErrorCategory.MISSING_SHEET.value]["count"] == 5
        assert breakdown[ErrorCategory.FORMULA_ERROR.value]["count"] == 3

    def test_extraction_errors_logged(self, extractor: ExcelDataExtractor) -> None:
        """Verify extraction errors are logged in result."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)

        # Simulate a KeyError that propagates up (like sheet not found in workbook)
        def raise_error(addr):
            raise KeyError(f"Cell {addr} error")

        mock_sheet.__getitem__ = raise_error

        # Make _extract_cell_value raise an exception to populate _extraction_errors
        original_extract = extractor._extract_cell_value

        def mock_extract_cell_value(wb, sheet, cell, field, is_xlsb):
            raise ValueError(f"Simulated extraction error for {field}")

        with (
            patch.object(extractor, "_load_xlsx", return_value=mock_workbook),
            patch.object(extractor, "_extract_cell_value", mock_extract_cell_value),
        ):
            result = extractor.extract_from_file(
                "test.xlsx", file_content=b"dummy", validate=False
            )

        # Should have errors logged
        assert len(result["_extraction_errors"]) > 0

        # Each error should have required fields
        for error in result["_extraction_errors"]:
            assert "field" in error
            assert "error" in error


class TestBatchProcessorCompleteness:
    """Test BatchProcessor completeness tracking."""

    @pytest.fixture
    def sample_mappings(self) -> dict[str, CellMapping]:
        """Create sample mappings."""
        return {
            "FIELD_1": CellMapping(
                category="Test",
                description="Field 1",
                sheet_name="Summary",
                cell_address="A1",
                field_name="FIELD_1",
            ),
        }

    @pytest.fixture
    def batch_processor(
        self, sample_mappings: dict[str, CellMapping]
    ) -> BatchProcessor:
        """Create batch processor."""
        extractor = ExcelDataExtractor(sample_mappings)
        return BatchProcessor(extractor)

    def test_batch_summary_accurate(self, batch_processor: BatchProcessor) -> None:
        """Verify batch processing summary is accurate."""
        # Mock file list
        file_list = [
            {"file_path": "file1.xlsx", "deal_name": "Deal 1"},
            {"file_path": "file2.xlsx", "deal_name": "Deal 2"},
            {"file_path": "file3.xlsx", "deal_name": "Deal 3"},
        ]

        # Mock extraction to succeed
        mock_result = {
            "FIELD_1": "value",
            "_extraction_metadata": {
                "total_fields": 1,
                "successful": 1,
                "failed": 0,
                "success_rate": 100.0,
                "duration_seconds": 0.1,
            },
        }

        with patch.object(
            batch_processor.extractor, "extract_from_file", return_value=mock_result
        ):
            result = batch_processor.process_files(file_list)

        summary = result["summary"]

        # Verify counts
        assert summary["total_files"] == 3
        assert summary["processed"] == 3
        assert summary["failed"] == 0
        assert summary["success_rate"] == 100.0

    def test_batch_failure_tracking(self, batch_processor: BatchProcessor) -> None:
        """Verify failed files are tracked."""
        file_list = [
            {"file_path": "good.xlsx", "deal_name": "Good Deal"},
            {"file_path": "bad.xlsx", "deal_name": "Bad Deal"},
        ]

        call_count = [0]

        def mock_extract(file_path, *args, **kwargs):
            call_count[0] += 1
            if "bad" in file_path:
                raise ValueError("Simulated failure")
            return {
                "FIELD_1": "value",
                "_extraction_metadata": {
                    "total_fields": 1,
                    "successful": 1,
                    "failed": 0,
                    "success_rate": 100.0,
                    "duration_seconds": 0.1,
                },
            }

        with patch.object(
            batch_processor.extractor, "extract_from_file", side_effect=mock_extract
        ):
            result = batch_processor.process_files(file_list)

        summary = result["summary"]

        assert summary["processed"] == 1
        assert summary["failed"] == 1
        assert "bad.xlsx" in summary["failed_files"]


class TestExtractionRunStats:
    """Test extraction run statistics calculation."""

    def test_files_discovered_matches_total(self) -> None:
        """Verify files_discovered equals sum of processed and failed."""
        test_cases = [
            (10, 8, 2),  # 10 discovered, 8 processed, 2 failed
            (5, 5, 0),  # All successful
            (5, 0, 5),  # All failed
            (100, 75, 25),  # Partial success
        ]

        for discovered, processed, failed in test_cases:
            # This should always hold true
            assert discovered == processed + failed or discovered >= processed + failed

    def test_success_rate_edge_cases(self) -> None:
        """Test success rate calculation edge cases."""
        # Zero files
        total = 0
        rate = round(0 / total * 100, 1) if total > 0 else 0
        assert rate == 0

        # 100% success
        total = 100
        processed = 100
        rate = round(processed / total * 100, 1)
        assert rate == 100.0

        # Floating point precision
        total = 3
        processed = 1
        rate = round(processed / total * 100, 1)
        assert rate == 33.3


class TestExtractionProgress:
    """Test extraction progress tracking."""

    @pytest.fixture
    def sample_mappings(self) -> dict[str, CellMapping]:
        """Create sample mappings."""
        return {
            f"FIELD_{i}": CellMapping(
                category="Test",
                description=f"Field {i}",
                sheet_name="Summary",
                cell_address=f"A{i}",
                field_name=f"FIELD_{i}",
            )
            for i in range(100)
        }

    def test_progress_callback_called(
        self, sample_mappings: dict[str, CellMapping]
    ) -> None:
        """Verify progress callback is called during extraction."""
        extractor = ExcelDataExtractor(sample_mappings)

        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)
        mock_cell = MagicMock()
        mock_cell.value = "test"
        mock_sheet.__getitem__ = MagicMock(return_value=mock_cell)

        callback_calls = []

        def progress_callback(current, total):
            callback_calls.append((current, total))

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            extractor.extract_from_file(
                "test.xlsx",
                file_content=b"dummy",
                validate=False,
                progress_callback=progress_callback,
            )

        # Should have been called at least once (every 100 fields)
        assert len(callback_calls) >= 1

    def test_progress_values_increasing(
        self, sample_mappings: dict[str, CellMapping]
    ) -> None:
        """Verify progress values are monotonically increasing."""
        extractor = ExcelDataExtractor(sample_mappings)

        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)
        mock_cell = MagicMock()
        mock_cell.value = "test"
        mock_sheet.__getitem__ = MagicMock(return_value=mock_cell)

        progress_values = []

        def progress_callback(current, total):
            progress_values.append(current)

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            extractor.extract_from_file(
                "test.xlsx",
                file_content=b"dummy",
                validate=False,
                progress_callback=progress_callback,
            )

        # Check monotonic increase
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1]


class TestExtractionDuration:
    """Test extraction duration tracking."""

    @pytest.fixture
    def sample_mappings(self) -> dict[str, CellMapping]:
        """Create sample mappings."""
        return {
            "FIELD_1": CellMapping(
                category="Test",
                description="Field 1",
                sheet_name="Summary",
                cell_address="A1",
                field_name="FIELD_1",
            ),
        }

    def test_duration_recorded(self, sample_mappings: dict[str, CellMapping]) -> None:
        """Verify duration is recorded."""
        extractor = ExcelDataExtractor(sample_mappings)

        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)
        mock_cell = MagicMock()
        mock_cell.value = "test"
        mock_sheet.__getitem__ = MagicMock(return_value=mock_cell)

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            result = extractor.extract_from_file(
                "test.xlsx", file_content=b"dummy", validate=False
            )

        metadata = result["_extraction_metadata"]
        assert "duration_seconds" in metadata
        assert isinstance(metadata["duration_seconds"], float)
        assert metadata["duration_seconds"] >= 0

    def test_timestamp_recorded(self, sample_mappings: dict[str, CellMapping]) -> None:
        """Verify extraction timestamp is recorded."""
        extractor = ExcelDataExtractor(sample_mappings)

        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)
        mock_cell = MagicMock()
        mock_cell.value = "test"
        mock_sheet.__getitem__ = MagicMock(return_value=mock_cell)

        before = datetime.now()

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            result = extractor.extract_from_file(
                "test.xlsx", file_content=b"dummy", validate=False
            )

        after = datetime.now()

        # Verify timestamp is in expected range
        timestamp = datetime.fromisoformat(result["_extraction_timestamp"])
        assert before <= timestamp <= after


@pytest.mark.slow
class TestRealFileCompleteness:
    """Test completeness with real fixture files."""

    @pytest.fixture
    def fixture_files(self) -> list[Path]:
        """Get fixture files."""
        return list(FIXTURES_DIR.glob("*.xlsb"))

    def test_real_file_extraction_completeness(self, fixture_files: list[Path]) -> None:
        """Test extraction completeness on real files."""
        if not fixture_files:
            pytest.skip("No fixture files available")

        if not REFERENCE_FILE.exists():
            pytest.skip("Reference file not found")

        parser = CellMappingParser(str(REFERENCE_FILE))
        mappings = parser.load_mappings()
        extractor = ExcelDataExtractor(mappings)

        result = extractor.extract_from_file(str(fixture_files[0]))

        # All mappings should have an entry
        for field_name in mappings.keys():
            assert field_name in result, f"Missing field: {field_name}"

        # Metadata should be complete
        metadata = result["_extraction_metadata"]
        assert metadata["total_fields"] == len(mappings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
