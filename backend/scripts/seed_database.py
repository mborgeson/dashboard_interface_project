"""
Seed the database with realistic multifamily real estate data.

Populates properties, deals, transactions, documents, report templates,
queued reports, distribution schedules, and users using property names
derived from the extracted_values table.

Usage:
    cd backend && python scripts/seed_database.py
"""

import json
import random
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add backend directory to sys.path so 'app' package is importable
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.base import Base
from app.db.session import SessionLocal, sync_engine
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
# Deduplicated property data from extraction table
# ---------------------------------------------------------------------------

# Map of canonical property name -> city (extracted from parenthetical suffixes
# or defaulted to a suitable Phoenix MSA city)
PROPERTY_DATA = {
    "454 W Brown Road": "Mesa",
    "505 West": "Tempe",
    "Acacia Pointe": "Glendale",
    "Alante at the Islands": "Chandler",
    "Alta Surprise": "Surprise",
    "Alta Vista Village": "Phoenix",
    "Ardella on 28th": "Phoenix",
    "Artisan at Downtown Chandler": "Chandler",
    "Aura at Midtown": "Phoenix",
    "Be Mesa": "Mesa",
    "Bingham Block": "Phoenix",
    "Broadstone 7th Street": "Phoenix",
    "Broadstone Portland": "Phoenix",
    "Buenas Paradise Valley": "Phoenix",
    "Cantala": "Glendale",
    "Cimarron": "Mesa",
    "Citra": "Phoenix",
    "Copper Point Apartments": "Mesa",
    "Coral Point": "Mesa",
    "Cortland Arrowhead Summit": "Glendale",
    "Emparrado": "Mesa",
    "Estrella Gateway": "Avondale",
    "Fringe Mountain View": "Phoenix",
    "Glen 91": "Glendale",
    "Harmony at Surprise": "Surprise",
    "Haven Townhomes at P83": "Peoria",
    "Hayden Park": "Scottsdale",
    "Jade Ridge": "Phoenix",
    "La Paloma": "Tempe",
    "Monterra": "Phoenix",
    "North Country Club": "Mesa",
    "Park on Bell": "Phoenix",
    "Town Center Apartments": "Tempe",
    "Tresa at Arrowhead": "Glendale",
    "Urban 148": "Phoenix",
}

# Submarket mapping by city
SUBMARKET_MAP = {
    "Phoenix": [
        "Phoenix - Central",
        "Phoenix - North",
        "Phoenix - Camelback Corridor",
        "Phoenix - Arcadia",
        "Phoenix - Midtown",
    ],
    "Tempe": ["Tempe - ASU Area", "Tempe - South", "Tempe - Downtown"],
    "Mesa": ["Mesa - East", "Mesa - West", "Mesa - Downtown"],
    "Chandler": ["Chandler - Downtown", "Chandler - South"],
    "Glendale": ["Glendale - West", "Glendale - Downtown"],
    "Scottsdale": ["Scottsdale - South", "Scottsdale - Old Town"],
    "Surprise": ["Surprise - West Valley"],
    "Avondale": ["Avondale - West Valley"],
    "Peoria": ["Peoria - P83 District"],
}

# Realistic Phoenix MSA zip codes by city
ZIP_CODES = {
    "Phoenix": ["85003", "85004", "85006", "85012", "85013", "85014", "85016", "85018"],
    "Tempe": ["85281", "85282", "85283", "85284"],
    "Mesa": ["85201", "85202", "85204", "85210", "85213"],
    "Chandler": ["85224", "85225", "85226", "85248"],
    "Glendale": ["85301", "85302", "85304", "85306"],
    "Scottsdale": ["85251", "85254", "85257"],
    "Surprise": ["85374", "85378", "85379"],
    "Avondale": ["85323", "85392"],
    "Peoria": ["85345", "85381", "85382"],
}

