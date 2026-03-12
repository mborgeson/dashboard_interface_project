"""
Tests for extraction output validation.

Covers:
- Valid values pass checks
- Out-of-range values flagged as errors
- Boundary values handled correctly
- Warning-level flags for unusual but possible values
- None/missing values handled gracefully
- Multiple validation errors collected (not fail-fast)
"""

import math

import numpy as np
import pytest

from app.extraction.output_validation import (
    VALIDATION_RULES,
    ValidationResult,
    ValidationRule,
    ValidationStatus,
    ValidationSummary,
    validate_extraction_output,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result_for(summary: ValidationSummary, field: str) -> ValidationResult:
    """Return the first result matching a field name."""
    for r in summary.results:
        if r.field_name == field:
            return r
    raise KeyError(f"No result for field '{field}'")


# ---------------------------------------------------------------------------
# Happy path: all values within normal range
# ---------------------------------------------------------------------------


class TestValidValues:
    """Values comfortably inside expected ranges should be VALID."""

    def test_typical_phoenix_deal(self):
        extracted = {
            "cap_rate": 5.5,
            "purchase_price": 25_000_000,
            "total_units": 150,
            "year_built": 1985,
            "noi": 1_500_000,
            "avg_rent": 1_200,
            "price_per_unit": 166_667,
            "occupancy": 93.5,
            "total_sf": 120_000,
        }
        summary = validate_extraction_output(extracted)

        assert summary.errors == 0
        assert summary.warnings == 0
        assert summary.valid == len(summary.results) - summary.skipped

    def test_each_field_valid_individually(self):
        cases = [
            ("cap_rate", 6.0),
            ("purchase_price", 50_000_000),
            ("unit_count", 200),
            ("year_built", 2000),
            ("noi", 3_000_000),
            ("rent_per_unit", 1_100),
            ("price_per_unit", 150_000),
            ("occupancy", 95.0),
            ("sqft", 100_000),
        ]
        for field_name, value in cases:
            summary = validate_extraction_output({field_name: value})
            result = _result_for(summary, field_name)
            assert result.status == ValidationStatus.VALID, (
                f"{field_name}={value} should be VALID, got {result.status}: {result.message}"
            )


# ---------------------------------------------------------------------------
# Error range: values outside hard bounds
# ---------------------------------------------------------------------------


class TestErrorValues:
    """Values outside hard bounds should be flagged as ERROR."""

    @pytest.mark.parametrize(
        "field_name, value",
        [
            ("cap_rate", -1.0),
            ("cap_rate", 25.0),
            ("purchase_price", 50),
            ("purchase_price", 1_000_000_000),
            ("unit_count", 0),
            ("unit_count", 10_000),
            ("year_built", 1800),
            ("year_built", 2030),
            ("noi", -50_000_000),
            ("noi", 200_000_000),
            ("rent_per_unit", -100),
            ("rent_per_unit", 20_000),
            ("price_per_unit", 5_000),
            ("price_per_unit", 2_000_000),
            ("occupancy", -5),
            ("occupancy", 110),
            ("sqft", 10),
            ("sqft", 100_000_000),
        ],
    )
    def test_out_of_range_is_error(self, field_name: str, value: float):
        summary = validate_extraction_output({field_name: value})
        result = _result_for(summary, field_name)
        assert result.status == ValidationStatus.ERROR, (
            f"{field_name}={value} should be ERROR, got {result.status}: {result.message}"
        )


# ---------------------------------------------------------------------------
# Warning range: unusual but technically valid
# ---------------------------------------------------------------------------


class TestWarningValues:
    """Values inside hard bounds but outside typical range -> WARNING."""

    @pytest.mark.parametrize(
        "field_name, value",
        [
            ("cap_rate", 1.0),  # below warning_min 2.0
            ("cap_rate", 18.0),  # above warning_max 15.0
            ("purchase_price", 200_000),  # below warning_min 1M
            ("purchase_price", 300_000_000),  # above warning_max 200M
            ("unit_count", 5),  # below warning_min 10
            ("unit_count", 3000),  # above warning_max 2000
            ("year_built", 1910),  # below warning_min 1950
            ("noi", -500_000),  # below warning_min 0
            ("noi", 60_000_000),  # above warning_max 50M
            ("rent_per_unit", 200),  # below warning_min 400
            ("rent_per_unit", 7_000),  # above warning_max 5000
            ("price_per_unit", 15_000),  # below warning_min 30K
            ("price_per_unit", 700_000),  # above warning_max 500K
            ("occupancy", 30),  # below warning_min 50
            ("sqft", 500),  # below warning_min 5000
            ("sqft", 8_000_000),  # above warning_max 5M
        ],
    )
    def test_unusual_value_is_warning(self, field_name: str, value: float):
        summary = validate_extraction_output({field_name: value})
        result = _result_for(summary, field_name)
        assert result.status == ValidationStatus.WARNING, (
            f"{field_name}={value} should be WARNING, got {result.status}: {result.message}"
        )


# ---------------------------------------------------------------------------
# Boundary values: exactly at the edges
# ---------------------------------------------------------------------------


class TestBoundaryValues:
    """Values exactly at boundaries should be correct status."""

    def test_cap_rate_at_zero_is_valid(self):
        """0% cap rate is at the hard min, so valid (>= min_value)."""
        summary = validate_extraction_output({"cap_rate": 0.0})
        result = _result_for(summary, "cap_rate")
        # 0.0 >= min(0.0) but < warning_min(2.0) -> WARNING
        assert result.status == ValidationStatus.WARNING

    def test_cap_rate_at_20_is_valid(self):
        """20% cap rate is at the hard max, so not error (<=)."""
        summary = validate_extraction_output({"cap_rate": 20.0})
        result = _result_for(summary, "cap_rate")
        # 20.0 <= max(20.0) but > warning_max(15.0) -> WARNING
        assert result.status == ValidationStatus.WARNING

    def test_unit_count_at_one(self):
        """1 unit is at the hard min."""
        summary = validate_extraction_output({"unit_count": 1})
        result = _result_for(summary, "unit_count")
        # 1 >= min(1) but < warning_min(10) -> WARNING
        assert result.status == ValidationStatus.WARNING

    def test_occupancy_at_100(self):
        """100% occupancy is at max and within warning range."""
        summary = validate_extraction_output({"occupancy": 100.0})
        result = _result_for(summary, "occupancy")
        assert result.status == ValidationStatus.VALID

    def test_occupancy_at_zero(self):
        """0% occupancy is at hard min but below warning_min."""
        summary = validate_extraction_output({"occupancy": 0.0})
        result = _result_for(summary, "occupancy")
        assert result.status == ValidationStatus.WARNING

    def test_purchase_price_at_min(self):
        """$100K is at hard min but below warning_min."""
        summary = validate_extraction_output({"purchase_price": 100_000})
        result = _result_for(summary, "purchase_price")
        assert result.status == ValidationStatus.WARNING

    def test_purchase_price_at_max(self):
        """$500M is at hard max but above warning_max."""
        summary = validate_extraction_output({"purchase_price": 500_000_000})
        result = _result_for(summary, "purchase_price")
        assert result.status == ValidationStatus.WARNING


# ---------------------------------------------------------------------------
# None / missing / NaN handling
# ---------------------------------------------------------------------------


class TestMissingValues:
    """None, NaN, and empty string values should be SKIPPED, not error."""

    def test_none_value_skipped(self):
        summary = validate_extraction_output({"cap_rate": None})
        result = _result_for(summary, "cap_rate")
        assert result.status == ValidationStatus.SKIPPED

    def test_nan_value_skipped(self):
        summary = validate_extraction_output({"noi": np.nan})
        result = _result_for(summary, "noi")
        assert result.status == ValidationStatus.SKIPPED

    def test_float_nan_skipped(self):
        summary = validate_extraction_output({"purchase_price": float("nan")})
        result = _result_for(summary, "purchase_price")
        assert result.status == ValidationStatus.SKIPPED

    def test_empty_string_skipped(self):
        summary = validate_extraction_output({"occupancy": ""})
        result = _result_for(summary, "occupancy")
        assert result.status == ValidationStatus.SKIPPED

    def test_whitespace_string_skipped(self):
        summary = validate_extraction_output({"unit_count": "   "})
        result = _result_for(summary, "unit_count")
        assert result.status == ValidationStatus.SKIPPED

    def test_non_numeric_string_skipped(self):
        summary = validate_extraction_output({"year_built": "N/A"})
        result = _result_for(summary, "year_built")
        assert result.status == ValidationStatus.SKIPPED


# ---------------------------------------------------------------------------
# Multiple errors collected (not fail-fast)
# ---------------------------------------------------------------------------


class TestMultipleErrors:
    """All fields should be validated even if some have errors."""

    def test_collects_all_errors(self):
        extracted = {
            "cap_rate": -5.0,  # ERROR
            "purchase_price": 10,  # ERROR
            "unit_count": 0,  # ERROR
            "year_built": 1800,  # ERROR
            "noi": 200_000_000,  # ERROR
        }
        summary = validate_extraction_output(extracted)
        assert summary.errors == 5
        assert summary.total == 5

    def test_mixed_statuses(self):
        extracted = {
            "cap_rate": 6.0,  # VALID
            "purchase_price": 200,  # ERROR
            "unit_count": 5,  # WARNING
            "year_built": None,  # SKIPPED
        }
        summary = validate_extraction_output(extracted)
        assert summary.valid == 1
        assert summary.errors == 1
        assert summary.warnings == 1
        assert summary.skipped == 1
        assert summary.total == 4

    def test_summary_properties(self):
        extracted = {
            "cap_rate": -5.0,
            "noi": 1_000,
        }
        summary = validate_extraction_output(extracted)
        assert summary.has_errors is True
        # noi=1000 is within warning range (0 to 50M)
        assert summary.has_warnings is False


# ---------------------------------------------------------------------------
# Metadata fields ignored
# ---------------------------------------------------------------------------


class TestMetadataSkipped:
    """Fields starting with '_' should be ignored entirely."""

    def test_metadata_fields_not_validated(self):
        extracted = {
            "_file_path": "/some/path.xlsx",
            "_extraction_timestamp": "2026-01-01T00:00:00",
            "_extraction_errors": [],
            "_extraction_metadata": {},
            "cap_rate": 6.0,
        }
        summary = validate_extraction_output(extracted)
        assert summary.total == 1
        assert summary.valid == 1


# ---------------------------------------------------------------------------
# Unmatched fields ignored
# ---------------------------------------------------------------------------


class TestUnmatchedFields:
    """Fields that don't match any rule pattern are silently skipped."""

    def test_unknown_field_not_validated(self):
        extracted = {
            "some_random_field": 999_999,
            "another_thing": "hello",
        }
        summary = validate_extraction_output(extracted)
        assert summary.total == 0

    def test_mixed_known_unknown(self):
        extracted = {
            "cap_rate": 6.0,
            "unknown_metric": 42,
        }
        summary = validate_extraction_output(extracted)
        assert summary.total == 1


# ---------------------------------------------------------------------------
# Custom rules
# ---------------------------------------------------------------------------


class TestCustomRules:
    """Callers can pass custom rules instead of defaults."""

    def test_custom_rule_applied(self):
        custom = [
            ValidationRule(
                name="custom_metric",
                field_patterns=["my_metric"],
                min_value=0,
                max_value=100,
            ),
        ]
        summary = validate_extraction_output({"my_metric": 50}, rules=custom)
        assert summary.valid == 1

        summary_err = validate_extraction_output({"my_metric": 200}, rules=custom)
        assert summary_err.errors == 1


# ---------------------------------------------------------------------------
# String numeric conversion
# ---------------------------------------------------------------------------


class TestStringConversion:
    """Numeric strings (with $, commas, %) should be parsed."""

    def test_dollar_string(self):
        summary = validate_extraction_output({"purchase_price": "$25,000,000"})
        result = _result_for(summary, "purchase_price")
        assert result.status == ValidationStatus.VALID

    def test_percentage_string(self):
        summary = validate_extraction_output({"cap_rate": "5.5%"})
        result = _result_for(summary, "cap_rate")
        assert result.status == ValidationStatus.VALID

    def test_comma_formatted_number(self):
        summary = validate_extraction_output({"noi": "1,500,000"})
        result = _result_for(summary, "noi")
        assert result.status == ValidationStatus.VALID


# ---------------------------------------------------------------------------
# ValidationRule.matches_field
# ---------------------------------------------------------------------------


class TestRuleMatching:
    """Verify field name pattern matching handles variations."""

    def test_exact_pattern(self):
        rule = VALIDATION_RULES[0]  # cap_rate
        assert rule.matches_field("cap_rate")

    def test_case_insensitive(self):
        rule = VALIDATION_RULES[0]
        assert rule.matches_field("Cap_Rate")
        assert rule.matches_field("CAP_RATE")

    def test_with_spaces(self):
        rule = VALIDATION_RULES[0]
        assert rule.matches_field("cap rate")

    def test_with_hyphens(self):
        rule = VALIDATION_RULES[0]
        assert rule.matches_field("cap-rate")

    def test_partial_match(self):
        """Pattern 'cap_rate' should match 'going_in_cap_rate'."""
        rule = VALIDATION_RULES[0]
        assert rule.matches_field("going_in_cap_rate")

    def test_no_match(self):
        rule = VALIDATION_RULES[0]
        assert not rule.matches_field("purchase_price")
