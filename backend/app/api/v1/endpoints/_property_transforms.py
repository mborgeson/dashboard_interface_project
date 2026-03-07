"""
Property data transforms — converts flat DB rows to the nested frontend shape.

Extracted from properties.py to keep route definitions clean.
"""

import re
from decimal import Decimal

from app.models import Property

# ---------------------------------------------------------------------------
# Scalar helpers
# ---------------------------------------------------------------------------


def _decimal_to_float(value: Decimal | None) -> float | None:
    """Convert Decimal to float, returning None if input is None."""
    return float(value) if value is not None else None


def _is_placeholder(val: str | None) -> bool:
    """Check if a string is a bracket placeholder or generic label."""
    if not val:
        return True
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        return True
    val_lower = val.lower()
    _BAD_VALUES = {
        "zip code",
        "00000",
        "unknown",
        "n/a",
        "na",
        "none",
        "tbd",
        "[county]",
        "[market (msa)]",
        "[submarket]",
        "[city]",
        "[state]",
        "[zip]",
        "[address]",
        "city",
        "state",
        "county",
    }
    return val_lower in _BAD_VALUES


# Values that are valid submarkets but should not be used as city names
_SUBMARKET_NOT_CITY = {
    "deer valley",
    "east valley",
    "north phoenix",
    "south west valley",
    "north west valley",
    "downtown phoenix",
    "old town scottsdale",
    "chandler",
    "gilbert",  # these are valid cities AND submarkets -- keep them
}
# Remove actual AZ cities from the set (they ARE valid as both)
_SUBMARKET_NOT_CITY -= {"chandler", "gilbert", "tempe", "mesa", "scottsdale", "peoria"}


def _is_placeholder_city(val: str | None) -> bool:
    """Check if a value is a placeholder OR a submarket being misused as a city."""
    if _is_placeholder(val):
        return True
    val_lower = val.strip().lower() if val else ""
    # Also catch submarkets and other non-city values used as city
    _CITY_BAD_VALUES = {
        "acquisition",
        "disposition",
        "refinance",
        "deer valley",
        "east valley",
        "north phoenix",
        "south west valley",
        "north west valley",
        "downtown phoenix",
        "old town scottsdale",
    }
    return val_lower in _CITY_BAD_VALUES


def _clean_str(val: str | None, default: str = "") -> str:
    """Return val if it's real data, otherwise default."""
    return default if _is_placeholder(val) else (val or default)


# ---------------------------------------------------------------------------
# CoStar Submarket mappings
# ---------------------------------------------------------------------------

# Authoritative CoStar Submarket Cluster mapping by property name
# Source: docs/Dashboard Project - Basic Deal Info.xlsx
_PROPERTY_COSTAR_CLUSTER: dict[str, str] = {
    "505 West": "Tempe",
    "Acacia Pointe": "North West Valley",
    "Alante at the Islands": "Gilbert",
    "Alta Surprise": "North West Valley",
    "Alta Vista Village": "South West Valley",
    "Artisan at Downtown Chandler": "Chandler",
    "Be Mesa": "East Valley",
    "Bingham Blocks": "North West Valley",
    "Broadstone 7th Street": "Downtown Phoenix",
    "Broadstone Portland": "Downtown Phoenix",
    "Buenas Paradise Valley": "North Phoenix",
    "Cantala": "Deer Valley",
    "Casitas at San Marcos": "Chandler",
    "Cimarron": "East Valley",
    "Copper Point Apartments": "East Valley",
    "Cortland Arrowhead Summit": "Deer Valley",
    "Estrella Gateway": "South West Valley",
    "Fringe Mountain View": "North Phoenix",
    "Glen 91": "South West Valley",
    "GLEN 91": "South West Valley",
    "Harmony at Surprise": "North West Valley",
    "Haven Townhomes at P83": "Deer Valley",
    "Hayden Park": "Old Town Scottsdale",
    "Jade Ridge": "Deer Valley",
    "La Paloma": "Tempe",
    "454 West Brown": "East Valley",
    "Park on Bell": "Deer Valley",
    "Emparrado": "East Valley",
    "Tempe Metro": "Tempe",
    "Cabana on 99th": "South West Valley",
    "Town Center Apartments": "East Valley",
}

