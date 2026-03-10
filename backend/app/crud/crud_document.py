"""
CRUD operations for Document model.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.document import Document, DocumentType
from app.schemas.document import DocumentCreate, DocumentUpdate


class CRUDDocument(CRUDBase[Document, DocumentCreate, DocumentUpdate]):
    """
    CRUD operations for Document model with additional document-specific methods.
    """

    async def get_by_property(
        self,
        db: AsyncSession,
        *,
        property_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        """Get documents by property ID."""
        result = await db.execute(
            select(Document)
            .where(Document.property_id == property_id)
            .where(Document.is_deleted.is_(False))
            .order_by(Document.uploaded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type(
        self,
        db: AsyncSession,
        *,
        doc_type: DocumentType,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        """Get documents by type."""
        result = await db.execute(
            select(Document)
            .where(Document.type == doc_type)
            .where(Document.is_deleted.is_(False))
            .order_by(Document.uploaded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def _date_range_cutoff(date_range: str | None) -> datetime | None:
        """Convert a date range string to a cutoff datetime."""
        if not date_range or date_range == "all":
            return None

        days_map = {
            "7days": 7,
            "30days": 30,
            "90days": 90,
            "1year": 365,
        }
        days = days_map.get(date_range)
        return datetime.now(UTC) - timedelta(days=days) if days else None

    def _build_document_conditions(
        self,
        *,
        doc_type: str | None = None,
        property_id: str | None = None,
        search_term: str | None = None,
        date_range: str | None = None,
    ) -> list:
        """Build SQLAlchemy filter conditions for document queries."""
        conditions: list = []

        if doc_type and doc_type != "all":
            try:
                type_enum = DocumentType(doc_type)
                conditions.append(Document.type == type_enum)
            except ValueError:
                pass  # Invalid type, ignore filter

        if property_id and property_id != "all":
            conditions.append(Document.property_id == property_id)

        if search_term:
            search_pattern = f"%{search_term}%"
            conditions.append(
                or_(
                    Document.name.ilike(search_pattern),
                    Document.description.ilike(search_pattern),
                )
            )

        cutoff = self._date_range_cutoff(date_range)
        if cutoff:
            conditions.append(Document.uploaded_at >= cutoff)

        return conditions

    async def get_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        doc_type: str | None = None,
        property_id: str | None = None,
        search_term: str | None = None,
        date_range: str | None = None,
        order_by: str = "uploaded_at",
        order_desc: bool = True,
    ) -> list[Document]:
        """Get documents with multiple filters."""
        conditions = self._build_document_conditions(
            doc_type=doc_type,
            property_id=property_id,
            search_term=search_term,
            date_range=date_range,
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
        doc_type: str | None = None,
        property_id: str | None = None,
        search_term: str | None = None,
        date_range: str | None = None,
    ) -> int:
        """Count documents with filters."""
        conditions = self._build_document_conditions(
            doc_type=doc_type,
            property_id=property_id,
            search_term=search_term,
            date_range=date_range,
        )
        return await self.count_where(db, conditions=conditions)

    async def get_stats(self, db: AsyncSession) -> dict[str, Any]:
        """Get document statistics."""
        # Total documents count
        total_result = await db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.is_deleted.is_(False))
        )
        total_documents = total_result.scalar() or 0

        # Total size
        size_result = await db.execute(
            select(func.sum(Document.size)).where(Document.is_deleted.is_(False))
        )
        total_size = size_result.scalar() or 0

        # Count by type
        by_type: dict[str, int] = {}
        for doc_type in DocumentType:
            type_result = await db.execute(
                select(func.count())
                .select_from(Document)
                .where(Document.type == doc_type)
                .where(Document.is_deleted.is_(False))
            )
            by_type[doc_type.value] = type_result.scalar() or 0

        # Recent uploads (last 30 days)
        cutoff = datetime.now(UTC) - timedelta(days=30)
        recent_result = await db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.uploaded_at >= cutoff)
            .where(Document.is_deleted.is_(False))
        )
        recent_uploads = recent_result.scalar() or 0

        return {
            "total_documents": total_documents,
            "total_size": total_size,
            "by_type": by_type,
            "recent_uploads": recent_uploads,
        }

    async def soft_delete(self, db: AsyncSession, *, id: int) -> Document | None:
        """Soft delete a document."""
        doc = await self.get(db, id)
        if doc:
            doc.soft_delete()
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
        return doc


# Singleton instance
document = CRUDDocument(Document)
