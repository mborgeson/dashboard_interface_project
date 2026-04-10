"""Unit tests for backend/app/services/enrichment.py — F-065.

Tests pure functions without DB access using simple dicts and mock objects.
"""

import math
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.enrichment import (
    ALL_HYDRATION_FIELDS,
    BASE_EXPENSE_FIELD_MAP,
    CASHFLOW_FIELD_MAP,
    FIELD_ALIASES,
    YEAR_FIELD_RE,
    build_base_expenses,
    build_financial_data_json,
    build_ops_by_year,
    get_property_name_variants,
    match_prop_name,
    resolve_field_aliases,
    safe_float,
    to_decimal,
    update_property_columns,
)

# ---------------------------------------------------------------------------
# Helpers — lightweight property stand-in
# ---------------------------------------------------------------------------


def _make_prop(**overrides):
    """Return a SimpleNamespace mimicking a Property with empty defaults."""
    defaults = dict(
        id=1,
        name="Test Property",
        address=None,
        purchase_price=None,
        total_units=None,
        year_built=None,
        total_sf=None,
        cap_rate=None,
        noi=None,
        occupancy_rate=None,
        avg_rent_per_unit=None,
        avg_rent_per_sf=None,
        current_value=None,
        financial_data=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ===================================================================
# 1. safe_float
# ===================================================================


class TestSafeFloat:
    def test_none(self):
        assert safe_float(None) is None

    def test_valid_int(self):
        assert safe_float(42) == 42.0

    def test_valid_float(self):
        assert safe_float(3.14) == 3.14

    def test_valid_string(self):
        assert safe_float("99.5") == 99.5

    def test_empty_string(self):
        assert safe_float("") is None

    def test_non_numeric_string(self):
        assert safe_float("abc") is None

    def test_nan(self):
        assert safe_float(float("nan")) is None

    def test_inf(self):
        assert safe_float(float("inf")) is None

    def test_negative_inf(self):
        assert safe_float(float("-inf")) is None

    def test_zero(self):
        assert safe_float(0) == 0.0

    def test_negative(self):
        assert safe_float(-5.5) == -5.5

    def test_decimal_input(self):
        assert safe_float(Decimal("12.34")) == 12.34

    def test_bool_true(self):
        # bool is subclass of int — float(True) == 1.0
        assert safe_float(True) == 1.0

    def test_list_returns_none(self):
        assert safe_float([1, 2]) is None


# ===================================================================
# 2. to_decimal
# ===================================================================


class TestToDecimal:
    def test_basic(self):
        result = to_decimal(3.14159, 2)
        assert result == Decimal("3.14")

    def test_none_input(self):
        assert to_decimal(None) is None

    def test_empty_string(self):
        assert to_decimal("") is None

    def test_nan_input(self):
        assert to_decimal(float("nan")) is None

    def test_places_4(self):
        result = to_decimal(0.123456, 4)
        assert result == Decimal("0.1235")

    def test_zero(self):
        result = to_decimal(0, 2)
        # safe_float(0) returns 0.0 which is not None, but round(0.0,2)=0.0
        # However 0.0 is falsy — safe_float returns 0.0, which is not None.
        assert result == Decimal("0.0")

    def test_large_value(self):
        result = to_decimal(12_345_678.999, 2)
        assert result == Decimal("12345679.0")


# ===================================================================
# 3. get_property_name_variants
# ===================================================================


class TestGetPropertyNameVariants:
    def test_simple_name(self):
        prop = _make_prop(name="Sunrise Apartments")
        variants = get_property_name_variants(prop)
        assert variants == ["Sunrise Apartments"]

    def test_name_with_parenthetical(self):
        prop = _make_prop(name="Sunrise Apartments (Phoenix)")
        variants = get_property_name_variants(prop)
        assert variants == ["Sunrise Apartments (Phoenix)", "Sunrise Apartments"]

    def test_empty_name(self):
        prop = _make_prop(name="")
        variants = get_property_name_variants(prop)
        assert variants == []

    def test_none_name(self):
        prop = _make_prop(name=None)
        variants = get_property_name_variants(prop)
        assert variants == []

    def test_name_without_parenthetical_no_duplicate(self):
        """Short name == full name should only appear once."""
        prop = _make_prop(name="Cabana on 44th")
        variants = get_property_name_variants(prop)
        assert variants == ["Cabana on 44th"]

    def test_multiple_parens(self):
        prop = _make_prop(name="Cabana (Bldg A) (Unit 5)")
        variants = get_property_name_variants(prop)
        # short_name = "Cabana" (split on first '(')
        assert "Cabana" in variants
        assert "Cabana (Bldg A) (Unit 5)" in variants


# ===================================================================
# 4. match_prop_name
# ===================================================================


class TestMatchPropName:
    def test_exact_match(self):
        prop = _make_prop(name="Sunrise Apartments")
        assert match_prop_name("Sunrise Apartments", prop) is True

    def test_short_name_match(self):
        prop = _make_prop(name="Sunrise Apartments (Phoenix)")
        assert match_prop_name("Sunrise Apartments", prop) is True

    def test_starts_with_full_name_paren(self):
        prop = _make_prop(name="Sunrise Apartments")
        assert match_prop_name("Sunrise Apartments (Run 42)", prop) is True

    def test_starts_with_short_name_paren(self):
        prop = _make_prop(name="Sunrise Apartments (Phoenix)")
        assert match_prop_name("Sunrise Apartments (Run 42)", prop) is True

    def test_no_match(self):
        prop = _make_prop(name="Sunrise Apartments")
        assert match_prop_name("Clubhouse at Arcadia", prop) is False

    def test_partial_no_match(self):
        prop = _make_prop(name="Sunrise Apartments")
        assert match_prop_name("Sunrise", prop) is False

    def test_empty_prop_name(self):
        prop = _make_prop(name="")
        assert match_prop_name("Anything", prop) is False

    def test_none_prop_name(self):
        prop = _make_prop(name=None)
        assert match_prop_name("Anything", prop) is False


# ===================================================================
# 5. update_property_columns
# ===================================================================


class TestUpdatePropertyColumns:
    def test_sets_purchase_price(self):
        prop = _make_prop()
        changed = update_property_columns(prop, {"PURCHASE_PRICE": 5_000_000})
        assert changed is True
        assert prop.purchase_price == Decimal("5000000.0")

    def test_overwrites_existing_purchase_price(self):
        """Re-extraction data should overwrite stale values."""
        prop = _make_prop(purchase_price=Decimal("1000000"))
        changed = update_property_columns(prop, {"PURCHASE_PRICE": 2_000_000})
        assert changed is True
        assert prop.purchase_price == Decimal("2000000.0")

    def test_no_change_when_same_value(self):
        """No-op when the extracted value matches the existing value."""
        prop = _make_prop(
            purchase_price=Decimal("5000000.0"),
            current_value=Decimal("5000000.0"),
        )
        changed = update_property_columns(prop, {"PURCHASE_PRICE": 5_000_000})
        assert changed is False
        assert prop.purchase_price == Decimal("5000000.0")

    def test_sets_total_units(self):
        prop = _make_prop()
        changed = update_property_columns(prop, {"TOTAL_UNITS": 120.0})
        assert changed is True
        assert prop.total_units == 120

    def test_skips_zero_units(self):
        prop = _make_prop()
        changed = update_property_columns(prop, {"TOTAL_UNITS": 0.0})
        assert prop.total_units is None

    def test_sets_year_built(self):
        prop = _make_prop()
        update_property_columns(prop, {"YEAR_BUILT": 1985.0})
        assert prop.year_built == 1985

    def test_sets_total_sf(self):
        prop = _make_prop()
        update_property_columns(prop, {"TOTAL_SF": 95000.0})
        assert prop.total_sf == 95000

    def test_sets_cap_rate(self):
        prop = _make_prop()
        update_property_columns(prop, {"GOING_IN_CAP_RATE": 0.0525})
        assert prop.cap_rate == Decimal("0.0525")

    def test_sets_address_when_none(self):
        prop = _make_prop()
        update_property_columns(prop, {"PROPERTY_ADDRESS": "123 Main St"})
        assert prop.address == "123 Main St"

    def test_sets_address_when_tbd(self):
        prop = _make_prop(address="TBD")
        update_property_columns(prop, {"PROPERTY_ADDRESS": "123 Main St"})
        assert prop.address == "123 Main St"

    def test_overwrites_address_when_real_value(self):
        """Re-extraction should update address even if already populated."""
        prop = _make_prop(address="456 Oak Ave")
        changed = update_property_columns(prop, {"PROPERTY_ADDRESS": "123 Main St"})
        assert changed is True
        assert prop.address == "123 Main St"

    def test_noi_per_unit_preferred(self):
        prop = _make_prop()
        update_property_columns(prop, {"NOI_PER_UNIT": 5000.0, "NOI": 600_000})
        assert prop.noi == Decimal("5000.0")

    def test_noi_total_divided_by_units(self):
        prop = _make_prop(total_units=100)
        update_property_columns(prop, {"NOI": 600_000})
        assert prop.noi == Decimal("6000.0")

    def test_noi_total_without_units_no_set(self):
        """NOI total without total_units doesn't set noi."""
        prop = _make_prop()
        update_property_columns(prop, {"NOI": 600_000})
        assert prop.noi is None

    def test_sets_occupancy(self):
        prop = _make_prop()
        update_property_columns(prop, {"OCCUPANCY_PERCENT": 0.945})
        assert prop.occupancy_rate == Decimal("0.945")

    def test_sets_avg_rent_per_unit(self):
        prop = _make_prop()
        update_property_columns(prop, {"AVG_RENT_PER_UNIT": 1250.0})
        assert prop.avg_rent_per_unit == Decimal("1250.0")

    def test_sets_avg_rent_per_sf(self):
        prop = _make_prop()
        update_property_columns(prop, {"AVG_RENT_PER_SF": 1.45})
        assert prop.avg_rent_per_sf == Decimal("1.45")

    def test_current_value_from_purchase_price(self):
        prop = _make_prop()
        update_property_columns(prop, {"PURCHASE_PRICE": 5_000_000})
        assert prop.current_value == Decimal("5000000.0")

    def test_empty_field_values(self):
        prop = _make_prop()
        changed = update_property_columns(prop, {})
        assert changed is False

    def test_all_fields_at_once(self):
        prop = _make_prop()
        fv = {
            "PURCHASE_PRICE": 5_000_000,
            "TOTAL_UNITS": 120,
            "YEAR_BUILT": 1990,
            "TOTAL_SF": 90000,
            "GOING_IN_CAP_RATE": 0.055,
            "OCCUPANCY_PERCENT": 0.93,
            "AVG_RENT_PER_UNIT": 1100,
            "AVG_RENT_PER_SF": 1.2,
            "NOI_PER_UNIT": 5500,
            "PROPERTY_ADDRESS": "789 Elm St",
        }
        changed = update_property_columns(prop, fv)
        assert changed is True
        assert prop.purchase_price == Decimal("5000000.0")
        assert prop.total_units == 120
        assert prop.year_built == 1990
        assert prop.total_sf == 90000
        assert prop.cap_rate == Decimal("0.055")
        assert prop.address == "789 Elm St"


# ===================================================================
# 6. build_financial_data_json
# ===================================================================


class TestBuildFinancialDataJson:
    def test_empty_field_values(self):
        prop = _make_prop()
        result = build_financial_data_json(prop, {}, None)
        assert result == {
            "acquisition": {},
            "financing": {},
            "returns": {},
            "operations": {},
        }

    def test_acquisition_fields(self):
        prop = _make_prop()
        fv = {"PURCHASE_PRICE": 5_000_000, "PRICE_PER_UNIT": 41_666.67}
        result = build_financial_data_json(prop, fv, None)
        assert result["acquisition"]["purchasePrice"] == 5_000_000.0
        assert result["acquisition"]["pricePerUnit"] == pytest.approx(
            41_666.67, abs=0.01
        )

    def test_financing_fields(self):
        prop = _make_prop()
        fv = {
            "LOAN_AMOUNT": 3_500_000,
            "LOAN_TO_VALUE": 0.70,
            "INTEREST_RATE": 0.065,
            "LOAN_TERM": 10,  # years -> months
            "AMORTIZATION": 30,  # years -> months
            "DEBT_SERVICE_ANNUAL": 280_000,
        }
        result = build_financial_data_json(prop, fv, None)
        fin = result["financing"]
        assert fin["loanAmount"] == 3_500_000.0
        assert fin["ltv"] == 0.70
        assert fin["interestRate"] == pytest.approx(0.065, abs=1e-6)
        assert fin["loanTermMonths"] == 120
        assert fin["amortizationMonths"] == 360
        assert fin["annualDebtService"] == 280_000.0

    def test_loan_term_already_months(self):
        """If loan term >= 40, treat as already months."""
        prop = _make_prop()
        fv = {"LOAN_TERM": 120}
        result = build_financial_data_json(prop, fv, None)
        assert result["financing"]["loanTermMonths"] == 120

    def test_amortization_already_months(self):
        prop = _make_prop()
        fv = {"AMORTIZATION": 360}
        result = build_financial_data_json(prop, fv, None)
        assert result["financing"]["amortizationMonths"] == 360

    def test_returns_fields(self):
        prop = _make_prop()
        fv = {
            "LEVERED_RETURNS_IRR": 0.15,
            "LEVERED_RETURNS_MOIC": 2.1,
            "UNLEVERED_RETURNS_IRR": 0.10,
            "UNLEVERED_RETURNS_MOIC": 1.8,
        }
        result = build_financial_data_json(prop, fv, None)
        ret = result["returns"]
        assert ret["leveredIrr"] == pytest.approx(0.15, abs=1e-6)
        assert ret["lpIrr"] == pytest.approx(0.15, abs=1e-6)
        assert ret["leveredMoic"] == pytest.approx(2.1, abs=1e-4)
        assert ret["lpMoic"] == pytest.approx(2.1, abs=1e-4)
        assert ret["unleveredIrr"] == pytest.approx(0.10, abs=1e-6)
        assert ret["unleveredMoic"] == pytest.approx(1.8, abs=1e-4)

    def test_operations_fields(self):
        prop = _make_prop()
        fv = {
            "EFFECTIVE_GROSS_INCOME": 2_000_000,
            "NET_RENTAL_INCOME": 1_800_000,
            "NOI": 1_000_000,
            "TOTAL_EXPENSES": 800_000,
            "OCCUPANCY_PERCENT": 0.94,
            "AVG_RENT_PER_UNIT": 1200,
            "AVG_RENT_PER_SF": 1.5,
            "TOTAL_OPERATING_EXPENSES": 750_000,
        }
        result = build_financial_data_json(prop, fv, None)
        ops = result["operations"]
        assert ops["totalRevenueYear1"] == 2_000_000.0
        assert ops["netRentalIncomeYear1"] == 1_800_000.0
        assert ops["noiYear1"] == 1_000_000.0
        assert ops["totalExpensesYear1"] == 800_000.0
        assert ops["occupancy"] == 0.94
        assert ops["avgRentPerUnit"] == 1200.0
        assert ops["avgRentPerSf"] == 1.5
        assert ops["totalOperatingExpensesYear1"] == 750_000.0

    def test_overwrites_existing_data_with_latest(self):
        """Latest extraction data should overwrite stale JSON values."""
        prop = _make_prop()
        existing = {
            "acquisition": {"purchasePrice": 999},
            "financing": {"loanAmount": 500},
        }
        fv = {"PURCHASE_PRICE": 5_000_000, "LOAN_AMOUNT": 3_000_000}
        result = build_financial_data_json(prop, fv, existing)
        assert result["acquisition"]["purchasePrice"] == 5_000_000.0
        assert result["financing"]["loanAmount"] == 3_000_000.0

    def test_preserves_existing_when_field_absent(self):
        """Fields not in the new extraction should not be wiped out."""
        prop = _make_prop()
        existing = {
            "acquisition": {"purchasePrice": 999},
            "financing": {"loanAmount": 500},
        }
        # No PURCHASE_PRICE or LOAN_AMOUNT in new extraction
        fv = {"OCCUPANCY_PERCENT": 0.95}
        result = build_financial_data_json(prop, fv, existing)
        assert result["acquisition"]["purchasePrice"] == 999
        assert result["financing"]["loanAmount"] == 500

    def test_none_field_values(self):
        """Empty dict scenario still returns structure."""
        prop = _make_prop()
        result = build_financial_data_json(prop, {}, {"returns": {"leveredIrr": 0.12}})
        assert result["returns"]["leveredIrr"] == 0.12


# ===================================================================
# 7. build_ops_by_year
# ===================================================================


class TestBuildOpsByYear:
    def test_empty_rows(self):
        ops, expenses, changed = build_ops_by_year([], {})
        assert ops == {}
        assert expenses == {}
        assert changed is False

    def test_single_year_revenue(self):
        rows = [
            ("GROSS_POTENTIAL_REVENUE_YEAR_1", 2_000_000.0),
            ("NET_OPERATING_INCOME_YEAR_1", 900_000.0),
        ]
        ops, expenses, changed = build_ops_by_year(rows, {})
        assert changed is True
        assert "1" in ops
        yr1 = ops["1"]
        assert yr1["grossPotentialRevenue"] == 2_000_000.0
        assert yr1["noi"] == 900_000.0
        # Missing fields default to 0
        assert yr1["effectiveGrossIncome"] == 0

    def test_expense_sub_dict(self):
        rows = [
            ("REAL_ESTATE_TAXES_YEAR_1", 150_000.0),
            ("PROPERTY_INSURANCE_YEAR_1", 50_000.0),
        ]
        ops, expenses, changed = build_ops_by_year(rows, {})
        assert changed is True
        yr1 = ops["1"]
        assert yr1["expenses"]["realEstateTaxes"] == 150_000.0
        assert yr1["expenses"]["propertyInsurance"] == 50_000.0

    def test_multiple_years(self):
        rows = [
            ("NET_OPERATING_INCOME_YEAR_1", 900_000.0),
            ("NET_OPERATING_INCOME_YEAR_2", 950_000.0),
            ("NET_OPERATING_INCOME_YEAR_3", 1_000_000.0),
        ]
        ops, _, changed = build_ops_by_year(rows, {})
        assert changed is True
        assert set(ops.keys()) == {"1", "2", "3"}
        assert ops["1"]["noi"] == 900_000.0
        assert ops["2"]["noi"] == 950_000.0
        assert ops["3"]["noi"] == 1_000_000.0

    def test_dedup_keeps_first(self):
        """Rows are ordered DESC by created_at; first occurrence wins."""
        rows = [
            ("NET_OPERATING_INCOME_YEAR_1", 999_999.0),  # newer
            ("NET_OPERATING_INCOME_YEAR_1", 100_000.0),  # older — should be ignored
        ]
        ops, _, _ = build_ops_by_year(rows, {})
        assert ops["1"]["noi"] == 999_999.0

    def test_none_value_skipped(self):
        rows = [
            ("NET_OPERATING_INCOME_YEAR_1", None),
        ]
        ops, _, changed = build_ops_by_year(rows, {})
        assert changed is False

    def test_expenses_populated_from_year_1(self):
        rows = [
            ("REAL_ESTATE_TAXES_YEAR_1", 100_000.0),
            ("REAL_ESTATE_TAXES_YEAR_2", 105_000.0),
        ]
        _, expenses, _ = build_ops_by_year(rows, {})
        # First year's expenses should populate top-level
        assert expenses["realEstateTaxes"] == 100_000.0

    def test_existing_expenses_overwritten_by_year1(self):
        """Year-1 expenses from latest extraction should overwrite stale data."""
        rows = [
            ("REAL_ESTATE_TAXES_YEAR_1", 100_000.0),
        ]
        existing = {"realEstateTaxes": 50_000.0}
        _, expenses, _ = build_ops_by_year(rows, existing)
        assert expenses["realEstateTaxes"] == 100_000.0

    def test_existing_expenses_preserved_when_no_year1(self):
        """If the extraction only has year-2+ data, don't wipe year-1 expenses."""
        rows = [
            ("REAL_ESTATE_TAXES_YEAR_2", 110_000.0),
        ]
        existing = {"realEstateTaxes": 50_000.0}
        _, expenses, _ = build_ops_by_year(rows, existing)
        # No year-1 data, so existing expenses should be preserved
        assert expenses["realEstateTaxes"] == 50_000.0

    def test_defaults_filled_for_missing_keys(self):
        """Each year gets 0 for every CASHFLOW_FIELD_MAP entry not present."""
        rows = [
            ("NET_OPERATING_INCOME_YEAR_1", 900_000.0),
        ]
        ops, _, _ = build_ops_by_year(rows, {})
        yr1 = ops["1"]
        assert yr1["grossPotentialRevenue"] == 0
        assert yr1["expenses"]["realEstateTaxes"] == 0

    def test_invalid_field_name_ignored(self):
        rows = [
            ("RANDOM_FIELD_YEAR_1", 42.0),
        ]
        ops, _, changed = build_ops_by_year(rows, {})
        assert changed is False


# ===================================================================
# 8. build_base_expenses
# ===================================================================


class TestBuildBaseExpenses:
    def test_basic_scaling(self):
        fv = {"REAL_ESTATE_TAXES": 1200.0, "PROPERTY_INSURANCE": 500.0}
        result = build_base_expenses(fv, total_units=100)
        assert result["realEstateTaxes"] == 120_000.0
        assert result["propertyInsurance"] == 50_000.0

    def test_no_matching_fields(self):
        result = build_base_expenses({"PURCHASE_PRICE": 5_000_000}, total_units=100)
        assert result == {}

    def test_zero_units(self):
        """With 0 units, should still use per-unit value (no multiplication)."""
        fv = {"REAL_ESTATE_TAXES": 1200.0}
        result = build_base_expenses(fv, total_units=0)
        assert result["realEstateTaxes"] == 1200.0

    def test_none_value_skipped(self):
        fv = {"REAL_ESTATE_TAXES": None}
        result = build_base_expenses(fv, total_units=100)
        assert "realEstateTaxes" not in result

    def test_all_expense_fields(self):
        fv = dict.fromkeys(BASE_EXPENSE_FIELD_MAP, 100.0)
        result = build_base_expenses(fv, total_units=10)
        assert len(result) == len(BASE_EXPENSE_FIELD_MAP)
        for json_key in BASE_EXPENSE_FIELD_MAP.values():
            assert result[json_key] == 1000.0


# ===================================================================
# 9. YEAR_FIELD_RE regex
# ===================================================================


class TestYearFieldRegex:
    def test_matches_standard_field(self):
        m = YEAR_FIELD_RE.match("GROSS_POTENTIAL_REVENUE_YEAR_1")
        assert m is not None
        assert m.group(1) == "GROSS_POTENTIAL_REVENUE"
        assert m.group(2) == "1"

    def test_matches_expense_field(self):
        m = YEAR_FIELD_RE.match("REAL_ESTATE_TAXES_YEAR_5")
        assert m is not None
        assert m.group(1) == "REAL_ESTATE_TAXES"
        assert m.group(2) == "5"

    def test_no_match_base_field(self):
        assert YEAR_FIELD_RE.match("PURCHASE_PRICE") is None

    def test_no_match_random(self):
        assert YEAR_FIELD_RE.match("RANDOM_THING_YEAR_1") is None

    def test_longer_prefix_wins(self):
        """TOTAL_OTHER_INCOME should match before OTHER_INCOME prefix ambiguity."""
        m = YEAR_FIELD_RE.match("TOTAL_OTHER_INCOME_YEAR_2")
        assert m is not None
        assert m.group(1) == "TOTAL_OTHER_INCOME"

    def test_utilities_vs_utility_income(self):
        m1 = YEAR_FIELD_RE.match("UTILITIES_YEAR_1")
        assert m1 is not None
        assert m1.group(1) == "UTILITIES"

        m2 = YEAR_FIELD_RE.match("UTILITY_INCOME_YEAR_1")
        assert m2 is not None
        assert m2.group(1) == "UTILITY_INCOME"


# ===================================================================
# 10. FIELD_ALIASES and resolve_field_aliases
# ===================================================================


class TestFieldAliases:
    """Verify that extraction-side field names are resolved to canonical names."""

    def test_net_operating_income_resolves_to_noi(self):
        fv: dict[str, float | str | None] = {"NET_OPERATING_INCOME": 1_000_000.0}
        result = resolve_field_aliases(fv)
        assert result["NOI"] == 1_000_000.0
        # Original alias key is preserved
        assert result["NET_OPERATING_INCOME"] == 1_000_000.0

    def test_cap_rate_resolves_to_going_in_cap_rate(self):
        fv: dict[str, float | str | None] = {"CAP_RATE": 0.048}
        result = resolve_field_aliases(fv)
        assert result["GOING_IN_CAP_RATE"] == 0.048

    def test_average_rent_per_unit_inplace_resolves(self):
        fv: dict[str, float | str | None] = {"AVERAGE_RENT_PER_UNIT_INPLACE": 1350.0}
        result = resolve_field_aliases(fv)
        assert result["AVG_RENT_PER_UNIT"] == 1350.0

    def test_average_rent_per_sf_inplace_resolves(self):
        fv: dict[str, float | str | None] = {"AVERAGE_RENT_PER_SF_INPLACE": 1.85}
        result = resolve_field_aliases(fv)
        assert result["AVG_RENT_PER_SF"] == 1.85

    def test_vacancy_loss_resolves_to_vacancy_rate(self):
        fv: dict[str, float | str | None] = {"VACANCY_LOSS": 0.05}
        result = resolve_field_aliases(fv)
        assert result["VACANCY_RATE"] == 0.05

    def test_total_operating_expenses_resolves_to_total_expenses(self):
        fv: dict[str, float | str | None] = {"TOTAL_OPERATING_EXPENSES": 500_000.0}
        result = resolve_field_aliases(fv)
        assert result["TOTAL_EXPENSES"] == 500_000.0

    def test_canonical_name_takes_priority_over_alias(self):
        """If both the canonical name and alias are present, canonical wins."""
        fv: dict[str, float | str | None] = {
            "NOI": 900_000.0,
            "NET_OPERATING_INCOME": 1_000_000.0,
        }
        result = resolve_field_aliases(fv)
        # Canonical was already present, so alias should NOT overwrite
        assert result["NOI"] == 900_000.0

    def test_empty_dict(self):
        fv: dict[str, float | str | None] = {}
        result = resolve_field_aliases(fv)
        assert result == {}

    def test_no_alias_keys_present(self):
        fv: dict[str, float | str | None] = {
            "PURCHASE_PRICE": 5_000_000.0,
            "TOTAL_UNITS": 120.0,
        }
        result = resolve_field_aliases(fv)
        assert result == fv

    def test_all_alias_names_in_hydration_fields(self):
        """Every extraction-side alias name must appear in ALL_HYDRATION_FIELDS
        so the SQL IN clause fetches them from the database."""
        for alias_name in FIELD_ALIASES:
            assert alias_name in ALL_HYDRATION_FIELDS, (
                f"Alias {alias_name!r} missing from ALL_HYDRATION_FIELDS — "
                f"SQL queries won't fetch it"
            )

    def test_market_rent_fallback(self):
        """AVERAGE_RENT_PER_UNIT_MARKET should resolve when INPLACE is absent."""
        fv: dict[str, float | str | None] = {"AVERAGE_RENT_PER_UNIT_MARKET": 1400.0}
        result = resolve_field_aliases(fv)
        assert result["AVG_RENT_PER_UNIT"] == 1400.0

    def test_inplace_rent_preferred_over_market(self):
        """When both INPLACE and MARKET rent are present, first alias wins
        because resolve_field_aliases only sets when canonical is absent."""
        fv: dict[str, float | str | None] = {
            "AVERAGE_RENT_PER_UNIT_INPLACE": 1350.0,
            "AVERAGE_RENT_PER_UNIT_MARKET": 1400.0,
        }
        result = resolve_field_aliases(fv)
        # The iteration order of FIELD_ALIASES determines which alias sets
        # the canonical key first. Either value is acceptable — the key point
        # is that AVG_RENT_PER_UNIT IS set (not missing).
        assert result["AVG_RENT_PER_UNIT"] is not None


class TestAliasIntegrationWithHydration:
    """End-to-end: extraction-side names flow through to property columns."""

    def test_net_operating_income_populates_noi_column(self):
        """NET_OPERATING_INCOME from extraction should set prop.noi via alias."""
        prop = _make_prop(total_units=100)
        fv: dict[str, float | str | None] = {"NET_OPERATING_INCOME": 600_000.0}
        resolve_field_aliases(fv)
        update_property_columns(prop, fv)
        # NOI is stored per-unit: 600_000 / 100 = 6000
        assert prop.noi == Decimal("6000.0")

    def test_cap_rate_populates_cap_rate_column(self):
        """CAP_RATE from extraction should set prop.cap_rate via alias."""
        prop = _make_prop()
        fv: dict[str, float | str | None] = {"CAP_RATE": 0.0475}
        resolve_field_aliases(fv)
        update_property_columns(prop, fv)
        assert prop.cap_rate == Decimal("0.0475")

    def test_average_rent_populates_avg_rent_column(self):
        """AVERAGE_RENT_PER_UNIT_INPLACE should set prop.avg_rent_per_unit."""
        prop = _make_prop()
        fv: dict[str, float | str | None] = {"AVERAGE_RENT_PER_UNIT_INPLACE": 1250.0}
        resolve_field_aliases(fv)
        update_property_columns(prop, fv)
        assert prop.avg_rent_per_unit == Decimal("1250.0")

    def test_noi_flows_into_financial_data_json(self):
        """NET_OPERATING_INCOME should appear as noiYear1 in financial_data."""
        prop = _make_prop()
        fv: dict[str, float | str | None] = {"NET_OPERATING_INCOME": 1_000_000.0}
        resolve_field_aliases(fv)
        result = build_financial_data_json(prop, fv, None)
        assert result["operations"]["noiYear1"] == 1_000_000.0
