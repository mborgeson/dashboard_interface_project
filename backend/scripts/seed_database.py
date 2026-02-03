"""
Seed the database from real extraction data.

Queries extracted_values and monitored_files tables to populate properties,
deals, documents, and transactions with real UW Model data.

Usage:
    cd backend && python scripts/seed_database.py
"""

import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add backend directory to sys.path so 'app' package is importable
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import text

from app.db.session import SessionLocal
from app.models import (
    Deal,
    DealStage,
    DistributionSchedule,
    Document,
    Property,
    QueuedReport,
    ReportCategory,
    ReportFormat,
    ReportStatus,
    ReportTemplate,
    ScheduleFrequency,
    User,
)
from app.models.transaction import Transaction

# ---------------------------------------------------------------------------
# Two manually-defined closed deals (not in extraction data)
# ---------------------------------------------------------------------------
CLOSED_DEALS = [
    {
        "name": "Cabana on 99th",
        "city": "Glendale",
        "state": "AZ",
        "zip_code": "85305",
        "county": "Maricopa",
        "market": "Phoenix",
        "submarket": "Glendale",
        "property_type": "multifamily",
        "building_type": "Garden",
        "total_units": 120,
        "year_built": 1985,
        "purchase_price": Decimal("12500000"),
        "latitude": Decimal("33.5131"),
        "longitude": Decimal("-112.2358"),
    },
    {
        "name": "Tempe Metro",
        "city": "Tempe",
        "state": "AZ",
        "zip_code": "85281",
        "county": "Maricopa",
        "market": "Phoenix",
        "submarket": "Tempe",
        "property_type": "multifamily",
        "building_type": "Garden",
        "total_units": 200,
        "year_built": 1990,
        "purchase_price": Decimal("28000000"),
        "latitude": Decimal("33.4255"),
        "longitude": Decimal("-111.9400"),
    },
]

# Deal stage mapping from monitored_files stages
STAGE_MAP = {
    "dead": DealStage.DEAD,
    "initial_review": DealStage.INITIAL_REVIEW,
    "underwriting": DealStage.UNDERWRITING,
    "closed": DealStage.CLOSED,
}


def safe_numeric(val_text, val_numeric, default=None):
    """Extract a numeric value, preferring value_numeric."""
    if val_numeric is not None:
        return float(val_numeric)
    if val_text is not None:
        try:
            return float(val_text)
        except (ValueError, TypeError):
            return default
    return default


def safe_text(val_text, default=None):
    """Extract a text value."""
    if val_text and str(val_text).strip():
        return str(val_text).strip()
    return default


def safe_int(val_text, val_numeric, default=None):
    """Extract an integer value."""
    v = safe_numeric(val_text, val_numeric)
    if v is not None:
        return int(round(v))
    return default


def safe_zip(val_text, val_numeric):
    """Extract zip code, stripping .0 suffix from numeric values."""
    v = safe_numeric(val_text, val_numeric)
    if v is not None:
        return str(int(v))
    if val_text:
        return str(val_text).replace(".0", "").strip()
    return "00000"


def get_extracted_fields(session, property_name: str) -> dict:
    """Query all non-error extracted values for a property, return as dict."""
    rows = session.execute(
        text("""
            SELECT field_name, value_text, value_numeric
            FROM extracted_values
            WHERE property_name = :pname AND is_error = false
        """),
        {"pname": property_name},
    ).fetchall()
    fields = {}
    for field_name, value_text, value_numeric in rows:
        fields[field_name] = {"text": value_text, "numeric": value_numeric}
    return fields


def field_num(fields: dict, key: str, default=None):
    """Get numeric value from extracted fields dict."""
    f = fields.get(key)
    if f is None:
        return default
    return safe_numeric(f["text"], f["numeric"], default)


def field_text(fields: dict, key: str, default=None):
    """Get text value from extracted fields dict."""
    f = fields.get(key)
    if f is None:
        return default
    return safe_text(f["text"], default)


def field_int(fields: dict, key: str, default=None):
    """Get integer value from extracted fields dict."""
    f = fields.get(key)
    if f is None:
        return default
    return safe_int(f["text"], f["numeric"], default)


