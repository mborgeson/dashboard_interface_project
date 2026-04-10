"""
Tests for template variant detection and cell address remapping.

Run from backend directory:
    python -m pytest tests/test_extraction/test_variant_detector.py -v
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.extraction.cell_mapping import CellMapping
from app.extraction.variant_detector import (
    VariantDetectionResult,
    VariantRemap,
    _ASSUMPTIONS_SHEET,
    _VARIANT_FIELDS,
    _load_known_candidate_rows,
    apply_variant_remaps,
    detect_variant,
    reset_candidate_rows_cache,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset the module-level candidate rows cache between tests."""
    reset_candidate_rows_cache()
    yield
    reset_candidate_rows_cache()


@pytest.fixture
def sample_mappings() -> dict[str, CellMapping]:
    """Base mappings matching the production template."""
    return {
        "VACANCY_LOSS_YEAR_1_RATE": CellMapping(
            category="Operating",
            description="Vacancy Loss Year 1 Rate",
            sheet_name=_ASSUMPTIONS_SHEET,
            cell_address="D216",
            field_name="VACANCY_LOSS_YEAR_1_RATE",
        ),
        "PURCHASE_PRICE": CellMapping(
            category="Acquisition",
            description="Purchase Price",
            sheet_name=_ASSUMPTIONS_SHEET,
            cell_address="D478",
            field_name="PURCHASE_PRICE",
        ),
        "LOAN_AMOUNT": CellMapping(
            category="Debt",
            description="Loan Amount",
            sheet_name=_ASSUMPTIONS_SHEET,
            cell_address="D359",
            field_name="LOAN_AMOUNT",
        ),
        "PROPERTY_NAME": CellMapping(
            category="General",
            description="Property Name",
            sheet_name="Summary",
            cell_address="C3",
            field_name="PROPERTY_NAME",
        ),
    }


@pytest.fixture
def remaps_dir(tmp_path) -> Path:
    """Create a temp dir with a minimal field_remaps.json."""
    remaps = {
        "group_40": {
            "file": "(auto-remapped for oc_majority)",
            "remaps": {
                "VACANCY_LOSS_YEAR_1_RATE": {
                    "prod_cell": "D216",
                    "group_cell": "D45",
                    "offset": -171,
                    "type": "section_shift",
                    "reason": "Vacancy at row 45",
                },
                "PURCHASE_PRICE": {
                    "prod_cell": "D478",
                    "group_cell": "D387",
                    "offset": -91,
                    "type": "section_shift",
                    "reason": "PP at row 387",
                },
                "LOAN_AMOUNT": {
                    "prod_cell": "D359",
                    "group_cell": "D268",
                    "offset": -91,
                    "type": "section_shift",
                    "reason": "LA at row 268",
                },
            },
        },
        "group_16": {
            "file": "(auto-remapped for refi_senior)",
            "remaps": {
                "VACANCY_LOSS_YEAR_1_RATE": {
                    "prod_cell": "D216",
                    "group_cell": "D45",
                    "offset": -171,
                    "type": "section_shift",
                    "reason": "Vacancy at row 45",
                },
                "PURCHASE_PRICE": {
                    "prod_cell": "D478",
                    "group_cell": "D272",
                    "offset": -206,
                    "type": "section_shift",
                    "reason": "PP at row 272",
                },
                "LOAN_AMOUNT": {
                    "prod_cell": "D359",
                    "group_cell": "D207",
                    "offset": -152,
                    "type": "section_shift",
                    "reason": "LA at row 207",
                },
            },
        },
    }
    (tmp_path / "field_remaps.json").write_text(json.dumps(remaps))
    return tmp_path


# ---------------------------------------------------------------------------
# Tests: _load_known_candidate_rows
# ---------------------------------------------------------------------------


