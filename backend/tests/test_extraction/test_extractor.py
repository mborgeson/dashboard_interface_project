"""
Test script to validate extraction module with fixture files.

Run from backend directory:
    python -m pytest tests/test_extraction/test_extractor.py -v

Or run this script directly:
    python tests/test_extraction/test_extractor.py
"""

import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

import zipfile
from unittest.mock import patch

import pytest

from app.extraction.cell_mapping import CellMapping, CellMappingParser
from app.extraction.error_handler import ErrorCategory, ErrorHandler
from app.extraction.extractor import BatchProcessor, ExcelDataExtractor, FileAccessError

# Paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "uw_models"
REFERENCE_FILE = backend_path.parent / "Underwriting_Dashboard_Cell_References.xlsx"


class TestCellMappingParser:
    """Tests for CellMappingParser"""

    def test_load_mappings_file_exists(self):
        """Verify reference file exists"""
        assert REFERENCE_FILE.exists(), f"Reference file not found: {REFERENCE_FILE}"

    def test_load_mappings_count(self):
        """Verify expected number of mappings loaded"""
        parser = CellMappingParser(str(REFERENCE_FILE))
        mappings = parser.load_mappings()

        # Should have approximately 1,179 mappings (may vary slightly with dedup)
        assert len(mappings) >= 1100, f"Expected ~1179 mappings, got {len(mappings)}"
        assert len(mappings) <= 1300, f"Too many mappings: {len(mappings)}"
        print(f"✓ Loaded {len(mappings)} mappings")

    def test_no_duplicate_field_names(self):
        """Verify all field names are unique (fix for DQ-001)"""
        parser = CellMappingParser(str(REFERENCE_FILE))
        mappings = parser.load_mappings()

        field_names = list(mappings.keys())
        unique_names = set(field_names)

        assert len(field_names) == len(unique_names), (
            f"Duplicate field names found: {len(field_names)} total, {len(unique_names)} unique"
        )
        print(f"✓ All {len(field_names)} field names are unique")

    def test_validation_report(self):
        """Test mapping validation"""
        parser = CellMappingParser(str(REFERENCE_FILE))
        parser.load_mappings()

        report = parser.validate_mappings()
        print(f"Validation report: {report}")

        assert report["valid"], f"Validation failed: {report['issues']}"
        print(
            f"✓ Mappings validated: {report['total_mappings']} fields across {report['unique_sheets']} sheets"
        )


class TestErrorHandler:
    """Tests for ErrorHandler"""

    def test_all_error_categories(self):
        """Verify all 9 error categories return NullValue"""
        from app.extraction.error_handler import NullValue, is_null_value

        handler = ErrorHandler()

        # Test each handler returns NullValue
        results = [
            handler.handle_missing_sheet("field", "Sheet1", ["Other"]),
            handler.handle_invalid_cell_address("field", "Sheet1", "XYZ", "bad format"),
            handler.handle_cell_not_found("field", "Sheet1", "Z999"),
            handler.handle_formula_error("field", "Sheet1", "A1", "#REF!"),
            handler.handle_data_type_error("field", "Sheet1", "A1", "abc", "int"),
            handler.handle_empty_value("field", "Sheet1", "A1"),
            handler.handle_parsing_error("field", "Sheet1", "A1", "parse failed"),
            handler.handle_file_access_error("field", "cannot read"),
            handler.handle_unknown_error("field", "Sheet1", "A1", "unknown"),
        ]

        for i, result in enumerate(results):
            assert isinstance(result, NullValue), (
                f"Error handler {i} did not return NullValue, got {type(result)}"
            )
            assert is_null_value(result)

        # Error handlers (all except handle_empty_value) should be is_error=True
        for i, result in enumerate(results):
            if i == 5:  # handle_empty_value without treat_as_error
                assert result.is_error is False
            else:
                assert result.is_error is True

        print("✓ All 9 error categories return NullValue")

    def test_process_cell_value_formula_errors(self):
        """Test formula error detection"""
        from app.extraction.error_handler import NullValue

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
            assert isinstance(result, NullValue), f"Formula error {error} not detected"
            assert result.is_error is True
            assert result.error_category == "formula_error"
            assert result.raw_value == error

        print("✓ All 7 formula error types detected")

    def test_process_cell_value_valid(self):
        """Test valid value processing"""
        handler = ErrorHandler()

        # Numbers
        assert handler.process_cell_value(42, "field", "Sheet", "A1") == 42
        assert handler.process_cell_value(3.14, "field", "Sheet", "A1") == 3.14

        # Strings
        assert handler.process_cell_value("hello", "field", "Sheet", "A1") == "hello"
        assert (
            handler.process_cell_value("  trimmed  ", "field", "Sheet", "A1")
            == "trimmed"
        )

        print("✓ Valid values processed correctly")