# Fallback: map extracted submarket names to CoStar clusters
_SUBMARKET_CLUSTER_MAP: dict[str, str] = {
    "West Tempe": "Tempe",
    "Tempe": "Tempe",
    "Apache": "Tempe",
    "Mesa": "East Valley",
    "Central Mesa": "East Valley",
    "Downtown Mesa": "East Valley",
    "Country Club": "East Valley",
    "Scottsdale": "Old Town Scottsdale",
    "South Scottsdale": "Old Town Scottsdale",
    "Deer Valley": "Deer Valley",
    "Arrowhead": "Deer Valley",
    "Roosevelt Row": "Downtown Phoenix",
    "Uptown Phoenix": "Downtown Phoenix",
    "North Phoenix": "North Phoenix",
    "Paradise Valley North": "North Phoenix",
    "South Peoria": "North West Valley",
    "South Surprise": "North West Valley",
    "Westside": "South West Valley",
    "Crystal Gardens": "South West Valley",
    "Downtown Chandler": "Chandler",
    "North Chandler": "Chandler",
    "The Islands": "Gilbert",
    "Gilbert": "Gilbert",
    "Queen Creek": "East Valley",
}

# Fallback: map city to CoStar cluster
_CITY_CLUSTER_MAP: dict[str, str] = {
    "Tempe": "Tempe",
    "Mesa": "East Valley",
    "Chandler": "Chandler",
    "Gilbert": "Gilbert",
    "Scottsdale": "Old Town Scottsdale",
    "Phoenix": "North Phoenix",
    "Glendale": "North West Valley",
    "Peoria": "Deer Valley",
    "Surprise": "North West Valley",
    "Avondale": "South West Valley",
    "Queen Creek": "East Valley",
    "Goodyear": "South West Valley",
    "Buckeye": "South West Valley",
    "Paradise Valley": "North Phoenix",
}


def _get_costar_submarket(
    prop_name: str | None, submarket: str | None, city: str | None
) -> str:
    """
    Resolve CoStar Submarket Cluster for a property.
    Priority: exact property name match > extracted submarket > city > default.
    """
    if prop_name:
        # Try matching by the short name (before the city parenthetical)
        short_name = prop_name.split("(")[0].strip()
        cluster = _PROPERTY_COSTAR_CLUSTER.get(short_name)
        if cluster:
            return cluster
        # Also try full name
        cluster = _PROPERTY_COSTAR_CLUSTER.get(prop_name)
        if cluster:
            return cluster

    if submarket and not _is_placeholder(submarket):
        cluster = _SUBMARKET_CLUSTER_MAP.get(submarket)
        if cluster:
            return cluster

    if city:
        cluster = _CITY_CLUSTER_MAP.get(city)
        if cluster:
            return cluster

    return "North Phoenix"


# ---------------------------------------------------------------------------
# Operations helpers
# ---------------------------------------------------------------------------


def _build_operations_by_year(fd: dict) -> list[dict]:
    """Build multi-year operations array from operationsByYear in financial_data."""
    ops_by_year = fd.get("operationsByYear", {})
    if not ops_by_year:
        return []

    years = []
    for yr_str in sorted(ops_by_year.keys(), key=int):
        yr_data = ops_by_year[yr_str]
        yr_exp = yr_data.get("expenses", {})
        years.append(
            {
                "year": int(yr_str),
                "grossPotentialRevenue": yr_data.get("grossPotentialRevenue") or 0,
                "lossToLease": abs(yr_data.get("lossToLease") or 0),
                "vacancyLoss": abs(yr_data.get("vacancyLoss") or 0),
                "badDebts": abs(yr_data.get("badDebts") or 0),
                "concessions": abs(yr_data.get("concessions") or 0),
                "otherLoss": abs(yr_data.get("otherLoss") or 0),
                "netRentalIncome": yr_data.get("netRentalIncome") or 0,
                "otherIncome": yr_data.get("otherIncome") or 0,
                "laundryIncome": yr_data.get("laundryIncome") or 0,
                "parkingIncome": yr_data.get("parkingIncome") or 0,
                "petIncome": yr_data.get("petIncome") or 0,
                "storageIncome": yr_data.get("storageIncome") or 0,
                "utilityIncome": yr_data.get("utilityIncome") or 0,
                "otherMiscIncome": yr_data.get("otherMiscIncome") or 0,
                "effectiveGrossIncome": yr_data.get("effectiveGrossIncome") or 0,
                "noi": yr_data.get("noi") or 0,
                "totalOperatingExpenses": abs(
                    yr_data.get("totalOperatingExpenses") or 0
                ),
                "expenses": {
                    "realEstateTaxes": abs(yr_exp.get("realEstateTaxes") or 0),
                    "propertyInsurance": abs(yr_exp.get("propertyInsurance") or 0),
                    "staffingPayroll": abs(yr_exp.get("staffingPayroll") or 0),
                    "propertyManagementFee": abs(
                        yr_exp.get("propertyManagementFee") or 0
                    ),
                    "repairsAndMaintenance": abs(
                        yr_exp.get("repairsAndMaintenance") or 0
                    ),
                    "turnover": abs(yr_exp.get("turnover") or 0),
                    "contractServices": abs(yr_exp.get("contractServices") or 0),
                    "reservesForReplacement": abs(
                        yr_exp.get("reservesForReplacement") or 0
                    ),
                    "adminLegalSecurity": abs(yr_exp.get("adminLegalSecurity") or 0),
                    "advertisingLeasingMarketing": abs(
                        yr_exp.get("advertisingLeasingMarketing") or 0
                    ),
                    "otherExpenses": abs(yr_exp.get("otherExpenses") or 0),
                    "utilities": abs(yr_exp.get("utilities") or 0),
                },
            }
        )
    return years