def parse_city_from_deal_name(deal_name: str) -> tuple[str, str, str]:
    """
    Parse 'Deal Name (City, ST)' into (name, city, state).
    E.g., '505 West (Tempe, AZ)' -> ('505 West', 'Tempe', 'AZ')
    """
    if "(" in deal_name and ")" in deal_name:
        name_part = deal_name.split("(")[0].strip()
        location = deal_name.split("(")[1].rstrip(")")
        parts = [p.strip() for p in location.split(",")]
        city = parts[0] if parts else ""
        state = parts[1] if len(parts) > 1 else "AZ"
        return name_part, city, state
    return deal_name, "", "AZ"


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------


def clear_data(session):
    """Clear existing fabricated data while preserving extraction tables."""
    print("Clearing existing data...")
    # Order matters due to foreign keys
    session.execute(text("DELETE FROM transactions"))
    session.execute(text("DELETE FROM deals"))
    session.execute(text("DELETE FROM documents"))
    session.execute(text("DELETE FROM distribution_schedules"))
    session.execute(text("DELETE FROM queued_reports"))
    session.execute(text("DELETE FROM report_templates"))
    session.execute(text("DELETE FROM properties"))
    # Don't delete users - just update them
    session.commit()
    print("  Cleared: transactions, deals, documents, distribution_schedules,")
    print("           queued_reports, report_templates, properties")


