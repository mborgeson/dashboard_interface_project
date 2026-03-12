"""
CRUD operations for Property model.

Field-mapping constants and enrichment business logic live in
``app.services.enrichment``. The methods here are thin wrappers that
orchestrate DB queries (or accept pre-fetched data), delegate to the
service for transformation, then persist the results.
"""

from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import Property
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.services.enrichment import (
    build_base_expenses,
    build_financial_data_json,
    build_ops_by_year,
    fetch_base_field_values,
    fetch_bulk_base_rows,
    fetch_bulk_year_rows,
    fetch_year_field_rows,
    get_property_name_variants,
    match_prop_name,
    update_property_columns,
)


class CRUDProperty(CRUDBase[Property, PropertyCreate, PropertyUpdate]):
    """
    CRUD operations for Property model with property-specific methods.
    """

    async def enrich_financial_data(
        self,
        db: AsyncSession,
        prop: Property,
        *,
        _prefetched_base: dict[str, float | str | None] | None = None,
        _prefetched_year: list[tuple[str, float | None]] | None = None,
    ) -> Property:
        """
        Populate a property's direct columns and financial_data JSON from
        extracted_values if financial_data is currently NULL/empty.

        Business logic (field mapping, JSON building, unit conversion) is
        delegated to ``app.services.enrichment``. This method handles DB
        queries and persistence.

        When called from ``enrich_financial_data_batch``, pre-fetched data
        is passed via ``_prefetched_base`` and ``_prefetched_year`` to avoid
        per-property DB queries (N+1 elimination).
        """
        # -- Resolve base field values --
        if _prefetched_base is not None:
            field_values = dict(_prefetched_base)
        else:
            field_values = await fetch_base_field_values(db, prop)

        changed = False

        # -- Update direct columns via service --
        if field_values:
            changed = update_property_columns(prop, field_values)

        # -- Build financial_data JSON via service --
        fd = dict(prop.financial_data) if prop.financial_data else {}
        new_fd = build_financial_data_json(prop, field_values, fd)

        # -- Build expense breakdown + multi-year ops --
        expenses = fd.get("expenses", {})
        ops_by_year = fd.get("operationsByYear", {})
        if not expenses or not ops_by_year:
            # Resolve year rows
            if _prefetched_year is not None:
                year_rows = _prefetched_year
            else:
                year_rows = await fetch_year_field_rows(db, prop)

            ops_by_year, expenses, ev_changed = build_ops_by_year(
                year_rows,
                expenses,
                property_id=prop.id,
                property_name=prop.name,
            )
            if ev_changed:
                changed = True

        # Fallback: build expenses from base per-unit fields when YEAR_N
        # fields didn't produce an expenses dict
        if not expenses and field_values:
            expenses = build_base_expenses(field_values, prop.total_units or 0)
            if expenses:
                changed = True

        if expenses:
            new_fd["expenses"] = expenses
        if ops_by_year:
            new_fd["operationsByYear"] = ops_by_year

        if new_fd and new_fd != (prop.financial_data or {}):
            prop.financial_data = new_fd
            changed = True

        if changed:
            db.add(prop)
            await db.flush()
            await db.refresh(prop)
            logger.info(
                "property_financial_data_enriched",
                property_id=prop.id,
                property_name=prop.name,
                fields_found=len(field_values),
            )

        return prop

    async def enrich_financial_data_batch(
        self, db: AsyncSession, properties: list[Property]
    ) -> list[Property]:
        """Batch-enrich multiple properties that are missing financial_data.

        Instead of issuing 2-3 DB queries per property (N+1 pattern), this
        method collects all name variants, executes two bulk queries (base
        fields + YEAR_N fields), partitions the results by property name,
        and then delegates to the existing per-property enrichment logic.

        Properties that already have ``financial_data`` are skipped.

        Returns the full list with enriched properties in their original positions.
        """
        from app.models.extraction import ExtractedValue

        # Identify properties needing enrichment
        needs_enrichment = [p for p in properties if not p.financial_data]
        if not needs_enrichment:
            return properties

        # Build name→property mapping and collect all name variants
        all_names: list[str] = []
        name_to_props: dict[str, list[Property]] = {}
        for prop in needs_enrichment:
            variants = get_property_name_variants(prop)
            for v in variants:
                name_to_props.setdefault(v, []).append(prop)
                all_names.append(v)

        if not all_names:
            return properties

        # Build OR conditions for all property name variants
        name_conditions = []
        for name in set(all_names):
            name_conditions.append(ExtractedValue.property_name == name)
            name_conditions.append(ExtractedValue.property_name.like(name + " (%"))

        # Bulk queries via service helpers
        base_rows = await fetch_bulk_base_rows(db, name_conditions)
        year_rows = await fetch_bulk_year_rows(db, name_conditions)

        for prop in needs_enrichment:
            # Build per-property base field dict (dedup by field_name, first=latest)
            prop_base: dict[str, float | str | None] = {}
            for pname, fname, vnumeric, vtext in base_rows:
                if fname not in prop_base and match_prop_name(pname, prop):
                    prop_base[fname] = vnumeric if vnumeric is not None else vtext

            # Build per-property year rows list
            prop_year: list[tuple[str, float | None]] = [
                (fname, vnumeric)
                for pname, fname, vnumeric in year_rows
                if match_prop_name(pname, prop)
            ]

            await self.enrich_financial_data(
                db,
                prop,
                _prefetched_base=prop_base if prop_base else {},
                _prefetched_year=prop_year if prop_year else [],
            )

        logger.info(
            "batch_financial_data_enrichment",
            properties_enriched=len(needs_enrichment),
            base_rows_fetched=len(base_rows),
            year_rows_fetched=len(year_rows),
        )

        return properties

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
        """Get aggregate analytics for all properties in a single query."""
        result = await db.execute(
            select(
                func.count().label("total_count"),
                func.coalesce(func.sum(Property.total_units), 0).label("total_units"),
                func.coalesce(func.sum(Property.total_sf), 0).label("total_sf"),
                func.avg(Property.cap_rate).label("avg_cap_rate"),
                func.avg(Property.occupancy_rate).label("avg_occupancy"),
            ).select_from(Property)
        )
        row = result.one()

        return {
            "total_properties": row.total_count or 0,
            "total_units": row.total_units or 0,
            "total_sf": row.total_sf or 0,
            "avg_cap_rate": float(row.avg_cap_rate) if row.avg_cap_rate else None,
            "avg_occupancy": float(row.avg_occupancy) if row.avg_occupancy else None,
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
