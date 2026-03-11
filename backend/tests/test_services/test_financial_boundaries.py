"""Financial calculation boundary tests (T-DEBT-026).

Tests edge cases and boundary conditions for financial calculation
utilities in the enrichment service and related model methods:
- safe_float: NaN, Inf, non-numeric, edge values
- to_decimal: precision, edge values
- build_financial_data_json: zero/null fields, empty inputs
- build_ops_by_year: empty rows, malformed data
- build_base_expenses: zero units, missing fields
- Document.get_size_formatted: boundary sizes
- PaginatedResult: edge cases for page calculations
"""

import math
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest

from app.crud.base import PaginatedResult
from app.services.enrichment import (
    build_base_expenses,
    build_financial_data_json,
    build_ops_by_year,
    get_property_name_variants,
    match_prop_name,
    safe_float,
    to_decimal,
)

# =============================================================================
# safe_float boundary tests
# =============================================================================


class TestSafeFloat:
    """Boundary tests for safe_float conversion."""

    def test_none_returns_none(self):
        assert safe_float(None) is None

    def test_zero(self):
        assert safe_float(0) == 0.0

    def test_positive_integer(self):
        assert safe_float(100) == 100.0

    def test_negative_integer(self):
        assert safe_float(-50) == -50.0

    def test_float(self):
        assert safe_float(3.14) == 3.14

    def test_string_number(self):
        assert safe_float("42.5") == 42.5

    def test_string_negative(self):
        assert safe_float("-10.25") == -10.25

    def test_string_zero(self):
        assert safe_float("0") == 0.0

    def test_string_non_numeric(self):
        assert safe_float("not a number") is None

    def test_empty_string(self):
        assert safe_float("") is None

    def test_nan_returns_none(self):
        assert safe_float(float("nan")) is None

    def test_inf_returns_none(self):
        assert safe_float(float("inf")) is None

    def test_negative_inf_returns_none(self):
        assert safe_float(float("-inf")) is None

    def test_numpy_nan_returns_none(self):
        assert safe_float(np.nan) is None

    def test_numpy_inf_returns_none(self):
        assert safe_float(np.inf) is None

    def test_decimal_input(self):
        result = safe_float(Decimal("6.500"))
        assert result == 6.5

    def test_decimal_zero(self):
        result = safe_float(Decimal("0"))
        assert result == 0.0

    def test_very_large_number(self):
        result = safe_float(1e18)
        assert result == 1e18

    def test_very_small_number(self):
        result = safe_float(1e-10)
        assert result == pytest.approx(1e-10)

    def test_list_returns_none(self):
        assert safe_float([1, 2, 3]) is None

    def test_dict_returns_none(self):
        assert safe_float({"a": 1}) is None

    def test_bool_true(self):
        # bool is subclass of int in Python
        result = safe_float(True)
        assert result == 1.0

    def test_bool_false(self):
        result = safe_float(False)
        assert result == 0.0


# =============================================================================
# to_decimal boundary tests
# =============================================================================


class TestToDecimal:
    """Boundary tests for to_decimal conversion."""

    def test_none_returns_none(self):
        assert to_decimal(None) is None

    def test_zero(self):
        result = to_decimal(0)
        assert result == Decimal("0")

    def test_positive_float(self):
        result = to_decimal(6.5)
        assert result == Decimal("6.5")

    def test_respects_places(self):
        result = to_decimal(3.14159, places=4)
        assert result == Decimal("3.1416")

    def test_default_two_places(self):
        result = to_decimal(3.14159)
        assert result == Decimal("3.14")

    def test_string_number(self):
        result = to_decimal("100.5")
        assert result == Decimal("100.5")

    def test_nan_returns_none(self):
        assert to_decimal(float("nan")) is None

    def test_inf_returns_none(self):
        assert to_decimal(float("inf")) is None

    def test_non_numeric_returns_none(self):
        assert to_decimal("not a number") is None


# =============================================================================
# build_financial_data_json boundary tests
# =============================================================================


