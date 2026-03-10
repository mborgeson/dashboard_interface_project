"""
Property financial data enrichment service.

Extracts field-mapping constants, JSON-building logic, and unit conversion
out of the CRUD layer. The CRUD methods delegate here for all enrichment
business logic while retaining responsibility for DB persistence.
"""

import re
from decimal import Decimal
from typing import Any

import numpy as np
from loguru import logger
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Property

# ---------------------------------------------------------------------------
# Mapping from extracted_values field name prefixes (YEAR_N stripped) to the
# operationsByYear JSON keys expected by the frontend.
#
# The extraction pipeline stores annual cashflow fields with names like
# ``GROSS_POTENTIAL_REVENUE_YEAR_1``, ``NET_OPERATING_INCOME_YEAR_3``, etc.
# This map converts the prefix (before ``_YEAR_``) to the camelCase key used
# in the ``operationsByYear`` dict.
# ---------------------------------------------------------------------------
CASHFLOW_FIELD_MAP: dict[str, tuple[str, str | None]] = {
    # prefix -> (json_key, sub_dict)
    # sub_dict is None for top-level, "expenses" for expense sub-dict
    "GROSS_POTENTIAL_REVENUE": ("grossPotentialRevenue", None),
    "LOSS_TO_LEASE": ("lossToLease", None),
    "VACANCY_LOSS": ("vacancyLoss", None),
    "BAD_DEBTS": ("badDebts", None),
    "CONCESSIONS": ("concessions", None),
    "OTHER_LOSS": ("otherLoss", None),
    "NET_RENTAL_INCOME": ("netRentalIncome", None),
    "TOTAL_OTHER_INCOME": ("otherIncome", None),
    "LAUNDRY_INCOME": ("laundryIncome", None),
    "PARKING_INCOME": ("parkingIncome", None),
    "PET_INCOME": ("petIncome", None),
    "STORAGE_INCOME": ("storageIncome", None),
    "UTILITY_INCOME": ("utilityIncome", None),
    "OTHER_MISC_INCOME": ("otherMiscIncome", None),
    "EFFECTIVE_GROSS_INCOME": ("effectiveGrossIncome", None),
    "NET_OPERATING_INCOME": ("noi", None),
    "TOTAL_OPERATING_EXPENSES": ("totalOperatingExpenses", None),
    # Expense sub-dict
    "REAL_ESTATE_TAXES": ("realEstateTaxes", "expenses"),
    "PROPERTY_INSURANCE": ("propertyInsurance", "expenses"),
    "STAFFING_PAYROLL": ("staffingPayroll", "expenses"),
    "PROPERTY_MANAGEMENT_FEE": ("propertyManagementFee", "expenses"),
    "REPAIRS_AND_MAINTENANCE": ("repairsAndMaintenance", "expenses"),
    "TURNOVER": ("turnover", "expenses"),
    "CONTRACT_SERVICES": ("contractServices", "expenses"),
    "RESERVES_FOR_REPLACEMENT": ("reservesForReplacement", "expenses"),
    "ADMIN_LEGAL_AND_SECURITY": ("adminLegalSecurity", "expenses"),
    "ADVERTISING_LEASING_AND_MARKETING": ("advertisingLeasingMarketing", "expenses"),
    "UTILITIES": ("utilities", "expenses"),
    "OTHER_EXPENSES": ("otherExpenses", "expenses"),
}

# Regex to match annual cashflow field names: PREFIX_YEAR_N
# Sort by length descending so longer prefixes match first (e.g. UTILITY_INCOME
# before UTILITIES, TOTAL_OTHER_INCOME before OTHER_INCOME).
YEAR_FIELD_RE = re.compile(
    r"^("
    + "|".join(re.escape(k) for k in sorted(CASHFLOW_FIELD_MAP, key=len, reverse=True))
    + r")_YEAR_(\d+)$"
)