class TestLoadKnownCandidateRows:
    def test_loads_from_remaps_json(self, remaps_dir):
        rows = _load_known_candidate_rows(remaps_dir)

        # Vacancy should have production (216) + variant (45)
        assert 216 in rows["VACANCY_LOSS_YEAR_1_RATE"]
        assert 45 in rows["VACANCY_LOSS_YEAR_1_RATE"]

        # Purchase Price should include all group_cell rows
        assert 478 in rows["PURCHASE_PRICE"]
        assert 387 in rows["PURCHASE_PRICE"]
        assert 272 in rows["PURCHASE_PRICE"]

        # Loan Amount
        assert 359 in rows["LOAN_AMOUNT"]
        assert 268 in rows["LOAN_AMOUNT"]
        assert 207 in rows["LOAN_AMOUNT"]

    def test_returns_defaults_when_no_file(self, tmp_path):
        rows = _load_known_candidate_rows(tmp_path)

        # Should still include production + hardcoded vacancy row
        assert 216 in rows["VACANCY_LOSS_YEAR_1_RATE"]
        assert 45 in rows["VACANCY_LOSS_YEAR_1_RATE"]
        assert 478 in rows["PURCHASE_PRICE"]
        assert 359 in rows["LOAN_AMOUNT"]

    def test_handles_malformed_json(self, tmp_path):
        (tmp_path / "field_remaps.json").write_text("not valid json")
        rows = _load_known_candidate_rows(tmp_path)
        # Should still return defaults
        assert "VACANCY_LOSS_YEAR_1_RATE" in rows

    def test_rows_are_sorted(self, remaps_dir):
        rows = _load_known_candidate_rows(remaps_dir)
        for field, row_list in rows.items():
            assert row_list == sorted(row_list), f"{field} rows not sorted"


# ---------------------------------------------------------------------------
# Tests: detect_variant (with mocked workbook I/O)
# ---------------------------------------------------------------------------


def _make_mock_xlsx_workbook(cell_values: dict[tuple[str, str, int], str | None]):
    """
    Create a fake openpyxl workbook backed by a cell_values dict.

    cell_values: dict of (sheet_name, col_letter, row) -> cell_value

    Uses real classes (not MagicMock) for __getitem__ to avoid
    MagicMock's dunder-method self-parameter issues.
    """
    import re as _re

    sheets_in_wb = set()
    for sn, _, _ in cell_values:
        sheets_in_wb.add(sn)

    class FakeCell:
        __slots__ = ("value",)

        def __init__(self, value):
            self.value = value

    class FakeSheet:
        def __init__(self, sheet_name: str):
            self._sheet_name = sheet_name

        def __getitem__(self, addr: str) -> FakeCell:
            m = _re.match(r"([A-Z]+)(\d+)", addr)
            if m:
                col, row = m.group(1), int(m.group(2))
                val = cell_values.get((self._sheet_name, col, row))
                return FakeCell(val)
            return FakeCell(None)

    sheet_objs = {sn: FakeSheet(sn) for sn in sheets_in_wb}

    class FakeWorkbook:
        sheetnames = list(sheets_in_wb)

        def __getitem__(self, key):
            return sheet_objs.get(key)

        def close(self):
            pass

    return FakeWorkbook()


_OPENPYXL_PATCH = "app.extraction.variant_detector.openpyxl"