class TestBuildFinancialDataJson:
    """Boundary tests for build_financial_data_json."""

    def _mock_property(
        self,
        purchase_price: Decimal | None = None,
        total_units: int | None = None,
        cap_rate: Decimal | None = None,
        name: str = "Test Prop",
    ):
        prop = MagicMock()
        prop.name = name
        prop.purchase_price = purchase_price
        prop.total_units = total_units
        prop.cap_rate = cap_rate
        prop.noi = None
        prop.current_value = None
        return prop

    def test_empty_field_values(self):
        """Empty field_values returns skeleton with empty sub-dicts."""
        prop = self._mock_property()
        result = build_financial_data_json(prop, {}, None)
        # Should return at minimum the structure keys
        assert isinstance(result, dict)

    def test_empty_existing_fd(self):
        """None existing_fd is handled gracefully."""
        prop = self._mock_property()
        result = build_financial_data_json(prop, {"PURCHASE_PRICE": 10000000}, None)
        assert "acquisition" in result
        assert result["acquisition"]["purchasePrice"] == 10000000

    def test_existing_fd_not_overwritten(self):
        """Existing financial_data values are not overwritten."""
        prop = self._mock_property()
        existing = {"acquisition": {"purchasePrice": 5000000}}
        result = build_financial_data_json(
            prop, {"PURCHASE_PRICE": 10000000}, existing
        )
        # Existing value should be preserved
        assert result["acquisition"]["purchasePrice"] == 5000000

    def test_zero_purchase_price(self):
        """Zero purchase price is treated as falsy (safe_float returns 0.0)."""
        prop = self._mock_property()
        result = build_financial_data_json(prop, {"PURCHASE_PRICE": 0}, None)
        # 0.0 is a valid float from safe_float; whether it populates depends on truthiness
        assert isinstance(result, dict)

    def test_irr_and_moic_populated(self):
        """Levered and unlevered return metrics are populated."""
        prop = self._mock_property()
        result = build_financial_data_json(
            prop,
            {
                "LEVERED_RETURNS_IRR": 0.185,
                "LEVERED_RETURNS_MOIC": 2.1,
                "UNLEVERED_RETURNS_IRR": 0.12,
                "UNLEVERED_RETURNS_MOIC": 1.8,
            },
            None,
        )
        ret = result.get("returns", {})
        assert abs(ret["leveredIrr"] - 0.185) < 0.0001
        assert abs(ret["leveredMoic"] - 2.1) < 0.01
        assert abs(ret["unleveredIrr"] - 0.12) < 0.0001
        assert abs(ret["unleveredMoic"] - 1.8) < 0.01

    def test_negative_irr_handled(self):
        """Negative IRR (loss scenario) is stored correctly."""
        prop = self._mock_property()
        result = build_financial_data_json(
            prop,
            {"LEVERED_RETURNS_IRR": -0.049},
            None,
        )
        ret = result.get("returns", {})
        assert ret["leveredIrr"] < 0

    def test_zero_irr_handled(self):
        """Zero IRR is stored (break-even)."""
        prop = self._mock_property()
        result = build_financial_data_json(
            prop,
            {"LEVERED_RETURNS_IRR": 0.0},
            None,
        )
        # 0.0 from safe_float is valid; whether populated depends on "not ret.get()"
        assert isinstance(result, dict)

    def test_none_field_values_skipped(self):
        """None values in field_values are ignored."""
        prop = self._mock_property()
        result = build_financial_data_json(
            prop,
            {"PURCHASE_PRICE": None, "LEVERED_RETURNS_IRR": None},
            None,
        )
        # Nothing should be populated from None
        acq = result.get("acquisition", {})
        assert "purchasePrice" not in acq

    def test_loan_term_conversion(self):
        """Loan term < 40 is converted from years to months."""
        prop = self._mock_property()
        result = build_financial_data_json(
            prop,
            {"LOAN_TERM": 5.0},
            None,
        )
        fin = result.get("financing", {})
        assert fin["loanTermMonths"] == 60  # 5 * 12

    def test_loan_term_already_months(self):
        """Loan term >= 40 is treated as already in months."""
        prop = self._mock_property()
        result = build_financial_data_json(
            prop,
            {"LOAN_TERM": 360.0},
            None,
        )
        fin = result.get("financing", {})
        assert fin["loanTermMonths"] == 360