def seed_properties_from_extraction(session) -> dict[str, int]:
    """
    Create property records from extracted_values data.
    Returns mapping of deal_name -> property_id.
    """
    print("\nSeeding properties from extraction data...")

    # Get all monitored files with deal names (deduplicated)
    monitored = session.execute(
        text("""
            SELECT DISTINCT ON (deal_name) deal_name, deal_stage, file_name,
                   file_path, size_bytes, modified_date, first_seen
            FROM monitored_files
            WHERE deal_name IS NOT NULL AND deal_name <> ''
            ORDER BY deal_name, modified_date DESC
        """)
    ).fetchall()

    property_map = {}  # deal_name -> property_id
    count = 0

    for mf in monitored:
        deal_name = mf[0]
        deal_stage = mf[1]

        # Get extracted fields for this property
        fields = get_extracted_fields(session, deal_name)

        # Parse city/state from deal name as fallback
        _, name_city, name_state = parse_city_from_deal_name(deal_name)

        # Get values from extraction (with fallbacks)
        city = field_text(fields, "PROPERTY_CITY", name_city or "Phoenix")
        state = field_text(fields, "PROPERTY_STATE", name_state or "AZ")

        # PROPERTY_ADDRESS sometimes contains year_built instead of address
        raw_address = field_text(fields, "PROPERTY_ADDRESS", "")
        try:
            float(raw_address)
            # It's a number (like year_built bleeding in), use deal name as address
            address = deal_name.split("(")[0].strip()
        except (ValueError, TypeError):
            address = raw_address if raw_address else deal_name.split("(")[0].strip()

        zip_code = safe_zip(
            fields.get("PROPERTY_ZIP", {}).get("text") if fields.get("PROPERTY_ZIP") else None,
            fields.get("PROPERTY_ZIP", {}).get("numeric") if fields.get("PROPERTY_ZIP") else None,
        )

        total_units = field_int(fields, "TOTAL_UNITS")
        avg_sf = field_num(fields, "AVG_SQUARE_FEET")
        total_sf = int(avg_sf * total_units) if avg_sf and total_units else None
        purchase_price = field_num(fields, "PURCHASE_PRICE")
        noi_raw = field_num(fields, "NET_OPERATING_INCOME")
        cap_rate = field_num(fields, "CAP_RATE")
        vacancy_rate = field_num(fields, "VACANCY_LOSS_YEAR_1_RATE")
        occupancy = round((1 - vacancy_rate) * 100, 2) if vacancy_rate is not None else None

        # Build financial_data JSON for frontend nested fields
        financial_data = {
            "acquisition": {
                "purchasePrice": purchase_price,
                "totalAcquisitionBudget": field_num(fields, "TOTAL_ACQUISITION_BUDGET"),
                "landAndAcquisitionCosts": field_num(fields, "TOTAL_LAND_AND_ACQUISITION_COSTS"),
                "hardCosts": field_num(fields, "TOTAL_HARD_COSTS"),
                "softCosts": field_num(fields, "TOTAL_SOFT_COSTS"),
                "lenderClosingCosts": field_num(fields, "TOTAL_LENDER_CLOSING_COSTS"),
                "equityClosingCosts": field_num(fields, "TOTAL_EQUITY_CLOSING_COSTS"),
                "closingCosts": field_num(fields, "EQUITY_CLOSING_COSTS_EXPENSES"),
                "acquisitionFee": field_num(fields, "ACQUISITION_FEE"),
                "pricePerUnit": round(purchase_price / total_units, 2) if purchase_price and total_units else None,
            },
            "financing": {
                "loanAmount": field_num(fields, "LOAN_AMOUNT"),
                "ltv": round(field_num(fields, "LOAN_AMOUNT", 0) / purchase_price, 3) if purchase_price and field_num(fields, "LOAN_AMOUNT") else None,
                "interestRate": field_num(fields, "SENIOR_INTEREST_RATE"),
                "loanTermMonths": field_int(fields, "LOAN_TERM_MONTHS"),
                "amortizationMonths": field_int(fields, "AMORTIZATION_MONTHS"),
                "annualDebtService": field_num(fields, "ANNUAL_DEBT_SERVICE"),
                "debtServiceYear1": field_num(fields, "SENIOR_LOAN_DEBT_SERVICE_YEAR_1"),
            },
            "returns": {
                "lpIrr": field_num(fields, "LP_RETURNS_IRR"),
                "lpMoic": field_num(fields, "LP_RETURNS_MOIC"),
                "leveredIrr": field_num(fields, "LEVERED_RETURNS_IRR"),
                "leveredMoic": field_num(fields, "LEVERED_RETURNS_MOIC"),
                "cashOnCashYear1": field_num(fields, "LP_RETURNS_PREREFI_CASH_ON_CASH"),
                "cashOnCashYear2": field_num(fields, "LP_RETURNS_POSTREFI_CASH_ON_CASH"),
                "cashOnCashYear3": field_num(fields, "LP_RETURNS_AVG_REFI_CASH_ON_CASH"),
                "unleveredIrr": field_num(fields, "UNLEVERED_RETURNS_IRR"),
                "unleveredMoic": field_num(fields, "UNLEVERED_RETURNS_MOIC"),
                "lpCashflowInflow": field_num(fields, "LP_CASHFLOW_INFLOW_RETURN_TOTAL"),
                "totalEquityCommitment": field_num(fields, "EQUITY_LP_CAPITAL"),
            },
            "operations": {
                "vacancyRate": vacancy_rate,
                "occupancy": occupancy,
                "avgRentPerUnit": field_num(fields, "AVERAGE_RENT_PER_UNIT_INPLACE"),
                "avgRentPerSf": field_num(fields, "AVERAGE_RENT_PER_SF_INPLACE"),
                "totalOperatingExpenses": field_num(fields, "TOTAL_OPERATING_EXPENSES"),
                "noiYear1": field_num(fields, "NET_OPERATING_INCOME_YEAR_1"),
                "totalRevenueYear1": field_num(fields, "GROSS_POTENTIAL_REVENUE_YEAR_1"),
                "netRentalIncomeYear1": field_num(fields, "NET_RENTAL_INCOME_YEAR_1"),
                "otherIncomeYear1": field_num(fields, "TOTAL_OTHER_INCOME_YEAR_1"),
                "vacancyLossYear1": field_num(fields, "VACANCY_LOSS_YEAR_1"),
                "concessionsYear1": field_num(fields, "CONCESSIONS_YEAR_1"),
            },
            # Multi-year operations data (years 1-5)
            "operationsByYear": {
                str(yr): {
                    "grossPotentialRevenue": field_num(fields, f"GROSS_POTENTIAL_REVENUE_YEAR_{yr}"),
                    "lossToLease": field_num(fields, f"LOSS_TO_LEASE_YEAR_{yr}"),
                    "vacancyLoss": field_num(fields, f"VACANCY_LOSS_YEAR_{yr}"),
                    "badDebts": field_num(fields, f"BAD_DEBTS_YEAR_{yr}"),
                    "concessions": field_num(fields, f"CONCESSIONS_YEAR_{yr}"),
                    "otherLoss": field_num(fields, f"OTHER_LOSS_YEAR_{yr}"),
                    "netRentalIncome": field_num(fields, f"NET_RENTAL_INCOME_YEAR_{yr}"),
                    "otherIncome": field_num(fields, f"TOTAL_OTHER_INCOME_YEAR_{yr}"),
                    "laundryIncome": field_num(fields, f"LAUNDRY_INCOME_YEAR_{yr}"),
                    "parkingIncome": field_num(fields, f"PARKING_INCOME_YEAR_{yr}"),
                    "petIncome": field_num(fields, f"PET_INCOME_YEAR_{yr}"),
                    "storageIncome": field_num(fields, f"STORAGE_INCOME_YEAR_{yr}"),
                    "utilityIncome": field_num(fields, f"UTILITY_INCOME_YEAR_{yr}"),
                    "otherMiscIncome": field_num(fields, f"OTHER_MISC_INCOME_YEAR_{yr}"),
                    "effectiveGrossIncome": field_num(fields, f"EFFECTIVE_GROSS_INCOME_YEAR_{yr}"),
                    "totalOperatingExpenses": field_num(fields, f"TOTAL_OPERATING_EXPENSES_YEAR_{yr}"),
                    "noi": field_num(fields, f"NET_OPERATING_INCOME_YEAR_{yr}"),
                    "expenses": {
                        "realEstateTaxes": field_num(fields, f"REAL_ESTATE_TAXES_YEAR_{yr}"),
                        "propertyInsurance": field_num(fields, f"PROPERTY_INSURANCE_YEAR_{yr}"),
                        "staffingPayroll": field_num(fields, f"STAFFING_PAYROLL_YEAR_{yr}"),
                        "propertyManagementFee": field_num(fields, f"PROPERTY_MANAGEMENT_FEE_YEAR_{yr}"),
                        "repairsAndMaintenance": field_num(fields, f"REPAIRS_AND_MAINTENANCE_YEAR_{yr}"),
                        "turnover": field_num(fields, f"TURNOVER_YEAR_{yr}"),
                        "contractServices": field_num(fields, f"CONTRACT_SERVICES_YEAR_{yr}"),
                        "reservesForReplacement": field_num(fields, f"RESERVES_FOR_REPLACEMENT_YEAR_{yr}"),
                        "adminLegalSecurity": field_num(fields, f"ADMIN_LEGAL_AND_SECURITY_YEAR_{yr}"),
                        "advertisingLeasingMarketing": field_num(fields, f"ADVERTISING_LEASING_AND_MARKETING_YEAR_{yr}"),
                        "otherExpenses": field_num(fields, f"OTHER_EXPENSES_YEAR_{yr}"),
                        "utilities": field_num(fields, f"UTILITIES_YEAR_{yr}"),
                    },
                }
                for yr in range(1, 6)
            },
            "expenses": {
                "realEstateTaxes": field_num(fields, "REAL_ESTATE_TAXES_YEAR_1"),
                "insurance": field_num(fields, "INSURANCE_PREMIUM"),
                "utilities": field_num(fields, "UTILITIES_YEAR_1"),
                "management": field_num(fields, "PROPERTY_MANAGEMENT_FEE_YEAR_1"),
                "managementRate": field_num(fields, "PROPERTY_MANAGEMENT_FEE_RATE"),
                "repairs": field_num(fields, "REPAIRS_AND_MAINTENANCE_YEAR_1"),
                "payroll": field_num(fields, "STAFFING_PAYROLL_YEAR_1"),
                "marketing": field_num(fields, "ADVERTISING_LEASING_AND_MARKETING_YEAR_1"),
                "contractServices": field_num(fields, "CONTRACT_SERVICES_YEAR_1"),
                "adminLegalSecurity": field_num(fields, "ADMIN_LEGAL_AND_SECURITY_YEAR_1"),
                "reserves": field_num(fields, "RESERVES_FOR_REPLACEMENT_YEAR_1"),
                "turnover": field_num(fields, "TURNOVER_YEAR_1"),
                "otherExpenses": field_num(fields, "OTHER_EXPENSES_YEAR_1"),
            },
            "exit": {
                "exitCapRate": field_num(fields, "EXIT_CAP_RATE"),
                "exitPeriodMonths": field_int(fields, "EXIT_PERIOD_MONTHS"),
                "holdPeriodYears": round(field_num(fields, "EXIT_PERIOD_MONTHS", 60) / 12, 1),
                "basisPerUnitAtClose": field_num(fields, "BASIS_UNIT_AT_CLOSE"),
                "basisPerUnitAtExit": field_num(fields, "BASIS_UNIT_AT_EXIT"),
                "seniorDebtBasisPerUnitAtClose": field_num(fields, "SENIOR_DEBT_BASIS_UNIT_AT_CLOSE"),
                "seniorDebtBasisPerUnitAtExit": field_num(fields, "SENIOR_DEBT_BASIS_UNIT_AT_EXIT"),
            },
            "physical": {
                "numberOfBuildings": field_int(fields, "NUMBER_OF_BUILDINGS"),
                "stories": field_int(fields, "STORIES"),
                "landArea": field_num(fields, "LAND_AREA"),
            },
        }

        prop = Property(
            name=deal_name,
            property_type="multifamily",
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            county=field_text(fields, "COUNTY", "Maricopa"),
            market=field_text(fields, "MARKET", "Phoenix"),
            submarket=field_text(fields, "SUBMARKET"),
            latitude=Decimal(str(field_num(fields, "PROPERTY_LATITUDE", 33.45))),
            longitude=Decimal(str(field_num(fields, "PROPERTY_LONGITUDE", -112.07))),
            building_type=field_text(fields, "BUILDING_TYPE", "Garden"),
            year_built=field_int(fields, "YEAR_BUILT"),
            total_units=total_units,
            total_sf=total_sf,
            lot_size_acres=Decimal(str(field_num(fields, "LAND_AREA"))) if field_num(fields, "LAND_AREA") else None,
            purchase_price=Decimal(str(round(purchase_price, 2))) if purchase_price else None,
            current_value=Decimal(str(round(purchase_price, 2))) if purchase_price else None,
            occupancy_rate=Decimal(str(occupancy)) if occupancy else None,
            avg_rent_per_unit=Decimal(str(round(field_num(fields, "AVERAGE_RENT_PER_UNIT_INPLACE", 0), 2))) if field_num(fields, "AVERAGE_RENT_PER_UNIT_INPLACE") else None,
            avg_rent_per_sf=Decimal(str(round(field_num(fields, "AVERAGE_RENT_PER_SF_INPLACE", 0), 2))) if field_num(fields, "AVERAGE_RENT_PER_SF_INPLACE") else None,
            noi=Decimal(str(round(noi_raw, 2))) if noi_raw else None,
            cap_rate=Decimal(str(round(cap_rate, 4))) if cap_rate else None,
            data_source="extraction",
            financial_data=financial_data,
        )
        session.add(prop)
        session.flush()  # Get the ID
        property_map[deal_name] = prop.id
        count += 1

        if fields:
            print(f"  {count}. {deal_name} → id={prop.id} ({len(fields)} fields)")
        else:
            print(f"  {count}. {deal_name} → id={prop.id} (no extraction data)")

    # Add closed deals (not in extraction)
    for cd in CLOSED_DEALS:
        prop = Property(
            name=f"{cd['name']} ({cd['city']}, {cd['state']})",
            property_type=cd["property_type"],
            address=cd["name"],
            city=cd["city"],
            state=cd["state"],
            zip_code=cd["zip_code"],
            county=cd["county"],
            market=cd["market"],
            submarket=cd["submarket"],
            building_type=cd["building_type"],
            total_units=cd["total_units"],
            year_built=cd["year_built"],
            purchase_price=cd["purchase_price"],
            current_value=cd["purchase_price"],
            latitude=cd["latitude"],
            longitude=cd["longitude"],
            data_source="manual",
        )
        session.add(prop)
        session.flush()
        full_name = f"{cd['name']} ({cd['city']}, {cd['state']})"
        property_map[full_name] = prop.id
        count += 1
        print(f"  {count}. {full_name} → id={prop.id} (closed deal, manual entry)")

    session.commit()
    print(f"\n  Total properties created: {count}")
    return property_map