class TestDetectVariant:
    """Tests for detect_variant with mocked workbook loading."""

    def test_production_template_no_remaps(self, remaps_dir):
        """File with labels at production rows should NOT be detected as variant."""
        cell_values = {
            (_ASSUMPTIONS_SHEET, "A", 216): "Vacancy Loss",
            (_ASSUMPTIONS_SHEET, "A", 478): "Purchase Price",
            (_ASSUMPTIONS_SHEET, "A", 359): "Loan Amount",
        }
        wb = _make_mock_xlsx_workbook(cell_values)

        with patch(_OPENPYXL_PATCH) as mock_openpyxl:
            mock_openpyxl.load_workbook.return_value = wb
            result = detect_variant("test.xlsx", data_dir=remaps_dir)

        assert not result.is_variant
        assert result.remaps == []

    def test_oc_majority_variant_detected(self, remaps_dir):
        """File with labels at oc_majority rows should be detected and remapped."""
        cell_values = {
            (_ASSUMPTIONS_SHEET, "A", 216): None,  # no label at prod row
            (_ASSUMPTIONS_SHEET, "A", 45): "Vacancy Loss",
            (_ASSUMPTIONS_SHEET, "A", 478): None,
            (_ASSUMPTIONS_SHEET, "A", 387): "Purchase Price",
            (_ASSUMPTIONS_SHEET, "A", 359): None,
            (_ASSUMPTIONS_SHEET, "A", 268): "Loan Amount",
        }
        wb = _make_mock_xlsx_workbook(cell_values)

        with patch(_OPENPYXL_PATCH) as mock_openpyxl:
            mock_openpyxl.load_workbook.return_value = wb
            result = detect_variant("test.xlsx", data_dir=remaps_dir)

        assert result.is_variant
        assert len(result.remaps) == 3

        remap_map = {r.field_name: r for r in result.remaps}
        assert remap_map["VACANCY_LOSS_YEAR_1_RATE"].variant_cell == "D45"
        assert remap_map["PURCHASE_PRICE"].variant_cell == "D387"
        assert remap_map["LOAN_AMOUNT"].variant_cell == "D268"

    def test_refi_senior_variant_detected(self, remaps_dir):
        """File with refi_senior row positions should be detected."""
        cell_values = {
            (_ASSUMPTIONS_SHEET, "A", 216): None,
            (_ASSUMPTIONS_SHEET, "A", 45): "Vacancy Loss",
            (_ASSUMPTIONS_SHEET, "A", 478): None,
            (_ASSUMPTIONS_SHEET, "A", 272): "Purchase Price",
            (_ASSUMPTIONS_SHEET, "A", 359): None,
            (_ASSUMPTIONS_SHEET, "A", 207): "Loan Amount",
        }
        wb = _make_mock_xlsx_workbook(cell_values)

        with patch(_OPENPYXL_PATCH) as mock_openpyxl:
            mock_openpyxl.load_workbook.return_value = wb
            result = detect_variant("test.xlsx", data_dir=remaps_dir)

        assert result.is_variant
        remap_map = {r.field_name: r for r in result.remaps}
        assert remap_map["PURCHASE_PRICE"].variant_cell == "D272"
        assert remap_map["LOAN_AMOUNT"].variant_cell == "D207"

    def test_partial_variant_only_vacancy(self, remaps_dir):
        """File where only vacancy is shifted but PP/LA at production rows."""
        cell_values = {
            (_ASSUMPTIONS_SHEET, "A", 216): None,
            (_ASSUMPTIONS_SHEET, "A", 45): "Vacancy Loss",
            (_ASSUMPTIONS_SHEET, "A", 478): "Purchase Price",
            (_ASSUMPTIONS_SHEET, "A", 359): "Loan Amount",
        }
        wb = _make_mock_xlsx_workbook(cell_values)

        with patch(_OPENPYXL_PATCH) as mock_openpyxl:
            mock_openpyxl.load_workbook.return_value = wb
            result = detect_variant("test.xlsx", data_dir=remaps_dir)

        assert result.is_variant
        assert len(result.remaps) == 1
        assert result.remaps[0].field_name == "VACANCY_LOSS_YEAR_1_RATE"

    def test_missing_assumptions_sheet_returns_no_variant(self, remaps_dir):
        """File without 'Assumptions (Summary)' sheet should not be variant."""
        wb = MagicMock()
        wb.sheetnames = ["Summary", "Cash Flow"]
        wb.close = MagicMock()

        with patch(_OPENPYXL_PATCH) as mock_openpyxl:
            mock_openpyxl.load_workbook.return_value = wb
            result = detect_variant("test.xlsx", data_dir=remaps_dir)

        assert not result.is_variant

    def test_workbook_load_failure_returns_no_variant(self, remaps_dir):
        """If workbook fails to open, return non-variant gracefully."""
        with patch(_OPENPYXL_PATCH) as mock_openpyxl:
            mock_openpyxl.load_workbook.side_effect = Exception("corrupt file")
            result = detect_variant("test.xlsx", data_dir=remaps_dir)

        assert not result.is_variant
        assert result.remaps == []

    def test_case_insensitive_label_matching(self, remaps_dir):
        """Labels should be matched case-insensitively."""
        cell_values = {
            (_ASSUMPTIONS_SHEET, "A", 216): None,
            (_ASSUMPTIONS_SHEET, "A", 45): "VACANCY LOSS",
            (_ASSUMPTIONS_SHEET, "A", 478): None,
            (_ASSUMPTIONS_SHEET, "A", 387): "purchase price (net)",
            (_ASSUMPTIONS_SHEET, "A", 359): None,
            (_ASSUMPTIONS_SHEET, "A", 268): "Total Loan Amount",
        }
        wb = _make_mock_xlsx_workbook(cell_values)

        with patch(_OPENPYXL_PATCH) as mock_openpyxl:
            mock_openpyxl.load_workbook.return_value = wb
            result = detect_variant("test.xlsx", data_dir=remaps_dir)

        assert result.is_variant
        assert len(result.remaps) == 3