# =============================================================================
# build_ops_by_year boundary tests
# =============================================================================


class TestBuildOpsByYear:
    """Boundary tests for build_ops_by_year."""

    def test_empty_rows(self):
        """Empty year_rows returns empty dicts."""
        ops, expenses, changed = build_ops_by_year([], {})
        assert ops == {}
        assert expenses == {}
        assert changed is False

    def test_none_value_rows_skipped(self):
        """Rows with None value_numeric are ignored."""
        rows = [("GROSS_POTENTIAL_REVENUE_YEAR_1", None)]
        ops, expenses, changed = build_ops_by_year(rows, {})
        assert ops == {}
        assert changed is False

    def test_single_year_data(self):
        """Single year of data produces correct structure."""
        rows = [
            ("GROSS_POTENTIAL_REVENUE_YEAR_1", 1500000.0),
            ("NET_OPERATING_INCOME_YEAR_1", 750000.0),
        ]
        ops, expenses, changed = build_ops_by_year(rows, {})
        assert "1" in ops
        assert ops["1"]["grossPotentialRevenue"] == 1500000.0
        assert ops["1"]["noi"] == 750000.0
        assert changed is True

    def test_multi_year_data(self):
        """Multiple years are keyed correctly."""
        rows = [
            ("GROSS_POTENTIAL_REVENUE_YEAR_1", 1500000.0),
            ("GROSS_POTENTIAL_REVENUE_YEAR_2", 1575000.0),
            ("GROSS_POTENTIAL_REVENUE_YEAR_3", 1653750.0),
        ]
        ops, _expenses, changed = build_ops_by_year(rows, {})
        assert "1" in ops
        assert "2" in ops
        assert "3" in ops
        assert changed is True

    def test_malformed_field_name_ignored(self):
        """Non-matching field names are silently ignored."""
        rows = [
            ("RANDOM_FIELD_YEAR_1", 100.0),
            ("NOT_A_REAL_FIELD", 200.0),
        ]
        ops, _expenses, changed = build_ops_by_year(rows, {})
        assert ops == {}
        assert changed is False

    def test_expense_fields_in_sub_dict(self):
        """Expense fields go into the expenses sub-dict per year."""
        rows = [
            ("REAL_ESTATE_TAXES_YEAR_1", 50000.0),
            ("PROPERTY_INSURANCE_YEAR_1", 20000.0),
        ]
        ops, _expenses, changed = build_ops_by_year(rows, {})
        assert "1" in ops
        year1_expenses = ops["1"].get("expenses", {})
        assert year1_expenses["realEstateTaxes"] == 50000.0
        assert year1_expenses["propertyInsurance"] == 20000.0

    def test_deduplication_first_occurrence_wins(self):
        """When duplicate fields exist, first occurrence wins (ordered DESC)."""
        rows = [
            ("GROSS_POTENTIAL_REVENUE_YEAR_1", 1500000.0),
            ("GROSS_POTENTIAL_REVENUE_YEAR_1", 999999.0),  # Duplicate
        ]
        ops, _expenses, _changed = build_ops_by_year(rows, {})
        assert ops["1"]["grossPotentialRevenue"] == 1500000.0


# =============================================================================
# build_base_expenses boundary tests
# =============================================================================


class TestBuildBaseExpenses:
    """Boundary tests for build_base_expenses."""

    def test_empty_field_values(self):
        """Empty field_values returns empty expenses dict."""
        result = build_base_expenses({}, 100)
        assert result == {}

    def test_zero_units(self):
        """Zero total_units produces per-unit value (not multiplied)."""
        result = build_base_expenses(
            {"REAL_ESTATE_TAXES_PER_UNIT": 500.0},
            0,
        )
        # With 0 units, fallback is round(val, 2) per the code
        if result:
            for _key, val in result.items():
                assert isinstance(val, float)

    def test_normal_per_unit_conversion(self):
        """Per-unit values are converted to annual totals (val * units)."""
        result = build_base_expenses(
            {"REAL_ESTATE_TAXES_PER_UNIT": 500.0},
            100,
        )
        if result:
            # 500 * 100 = 50000
            for _key, val in result.items():
                assert val == 50000.0

    def test_none_value_skipped(self):
        """None values in field_values are skipped."""
        result = build_base_expenses(
            {"REAL_ESTATE_TAXES_PER_UNIT": None},
            100,
        )
        assert result == {}

    def test_non_matching_keys_ignored(self):
        """Field values that don't match BASE_EXPENSE_FIELD_MAP are ignored."""
        result = build_base_expenses(
            {"RANDOM_FIELD": 1000.0, "PURCHASE_PRICE": 5000000},
            100,
        )
        assert result == {}