# ---------------------------------------------------------------------------
# Sub-computations extracted from _to_frontend_property
# ---------------------------------------------------------------------------


def _compute_unit_economics(
    prop: Property, fd: dict
) -> tuple[
    float, int, int, int, float, float, float, float, float, float, float, float
]:
    """Return (purchase_price, total_units, total_sf, avg_unit_size,
    loan_amount, total_invested, annual_noi, cap_rate, occupancy, avg_rent,
    rent_per_sf, interest_rate)."""
    acq = fd.get("acquisition", {})
    fin = fd.get("financing", {})
    ops = fd.get("operations", {})

    purchase_price = (
        _decimal_to_float(prop.purchase_price) or acq.get("purchasePrice") or 0
    )
    total_units = prop.total_units or 0
    total_sf = prop.total_sf or 0
    avg_unit_size = round(total_sf / total_units) if total_sf and total_units else 0
    loan_amount = fin.get("loanAmount") or 0
    total_invested = acq.get("totalAcquisitionBudget") or purchase_price

    # NOI: prop.noi is per-unit, ops.totalOperatingExpenses is per-unit,
    # ops.noiYear1 is unreliable (often negative extraction artifact).
    noi_per_unit = _decimal_to_float(prop.noi) or 0
    if noi_per_unit and total_units:
        annual_noi = noi_per_unit * total_units
    else:
        # Try computing from total revenue minus per-unit expenses * units
        total_revenue = ops.get("totalRevenueYear1") or 0
        per_unit_opex = ops.get("totalOperatingExpenses") or 0
        if total_revenue and per_unit_opex and total_units:
            annual_noi = total_revenue - (per_unit_opex * total_units)
        else:
            # Last resort: noiYear1 — but only if positive (negative values
            # are extraction artifacts, not real NOI)
            noi_y1 = ops.get("noiYear1") or 0
            annual_noi = noi_y1 if noi_y1 > 0 else 0

    # Cap rate = annual NOI / purchase price
    cap_rate = _decimal_to_float(prop.cap_rate) or 0
    if not cap_rate and annual_noi and purchase_price:
        cap_rate = round(annual_noi / purchase_price, 4)

    raw_occupancy = _decimal_to_float(prop.occupancy_rate) or ops.get("occupancy") or 0
    occupancy = raw_occupancy / 100 if raw_occupancy > 1 else raw_occupancy
    avg_rent = (
        _decimal_to_float(prop.avg_rent_per_unit) or ops.get("avgRentPerUnit") or 0
    )
    rent_per_sf = (
        _decimal_to_float(prop.avg_rent_per_sf) or ops.get("avgRentPerSf") or 0
    )
    interest_rate = fin.get("interestRate") or 0

    return (
        purchase_price,
        total_units,
        total_sf,
        avg_unit_size,
        loan_amount,
        total_invested,
        annual_noi,
        cap_rate,
        occupancy,
        avg_rent,
        rent_per_sf,
        interest_rate,
    )


def _derive_property_class(year_built: int) -> str:
    """Derive A/B/C class from year_built."""
    if year_built >= 2015:
        return "A"
    if year_built >= 1990:
        return "B"
    return "C"


