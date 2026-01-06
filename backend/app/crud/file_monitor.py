"""
CRUD operations for file monitoring models.

Provides database operations for:
- MonitoredFile records (tracking SharePoint file state)
- FileChangeLog records (audit trail of detected changes)
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_monitor import FileChangeLog, MonitoredFile


class MonitoredFileCRUD:
    """CRUD operations for MonitoredFile model."""

    @staticmethod
    async def create(
        db: AsyncSession,
        file_path: str,
        file_name: str,
        deal_name: str,
        size_bytes: int,
        modified_date: datetime,
        deal_stage: str | None = None,
    ) -> MonitoredFile:
        """Create a new monitored file record."""
        now = datetime.utcnow()
        file = MonitoredFile(
            file_path=file_path,
            file_name=file_name,
            deal_name=deal_name,
            size_bytes=size_bytes,
            modified_date=modified_date,
            first_seen=now,
            last_checked=now,
            is_active=True,
            extraction_pending=True,
            deal_stage=deal_stage,
        )
        db.add(file)
        await db.commit()
        await db.refresh(file)
        return file

    @staticmethod
    async def get(db: AsyncSession, file_id: UUID) -> MonitoredFile | None:
        """Get monitored file by ID."""
        return await db.get(MonitoredFile, file_id)

    @staticmethod
    async def get_by_path(db: AsyncSession, file_path: str) -> MonitoredFile | None:
        """Get monitored file by SharePoint path."""
        stmt = select(MonitoredFile).where(MonitoredFile.file_path == file_path)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_active(db: AsyncSession) -> list[MonitoredFile]:
        """Get all active monitored files."""
        stmt = (
            select(MonitoredFile)
            .where(MonitoredFile.is_active.is_(True))
            .order_by(MonitoredFile.deal_name, MonitoredFile.file_name)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_deal(
        db: AsyncSession,
        deal_name: str,
        active_only: bool = True,
    ) -> list[MonitoredFile]:
        """Get monitored files for a specific deal."""
        stmt = select(MonitoredFile).where(MonitoredFile.deal_name == deal_name)
        if active_only:
            stmt = stmt.where(MonitoredFile.is_active.is_(True))
        stmt = stmt.order_by(MonitoredFile.file_name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_pending_extraction(db: AsyncSession) -> list[MonitoredFile]:
        """Get files that need extraction."""
        stmt = (
            select(MonitoredFile)
            .where(
                MonitoredFile.extraction_pending.is_(True),
                MonitoredFile.is_active.is_(True),
            )
            .order_by(MonitoredFile.deal_name, MonitoredFile.file_name)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_or_update(
        db: AsyncSession,
        file_path: str,
        file_name: str,
        deal_name: str,
        size_bytes: int,
        modified_date: datetime,
        deal_stage: str | None = None,
    ) -> tuple[MonitoredFile, bool]:
        """
        Create or update a monitored file record.

        Returns:
            Tuple of (MonitoredFile, is_new) where is_new indicates if created
        """
        existing = await MonitoredFileCRUD.get_by_path(db, file_path)
        now = datetime.utcnow()

        if existing:
            # Check if file was modified
            was_modified = (
                modified_date > existing.modified_date
                or size_bytes != existing.size_bytes
            )

            existing.file_name = file_name
            existing.deal_name = deal_name
            existing.size_bytes = size_bytes
            existing.modified_date = modified_date
            existing.last_checked = now
            existing.deal_stage = deal_stage
            existing.is_active = True

            if was_modified:
                existing.extraction_pending = True

            await db.commit()
            await db.refresh(existing)
            return existing, False
        else:
            file = MonitoredFile(
                file_path=file_path,
                file_name=file_name,
                deal_name=deal_name,
                size_bytes=size_bytes,
                modified_date=modified_date,
                first_seen=now,
                last_checked=now,
                is_active=True,
                extraction_pending=True,
                deal_stage=deal_stage,
            )
            db.add(file)
            await db.commit()
            await db.refresh(file)
            return file, True

    @staticmethod
    async def mark_extracted(
        db: AsyncSession,
        file_path: str,
        extraction_run_id: UUID,
    ) -> MonitoredFile | None:
        """Mark a file as having been extracted."""
        stmt = (
            update(MonitoredFile)
            .where(MonitoredFile.file_path == file_path)
            .values(
                extraction_pending=False,
                last_extracted=datetime.utcnow(),
                extraction_run_id=extraction_run_id,
            )
            .returning(MonitoredFile)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def mark_inactive(
        db: AsyncSession,
        file_path: str,
    ) -> MonitoredFile | None:
        """Mark a file as inactive (deleted from SharePoint)."""
        file = await MonitoredFileCRUD.get_by_path(db, file_path)
        if file:
            file.is_active = False
            file.last_checked = datetime.utcnow()
            await db.commit()
            await db.refresh(file)
        return file

    @staticmethod
    async def bulk_update_last_checked(
        db: AsyncSession,
        file_paths: list[str],
    ) -> int:
        """Update last_checked timestamp for multiple files."""
        stmt = (
            update(MonitoredFile)
            .where(MonitoredFile.file_path.in_(file_paths))
            .values(last_checked=datetime.utcnow())
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def get_stats(db: AsyncSession) -> dict[str, Any]:
        """Get statistics about monitored files."""
        # Total active files
        total_stmt = select(func.count(MonitoredFile.id)).where(
            MonitoredFile.is_active.is_(True)
        )
        total = (await db.execute(total_stmt)).scalar_one()

        # Pending extraction
        pending_stmt = select(func.count(MonitoredFile.id)).where(
            and_(
                MonitoredFile.is_active.is_(True),
                MonitoredFile.extraction_pending.is_(True),
            )
        )
        pending = (await db.execute(pending_stmt)).scalar_one()

        # Unique deals
        deals_stmt = select(func.count(func.distinct(MonitoredFile.deal_name))).where(
            MonitoredFile.is_active.is_(True)
        )
        deals = (await db.execute(deals_stmt)).scalar_one()

        # Files by deal stage
        stage_stmt = (
            select(
                MonitoredFile.deal_stage,
                func.count(MonitoredFile.id),
            )
            .where(MonitoredFile.is_active.is_(True))
            .group_by(MonitoredFile.deal_stage)
        )
        stage_result = await db.execute(stage_stmt)
        by_stage = {row[0] or "unknown": row[1] for row in stage_result}

        return {
            "total_files": total,
            "pending_extraction": pending,
            "unique_deals": deals,
            "by_deal_stage": by_stage,
        }


class FileChangeLogCRUD:
    """CRUD operations for FileChangeLog model."""

    @staticmethod
    async def create(
        db: AsyncSession,
        file_path: str,
        file_name: str,
        deal_name: str,
        change_type: str,
        old_modified_date: datetime | None = None,
        new_modified_date: datetime | None = None,
        old_size_bytes: int | None = None,
        new_size_bytes: int | None = None,
        monitored_file_id: UUID | None = None,
    ) -> FileChangeLog:
        """Create a file change log entry."""
        log = FileChangeLog(
            file_path=file_path,
            file_name=file_name,
            deal_name=deal_name,
            change_type=change_type,
            old_modified_date=old_modified_date,
            new_modified_date=new_modified_date,
            old_size_bytes=old_size_bytes,
            new_size_bytes=new_size_bytes,
            detected_at=datetime.utcnow(),
            monitored_file_id=monitored_file_id,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def get_recent(
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        change_type: str | None = None,
        deal_name: str | None = None,
    ) -> list[FileChangeLog]:
        """Get recent file change log entries."""
        stmt = select(FileChangeLog)

        if change_type:
            stmt = stmt.where(FileChangeLog.change_type == change_type)
        if deal_name:
            stmt = stmt.where(FileChangeLog.deal_name == deal_name)

        stmt = (
            stmt.order_by(FileChangeLog.detected_at.desc()).offset(offset).limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def count_by_type(
        db: AsyncSession,
        since: datetime | None = None,
    ) -> dict[str, int]:
        """Count changes by type, optionally since a given date."""
        stmt = select(
            FileChangeLog.change_type,
            func.count(FileChangeLog.id),
        ).group_by(FileChangeLog.change_type)

        if since:
            stmt = stmt.where(FileChangeLog.detected_at >= since)

        result = await db.execute(stmt)
        return {row[0]: row[1] for row in result}

    @staticmethod
    async def mark_extraction_triggered(
        db: AsyncSession,
        log_ids: list[UUID],
        extraction_run_id: UUID,
    ) -> int:
        """Mark change logs as having triggered extraction."""
        stmt = (
            update(FileChangeLog)
            .where(FileChangeLog.id.in_(log_ids))
            .values(
                extraction_triggered=True,
                extraction_run_id=extraction_run_id,
            )
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def get_total_count(
        db: AsyncSession,
        since: datetime | None = None,
    ) -> int:
        """Get total count of change log entries."""
        stmt = select(func.count(FileChangeLog.id))
        if since:
            stmt = stmt.where(FileChangeLog.detected_at >= since)
        return (await db.execute(stmt)).scalar_one()
