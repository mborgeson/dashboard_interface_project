"""
CRUD operations for Deal model.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import Deal, DealStage
from app.schemas.deal import DealCreate, DealUpdate


class CRUDDeal(CRUDBase[Deal, DealCreate, DealUpdate]):
    """
    CRUD operations for Deal model with additional deal-specific methods.
    """

    async def get_with_relations(
        self, db: AsyncSession, id: int
    ) -> Optional[Deal]:
        """Get deal with related data."""
        # Note: Relationships (assigned_user, property) are not yet enabled in the model
        # When enabled, add: .options(selectinload(Deal.assigned_user), selectinload(Deal.property))
        result = await db.execute(
            select(Deal).where(Deal.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_stage(
        self,
        db: AsyncSession,
        *,
        stage: DealStage,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Deal]:
        """Get deals filtered by stage."""
        result = await db.execute(
            select(Deal)
            .where(Deal.stage == stage)
            .order_by(Deal.stage_order.asc(), Deal.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        stage: Optional[str] = None,
        deal_type: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_user_id: Optional[int] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> List[Deal]:
        """Get deals with multiple filters."""
        query = select(Deal)

        # Apply filters
        if stage:
            try:
                stage_enum = DealStage(stage)
                query = query.where(Deal.stage == stage_enum)
            except ValueError:
                pass  # Invalid stage, ignore filter

        if deal_type:
            query = query.where(Deal.deal_type == deal_type)

        if priority:
            query = query.where(Deal.priority == priority)

        if assigned_user_id:
            query = query.where(Deal.assigned_user_id == assigned_user_id)

        # Apply ordering
        if hasattr(Deal, order_by):
            col = getattr(Deal, order_by)
            query = query.order_by(col.desc() if order_desc else col.asc())

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        stage: Optional[str] = None,
        deal_type: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_user_id: Optional[int] = None,
    ) -> int:
        """Count deals with filters."""
        query = select(func.count()).select_from(Deal)

        if stage:
            try:
                stage_enum = DealStage(stage)
                query = query.where(Deal.stage == stage_enum)
            except ValueError:
                pass

        if deal_type:
            query = query.where(Deal.deal_type == deal_type)

        if priority:
            query = query.where(Deal.priority == priority)

        if assigned_user_id:
            query = query.where(Deal.assigned_user_id == assigned_user_id)

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_kanban_data(
        self,
        db: AsyncSession,
        *,
        deal_type: Optional[str] = None,
        assigned_user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get deals organized by stage for Kanban board."""
        query = select(Deal)

        if deal_type:
            query = query.where(Deal.deal_type == deal_type)

        if assigned_user_id:
            query = query.where(Deal.assigned_user_id == assigned_user_id)

        query = query.order_by(Deal.stage_order.asc())
        result = await db.execute(query)
        deals = list(result.scalars().all())

        # Group by stage
        stages: Dict[str, List[Deal]] = {stage.value: [] for stage in DealStage}
        stage_counts: Dict[str, int] = {stage.value: 0 for stage in DealStage}

        for deal in deals:
            stage_value = deal.stage.value if hasattr(deal.stage, 'value') else str(deal.stage)
            if stage_value in stages:
                stages[stage_value].append(deal)
                stage_counts[stage_value] += 1

        return {
            "stages": stages,
            "total_deals": len(deals),
            "stage_counts": stage_counts,
        }

    async def update_stage(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        new_stage: DealStage,
        stage_order: Optional[int] = None,
    ) -> Optional[Deal]:
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