# ---------------------------------------------------------------------------
# Tests: apply_variant_remaps
# ---------------------------------------------------------------------------


class TestApplyVariantRemaps:
    def test_applies_remaps_to_mappings(self, sample_mappings):
        detection = VariantDetectionResult(
            is_variant=True,
            remaps=[
                VariantRemap(
                    field_name="VACANCY_LOSS_YEAR_1_RATE",
                    prod_cell="D216",
                    variant_cell="D45",
                    detected_row=45,
                    label_found="Vacancy Loss",
                ),
                VariantRemap(
                    field_name="PURCHASE_PRICE",
                    prod_cell="D478",
                    variant_cell="D387",
                    detected_row=387,
                    label_found="Purchase Price",
                ),
            ],
        )
        modified, applied = apply_variant_remaps(sample_mappings, detection)

        # Modified mappings should have new addresses
        assert modified["VACANCY_LOSS_YEAR_1_RATE"].cell_address == "D45"
        assert modified["PURCHASE_PRICE"].cell_address == "D387"
        # Unremapped field should keep original address
        assert modified["LOAN_AMOUNT"].cell_address == "D359"
        assert modified["PROPERTY_NAME"].cell_address == "C3"

        assert len(applied) == 2

    def test_does_not_mutate_original(self, sample_mappings):
        detection = VariantDetectionResult(
            is_variant=True,
            remaps=[
                VariantRemap(
                    field_name="VACANCY_LOSS_YEAR_1_RATE",
                    prod_cell="D216",
                    variant_cell="D45",
                    detected_row=45,
                    label_found="Vacancy Loss",
                ),
            ],
        )
        original_addr = sample_mappings["VACANCY_LOSS_YEAR_1_RATE"].cell_address
        apply_variant_remaps(sample_mappings, detection)

        # Original should be untouched
        assert sample_mappings["VACANCY_LOSS_YEAR_1_RATE"].cell_address == original_addr

    def test_non_variant_returns_original(self, sample_mappings):
        detection = VariantDetectionResult(is_variant=False, remaps=[])
        modified, applied = apply_variant_remaps(sample_mappings, detection)

        # Should return the same dict (not a copy)
        assert modified is sample_mappings
        assert applied == []

    def test_remap_for_missing_field_is_skipped(self, sample_mappings):
        detection = VariantDetectionResult(
            is_variant=True,
            remaps=[
                VariantRemap(
                    field_name="NONEXISTENT_FIELD",
                    prod_cell="X99",
                    variant_cell="X100",
                    detected_row=100,
                    label_found="Nonexistent",
                ),
            ],
        )
        modified, applied = apply_variant_remaps(sample_mappings, detection)
        assert len(applied) == 0


# ---------------------------------------------------------------------------
# Tests: VariantDetectionResult serialization
# ---------------------------------------------------------------------------