class TestExcelDataExtractor:
    """Tests for ExcelDataExtractor with real fixture files"""

    @pytest.fixture
    def extractor(self):
        """Create extractor with loaded mappings"""
        parser = CellMappingParser(str(REFERENCE_FILE))
        mappings = parser.load_mappings()
        return ExcelDataExtractor(mappings)

    @pytest.fixture
    def fixture_files(self):
        """Get list of fixture files"""
        return list(FIXTURES_DIR.glob("*.xlsb"))

    def test_fixtures_exist(self, fixture_files):
        """Verify fixture files exist"""
        assert len(fixture_files) > 0, f"No fixture files found in {FIXTURES_DIR}"
        print(f"✓ Found {len(fixture_files)} fixture files")

    @pytest.mark.slow
    def test_extract_single_file(self, extractor, fixture_files):
        """Test extraction from a single fixture file (slow - processes large Excel files)"""
        if not fixture_files:
            pytest.skip("No fixture files available")

        file_path = str(fixture_files[0])
        print(f"\nExtracting from: {Path(file_path).name}")

        result = extractor.extract_from_file(file_path)

        # Check metadata
        assert "_extraction_metadata" in result
        metadata = result["_extraction_metadata"]

        print(f"  Total fields: {metadata['total_fields']}")
        print(f"  Successful: {metadata['successful']}")
        print(f"  Failed: {metadata['failed']}")
        print(f"  Success rate: {metadata['success_rate']}%")
        print(f"  Duration: {metadata['duration_seconds']}s")

        # Should have some successful extractions
        assert metadata["successful"] > 0, "No successful extractions"
        print(f"✓ Extraction completed with {metadata['success_rate']}% success rate")

    @pytest.mark.slow
    def test_extract_multiple_files(self, extractor, fixture_files):
        """Test extraction from all fixture files (slow - processes large Excel files)"""
        if len(fixture_files) < 2:
            pytest.skip("Need at least 2 fixture files")

        print(f"\nExtracting from {len(fixture_files)} files...")

        total_successful = 0
        total_failed = 0

        for file_path in fixture_files[:3]:  # Limit to first 3 for speed
            result = extractor.extract_from_file(str(file_path))
            metadata = result["_extraction_metadata"]

            total_successful += metadata["successful"]
            total_failed += metadata["failed"]

            print(f"  {Path(file_path).name}: {metadata['success_rate']}% success")

        print(
            f"✓ Processed {min(3, len(fixture_files))} files: {total_successful} successful, {total_failed} failed"
        )


