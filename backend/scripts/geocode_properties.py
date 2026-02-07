#!/usr/bin/env python3
"""
One-time script to geocode properties with missing coordinates.
Uses Nominatim (OpenStreetMap) — free, no API key needed.
Respects rate limit of 1 request per second.

Usage:
    cd backend
    python -m scripts.geocode_properties
"""

import asyncio
import re
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import Property
from app.services.geocoding import geocode_with_fallback


async def main():
    """Geocode all properties with NULL latitude."""
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        async_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    else:
        async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(async_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Find properties with NULL or fallback (33.45, -112.07) coordinates
        from sqlalchemy import and_, or_

        result = await db.execute(
            select(Property).where(
                or_(
                    Property.latitude.is_(None),
                    and_(
                        Property.latitude == 33.45,
                        Property.longitude == -112.07,
                    ),
                )
            )
        )
        properties = result.scalars().all()

        print(f"Found {len(properties)} properties with missing coordinates")

        if not properties:
            print("Nothing to geocode.")
            return

        geocoded = 0
        failed = 0

        for prop in properties:
            # Parse city from name if needed (format: "Name (City, ST)")
            city = prop.city or ""
            state = prop.state or "AZ"
            street = prop.address or ""

            if not city and prop.name:
                m = re.search(r"\(([^,]+),\s*([A-Z]{2})\)", prop.name)
                if m:
                    city = m.group(1).strip()
                    state = m.group(2).strip()

            if not city:
                city = "Phoenix"

            # Clean placeholder values
            placeholders = {"[Year Built]", "Zip Code", "00000", "[County]"}
            if street in placeholders:
                street = ""
            if city in placeholders:
                city = "Phoenix"

            short_name = prop.name.split("(")[0].strip() if prop.name else ""

            print(f"  Geocoding: {prop.name} ({street}, {city}, {state})...", end=" ")

            coords = await geocode_with_fallback(
                property_name=prop.name or "",
                street=street or short_name,
                city=city,
                state=state,
                zip_code=prop.zip_code if prop.zip_code not in placeholders else None,
            )

            if coords:
                prop.latitude = coords[0]
                prop.longitude = coords[1]
                db.add(prop)
                print(f"OK -> ({coords[0]:.6f}, {coords[1]:.6f})")
                geocoded += 1
            else:
                print("FAILED")
                failed += 1

            # Rate limit: 1 request per second
            await asyncio.sleep(1.1)

        await db.commit()
        print(f"\nDone: {geocoded} geocoded, {failed} failed")


if __name__ == "__main__":
    asyncio.run(main())
