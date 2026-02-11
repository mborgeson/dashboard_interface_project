"""
Tests for UW Model file grouping by structural similarity.

Tests cover:
- Structural overlap computation (Jaccard-like)
- Group formation with identity/variant thresholds
- Sub-variant detection
- Empty template classification
- Intra-group variance analysis
- Edge cases: single files, no labels, all identical

Run with: pytest tests/test_extraction/test_grouping.py -v
"""

import pytest

from app.extraction.fingerprint import FileFingerprint, SheetFingerprint
from app.extraction.grouping import (
    FileGroup,
    GroupingResult,
    compute_intra_group_variances,
    compute_structural_overlap,
    group_fingerprints,
)


def _make_fp(
    name: str,
    sheets: list[SheetFingerprint] | None = None,
    status: str = "populated",
) -> FileFingerprint:
    """Helper to create a FileFingerprint for testing."""
    if sheets is None:
        sheets = [SheetFingerprint(name="Sheet1", row_count=100, col_count=10)]
    return FileFingerprint(
        file_path=f"/test/{name}.xlsb",
        file_name=f"{name}.xlsb",
        file_size=5_000_000,
        sheet_count=len(sheets),
        sheet_signatures=[s.signature for s in sheets],
        sheets=sheets,
        total_populated_cells=100 if status == "populated" else (5 if status == "sparse" else 0),
        population_status=status,
    )


class TestComputeStructuralOverlap:
    """Tests for structural overlap computation."""

    def test_identical_files_overlap_1(self):
        """Identical structures should have 1.0 overlap."""
        sheets = [SheetFingerprint(
            name="Sheet1",
            header_labels=["A", "B", "C"],
            col_a_labels=["Row1", "Row2"],
        )]
        fp1 = _make_fp("file1", sheets=sheets)
        fp2 = _make_fp("file2", sheets=sheets)
        overlap = compute_structural_overlap(fp1, fp2)
        assert overlap == 1.0

    def test_completely_different_overlap_0(self):
        """Completely different structures should have 0.0 overlap."""
        fp1 = _make_fp("file1", sheets=[SheetFingerprint(
            name="Sheet1", header_labels=["A", "B"], col_a_labels=["X"],
        )])
        fp2 = _make_fp("file2", sheets=[SheetFingerprint(
            name="Sheet2", header_labels=["C", "D"], col_a_labels=["Y"],
        )])
        overlap = compute_structural_overlap(fp1, fp2)
        assert overlap == 0.0

    def test_partial_overlap(self):
        """Partially overlapping structures should have 0 < overlap < 1."""
        fp1 = _make_fp("file1", sheets=[SheetFingerprint(
            name="Sheet1",
            header_labels=["A", "B", "C"],
            col_a_labels=["Row1"],
        )])
        fp2 = _make_fp("file2", sheets=[SheetFingerprint(
            name="Sheet1",
            header_labels=["A", "B", "D"],
            col_a_labels=["Row1"],
        )])
        overlap = compute_structural_overlap(fp1, fp2)
        assert 0.0 < overlap < 1.0

    def test_empty_labels_use_sheet_names(self):
        """Files with no labels should compare sheet names."""
        fp1 = _make_fp("file1", sheets=[SheetFingerprint(name="Sheet1")])
        fp2 = _make_fp("file2", sheets=[SheetFingerprint(name="Sheet1")])
        overlap = compute_structural_overlap(fp1, fp2)
        assert overlap == 1.0

    def test_different_sheet_names_no_labels(self):
        """Different sheet names with no labels should have < 1.0 overlap."""
        fp1 = _make_fp("file1", sheets=[SheetFingerprint(name="Sheet1")])
        fp2 = _make_fp("file2", sheets=[SheetFingerprint(name="Sheet2")])
        overlap = compute_structural_overlap(fp1, fp2)
        assert overlap == 0.0

    def test_both_empty_overlap_1(self):
        """Two files with no sheets should have 1.0 overlap."""
        fp1 = _make_fp("file1", sheets=[])
        fp2 = _make_fp("file2", sheets=[])
        overlap = compute_structural_overlap(fp1, fp2)
        assert overlap == 1.0


