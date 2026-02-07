"""
Database seeding script for B&R Capital Dashboard.

Creates realistic mock data for development and testing:
- Users (admin, analysts, investors)
- Properties (multifamily assets)
- Deals (various stages)
- Underwriting models with full assumptions and projections
"""

import asyncio
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from random import choice, randint, uniform

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.deal import Deal, DealStage
from app.models.property import Property
from app.models.underwriting import (
    AnnualCashflow,
    BudgetAssumptions,
    EquityReturns,
    ExitAssumptions,
    FinancingAssumptions,
    GeneralAssumptions,
    NOIAssumptions,
    PropertyReturns,
    RentComp,
    SalesComp,
    UnderwritingModel,
    UnderwritingStatus,
    UnitMix,
)
from app.models.user import User

# Database URL - use settings module (reads from environment variables)
DATABASE_URL = settings.database_url_async


# ============================================================================
# SAMPLE DATA GENERATORS
# ============================================================================

PROPERTY_NAMES = [
    "The Residences at Scottsdale Quarter",
    "Desert Ridge Apartments",
    "Tempe Gateway Lofts",
    "Chandler Heights Apartments",
    "Mesa Vista Townhomes",
    "Gilbert Crossing",
    "Phoenix Palms",
    "Camelback Terrace",
    "Arcadia Park Apartments",
    "Paradise Valley Estates",
]

MARKETS = ["Phoenix", "Tucson", "Las Vegas", "Denver", "Austin", "Dallas"]
STATES = ["AZ", "AZ", "NV", "CO", "TX", "TX"]
CITIES = ["Phoenix", "Tucson", "Las Vegas", "Denver", "Austin", "Dallas"]
SUBMARKETS = ["Central", "East", "West", "North", "South", "Downtown"]

UNIT_TYPES = ["Studio", "1BR/1BA", "2BR/1BA", "2BR/2BA", "3BR/2BA"]
COMP_NAMES = [
    "Comparable A",
    "Comparable B",
    "Comparable C",
    "Market Leader",
    "Recent Build",
    "Nearby Community",
]


def random_decimal(min_val: float, max_val: float, precision: int = 2) -> Decimal:
    """Generate a random Decimal within range."""
    return Decimal(str(round(uniform(min_val, max_val), precision)))


def random_date(days_back: int = 365) -> date:
    """Generate a random date within the past N days."""
    delta = timedelta(days=randint(0, days_back))
    return date.today() - delta


# ============================================================================
# USER SEEDING
# ============================================================================


async def seed_users(session: AsyncSession) -> list[User]:
    """Create sample users."""
    users_data = [
        {
            "email": "admin@bandrcapital.com",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4QwNOdIzQlKZ7CZa",  # password123
            "full_name": "System Administrator",
            "is_active": True,
            "is_verified": True,
            "role": "admin",
            "department": "Technology",
        },
        {
            "email": "analyst@bandrcapital.com",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4QwNOdIzQlKZ7CZa",
            "full_name": "Senior Analyst",
            "is_active": True,
            "is_verified": True,
            "role": "analyst",
            "department": "Acquisitions",
        },
        {
            "email": "investor@bandrcapital.com",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4QwNOdIzQlKZ7CZa",
            "full_name": "LP Investor",
            "is_active": True,
            "is_verified": True,
            "role": "viewer",
            "department": "Investors",
        },
    ]

    users = []
    for user_data in users_data:
        user = User(**user_data)
        session.add(user)
        users.append(user)

    await session.flush()
    print(f"✅ Created {len(users)} users")
    return users


# ============================================================================
# PROPERTY SEEDING
# ============================================================================


async def seed_properties(session: AsyncSession) -> list[Property]:
    """Create sample properties."""
    properties = []

    for i, name in enumerate(PROPERTY_NAMES):
        market_idx = i % len(MARKETS)
        prop = Property(
            name=name,
            address=f"{randint(100, 9999)} E. Main Street",
            city=CITIES[market_idx],
            state=STATES[market_idx],
            zip_code=f"{randint(85000, 85999)}",
            market=MARKETS[market_idx],
            submarket=choice(SUBMARKETS),
            property_type="multifamily",
            year_built=randint(1985, 2022),
            total_units=randint(100, 400),
            total_sf=randint(80000, 400000),
            lot_size_acres=random_decimal(2.0, 15.0),
            parking_spaces=randint(100, 500),
            amenities={"features": ["Pool", "Fitness Center", "Clubhouse", "Dog Park"]},
        )
        session.add(prop)
        properties.append(prop)

    await session.flush()
    print(f"✅ Created {len(properties)} properties")
    return properties


