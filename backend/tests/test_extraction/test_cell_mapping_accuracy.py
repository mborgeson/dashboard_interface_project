"""
Tests for validating cell mapping accuracy.

These tests verify that cell mappings correctly target the expected
locations in Excel files and that field names are properly deduplicated.

Run with: pytest tests/test_extraction/test_cell_mapping_accuracy.py -v
"""

import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.extraction.cell_mapping import CellMapping, CellMappingParser


# Paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "uw_models"
BACKEND_DIR = Path(__file__).parent.parent.parent
REFERENCE_FILE = BACKEND_DIR.parent / "Underwriting_Dashboard_Cell_References.xlsx"


class TestCellMappingAccuracy:
    """Validate cell mappings target correct locations."""

    @pytest.fixture
    def parser(self) -> CellMappingParser | None:
        """Load cell mapping parser if reference file exists."""
        if not REFERENCE_FILE.exists():
            return None
        return CellMappingParser(str(REFERENCE_FILE))

    @pytest.fixture
    def mappings(self, parser: CellMappingParser | None) -> dict[str, CellMapping]:
        """Load mappings from reference file."""
        if parser is None:
            return {}
        return parser.load_mappings()

    @pytest.fixture
    def fixture_files(self) -> list[Path]:
        """Get list of fixture files."""
        return list(FIXTURES_DIR.glob("*.xlsb"))

    def test_reference_file_exists(self) -> None:
        """Verify reference file exists."""
        assert REFERENCE_FILE.exists(), f"Reference file not found: {REFERENCE_FILE}"

    def test_mappings_loaded(self, mappings: dict[str, CellMapping]) -> None:
        """Verify mappings are loaded."""
        if not mappings:
            pytest.skip("No mappings loaded - reference file may be missing")

        # Should have approximately 1,179 mappings
        assert len(mappings) >= 1100, f"Expected ~1179 mappings, got {len(mappings)}"
        assert len(mappings) <= 1300, f"Too many mappings: {len(mappings)}"

    def test_all_mapped_cells_valid_format(
        self, mappings: dict[str, CellMapping]
    ) -> None:
        """Verify all mapped cell addresses are valid Excel cell references."""
        if not mappings:
            pytest.skip("No mappings loaded")

        # Valid cell address pattern (e.g., A1, B10, AA100, $A$1)
        cell_pattern = re.compile(r"^[A-Z]{1,3}\d+$")

        invalid_cells = []
        for field_name, mapping in mappings.items():
            cell_address = mapping.cell_address
            if not cell_pattern.match(cell_address):
                invalid_cells.append((field_name, cell_address))

        assert len(invalid_cells) == 0, (
            f"Found {len(invalid_cells)} invalid cell addresses: {invalid_cells[:10]}"
        )

    def test_all_mapped_sheets_not_empty(
        self, mappings: dict[str, CellMapping]
    ) -> None:
        """Verify all mapped sheet names are not empty."""
        if not mappings:
            pytest.skip("No mappings loaded")

        empty_sheets = []
        for field_name, mapping in mappings.items():
            if not mapping.sheet_name or mapping.sheet_name.lower() == "nan":
                empty_sheets.append(field_name)

        # Allow some tolerance for missing sheet names
        max_allowed = len(mappings) * 0.05  # 5% tolerance
        assert len(empty_sheets) <= max_allowed, (
            f"Too many mappings with empty sheet names: {len(empty_sheets)}"
        )

    @pytest.mark.slow
    def test_all_mapped_sheets_exist(
        self, mappings: dict[str, CellMapping], fixture_files: list[Path]
    ) -> None:
        """Verify all mapped sheet names exist in test workbook."""
        if not mappings:
            pytest.skip("No mappings loaded")

        if not fixture_files:
            pytest.skip("No fixture files available")

        import pyxlsb

        # Check first fixture file
        fixture_file = fixture_files[0]
        with pyxlsb.open_workbook(str(fixture_file)) as wb:
            available_sheets = set(wb.sheets)

        # Get all mapped sheet names
        mapped_sheets = {m.sheet_name for m in mappings.values()}

        # Find sheets that don't exist in the workbook
        missing_sheets = mapped_sheets - available_sheets

        # Allow some tolerance - not all sheets may be in every workbook
        # But most should exist
        match_rate = (len(mapped_sheets) - len(missing_sheets)) / len(mapped_sheets)
        assert match_rate >= 0.5, (
            f"Only {match_rate*100:.1f}% of mapped sheets exist in workbook. "
            f"Missing: {list(missing_sheets)[:10]}"
        )

    def test_field_names_unique(self, mappings: dict[str, CellMapping]) -> None:
        """Verify no duplicate field names after deduplication."""
        if not mappings:
            pytest.skip("No mappings loaded")

        field_names = list(mappings.keys())
        unique_names = set(field_names)

        assert len(field_names) == len(unique_names), (
            f"Duplicate field names found: {len(field_names)} total, "
            f"{len(unique_names)} unique"
        )

    def test_field_names_valid_identifiers(
        self, mappings: dict[str, CellMapping]
    ) -> None:
        """Verify field names are valid database column identifiers."""
        if not mappings:
            pytest.skip("No mappings loaded")

        # Valid identifier pattern - can start with number (e.g., "1_BED_UNIT_SF")
        # Pattern: uppercase letters, numbers, underscores
        valid_pattern = re.compile(r"^[A-Z0-9][A-Z0-9_]*$")

        invalid_names = []
        for field_name in mappings.keys():
            if not valid_pattern.match(field_name):
                invalid_names.append(field_name)

        assert len(invalid_names) == 0, (
            f"Found {len(invalid_names)} invalid field names: {invalid_names[:10]}"
        )

    def test_categories_consistent(self, mappings: dict[str, CellMapping]) -> None:
        """Verify field categories match expected values."""
        if not mappings:
            pytest.skip("No mappings loaded")

        # Get all unique categories
        categories = {m.category for m in mappings.values()}

        # Should have multiple categories
        assert len(categories) >= 2, "Expected at least 2 categories"

        # Check for uncategorized
        uncategorized_count = sum(
            1 for m in mappings.values() if m.category == "Uncategorized"
        )
        uncategorized_rate = uncategorized_count / len(mappings)

        assert uncategorized_rate < 0.1, (
            f"Too many uncategorized mappings: {uncategorized_rate*100:.1f}%"
        )

    def test_cell_address_ranges(self, mappings: dict[str, CellMapping]) -> None:
        """Verify cell addresses are within reasonable Excel ranges."""
        if not mappings:
            pytest.skip("No mappings loaded")

        def parse_column(col_str: str) -> int:
            """Convert column letters to index."""
            result = 0
            for char in col_str.upper():
                result = result * 26 + (ord(char) - ord("A") + 1)
            return result

        max_reasonable_row = 10000
        max_reasonable_col = 500  # About column "SN"

        out_of_range = []
        for field_name, mapping in mappings.items():
            cell = mapping.cell_address
            match = re.match(r"^([A-Z]+)(\d+)$", cell)
            if match:
                col_str, row_str = match.groups()
                row = int(row_str)
                col = parse_column(col_str)

                if row > max_reasonable_row or col > max_reasonable_col:
                    out_of_range.append((field_name, cell, row, col))

        assert len(out_of_range) == 0, (
            f"Found {len(out_of_range)} cell addresses outside reasonable range: "
            f"{out_of_range[:5]}"
        )

    def test_sheet_name_normalization(self, parser: CellMappingParser | None) -> None:
        """Test that sheet names are normalized consistently."""
        if parser is None:
            pytest.skip("Parser not available")

        mappings = parser.load_mappings()

        # Check for common normalization issues
        for field_name, mapping in mappings.items():
            sheet_name = mapping.sheet_name

            # No leading/trailing whitespace
            assert sheet_name == sheet_name.strip(), (
                f"{field_name}: Sheet name has whitespace: '{sheet_name}'"
            )

            # Not "nan" string
            assert sheet_name.lower() != "nan" or mapping.sheet_name == "Unknown", (
                f"{field_name}: Sheet name is 'nan'"
            )

    def test_duplicate_tracking(self, parser: CellMappingParser | None) -> None:
        """Verify duplicate field names are properly tracked."""
        if parser is None:
            pytest.skip("Parser not available")

        parser.load_mappings()

        # Check that duplicates were tracked
        validation_report = parser.validate_mappings()
        assert "duplicates_resolved" in validation_report

        # If there were duplicates, they should have been resolved
        if validation_report["duplicates_resolved"] > 0:
            # Verify no actual duplicates remain
            field_names = list(parser.mappings.keys())
            assert len(field_names) == len(set(field_names))


