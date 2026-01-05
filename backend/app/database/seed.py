"""
Database seeding module for B&R Capital Dashboard.
Provides mock data for development and testing environments.

Usage:
    python -m app.database.seed           # Seed database with mock data
    python -m app.database.seed --clear   # Clear all seeded data
"""

import asyncio
import sys
from datetime import date, timedelta
from decimal import Decimal
import random
from loguru import logger

from sqlalchemy import select, delete

from app.db.session import AsyncSessionLocal
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import User, Property, Deal, DealStage


# =============================================================================
# Sample Data Generators
# =============================================================================


def generate_property_data() -> list[dict]:
    """Generate sample property data matching Property model fields."""
    # Must match schema pattern: multifamily|office|retail|industrial|mixed_use|other
    property_types = [
        "multifamily",
        "office",
        "retail",
        "industrial",
        "mixed_use",
        "other",
    ]

    # Market data: city, state, zip_code prefix
    markets = [
        ("Phoenix", "AZ", "850"),
        ("Los Angeles", "CA", "900"),
        ("Dallas", "TX", "752"),
        ("Denver", "CO", "802"),
        ("Atlanta", "GA", "303"),
        ("Chicago", "IL", "606"),
        ("Miami", "FL", "331"),
        ("Seattle", "WA", "981"),
        ("Austin", "TX", "787"),
        ("Nashville", "TN", "372"),
        ("Charlotte", "NC", "282"),
        ("Tampa", "FL", "336"),
    ]

    street_names = [
        "Main",
        "Oak",
        "Commerce",
        "Industrial",
        "Business",
        "Park",
        "First",
        "Market",
    ]
    street_types = ["St", "Ave", "Blvd", "Dr", "Way", "Pkwy"]

    properties = []
    for i in range(1, 26):  # 25 sample properties
        prop_type = random.choice(property_types)
        city, state, zip_prefix = random.choice(markets)

        # Generate realistic pricing based on property type
        base_price = {
            "multifamily": 25_000_000,
            "office": 15_000_000,
            "retail": 8_000_000,
            "industrial": 12_000_000,
            "mixed_use": 20_000_000,
            "other": 18_000_000,
        }[prop_type]

        purchase_price = base_price * random.uniform(0.5, 2.5)
        total_sf = int(purchase_price / random.uniform(150, 350))
        total_units = (
            int(total_sf / random.uniform(800, 1200))
            if prop_type == "multifamily"
            else None
        )

        properties.append(
            {
                "name": f"{city} {prop_type.title()} {i}",
                "property_type": prop_type,
                "address": f"{random.randint(100, 9999)} {random.choice(street_names)} {random.choice(street_types)}",
                "city": city,
                "state": state,
                "zip_code": f"{zip_prefix}{random.randint(10, 99)}",
                "market": f"{city} Metro",
                "year_built": random.randint(1980, 2023),
                "total_sf": total_sf,
                "total_units": total_units,
                "purchase_price": Decimal(str(round(purchase_price, 2))),
                "cap_rate": Decimal(str(round(random.uniform(4.5, 8.5), 3))),
                "occupancy_rate": Decimal(str(round(random.uniform(75, 98), 2))),
            }
        )

    return properties


def generate_deal_data(user_ids: list[int]) -> list[dict]:
    """
    Generate sample deal pipeline data matching Deal model fields.

    Args:
        user_ids: List of user IDs to assign deals to
    """
    stages = list(DealStage)
    deal_types = ["acquisition", "disposition", "refinance", "development"]
    sources = [
        "Broker",
        "Off-market",
        "CBRE",
        "JLL",
        "Cushman & Wakefield",
        "Marcus & Millichap",
    ]

    deals = []
    for i in range(1, 31):  # 30 sample deals
        stage = random.choice(stages)
        days_offset = random.randint(-90, 0)

        # Generate realistic pricing
        asking_price = Decimal(str(round(random.uniform(5_000_000, 100_000_000), 2)))

        deals.append(
            {
                "name": f"Deal #{i:04d} - {random.choice(['Downtown', 'Suburban', 'Urban', 'Metro'])} {random.choice(['Acquisition', 'Portfolio', 'Development'])}",
                "deal_type": random.choice(deal_types),
                "stage": stage,
                "stage_order": random.randint(0, 10),
                "assigned_user_id": random.choice(user_ids) if user_ids else None,
                "asking_price": asking_price,
                "offer_price": Decimal(
                    str(round(float(asking_price) * random.uniform(0.85, 0.98), 2))
                ),
                "projected_irr": Decimal(str(round(random.uniform(12.0, 25.0), 3))),
                "projected_coc": Decimal(str(round(random.uniform(6.0, 12.0), 3))),
                "projected_equity_multiple": Decimal(
                    str(round(random.uniform(1.5, 2.5), 2))
                ),
                "hold_period_years": random.randint(3, 10),
                "initial_contact_date": date.today() + timedelta(days=days_offset),
                "target_close_date": date.today()
                + timedelta(days=random.randint(30, 180)),
                "source": random.choice(sources),
                "priority": random.choice(["low", "medium", "high", "urgent"]),
                "competition_level": random.choice(["low", "medium", "high"]),
            }
        )

    return deals