# ============================================================================
# DEAL SEEDING
# ============================================================================


async def seed_deals(
    session: AsyncSession, properties: list[Property], users: list[User]
) -> list[Deal]:
    """Create sample deals."""
    deals = []
    stages = list(DealStage)

    for i, prop in enumerate(properties[:7]):  # Create deals for first 7 properties
        stage = stages[i % len(stages)]
        deal = Deal(
            name=f"{prop.name} Acquisition",
            property_id=prop.id,
            deal_type="acquisition",
            stage=stage,
            stage_order=i,
            assigned_user_id=users[1].id if len(users) > 1 else users[0].id,
            initial_contact_date=random_date(180)
            if stage in [DealStage.CLOSED, DealStage.LOI_SUBMITTED]
            else None,
            target_close_date=date.today() + timedelta(days=randint(30, 180)),
            asking_price=random_decimal(10_000_000, 50_000_000, 0),
            notes=f"Acquisition opportunity for {prop.name} in {prop.market}.",
            priority="medium",
        )
        session.add(deal)
        deals.append(deal)

    await session.flush()
    print(f"✅ Created {len(deals)} deals")
    return deals


# ============================================================================
# UNDERWRITING MODEL SEEDING
# ============================================================================


async def seed_underwriting_models(
    session: AsyncSession, deals: list[Deal], properties: list[Property]
) -> list[UnderwritingModel]:
    """Create underwriting models with all child tables."""
    models = []

    for deal in deals:
        prop = next(p for p in properties if p.id == deal.property_id)

        # Create main underwriting model
        uw_model = UnderwritingModel(
            name=f"UW Model - {deal.name}",
            deal_id=deal.id,
            property_id=prop.id,
            status=UnderwritingStatus.IN_PROGRESS,
            version=1,
            scenario_name="Base Case",
            description=f"Underwriting analysis for {deal.name}",
        )
        session.add(uw_model)
        await session.flush()

        # Seed all child tables
        await seed_general_assumptions(session, uw_model, deal, prop)
        await seed_exit_assumptions(session, uw_model)
        await seed_noi_assumptions(session, uw_model)
        await seed_financing_assumptions(session, uw_model, deal)
        await seed_budget_assumptions(session, uw_model)
        await seed_property_returns(session, uw_model)
        await seed_equity_returns(session, uw_model)
        await seed_unit_mix(session, uw_model, prop)
        await seed_rent_comps(session, uw_model)
        await seed_sales_comps(session, uw_model)
        await seed_annual_cashflows(session, uw_model, prop)

        models.append(uw_model)

    print(f"✅ Created {len(models)} underwriting models with all assumptions")
    return models


async def seed_general_assumptions(
    session: AsyncSession, uw: UnderwritingModel, deal: Deal, prop: Property
):
    """Create general assumptions for underwriting model."""
    assumptions = GeneralAssumptions(
        underwriting_model_id=uw.id,
        property_name=prop.name,
        property_street_address=prop.address,
        property_city=prop.city,
        property_state=prop.state,
        submarket=prop.submarket,
        year_built=prop.year_built,
        units=prop.total_units,
        total_sf=prop.total_sf,
        acquisition_date=deal.initial_contact_date or date.today(),
        analysis_date=date.today(),
    )
    session.add(assumptions)


async def seed_exit_assumptions(session: AsyncSession, uw: UnderwritingModel):
    """Create exit assumptions."""
    assumptions = ExitAssumptions(
        underwriting_model_id=uw.id,
        exit_cap_rate=random_decimal(4.5, 6.5, 2),
        exit_period_months=60,  # 5-year hold
        sales_transaction_costs=random_decimal(1.5, 2.5, 2),
    )
    session.add(assumptions)


async def seed_noi_assumptions(session: AsyncSession, uw: UnderwritingModel):
    """Create NOI assumptions."""
    base_rent_growth = random_decimal(0.02, 0.04, 4)  # 2-4% as decimal
    assumptions = NOIAssumptions(
        underwriting_model_id=uw.id,
        # Revenue assumptions
        rent_growth_year_1=base_rent_growth,
        rent_growth_year_2=base_rent_growth,
        rent_growth_year_3=base_rent_growth - Decimal("0.005"),
        rent_growth_year_4=base_rent_growth - Decimal("0.005"),
        rent_growth_year_5=base_rent_growth - Decimal("0.01"),
        loss_to_lease_pct=random_decimal(0.0, 0.05, 4),
        physical_vacancy_pct=random_decimal(0.04, 0.08, 4),
        bad_debt_pct=random_decimal(0.005, 0.02, 4),
        concessions_pct=random_decimal(0.0, 0.03, 4),
        # Expense assumptions
        expense_growth_rate=random_decimal(0.02, 0.035, 4),
        management_fee_pct=random_decimal(0.025, 0.04, 4),
        replacement_reserves_per_unit=Decimal("250.00"),
        insurance_per_unit=Decimal("450.00"),
        real_estate_taxes_per_unit=Decimal("1200.00"),
    )
    session.add(assumptions)