class TestCorruptFileHandling:
    """Tests for graceful handling of corrupt/invalid Excel files."""

    @pytest.fixture
    def simple_extractor(self) -> ExcelDataExtractor:
        """Create extractor with minimal mappings for unit tests."""
        mappings = {
            "PROPERTY_NAME": CellMapping(
                category="General",
                description="Property Name",
                field_name="PROPERTY_NAME",
                sheet_name="Summary",
                cell_address="B2",
            ),
            "TOTAL_UNITS": CellMapping(
                category="General",
                description="Total Units",
                field_name="TOTAL_UNITS",
                sheet_name="Summary",
                cell_address="B3",
            ),
        }
        return ExcelDataExtractor(mappings)

    def test_load_xlsb_bad_zip_file_raises_file_access_error(
        self, simple_extractor: ExcelDataExtractor
    ) -> None:
        """_load_xlsb raises FileAccessError for corrupt zip files."""
        corrupt_content = b"This is not a valid zip file at all"
        with pytest.raises(FileAccessError, match="corrupt or not a valid zip archive"):
            simple_extractor._load_xlsb("Charleston_Row.xlsb", corrupt_content)

    def test_load_xlsx_bad_zip_file_raises_file_access_error(
        self, simple_extractor: ExcelDataExtractor
    ) -> None:
        """_load_xlsx raises FileAccessError for corrupt zip files."""
        corrupt_content = b"This is not a valid zip file at all"
        with pytest.raises(FileAccessError, match="corrupt or not a valid zip archive"):
            simple_extractor._load_xlsx("Zen_on_50.xlsx", corrupt_content)

    def test_extract_from_file_returns_graceful_result_for_corrupt_xlsb(
        self, simple_extractor: ExcelDataExtractor
    ) -> None:
        """extract_from_file returns a result dict (not exception) for corrupt XLSB."""
        corrupt_content = b"not a zip file"
        result = simple_extractor.extract_from_file(
            "Charleston_Row.xlsb",
            file_content=corrupt_content,
            validate=False,
        )

        # Should return a result dict, not raise
        assert isinstance(result, dict)
        assert result["_file_path"] == "Charleston_Row.xlsb"

        # Should have load error metadata
        assert "_load_error" in result
        assert "corrupt" in result["_load_error"]

        # Should record the error in _extraction_errors
        assert len(result["_extraction_errors"]) == 1
        assert result["_extraction_errors"][0]["field"] == "_workbook_load"

        # Metadata should show all fields failed
        metadata = result["_extraction_metadata"]
        assert metadata["successful"] == 0
        assert metadata["failed"] == len(simple_extractor.mappings)
        assert metadata["success_rate"] == 0
        assert metadata["skipped"] is True
        assert "corrupt" in metadata["skip_reason"]

    def test_extract_from_file_returns_graceful_result_for_corrupt_xlsx(
        self, simple_extractor: ExcelDataExtractor
    ) -> None:
        """extract_from_file returns a result dict (not exception) for corrupt XLSX."""
        corrupt_content = b"definitely not an xlsx file"
        result = simple_extractor.extract_from_file(
            "Villas_at_Vesta_View.xlsx",
            file_content=corrupt_content,
            validate=False,
        )

        assert isinstance(result, dict)
        assert "_load_error" in result
        assert result["_extraction_metadata"]["skipped"] is True

    def test_batch_processor_skips_corrupt_file_and_continues(
        self, simple_extractor: ExcelDataExtractor
    ) -> None:
        """BatchProcessor continues processing after a corrupt file."""
        corrupt_content = b"bad zip content"
        file_list = [
            {
                "file_path": "corrupt_file.xlsb",
                "file_content": corrupt_content,
                "deal_name": "Corrupt Deal",
                "deal_stage": "Screening",
                "modified_date": None,
            },
        ]

        processor = BatchProcessor(simple_extractor, batch_size=10, max_workers=1)

        # Mock validation to skip filename pattern check (we're testing load, not filter)
        with patch.object(simple_extractor, "validate_file", return_value=(True, None)):
            batch_result = processor.process_files(file_list)

        # The file should be processed (not crash), with load error in result
        assert batch_result["summary"]["total_files"] == 1
        assert batch_result["summary"]["processed"] == 1
        assert batch_result["summary"]["failed"] == 0

        # The result should contain the graceful error dict
        result = batch_result["results"][0]
        assert "_load_error" in result
        assert result["_extraction_metadata"]["skipped"] is True

    def test_file_access_error_message_includes_filename(
        self, simple_extractor: ExcelDataExtractor
    ) -> None:
        """FileAccessError message includes the file name for diagnostics."""
        corrupt_content = b"nope"
        with pytest.raises(FileAccessError) as exc_info:
            simple_extractor._load_xlsb(
                "/mnt/c/Users/data/Zen_on_50.xlsb", corrupt_content
            )
        assert "Zen_on_50.xlsb" in str(exc_info.value)

    def test_file_access_error_is_extraction_error_subclass(self) -> None:
        """FileAccessError inherits from ExtractionError for catch-all handling."""
        from app.extraction.extractor import ExtractionError

        assert issubclass(FileAccessError, ExtractionError)


def run_quick_test():
    """Quick test without pytest"""
    print("=" * 60)
    print("Extraction Module Quick Test")
    print("=" * 60)

    # Test 1: Load mappings
    print("\n1. Testing CellMappingParser...")
    parser = CellMappingParser(str(REFERENCE_FILE))
    mappings = parser.load_mappings()
    print(f"   ✓ Loaded {len(mappings)} mappings")

    # Validate
    report = parser.validate_mappings()
    print(
        f"   ✓ Validation: {report['total_mappings']} fields, {report['duplicates_resolved']} duplicates resolved"
    )

    # Test 2: Check error handler
    print("\n2. Testing ErrorHandler...")
    import numpy as np

    handler = ErrorHandler()
    from app.extraction.error_handler import NullValue

    result = handler.handle_missing_sheet("test", "Missing", ["Other"])
    assert isinstance(result, NullValue)
    print("   ✓ Error handler returns NullValue for errors")

    # Test 3: Extract from first fixture
    print("\n3. Testing ExcelDataExtractor...")
    fixture_files = list(FIXTURES_DIR.glob("*.xlsb"))

    if fixture_files:
        extractor = ExcelDataExtractor(mappings)
        file_path = str(fixture_files[0])
        print(f"   Extracting from: {Path(file_path).name}")

        result = extractor.extract_from_file(file_path)
        metadata = result["_extraction_metadata"]

        print(
            f"   ✓ Extracted {metadata['successful']}/{metadata['total_fields']} fields ({metadata['success_rate']}%)"
        )
        print(f"   ✓ Duration: {metadata['duration_seconds']}s")

        # Show sample values
        print("\n   Sample extracted values:")
        count = 0
        for key, value in result.items():
            if not key.startswith("_") and value is not None:
                from app.extraction.error_handler import is_null_value

                if not is_null_value(value):
                    print(f"     {key}: {value}")
                    count += 1
                    if count >= 5:
                        break
    else:
        print("   ⚠ No fixture files found, skipping extraction test")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_quick_test()
