"""
Tests for CandidateFileFilter — Old UW Model file criteria.

Criteria:
  Include (ALL must match):
    1a. Contains "vCurrent.xlsb" (case-insensitive)
    1b. Contains "Model", "UW", or "Proforma" (case-insensitive)
    3.  Modified before 2024-07-15
    4.  Extension .xlsb only

  Exclude (ANY triggers rejection):
    "[Deal Name]", "Settlement Statement", "Due Diligence Tracker",
    "AutoRecovered", "Speedboat", "Tax", "Cashflows", "Development",
    "Portfolio", "Template", "~$"

Run with: pytest tests/test_extraction/test_candidate_filter.py -v
"""

from datetime import datetime

import pytest

from app.extraction.file_filter import (
    CandidateFileFilter,
    FilterResult,
    SkipReason,
)


@pytest.fixture
def cf():
    """CandidateFileFilter instance."""
    return CandidateFileFilter()


class TestAcceptance:
    """Files that should be accepted."""

    def test_proforma_vcurrent_old_date(self, cf):
        """Proforma vCurrent.xlsb modified before cutoff → accepted."""
        result = cf.should_process(
            "Deal Proforma vCurrent.xlsb",
            modified_date=datetime(2022, 6, 1),
        )
        assert result.should_process is True

    def test_uw_model_vcurrent_old_date(self, cf):
        """UW Model vCurrent.xlsb modified before cutoff → accepted."""
        result = cf.should_process(
            "Deal UW Model vCurrent.xlsb",
            modified_date=datetime(2023, 1, 15),
        )
        assert result.should_process is True

    def test_model_keyword_only(self, cf):
        """File with 'Model' keyword + vCurrent.xlsb → accepted."""
        result = cf.should_process(
            "Deal Model vCurrent.xlsb",
            modified_date=datetime(2022, 3, 1),
        )
        assert result.should_process is True

    def test_uw_keyword_only(self, cf):
        """File with 'UW' keyword + vCurrent.xlsb → accepted."""
        result = cf.should_process(
            "Deal UW vCurrent.xlsb",
            modified_date=datetime(2022, 3, 1),
        )
        assert result.should_process is True

    def test_case_insensitive_match(self, cf):
        """Case-insensitive matching works."""
        result = cf.should_process(
            "deal proforma VCURRENT.XLSB",
            modified_date=datetime(2022, 1, 1),
        )
        assert result.should_process is True

    def test_no_modified_date_accepted(self, cf):
        """File with no modified_date should still be accepted (date check skipped)."""
        result = cf.should_process(
            "Deal Proforma vCurrent.xlsb",
            modified_date=None,
        )
        assert result.should_process is True

    def test_day_before_cutoff_accepted(self, cf):
        """File modified on 2024-07-14 (one day before cutoff) → accepted."""
        result = cf.should_process(
            "Deal UW Model vCurrent.xlsb",
            modified_date=datetime(2024, 7, 14),
        )
        assert result.should_process is True