async def seed_financing_assumptions(
    session: AsyncSession, uw: UnderwritingModel, deal: Deal
):
    """Create financing assumptions."""
    purchase_price = deal.asking_price or Decimal("25000000")
    ltv = random_decimal(60, 75, 1)
    loan_amount = purchase_price * (ltv / 100)

    assumptions = FinancingAssumptions(
        underwriting_model_id=uw.id,
        senior_loan_amount=loan_amount,
        senior_ltv=ltv,
        senior_interest_rate=random_decimal(5.0, 7.5, 3),
        senior_term_months=120,  # 10 years
        senior_amortization_months=360,  # 30 years
        senior_io_period_months=randint(12, 36),
        senior_origination_fee_pct=random_decimal(0.5, 1.5, 2),
    )
    session.add(assumptions)


async def seed_budget_assumptions(session: AsyncSession, uw: UnderwritingModel):
    """Create budget/renovation assumptions."""
    assumptions = BudgetAssumptions(
        underwriting_model_id=uw.id,
        total_renovation_budget=random_decimal(1_000_000, 5_000_000, 0),
        interior_renovation_per_unit=random_decimal(8000, 15000, 0),
        exterior_renovation=random_decimal(200_000, 500_000, 0),
        amenity_improvements=random_decimal(100_000, 300_000, 0),
        renovation_contingency_pct=random_decimal(5, 10, 1),
    )
    session.add(assumptions)


async def seed_property_returns(session: AsyncSession, uw: UnderwritingModel):
    """Create property returns."""
    returns = PropertyReturns(
        underwriting_model_id=uw.id,
        going_in_cap_rate=random_decimal(4.5, 6.0, 2),
        exit_cap_rate=random_decimal(5.0, 6.5, 2),
        unlevered_irr=random_decimal(8.0, 12.0, 2),
        unlevered_equity_multiple=random_decimal(1.6, 2.2, 2),
        unlevered_cash_on_cash_avg=random_decimal(4.0, 8.0, 2),
    )
    session.add(returns)


async def seed_equity_returns(session: AsyncSession, uw: UnderwritingModel):
    """Create equity returns - single row with levered, LP, and GP returns."""
    returns = EquityReturns(
        underwriting_model_id=uw.id,
        # Overall levered returns (IRR as decimal, e.g., 0.18 = 18%)
        levered_irr=random_decimal(0.14, 0.22, 4),
        levered_equity_multiple=random_decimal(1.8, 2.5, 3),
        levered_cash_on_cash_year_1=random_decimal(0.05, 0.08, 4),
        levered_cash_on_cash_avg=random_decimal(0.06, 0.10, 4),
        # LP returns (Limited Partners)
        lp_irr=random_decimal(0.12, 0.18, 4),
        lp_equity_multiple=random_decimal(1.6, 2.2, 3),
        lp_total_distributions=random_decimal(8_000_000, 25_000_000, 2),
        lp_preferred_return=random_decimal(0.07, 0.09, 4),
        lp_profit_share=random_decimal(0.70, 0.85, 4),
        # GP returns (General Partner)
        gp_irr=random_decimal(0.18, 0.35, 4),
        gp_equity_multiple=random_decimal(2.0, 3.5, 3),
        gp_total_distributions=random_decimal(1_000_000, 5_000_000, 2),
        gp_promote_earned=random_decimal(500_000, 2_000_000, 2),
        gp_fees_earned=random_decimal(100_000, 500_000, 2),
        # Total investment/distribution metrics
        total_equity_invested=random_decimal(5_000_000, 20_000_000, 2),
        total_distributions=random_decimal(10_000_000, 35_000_000, 2),
        total_profit=random_decimal(3_000_000, 15_000_000, 2),
    )
    session.add(returns)