def generate_user_data() -> list[dict]:
    """Generate sample user data matching User model fields."""

    # Default password for all seed users
    default_password = get_password_hash("Password123!")

    users = [
        {
            "email": "admin@brcapital.com",
            "hashed_password": default_password,
            "full_name": "Admin User",
            "role": "admin",
            "is_active": True,
            "is_verified": True,
            "department": "Executive",
        },
        {
            "email": "john.smith@brcapital.com",
            "hashed_password": default_password,
            "full_name": "John Smith",
            "role": "analyst",
            "is_active": True,
            "is_verified": True,
            "department": "Acquisitions",
        },
        {
            "email": "jane.doe@brcapital.com",
            "hashed_password": default_password,
            "full_name": "Jane Doe",
            "role": "analyst",
            "is_active": True,
            "is_verified": True,
            "department": "Underwriting",
        },
        {
            "email": "mike.johnson@brcapital.com",
            "hashed_password": default_password,
            "full_name": "Mike Johnson",
            "role": "analyst",
            "is_active": True,
            "is_verified": True,
            "department": "Asset Management",
        },
        {
            "email": "sarah.wilson@brcapital.com",
            "hashed_password": default_password,
            "full_name": "Sarah Wilson",
            "role": "admin",
            "is_active": True,
            "is_verified": True,
            "department": "Executive",
        },
        {
            "email": "demo@brcapital.com",
            "hashed_password": default_password,
            "full_name": "Demo User",
            "role": "viewer",
            "is_active": True,
            "is_verified": True,
            "department": "Guest",
        },
    ]

    return users


# =============================================================================
# Seeding Functions
# =============================================================================


async def seed_database(clear_first: bool = False) -> None:
    """
    Seed the database with mock data.

    Args:
        clear_first: If True, clear existing data before seeding
    """
    logger.info("Starting database seeding...")

    if settings.ENVIRONMENT == "production":
        logger.error("Cannot seed database in production environment!")
        return

    async with AsyncSessionLocal() as session:
        try:
            if clear_first:
                await clear_database()

            # Check if data already exists
            existing_users = await session.execute(select(User).limit(1))
            if existing_users.scalar_one_or_none():
                logger.warning("Database already contains data. Use --clear to reset.")
                return

            # Generate and insert users first (needed for deal assignments)
            user_data = generate_user_data()
            users = []
            for data in user_data:
                user = User(**data)
                session.add(user)
                users.append(user)

            await session.flush()  # Get IDs assigned
            user_ids = [u.id for u in users]
            logger.info(f"Created {len(users)} users")

            # Generate and insert properties
            property_data = generate_property_data()
            for data in property_data:
                prop = Property(**data)
                session.add(prop)
            logger.info(f"Created {len(property_data)} properties")

            # Generate and insert deals
            deal_data = generate_deal_data(user_ids)
            for data in deal_data:
                deal = Deal(**data)
                session.add(deal)
            logger.info(f"Created {len(deal_data)} deals")

            await session.commit()
            logger.success("✅ Database seeding completed successfully!")

        except Exception as e:
            logger.error(f"Error seeding database: {e}")
            await session.rollback()
            raise


async def clear_database() -> None:
    """Clear all seeded data from the database."""
    logger.warning("Clearing database...")

    if settings.ENVIRONMENT == "production":
        logger.error("Cannot clear database in production environment!")
        return

    async with AsyncSessionLocal() as session:
        try:
            # Import underwriting models for deletion
            from app.models.underwriting.underwriting_model import UnderwritingModel

            # Delete in order respecting foreign key constraints
            # UnderwritingModel references Deal, so delete it first
            await session.execute(delete(UnderwritingModel))
            await session.execute(delete(Deal))
            await session.execute(delete(Property))
            await session.execute(delete(User))
            await session.commit()

            logger.success("✅ Database cleared successfully!")

        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            await session.rollback()
            raise


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """CLI entry point for database seeding."""
    clear_first = "--clear" in sys.argv

    if "--help" in sys.argv:
        print(__doc__)
        print("\nDefault credentials for seeded users:")
        print("  Email: admin@brcapital.com (or any seeded email)")
        print("  Password: Password123!")
        return

    asyncio.run(seed_database(clear_first=clear_first))


if __name__ == "__main__":
    main()
