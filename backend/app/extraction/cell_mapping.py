"""
B&R Capital Dashboard - Cell Mapping Module

Parses the Excel reference file containing ~1,179 cell mappings that define
which cells to extract from underwriting models.

Improvements over prior implementation:
- FIXED: Duplicate field names now get unique suffixes (sheet_rowindex)
- Added validation for required columns
- Better error handling for malformed reference files
"""

import pandas as pd
import structlog
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Set
from collections import Counter


@dataclass
class CellMapping:
    """Represents a single cell mapping from the reference file"""

    category: str
    description: str
    sheet_name: str
    cell_address: str
    field_name: str  # Cleaned, unique field name for database


class CellMappingParser:
    """
    Parses the Excel reference file containing ~1,179 cell mappings.

    The reference file is expected to have a sheet named
    "UW Model - Cell Reference Table" with columns:
    - B: Category
    - C: Description (field description)
    - D: Sheet Name (target sheet in UW model)
    - G: Cell Address (e.g., "D6", "$G$10")
    """

    # Expected sheet name in reference file
    REFERENCE_SHEET_NAME = "UW Model - Cell Reference Table"

    def __init__(self, reference_file_path: str):
        self.reference_file_path = Path(reference_file_path)
        self.mappings: Dict[str, CellMapping] = {}
        self.logger = structlog.get_logger().bind(component="CellMappingParser")
        self._duplicate_tracker: Set[str] = set()

    def load_mappings(self) -> Dict[str, CellMapping]:
        """
        Load and parse cell mappings from reference Excel file.

        Returns:
            Dictionary mapping unique field names to CellMapping objects

        Raises:
            FileNotFoundError: If reference file doesn't exist
            ValueError: If required sheet or columns are missing
        """
        if not self.reference_file_path.exists():
            raise FileNotFoundError(
                f"Reference file not found: {self.reference_file_path}"
            )

        self.logger.info(
            "loading_cell_mappings", file_path=str(self.reference_file_path)
        )

        try:
            # Read the reference file
            df = pd.read_excel(
                self.reference_file_path, sheet_name=self.REFERENCE_SHEET_NAME
            )
        except ValueError as e:
            raise ValueError(
                f"Sheet '{self.REFERENCE_SHEET_NAME}' not found in reference file. "
                f"Available sheets should include the cell reference table."
            ) from e

        self.logger.debug(
            "reference_file_loaded", columns=list(df.columns), rows=len(df)
        )

        # Map columns by position (0-indexed)
        # B=1 (Category), C=2 (Description), D=3 (Sheet), G=6 (Cell)
        col_names = list(df.columns)

        if len(col_names) < 7:
            raise ValueError(
                f"Reference file has only {len(col_names)} columns, expected at least 7"
            )

        category_col = col_names[1]  # Column B
        description_col = col_names[2]  # Column C
        sheet_col = col_names[3]  # Column D
        cell_col = col_names[6]  # Column G

        # Track field names to ensure uniqueness
        field_name_counts: Counter = Counter()

        # First pass: count field name occurrences
        for idx, row in df.iterrows():
            if pd.notna(row[description_col]) and pd.notna(row[cell_col]):
                base_name = self._clean_field_name(str(row[description_col]))
                field_name_counts[base_name] += 1

        # Second pass: create mappings with unique names
        seen_counts: Counter = Counter()
        mapping_count = 0

        for idx, row in df.iterrows():
            if pd.notna(row[description_col]) and pd.notna(row[cell_col]):
                base_name = self._clean_field_name(str(row[description_col]))
                sheet_name = (
                    str(row[sheet_col]) if pd.notna(row[sheet_col]) else "Unknown"
                )

                # Make field name unique if there are duplicates
                if field_name_counts[base_name] > 1:
                    seen_counts[base_name] += 1
                    # Append sheet abbreviation and occurrence number
                    sheet_abbrev = self._abbreviate_sheet_name(sheet_name)
                    field_name = f"{base_name}_{sheet_abbrev}_{seen_counts[base_name]}"
                    self._duplicate_tracker.add(base_name)
                else:
                    field_name = base_name

                mapping = CellMapping(
                    category=(
                        str(row[category_col])
                        if pd.notna(row[category_col])
                        else "Uncategorized"
                    ),
                    description=str(row[description_col]),
                    sheet_name=sheet_name,
                    cell_address=str(row[cell_col]).strip().upper().replace("$", ""),
                    field_name=field_name,
                )

                self.mappings[field_name] = mapping
                mapping_count += 1

        # Log duplicate handling
        if self._duplicate_tracker:
            self.logger.info(
                "duplicate_fields_renamed",
                duplicate_count=len(self._duplicate_tracker),
                examples=list(self._duplicate_tracker)[:5],
            )

        self.logger.info(
            "mappings_loaded",
            count=mapping_count,
            unique_categories=len(set(m.category for m in self.mappings.values())),
            duplicates_handled=len(self._duplicate_tracker),
        )

        return self.mappings

    def _clean_field_name(self, description: str) -> str:
        """
        Convert description to clean field name.

        Transformations:
        - Strip whitespace
        - Replace spaces and special chars with underscores
        - Convert to UPPERCASE
        - Remove consecutive underscores
        """
        clean_name = description.strip()

        # Replace special characters
        replacements = {
            " ": "_",
            "-": "_",
            "(": "",
            ")": "",
            "/": "_",
            ".": "",
            ",": "",
            "'": "",
            '"': "",
            "#": "NUM",
            "%": "PCT",
            "$": "",
            "&": "AND",
        }

        for old, new in replacements.items():
            clean_name = clean_name.replace(old, new)

        clean_name = clean_name.upper()

        # Remove consecutive underscores
        while "__" in clean_name:
            clean_name = clean_name.replace("__", "_")

        # Remove leading/trailing underscores
        clean_name = clean_name.strip("_")

        return clean_name

    def _abbreviate_sheet_name(self, sheet_name: str) -> str:
        """Create short abbreviation from sheet name for unique field suffix"""
        # Take first letter of each word, max 4 chars
        words = sheet_name.replace("-", " ").replace("_", " ").split()
        abbrev = "".join(w[0].upper() for w in words if w)[:4]
        return abbrev or "UNK"

    def get_mappings_by_category(self) -> Dict[str, list]:
        """Group mappings by category"""
        by_category: Dict[str, list] = {}
        for mapping in self.mappings.values():
            if mapping.category not in by_category:
                by_category[mapping.category] = []
            by_category[mapping.category].append(mapping)
        return by_category

    def get_mappings_by_sheet(self) -> Dict[str, list]:
        """Group mappings by target sheet name"""
        by_sheet: Dict[str, list] = {}
        for mapping in self.mappings.values():
            if mapping.sheet_name not in by_sheet:
                by_sheet[mapping.sheet_name] = []
            by_sheet[mapping.sheet_name].append(mapping)
        return by_sheet

    def export_mapping_summary(self, output_path: str) -> None:
        """Export mapping summary to CSV for documentation"""
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        summary_data = [
            {
                "Field Name": mapping.field_name,
                "Category": mapping.category,
                "Description": mapping.description,
                "Sheet": mapping.sheet_name,
                "Cell": mapping.cell_address,
            }
            for mapping in self.mappings.values()
        ]

        df = pd.DataFrame(summary_data)
        df.to_csv(output_path, index=False)
        self.logger.info("mapping_summary_exported", path=output_path)

    def validate_mappings(self) -> Dict[str, any]:
        """
        Validate loaded mappings and return quality report.

        Returns:
            Dict with validation results and any issues found
        """
        issues = []

        # Check for empty mappings
        if not self.mappings:
            issues.append("No mappings loaded")
            return {"valid": False, "issues": issues}

        # Check for missing sheet names
        missing_sheets = [
            m.field_name
            for m in self.mappings.values()
            if not m.sheet_name or m.sheet_name == "nan"
        ]
        if missing_sheets:
            issues.append(f"{len(missing_sheets)} mappings have missing sheet names")

        # Check for invalid cell addresses
        import re

        cell_pattern = re.compile(r"^[A-Z]+\d+$")
        invalid_cells = [
            m.field_name
            for m in self.mappings.values()
            if not cell_pattern.match(m.cell_address)
        ]
        if invalid_cells:
            issues.append(f"{len(invalid_cells)} mappings have invalid cell addresses")

        return {
            "valid": len(issues) == 0,
            "total_mappings": len(self.mappings),
            "unique_sheets": len(set(m.sheet_name for m in self.mappings.values())),
            "unique_categories": len(set(m.category for m in self.mappings.values())),
            "duplicates_resolved": len(self._duplicate_tracker),
            "issues": issues,
        }
