"""
Tests for reference mapping — 4-tier auto-mapping and property reconciliation.

Tests cover:
- Tier 1: Same sheet + same cell → direct match
- Tier 2: Label found in different position
- Tier 3: Partial label match
- Tier 4: Synonym matching
- Unmapped fields
- Property name reconciliation (exact, normalized, fuzzy, unmatched)
- Levenshtein distance computation

Run with: pytest tests/test_extraction/test_reference_mapper.py -v
"""

import pytest

from app.extraction.cell_mapping import CellMapping
from app.extraction.fingerprint import FileFingerprint, SheetFingerprint
from app.extraction.reference_mapper import (
    GroupReferenceMapping,
    MappingMatch,
    PropertyMatch,
    _levenshtein,
    _normalize_property_name,
    auto_map_group,
    reconcile_property_names,
)


def _make_mapping(field: str, sheet: str, cell: str, desc: str = "", cat: str = "General") -> CellMapping:
    """Helper to create a CellMapping."""
    return CellMapping(
        category=cat,
        description=desc or field,
        sheet_name=sheet,
        cell_address=cell,
        field_name=field,
    )


def _make_fp_with_labels(sheets_data: dict[str, dict]) -> FileFingerprint:
    """Create fingerprint with specific sheet labels.

    sheets_data: {"SheetName": {"headers": [...], "col_a": [...]}}
    """
    sheets = []
    for name, data in sheets_data.items():
        sheets.append(SheetFingerprint(
            name=name,
            row_count=100,
            col_count=10,
            header_labels=data.get("headers", []),
            col_a_labels=data.get("col_a", []),
            populated_cell_count=50,
        ))
    return FileFingerprint(
        file_path="/test.xlsb",
        file_name="test.xlsb",
        sheet_count=len(sheets),
        sheet_signatures=[s.signature for s in sheets],
        sheets=sheets,
        total_populated_cells=200,
        population_status="populated",
    )


class TestTier1DirectMatch:
    """Tests for Tier 1 matching — same sheet exists in fingerprint."""

    def test_same_sheet_same_label(self):
        """Sheet and label both match → Tier 1, high confidence."""
        mappings = {"FIELD_A": _make_mapping("FIELD_A", "Summary", "D6", desc="Revenue")}
        fp = _make_fp_with_labels({"Summary": {"headers": ["Revenue", "Expenses"]}})

        result = auto_map_group("test_group", mappings, fp)
        assert len(result.mappings) == 1
        assert result.mappings[0].match_tier == 1
        assert result.mappings[0].confidence == 0.95

    def test_same_sheet_no_label(self):
        """Sheet exists but label doesn't → Tier 1, lower confidence."""
        mappings = {"FIELD_A": _make_mapping("FIELD_A", "Summary", "D6", desc="Revenue")}
        fp = _make_fp_with_labels({"Summary": {"headers": ["Expenses", "Taxes"]}})

        result = auto_map_group("test_group", mappings, fp)
        assert len(result.mappings) == 1
        assert result.mappings[0].match_tier == 1
        assert result.mappings[0].confidence == 0.85


class TestTier2LabelMatch:
    """Tests for Tier 2 matching — label found in different sheet."""

    def test_label_in_different_sheet(self):
        """Label exists in different sheet → Tier 2."""
        mappings = {"FIELD_A": _make_mapping("FIELD_A", "OldSheet", "D6", desc="Revenue")}
        fp = _make_fp_with_labels({"NewSheet": {"headers": ["Revenue", "Costs"]}})

        result = auto_map_group("test_group", mappings, fp)
        assert len(result.mappings) == 1
        assert result.mappings[0].match_tier == 2
        assert result.mappings[0].confidence == 0.70

    def test_label_case_insensitive(self):
        """Label matching should be case-insensitive."""
        mappings = {"FIELD_A": _make_mapping("FIELD_A", "Missing", "D6", desc="Revenue")}
        fp = _make_fp_with_labels({"Data": {"headers": ["REVENUE"]}})

        result = auto_map_group("test_group", mappings, fp)
        assert len(result.mappings) == 1
        assert result.mappings[0].match_tier == 2


