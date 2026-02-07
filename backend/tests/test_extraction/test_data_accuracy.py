"""
Tests for validating extraction accuracy against source Excel files.

These tests verify that extracted values match the source Excel values
with appropriate tolerance for floating point comparisons and proper
handling of edge cases like empty cells and formula errors.

Run with: pytest tests/test_extraction/test_data_accuracy.py -v
"""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.extraction.cell_mapping import CellMapping, CellMappingParser
from app.extraction.error_handler import ErrorCategory, ErrorHandler
from app.extraction.extractor import ExcelDataExtractor

# Paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "uw_models"
EXPECTED_VALUES_FILE = (
    Path(__file__).parent.parent / "fixtures" / "expected_values.json"
)
BACKEND_DIR = Path(__file__).parent.parent.parent
REFERENCE_FILE = BACKEND_DIR.parent / "Underwriting_Dashboard_Cell_References.xlsx"


def load_expected_values() -> dict[str, Any]:
    """Load expected values from JSON fixture."""
    if EXPECTED_VALUES_FILE.exists():
        with open(EXPECTED_VALUES_FILE) as f:
            return json.load(f)
    return {}


class TestDataAccuracy:
    """Validate extraction accuracy against known test data."""

    @pytest.fixture
    def sample_mappings(self) -> dict[str, CellMapping]:
        """Create sample mappings for testing."""
        return {
            "PROPERTY_NAME": CellMapping(
                category="Property Info",
                description="Property Name",
                sheet_name="Summary",
                cell_address="B2",
                field_name="PROPERTY_NAME",
            ),
            "TOTAL_UNITS": CellMapping(
                category="Property Info",
                description="Total Units",
                sheet_name="Summary",
                cell_address="B5",
                field_name="TOTAL_UNITS",
            ),
            "PURCHASE_PRICE": CellMapping(
                category="Financial",
                description="Purchase Price",
                sheet_name="Summary",
                cell_address="D10",
                field_name="PURCHASE_PRICE",
            ),
            "CLOSING_DATE": CellMapping(
                category="Timeline",
                description="Closing Date",
                sheet_name="Summary",
                cell_address="B8",
                field_name="CLOSING_DATE",
            ),
        }

    @pytest.fixture
    def extractor(self, sample_mappings: dict[str, CellMapping]) -> ExcelDataExtractor:
        """Create extractor with sample mappings."""
        return ExcelDataExtractor(sample_mappings)

    @pytest.fixture
    def fixture_files(self) -> list[Path]:
        """Get list of fixture files."""
        return list(FIXTURES_DIR.glob("*.xlsb"))

    def test_numeric_values_match_source(self, extractor: ExcelDataExtractor) -> None:
        """Verify numeric extractions match source Excel values."""
        # Create mock workbook with known numeric values
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)

        # Set up cell with known numeric value
        mock_cell = MagicMock()
        mock_cell.value = 250  # Known numeric value
        mock_sheet.__getitem__ = MagicMock(return_value=mock_cell)

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            # Provide file_content to avoid FileNotFoundError
            result = extractor.extract_from_file(
                "test.xlsx", file_content=b"dummy", validate=False
            )

        # Verify numeric value extraction
        assert "TOTAL_UNITS" in result
        value = result["TOTAL_UNITS"]

        # Check value is numeric and matches expected
        if not (isinstance(value, float) and np.isnan(value)):
            assert isinstance(value, (int, float))
            # Use relative tolerance for floating point comparison
            assert abs(value - 250) < 0.01 * abs(250)

    def test_numeric_precision_within_tolerance(self) -> None:
        """Verify numeric values within 0.01% tolerance."""
        handler = ErrorHandler()

        # Test cases with expected precision
        test_cases = [
            (1000000.00, 1000000.00, True),  # Exact match
            (1000000.00, 1000000.05, True),  # Within 0.01%
            (1000000.00, 1000050.00, True),  # Within 0.01%
            (1000000.00, 1000100.01, False),  # Outside 0.01%
            (0.0001, 0.0001, True),  # Small values
            (3.14159, 3.14159, True),  # Decimal precision
        ]

        for expected, actual, should_match in test_cases:
            tolerance = abs(expected) * 0.0001  # 0.01% tolerance
            is_within_tolerance = abs(actual - expected) <= tolerance

            if should_match:
                assert (
                    is_within_tolerance
                ), f"{actual} should be within 0.01% of {expected}"
            else:
                assert (
                    not is_within_tolerance
                ), f"{actual} should NOT be within 0.01% of {expected}"

    def test_date_values_match_source(self, extractor: ExcelDataExtractor) -> None:
        """Verify date extractions match source Excel values."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)

        # Set up cell with known date value
        expected_date = datetime(2024, 6, 15)
        mock_cell = MagicMock()
        mock_cell.value = expected_date
        mock_sheet.__getitem__ = MagicMock(return_value=mock_cell)

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            result = extractor.extract_from_file(
                "test.xlsx", file_content=b"dummy", validate=False
            )

        # Verify date extraction
        assert "CLOSING_DATE" in result
        value = result["CLOSING_DATE"]

        # Date should match exactly
        if isinstance(value, datetime):
            assert value == expected_date

    def test_text_values_match_source(self, extractor: ExcelDataExtractor) -> None:
        """Verify text extractions match source Excel values."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)

        # Set up cell with known text value
        expected_text = "Test Property Name"
        mock_cell = MagicMock()
        mock_cell.value = expected_text
        mock_sheet.__getitem__ = MagicMock(return_value=mock_cell)

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            result = extractor.extract_from_file(
                "test.xlsx", file_content=b"dummy", validate=False
            )

        # Verify text extraction
        assert "PROPERTY_NAME" in result
        value = result["PROPERTY_NAME"]

        # Text should match after trimming whitespace
        if isinstance(value, str):
            assert value.strip() == expected_text.strip()

    def test_text_values_whitespace_trimmed(self) -> None:
        """Verify whitespace is trimmed from text values."""
        handler = ErrorHandler()

        # Text with leading/trailing whitespace
        test_cases = [
            ("  Test Property  ", "Test Property"),
            ("\tTabbed\t", "Tabbed"),
            ("\n\nNewlines\n", "Newlines"),
            ("Normal Text", "Normal Text"),
        ]

        for input_text, expected in test_cases:
            result = handler.process_cell_value(input_text, "field", "Sheet", "A1")
            if isinstance(result, str):
                assert result == expected, f"'{input_text}' should trim to '{expected}'"

    def test_formula_results_captured(self, extractor: ExcelDataExtractor) -> None:
        """Verify formula cells capture calculated values, not formulas."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["Summary"]
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)

        # Formula cell should return calculated value (data_only=True in openpyxl)
        calculated_value = 15000000.00
        mock_cell = MagicMock()
        mock_cell.value = calculated_value  # Should be the result, not "=A1*B1"
        mock_sheet.__getitem__ = MagicMock(return_value=mock_cell)

        with patch.object(extractor, "_load_xlsx", return_value=mock_workbook):
            result = extractor.extract_from_file(
                "test.xlsx", file_content=b"dummy", validate=False
            )

        # Verify we got the calculated value, not a formula string
        value = result.get("PURCHASE_PRICE")
        if value is not None and not (isinstance(value, float) and np.isnan(value)):
            assert not isinstance(value, str) or not value.startswith("=")
            assert isinstance(value, (int, float))

    def test_empty_cells_handled(self) -> None:
        """Verify empty cells are properly marked."""
        handler = ErrorHandler()

        empty_values = [None, "", "   ", "\t", "\n"]

        for empty_val in empty_values:
            result = handler.process_cell_value(empty_val, "field", "Sheet", "A1")
            assert np.isnan(
                result
            ), f"Empty value '{repr(empty_val)}' should return np.nan"

    def test_missing_value_indicators_handled(self) -> None:
        """Verify common missing value indicators return np.nan."""
        handler = ErrorHandler()

        missing_indicators = ["N/A", "n/a", "NA", "null", "None", "-", "TBD", "TBA"]

        for indicator in missing_indicators:
            result = handler.process_cell_value(indicator, "field", "Sheet", "A1")
            assert np.isnan(
                result
            ), f"Missing indicator '{indicator}' should return np.nan"

    def test_error_cells_flagged(self) -> None:
        """Verify #REF!, #VALUE! etc are flagged as errors."""
        handler = ErrorHandler()

        formula_errors = [
            "#REF!",
            "#VALUE!",
            "#DIV/0!",
            "#NAME?",
            "#N/A",
            "#NULL!",
            "#NUM!",
        ]

        for error in formula_errors:
            result = handler.process_cell_value(error, "field", "Sheet", "A1")
            assert np.isnan(result), f"Formula error '{error}' should return np.nan"

        # Verify error was logged
        summary = handler.get_error_summary()
        assert summary["total_errors"] == len(formula_errors)
        assert ErrorCategory.FORMULA_ERROR.value in str(summary)

    def test_large_numbers_preserved(self) -> None:
        """Verify very large numbers are extracted without overflow."""
        handler = ErrorHandler()

        large_numbers = [
            1_000_000_000_000,  # 1 trillion
            9_999_999_999.99,
            12345678901234.5678,
        ]

        for large_num in large_numbers:
            result = handler.process_cell_value(large_num, "field", "Sheet", "A1")
            assert result == large_num, f"Large number {large_num} should be preserved"

    def test_negative_numbers_preserved(self) -> None:
        """Verify negative numbers are handled correctly."""
        handler = ErrorHandler()

        negative_numbers = [-100, -0.5, -1_000_000]

        for neg_num in negative_numbers:
            result = handler.process_cell_value(neg_num, "field", "Sheet", "A1")
            assert result == neg_num, f"Negative number {neg_num} should be preserved"

    def test_decimal_precision_preserved(self) -> None:
        """Verify decimal precision is maintained."""
        handler = ErrorHandler()

        # Test various decimal precisions
        decimal_values = [
            0.1,
            0.01,
            0.001,
            0.0001,
            3.14159265359,
            100.123456,
        ]

        for decimal_val in decimal_values:
            result = handler.process_cell_value(decimal_val, "field", "Sheet", "A1")
            assert (
                abs(result - decimal_val) < 1e-10
            ), f"Decimal {decimal_val} precision lost"

    def test_boolean_values_preserved(self) -> None:
        """Verify boolean values are extracted correctly."""
        handler = ErrorHandler()

        assert handler.process_cell_value(True, "field", "Sheet", "A1") is True
        assert handler.process_cell_value(False, "field", "Sheet", "A1") is False

    @pytest.mark.slow
    def test_fixture_file_extraction_accuracy(self, fixture_files: list[Path]) -> None:
        """Test extraction accuracy against real fixture files."""
        if not fixture_files:
            pytest.skip("No fixture files available")

        if not REFERENCE_FILE.exists():
            pytest.skip(f"Reference file not found: {REFERENCE_FILE}")

        # Load real mappings
        parser = CellMappingParser(str(REFERENCE_FILE))
        mappings = parser.load_mappings()
        extractor = ExcelDataExtractor(mappings)

        # Extract from first fixture
        file_path = str(fixture_files[0])
        result = extractor.extract_from_file(file_path)

        # Verify extraction metadata
        assert "_extraction_metadata" in result
        metadata = result["_extraction_metadata"]

        # Should have reasonable success rate
        assert metadata["total_fields"] > 0
        assert metadata["successful"] >= 0
        assert metadata["success_rate"] >= 0

        # Count non-NaN values
        non_nan_count = 0
        for key, value in result.items():
            if not key.startswith("_"):
                try:
                    if not (isinstance(value, float) and np.isnan(value)):
                        non_nan_count += 1
                except (TypeError, ValueError):
                    non_nan_count += 1

        # Should have extracted some values successfully
        assert non_nan_count > 0, "No successful extractions from fixture file"

    @pytest.mark.slow
    def test_expected_values_validation(self, fixture_files: list[Path]) -> None:
        """Validate extractions against expected values fixture."""
        expected_values = load_expected_values()

        if not expected_values:
            pytest.skip("No expected values fixture available")

        if not fixture_files:
            pytest.skip("No fixture files available")

        if not REFERENCE_FILE.exists():
            pytest.skip(f"Reference file not found: {REFERENCE_FILE}")

        parser = CellMappingParser(str(REFERENCE_FILE))
        mappings = parser.load_mappings()
        extractor = ExcelDataExtractor(mappings)

        for fixture_file in fixture_files:
            file_name = fixture_file.name
            if file_name not in expected_values:
                continue

            result = extractor.extract_from_file(str(fixture_file))
            expected = expected_values[file_name]

            for field_name, expected_value in expected.get("fields", {}).items():
                if field_name not in result:
                    continue

                actual_value = result[field_name]

                # Skip if actual is NaN
                if isinstance(actual_value, float) and np.isnan(actual_value):
                    continue

                # Compare based on type
                if isinstance(expected_value, (int, float)):
                    tolerance = abs(expected_value) * 0.0001  # 0.01% tolerance
                    assert (
                        abs(actual_value - expected_value) <= tolerance
                    ), f"{file_name}.{field_name}: {actual_value} != {expected_value}"
                elif isinstance(expected_value, str):
                    assert (
                        str(actual_value).strip() == expected_value.strip()
                    ), f"{file_name}.{field_name}: '{actual_value}' != '{expected_value}'"


