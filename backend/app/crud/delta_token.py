"""
CRUD operations for DeltaToken model.

Provides async database operations for managing Microsoft Graph
delta query tokens used for incremental SharePoint sync.
"""

from __future__ import annotations

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delta_token import DeltaToken


class DeltaTokenCRUD:
    """CRUD operations for DeltaToken model."""

    @staticmethod
    async def get_by_drive_id(
        db: AsyncSession,
        drive_id: str,
    ) -> DeltaToken | None:
        """Get delta token for a specific drive.

        Args:
            db: Async database session.
            drive_id: Microsoft Graph drive ID.

        Returns:
            DeltaToken if found, None otherwise.
        """
        stmt = select(DeltaToken).where(DeltaToken.drive_id == drive_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert_token(
        db: AsyncSession,
        drive_id: str,
        token: str,
    ) -> DeltaToken:
        """Create or update a delta token for a drive.

        If a token already exists for the drive_id, updates the token
        value and last_sync_at timestamp. Otherwise creates a new record.

        Args:
            db: Async database session.
            drive_id: Microsoft Graph drive ID.
            token: The delta token string from the Graph API response.

        Returns:
            The created or updated DeltaToken.
        """
        now = datetime.now(UTC)
        existing = await DeltaTokenCRUD.get_by_drive_id(db, drive_id)

        if existing:
            existing.delta_token = token
            existing.last_sync_at = now
            existing.updated_at = now
            await db.flush()
            await db.refresh(existing)
            logger.debug(
                "Delta token updated for drive_id={}",
                drive_id,
            )
            return existing

        new_token = DeltaToken(
            drive_id=drive_id,
            delta_token=token,
            last_sync_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(new_token)
        await db.flush()
        await db.refresh(new_token)
        logger.debug(
            "Delta token created for drive_id={}",
            drive_id,
        )
        return new_token

    @staticmethod
    async def clear_token(
        db: AsyncSession,
        drive_id: str,
    ) -> bool:
        """Delete the delta token for a drive.

        Called when the token has expired (HTTP 410 Gone) and the
        client needs to fall back to a full scan.

        Args:
            db: Async database session.
            drive_id: Microsoft Graph drive ID.

        Returns:
            True if a token was deleted, False if no token existed.
        """
        stmt = delete(DeltaToken).where(DeltaToken.drive_id == drive_id)
        result = await db.execute(stmt)
        await db.flush()
        deleted = result.rowcount > 0  # type: ignore[attr-defined]
        if deleted:
            logger.info(
                "Delta token cleared for drive_id={} (expired or reset)",
                drive_id,
            )
        return deleted
