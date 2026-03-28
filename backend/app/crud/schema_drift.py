"""
CRUD operations for SchemaDriftAlert model.

Provides async database operations for creating, querying, and
resolving schema drift alerts generated during extraction.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema_drift_alert import SchemaDriftAlert


class SchemaDriftAlertCRUD:
    """CRUD operations for SchemaDriftAlert model."""

    @staticmethod
    async def create_alert(
        db: AsyncSession,
        *,
        group_name: str,
        file_path: str,
        similarity_score: float,
        severity: str,
        changed_sheets: list[str] | None = None,
        missing_sheets: list[str] | None = None,
        new_sheets: list[str] | None = None,
        details: dict | None = None,
    ) -> SchemaDriftAlert:
        """Create a new schema drift alert.

        Args:
            db: Async database session.
            group_name: Name of the affected group.
            file_path: Path to the file that triggered the alert.
            similarity_score: Computed similarity (0.0-1.0).
            severity: Alert severity level (info/warning/error).
            changed_sheets: Sheets with structural changes.
            missing_sheets: Sheets present in baseline but not in file.
            new_sheets: Sheets present in file but not in baseline.
            details: Additional comparison details.

        Returns:
            The created SchemaDriftAlert.
        """
        now = datetime.now(UTC)
        alert = SchemaDriftAlert(
            id=uuid4(),
            group_name=group_name,
            file_path=file_path,
            similarity_score=similarity_score,
            severity=severity,
            changed_sheets=changed_sheets,
            missing_sheets=missing_sheets,
            new_sheets=new_sheets,
            details=details,
            resolved=False,
            resolved_at=None,
            created_at=now,
            updated_at=now,
        )
        db.add(alert)
        await db.flush()
        await db.refresh(alert)

        logger.info(
            "drift_alert_created",
            alert_id=str(alert.id),
            group_name=group_name,
            severity=severity,
            similarity_score=similarity_score,
        )
        return alert

    @staticmethod
    async def get_alerts(
        db: AsyncSession,
        *,
        group_name: str | None = None,
        severity: str | None = None,
        resolved: bool | None = None,
        limit: int = 50,
    ) -> list[SchemaDriftAlert]:
        """Query schema drift alerts with optional filters.

        Args:
            db: Async database session.
            group_name: Filter by group name.
            severity: Filter by severity level.
            resolved: Filter by resolution status.
            limit: Maximum number of results.

        Returns:
            List of matching SchemaDriftAlert records.
        """
        stmt = select(SchemaDriftAlert).order_by(SchemaDriftAlert.created_at.desc())

        if group_name is not None:
            stmt = stmt.where(SchemaDriftAlert.group_name == group_name)
        if severity is not None:
            stmt = stmt.where(SchemaDriftAlert.severity == severity)
        if resolved is not None:
            stmt = stmt.where(SchemaDriftAlert.resolved == resolved)

        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def resolve_alert(
        db: AsyncSession,
        alert_id: UUID,
    ) -> SchemaDriftAlert | None:
        """Mark a schema drift alert as resolved.

        Args:
            db: Async database session.
            alert_id: UUID of the alert to resolve.

        Returns:
            The updated SchemaDriftAlert, or None if not found.
        """
        stmt = select(SchemaDriftAlert).where(SchemaDriftAlert.id == alert_id)
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()

        if alert is None:
            return None

        now = datetime.now(UTC)
        alert.resolved = True
        alert.resolved_at = now
        alert.updated_at = now
        await db.flush()
        await db.refresh(alert)

        logger.info(
            "drift_alert_resolved",
            alert_id=str(alert_id),
            group_name=alert.group_name,
        )
        return alert
