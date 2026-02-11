"""
Tests for CandidateFileFilter — inverse filter logic for UW model grouping.

Tests cover:
- Candidate pattern matching (UW Model, Proforma)
- Always-exclude patterns (Notes, Backup, Copy, Draft, Template)
- Extension validation
- Inverse logic: accepts files that FAIL production filter
- Rejects files that PASS production filter (already handled)

Run with: pytest tests/test_extraction/test_candidate_filter.py -v
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.extraction.file_filter import (
    CandidateFileFilter,
    FileFilter,
    FilterResult,
    SkipReason,
)


@pytest.fixture
def mock_settings():
    """Settings mock with standard production filter config."""
    s = MagicMock()
    s.FILE_PATTERN = r".*UW\s*Model.*vCurrent.*"
    s.EXCLUDE_PATTERNS = "~$,.tmp,backup,old,archive,Speedboat,vOld"
    s.FILE_EXTENSIONS = ".xlsb,.xlsm,.xlsx"
    s.CUTOFF_DATE = "2024-07-15"
    s.MAX_FILE_SIZE_MB = 100
    return s


@pytest.fixture
def production_filter(mock_settings):
    return FileFilter(mock_settings)


@pytest.fixture
def candidate_filter(production_filter):
    return CandidateFileFilter(production_filter)


class TestCandidateFilterAcceptance:
    """Tests for files that should be accepted as candidates."""

    def test_old_uw_model_accepted(self, candidate_filter):
        """Old UW Model file (before cutoff) should be accepted."""
        result = candidate_filter.should_process(
            "Property UW Model v3.xlsb",
            size_bytes=5_000_000,
            modified_date=datetime(2023, 1, 15),
        )
        assert result.should_process is True

    def test_non_vcurrent_uw_model_accepted(self, candidate_filter):
        """Non-vCurrent UW Model should be accepted."""
        result = candidate_filter.should_process(
            "Deal UW Model v2.xlsb",
            size_bytes=5_000_000,
            modified_date=datetime(2025, 1, 1),
        )
        assert result.should_process is True

    def test_proforma_vcurrent_old_date_accepted(self, candidate_filter):
        """Proforma vCurrent with old date should be accepted."""
        result = candidate_filter.should_process(
            "Proforma vCurrent.xlsb",
            size_bytes=5_000_000,
            modified_date=datetime(2022, 6, 1),
        )
        assert result.should_process is True

    def test_uw_model_speedboat_accepted(self, candidate_filter):
        """Speedboat UW Model is excluded by production but matches broad pattern."""
        result = candidate_filter.should_process(
            "Speedboat UW Model vCurrent.xlsb",
            size_bytes=5_000_000,
            modified_date=datetime(2025, 1, 1),
        )
        # Speedboat is in production exclude patterns,
        # but candidate's ALWAYS_EXCLUDE doesn't have "speedboat"
        # Production filter would reject it → candidate filter should accept
        assert result.should_process is True

    def test_uw_model_void_accepted(self, candidate_filter):
        """vOld UW Model file should be accepted."""
        result = candidate_filter.should_process(
            "Deal UW Model vOld.xlsb",
            size_bytes=5_000_000,
            modified_date=datetime(2025, 1, 1),
        )
        assert result.should_process is True


class TestCandidateFilterRejection:
    """Tests for files that should be rejected."""

    def test_production_vcurrent_rejected(self, candidate_filter):
        """Standard vCurrent UW Model (passes production) should be rejected."""
        result = candidate_filter.should_process(
            "Deal UW Model vCurrent.xlsb",
            size_bytes=5_000_000,
            modified_date=datetime(2025, 1, 1),
        )
        assert result.should_process is False
        assert result.skip_reason == SkipReason.PATTERN_MISMATCH
        assert "production pipeline" in (result.skip_details or "")

    def test_non_uw_file_rejected(self, candidate_filter):
        """File not matching UW pattern should be rejected."""
        result = candidate_filter.should_process(
            "Random Report.xlsb",
            size_bytes=5_000_000,
        )
        assert result.should_process is False
        assert result.skip_reason == SkipReason.PATTERN_MISMATCH

    def test_invalid_extension_rejected(self, candidate_filter):
        """Non-Excel extension should be rejected."""
        result = candidate_filter.should_process("UW Model v3.pdf")
        assert result.should_process is False
        assert result.skip_reason == SkipReason.INVALID_EXTENSION

    def test_always_exclude_notes_rejected(self, candidate_filter):
        """File with 'Notes' in name should be excluded."""
        result = candidate_filter.should_process("UW Model Notes.xlsb")
        assert result.should_process is False
        assert result.skip_reason == SkipReason.EXCLUDED_PATTERN
        assert "notes" in (result.skip_details or "")

    def test_always_exclude_backup_rejected(self, candidate_filter):
        """File with 'Backup' in name should be excluded."""
        result = candidate_filter.should_process("Backup UW Model.xlsb")
        assert result.should_process is False
        assert result.skip_reason == SkipReason.EXCLUDED_PATTERN

    def test_always_exclude_copy_rejected(self, candidate_filter):
        """File with 'Copy' in name should be excluded."""
        result = candidate_filter.should_process("UW Model Copy.xlsb")
        assert result.should_process is False
        assert result.skip_reason == SkipReason.EXCLUDED_PATTERN

    def test_always_exclude_draft_rejected(self, candidate_filter):
        """File with 'Draft' in name should be excluded."""
        result = candidate_filter.should_process("Draft UW Model.xlsb")
        assert result.should_process is False
        assert result.skip_reason == SkipReason.EXCLUDED_PATTERN

    def test_always_exclude_template_rejected(self, candidate_filter):
        """File with 'Template' in name should be excluded."""
        result = candidate_filter.should_process("UW Model Template.xlsb")
        assert result.should_process is False
        assert result.skip_reason == SkipReason.EXCLUDED_PATTERN

    def test_temp_file_rejected(self, candidate_filter):
        """Temp file (~$) should be excluded."""
        result = candidate_filter.should_process("~$UW Model.xlsb")
        assert result.should_process is False
        assert result.skip_reason == SkipReason.EXCLUDED_PATTERN


class TestCandidateFilterEdgeCases:
    """Edge cases for CandidateFileFilter."""

    def test_xlsx_extension_accepted(self, candidate_filter):
        """XLSX UW Model should be accepted as candidate."""
        result = candidate_filter.should_process(
            "UW Model v1.xlsx",
            modified_date=datetime(2020, 1, 1),
        )
        assert result.should_process is True

    def test_xlsm_extension_accepted(self, candidate_filter):
        """XLSM UW Model should be accepted as candidate."""
        result = candidate_filter.should_process(
            "UW Model v1.xlsm",
            modified_date=datetime(2020, 1, 1),
        )
        assert result.should_process is True

    def test_case_insensitive_pattern(self, candidate_filter):
        """Pattern matching should be case-insensitive."""
        result = candidate_filter.should_process(
            "uw model v2.xlsb",
            modified_date=datetime(2020, 1, 1),
        )
        assert result.should_process is True

    def test_get_extension_no_dot(self, candidate_filter):
        """File without extension returns empty string."""
        ext = candidate_filter._get_extension("no_extension")
        assert ext == ""

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