def seed_deals(session, property_map: dict[str, int]):
    """Create deal records from monitored_files data."""
    print("\nSeeding deals...")

    # Get monitored files data
    monitored = session.execute(
        text("""
            SELECT DISTINCT ON (deal_name) deal_name, deal_stage, first_seen
            FROM monitored_files
            WHERE deal_name IS NOT NULL AND deal_name <> ''
            ORDER BY deal_name, modified_date DESC
        """)
    ).fetchall()

    count = 0
    for mf in monitored:
        deal_name = mf[0]
        deal_stage_str = mf[1]
        first_seen = mf[2]

        prop_id = property_map.get(deal_name)
        stage = STAGE_MAP.get(deal_stage_str, DealStage.LEAD)

        # Get financial metrics from extracted data
        fields = get_extracted_fields(session, deal_name)

        irr = field_num(fields, "LP_RETURNS_IRR")
        moic = field_num(fields, "LP_RETURNS_MOIC")
        purchase_price = field_num(fields, "PURCHASE_PRICE")
        exit_months = field_num(fields, "EXIT_PERIOD_MONTHS")

        # Calculate deal score (0-100) based on IRR and MOIC
        deal_score = None
        if irr is not None and moic is not None:
            irr_score = min(irr / 0.25 * 50, 50)  # 25% IRR = 50 points
            moic_score = min((moic - 1) / 1.5 * 50, 50)  # 2.5x MOIC = 50 points
            deal_score = int(round(irr_score + moic_score))

        deal = Deal(
            name=deal_name,
            deal_type="acquisition",
            stage=stage,
            stage_order=0,
            property_id=prop_id,
            asking_price=Decimal(str(round(purchase_price, 2))) if purchase_price else None,
            projected_irr=Decimal(str(round(irr, 4))) if irr is not None else None,
            projected_coc=None,  # CoC extracted as raw $ not rate; stored in financial_data
            projected_equity_multiple=Decimal(str(round(moic, 2))) if moic is not None else None,
            hold_period_years=int(round(exit_months / 12)) if exit_months else 5,
            initial_contact_date=first_seen.date() if first_seen else None,
            source="Broker",
            priority="medium",
            deal_score=deal_score,
        )
        session.add(deal)
        count += 1

    # Add closed deals
    for cd in CLOSED_DEALS:
        full_name = f"{cd['name']} ({cd['city']}, {cd['state']})"
        prop_id = property_map.get(full_name)
        deal = Deal(
            name=full_name,
            deal_type="acquisition",
            stage=DealStage.CLOSED,
            stage_order=0,
            property_id=prop_id,
            asking_price=cd["purchase_price"],
            final_price=cd["purchase_price"],
            source="Off-Market",
            priority="high",
            actual_close_date=date(2024, 6, 15) if cd["name"] == "Cabana on 99th" else date(2024, 9, 1),
            deal_score=75,
        )
        session.add(deal)
        count += 1

    session.commit()
    print(f"  Created {count} deals")


