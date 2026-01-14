"""
CRUD operations for Activity models.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.activity import (
    ActivityType,
    DealActivity,
    PropertyActivity,
    UserWatchlist,
)
from app.schemas.activity import (
    DealActivityCreate,
    PropertyActivityCreate,
    WatchlistCreate,
)


class CRUDPropertyActivity(
    CRUDBase[PropertyActivity, PropertyActivityCreate, PropertyActivityCreate]
):
    """CRUD operations for PropertyActivity model."""

    async def get_by_property(
        self,
        db: AsyncSession,
        *,
        property_id: int,
        skip: int = 0,
        limit: int = 50,
        activity_type: str | None = None,
    ) -> list[PropertyActivity]:
        """Get activities for a specific property."""
        query = select(PropertyActivity).where(
            PropertyActivity.property_id == property_id
        )

        if activity_type:
            try:
                type_enum = ActivityType(activity_type)
                query = query.where(PropertyActivity.activity_type == type_enum)
            except ValueError:
                pass  # Invalid type, ignore filter

        query = (
            query.order_by(PropertyActivity.created_at.desc()).offset(skip).limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_by_property(
        self,
        db: AsyncSession,
        *,
        property_id: int,
        activity_type: str | None = None,
    ) -> int:
        """Count activities for a property."""
        query = (
            select(func.count())
            .select_from(PropertyActivity)
            .where(PropertyActivity.property_id == property_id)
        )

        if activity_type:
            try:
                type_enum = ActivityType(activity_type)
                query = query.where(PropertyActivity.activity_type == type_enum)
            except ValueError:
                pass

        result = await db.execute(query)
        return result.scalar() or 0

    async def log_view(
        self,
        db: AsyncSession,
        *,
        property_id: int,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PropertyActivity:
        """Log a property view."""
        activity = PropertyActivity(
            property_id=property_id,
            user_id=user_id,
            activity_type=ActivityType.VIEW,
            description="Viewed property details",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(activity)
        return activity

    async def log_edit(
        self,
        db: AsyncSession,
        *,
        property_id: int,
        user_id: int,
        field_changed: str,
        old_value: str | None,
        new_value: str | None,
    ) -> PropertyActivity:
        """Log a property edit."""
        activity = PropertyActivity(
            property_id=property_id,
            user_id=user_id,
            activity_type=ActivityType.EDIT,
            description=f"Modified {field_changed}",
            field_changed=field_changed,
            old_value=str(old_value) if old_value else None,
            new_value=str(new_value) if new_value else None,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(activity)
        return activity


class CRUDDealActivity(CRUDBase[DealActivity, DealActivityCreate, DealActivityCreate]):
    """CRUD operations for DealActivity model."""

    async def get_by_deal(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        skip: int = 0,
        limit: int = 50,
        activity_type: str | None = None,
    ) -> list[DealActivity]:
        """Get activities for a specific deal."""
        query = select(DealActivity).where(DealActivity.deal_id == deal_id)

        if activity_type:
            try:
                type_enum = ActivityType(activity_type)
                query = query.where(DealActivity.activity_type == type_enum)
            except ValueError:
                pass

        query = query.order_by(DealActivity.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_by_deal(
        self,
        db: AsyncSession,
        *,
        deal_id: int,
        activity_type: str | None = None,
    ) -> int:
        """Count activities for a deal."""
        query = (
            select(func.count())
            .select_from(DealActivity)
            .where(DealActivity.deal_id == deal_id)
        )

        if activity_type:
            try:
                type_enum = ActivityType(activity_type)
                query = query.where(DealActivity.activity_type == type_enum)
            except ValueError:
                pass

        result = await db.execute(query)
        return result.scalar() or 0


class CRUDWatchlist(CRUDBase[UserWatchlist, WatchlistCreate, WatchlistCreate]):
    """CRUD operations for UserWatchlist model."""

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[UserWatchlist]:
        """Get all watched deals for a user."""
        query = (
            select(UserWatchlist)
            .where(UserWatchlist.user_id == user_id)
            .order_by(UserWatchlist.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_user_and_deal(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        deal_id: int,
    ) -> UserWatchlist | None:
        """Check if a user is watching a specific deal."""
        query = select(UserWatchlist).where(
            UserWatchlist.user_id == user_id,
            UserWatchlist.deal_id == deal_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def is_watching(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        deal_id: int,
    ) -> bool:
        """Check if user is watching a deal."""
        entry = await self.get_by_user_and_deal(db, user_id=user_id, deal_id=deal_id)
        return entry is not None

    async def add_to_watchlist(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        deal_id: int,
        notes: str | None = None,
    ) -> UserWatchlist:
        """Add a deal to user's watchlist."""
        # Check if already watching
        existing = await self.get_by_user_and_deal(db, user_id=user_id, deal_id=deal_id)
        if existing:
            return existing

        watchlist_entry = UserWatchlist(
            user_id=user_id,
            deal_id=deal_id,
            notes=notes,
        )
        db.add(watchlist_entry)
        await db.commit()
        await db.refresh(watchlist_entry)
        return watchlist_entry

    async def remove_from_watchlist(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        deal_id: int,
    ) -> bool:
        """Remove a deal from user's watchlist."""
        entry = await self.get_by_user_and_deal(db, user_id=user_id, deal_id=deal_id)
        if not entry:
            return False

        await db.delete(entry)
        await db.commit()
        return True

    async def toggle_watchlist(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        deal_id: int,
        notes: str | None = None,
    ) -> tuple[bool, UserWatchlist | None]:
        """
        Toggle a deal on/off the user's watchlist.

        Returns:
            Tuple of (is_now_watched, watchlist_entry or None)
        """
        existing = await self.get_by_user_and_deal(db, user_id=user_id, deal_id=deal_id)

        if existing:
            # Remove from watchlist
            await db.delete(existing)
            await db.commit()
            return (False, None)
        else:
            # Add to watchlist
            entry = await self.add_to_watchlist(
                db, user_id=user_id, deal_id=deal_id, notes=notes
            )
            return (True, entry)

    async def count_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> int:
        """Count watched deals for a user."""
        query = (
            select(func.count())
            .select_from(UserWatchlist)
            .where(UserWatchlist.user_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar() or 0


# Singleton instances
property_activity = CRUDPropertyActivity(PropertyActivity)
deal_activity = CRUDDealActivity(DealActivity)
watchlist = CRUDWatchlist(UserWatchlist)
