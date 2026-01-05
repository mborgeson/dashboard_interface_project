"""
CRUD operations for Property model.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import Property
from app.schemas.property import PropertyCreate, PropertyUpdate


class CRUDProperty(CRUDBase[Property, PropertyCreate, PropertyUpdate]):
    """
    CRUD operations for Property model with property-specific methods.
    """

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
        query = select(Property)

        # Apply filters
        if property_type:
            query = query.where(Property.property_type == property_type)

        if city:
            query = query.where(func.lower(Property.city) == func.lower(city))

        if state:
            query = query.where(func.upper(Property.state) == func.upper(state))

        if market:
            query = query.where(func.lower(Property.market) == func.lower(market))

        if min_units is not None:
            query = query.where(Property.total_units >= min_units)

        if max_units is not None:
            query = query.where(Property.total_units <= max_units)

        # Apply ordering
        if hasattr(Property, order_by):
            col = getattr(Property, order_by)
            query = query.order_by(col.desc() if order_desc else col.asc())

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

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
        query = select(func.count()).select_from(Property)

        if property_type:
            query = query.where(Property.property_type == property_type)

        if city:
            query = query.where(func.lower(Property.city) == func.lower(city))

        if state:
            query = query.where(func.upper(Property.state) == func.upper(state))

        if market:
            query = query.where(func.lower(Property.market) == func.lower(market))

        if min_units is not None:
            query = query.where(Property.total_units >= min_units)

        if max_units is not None:
            query = query.where(Property.total_units <= max_units)

        result = await db.execute(query)
        return result.scalar() or 0

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