# Must match extraction.py _FINANCIAL_DATA_FIELDS + _EXTRACTED_FIELD_MAP keys
ALL_HYDRATION_FIELDS: set[str] = {
    "PURCHASE_PRICE",
    "PRICE_PER_UNIT",
    "TOTAL_UNITS",
    "YEAR_BUILT",
    "TOTAL_SF",
    "GOING_IN_CAP_RATE",
    "T3_RETURN_ON_COST",
    "INTEREST_RATE",
    "LOAN_AMOUNT",
    "LOAN_TO_VALUE",
    "EQUITY",
    "LOAN_TERM",
    "AMORTIZATION",
    "IO_PERIOD",
    "DEBT_SERVICE_ANNUAL",
    "LEVERED_RETURNS_IRR",
    "LEVERED_RETURNS_MOIC",
    "UNLEVERED_RETURNS_IRR",
    "UNLEVERED_RETURNS_MOIC",
    "NOI",
    "NOI_PER_UNIT",
    "EFFECTIVE_GROSS_INCOME",
    "NET_RENTAL_INCOME",
    "TOTAL_REVENUE",
    "TOTAL_EXPENSES",
    "TOTAL_OPERATING_EXPENSES",
    "VACANCY_RATE",
    "AVG_RENT_PER_UNIT",
    "AVG_RENT_PER_SF",
    "OCCUPANCY_PERCENT",
    "PROPERTY_ADDRESS",
    # Per-unit expense fields (base, no YEAR_N suffix) from extraction
    "REAL_ESTATE_TAXES",
    "PROPERTY_INSURANCE",
    "STAFFING_PAYROLL",
    "PROPERTY_MANAGEMENT_FEE",
    "REPAIRS_AND_MAINTENANCE",
    "TURNOVER",
    "CONTRACT_SERVICES",
    "RESERVES_FOR_REPLACEMENT",
    "ADMIN_LEGAL_AND_SECURITY",
    "ADVERTISING_LEASING_AND_MARKETING",
    "UTILITIES",
    "OTHER_EXPENSES",
}

