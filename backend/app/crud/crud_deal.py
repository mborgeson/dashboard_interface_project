"""
CRUD operations for Deal model.
"""

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import Deal, DealStage
from app.schemas.deal import DealCreate, DealUpdate


class CRUDDeal(CRUDBase[Deal, DealCreate, DealUpdate]):
    """
    CRUD operations for Deal model with additional deal-specific methods.
    """

    async def get_with_relations(
        self,
        db: AsyncSession,
        id: int,
        *,
        include_deleted: bool = False,
    ) -> Deal | None:
        """Get deal with related data."""
        # Note: Relationships (assigned_user, property) are not yet enabled in the model
        # When enabled, add: .options(selectinload(Deal.assigned_user), selectinload(Deal.property))
        query = select(Deal).where(Deal.id == id)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_stage(
        self,
        db: AsyncSession,
        *,
        stage: DealStage,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> list[Deal]:
        """Get deals filtered by stage."""
        # Custom ordering (stage_order + created_at) prevents use of
        # get_multi_ordered which only supports single-column ordering.
        query = (
            select(Deal)
            .where(Deal.stage == stage)
            .order_by(Deal.stage_order.asc(), Deal.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        result = await db.execute(query)
        return list(result.scalars().all())

    def _build_deal_conditions(
        self,
        *,
        stage: str | None = None,
        deal_type: str | None = None,
        priority: str | None = None,
        assigned_user_id: int | None = None,
    ) -> list:
        """Build SQLAlchemy filter conditions for deal queries."""
        conditions: list = []

        if stage:
            try:
                stage_enum = DealStage(stage)
                conditions.append(Deal.stage == stage_enum)
            except ValueError:
                pass  # Invalid stage, ignore filter

        if deal_type:
            conditions.append(Deal.deal_type == deal_type)

        if priority:
            conditions.append(Deal.priority == priority)

        if assigned_user_id:
            conditions.append(Deal.assigned_user_id == assigned_user_id)

        return conditions

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        stage: str | None = None,
        deal_type: str | None = None,
        priority: str | None = None,
        assigned_user_id: int | None = None,
        order_by: str = "created_at",
        order_desc: bool = True,
        include_deleted: bool = False,
    ) -> list[Deal]:
        """Get deals with multiple filters."""
        conditions = self._build_deal_conditions(
            stage=stage,
            deal_type=deal_type,
            priority=priority,
            assigned_user_id=assigned_user_id,
        )
        return await self.get_multi_ordered(
            db,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc,
            conditions=conditions,
            include_deleted=include_deleted,
        )

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        stage: str | None = None,
        deal_type: str | None = None,
        priority: str | None = None,
        assigned_user_id: int | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Count deals with filters."""
        conditions = self._build_deal_conditions(
            stage=stage,
            deal_type=deal_type,
            priority=priority,
            assigned_user_id=assigned_user_id,
        )
        return await self.count_where(
            db,
            conditions=conditions,
            include_deleted=include_deleted,
        )

    async def get_kanban_data(
        self,
        db: AsyncSession,
        *,
        deal_type: str | None = None,
        assigned_user_id: int | None = None,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Get deals organized by stage for Kanban board."""
        query = select(Deal)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)

        if deal_type:
            query = query.where(Deal.deal_type == deal_type)

        if assigned_user_id:
            query = query.where(Deal.assigned_user_id == assigned_user_id)

        query = query.order_by(Deal.stage_order.asc())
        result = await db.execute(query)
        deals = list(result.scalars().all())

        # Group by stage
        stages: dict[str, list[Deal]] = {stage.value: [] for stage in DealStage}
        stage_counts: dict[str, int] = {stage.value: 0 for stage in DealStage}

        for deal in deals:
            stage_value = (
                deal.stage.value if hasattr(deal.stage, "value") else str(deal.stage)
            )
            if stage_value in stages:
                stages[stage_value].append(deal)
                stage_counts[stage_value] += 1

        return {
            "stages": stages,
            "total_deals": len(deals),
            "stage_counts": stage_counts,
        }

    async def get_by_ids(
        self,
        db: AsyncSession,
        *,
        ids: list[int],
        include_deleted: bool = False,
    ) -> list[Deal]:
        """Batch-fetch multiple deals by ID in a single query.

        Returns deals matching any of the given IDs (order not guaranteed).
        """
        if not ids:
            return []
        query = select(Deal).where(Deal.id.in_(ids))
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_optimistic(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        expected_version: int,
        update_data: dict[str, Any],
    ) -> Deal | None:
        """
        Update a deal with optimistic locking.

        Uses a WHERE clause on version to detect concurrent edits.
        Returns the updated Deal on success, or None if the version
        was stale (meaning another update happened first).
        """
        # Remove 'version' from update_data if present — we set it ourselves
        update_data.pop("version", None)

        # Build the UPDATE ... WHERE id = :id AND version = :expected_version
        stmt = (
            update(Deal)
            .where(Deal.id == deal_id, Deal.version == expected_version)
            .values(version=expected_version + 1, **update_data)
        )
        result = await db.execute(stmt)

        if result.rowcount == 0:  # type: ignore[attr-defined]
            # No rows matched — version was stale or deal doesn't exist
            return None

        await db.commit()

        # Re-fetch the updated object
        return await self.get(db, deal_id)

    async def update_stage(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        new_stage: DealStage,
        stage_order: int | None = None,
    ) -> Deal | None:
        """Update deal stage (for Kanban drag-and-drop)."""
        deal = await self.get(db, deal_id)
        if not deal:
            return None

        deal.stage = new_stage
        if stage_order is not None:
            deal.stage_order = stage_order

        db.add(deal)
        await db.commit()
        await db.refresh(deal)
        return deal


# Singleton instance
deal = CRUDDeal(Deal)