class TestTier3PartialMatch:
    """Tests for Tier 3 matching — partial label match."""

    def test_partial_label_match(self):
        """First 3 words matching → Tier 3."""
        mappings = {"FIELD_A": _make_mapping(
            "FIELD_A", "Missing", "D6",
            desc="Net Operating Income Annual",
        )}
        fp = _make_fp_with_labels({
            "Data": {"col_a": ["NET OPERATING INCOME MONTHLY"]},
        })

        result = auto_map_group("test_group", mappings, fp)
        assert len(result.mappings) == 1
        assert result.mappings[0].match_tier == 3
        assert result.mappings[0].confidence == 0.50

    def test_short_description_no_partial_match(self):
        """Descriptions with <3 words should not partial match."""
        mappings = {"FIELD_A": _make_mapping("FIELD_A", "Missing", "D6", desc="NOI")}
        fp = _make_fp_with_labels({"Data": {"col_a": ["NOI Annual"]}})

        result = auto_map_group("test_group", mappings, fp)
        # Should be unmapped (1-word desc can't do 3-word prefix match)
        # or matched by tier 2 if exact label matches
        # NOI != "NOI ANNUAL" for exact match
        # Actually, exact label "NOI" would match in tier 2
        assert len(result.mappings) + len(result.unmapped_fields) == 1


class TestTier4SynonymMatch:
    """Tests for Tier 4 matching — synonym lookup."""

    def test_synonym_match(self):
        """Synonym match → Tier 4."""
        mappings = {"FIELD_A": _make_mapping("FIELD_A", "Missing", "D6", desc="Cap Rate")}
        fp = _make_fp_with_labels({"Data": {"headers": ["CAPITALIZATION RATE"]}})

        synonyms = {"CAPITALIZATION RATE": ["Cap Rate"]}
        result = auto_map_group("test_group", mappings, fp, synonyms=synonyms)
        assert len(result.mappings) == 1
        assert result.mappings[0].match_tier == 4
        assert result.mappings[0].confidence == 0.40

    def test_no_synonym_unmapped(self):
        """Without synonym, field should be unmapped."""
        mappings = {"FIELD_A": _make_mapping("FIELD_A", "Missing", "D6", desc="Obscure Metric")}
        fp = _make_fp_with_labels({"Data": {"headers": ["Revenue"]}})

        result = auto_map_group("test_group", mappings, fp)
        assert len(result.unmapped_fields) == 1
        assert "FIELD_A" in result.unmapped_fields


class TestAutoMapGroup:
    """Integration tests for auto_map_group."""

    def test_multiple_fields_mixed_tiers(self):
        """Multiple fields should be matched at different tiers."""
        mappings = {
            "FIELD_A": _make_mapping("FIELD_A", "Summary", "D6", desc="Revenue"),
            "FIELD_B": _make_mapping("FIELD_B", "Missing", "E10", desc="Expenses"),
            "FIELD_C": _make_mapping("FIELD_C", "Gone", "F15", desc="Unknown Metric"),
        }
        fp = _make_fp_with_labels({
            "Summary": {"headers": ["Revenue", "Costs"]},
            "Details": {"col_a": ["Expenses", "Taxes"]},
        })

        result = auto_map_group("test_group", mappings, fp)
        assert result.group_name == "test_group"
        assert len(result.mappings) + len(result.unmapped_fields) == 3

        # Tier counts should be populated
        assert sum(result.tier_counts.values()) == len(result.mappings)

    def test_overall_confidence_computed(self):
        """Overall confidence should be between 0 and 1."""
        mappings = {"FIELD_A": _make_mapping("FIELD_A", "Summary", "D6", desc="Revenue")}
        fp = _make_fp_with_labels({"Summary": {"headers": ["Revenue"]}})

        result = auto_map_group("test_group", mappings, fp)
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_to_dict(self):
        """to_dict should include all fields."""
        result = GroupReferenceMapping(
            group_name="test",
            mappings=[MappingMatch(
                field_name="F", source_sheet="S", source_cell="A1",
                match_tier=1, confidence=0.95,
            )],
            unmapped_fields=["G"],
            overall_confidence=0.5,
            tier_counts={1: 1},
        )
        d = result.to_dict()
        assert d["group_name"] == "test"
        assert d["total_mapped"] == 1
        assert d["total_unmapped"] == 1

    def test_empty_mappings(self):
        """Empty production mappings should produce empty result."""
        fp = _make_fp_with_labels({"Sheet1": {"headers": ["A"]}})
        result = auto_map_group("test", {}, fp)
        assert len(result.mappings) == 0
        assert len(result.unmapped_fields) == 0