# Mapping from extracted_values base field names to frontend expense JSON keys
BASE_EXPENSE_FIELD_MAP: dict[str, str] = {
    "REAL_ESTATE_TAXES": "realEstateTaxes",
    "PROPERTY_INSURANCE": "propertyInsurance",
    "STAFFING_PAYROLL": "staffingPayroll",
    "PROPERTY_MANAGEMENT_FEE": "propertyManagementFee",
    "REPAIRS_AND_MAINTENANCE": "repairsAndMaintenance",
    "TURNOVER": "turnover",
    "CONTRACT_SERVICES": "contractServices",
    "RESERVES_FOR_REPLACEMENT": "reservesForReplacement",
    "ADMIN_LEGAL_AND_SECURITY": "adminLegalSecurity",
    "ADVERTISING_LEASING_AND_MARKETING": "advertisingLeasingMarketing",
    "UTILITIES": "utilities",
    "OTHER_EXPENSES": "otherExpenses",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def safe_float(val: Any) -> float | None:
    """Safely convert to float, returning None on failure."""
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def to_decimal(val: Any, places: int = 2) -> Decimal | None:
    """Convert to Decimal for SQLAlchemy Numeric columns."""
    f = safe_float(val)
    return Decimal(str(round(f, places))) if f is not None else None


def get_property_name_variants(prop: Property) -> list[str]:
    """Return the list of name variants for matching extracted values."""
    short_name = prop.name.split("(")[0].strip() if prop.name else ""
    variants = [prop.name] if prop.name else []
    if short_name and short_name != prop.name:
        variants.append(short_name)
    return variants


def match_prop_name(prop_name_from_db: str, prop: Property) -> bool:
    """Check if an extracted value row belongs to a given property."""
    short = prop.name.split("(")[0].strip() if prop.name else ""
    return bool(
        prop_name_from_db == prop.name
        or (short and prop_name_from_db == short)
        or (prop.name and prop_name_from_db.startswith(prop.name + " ("))
        or (short and prop_name_from_db.startswith(short + " ("))
    )


# ---------------------------------------------------------------------------
# Core enrichment logic — pure business logic, no DB writes
# ---------------------------------------------------------------------------


def update_property_columns(
    prop: Property,
    field_values: dict[str, float | str | None],
) -> bool:
    """Update a property's direct columns from extracted field values.

    Only updates columns that are currently empty/falsy.
    Mutates ``prop`` in-place, returns True if any column was changed.
    """
    changed = False

    pp = safe_float(field_values.get("PURCHASE_PRICE"))
    if pp is not None and not prop.purchase_price:
        prop.purchase_price = to_decimal(pp, 2)
        changed = True

    units_f = safe_float(field_values.get("TOTAL_UNITS"))
    if units_f is not None and units_f > 0 and not prop.total_units:
        prop.total_units = int(units_f)
        changed = True

    yb = safe_float(field_values.get("YEAR_BUILT"))
    if yb is not None and not prop.year_built:
        prop.year_built = int(yb)
        changed = True

    sf = safe_float(field_values.get("TOTAL_SF"))
    if sf is not None and not prop.total_sf:
        prop.total_sf = int(sf)
        changed = True

    cap = safe_float(field_values.get("GOING_IN_CAP_RATE"))
    if cap is not None and not prop.cap_rate:
        prop.cap_rate = to_decimal(cap, 6)
        changed = True

    addr = field_values.get("PROPERTY_ADDRESS")
    if addr and (not prop.address or prop.address == "TBD"):
        prop.address = str(addr)
        changed = True

    noi_total = safe_float(field_values.get("NOI"))
    noi_per_unit = safe_float(field_values.get("NOI_PER_UNIT"))
    if noi_per_unit and not prop.noi:
        prop.noi = to_decimal(noi_per_unit, 2)
        changed = True
    elif noi_total and prop.total_units and not prop.noi:
        prop.noi = to_decimal(noi_total / prop.total_units, 2)
        changed = True

    occ = safe_float(field_values.get("OCCUPANCY_PERCENT"))
    if occ and not prop.occupancy_rate:
        prop.occupancy_rate = to_decimal(occ, 4)
        changed = True

    avg_rent = safe_float(field_values.get("AVG_RENT_PER_UNIT"))
    if avg_rent and not prop.avg_rent_per_unit:
        prop.avg_rent_per_unit = to_decimal(avg_rent, 2)
        changed = True

    avg_rent_sf = safe_float(field_values.get("AVG_RENT_PER_SF"))
    if avg_rent_sf and not prop.avg_rent_per_sf:
        prop.avg_rent_per_sf = to_decimal(avg_rent_sf, 4)
        changed = True

    if not prop.current_value and prop.purchase_price:
        prop.current_value = prop.purchase_price
        changed = True

    return changed


def build_financial_data_json(
    prop: Property,
    field_values: dict[str, float | str | None],
    existing_fd: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the financial_data JSON structure from extracted field values.

    Returns the assembled dict with acquisition, financing, returns, and
    operations sub-dicts. Does NOT include expenses or operationsByYear —
    those are built separately via ``build_ops_by_year``.
    """
    fd = dict(existing_fd) if existing_fd else {}
    acq = fd.get("acquisition", {})
    fin = fd.get("financing", {})
    ret = fd.get("returns", {})
    ops = fd.get("operations", {})

    if not field_values:
        return {"acquisition": acq, "financing": fin, "returns": ret, "operations": ops}

    pp = safe_float(field_values.get("PURCHASE_PRICE"))
    occ = safe_float(field_values.get("OCCUPANCY_PERCENT"))
    avg_rent = safe_float(field_values.get("AVG_RENT_PER_UNIT"))
    avg_rent_sf = safe_float(field_values.get("AVG_RENT_PER_SF"))

    # Acquisition
    if pp is not None and not acq.get("purchasePrice"):
        acq["purchasePrice"] = round(pp, 2)
    ppu = safe_float(field_values.get("PRICE_PER_UNIT"))
    if ppu is not None and not acq.get("pricePerUnit"):
        acq["pricePerUnit"] = round(ppu, 2)
    eq = safe_float(field_values.get("EQUITY"))
    if eq is not None:
        acq["totalAcquisitionBudget"] = acq.get("totalAcquisitionBudget") or round(
            pp or 0, 2
        )

    # Financing
    la = safe_float(field_values.get("LOAN_AMOUNT"))
    if la is not None and not fin.get("loanAmount"):
        fin["loanAmount"] = round(la, 2)
    ltv = safe_float(field_values.get("LOAN_TO_VALUE"))
    if ltv is not None and not fin.get("ltv"):
        fin["ltv"] = round(ltv, 4)
    ir = safe_float(field_values.get("INTEREST_RATE"))
    if ir is not None and not fin.get("interestRate"):
        fin["interestRate"] = round(ir, 6)
    lt = safe_float(field_values.get("LOAN_TERM"))
    if lt is not None and not fin.get("loanTermMonths"):
        fin["loanTermMonths"] = int(lt * 12) if lt < 40 else int(lt)
    amort = safe_float(field_values.get("AMORTIZATION"))
    if amort is not None and not fin.get("amortizationMonths"):
        fin["amortizationMonths"] = int(amort * 12) if amort < 50 else int(amort)
    ds = safe_float(field_values.get("DEBT_SERVICE_ANNUAL"))
    if ds is not None and not fin.get("annualDebtService"):
        fin["annualDebtService"] = round(ds, 2)

    # Returns
    lirr = safe_float(field_values.get("LEVERED_RETURNS_IRR"))
    if lirr is not None and not ret.get("leveredIrr"):
        ret["leveredIrr"] = round(lirr, 6)
        ret["lpIrr"] = round(lirr, 6)
    lmoic = safe_float(field_values.get("LEVERED_RETURNS_MOIC"))
    if lmoic is not None and not ret.get("leveredMoic"):
        ret["leveredMoic"] = round(lmoic, 4)
        ret["lpMoic"] = round(lmoic, 4)
    uirr = safe_float(field_values.get("UNLEVERED_RETURNS_IRR"))
    if uirr is not None and not ret.get("unleveredIrr"):
        ret["unleveredIrr"] = round(uirr, 6)
    umoic = safe_float(field_values.get("UNLEVERED_RETURNS_MOIC"))
    if umoic is not None and not ret.get("unleveredMoic"):
        ret["unleveredMoic"] = round(umoic, 4)

    # Operations
    egi = safe_float(field_values.get("EFFECTIVE_GROSS_INCOME"))
    if egi is not None and not ops.get("totalRevenueYear1"):
        ops["totalRevenueYear1"] = round(egi, 2)
    nri = safe_float(field_values.get("NET_RENTAL_INCOME"))
    if nri is not None and not ops.get("netRentalIncomeYear1"):
        ops["netRentalIncomeYear1"] = round(nri, 2)
    noi_val = safe_float(field_values.get("NOI"))
    if noi_val is not None and not ops.get("noiYear1"):
        ops["noiYear1"] = round(noi_val, 2)
    tex = safe_float(field_values.get("TOTAL_EXPENSES"))
    if tex is not None and not ops.get("totalExpensesYear1"):
        ops["totalExpensesYear1"] = round(tex, 2)
    if occ is not None and not ops.get("occupancy"):
        ops["occupancy"] = round(occ, 4)
    if avg_rent is not None and not ops.get("avgRentPerUnit"):
        ops["avgRentPerUnit"] = round(avg_rent, 2)
    if avg_rent_sf is not None and not ops.get("avgRentPerSf"):
        ops["avgRentPerSf"] = round(avg_rent_sf, 4)

    # Total operating expenses (annual total, not per-unit)
    toe = safe_float(field_values.get("TOTAL_OPERATING_EXPENSES"))
    if toe is not None and not ops.get("totalOperatingExpensesYear1"):
        ops["totalOperatingExpensesYear1"] = round(toe, 2)

    result: dict[str, Any] = {}
    if acq:
        result["acquisition"] = acq
    if fin:
        result["financing"] = fin
    if ret:
        result["returns"] = ret
    if ops:
        result["operations"] = ops
    return result


def build_ops_by_year(
    year_rows: list[tuple[str, float | None]],
    existing_expenses: dict[str, Any],
    *,
    property_id: Any = None,
    property_name: str | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], bool]:
    """Build ``operationsByYear`` dict from year-field rows.

    Args:
        year_rows: List of (field_name, value_numeric) tuples, ordered by
            created_at DESC so that the first occurrence of each field wins.
        existing_expenses: Current expenses dict to fall back on.
        property_id: For logging only.
        property_name: For logging only.

    Returns:
        (ops_by_year dict, expenses dict, changed bool)
    """
    if not year_rows:
        return {}, existing_expenses, False

    # Group values by year, keeping only the latest per field (ordered DESC)
    seen: set[str] = set()
    year_values: dict[int, dict[str, float]] = {}

    for field_name, value_numeric in year_rows:
        if field_name in seen:
            continue
        seen.add(field_name)

        match = YEAR_FIELD_RE.match(field_name)
        if not match or value_numeric is None:
            continue

        prefix = match.group(1)
        year_num = int(match.group(2))
        mapping = CASHFLOW_FIELD_MAP.get(prefix)
        if not mapping:
            continue

        json_key, sub_dict = mapping
        if year_num not in year_values:
            year_values[year_num] = {}

        # Store with sub-dict prefix so we can separate later
        # Convert Decimal to float for JSON serialization
        storage_key = f"expenses.{json_key}" if sub_dict else json_key
        year_values[year_num][storage_key] = float(value_numeric)

    if not year_values:
        return {}, existing_expenses, False

    # Build operationsByYear structure
    ops_by_year: dict[str, dict[str, Any]] = {}
    expenses = dict(existing_expenses) if existing_expenses else {}

    for year_num in sorted(year_values.keys()):
        vals = year_values[year_num]
        yr_expenses: dict[str, float] = {}
        yr_data: dict[str, Any] = {}

        for storage_key, value in vals.items():
            if storage_key.startswith("expenses."):
                exp_key = storage_key[len("expenses.") :]
                yr_expenses[exp_key] = value
            else:
                yr_data[storage_key] = value

        # Fill defaults for missing keys
        for _prefix, (json_key, sub_dict) in CASHFLOW_FIELD_MAP.items():
            if sub_dict == "expenses":
                yr_expenses.setdefault(json_key, 0)
            else:
                yr_data.setdefault(json_key, 0)

        yr_data["expenses"] = yr_expenses
        ops_by_year[str(year_num)] = yr_data

        # Use the first year for top-level expenses
        if not expenses:
            expenses = dict(yr_expenses)

    logger.info(
        "ops_by_year_built_from_extracted_values",
        property_id=property_id,
        property_name=property_name,
        years=len(ops_by_year),
        total_fields=sum(
            len(v) + len(v.get("expenses", {})) for v in ops_by_year.values()
        ),
    )

    return ops_by_year, expenses, True


def build_base_expenses(
    field_values: dict[str, float | str | None],
    total_units: int,
) -> dict[str, float]:
    """Build expenses dict from base per-unit extracted fields.

    Base fields are per-unit values; this converts them to annual totals.
    """
    expenses: dict[str, float] = {}
    for ev_field, json_key in BASE_EXPENSE_FIELD_MAP.items():
        val = safe_float(field_values.get(ev_field))
        if val is not None:
            annual = round(val * total_units, 2) if total_units else round(val, 2)
            expenses[json_key] = annual
    return expenses


# ---------------------------------------------------------------------------
# DB query helpers — fetch extracted values for enrichment
# ---------------------------------------------------------------------------


async def fetch_base_field_values(
    db: AsyncSession,
    prop: Property,
) -> dict[str, float | str | None]:
    """Query base hydration fields for a single property from extracted_values."""
    from app.models.extraction import ExtractedValue

    field_values: dict[str, float | str | None] = {}
    variants = get_property_name_variants(prop)

    for variant in variants:
        if not variant:
            continue
        rows = (
            await db.execute(
                select(
                    ExtractedValue.field_name,
                    ExtractedValue.value_numeric,
                    ExtractedValue.value_text,
                )
                .where(
                    and_(
                        or_(
                            ExtractedValue.property_name == variant,
                            ExtractedValue.property_name.like(variant + " (%"),
                        ),
                        ExtractedValue.is_error.is_(False),
                        ExtractedValue.field_name.in_(list(ALL_HYDRATION_FIELDS)),
                    )
                )
                .order_by(
                    ExtractedValue.field_name,
                    ExtractedValue.created_at.desc(),
                )
            )
        ).all()

        for fname, vnumeric, vtext in rows:
            if fname not in field_values:
                field_values[fname] = vnumeric if vnumeric is not None else vtext

        if field_values:
            break  # Found data with this variant

    return field_values


async def fetch_year_field_rows(
    db: AsyncSession,
    prop: Property,
) -> list[tuple[str, float | None]]:
    """Query YEAR_N cashflow fields for a single property from extracted_values."""
    from app.models.extraction import ExtractedValue

    variants = get_property_name_variants(prop)

    for variant in variants:
        if not variant:
            continue
        rows = (
            await db.execute(
                select(
                    ExtractedValue.field_name,
                    ExtractedValue.value_numeric,
                )
                .where(
                    and_(
                        or_(
                            ExtractedValue.property_name == variant,
                            ExtractedValue.property_name.like(variant + " (%"),
                        ),
                        ExtractedValue.is_error.is_(False),
                        ExtractedValue.field_name.like("%_YEAR_%"),
                    )
                )
                .order_by(ExtractedValue.created_at.desc())
            )
        ).all()

        if rows:
            return [(r[0], r[1]) for r in rows]

    return []


async def fetch_bulk_base_rows(
    db: AsyncSession,
    name_conditions: list,
) -> list:
    """Bulk-fetch base hydration fields for multiple properties."""
    from app.models.extraction import ExtractedValue

    result = await db.execute(
        select(
            ExtractedValue.property_name,
            ExtractedValue.field_name,
            ExtractedValue.value_numeric,
            ExtractedValue.value_text,
        )
        .where(
            and_(
                or_(*name_conditions),
                ExtractedValue.is_error.is_(False),
                ExtractedValue.field_name.in_(list(ALL_HYDRATION_FIELDS)),
            )
        )
        .order_by(
            ExtractedValue.property_name,
            ExtractedValue.field_name,
            ExtractedValue.created_at.desc(),
        )
    )
    return list(result.all())


async def fetch_bulk_year_rows(
    db: AsyncSession,
    name_conditions: list,
) -> list:
    """Bulk-fetch YEAR_N fields for multiple properties."""
    from app.models.extraction import ExtractedValue

    result = await db.execute(
        select(
            ExtractedValue.property_name,
            ExtractedValue.field_name,
            ExtractedValue.value_numeric,
        )
        .where(
            and_(
                or_(*name_conditions),
                ExtractedValue.is_error.is_(False),
                ExtractedValue.field_name.like("%_YEAR_%"),
            )
        )
        .order_by(
            ExtractedValue.property_name,
            ExtractedValue.created_at.desc(),
        )
    )
    return list(result.all())