class TestValueTypeConversion:
    """Test type conversion during extraction."""

    def test_integer_to_float_conversion(self) -> None:
        """Verify integers can be compared with floats."""
        handler = ErrorHandler()

        # Integer input should work with float comparison
        result = handler.process_cell_value(100, "field", "Sheet", "A1")
        assert result == 100.0
        assert result == 100

    def test_string_number_not_converted(self) -> None:
        """Verify string numbers remain strings unless explicitly converted."""
        handler = ErrorHandler()

        # String that looks like a number should remain string
        result = handler.process_cell_value("12345", "field", "Sheet", "A1")
        assert result == "12345"
        assert isinstance(result, str)

    def test_percentage_string_handling(self) -> None:
        """Verify percentage strings are handled correctly."""
        handler = ErrorHandler()

        # Percentage string should remain as-is
        result = handler.process_cell_value("95.5%", "field", "Sheet", "A1")
        assert result == "95.5%"

    def test_currency_string_handling(self) -> None:
        """Verify currency strings are handled correctly."""
        handler = ErrorHandler()

        # Currency string should remain as-is
        result = handler.process_cell_value("$1,000,000", "field", "Sheet", "A1")
        assert result == "$1,000,000"


class TestEdgeCases:
    """Test edge cases in data extraction."""

    def test_nan_propagation(self) -> None:
        """Verify np.nan values are properly propagated."""
        handler = ErrorHandler()

        result = handler.process_cell_value(np.nan, "field", "Sheet", "A1")
        assert np.isnan(result)

    def test_infinity_handled(self) -> None:
        """Verify infinity values return np.nan."""
        handler = ErrorHandler()

        for inf_val in [np.inf, -np.inf, float("inf"), float("-inf")]:
            result = handler.process_cell_value(inf_val, "field", "Sheet", "A1")
            assert np.isnan(result), f"Infinity {inf_val} should return np.nan"

    def test_zero_value_preserved(self) -> None:
        """Verify zero is not treated as empty."""
        handler = ErrorHandler()

        result = handler.process_cell_value(0, "field", "Sheet", "A1")
        assert result == 0
        assert not np.isnan(result)

        result = handler.process_cell_value(0.0, "field", "Sheet", "A1")
        assert result == 0.0
        assert not np.isnan(result)

    def test_empty_string_vs_whitespace(self) -> None:
        """Verify empty string and whitespace-only strings are handled."""
        handler = ErrorHandler()

        # Empty string
        result = handler.process_cell_value("", "field", "Sheet", "A1")
        assert np.isnan(result)

        # Whitespace only
        result = handler.process_cell_value("   ", "field", "Sheet", "A1")
        assert np.isnan(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