class TestVariantDetectionResult:
    def test_to_dict(self):
        result = VariantDetectionResult(
            is_variant=True,
            remaps=[
                VariantRemap(
                    field_name="VACANCY_LOSS_YEAR_1_RATE",
                    prod_cell="D216",
                    variant_cell="D45",
                    detected_row=45,
                    label_found="Vacancy Loss",
                ),
            ],
        )
        d = result.to_dict()
        assert d["is_variant"] is True
        assert d["remap_count"] == 1
        assert d["remaps"][0]["field"] == "VACANCY_LOSS_YEAR_1_RATE"

    def test_to_dict_no_remaps(self):
        result = VariantDetectionResult(is_variant=False, remaps=[])
        d = result.to_dict()
        assert d["is_variant"] is False
        assert d["remap_count"] == 0
        assert d["remaps"] == []


# ---------------------------------------------------------------------------
# Tests: integration with _extract_single_file
# ---------------------------------------------------------------------------


class TestExtractSingleFileIntegration:
    """Verify that _extract_single_file passes base_mappings for variant detection."""

    # The imports inside _extract_single_file use
    #   from app.extraction.variant_detector import detect_variant, apply_variant_remaps
    # so we patch at the source module.
    _DETECT_PATCH = "app.extraction.variant_detector.detect_variant"
    _APPLY_PATCH = "app.extraction.variant_detector.apply_variant_remaps"

    def test_variant_detection_called_when_base_mappings_provided(
        self, sample_mappings
    ):
        """When base_mappings is provided, detect_variant should be called."""
        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.return_value = {"PROPERTY_NAME": "Test"}

        with patch(self._DETECT_PATCH) as mock_detect:
            # Non-variant detection
            mock_detect.return_value = VariantDetectionResult(
                is_variant=False, remaps=[]
            )

            from app.api.v1.endpoints.extraction.common import _extract_single_file

            result = _extract_single_file(
                mock_extractor,
                "test.xlsx",
                "Test Deal",
                base_mappings=sample_mappings,
            )

            # detect_variant was called
            mock_detect.assert_called_once_with("test.xlsx")
            # Original extractor was used (non-variant)
            mock_extractor.extract_from_file.assert_called_once()

    def test_variant_creates_new_extractor(self, sample_mappings):
        """When variant is detected, a new extractor with remapped mappings is created."""
        mock_extractor = MagicMock()

        variant_result = VariantDetectionResult(
            is_variant=True,
            remaps=[
                VariantRemap(
                    field_name="VACANCY_LOSS_YEAR_1_RATE",
                    prod_cell="D216",
                    variant_cell="D45",
                    detected_row=45,
                    label_found="Vacancy Loss",
                ),
            ],
        )

        with (
            patch(self._DETECT_PATCH) as mock_detect,
            patch(self._APPLY_PATCH) as mock_apply,
            patch("app.extraction.extractor.ExcelDataExtractor") as mock_extractor_cls,
        ):
            mock_detect.return_value = variant_result
            mock_apply.return_value = (sample_mappings, [{"field_name": "test"}])
            mock_new_extractor = MagicMock()
            mock_new_extractor.extract_from_file.return_value = {"PROPERTY_NAME": "V"}
            mock_extractor_cls.return_value = mock_new_extractor

            from app.api.v1.endpoints.extraction.common import _extract_single_file

            fp, dn, data, err = _extract_single_file(
                mock_extractor,
                "variant.xlsx",
                "Variant Deal",
                base_mappings=sample_mappings,
            )

            assert err is None
            # detect_variant was called
            mock_detect.assert_called_once()
            # apply_variant_remaps was called
            mock_apply.assert_called_once()

    def test_no_base_mappings_skips_detection(self):
        """When base_mappings is None, variant detection is skipped."""
        mock_extractor = MagicMock()
        mock_extractor.extract_from_file.return_value = {"data": "ok"}

        from app.api.v1.endpoints.extraction.common import _extract_single_file

        with patch(self._DETECT_PATCH) as mock_detect:
            _extract_single_file(
                mock_extractor, "test.xlsx", "Deal", base_mappings=None
            )
            mock_detect.assert_not_called()