def _resolve_address(
    prop: Property,
) -> tuple[str, str, str, str, str]:
    """Return (clean_address, clean_city, clean_state, clean_zip, submarket)."""
    # Parse city from deal name as fallback (format: "Name (City, ST)")
    name_city = ""
    name_state = ""
    if prop.name and "(" in prop.name:
        m = re.search(r"\(([^,]+),\s*([A-Z]{2})\)", prop.name)
        if m:
            name_city = m.group(1).strip()
            name_state = m.group(2).strip()

    # Use _is_placeholder_city for city (catches submarkets misused as cities)
    # Also filter the fallback itself — name may contain "(Unknown, AZ)"
    city_fallback = (
        name_city if (name_city and not _is_placeholder_city(name_city)) else "Phoenix"
    )
    clean_city = (
        city_fallback
        if _is_placeholder_city(prop.city)
        else (prop.city or city_fallback)
    )
    clean_state = _clean_str(prop.state, name_state or "AZ")
    clean_zip = _clean_str(prop.zip_code, "")
    clean_address = _clean_str(
        prop.address, prop.name.split("(")[0].strip() if prop.name else ""
    )
    # Use cleaned city for submarket resolution (not raw prop.city which may be "Unknown")
    submarket = _get_costar_submarket(prop.name, prop.submarket, clean_city)
    return clean_address, clean_city, clean_state, clean_zip, submarket


def _compute_monthly_operations(
    avg_rent: float, total_units: int, exp: dict
) -> tuple[int, float]:
    """Return (monthly_revenue, total_expenses)."""
    monthly_revenue = round(avg_rent * total_units) if avg_rent and total_units else 0

    # Check both legacy short keys and full operationsByYear keys
    _expense_keys = [
        ("realEstateTaxes",),
        ("otherExpenses",),
        ("propertyInsurance", "insurance"),
        ("staffingPayroll", "payroll"),
        ("propertyManagementFee", "management"),
        ("repairsAndMaintenance", "repairs"),
        ("turnover",),
        ("contractServices",),
        ("reservesForReplacement", "reserves"),
        ("adminLegalSecurity",),
        ("advertisingLeasingMarketing", "marketing"),
        ("utilities",),
    ]
    total_expenses = 0.0
    for key_variants in _expense_keys:
        for key in key_variants:
            val = exp.get(key)
            if val:
                total_expenses += abs(val)
                break  # Use the first matching variant

    return monthly_revenue, total_expenses


def _compute_returns(
    fd: dict, purchase_price: float, loan_amount: float, total_units: int
) -> dict:
    """Compute IRR, MOIC, equity, and basis metrics; return a flat dict."""
    ret = fd.get("returns", {})
    acq = fd.get("acquisition", {})
    exit_data = fd.get("exit", {})

    hold_period_years = exit_data.get("holdPeriodYears") or (
        round((exit_data.get("exitPeriodMonths") or 60) / 12, 1)
    )
    exit_cap_rate = exit_data.get("exitCapRate") or 0

    levered_irr = ret.get("leveredIrr") or ret.get("lpIrr") or 0
    levered_moic = ret.get("leveredMoic") or ret.get("lpMoic") or 0
    unlevered_irr = ret.get("unleveredIrr")
    unlevered_moic = ret.get("unleveredMoic")

    total_equity_commitment = (
        ret.get("totalEquityCommitment")
        or (acq.get("totalAcquisitionBudget") or purchase_price) - loan_amount
        if loan_amount
        else (acq.get("totalAcquisitionBudget") or purchase_price)
    )
    total_cash_flows_to_equity = (
        ret.get("totalCashFlowsToEquity") or ret.get("lpCashflowInflow") or 0
    )
    net_cash_flows_to_equity = (
        (total_cash_flows_to_equity - total_equity_commitment)
        if total_cash_flows_to_equity is not None
        else 0
    )

    total_basis_per_unit_close = (
        exit_data.get("basisPerUnitAtClose")
        or ret.get("totalBasisPerUnitClose")
        or (round(purchase_price / total_units, 2) if total_units else 0)
    )
    senior_loan_basis_per_unit_close = (
        exit_data.get("seniorDebtBasisPerUnitAtClose")
        or ret.get("seniorLoanBasisPerUnitClose")
        or (round(loan_amount / total_units, 2) if total_units and loan_amount else 0)
    )
    total_basis_per_unit_exit = exit_data.get("basisPerUnitAtExit") or ret.get(
        "totalBasisPerUnitExit"
    )
    senior_loan_basis_per_unit_exit = exit_data.get(
        "seniorDebtBasisPerUnitAtExit"
    ) or ret.get("seniorLoanBasisPerUnitExit")

    return {
        "leveredIrr": levered_irr,
        "leveredMoic": levered_moic,
        "unleveredIrr": unlevered_irr,
        "unleveredMoic": unlevered_moic,
        "totalEquityCommitment": total_equity_commitment,
        "totalCashFlowsToEquity": total_cash_flows_to_equity,
        "netCashFlowsToEquity": net_cash_flows_to_equity,
        "holdPeriodYears": hold_period_years,
        "exitCapRate": exit_cap_rate,
        "totalBasisPerUnitClose": total_basis_per_unit_close,
        "seniorLoanBasisPerUnitClose": senior_loan_basis_per_unit_close,
        "totalBasisPerUnitExit": total_basis_per_unit_exit,
        "seniorLoanBasisPerUnitExit": senior_loan_basis_per_unit_exit,
    }