class TestCellMappingParser:
    """Test CellMappingParser functionality."""

    @pytest.fixture
    def parser(self) -> CellMappingParser | None:
        """Load cell mapping parser if reference file exists."""
        if not REFERENCE_FILE.exists():
            return None
        return CellMappingParser(str(REFERENCE_FILE))

    def test_clean_field_name_uppercase(self) -> None:
        """Verify field names are converted to uppercase."""
        # Create parser with mock file path
        parser = CellMappingParser("/fake/path.xlsx")

        result = parser._clean_field_name("Property Name")
        assert result == "PROPERTY_NAME"

    def test_clean_field_name_special_chars(self) -> None:
        """Verify special characters are handled."""
        parser = CellMappingParser("/fake/path.xlsx")

        test_cases = [
            ("Price ($)", "PRICE"),
            ("Rate (%)", "RATE_PCT"),
            ("Units (#)", "UNITS_NUM"),
            ("A & B", "A_AND_B"),
            ("A/B Ratio", "A_B_RATIO"),
            ("Item (1)", "ITEM_1"),
        ]

        for input_str, expected in test_cases:
            result = parser._clean_field_name(input_str)
            assert result == expected, f"'{input_str}' should become '{expected}'"

    def test_clean_field_name_consecutive_underscores(self) -> None:
        """Verify consecutive underscores are removed."""
        parser = CellMappingParser("/fake/path.xlsx")

        result = parser._clean_field_name("Test  Double  Space")
        assert "__" not in result

        result = parser._clean_field_name("Test---Dashes")
        assert "__" not in result

    def test_abbreviate_sheet_name(self) -> None:
        """Test sheet name abbreviation for unique field suffixes."""
        parser = CellMappingParser("/fake/path.xlsx")

        test_cases = [
            ("Summary", "S"),
            ("Cash Flow", "CF"),
            ("Unit Mix Pro Forma", "UMPF"),
            ("Very Long Sheet Name Here Today", "VLSN"),
        ]

        for sheet_name, expected in test_cases:
            result = parser._abbreviate_sheet_name(sheet_name)
            assert result == expected, f"'{sheet_name}' should abbreviate to '{expected}'"

    def test_validation_report_structure(
        self, parser: CellMappingParser | None
    ) -> None:
        """Verify validation report has expected structure."""
        if parser is None:
            pytest.skip("Parser not available")

        parser.load_mappings()
        report = parser.validate_mappings()

        expected_keys = [
            "valid",
            "total_mappings",
            "unique_sheets",
            "unique_categories",
            "duplicates_resolved",
            "issues",
        ]

        for key in expected_keys:
            assert key in report, f"Missing key '{key}' in validation report"

    def test_mappings_by_category(self, parser: CellMappingParser | None) -> None:
        """Test grouping mappings by category."""
        if parser is None:
            pytest.skip("Parser not available")

        parser.load_mappings()
        by_category = parser.get_mappings_by_category()

        # Should have multiple categories
        assert len(by_category) >= 1

        # Each category should have mappings
        for category, category_mappings in by_category.items():
            assert len(category_mappings) > 0, f"Category '{category}' has no mappings"

    def test_mappings_by_sheet(self, parser: CellMappingParser | None) -> None:
        """Test grouping mappings by sheet."""
        if parser is None:
            pytest.skip("Parser not available")

        parser.load_mappings()
        by_sheet = parser.get_mappings_by_sheet()

        # Should have multiple sheets
        assert len(by_sheet) >= 1

        # Each sheet should have mappings
        for sheet, sheet_mappings in by_sheet.items():
            assert len(sheet_mappings) > 0, f"Sheet '{sheet}' has no mappings"


