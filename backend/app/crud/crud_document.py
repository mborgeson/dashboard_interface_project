"""
CRUD operations for Document model.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, func, or_, select
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
        property_id: int,
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
        property_id: int | None = None,
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

        if property_id is not None:
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
        property_id: int | None = None,
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
        property_id: int | None = None,
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
        """Get document statistics.

        Optimized to use a single GROUP BY query for per-type counts
        instead of N separate COUNT queries (one per DocumentType).
        """
        # Single query for total count, total size, and recent uploads count
        cutoff = datetime.now(UTC) - timedelta(days=30)
        agg_result = await db.execute(
            select(
                func.count().label("total"),
                func.coalesce(func.sum(Document.size), 0).label("total_size"),
                func.sum(case((Document.uploaded_at >= cutoff, 1), else_=0)).label(
                    "recent"
                ),
            )
            .select_from(Document)
            .where(Document.is_deleted.is_(False))
        )
        agg_row = agg_result.one()
        total_documents = agg_row.total or 0
        total_size = agg_row.total_size or 0
        recent_uploads = agg_row.recent or 0

        # Single GROUP BY query for per-type counts (replaces N+1 loop)
        type_result = await db.execute(
            select(Document.type, func.count().label("cnt"))
            .where(Document.is_deleted.is_(False))
            .group_by(Document.type)
        )
        type_counts = {row.type: row.cnt for row in type_result.all()}

        # Ensure all document types are present (defaulting to 0)
        by_type: dict[str, int] = {
            dt.value: type_counts.get(dt.value, 0) for dt in DocumentType
        }

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