def _compute_acquisition_financing(
    prop: Property,
    fd: dict,
    purchase_price: float,
    loan_amount: float,
    interest_rate: float,
) -> tuple[dict, dict]:
    """Return (acquisition_dict, financing_dict)."""
    acq = fd.get("acquisition", {})
    fin = fd.get("financing", {})

    acq_date = "2024-01-15"
    if prop.acquisition_date:
        acq_date = prop.acquisition_date.isoformat()

    closing_costs = acq.get("closingCosts") or round(purchase_price * 0.02, 2)
    acquisition_fee = acq.get("acquisitionFee") or 0
    if isinstance(acquisition_fee, int | float) and acquisition_fee < 1:
        acquisition_fee = round(purchase_price * acquisition_fee, 2)

    total_invested = acq.get("totalAcquisitionBudget") or purchase_price

    ltv = fin.get("ltv") or (
        round(loan_amount / purchase_price, 3) if purchase_price and loan_amount else 0
    )
    loan_term = fin.get("loanTermMonths")
    loan_term_years = round(loan_term / 12) if loan_term else 5

    amort = fin.get("amortizationMonths") or 360
    if loan_amount and interest_rate:
        monthly_rate = interest_rate / 12
        if monthly_rate > 0 and amort > 0:
            monthly_payment = round(
                loan_amount
                * monthly_rate
                * (1 + monthly_rate) ** amort
                / ((1 + monthly_rate) ** amort - 1),
                2,
            )
        else:
            monthly_payment = 0
    else:
        monthly_payment = 0

    acquisition_dict = {
        "date": acq_date,
        "purchasePrice": purchase_price,
        "pricePerUnit": round(purchase_price / (prop.total_units or 1), 2)
        if prop.total_units
        else 0,
        "closingCosts": closing_costs,
        "acquisitionFee": acquisition_fee,
        "totalInvested": total_invested,
        "landAndAcquisitionCosts": acq.get("landAndAcquisitionCosts") or 0,
        "hardCosts": acq.get("hardCosts") or 0,
        "softCosts": acq.get("softCosts") or 0,
        "lenderClosingCosts": acq.get("lenderClosingCosts") or 0,
        "equityClosingCosts": acq.get("equityClosingCosts") or 0,
        "totalAcquisitionBudget": acq.get("totalAcquisitionBudget") or total_invested,
    }

    financing_dict = {
        "loanAmount": loan_amount,
        "loanToValue": ltv,
        "interestRate": interest_rate,
        "loanTerm": loan_term_years,
        "amortization": amort // 12 if amort else 30,
        "monthlyPayment": monthly_payment,
        "lender": fin.get("lender") or fin.get("lenderName") or None,
        "originationDate": acq_date,
        "maturityDate": fin.get("maturityDate") or fin.get("loanMaturityDate") or None,
    }

    return acquisition_dict, financing_dict


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def to_frontend_property(prop: Property) -> dict:
    """
    Transform a flat Property DB model into the nested structure
    the frontend Property TypeScript interface expects.
    """
    fd = prop.financial_data or {}
    ops = fd.get("operations", {})
    # Expense data may be stored at fd.expenses (legacy) or within operationsByYear
    # Build a merged expense dict: prefer operationsByYear[1].expenses, then fd.expenses
    _ops_by_year = fd.get("operationsByYear", {})
    _yr1_expenses = {}
    if _ops_by_year:
        _yr1_key = sorted(_ops_by_year.keys(), key=int)[0] if _ops_by_year else None
        if _yr1_key:
            _yr1_expenses = _ops_by_year[_yr1_key].get("expenses", {})
    exp = _yr1_expenses or fd.get("expenses", {})

    (
        purchase_price,
        total_units,
        total_sf,
        avg_unit_size,
        loan_amount,
        total_invested,
        annual_noi,
        cap_rate,
        occupancy,
        avg_rent,
        rent_per_sf,
        interest_rate,
    ) = _compute_unit_economics(prop, fd)

    year_built = prop.year_built or 0
    property_class = _derive_property_class(year_built)

    clean_address, clean_city, clean_state, clean_zip, submarket = _resolve_address(
        prop
    )

    clean_building_type = _clean_str(prop.building_type, "Garden")

    monthly_revenue, total_expenses = _compute_monthly_operations(
        avg_rent,
        total_units,
        exp,
    )

    # Fall back to ops expense totals if expense breakdown is unavailable
    if not total_expenses:
        total_expenses = abs(ops.get("totalExpensesYear1") or 0)
    if not total_expenses:
        # totalOperatingExpenses from group pipeline is per-unit
        per_unit_exp = ops.get("totalOperatingExpenses") or 0
        if per_unit_exp and total_units:
            total_expenses = abs(per_unit_exp * total_units)

    performance = _compute_returns(fd, purchase_price, loan_amount, total_units)

    acquisition_dict, financing_dict = _compute_acquisition_financing(
        prop,
        fd,
        purchase_price,
        loan_amount,
        interest_rate,
    )

    acq_date = acquisition_dict["date"]

    return {
        "id": str(prop.id),
        "name": prop.name,
        "address": {
            "street": clean_address,
            "city": clean_city,
            "state": clean_state,
            "zip": clean_zip,
            "latitude": float(prop.latitude) if prop.latitude else None,
            "longitude": float(prop.longitude) if prop.longitude else None,
            "submarket": submarket,
        },
        "propertyDetails": {
            "units": total_units,
            "squareFeet": total_sf,
            "averageUnitSize": avg_unit_size,
            "yearBuilt": year_built,
            "propertyClass": property_class,
            "assetType": clean_building_type,
            "amenities": list(prop.amenities.keys())
            if prop.amenities and isinstance(prop.amenities, dict)
            else (prop.amenities if isinstance(prop.amenities, list) else []),
        },
        "acquisition": acquisition_dict,
        "financing": financing_dict,
        "valuation": {
            "currentValue": _decimal_to_float(prop.current_value) or purchase_price,
            "lastAppraisalDate": acq_date,
            "capRate": cap_rate,
            "appreciationSinceAcquisition": 0,
        },
        "operations": {
            "occupancy": occupancy,
            "averageRent": avg_rent,
            "rentPerSqft": rent_per_sf,
            "monthlyRevenue": monthly_revenue,
            "otherIncome": ops.get("otherIncomeYear1") or 0,
            "expenses": {
                "realEstateTaxes": abs(exp.get("realEstateTaxes") or 0),
                "otherExpenses": abs(exp.get("otherExpenses") or 0),
                "propertyInsurance": abs(
                    exp.get("propertyInsurance") or exp.get("insurance") or 0
                ),
                "staffingPayroll": abs(
                    exp.get("staffingPayroll") or exp.get("payroll") or 0
                ),
                "propertyManagementFee": abs(
                    exp.get("propertyManagementFee") or exp.get("management") or 0
                ),
                "repairsAndMaintenance": abs(
                    exp.get("repairsAndMaintenance") or exp.get("repairs") or 0
                ),
                "turnover": abs(exp.get("turnover") or 0),
                "contractServices": abs(exp.get("contractServices") or 0),
                "reservesForReplacement": abs(
                    exp.get("reservesForReplacement") or exp.get("reserves") or 0
                ),
                "adminLegalSecurity": abs(exp.get("adminLegalSecurity") or 0),
                "advertisingLeasingMarketing": abs(
                    exp.get("advertisingLeasingMarketing") or exp.get("marketing") or 0
                ),
                "total": total_expenses,
            },
            "noi": annual_noi,
            "operatingExpenseRatio": round(total_expenses / (monthly_revenue * 12), 2)
            if monthly_revenue
            else 0,
            "grossPotentialRevenue": ops.get("totalRevenueYear1") or 0,
            "netRentalIncome": ops.get("netRentalIncomeYear1") or 0,
            "otherIncomeAnnual": ops.get("otherIncomeYear1") or 0,
            "vacancyLoss": abs(ops.get("vacancyLossYear1") or 0),
            "concessions": abs(ops.get("concessionsYear1") or 0),
        },
        "operationsByYear": _build_operations_by_year(fd),
        "performance": performance,
        "images": {
            "main": "",
            "gallery": [],
        },
        "lastAnalyzed": prop.updated_at.isoformat() if prop.updated_at else None,
    }
