"""
Property endpoints for CRUD operations, analytics, and dashboard views.
"""

import re
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user
from app.crud import property as property_crud
from app.crud.crud_activity import property_activity
from app.db.session import get_db
from app.models import Property
from app.models.activity import ActivityType as ActivityTypeModel
from app.schemas.activity import (
    ActivityType,
    PropertyActivityCreate,
    PropertyActivityListResponse,
    PropertyActivityResponse,
)
from app.schemas.property import (
    PropertyCreate,
    PropertyListResponse,
    PropertyResponse,
    PropertyUpdate,
)

router = APIRouter()


def _decimal_to_float(value: Decimal | None) -> float | None:
    """Convert Decimal to float, returning None if input is None."""
    return float(value) if value is not None else None


def _is_placeholder(val: str | None) -> bool:
    """Check if a string is a bracket placeholder like [Year Built] or 'Zip Code'."""
    if not val:
        return True
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        return True
    return val in ("Zip Code", "00000", "[County]", "[Market (MSA)]", "[Submarket]")


def _clean_str(val: str | None, default: str = "") -> str:
    """Return val if it's real data, otherwise default."""
    return default if _is_placeholder(val) else (val or default)


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


def _to_frontend_property(prop: Property) -> dict:
    """
    Transform a flat Property DB model into the nested structure
    the frontend Property TypeScript interface expects.
    """
    fd = prop.financial_data or {}
    acq = fd.get("acquisition", {})
    fin = fd.get("financing", {})
    ret = fd.get("returns", {})
    ops = fd.get("operations", {})
    exp = fd.get("expenses", {})

    purchase_price = (
        _decimal_to_float(prop.purchase_price) or acq.get("purchasePrice") or 0
    )
    total_units = prop.total_units or 0
    total_sf = prop.total_sf or 0
    avg_unit_size = round(total_sf / total_units) if total_sf and total_units else 0
    loan_amount = fin.get("loanAmount") or 0
    total_invested = acq.get("totalAcquisitionBudget") or purchase_price

    # NOI in DB is annual per-unit — multiply by units for total annual NOI
    noi_per_unit = _decimal_to_float(prop.noi) or ops.get("noiYear1") or 0
    annual_noi = noi_per_unit * total_units if noi_per_unit and total_units else 0

    # Cap rate = annual NOI / purchase price
    cap_rate = _decimal_to_float(prop.cap_rate) or 0
    if not cap_rate and annual_noi and purchase_price:
        cap_rate = round(annual_noi / purchase_price, 4)

    raw_occupancy = _decimal_to_float(prop.occupancy_rate) or ops.get("occupancy") or 0
    # Normalize to 0-1 scale (DB stores as whole percent e.g. 93.0)
    occupancy = raw_occupancy / 100 if raw_occupancy > 1 else raw_occupancy
    avg_rent = (
        _decimal_to_float(prop.avg_rent_per_unit) or ops.get("avgRentPerUnit") or 0
    )
    rent_per_sf = (
        _decimal_to_float(prop.avg_rent_per_sf) or ops.get("avgRentPerSf") or 0
    )
    interest_rate = fin.get("interestRate") or 0

    # Derive property class from year_built
    year_built = prop.year_built or 0
    if year_built >= 2015:
        property_class = "A"
    elif year_built >= 1990:
        property_class = "B"
    else:
        property_class = "C"

    # Parse city from deal name as fallback (format: "Name (City, ST)")
    name_city = ""
    name_state = ""
    if prop.name and "(" in prop.name:
        m = re.search(r"\(([^,]+),\s*([A-Z]{2})\)", prop.name)
        if m:
            name_city = m.group(1).strip()
            name_state = m.group(2).strip()

    # Clean placeholder values — use deal name parsing as fallback
    clean_city = _clean_str(prop.city, name_city or "Phoenix")
    clean_state = _clean_str(prop.state, name_state or "AZ")
    clean_zip = _clean_str(prop.zip_code, "")
    clean_address = _clean_str(
        prop.address, prop.name.split("(")[0].strip() if prop.name else ""
    )
    clean_building_type = _clean_str(prop.building_type, "Garden")

    # Map to CoStar Submarket Cluster using authoritative property-level mapping
    # Source: CoStar submarket data (docs/Dashboard Project - Basic Deal Info.xlsx)
    _property_submarket = _get_costar_submarket(prop.name, prop.submarket, prop.city)
    frontend_submarket = _property_submarket

    # Calculate monthly values
    monthly_revenue = round(avg_rent * total_units) if avg_rent and total_units else 0

    # Sum ALL 11 expense line items for total
    _expense_keys = [
        "realEstateTaxes",
        "otherExpenses",
        "insurance",
        "payroll",
        "management",
        "repairs",
        "turnover",
        "contractServices",
        "reserves",
        "adminLegalSecurity",
        "marketing",
    ]
    total_expenses = 0
    for key in _expense_keys:
        val = exp.get(key)
        if val:
            total_expenses += abs(val)

    # Exit / investment metrics from financial_data
    exit_data = fd.get("exit", {})
    hold_period_years = exit_data.get("holdPeriodYears") or (
        round((exit_data.get("exitPeriodMonths") or 60) / 12, 1)
    )
    exit_cap_rate = exit_data.get("exitCapRate") or 0

    # Levered / unlevered returns (from extraction if available, LP returns as proxy)
    levered_irr = ret.get("leveredIrr") or ret.get("lpIrr") or 0
    levered_moic = ret.get("leveredMoic") or ret.get("lpMoic") or 0
    # unlevered values may be None in extraction — keep as None for frontend to show "--"
    unlevered_irr = ret.get("unleveredIrr")  # None if not extracted
    unlevered_moic = ret.get("unleveredMoic")  # None if not extracted

    # Return breakdown values
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

    # Basis per unit metrics (from exit section or derived)
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
    )  # None if not available
    senior_loan_basis_per_unit_exit = exit_data.get(
        "seniorDebtBasisPerUnitAtExit"
    ) or ret.get("seniorLoanBasisPerUnitExit")  # None if not available

    # Acquisition date from deal initial contact or default
    acq_date = "2024-01-15"
    if prop.acquisition_date:
        acq_date = prop.acquisition_date.isoformat()

    closing_costs = acq.get("closingCosts") or round(purchase_price * 0.02, 2)
    acquisition_fee = acq.get("acquisitionFee") or 0
    # If acquisitionFee is a rate (< 1), convert to dollar amount
    if isinstance(acquisition_fee, (int, float)) and acquisition_fee < 1:
        acquisition_fee = round(purchase_price * acquisition_fee, 2)

    ltv = fin.get("ltv") or (
        round(loan_amount / purchase_price, 3) if purchase_price and loan_amount else 0
    )
    loan_term = fin.get("loanTermMonths")
    loan_term_years = round(loan_term / 12) if loan_term else 5

    amort = fin.get("amortizationMonths") or 360
    # Approximate monthly payment
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
            "submarket": frontend_submarket,
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
        "acquisition": {
            "date": acq_date,
            "purchasePrice": purchase_price,
            "pricePerUnit": round(purchase_price / total_units, 2)
            if total_units
            else 0,
            "closingCosts": closing_costs,
            "acquisitionFee": acquisition_fee,
            "totalInvested": total_invested,
            "landAndAcquisitionCosts": acq.get("landAndAcquisitionCosts") or 0,
            "hardCosts": acq.get("hardCosts") or 0,
            "softCosts": acq.get("softCosts") or 0,
            "lenderClosingCosts": acq.get("lenderClosingCosts") or 0,
            "equityClosingCosts": acq.get("equityClosingCosts") or 0,
            "totalAcquisitionBudget": acq.get("totalAcquisitionBudget")
            or total_invested,
        },
        "financing": {
            "loanAmount": loan_amount,
            "loanToValue": ltv,
            "interestRate": interest_rate,
            "loanTerm": loan_term_years,
            "amortization": amort // 12 if amort else 30,
            "monthlyPayment": monthly_payment,
            "lender": fin.get("lender") or fin.get("lenderName") or None,
            "originationDate": acq_date,
            "maturityDate": fin.get("maturityDate")
            or fin.get("loanMaturityDate")
            or None,
        },
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
                "propertyInsurance": abs(exp.get("insurance") or 0),
                "staffingPayroll": abs(exp.get("payroll") or 0),
                "propertyManagementFee": abs(exp.get("management") or 0),
                "repairsAndMaintenance": abs(exp.get("repairs") or 0),
                "turnover": abs(exp.get("turnover") or 0),
                "contractServices": abs(exp.get("contractServices") or 0),
                "reservesForReplacement": abs(exp.get("reserves") or 0),
                "adminLegalSecurity": abs(exp.get("adminLegalSecurity") or 0),
                "advertisingLeasingMarketing": abs(exp.get("marketing") or 0),
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
        "performance": {
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
        },
        "images": {
            "main": "",
            "gallery": [],
        },
    }