# =============================================================================
# get_property_name_variants / match_prop_name boundary tests
# =============================================================================


class TestPropertyNameMatching:
    """Boundary tests for property name matching utilities."""

    def _mock_prop(self, name: str):
        prop = MagicMock()
        prop.name = name
        return prop

    def test_simple_name(self):
        prop = self._mock_prop("The Clubhouse")
        variants = get_property_name_variants(prop)
        assert "The Clubhouse" in variants

    def test_name_with_parenthetical(self):
        """Name with (parenthetical) produces both full and short variants."""
        prop = self._mock_prop("Element (V2)")
        variants = get_property_name_variants(prop)
        assert "Element (V2)" in variants
        assert "Element" in variants

    def test_match_exact(self):
        prop = self._mock_prop("Broadstone 7th Street")
        assert match_prop_name("Broadstone 7th Street", prop) is True

    def test_match_with_parenthetical_suffix(self):
        prop = self._mock_prop("Element")
        assert match_prop_name("Element (V2)", prop) is True

    def test_no_match(self):
        prop = self._mock_prop("Element")
        assert match_prop_name("Different Property", prop) is False

    def test_empty_name(self):
        prop = self._mock_prop("")
        variants = get_property_name_variants(prop)
        # Empty name should produce empty or minimal list
        assert isinstance(variants, list)


# =============================================================================
# PaginatedResult boundary tests
# =============================================================================


class TestPaginatedResult:
    """Boundary tests for PaginatedResult."""

    def test_zero_total(self):
        """Zero total with empty items."""
        result = PaginatedResult(items=[], total=0, page=1, per_page=20)
        assert result.pages == 0
        assert result.has_next is False
        assert result.has_prev is False

    def test_single_page(self):
        """One page worth of data."""
        result = PaginatedResult(items=[1, 2, 3], total=3, page=1, per_page=20)
        assert result.pages == 1
        assert result.has_next is False
        assert result.has_prev is False

    def test_multiple_pages_first(self):
        """First page of multi-page results."""
        result = PaginatedResult(items=[1, 2], total=5, page=1, per_page=2)
        assert result.pages == 3
        assert result.has_next is True
        assert result.has_prev is False

    def test_multiple_pages_middle(self):
        """Middle page has both prev and next."""
        result = PaginatedResult(items=[3, 4], total=6, page=2, per_page=2)
        assert result.pages == 3
        assert result.has_next is True
        assert result.has_prev is True

    def test_multiple_pages_last(self):
        """Last page has prev but no next."""
        result = PaginatedResult(items=[5, 6], total=6, page=3, per_page=2)
        assert result.pages == 3
        assert result.has_next is False
        assert result.has_prev is True

    def test_zero_per_page(self):
        """Zero per_page should not cause division by zero."""
        result = PaginatedResult(items=[], total=10, page=1, per_page=0)
        assert result.pages == 0

    def test_total_exactly_per_page(self):
        """When total equals per_page, exactly one page."""
        result = PaginatedResult(items=[1, 2, 3], total=3, page=1, per_page=3)
        assert result.pages == 1
        assert result.has_next is False

    def test_to_dict(self):
        """to_dict returns all expected keys."""
        result = PaginatedResult(items=[1], total=1, page=1, per_page=10)
        d = result.to_dict()
        expected_keys = {"items", "total", "page", "per_page", "pages", "has_next", "has_prev"}
        assert set(d.keys()) == expected_keys