# Street name fragments for generating addresses
STREET_NAMES = [
    "N Central Ave",
    "E Camelback Rd",
    "W Indian School Rd",
    "S Mill Ave",
    "E University Dr",
    "N Scottsdale Rd",
    "W Bell Rd",
    "E McDowell Rd",
    "N 7th St",
    "W Glendale Ave",
    "E Baseline Rd",
    "N Hayden Rd",
    "W Thomas Rd",
    "E Broadway Rd",
    "S Price Rd",
    "N Litchfield Rd",
    "W Peoria Ave",
    "E Southern Ave",
    "N 44th St",
    "W Thunderbird Rd",
]

random.seed(42)  # Reproducible output


def random_date(start: date, end: date) -> date:
    """Return a random date between start and end inclusive."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def random_decimal(low: float, high: float, precision: int = 2) -> Decimal:
    """Return a random Decimal between low and high."""
    val = random.uniform(low, high)
    return Decimal(str(round(val, precision)))


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


def seed_users(db):
    """Create two users: admin and analyst."""
    print("  Seeding users...")
    users = [
        User(
            email="matt@brcapital.com",
            hashed_password="hashed_placeholder",
            full_name="Matt Brennan",
            role="admin",
            is_active=True,
            is_verified=True,
            department="Acquisitions",
        ),
        User(
            email="sarah@brcapital.com",
            hashed_password="hashed_placeholder",
            full_name="Sarah Chen",
            role="analyst",
            is_active=True,
            is_verified=True,
            department="Asset Management",
        ),
    ]
    db.add_all(users)
    db.commit()
    print(f"    Created {len(users)} users.")
    return users


def seed_properties(db):
    """Create properties from the deduplicated extraction data."""
    print("  Seeding properties...")
    properties = []
    for name, city in PROPERTY_DATA.items():
        units = random.randint(100, 400)
        avg_sf_per_unit = random.randint(750, 1050)
        total_sf = units * avg_sf_per_unit
        avg_rent = random_decimal(1200, 2100)
        occupancy = random_decimal(92.0, 97.0)
        annual_revenue = float(avg_rent) * units * 12
        noi = Decimal(str(round(annual_revenue * random.uniform(0.50, 0.60), 2)))
        purchase_price = random_decimal(15_000_000, 85_000_000)
        cap_rate = (noi / purchase_price * 100).quantize(Decimal("0.001"))
        # Clamp cap rate to realistic range
        if cap_rate < Decimal("4.0"):
            cap_rate = random_decimal(4.5, 5.5, 3)
        elif cap_rate > Decimal("7.0"):
            cap_rate = random_decimal(5.5, 6.5, 3)
        appreciation = random_decimal(1.05, 1.20)
        current_value = (purchase_price * appreciation).quantize(Decimal("0.01"))

        acq_date = random_date(date(2020, 1, 1), date(2024, 6, 30))
        year_built = random.randint(1985, 2023)
        submarkets = SUBMARKET_MAP.get(city, [f"{city}"])
        zips = ZIP_CODES.get(city, ["85001"])
        address_num = random.randint(100, 9999)
        street = random.choice(STREET_NAMES)

        prop = Property(
            name=name,
            property_type="multifamily",
            address=f"{address_num} {street}",
            city=city,
            state="AZ",
            zip_code=random.choice(zips),
            county="Maricopa",
            market="Phoenix MSA",
            submarket=random.choice(submarkets),
            year_built=year_built,
            total_units=units,
            total_sf=total_sf,
            purchase_price=purchase_price,
            current_value=current_value,
            acquisition_date=acq_date,
            occupancy_rate=occupancy,
            avg_rent_per_unit=avg_rent,
            noi=noi,
            cap_rate=cap_rate,
        )
        properties.append(prop)

    db.add_all(properties)
    db.commit()
    print(f"    Created {len(properties)} properties.")
    return properties


def seed_deals(db, properties):
    """Create ~20 deals distributed across pipeline stages."""
    print("  Seeding deals...")
    stages = list(DealStage)
    sources = ["Broker", "Off-market", "Auction", "Direct", "JV Partner"]
    priorities = ["low", "medium", "high", "urgent"]

    # Pick a subset of properties for deals
    deal_props = random.sample(properties, min(20, len(properties)))
    deals = []
    for i, prop in enumerate(deal_props):
        stage = stages[i % len(stages)]
        asking = prop.purchase_price * random_decimal(0.95, 1.10)
        offer = asking * random_decimal(0.90, 1.00)
        hold = random.randint(3, 7)
        irr = random_decimal(12.0, 22.0, 3)
        coc = random_decimal(6.0, 12.0, 3)
        em = random_decimal(1.50, 2.50)

        suffix_map = {
            DealStage.LEAD: "Lead",
            DealStage.INITIAL_REVIEW: "Review",
            DealStage.UNDERWRITING: "Underwriting",
            DealStage.DUE_DILIGENCE: "Due Diligence",
            DealStage.LOI_SUBMITTED: "LOI",
            DealStage.UNDER_CONTRACT: "Contract",
            DealStage.CLOSED: "Acquisition",
            DealStage.DEAD: "Passed",
        }

        deal = Deal(
            name=f"{prop.name} {suffix_map.get(stage, 'Acquisition')}",
            deal_type="acquisition",
            stage=stage,
            stage_order=i,
            property_id=prop.id,
            asking_price=asking.quantize(Decimal("0.01")),
            offer_price=offer.quantize(Decimal("0.01")),
            projected_irr=irr,
            projected_coc=coc,
            projected_equity_multiple=em,
            hold_period_years=hold,
            source=random.choice(sources),
            priority=random.choice(priorities),
            initial_contact_date=random_date(date(2023, 1, 1), date(2024, 12, 31)),
            notes=f"Potential {prop.total_units}-unit acquisition in {prop.city}.",
        )
        deals.append(deal)

    db.add_all(deals)
    db.commit()
    print(f"    Created {len(deals)} deals.")
    return deals


def seed_transactions(db, properties):
    """Create ~60 transactions: acquisitions, distributions, capex, refinances."""
    print("  Seeding transactions...")
    transactions = []

    for prop in properties:
        # 1) Acquisition transaction matching property purchase
        transactions.append(
            Transaction(
                property_id=prop.id,
                property_name=prop.name,
                type="acquisition",
                category="Purchase",
                amount=prop.purchase_price or Decimal("0"),
                date=prop.acquisition_date or date(2022, 1, 1),
                description=f"Acquisition of {prop.name}, {prop.total_units} units in {prop.city}, AZ.",
            )
        )

    # Pick a subset for quarterly distributions (2 quarters each)
    dist_props = random.sample(properties, min(10, len(properties)))
    for prop in dist_props:
        base_date = prop.acquisition_date or date(2022, 6, 1)
        for q in range(1, 3):
            dist_date = base_date + timedelta(days=90 * q)
            dist_amount = random_decimal(50_000, 250_000)
            transactions.append(
                Transaction(
                    property_id=prop.id,
                    property_name=prop.name,
                    type="distribution",
                    category="Quarterly Distribution",
                    amount=dist_amount,
                    date=dist_date,
                    description=f"Q{q} distribution for {prop.name}.",
                )
            )

    # Capital improvements on a handful of properties
    capex_props = random.sample(properties, min(8, len(properties)))
    capex_categories = [
        ("Unit Renovation", 500_000, 2_000_000),
        ("Exterior Improvements", 200_000, 800_000),
        ("Common Area Upgrades", 100_000, 500_000),
        ("HVAC Replacement", 150_000, 600_000),
        ("Roof Replacement", 250_000, 900_000),
    ]
    for prop in capex_props:
        cat_name, lo, hi = random.choice(capex_categories)
        capex_date = random_date(date(2021, 1, 1), date(2024, 12, 31))
        transactions.append(
            Transaction(
                property_id=prop.id,
                property_name=prop.name,
                type="capital_improvement",
                category=cat_name,
                amount=random_decimal(lo, hi),
                date=capex_date,
                description=f"{cat_name} at {prop.name}.",
            )
        )

    # A couple of refinances
    refi_props = random.sample(properties, min(3, len(properties)))
    for prop in refi_props:
        refi_date = random_date(date(2022, 6, 1), date(2024, 12, 31))
        refi_amount = (prop.purchase_price or Decimal("30000000")) * random_decimal(
            0.60, 0.75
        )
        transactions.append(
            Transaction(
                property_id=prop.id,
                property_name=prop.name,
                type="refinance",
                category="Refinance",
                amount=refi_amount.quantize(Decimal("0.01")),
                date=refi_date,
                description=f"Refinance of {prop.name} loan.",
            )
        )

    db.add_all(transactions)
    db.commit()
    print(f"    Created {len(transactions)} transactions.")
    return transactions


def seed_documents(db, properties):
    """Create ~40 documents across property types."""
    print("  Seeding documents...")
    doc_templates = [
        ("financial", "Q{q} Financial Report - {name}", ["financial", "quarterly"]),
        ("lease", "Lease Agreement - {name}", ["lease", "legal"]),
        ("legal", "Purchase Agreement - {name}", ["legal", "acquisition"]),
        ("due_diligence", "Phase I ESA - {name}", ["environmental", "due-diligence"]),
        ("due_diligence", "Property Inspection Report - {name}", ["inspection", "due-diligence"]),
        ("financial", "Rent Roll - {name}", ["rent-roll", "financial"]),
        ("financial", "T-12 Operating Statement - {name}", ["t-12", "financial"]),
        ("legal", "Title Report - {name}", ["title", "legal"]),
    ]

    documents = []
    doc_props = random.sample(properties, min(20, len(properties)))
    for prop in doc_props:
        # 2 documents per selected property
        chosen = random.sample(doc_templates, min(2, len(doc_templates)))
        for doc_type, name_tpl, tags in chosen:
            q = random.randint(1, 4)
            doc_name = name_tpl.format(q=q, name=prop.name)
            uploaded = datetime(
                random.randint(2022, 2024),
                random.randint(1, 12),
                random.randint(1, 28),
                random.randint(8, 17),
                random.randint(0, 59),
                tzinfo=UTC,
            )
            documents.append(
                Document(
                    name=doc_name,
                    type=doc_type,
                    property_id=str(prop.id),
                    property_name=prop.name,
                    size=random.randint(50_000, 15_000_000),
                    uploaded_at=uploaded,
                    uploaded_by=random.choice(
                        ["matt@brcapital.com", "sarah@brcapital.com"]
                    ),
                    description=f"{doc_type.replace('_', ' ').title()} document for {prop.name}.",
                    tags=tags,
                )
            )

    db.add_all(documents)
    db.commit()
    print(f"    Created {len(documents)} documents.")
    return documents


def seed_report_templates(db):
    """Create 5 report templates."""
    print("  Seeding report templates...")
    templates = [
        ReportTemplate(
            name="Executive Portfolio Summary",
            description="High-level overview of portfolio performance, key metrics, and investment highlights.",
            category=ReportCategory.EXECUTIVE,
            sections=[
                "Portfolio Overview",
                "Key Metrics",
                "Performance Summary",
                "Market Outlook",
            ],
            export_formats=["pdf", "pptx"],
            is_default=True,
            created_by="matt@brcapital.com",
        ),
        ReportTemplate(
            name="Financial Performance Report",
            description="Detailed financial analysis including NOI, cash flow, and return metrics.",
            category=ReportCategory.FINANCIAL,
            sections=[
                "Income Statement",
                "Cash Flow Analysis",
                "NOI Trends",
                "Debt Service Coverage",
                "Return Metrics",
            ],
            export_formats=["pdf", "excel"],
            is_default=True,
            created_by="sarah@brcapital.com",
        ),
        ReportTemplate(
            name="Market Analysis Report",
            description="Phoenix MSA market conditions, rent trends, and supply pipeline.",
            category=ReportCategory.MARKET,
            sections=[
                "Market Overview",
                "Rent Trends",
                "Occupancy Trends",
                "Supply Pipeline",
                "Demographic Data",
            ],
            export_formats=["pdf"],
            is_default=False,
            created_by="matt@brcapital.com",
        ),
        ReportTemplate(
            name="Portfolio Allocation Report",
            description="Asset allocation, geographic distribution, and diversification analysis.",
            category=ReportCategory.PORTFOLIO,
            sections=[
                "Asset Allocation",
                "Geographic Distribution",
                "Vintage Diversification",
                "Risk Analysis",
            ],
            export_formats=["pdf", "excel", "pptx"],
            is_default=False,
            created_by="matt@brcapital.com",
        ),
        ReportTemplate(
            name="Custom Deal Pipeline Report",
            description="Current deal pipeline status with projected returns and timelines.",
            category=ReportCategory.CUSTOM,
            sections=[
                "Pipeline Summary",
                "Stage Breakdown",
                "Projected Returns",
                "Timeline",
            ],
            export_formats=["pdf", "excel"],
            is_default=False,
            created_by="sarah@brcapital.com",
        ),
    ]
    db.add_all(templates)
    db.commit()
    print(f"    Created {len(templates)} report templates.")
    return templates


def seed_queued_reports(db, templates):
    """Create 6 queued reports in various statuses."""
    print("  Seeding queued reports...")
    now = datetime.now(UTC)
    queued = [
        QueuedReport(
            name="Q4 2024 Executive Summary",
            template_id=templates[0].id,
            status=ReportStatus.COMPLETED,
            progress=100,
            format=ReportFormat.PDF,
            requested_by="matt@brcapital.com",
            requested_at=now - timedelta(days=5),
            completed_at=now - timedelta(days=5, hours=-1),
            file_size="2.4 MB",
            download_url="/api/v1/reports/downloads/q4-2024-exec-summary.pdf",
        ),
        QueuedReport(
            name="January 2025 Financial Report",
            template_id=templates[1].id,
            status=ReportStatus.COMPLETED,
            progress=100,
            format=ReportFormat.EXCEL,
            requested_by="sarah@brcapital.com",
            requested_at=now - timedelta(days=3),
            completed_at=now - timedelta(days=3, hours=-1),
            file_size="5.1 MB",
            download_url="/api/v1/reports/downloads/jan-2025-financial.xlsx",
        ),
        QueuedReport(
            name="Phoenix MSA Market Analysis",
            template_id=templates[2].id,
            status=ReportStatus.GENERATING,
            progress=65,
            format=ReportFormat.PDF,
            requested_by="matt@brcapital.com",
            requested_at=now - timedelta(hours=2),
        ),
        QueuedReport(
            name="Portfolio Allocation Q1 2025",
            template_id=templates[3].id,
            status=ReportStatus.PENDING,
            progress=0,
            format=ReportFormat.PPTX,
            requested_by="matt@brcapital.com",
            requested_at=now - timedelta(hours=1),
        ),
        QueuedReport(
            name="Deal Pipeline - February 2025",
            template_id=templates[4].id,
            status=ReportStatus.PENDING,
            progress=0,
            format=ReportFormat.PDF,
            requested_by="sarah@brcapital.com",
            requested_at=now - timedelta(minutes=30),
        ),
        QueuedReport(
            name="Year-End 2024 Financial Report",
            template_id=templates[1].id,
            status=ReportStatus.FAILED,
            progress=42,
            format=ReportFormat.PDF,
            requested_by="matt@brcapital.com",
            requested_at=now - timedelta(days=10),
            error="Timeout: data aggregation exceeded 120s limit.",
        ),
    ]
    db.add_all(queued)
    db.commit()
    print(f"    Created {len(queued)} queued reports.")
    return queued


def seed_distribution_schedules(db, templates):
    """Create 4 distribution schedules."""
    print("  Seeding distribution schedules...")
    now = datetime.now(UTC)
    schedules = [
        DistributionSchedule(
            name="Weekly Executive Summary",
            template_id=templates[0].id,
            recipients=[
                "matt@brcapital.com",
                "investors@brcapital.com",
            ],
            frequency=ScheduleFrequency.WEEKLY,
            day_of_week=1,  # Monday
            time="08:00",
            format=ReportFormat.PDF,
            is_active=True,
            next_scheduled=now + timedelta(days=(7 - now.weekday()) % 7 or 7),
        ),
        DistributionSchedule(
            name="Monthly Financial Report",
            template_id=templates[1].id,
            recipients=[
                "matt@brcapital.com",
                "sarah@brcapital.com",
                "accounting@brcapital.com",
            ],
            frequency=ScheduleFrequency.MONTHLY,
            day_of_month=1,
            time="06:00",
            format=ReportFormat.EXCEL,
            is_active=True,
            next_scheduled=datetime(now.year, now.month % 12 + 1, 1, 6, 0, tzinfo=UTC),
        ),
        DistributionSchedule(
            name="Quarterly Market Report",
            template_id=templates[2].id,
            recipients=[
                "matt@brcapital.com",
                "research@brcapital.com",
            ],
            frequency=ScheduleFrequency.QUARTERLY,
            day_of_month=15,
            time="09:00",
            format=ReportFormat.PDF,
            is_active=True,
            next_scheduled=datetime(2025, 4, 15, 9, 0, tzinfo=UTC),
        ),
        DistributionSchedule(
            name="Daily Deal Pipeline Update",
            template_id=templates[4].id,
            recipients=[
                "matt@brcapital.com",
                "sarah@brcapital.com",
            ],
            frequency=ScheduleFrequency.DAILY,
            time="07:30",
            format=ReportFormat.PDF,
            is_active=False,
            next_scheduled=now + timedelta(days=1),
        ),
    ]
    db.add_all(schedules)
    db.commit()
    print(f"    Created {len(schedules)} distribution schedules.")
    return schedules


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("  Database Seed Script")
    print("=" * 60)

    # Create tables if they do not exist
    print("\nEnsuring tables exist...")
    Base.metadata.create_all(bind=sync_engine)
    print("  Done.")

    db = SessionLocal()
    try:
        # Idempotency check: skip if data already present
        existing_properties = db.query(Property).count()
        if existing_properties > 0:
            print(
                f"\nDatabase already contains {existing_properties} properties. "
                "Skipping seed to avoid duplicates."
            )
            print("To re-seed, truncate the tables first.\n")
            return

        print("\nSeeding database with realistic data...\n")

        users = seed_users(db)
        properties = seed_properties(db)
        deals = seed_deals(db, properties)
        transactions = seed_transactions(db, properties)
        documents = seed_documents(db, properties)
        templates = seed_report_templates(db)
        queued = seed_queued_reports(db, templates)
        schedules = seed_distribution_schedules(db, templates)

        print("\n" + "=" * 60)
        print("  Seed Summary")
        print("=" * 60)
        print(f"  Users:                  {len(users)}")
        print(f"  Properties:             {len(properties)}")
        print(f"  Deals:                  {len(deals)}")
        print(f"  Transactions:           {len(transactions)}")
        print(f"  Documents:              {len(documents)}")
        print(f"  Report Templates:       {len(templates)}")
        print(f"  Queued Reports:         {len(queued)}")
        print(f"  Distribution Schedules: {len(schedules)}")
        print("=" * 60)
        print("  Seeding complete!\n")

    except Exception as e:
        db.rollback()
        print(f"\nError during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