@router.get("/dashboard")
async def list_properties_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """
    List all properties in the nested frontend format.
    Returns { properties: [...], total: N } matching the frontend Property type.
    """
    items = await property_crud.get_multi_filtered(
        db,
        skip=0,
        limit=200,
        order_by="name",
        order_desc=False,
    )
    total = await property_crud.count_filtered(db)
    properties = [_to_frontend_property(p) for p in items]
    return {"properties": properties, "total": total}


@router.get("/dashboard/{property_id}")
async def get_property_dashboard(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single property in the nested frontend format.
    """
    prop = await property_crud.get(db, property_id)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )
    return _to_frontend_property(prop)


@router.get("/summary")
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio-level summary statistics.
    Returns PropertySummaryStats matching the frontend type.
    """
    items = await property_crud.get_multi_filtered(
        db,
        skip=0,
        limit=200,
        order_by="name",
        order_desc=False,
    )

    if not items:
        return {
            "totalProperties": 0,
            "totalUnits": 0,
            "totalValue": 0,
            "totalInvested": 0,
            "totalNOI": 0,
            "averageOccupancy": 0,
            "averageCapRate": 0,
            "portfolioCashOnCash": 0,
            "portfolioIRR": 0,
        }

    total_properties = len(items)
    total_units = sum(p.total_units or 0 for p in items)
    total_value = sum(float(p.current_value or 0) for p in items)

    # Use financial_data for invested amounts and returns
    total_invested = 0
    total_noi = 0
    occ_sum = 0
    cap_sum = 0
    occ_count = 0
    cap_count = 0
    irr_weighted = 0
    coc_weighted = 0
    equity_sum = 0

    for p in items:
        fd = p.financial_data or {}
        acq = fd.get("acquisition", {})
        ret = fd.get("returns", {})

        invested = acq.get("totalAcquisitionBudget") or float(p.purchase_price or 0)
        total_invested += invested

        # NOI in DB is annual per-unit — multiply by units for total
        noi_per_unit = float(p.noi or 0)
        units = p.total_units or 0
        annual_noi = noi_per_unit * units if noi_per_unit and units else 0
        total_noi += annual_noi

        if p.occupancy_rate:
            occ_sum += float(p.occupancy_rate)
            occ_count += 1

        # Compute cap rate from annual NOI / purchase price
        pp = float(p.purchase_price or 0)
        if annual_noi > 0 and pp > 0:
            cap_sum += annual_noi / pp
            cap_count += 1

        irr = ret.get("lpIrr") or 0
        coc = ret.get("cashOnCashYear1") or 0
        loan = fd.get("financing", {}).get("loanAmount") or 0
        equity = invested - loan if invested and loan else invested
        if equity > 0:
            irr_weighted += irr * equity
            coc_weighted += coc * equity
            equity_sum += equity

    return {
        "totalProperties": total_properties,
        "totalUnits": total_units,
        "totalValue": round(total_value, 2),
        "totalInvested": round(total_invested, 2),
        "totalNOI": round(total_noi, 2),
        "averageOccupancy": round(occ_sum / occ_count / 100, 4) if occ_count else 0,
        "averageCapRate": round(cap_sum / cap_count, 4) if cap_count else 0,
        "portfolioCashOnCash": round(coc_weighted / equity_sum, 4) if equity_sum else 0,
        "portfolioIRR": round(irr_weighted / equity_sum, 4) if equity_sum else 0,
    }


@router.get("/", response_model=PropertyListResponse)
async def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    property_type: str | None = None,
    city: str | None = None,
    state: str | None = None,
    market: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    sort_by: str | None = "name",
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db),
):
    """
    List all properties with filtering and pagination.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **property_type**: Filter by type (multifamily, office, retail, industrial)
    - **city**: Filter by city
    - **state**: Filter by state
    - **market**: Filter by market
    """
    skip = (page - 1) * page_size
    order_desc = sort_order.lower() == "desc"

    # Get filtered properties from database
    items = await property_crud.get_multi_filtered(
        db,
        skip=skip,
        limit=page_size,
        property_type=property_type,
        city=city,
        state=state,
        market=market,
        min_units=min_units,
        max_units=max_units,
        order_by=sort_by or "name",
        order_desc=order_desc,
    )

    # Get total count for pagination
    total = await property_crud.count_filtered(
        db,
        property_type=property_type,
        city=city,
        state=state,
        market=market,
        min_units=min_units,
        max_units=max_units,
    )

    return PropertyListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific property by ID.
    """
    property_obj = await property_crud.get(db, property_id)

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    return property_obj


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new property.
    """
    new_property = await property_crud.create(db, obj_in=property_data)
    logger.info(f"Created property: {new_property.name} (ID: {new_property.id})")
    return new_property


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing property.
    """
    existing = await property_crud.get(db, property_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    updated_property = await property_crud.update(
        db, db_obj=existing, obj_in=property_data
    )
    logger.info(f"Updated property: {property_id}")

    return updated_property


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a property (soft delete).
    """
    existing = await property_crud.get(db, property_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    await property_crud.remove(db, id=property_id)
    logger.info(f"Deleted property: {property_id}")
    return None


@router.get("/{property_id}/analytics")
async def get_property_analytics(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get analytics data for a specific property.

    Returns:
    - Historical performance metrics
    - Rent growth trends
    - Occupancy trends
    - Comparable market data
    """
    # Verify property exists
    property_obj = await property_crud.get(db, property_id)
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    # Get market comparables - properties in same market and type
    market_comps_filters = []
    if property_obj.market:
        market_comps_filters.append(
            func.lower(Property.market) == func.lower(property_obj.market)
        )
    if property_obj.property_type:
        market_comps_filters.append(
            Property.property_type == property_obj.property_type
        )

    # Exclude current property from comparables
    market_comps_filters.append(Property.id != property_id)

    # Query market averages for comparable properties
    market_comps_result = await db.execute(
        select(
            func.avg(Property.avg_rent_per_unit).label("avg_rent"),
            func.avg(Property.occupancy_rate).label("avg_occupancy"),
            func.avg(Property.cap_rate).label("avg_cap_rate"),
            func.count(Property.id).label("comp_count"),
        ).where(*market_comps_filters if market_comps_filters else [True])
    )
    market_row = market_comps_result.fetchone()

    # Get current property metrics
    current_rent = _decimal_to_float(property_obj.avg_rent_per_unit)
    raw_occ = _decimal_to_float(property_obj.occupancy_rate)
    current_occupancy = raw_occ / 100 if raw_occ and raw_occ > 1 else raw_occ
    current_cap_rate = _decimal_to_float(property_obj.cap_rate)
    current_noi = _decimal_to_float(property_obj.noi)

    # Get market averages
    market_avg_rent = _decimal_to_float(market_row.avg_rent) if market_row else None
    raw_market_occ = _decimal_to_float(market_row.avg_occupancy) if market_row else None
    market_avg_occupancy = (
        raw_market_occ / 100
        if raw_market_occ and raw_market_occ > 1
        else raw_market_occ
    )
    market_avg_cap_rate = (
        _decimal_to_float(market_row.avg_cap_rate) if market_row else None
    )
    comp_count = market_row.comp_count if market_row else 0

    # Calculate rent vs market ratio
    rent_vs_market = None
    if current_rent and market_avg_rent and market_avg_rent > 0:
        rent_vs_market = round(current_rent / market_avg_rent, 2)

    # If no real data available, return mock data as fallback
    if current_rent is None and current_occupancy is None:
        return {
            "property_id": property_id,
            "property_name": property_obj.name,
            "data_source": "mock",
            "metrics": {
                "ytd_rent_growth": 3.2,
                "ytd_noi_growth": 4.1,
                "avg_occupancy_12m": 95.0,
                "rent_vs_market": 1.05,
            },
            "trends": {
                "rent": [1400, 1425, 1450, 1475, 1490, 1500],
                "occupancy": [94.0, 95.0, 96.0, 96.5, 96.0, 96.5],
                "periods": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            },
            "comparables": {
                "market_avg_rent": 1425,
                "market_avg_occupancy": 94.0,
                "market_avg_cap_rate": 5.5,
                "comparable_count": 0,
            },
        }

    # Build response with actual data
    return {
        "property_id": property_id,
        "property_name": property_obj.name,
        "data_source": "database",
        "metrics": {
            "current_rent_per_unit": round(current_rent, 2) if current_rent else None,
            "current_occupancy": round(current_occupancy, 1)
            if current_occupancy
            else None,
            "current_cap_rate": round(current_cap_rate, 2)
            if current_cap_rate
            else None,
            "current_noi": round(current_noi, 2) if current_noi else None,
            # Historical growth rates would need time-series data
            "ytd_rent_growth": None,  # Would need historical rent data
            "ytd_noi_growth": None,  # Would need historical NOI data
            "avg_occupancy_12m": round(current_occupancy, 1)
            if current_occupancy
            else None,
            "rent_vs_market": rent_vs_market,
        },
        "trends": {
            # Trends would need historical data - returning current values as single point
            "rent": [round(current_rent, 0)] if current_rent else [],
            "occupancy": [round(current_occupancy, 1)] if current_occupancy else [],
            "periods": ["Current"],
            "note": "Historical trend data requires time-series tracking",
        },
        "comparables": {
            "market": property_obj.market,
            "property_type": property_obj.property_type,
            "market_avg_rent": round(market_avg_rent, 2) if market_avg_rent else None,
            "market_avg_occupancy": round(market_avg_occupancy, 1)
            if market_avg_occupancy
            else None,
            "market_avg_cap_rate": round(market_avg_cap_rate, 2)
            if market_avg_cap_rate
            else None,
            "comparable_count": comp_count,
        },
    }


@router.get("/{property_id}/activities", response_model=PropertyActivityListResponse)
async def get_property_activities(
    property_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    activity_type: str | None = Query(
        None,
        description="Filter by activity type: view, edit, comment, status_change, document_upload",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get activity history for a property.

    Returns a paginated list of activities including views, edits, comments,
    status changes, and document uploads.

    - **property_id**: Property ID to get activities for
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 50, max: 100)
    - **activity_type**: Filter by type (view, edit, comment, status_change, document_upload)
    """
    # Verify property exists
    property_obj = await property_crud.get(db, property_id)
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    # Validate activity_type if provided
    valid_types = {"view", "edit", "comment", "status_change", "document_upload"}
    if activity_type and activity_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity_type. Must be one of: {', '.join(valid_types)}",
        )

    # Get activities from database
    activities = await property_activity.get_by_property(
        db,
        property_id=property_id,
        skip=skip,
        limit=limit,
        activity_type=activity_type,
    )

    # Get total count
    total = await property_activity.count_by_property(
        db,
        property_id=property_id,
        activity_type=activity_type,
    )

    # Convert to response models
    items = []
    for activity in activities:
        items.append(
            PropertyActivityResponse(
                id=activity.id,
                property_id=activity.property_id,
                user_id=activity.user_id,
                user_name=None,  # Would need join with users table
                activity_type=ActivityType(activity.activity_type.value),
                description=activity.description,
                field_changed=activity.field_changed,
                old_value=activity.old_value,
                new_value=activity.new_value,
                comment_text=activity.comment_text,
                document_name=activity.document_name,
                document_url=activity.document_url,
                created_at=activity.created_at,
                updated_at=activity.updated_at,
            )
        )

    return PropertyActivityListResponse(
        activities=items,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.post("/{property_id}/activities", response_model=PropertyActivityResponse)
async def create_property_activity(
    property_id: int,
    activity_data: PropertyActivityCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Create a new activity entry for a property.

    Used to log comments, document uploads, and other manual activities.
    Views and edits are typically logged automatically.

    - **property_id**: Property ID
    - **activity_data**: Activity details
    """
    # Verify property exists
    property_obj = await property_crud.get(db, property_id)
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    # Ensure property_id in body matches path
    if activity_data.property_id != property_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property ID in body must match path parameter",
        )

    # Create the activity
    from app.models.activity import PropertyActivity as PropertyActivityModel

    activity = PropertyActivityModel(
        property_id=property_id,
        user_id=current_user.id,
        activity_type=ActivityTypeModel(activity_data.activity_type.value),
        description=activity_data.description,
        field_changed=activity_data.field_changed,
        old_value=activity_data.old_value,
        new_value=activity_data.new_value,
        comment_text=activity_data.comment_text,
        document_name=activity_data.document_name,
        document_url=activity_data.document_url,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    db.add(activity)
    await db.commit()
    await db.refresh(activity)

    logger.info(
        f"User {current_user.email} created {activity_data.activity_type} activity for property {property_id}"
    )

    return PropertyActivityResponse(
        id=activity.id,
        property_id=activity.property_id,
        user_id=activity.user_id,
        user_name=current_user.full_name,
        activity_type=ActivityType(activity.activity_type.value),
        description=activity.description,
        field_changed=activity.field_changed,
        old_value=activity.old_value,
        new_value=activity.new_value,
        comment_text=activity.comment_text,
        document_name=activity.document_name,
        document_url=activity.document_url,
        created_at=activity.created_at,
        updated_at=activity.updated_at,
    )