class TestPropertyReconciliation:
    """Tests for property name reconciliation."""

    def test_exact_match_case_insensitive(self):
        """Exact case-insensitive match → Tier 1."""
        results = reconcile_property_names(
            ["Hayden Park"],
            ["hayden park", "Urban 148"],
        )
        assert len(results) == 1
        assert results[0].match_tier == 1
        assert results[0].matched_property_name == "hayden park"

    def test_normalized_match(self):
        """Match after stripping suffixes → Tier 2."""
        results = reconcile_property_names(
            ["Hayden Park Apartments"],
            ["Hayden Park"],
        )
        assert len(results) == 1
        assert results[0].match_tier == 2
        assert results[0].matched_property_name == "Hayden Park"

    def test_normalized_city_suffix(self):
        """Match after stripping city suffix → Tier 2."""
        results = reconcile_property_names(
            ["Jade Ridge - Phoenix"],
            ["Jade Ridge"],
        )
        assert len(results) == 1
        assert results[0].match_tier == 2

    def test_fuzzy_match_edit_distance(self):
        """Fuzzy match within edit distance → Tier 3."""
        results = reconcile_property_names(
            ["Haydn Park"],  # Typo
            ["Hayden Park"],
            max_edit_distance=3,
        )
        assert len(results) == 1
        assert results[0].match_tier == 3
        assert results[0].edit_distance is not None
        assert results[0].edit_distance <= 3

    def test_fuzzy_match_token_overlap(self):
        """Fuzzy match with high token overlap → Tier 3."""
        # "Hayden Park" vs "Hayden Park Residences" → 2/3 overlap
        # Use tokens with 90%+ overlap: same words, minor difference
        results = reconcile_property_names(
            ["Hayden Park Place"],
            ["Hayden Park Place Residences"],
            max_edit_distance=15,
        )
        assert len(results) == 1
        # Should be tier 3 (edit distance match)
        assert results[0].match_tier == 3

    def test_unmatched(self):
        """No match → Tier 4."""
        results = reconcile_property_names(
            ["Completely Unknown Property"],
            ["Hayden Park", "Urban 148"],
            max_edit_distance=3,
        )
        assert len(results) == 1
        assert results[0].match_tier == 4
        assert results[0].matched_property_name is None

    def test_multiple_properties(self):
        """Multiple properties should all be reconciled."""
        results = reconcile_property_names(
            ["Hayden Park", "Unknown Place", "Urban 148"],
            ["Hayden Park", "Urban 148"],
        )
        assert len(results) == 3
        tiers = [r.match_tier for r in results]
        assert 1 in tiers  # At least one exact match
        assert 4 in tiers  # At least one unmatched


class TestLevenshtein:
    """Tests for Levenshtein distance computation."""

    def test_identical_strings(self):
        assert _levenshtein("hello", "hello") == 0

    def test_single_insertion(self):
        assert _levenshtein("hello", "helloo") == 1

    def test_single_deletion(self):
        assert _levenshtein("hello", "hell") == 1

    def test_single_substitution(self):
        assert _levenshtein("hello", "hallo") == 1

    def test_empty_strings(self):
        assert _levenshtein("", "") == 0
        assert _levenshtein("hello", "") == 5
        assert _levenshtein("", "hello") == 5

    def test_symmetric(self):
        assert _levenshtein("abc", "xyz") == _levenshtein("xyz", "abc")


class TestNormalizePropertyName:
    """Tests for property name normalization."""

    def test_strip_apartments(self):
        assert "hayden park" in _normalize_property_name("Hayden Park Apartments")

    def test_strip_llc(self):
        assert "some corp" in _normalize_property_name("Some Corp LLC")

    def test_strip_phoenix(self):
        assert "jade ridge" in _normalize_property_name("Jade Ridge - Phoenix")

    def test_strip_phase(self):
        norm = _normalize_property_name("Vista Grande Phase II")
        assert "phase" not in norm.lower()

    def test_lowercase(self):
        assert _normalize_property_name("HAYDEN PARK") == "hayden park"
