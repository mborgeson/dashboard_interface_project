"""
CRUD operations for Property model.
"""

import re
from decimal import Decimal
from typing import Any

import numpy as np
from loguru import logger
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import Property
from app.schemas.property import PropertyCreate, PropertyUpdate

# ---------------------------------------------------------------------------
# Mapping from extracted_values field name prefixes (YEAR_N stripped) to the
# operationsByYear JSON keys expected by the frontend.
#
# The extraction pipeline stores annual cashflow fields with names like
# ``GROSS_POTENTIAL_REVENUE_YEAR_1``, ``NET_OPERATING_INCOME_YEAR_3``, etc.
# This map converts the prefix (before ``_YEAR_``) to the camelCase key used
# in the ``operationsByYear`` dict.
# ---------------------------------------------------------------------------
_CASHFLOW_FIELD_MAP: dict[str, tuple[str, str | None]] = {
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
_YEAR_FIELD_RE = re.compile(
    r"^("
    + "|".join(re.escape(k) for k in sorted(_CASHFLOW_FIELD_MAP, key=len, reverse=True))
    + r")_YEAR_(\d+)$"
)


def _safe_float(val: Any) -> float | None:
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


def _dec(val: Any, places: int = 2) -> Decimal | None:
    """Convert to Decimal for SQLAlchemy Numeric columns."""
    f = _safe_float(val)
    return Decimal(str(round(f, places))) if f is not None else None


# Must match extraction.py _FINANCIAL_DATA_FIELDS + _EXTRACTED_FIELD_MAP keys
_ALL_HYDRATION_FIELDS: set[str] = {
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
_BASE_EXPENSE_FIELD_MAP: dict[str, str] = {
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


class CRUDProperty(CRUDBase[Property, PropertyCreate, PropertyUpdate]):
    """
    CRUD operations for Property model with property-specific methods.
    """

    async def enrich_financial_data(self, db: AsyncSession, prop: Property) -> Property:
        """
        Populate a property's direct columns and financial_data JSON from
        extracted_values if financial_data is currently NULL/empty.

        This is a per-property async version of the batch
        ``hydrate_properties_from_extracted()`` in crud/extraction.py.
        Uses the SAME field mapping logic to avoid divergence.

        The property is updated in-place and committed to DB so subsequent
        requests are served from the cached column.
        """
        # Import here to avoid circular imports at module level
        from app.models.extraction import ExtractedValue

        # Build name variants for matching
        short_name = prop.name.split("(")[0].strip() if prop.name else ""
        name_variants = [prop.name]
        if short_name and short_name != prop.name:
            name_variants.append(short_name)

        field_values: dict[str, float | str | None] = {}

        for variant in name_variants:
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
                            ExtractedValue.field_name.in_(list(_ALL_HYDRATION_FIELDS)),
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

        changed = False

        # -- Build financial_data JSON (same structure as extraction.py) --
        fd = dict(prop.financial_data) if prop.financial_data else {}
        acq = fd.get("acquisition", {})
        fin = fd.get("financing", {})
        ret = fd.get("returns", {})
        ops = fd.get("operations", {})

        if field_values:
            # -- Update direct columns (only if currently empty) --
            pp = _safe_float(field_values.get("PURCHASE_PRICE"))
            if pp is not None and not prop.purchase_price:
                prop.purchase_price = _dec(pp, 2)
                changed = True

            units_f = _safe_float(field_values.get("TOTAL_UNITS"))
            if units_f is not None and units_f > 0 and not prop.total_units:
                prop.total_units = int(units_f)
                changed = True

            yb = _safe_float(field_values.get("YEAR_BUILT"))
            if yb is not None and not prop.year_built:
                prop.year_built = int(yb)
                changed = True

            sf = _safe_float(field_values.get("TOTAL_SF"))
            if sf is not None and not prop.total_sf:
                prop.total_sf = int(sf)
                changed = True

            cap = _safe_float(field_values.get("GOING_IN_CAP_RATE"))
            if cap is not None and not prop.cap_rate:
                prop.cap_rate = _dec(cap, 6)
                changed = True

            addr = field_values.get("PROPERTY_ADDRESS")
            if addr and (not prop.address or prop.address == "TBD"):
                prop.address = str(addr)
                changed = True

            noi_total = _safe_float(field_values.get("NOI"))
            noi_per_unit = _safe_float(field_values.get("NOI_PER_UNIT"))
            if noi_per_unit and not prop.noi:
                prop.noi = _dec(noi_per_unit, 2)
                changed = True
            elif noi_total and prop.total_units and not prop.noi:
                prop.noi = _dec(noi_total / prop.total_units, 2)
                changed = True

            occ = _safe_float(field_values.get("OCCUPANCY_PERCENT"))
            if occ and not prop.occupancy_rate:
                prop.occupancy_rate = _dec(occ, 4)
                changed = True

            avg_rent = _safe_float(field_values.get("AVG_RENT_PER_UNIT"))
            if avg_rent and not prop.avg_rent_per_unit:
                prop.avg_rent_per_unit = _dec(avg_rent, 2)
                changed = True

            avg_rent_sf = _safe_float(field_values.get("AVG_RENT_PER_SF"))
            if avg_rent_sf and not prop.avg_rent_per_sf:
                prop.avg_rent_per_sf = _dec(avg_rent_sf, 4)
                changed = True

            if not prop.current_value and prop.purchase_price:
                prop.current_value = prop.purchase_price
                changed = True

            # Acquisition
            if pp is not None and not acq.get("purchasePrice"):
                acq["purchasePrice"] = round(pp, 2)
            ppu = _safe_float(field_values.get("PRICE_PER_UNIT"))
            if ppu is not None and not acq.get("pricePerUnit"):
                acq["pricePerUnit"] = round(ppu, 2)
            eq = _safe_float(field_values.get("EQUITY"))
            if eq is not None:
                acq["totalAcquisitionBudget"] = acq.get(
                    "totalAcquisitionBudget"
                ) or round(pp or 0, 2)

            # Financing
            la = _safe_float(field_values.get("LOAN_AMOUNT"))
            if la is not None and not fin.get("loanAmount"):
                fin["loanAmount"] = round(la, 2)
            ltv = _safe_float(field_values.get("LOAN_TO_VALUE"))
            if ltv is not None and not fin.get("ltv"):
                fin["ltv"] = round(ltv, 4)
            ir = _safe_float(field_values.get("INTEREST_RATE"))
            if ir is not None and not fin.get("interestRate"):
                fin["interestRate"] = round(ir, 6)
            lt = _safe_float(field_values.get("LOAN_TERM"))
            if lt is not None and not fin.get("loanTermMonths"):
                fin["loanTermMonths"] = int(lt * 12) if lt < 40 else int(lt)
            amort = _safe_float(field_values.get("AMORTIZATION"))
            if amort is not None and not fin.get("amortizationMonths"):
                fin["amortizationMonths"] = (
                    int(amort * 12) if amort < 50 else int(amort)
                )
            ds = _safe_float(field_values.get("DEBT_SERVICE_ANNUAL"))
            if ds is not None and not fin.get("annualDebtService"):
                fin["annualDebtService"] = round(ds, 2)

            # Returns
            lirr = _safe_float(field_values.get("LEVERED_RETURNS_IRR"))
            if lirr is not None and not ret.get("leveredIrr"):
                ret["leveredIrr"] = round(lirr, 6)
                ret["lpIrr"] = round(lirr, 6)
            lmoic = _safe_float(field_values.get("LEVERED_RETURNS_MOIC"))
            if lmoic is not None and not ret.get("leveredMoic"):
                ret["leveredMoic"] = round(lmoic, 4)
                ret["lpMoic"] = round(lmoic, 4)
            uirr = _safe_float(field_values.get("UNLEVERED_RETURNS_IRR"))
            if uirr is not None and not ret.get("unleveredIrr"):
                ret["unleveredIrr"] = round(uirr, 6)
            umoic = _safe_float(field_values.get("UNLEVERED_RETURNS_MOIC"))
            if umoic is not None and not ret.get("unleveredMoic"):
                ret["unleveredMoic"] = round(umoic, 4)

            # Operations
            egi = _safe_float(field_values.get("EFFECTIVE_GROSS_INCOME"))
            if egi is not None and not ops.get("totalRevenueYear1"):
                ops["totalRevenueYear1"] = round(egi, 2)
            nri = _safe_float(field_values.get("NET_RENTAL_INCOME"))
            if nri is not None and not ops.get("netRentalIncomeYear1"):
                ops["netRentalIncomeYear1"] = round(nri, 2)
            noi_val = _safe_float(field_values.get("NOI"))
            if noi_val is not None and not ops.get("noiYear1"):
                ops["noiYear1"] = round(noi_val, 2)
            tex = _safe_float(field_values.get("TOTAL_EXPENSES"))
            if tex is not None and not ops.get("totalExpensesYear1"):
                ops["totalExpensesYear1"] = round(tex, 2)
            if occ is not None and not ops.get("occupancy"):
                ops["occupancy"] = round(occ, 4)
            if avg_rent is not None and not ops.get("avgRentPerUnit"):
                ops["avgRentPerUnit"] = round(avg_rent, 2)
            if avg_rent_sf is not None and not ops.get("avgRentPerSf"):
                ops["avgRentPerSf"] = round(avg_rent_sf, 4)

            # Total operating expenses (annual total, not per-unit)
            toe = _safe_float(field_values.get("TOTAL_OPERATING_EXPENSES"))
            if toe is not None and not ops.get("totalOperatingExpensesYear1"):
                ops["totalOperatingExpensesYear1"] = round(toe, 2)

        # -- Build expense breakdown + multi-year ops from extracted_values --
        expenses = fd.get("expenses", {})
        ops_by_year = fd.get("operationsByYear", {})
        if not expenses or not ops_by_year:
            # Query YEAR_N fields from extracted_values (annual totals)
            (
                ops_by_year,
                expenses,
                ev_changed,
            ) = await self._build_ops_from_extracted_values(db, prop, expenses)
            if ev_changed:
                changed = True

        # Fallback: build expenses from base per-unit fields when YEAR_N
        # fields didn't produce an expenses dict
        if not expenses and field_values:
            total_units = prop.total_units or 0
            for ev_field, json_key in _BASE_EXPENSE_FIELD_MAP.items():
                val = _safe_float(field_values.get(ev_field))
                if val is not None:
                    # Base fields are per-unit; convert to annual total
                    annual = (
                        round(val * total_units, 2) if total_units else round(val, 2)
                    )
                    expenses[json_key] = annual
            if expenses:
                changed = True

        new_fd: dict[str, Any] = {}
        if acq:
            new_fd["acquisition"] = acq
        if fin:
            new_fd["financing"] = fin
        if ret:
            new_fd["returns"] = ret
        if ops:
            new_fd["operations"] = ops
        if expenses:
            new_fd["expenses"] = expenses
        if ops_by_year:
            new_fd["operationsByYear"] = ops_by_year

        if new_fd and new_fd != (prop.financial_data or {}):
            prop.financial_data = new_fd
            changed = True

        if changed:
            db.add(prop)
            await db.commit()
            await db.refresh(prop)
            logger.info(
                "property_financial_data_enriched",
                property_id=prop.id,
                property_name=prop.name,
                fields_found=len(field_values),
            )

        return prop

    async def _build_ops_from_extracted_values(
        self,
        db: AsyncSession,
        prop: Property,
        existing_expenses: dict,
    ) -> tuple[dict, dict, bool]:
        """
        Build ``operationsByYear`` dict from ``extracted_values`` rows.

        The extraction pipeline stores annual cashflow data as individual
        field rows with names like ``GROSS_POTENTIAL_REVENUE_YEAR_1``,
        ``NET_OPERATING_INCOME_YEAR_3``, etc.  This method queries those
        rows, groups them by year number, and assembles the same JSON
        structure that the frontend's OperationsTab expects.

        Returns:
            (ops_by_year dict, expenses dict, changed bool)
        """
        from app.models.extraction import ExtractedValue

        # Build name variants for matching (same logic as enrich_financial_data)
        short_name = prop.name.split("(")[0].strip() if prop.name else ""
        name_variants = [prop.name]
        if short_name and short_name != prop.name:
            name_variants.append(short_name)

        # Collect all YEAR_N fields for this property
        year_rows: list[tuple[str, float | None]] = []
        for variant in name_variants:
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
                            # Use LIKE for SQLite compatibility; Python regex
                            # in the loop below does precise matching.
                            ExtractedValue.field_name.like("%_YEAR_%"),
                        )
                    )
                    .order_by(ExtractedValue.created_at.desc())
                )
            ).all()

            if rows:
                year_rows = [(r[0], r[1]) for r in rows]
                break

        if not year_rows:
            return {}, existing_expenses, False

        # Group values by year, keeping only the latest per field (ordered DESC above)
        seen: set[str] = set()
        year_values: dict[int, dict[str, float]] = {}

        for field_name, value_numeric in year_rows:
            if field_name in seen:
                continue
            seen.add(field_name)

            match = _YEAR_FIELD_RE.match(field_name)
            if not match or value_numeric is None:
                continue

            prefix = match.group(1)
            year_num = int(match.group(2))
            mapping = _CASHFLOW_FIELD_MAP.get(prefix)
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
        ops_by_year: dict[str, dict] = {}
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
            for _prefix, (json_key, sub_dict) in _CASHFLOW_FIELD_MAP.items():
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
            property_id=prop.id,
            property_name=prop.name,
            years=len(ops_by_year),
            total_fields=sum(
                len(v) + len(v.get("expenses", {})) for v in ops_by_year.values()
            ),
        )

        return ops_by_year, expenses, True

    def _build_property_conditions(
        self,
        *,
        property_type: str | None = None,
        city: str | None = None,
        state: str | None = None,
        market: str | None = None,
        min_units: int | None = None,
        max_units: int | None = None,
    ) -> list:
        """Build SQLAlchemy filter conditions for property queries."""
        conditions: list = []

        if property_type:
            conditions.append(Property.property_type == property_type)

        if city:
            conditions.append(func.lower(Property.city) == func.lower(city))

        if state:
            conditions.append(func.upper(Property.state) == func.upper(state))

        if market:
            conditions.append(func.lower(Property.market) == func.lower(market))

        if min_units is not None:
            conditions.append(Property.total_units >= min_units)

        if max_units is not None:
            conditions.append(Property.total_units <= max_units)

        return conditions

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        property_type: str | None = None,
        city: str | None = None,
        state: str | None = None,
        market: str | None = None,
        min_units: int | None = None,
        max_units: int | None = None,
        order_by: str = "name",
        order_desc: bool = False,
    ) -> list[Property]:
        """Get properties with multiple filters."""
        conditions = self._build_property_conditions(
            property_type=property_type,
            city=city,
            state=state,
            market=market,
            min_units=min_units,
            max_units=max_units,
        )
        return await self.get_multi_ordered(
            db,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc,
            conditions=conditions,
        )

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        property_type: str | None = None,
        city: str | None = None,
        state: str | None = None,
        market: str | None = None,
        min_units: int | None = None,
        max_units: int | None = None,
    ) -> int:
        """Count properties with filters."""
        conditions = self._build_property_conditions(
            property_type=property_type,
            city=city,
            state=state,
            market=market,
            min_units=min_units,
            max_units=max_units,
        )
        return await self.count_where(db, conditions=conditions)

    async def get_by_market(
        self,
        db: AsyncSession,
        *,
        market: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Property]:
        """Get properties filtered by market."""
        result = await db.execute(
            select(Property)
            .where(func.lower(Property.market) == func.lower(market))
            .order_by(Property.name.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_analytics_summary(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Get aggregate analytics for all properties."""
        # Total count
        count_result = await db.execute(select(func.count()).select_from(Property))
        total_count = count_result.scalar() or 0

        # Sum of units
        units_result = await db.execute(select(func.sum(Property.total_units)))
        total_units = units_result.scalar() or 0

        # Sum of square feet
        sf_result = await db.execute(select(func.sum(Property.total_sf)))
        total_sf = sf_result.scalar() or 0

        # Average cap rate
        cap_result = await db.execute(select(func.avg(Property.cap_rate)))
        avg_cap_rate = cap_result.scalar()

        # Average occupancy
        occ_result = await db.execute(select(func.avg(Property.occupancy_rate)))
        avg_occupancy = occ_result.scalar()

        return {
            "total_properties": total_count,
            "total_units": total_units,
            "total_sf": total_sf,
            "avg_cap_rate": float(avg_cap_rate) if avg_cap_rate else None,
            "avg_occupancy": float(avg_occupancy) if avg_occupancy else None,
        }

    async def get_markets(
        self,
        db: AsyncSession,
    ) -> list[str]:
        """Get list of unique markets."""
        result = await db.execute(
            select(Property.market)
            .where(Property.market.isnot(None))
            .distinct()
            .order_by(Property.market)
        )
        return [row[0] for row in result.fetchall()]


# Singleton instance
property = CRUDProperty(Property)