class TestRejectionIncludeCriteria:
    """Files rejected because they don't meet include criteria."""

    def test_missing_vcurrent_xlsb(self, cf):
        """File without 'vCurrent.xlsb' → rejected."""
        result = cf.should_process(
            "Deal UW Model v3.xlsb",
            modified_date=datetime(2022, 1, 1),
        )
        assert result.should_process is False
        assert result.skip_reason == SkipReason.PATTERN_MISMATCH
        assert "vCurrent.xlsb" in (result.skip_details or "")

    def test_missing_keyword(self, cf):
        """File with vCurrent.xlsb but no Model/UW/Proforma → rejected."""
        result = cf.should_process(
            "Deal Summary vCurrent.xlsb",
            modified_date=datetime(2022, 1, 1),
        )
        assert result.should_process is False
        assert result.skip_reason == SkipReason.PATTERN_MISMATCH
        assert "Model" in (result.skip_details or "")

    def test_modified_after_cutoff(self, cf):
        """File modified on or after 2024-07-15 → rejected."""
        result = cf.should_process(
            "Deal UW Model vCurrent.xlsb",
            modified_date=datetime(2024, 7, 15),
        )
        assert result.should_process is False
        assert result.skip_reason == SkipReason.TOO_OLD

    def test_modified_well_after_cutoff(self, cf):
        """File modified in 2025 → rejected."""
        result = cf.should_process(
            "Deal Proforma vCurrent.xlsb",
            modified_date=datetime(2025, 6, 1),
        )
        assert result.should_process is False

    def test_xlsx_extension_rejected(self, cf):
        """Only .xlsb allowed — .xlsx rejected."""
        result = cf.should_process(
            "Deal UW Model vCurrent.xlsx",
            modified_date=datetime(2022, 1, 1),
        )
        assert result.should_process is False
        assert result.skip_reason == SkipReason.INVALID_EXTENSION

    def test_xlsm_extension_rejected(self, cf):
        """Only .xlsb allowed — .xlsm rejected."""
        result = cf.should_process(
            "Deal UW Model vCurrent.xlsm",
            modified_date=datetime(2022, 1, 1),
        )
        assert result.should_process is False
        assert result.skip_reason == SkipReason.INVALID_EXTENSION

    def test_pdf_extension_rejected(self, cf):
        """Non-Excel extension → rejected."""
        result = cf.should_process("Deal UW Model vCurrent.pdf")
        assert result.should_process is False
        assert result.skip_reason == SkipReason.INVALID_EXTENSION


class TestRejectionExcludeCriteria:
    """Files rejected because they contain excluded substrings."""

    @pytest.mark.parametrize("substring,filename", [
        ("speedboat", "Speedboat UW Model vCurrent.xlsb"),
        ("tax", "Tax UW Model vCurrent.xlsb"),
        ("cashflows", "Cashflows UW Model vCurrent.xlsb"),
        ("development", "Development UW Model vCurrent.xlsb"),
        ("portfolio", "Portfolio UW Model vCurrent.xlsb"),
        ("template", "Template UW Model vCurrent.xlsb"),
        ("autorecovered", "AutoRecovered UW Model vCurrent.xlsb"),
        ("[deal name]", "[Deal Name] UW Model vCurrent.xlsb"),
        ("settlement statement", "Settlement Statement UW Model vCurrent.xlsb"),
        ("due diligence tracker", "Due Diligence Tracker UW Model vCurrent.xlsb"),
        ("~$", "~$UW Model vCurrent.xlsb"),
        ("vold", "Deal vOld UW Model vCurrent.xlsb"),
    ])
    def test_excluded_substring(self, cf, substring, filename):
        """Each excluded substring triggers rejection."""
        result = cf.should_process(
            filename,
            modified_date=datetime(2022, 1, 1),
        )
        assert result.should_process is False
        assert result.skip_reason == SkipReason.EXCLUDED_PATTERN
        assert substring in (result.skip_details or "").lower()


class TestEdgeCases:
    """Edge cases."""

    def test_get_extension_no_dot(self, cf):
        """File without extension returns empty string."""
        assert cf._get_extension("no_extension") == ""

    def test_filter_result_reason_message(self):
        """FilterResult.reason_message property works correctly."""
        r = FilterResult(should_process=True)
        assert r.reason_message is None

        r2 = FilterResult(
            should_process=False,
            skip_reason=SkipReason.PATTERN_MISMATCH,
            skip_details="test detail",
        )
        assert "test detail" in r2.reason_message

    def test_constructor_backward_compat(self):
        """Constructor still accepts production_filter for backward compat."""
        from unittest.mock import MagicMock
        cf = CandidateFileFilter(production_filter=MagicMock())
        assert cf is not None

    def test_real_proforma_filename(self, cf):
        """Real Proforma filename from Dead Deals → accepted."""
        result = cf.should_process(
            "Dobson 2222 Proforma vCurrent.xlsb",
            modified_date=datetime(2022, 5, 3),
        )
        assert result.should_process is True

    def test_real_proforma_filename_2(self, cf):
        """Another real Proforma filename → accepted."""
        result = cf.should_process(
            "San Palmas Proforma vCurrent.xlsb",
            modified_date=datetime(2022, 4, 5),
        )
        assert result.should_process is True