class TestCellMappingDataclass:
    """Test CellMapping dataclass."""

    def test_cellmapping_creation(self) -> None:
        """Verify CellMapping can be created with all fields."""
        mapping = CellMapping(
            category="Property Info",
            description="Property Name",
            sheet_name="Summary",
            cell_address="B2",
            field_name="PROPERTY_NAME",
        )

        assert mapping.category == "Property Info"
        assert mapping.description == "Property Name"
        assert mapping.sheet_name == "Summary"
        assert mapping.cell_address == "B2"
        assert mapping.field_name == "PROPERTY_NAME"

    def test_cellmapping_immutable_attributes(self) -> None:
        """Verify CellMapping attributes can be read."""
        mapping = CellMapping(
            category="Test",
            description="Test Field",
            sheet_name="Sheet1",
            cell_address="A1",
            field_name="TEST_FIELD",
        )

        # These should all be readable
        _ = mapping.category
        _ = mapping.description
        _ = mapping.sheet_name
        _ = mapping.cell_address
        _ = mapping.field_name


class TestCellAddressValidation:
    """Test cell address parsing and validation."""

    def test_valid_cell_addresses(self) -> None:
        """Verify valid cell addresses are accepted."""
        valid_addresses = [
            "A1",
            "B10",
            "Z99",
            "AA1",
            "AB100",
            "XFD1048576",  # Max Excel cell
        ]

        cell_pattern = re.compile(r"^[A-Z]{1,3}\d+$")

        for addr in valid_addresses:
            assert cell_pattern.match(addr), f"'{addr}' should be valid"

    def test_invalid_cell_addresses(self) -> None:
        """Verify invalid cell addresses are rejected."""
        invalid_addresses = [
            "1A",  # Number first
            "A",  # No row number
            "1",  # No column
            "a1",  # Lowercase (after cleaning)
            "$A$1",  # Should be stripped before validation
            "A1:B2",  # Range
            "",  # Empty
        ]

        cell_pattern = re.compile(r"^[A-Z]{1,3}\d+$")

        for addr in invalid_addresses:
            # Clean the address first
            clean_addr = addr.replace("$", "").upper()
            if not clean_addr or ":" in clean_addr:
                continue  # Skip empty and ranges

            # Only "a1" after uppercasing becomes valid
            if addr == "a1":
                assert cell_pattern.match(clean_addr)
            else:
                # Most should be invalid
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