async def seed_unit_mix(session: AsyncSession, uw: UnderwritingModel, prop: Property):
    """Create unit mix entries."""
    total_units = prop.total_units or 200
    unit_distribution = [0.15, 0.35, 0.20, 0.20, 0.10]  # Distribution by type

    for i, unit_type in enumerate(UNIT_TYPES):
        unit_count = int(total_units * unit_distribution[i])
        beds = 0 if unit_type == "Studio" else int(unit_type[0])
        baths = 1 if beds <= 1 else 2
        avg_sf = 450 + (beds * 250)
        market_rent = 1200 + (beds * 350) + randint(-100, 100)

        unit = UnitMix(
            underwriting_model_id=uw.id,
            unit_type=unit_type,
            unit_count=unit_count,
            avg_sf=avg_sf,
            bedrooms=beds,
            bathrooms=Decimal(str(baths)),
            in_place_rent=Decimal(str(market_rent - randint(50, 150))),
            market_rent=Decimal(str(market_rent)),
            proforma_rent=Decimal(str(market_rent + randint(100, 250))),
        )
        session.add(unit)


async def seed_rent_comps(session: AsyncSession, uw: UnderwritingModel):
    """Create rent comparable entries."""
    for i, name in enumerate(COMP_NAMES[:4]):
        comp = RentComp(
            underwriting_model_id=uw.id,
            property_name=name,
            property_address=f"{randint(100, 9999)} W. Test Ave",
            distance_miles=random_decimal(0.5, 5.0, 1),
            year_built=randint(2000, 2022),
            total_units=randint(150, 350),
            occupancy_pct=random_decimal(92, 98, 1),
            one_br_rent=random_decimal(1200, 1800, 0),
            two_br_rent=random_decimal(1500, 2200, 0),
            avg_rent_per_sf=random_decimal(1.5, 2.5, 2),
            asset_class="A" if i < 2 else "B",
        )
        session.add(comp)


async def seed_sales_comps(session: AsyncSession, uw: UnderwritingModel):
    """Create sales comparable entries."""
    for i, name in enumerate(COMP_NAMES[:3]):
        sale_price = random_decimal(15_000_000, 45_000_000, 0)
        units = randint(150, 350)
        comp = SalesComp(
            underwriting_model_id=uw.id,
            property_name=f"{name} - Sale",
            property_address=f"{randint(100, 9999)} N. Sale Blvd",
            sale_date=random_date(365),
            sale_price=sale_price,
            price_per_unit=sale_price / units,
            cap_rate=random_decimal(4.5, 6.0, 2),
            total_units=units,
            year_built=randint(1995, 2020),
            occupancy_at_sale=random_decimal(90, 98, 1),
        )
        session.add(comp)


async def seed_annual_cashflows(
    session: AsyncSession, uw: UnderwritingModel, prop: Property
):
    """Create annual cashflow projections for 5 years."""
    units = prop.total_units or 200
    base_rent = units * 1500 * 12  # Annual GPR

    for year in range(1, 6):
        growth = 1 + (0.03 * (year - 1))  # 3% annual growth
        gpr = Decimal(str(int(base_rent * growth)))
        vacancy = gpr * Decimal("0.05")
        egi = gpr - vacancy
        expenses = egi * Decimal("0.40")
        noi = egi - expenses
        debt_service = noi * Decimal("0.65")
        cash_flow = noi - debt_service

        cashflow = AnnualCashflow(
            underwriting_model_id=uw.id,
            year_number=year,
            period_label=f"Year {year}",
            gross_potential_rent=gpr,
            vacancy_loss=vacancy,
            net_rental_income=gpr - vacancy,
            effective_gross_income=egi,
            total_operating_expenses=expenses,
            net_operating_income=noi,
            total_debt_service=debt_service,
            cash_flow_after_debt=cash_flow,
            dscr=noi / debt_service if debt_service > 0 else None,
            cash_on_cash_return=cash_flow / Decimal("5000000"),
        )
        session.add(cashflow)


# ============================================================================
# MAIN SEEDING FUNCTION
# ============================================================================


async def main():
    """Main seeding function."""
    print("=" * 60)
    print("🌱 B&R Capital Dashboard - Database Seeding")
    print("=" * 60)

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Create session factory
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Check if data already exists
            result = await session.execute(select(User).limit(1))
            if result.scalar_one_or_none():
                print("⚠️  Data already exists. Skipping seeding.")
                print(
                    "   Run 'alembic downgrade base && alembic upgrade head' to reset."
                )
                return

            # Seed in order of dependencies
            users = await seed_users(session)
            properties = await seed_properties(session)
            deals = await seed_deals(session, properties, users)
            await seed_underwriting_models(session, deals, properties)

            # Commit all changes
            await session.commit()

            print("=" * 60)
            print("✅ Database seeding completed successfully!")
            print("=" * 60)

        except Exception as e:
            await session.rollback()
            print(f"❌ Error during seeding: {e}")
            raise

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
