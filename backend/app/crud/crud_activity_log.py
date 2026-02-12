"""
CRUD operations for ActivityLog model.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.activity_log import ActivityAction, ActivityLog
from app.schemas.activity_log import ActivityLogCreate


class CRUDActivityLog(CRUDBase[ActivityLog, ActivityLogCreate, ActivityLogCreate]):
    """CRUD operations for ActivityLog model."""

    async def get_by_deal(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        skip: int = 0,
        limit: int = 50,
        action: str | None = None,
    ) -> list[ActivityLog]:
        """
        Get activity logs for a specific deal.

        Args:
            db: Database session
            deal_id: Deal ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            action: Optional action type filter

        Returns:
            List of ActivityLog records
        """
        query = select(ActivityLog).where(ActivityLog.deal_id == deal_id)

        if action:
            try:
                action_enum = ActivityAction(action)
                query = query.where(ActivityLog.action == action_enum)
            except ValueError:
                pass  # Invalid action type, ignore filter

        query = query.order_by(ActivityLog.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_by_deal(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        action: str | None = None,
    ) -> int:
        """
        Count activity logs for a deal.

        Args:
            db: Database session
            deal_id: Deal ID to filter by
            action: Optional action type filter

        Returns:
            Count of matching records
        """
        query = (
            select(func.count())
            .select_from(ActivityLog)
            .where(ActivityLog.deal_id == deal_id)
        )

        if action:
            try:
                action_enum = ActivityAction(action)
                query = query.where(ActivityLog.action == action_enum)
            except ValueError:
                pass

        result = await db.execute(query)
        return result.scalar() or 0

    async def create_for_deal(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        action: ActivityAction,
        description: str,
        user_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ActivityLog:
        """
        Create an activity log entry for a deal.

        Args:
            db: Database session
            deal_id: Deal ID
            action: Action type
            description: Human-readable description
            user_id: Optional user identifier
            meta: Optional JSONB metadata

        Returns:
            Created ActivityLog record
        """
        import uuid

        activity = ActivityLog(
            id=str(uuid.uuid4()),  # Convert to string for SQLite compatibility
            deal_id=deal_id,
            user_id=user_id,
            action=action,
            description=description,
            meta=meta,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(activity)
        return activity

    async def log_stage_change(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        old_stage: str,
        new_stage: str,
        user_id: str | None = None,
    ) -> ActivityLog:
        """
        Log a deal stage change.

        Args:
            db: Database session
            deal_id: Deal ID
            old_stage: Previous stage value
            new_stage: New stage value
            user_id: Optional user identifier

        Returns:
            Created ActivityLog record
        """
        return await self.create_for_deal(
            db,
            deal_id=deal_id,
            action=ActivityAction.STAGE_CHANGED,
            description=f"Stage changed from {old_stage} to {new_stage}",
            user_id=user_id,
            meta={"old_stage": old_stage, "new_stage": new_stage},
        )

    async def log_creation(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        deal_name: str,
        user_id: str | None = None,
    ) -> ActivityLog:
        """
        Log deal creation.

        Args:
            db: Database session
            deal_id: Deal ID
            deal_name: Name of the created deal
            user_id: Optional user identifier

        Returns:
            Created ActivityLog record
        """
        return await self.create_for_deal(
            db,
            deal_id=deal_id,
            action=ActivityAction.CREATED,
            description=f"Deal '{deal_name}' created",
            user_id=user_id,
            meta={"deal_name": deal_name},
        )

    async def log_update(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        changed_fields: list[str],
        user_id: str | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
    ) -> ActivityLog:
        """
        Log deal update.

        Args:
            db: Database session
            deal_id: Deal ID
            changed_fields: List of field names that were changed
            user_id: Optional user identifier
            old_values: Optional dict of old values
            new_values: Optional dict of new values

        Returns:
            Created ActivityLog record
        """
        fields_str = ", ".join(changed_fields)
        meta: dict[str, Any] = {"changed_fields": changed_fields}
        if old_values:
            meta["old_values"] = old_values
        if new_values:
            meta["new_values"] = new_values

        return await self.create_for_deal(
            db,
            deal_id=deal_id,
            action=ActivityAction.UPDATED,
            description=f"Updated fields: {fields_str}",
            user_id=user_id,
            meta=meta,
        )


# Singleton instance
activity_log = CRUDActivityLog(ActivityLog)
