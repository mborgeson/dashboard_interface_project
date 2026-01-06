"""
B&R Capital Dashboard - Extraction Validation Module

Provides validation utilities for comparing extracted values against
source Excel files and generating accuracy reports.

Features:
- Value comparison with type-appropriate tolerances
- Completeness validation against cell mappings
- Comprehensive accuracy reporting
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import numpy as np
import structlog

if TYPE_CHECKING:
    from app.extraction.cell_mapping import CellMapping
    from app.models.extraction import ExtractedValue


@dataclass
class ValueComparison:
    """Result of comparing an extracted value against source."""

    field_name: str
    expected_value: Any
    actual_value: Any
    matches: bool
    value_type: str
    tolerance_used: float | None = None
    difference: float | None = None
    error_message: str | None = None


@dataclass
class ValidationReport:
    """Report from validation against source Excel file."""

    source_file: str
    total_fields: int = 0
    matched_fields: int = 0
    mismatched_fields: int = 0
    missing_fields: int = 0
    error_fields: int = 0
    accuracy_rate: float = 0.0
    comparisons: list[ValueComparison] = field(default_factory=list)
    mismatches: list[ValueComparison] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_valid(self) -> bool:
        """Check if extraction meets accuracy threshold (95%)."""
        return self.accuracy_rate >= 95.0


@dataclass
class CompletenessReport:
    """Report from completeness validation against mappings."""

    total_mappings: int = 0
    attempted_fields: int = 0
    successful_fields: int = 0
    failed_fields: int = 0
    missing_fields: int = 0
    completeness_rate: float = 0.0
    missing_field_names: list[str] = field(default_factory=list)
    failed_field_names: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_complete(self) -> bool:
        """Check if all mappings were attempted."""
        return self.attempted_fields >= self.total_mappings


@dataclass
class AccuracyReport:
    """Comprehensive accuracy report for an extraction run."""

    run_id: UUID
    files_validated: int = 0
    total_values: int = 0
    accurate_values: int = 0
    inaccurate_values: int = 0
    error_values: int = 0
    overall_accuracy: float = 0.0
    validation_reports: list[ValidationReport] = field(default_factory=list)
    completeness_report: CompletenessReport | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def meets_threshold(self) -> bool:
        """Check if accuracy meets 95% threshold."""
        return self.overall_accuracy >= 95.0


class ExtractionValidator:
    """
    Validates extraction accuracy against source Excel files.

    Provides comparison utilities with appropriate tolerances for
    different value types and comprehensive reporting.
    """

    # Numeric tolerance (0.01% relative difference)
    NUMERIC_TOLERANCE = 0.0001

    def __init__(self):
        self.logger = structlog.get_logger().bind(component="ExtractionValidator")

    def compare_with_source(
        self,
        extracted: list["ExtractedValue"],
        source_path: str,
        mappings: dict[str, "CellMapping"] | None = None,
    ) -> ValidationReport:
        """
        Compare extracted values against source Excel file.

        Args:
            extracted: List of ExtractedValue objects from extraction
            source_path: Path to source Excel file
            mappings: Optional cell mappings for verification

        Returns:
            ValidationReport with comparison results
        """
        report = ValidationReport(source_file=source_path)
        report.total_fields = len(extracted)

        # Build lookup of extracted values
        extracted_lookup = {ev.field_name: ev for ev in extracted}

        # Load source file for comparison
        source_values = self._load_source_values(source_path, mappings)

        for field_name, expected_value in source_values.items():
            if field_name not in extracted_lookup:
                report.missing_fields += 1
                comparison = ValueComparison(
                    field_name=field_name,
                    expected_value=expected_value,
                    actual_value=None,
                    matches=False,
                    value_type="missing",
                    error_message="Field not in extraction results",
                )
                report.comparisons.append(comparison)
                report.mismatches.append(comparison)
                continue

            ev = extracted_lookup[field_name]
            actual_value = ev.value

            # Handle error values
            if ev.is_error:
                report.error_fields += 1
                comparison = ValueComparison(
                    field_name=field_name,
                    expected_value=expected_value,
                    actual_value=actual_value,
                    matches=False,
                    value_type="error",
                    error_message=f"Extraction error: {ev.error_category}",
                )
                report.comparisons.append(comparison)
                report.mismatches.append(comparison)
                continue

            # Compare values based on type
            comparison = self._compare_values(field_name, expected_value, actual_value)
            report.comparisons.append(comparison)

            if comparison.matches:
                report.matched_fields += 1
            else:
                report.mismatched_fields += 1
                report.mismatches.append(comparison)

        # Calculate accuracy rate
        total_comparable = report.total_fields - report.error_fields
        if total_comparable > 0:
            report.accuracy_rate = round(
                report.matched_fields / total_comparable * 100, 2
            )

        self.logger.info(
            "validation_complete",
            source_file=source_path,
            accuracy_rate=report.accuracy_rate,
            matched=report.matched_fields,
            mismatched=report.mismatched_fields,
        )

        return report

    def validate_completeness(
        self,
        extracted: list["ExtractedValue"],
        mappings: dict[str, "CellMapping"],
    ) -> CompletenessReport:
        """
        Check all mappings were attempted during extraction.

        Args:
            extracted: List of ExtractedValue objects
            mappings: Dictionary of field_name -> CellMapping

        Returns:
            CompletenessReport with coverage statistics
        """
        report = CompletenessReport()
        report.total_mappings = len(mappings)

        # Build lookup of extracted values
        extracted_lookup = {ev.field_name: ev for ev in extracted}
        report.attempted_fields = len(extracted_lookup)

        for field_name in mappings:
            if field_name not in extracted_lookup:
                report.missing_fields += 1
                report.missing_field_names.append(field_name)
                continue

            ev = extracted_lookup[field_name]
            if ev.is_error:
                report.failed_fields += 1
                report.failed_field_names.append(field_name)
            else:
                report.successful_fields += 1

        # Calculate completeness rate
        if report.total_mappings > 0:
            report.completeness_rate = round(
                report.attempted_fields / report.total_mappings * 100, 2
            )

        self.logger.info(
            "completeness_validation",
            total_mappings=report.total_mappings,
            attempted=report.attempted_fields,
            successful=report.successful_fields,
            failed=report.failed_fields,
            missing=report.missing_fields,
        )

        return report

    def generate_accuracy_report(
        self,
        run_id: UUID,
        extracted_values: list["ExtractedValue"],
        source_files: list[str] | None = None,
        mappings: dict[str, "CellMapping"] | None = None,
    ) -> AccuracyReport:
        """
        Generate comprehensive accuracy report for an extraction run.

        Args:
            run_id: UUID of the extraction run
            extracted_values: All extracted values from the run
            source_files: Optional list of source file paths for validation
            mappings: Optional cell mappings for completeness check

        Returns:
            AccuracyReport with comprehensive statistics
        """
        report = AccuracyReport(run_id=run_id)
        report.total_values = len(extracted_values)

        # Count accurate vs inaccurate (based on is_error flag)
        for ev in extracted_values:
            if ev.is_error:
                report.error_values += 1
            else:
                report.accurate_values += 1

        # Validate against source files if provided
        if source_files:
            # Group extracted values by source file
            by_source: dict[str, list[ExtractedValue]] = {}
            for ev in extracted_values:
                source = ev.source_file or "unknown"
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(ev)

            for source_file in source_files:
                if source_file in by_source:
                    validation_report = self.compare_with_source(
                        by_source[source_file],
                        source_file,
                        mappings,
                    )
                    report.validation_reports.append(validation_report)
                    report.files_validated += 1

        # Validate completeness if mappings provided
        if mappings:
            report.completeness_report = self.validate_completeness(
                extracted_values, mappings
            )

        # Calculate overall accuracy
        if report.total_values > 0:
            report.overall_accuracy = round(
                report.accurate_values / report.total_values * 100, 2
            )

        self.logger.info(
            "accuracy_report_generated",
            run_id=str(run_id),
            overall_accuracy=report.overall_accuracy,
            total_values=report.total_values,
            files_validated=report.files_validated,
        )

        return report

    def _compare_values(
        self,
        field_name: str,
        expected: Any,
        actual: Any,
    ) -> ValueComparison:
        """
        Compare two values with appropriate tolerance.

        Args:
            field_name: Name of the field being compared
            expected: Expected value from source
            actual: Actual extracted value

        Returns:
            ValueComparison with match result and details
        """
        # Handle None/NaN cases
        expected_is_empty = self._is_empty(expected)
        actual_is_empty = self._is_empty(actual)

        if expected_is_empty and actual_is_empty:
            return ValueComparison(
                field_name=field_name,
                expected_value=expected,
                actual_value=actual,
                matches=True,
                value_type="empty",
            )

        if expected_is_empty != actual_is_empty:
            return ValueComparison(
                field_name=field_name,
                expected_value=expected,
                actual_value=actual,
                matches=False,
                value_type="mismatch",
                error_message="One value is empty, the other is not",
            )

        # Compare numeric values
        if isinstance(expected, (int, float, Decimal)) and isinstance(
            actual, (int, float, Decimal)
        ):
            return self._compare_numeric(field_name, float(expected), float(actual))

        # Compare date values
        if isinstance(expected, datetime) and isinstance(actual, datetime):
            return self._compare_dates(field_name, expected, actual)

        # Compare text values
        if isinstance(expected, str) or isinstance(actual, str):
            return self._compare_text(field_name, str(expected), str(actual))

        # Fallback to exact comparison
        matches = expected == actual
        return ValueComparison(
            field_name=field_name,
            expected_value=expected,
            actual_value=actual,
            matches=matches,
            value_type=type(expected).__name__,
        )

    def _compare_numeric(
        self,
        field_name: str,
        expected: float,
        actual: float,
    ) -> ValueComparison:
        """Compare numeric values with relative tolerance."""
        # Handle zero case
        if expected == 0:
            difference = abs(actual)
            matches = difference < 1e-10
        else:
            difference = abs(actual - expected)
            tolerance = abs(expected) * self.NUMERIC_TOLERANCE
            matches = difference <= tolerance

        return ValueComparison(
            field_name=field_name,
            expected_value=expected,
            actual_value=actual,
            matches=matches,
            value_type="numeric",
            tolerance_used=self.NUMERIC_TOLERANCE,
            difference=difference,
        )

    def _compare_dates(
        self,
        field_name: str,
        expected: datetime,
        actual: datetime,
    ) -> ValueComparison:
        """Compare date values (exact match)."""
        # Normalize to date only for comparison
        expected_date = expected.date() if hasattr(expected, "date") else expected
        actual_date = actual.date() if hasattr(actual, "date") else actual

        matches = expected_date == actual_date

        return ValueComparison(
            field_name=field_name,
            expected_value=expected,
            actual_value=actual,
            matches=matches,
            value_type="date",
        )

    def _compare_text(
        self,
        field_name: str,
        expected: str,
        actual: str,
    ) -> ValueComparison:
        """Compare text values (whitespace-normalized)."""
        expected_normalized = expected.strip()
        actual_normalized = actual.strip()

        matches = expected_normalized == actual_normalized

        return ValueComparison(
            field_name=field_name,
            expected_value=expected,
            actual_value=actual,
            matches=matches,
            value_type="text",
        )

    def _is_empty(self, value: Any) -> bool:
        """Check if value is empty/null/NaN."""
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return isinstance(value, float) and np.isnan(value)

    def _load_source_values(
        self,
        source_path: str,
        mappings: dict[str, "CellMapping"] | None = None,
    ) -> dict[str, Any]:
        """
        Load values from source Excel file for comparison.

        Args:
            source_path: Path to Excel file
            mappings: Cell mappings to determine which cells to read

        Returns:
            Dictionary of field_name -> value from source
        """
        source_values: dict[str, Any] = {}

        if not Path(source_path).exists():
            self.logger.warning("source_file_not_found", path=source_path)
            return source_values

        if mappings is None:
            return source_values

        # Load workbook
        file_ext = Path(source_path).suffix.lower()

        try:
            if file_ext == ".xlsb":
                source_values = self._load_xlsb_values(source_path, mappings)
            else:
                source_values = self._load_xlsx_values(source_path, mappings)
        except Exception as e:
            self.logger.error(
                "source_load_failed",
                path=source_path,
                error=str(e),
            )

        return source_values

    def _load_xlsb_values(
        self,
        source_path: str,
        mappings: dict[str, "CellMapping"],
    ) -> dict[str, Any]:
        """Load values from .xlsb file."""
        import re

        import pyxlsb

        values: dict[str, Any] = {}

        with pyxlsb.open_workbook(source_path) as wb:
            for field_name, mapping in mappings.items():
                if mapping.sheet_name not in wb.sheets:
                    continue

                # Parse cell address
                match = re.match(r"^([A-Z]+)(\d+)$", mapping.cell_address)
                if not match:
                    continue

                col_str, row_str = match.groups()
                target_row = int(row_str) - 1
                target_col = self._column_to_index(col_str)

                with wb.get_sheet(mapping.sheet_name) as sheet:
                    for row in sheet.rows():
                        for cell in row:
                            if cell.r == target_row and cell.c == target_col:
                                values[field_name] = cell.v
                                break

        return values

    def _load_xlsx_values(
        self,
        source_path: str,
        mappings: dict[str, "CellMapping"],
    ) -> dict[str, Any]:
        """Load values from .xlsx file."""
        import openpyxl

        values: dict[str, Any] = {}

        wb = openpyxl.load_workbook(source_path, data_only=True)

        for field_name, mapping in mappings.items():
            if mapping.sheet_name not in wb.sheetnames:
                continue

            sheet = wb[mapping.sheet_name]
            cell = sheet[mapping.cell_address]
            values[field_name] = cell.value

        wb.close()
        return values

    def _column_to_index(self, col_str: str) -> int:
        """Convert column letters to 0-based index."""
        result = 0
        for char in col_str.upper():
            result = result * 26 + (ord(char) - ord("A") + 1)
        return result - 1


# Singleton instance for convenience
_validator_instance: ExtractionValidator | None = None


def get_validator() -> ExtractionValidator:
    """Get or create ExtractionValidator singleton."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ExtractionValidator()
    return _validator_instance