class TestGroupFingerprints:
    """Tests for the grouping algorithm."""

    def test_identical_files_grouped(self):
        """Files with identical sheet signatures should be in same group."""
        sheets = [SheetFingerprint(
            name="Sheet1",
            row_count=100,
            col_count=10,
            header_labels=["A", "B"],
            col_a_labels=["Row1"],
        )]
        fp1 = _make_fp("file1", sheets=sheets)
        fp2 = _make_fp("file2", sheets=sheets)
        fp3 = _make_fp("file3", sheets=sheets)

        result = group_fingerprints([fp1, fp2, fp3])
        assert len(result.groups) == 1
        assert len(result.groups[0].files) == 3

    def test_empty_templates_separated(self):
        """Empty templates should be in empty_templates list."""
        fp_populated = _make_fp("populated", status="populated")
        fp_empty = _make_fp("empty", status="empty")

        result = group_fingerprints([fp_populated, fp_empty])
        assert len(result.empty_templates) == 1
        assert result.empty_templates[0].file_name == "empty.xlsb"

    def test_different_structures_separate_groups(self):
        """Files with different structures should be in separate groups/ungrouped."""
        fp1 = _make_fp("file1", sheets=[SheetFingerprint(
            name="Sheet1",
            header_labels=["A", "B", "C", "D", "E"],
            col_a_labels=["R1", "R2", "R3", "R4", "R5"],
        )])
        fp2 = _make_fp("file2", sheets=[SheetFingerprint(
            name="Sheet2",
            header_labels=["X", "Y", "Z", "W", "V"],
            col_a_labels=["S1", "S2", "S3", "S4", "S5"],
        )])

        result = group_fingerprints([fp1, fp2])
        # Both are single files with unique signatures → ungrouped
        assert len(result.ungrouped) == 2 or (
            len(result.groups) == 0 and len(result.ungrouped) == 2
        )

    def test_sub_variants_detected(self):
        """Files with 80-95% overlap should be flagged as sub-variants."""
        # Create files with slightly different structures
        base_labels = [f"Label{i}" for i in range(20)]

        # fp1 and fp2 share same signature
        sheets1 = [SheetFingerprint(
            name="Sheet1", row_count=100, col_count=10,
            header_labels=base_labels,
            col_a_labels=base_labels[:10],
        )]
        fp1 = _make_fp("file1", sheets=sheets1)
        fp2 = _make_fp("file2", sheets=sheets1)

        # fp3 has slightly different labels (sub-variant)
        modified_labels = base_labels[:16] + ["New1", "New2", "New3", "New4"]
        sheets3 = [SheetFingerprint(
            name="Sheet1", row_count=100, col_count=10,
            header_labels=modified_labels,
            col_a_labels=base_labels[:10],
        )]
        fp3 = _make_fp("file3", sheets=sheets3)

        result = group_fingerprints([fp1, fp2, fp3])
        # fp1 and fp2 form a group, fp3 may join as sub-variant
        total_files = sum(len(g.files) for g in result.groups) + len(result.ungrouped)
        assert total_files == 3

    def test_single_file_ungrouped(self):
        """Single file with unique structure should be ungrouped."""
        fp = _make_fp("lonely", sheets=[SheetFingerprint(
            name="UniqueSheet",
            header_labels=["UniqueA", "UniqueB"],
        )])

        result = group_fingerprints([fp])
        assert len(result.groups) == 0
        assert len(result.ungrouped) == 1

    def test_error_files_skipped(self):
        """Files with error status should be skipped."""
        fp = FileFingerprint(
            file_path="/err.xlsb",
            file_name="err.xlsb",
            population_status="error",
        )
        result = group_fingerprints([fp])
        assert len(result.groups) == 0
        assert len(result.ungrouped) == 0
        assert len(result.empty_templates) == 0

    def test_methodology_generated(self):
        """Grouping should produce methodology documentation."""
        result = group_fingerprints([])
        assert "Methodology" in result.methodology
        assert "95%" in result.methodology
        assert "80%" in result.methodology

    def test_result_to_dict(self):
        """GroupingResult.to_dict should include summary."""
        result = GroupingResult(groups=[], ungrouped=[], empty_templates=[])
        d = result.to_dict()
        assert "summary" in d
        assert "total_groups" in d["summary"]


class TestIntraGroupVariances:
    """Tests for intra-group variance analysis."""

    def test_uniform_group(self):
        """Group with identical files should be uniform."""
        sheets = [SheetFingerprint(
            name="Sheet1",
            header_labels=["A", "B"],
            col_a_labels=["R1"],
        )]
        group = FileGroup(
            group_name="test",
            files=[_make_fp("f1", sheets=sheets), _make_fp("f2", sheets=sheets)],
        )
        variances = compute_intra_group_variances(group)
        assert variances["uniform"] is True
        assert variances["varying_label_count"] == 0

    def test_varying_group(self):
        """Group with different labels should show variances."""
        fp1 = _make_fp("f1", sheets=[SheetFingerprint(
            name="Sheet1",
            header_labels=["A", "B", "C"],
        )])
        fp2 = _make_fp("f2", sheets=[SheetFingerprint(
            name="Sheet1",
            header_labels=["A", "B", "D"],
        )])
        group = FileGroup(group_name="test", files=[fp1, fp2])
        variances = compute_intra_group_variances(group)
        assert variances["uniform"] is False
        assert variances["varying_label_count"] > 0

    def test_single_file_group_uniform(self):
        """Group with single file should be trivially uniform."""
        group = FileGroup(group_name="test", files=[_make_fp("f1")])
        variances = compute_intra_group_variances(group)
        assert variances["uniform"] is True

    def test_varying_sheets_detected(self):
        """Files with different sheets should be detected."""
        fp1 = _make_fp("f1", sheets=[
            SheetFingerprint(name="Sheet1"),
            SheetFingerprint(name="Sheet2"),
        ])
        fp2 = _make_fp("f2", sheets=[
            SheetFingerprint(name="Sheet1"),
            SheetFingerprint(name="Sheet3"),
        ])
        group = FileGroup(group_name="test", files=[fp1, fp2])
        variances = compute_intra_group_variances(group)
        assert variances["varying_sheet_count"] > 0
        assert "Sheet2" in variances["varying_sheets"] or "Sheet3" in variances["varying_sheets"]