def seed_documents(session, property_map: dict[str, int]):
    """Create document records from monitored_files."""
    print("\nSeeding documents...")

    monitored = session.execute(
        text("""
            SELECT DISTINCT ON (deal_name) deal_name, file_name, file_path,
                   size_bytes, modified_date
            FROM monitored_files
            WHERE deal_name IS NOT NULL AND deal_name <> ''
            ORDER BY deal_name, modified_date DESC
        """)
    ).fetchall()

    count = 0
    for mf in monitored:
        deal_name = mf[0]
        file_name = mf[1]
        file_path = mf[2]
        size_bytes = mf[3] or 0
        modified_date = mf[4] or datetime.now(UTC)

        prop_id = property_map.get(deal_name)

        doc = Document(
            name=file_name or f"{deal_name} UW Model",
            type="financial",
            property_id=str(prop_id) if prop_id else None,
            property_name=deal_name,
            size=size_bytes,
            uploaded_at=modified_date,
            uploaded_by="matt@bandrcapital.com",
            description=f"Underwriting model for {deal_name}",
            url=file_path,
            file_path=file_path,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        session.add(doc)
        count += 1

    session.commit()
    print(f"  Created {count} documents")


def seed_transactions(session, property_map: dict[str, int]):
    """Create transactions ONLY for closed deals."""
    print("\nSeeding transactions (closed deals only)...")

    count = 0
    for cd in CLOSED_DEALS:
        full_name = f"{cd['name']} ({cd['city']}, {cd['state']})"
        prop_id = property_map.get(full_name)

        # Acquisition transaction
        tx = Transaction(
            property_id=prop_id,
            property_name=full_name,
            type="acquisition",
            category="Purchase",
            amount=cd["purchase_price"],
            date=date(2024, 6, 15) if cd["name"] == "Cabana on 99th" else date(2024, 9, 1),
            description=f"Acquisition of {full_name}",
        )
        session.add(tx)
        count += 1

    session.commit()
    print(f"  Created {count} transactions")


def seed_users(session):
    """Create or update user accounts with correct email domain."""
    print("\nSeeding users...")

    # Check if users exist
    existing = session.execute(text("SELECT id, email FROM users")).fetchall()
    if existing:
        # Update email domain
        session.execute(
            text("UPDATE users SET email = REPLACE(email, 'brcapital.com', 'bandrcapital.com') WHERE email LIKE '%brcapital.com%'")
        )
        session.commit()
        print("  Updated existing user email domains")
        return

    from app.core.security import get_password_hash

    users = [
        User(
            email="matt@bandrcapital.com",
            full_name="Matt Brogan",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True,
            is_verified=True,
        ),
        User(
            email="sarah@bandrcapital.com",
            full_name="Sarah Chen",
            hashed_password=get_password_hash("user123"),
            role="analyst",
            is_active=True,
            is_verified=True,
        ),
    ]
    session.add_all(users)
    session.commit()
    print(f"  Created {len(users)} users")


def seed_report_templates(session):
    """Create report templates."""
    print("\nSeeding report templates...")

    templates = [
        ReportTemplate(
            name="Property Performance Summary",
            description="Comprehensive performance metrics for individual properties including NOI, occupancy, and returns.",
            category=ReportCategory.FINANCIAL,
            sections=["executive_summary", "financial_performance", "operations", "market_comparison"],
            export_formats=[ReportFormat.PDF, ReportFormat.EXCEL],
            is_default=True,
            created_by="matt@bandrcapital.com",
        ),
        ReportTemplate(
            name="Portfolio Overview",
            description="High-level portfolio summary with aggregate metrics across all properties.",
            category=ReportCategory.PORTFOLIO,
            sections=["portfolio_summary", "property_breakdown", "performance_trends"],
            export_formats=[ReportFormat.PDF, ReportFormat.EXCEL, ReportFormat.PPTX],
            is_default=True,
            created_by="matt@bandrcapital.com",
        ),
        ReportTemplate(
            name="Deal Pipeline Report",
            description="Current deal pipeline status with stage distribution and projected returns.",
            category=ReportCategory.EXECUTIVE,
            sections=["pipeline_overview", "stage_analysis", "deal_details", "projected_returns"],
            export_formats=[ReportFormat.PDF, ReportFormat.EXCEL],
            is_default=False,
            created_by="matt@bandrcapital.com",
        ),
        ReportTemplate(
            name="Market Analysis Report",
            description="Phoenix MSA market data including rent trends, supply, employment, and economic indicators.",
            category=ReportCategory.MARKET,
            sections=["market_overview", "rent_trends", "supply_pipeline", "economic_data"],
            export_formats=[ReportFormat.PDF],
            is_default=True,
            created_by="matt@bandrcapital.com",
        ),
        ReportTemplate(
            name="Investor Distribution Report",
            description="Quarterly investor distribution calculations and waterfall analysis.",
            category=ReportCategory.FINANCIAL,
            sections=["distribution_summary", "waterfall_analysis", "investor_returns"],
            export_formats=[ReportFormat.PDF, ReportFormat.EXCEL],
            is_default=False,
            created_by="matt@bandrcapital.com",
        ),
    ]
    session.add_all(templates)
    session.commit()
    print(f"  Created {len(templates)} report templates")
    return templates


def seed_queued_reports(session):
    """Create sample queued reports."""
    print("\nSeeding queued reports...")

    # Get actual template IDs
    templates = session.execute(text("SELECT id, name FROM report_templates ORDER BY id")).fetchall()
    if not templates:
        print("  No templates found, skipping queued reports")
        return
    tid_map = {t[1]: t[0] for t in templates}
    perf_id = tid_map.get("Property Performance Summary", templates[0][0])
    pipeline_id = tid_map.get("Deal Pipeline Report", templates[2][0] if len(templates) > 2 else templates[0][0])

    now = datetime.now(UTC)
    reports = [
        QueuedReport(
            template_id=perf_id,
            name="Q4 2025 Portfolio Overview",
            status=ReportStatus.COMPLETED,
            requested_by="matt@bandrcapital.com",
            requested_at=now - timedelta(days=7),
            completed_at=now - timedelta(days=7, hours=-1),
        ),
        QueuedReport(
            template_id=pipeline_id,
            name="January 2026 Deal Pipeline",
            status=ReportStatus.COMPLETED,
            requested_by="matt@bandrcapital.com",
            requested_at=now - timedelta(days=2),
            completed_at=now - timedelta(days=2, hours=-1),
        ),
        QueuedReport(
            template_id=perf_id,
            name="Cabana on 99th Performance",
            status=ReportStatus.PENDING,
            requested_by="matt@bandrcapital.com",
            requested_at=now,
        ),
    ]
    session.add_all(reports)
    session.commit()
    print(f"  Created {len(reports)} queued reports")


def seed_distribution_schedules(session):
    """Create distribution schedules for closed deals."""
    print("\nSeeding distribution schedules...")

    # Get actual template IDs
    templates = session.execute(text("SELECT id, name FROM report_templates ORDER BY id")).fetchall()
    tid_map = {t[1]: t[0] for t in templates}
    investor_tid = tid_map.get("Investor Distribution Report", templates[-1][0] if templates else 1)
    portfolio_tid = tid_map.get("Portfolio Overview", templates[1][0] if len(templates) > 1 else 1)
    pipeline_tid = tid_map.get("Deal Pipeline Report", templates[2][0] if len(templates) > 2 else 1)

    schedules = [
        DistributionSchedule(
            name="Cabana on 99th Quarterly Distribution",
            frequency=ScheduleFrequency.QUARTERLY,
            template_id=investor_tid,
            recipients=["investors@bandrcapital.com", "accounting@bandrcapital.com"],
            next_scheduled=datetime(2026, 4, 1, tzinfo=UTC),
            is_active=True,
            time="08:00",
        ),
        DistributionSchedule(
            name="Tempe Metro Quarterly Distribution",
            frequency=ScheduleFrequency.QUARTERLY,
            template_id=investor_tid,
            recipients=["investors@bandrcapital.com", "accounting@bandrcapital.com"],
            next_scheduled=datetime(2026, 4, 1, tzinfo=UTC),
            is_active=True,
            time="08:00",
        ),
        DistributionSchedule(
            name="Monthly Portfolio Summary",
            frequency=ScheduleFrequency.MONTHLY,
            template_id=portfolio_tid,
            recipients=["matt@bandrcapital.com"],
            next_scheduled=datetime(2026, 3, 1, tzinfo=UTC),
            is_active=True,
            time="07:00",
        ),
        DistributionSchedule(
            name="Weekly Deal Pipeline Update",
            frequency=ScheduleFrequency.WEEKLY,
            template_id=pipeline_tid,
            recipients=["matt@bandrcapital.com", "sarah@bandrcapital.com"],
            next_scheduled=datetime(2026, 2, 10, tzinfo=UTC),
            is_active=True,
            time="09:00",
        ),
    ]
    session.add_all(schedules)
    session.commit()
    print(f"  Created {len(schedules)} distribution schedules")


def link_extracted_values_to_properties(session, property_map: dict[str, int]):
    """Update extracted_values.property_id to point to properties table."""
    print("\nLinking extracted_values to properties...")

    count = 0
    for deal_name, prop_id in property_map.items():
        result = session.execute(
            text("UPDATE extracted_values SET property_id = :pid WHERE property_name = :pname"),
            {"pid": prop_id, "pname": deal_name},
        )
        if result.rowcount > 0:
            count += result.rowcount

    session.commit()
    print(f"  Linked {count} extracted values to {len(property_map)} properties")


def main():
    """Run all seed functions."""
    print("=" * 60)
    print("Seeding database from extraction data")
    print("=" * 60)

    with SessionLocal() as session:
        clear_data(session)
        seed_users(session)
        property_map = seed_properties_from_extraction(session)
        seed_deals(session, property_map)
        seed_documents(session, property_map)
        seed_transactions(session, property_map)
        seed_report_templates(session)
        seed_queued_reports(session)
        seed_distribution_schedules(session)
        link_extracted_values_to_properties(session, property_map)

    print("\n" + "=" * 60)
    print("Database seeding complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
