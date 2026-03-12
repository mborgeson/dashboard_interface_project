"""Tests for Document CRUD operations.

Covers CRUDDocument:
- get_by_property: retrieval by property ID
- get_by_type: retrieval by document type
- get_filtered / count_filtered: multi-filter queries
- get_stats: aggregate statistics
- soft_delete: soft-delete a document
- _date_range_cutoff: static helper
- _build_document_conditions: filter condition builder
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.crud.crud_document import document as document_crud
from app.models.document import Document, DocumentType

# =============================================================================
# Fixtures
# =============================================================================


async def _create_document(
    db_session,
    name: str = "Test Doc",
    doc_type: str = "financial",
    property_id: int | None = None,
    size: int = 1024,
    uploaded_at: datetime | None = None,
    description: str | None = None,
) -> Document:
    """Insert a document directly for testing."""
    doc = Document(
        name=name,
        type=doc_type,
        property_id=property_id,
        size=size,
        uploaded_at=uploaded_at or datetime.now(UTC),
        uploaded_by="test@example.com",
        description=description,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(doc)
    await db_session.flush()
    await db_session.refresh(doc)
    return doc


# =============================================================================
# get_by_property
# =============================================================================


class TestGetByProperty:
    """Tests for get_by_property."""

    @pytest.mark.asyncio
    async def test_returns_documents_for_property(self, db_session, test_property):
        """get_by_property returns documents linked to the property."""
        await _create_document(db_session, "Doc A", property_id=test_property.id)
        await _create_document(db_session, "Doc B", property_id=test_property.id)

        results = await document_crud.get_by_property(
            db_session, property_id=test_property.id
        )
        assert len(results) == 2
        for doc in results:
            assert doc.property_id == test_property.id

    @pytest.mark.asyncio
    async def test_excludes_other_properties(self, db_session, test_property):
        """get_by_property does not return documents from other properties."""
        await _create_document(db_session, "Doc A", property_id=test_property.id)
        await _create_document(db_session, "Doc B", property_id=99999)

        results = await document_crud.get_by_property(
            db_session, property_id=test_property.id
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_empty_for_unknown_property(self, db_session):
        """get_by_property returns empty list for unknown property."""
        results = await document_crud.get_by_property(db_session, property_id=99999)
        assert results == []

    @pytest.mark.asyncio
    async def test_excludes_soft_deleted(self, db_session, test_property):
        """get_by_property excludes soft-deleted documents."""
        doc = await _create_document(
            db_session, "Deleted Doc", property_id=test_property.id
        )
        doc.is_deleted = True
        doc.deleted_at = datetime.now(UTC)
        db_session.add(doc)
        await db_session.flush()

        results = await document_crud.get_by_property(
            db_session, property_id=test_property.id
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_pagination(self, db_session, test_property):
        """get_by_property supports skip and limit."""
        for i in range(5):
            await _create_document(db_session, f"Doc {i}", property_id=test_property.id)

        page1 = await document_crud.get_by_property(
            db_session, property_id=test_property.id, skip=0, limit=2
        )
        assert len(page1) == 2

        page2 = await document_crud.get_by_property(
            db_session, property_id=test_property.id, skip=2, limit=2
        )
        assert len(page2) == 2


# =============================================================================
# get_by_type
# =============================================================================


class TestGetByType:
    """Tests for get_by_type."""

    @pytest.mark.asyncio
    async def test_returns_documents_of_type(self, db_session):
        """get_by_type returns only documents matching the type."""
        await _create_document(db_session, "Lease A", doc_type="lease")
        await _create_document(db_session, "Financial B", doc_type="financial")

        leases = await document_crud.get_by_type(
            db_session, doc_type=DocumentType.LEASE
        )
        assert len(leases) == 1
        assert leases[0].type == "lease"

    @pytest.mark.asyncio
    async def test_excludes_soft_deleted(self, db_session):
        """get_by_type excludes soft-deleted documents."""
        doc = await _create_document(db_session, "Deleted", doc_type="legal")
        doc.is_deleted = True
        doc.deleted_at = datetime.now(UTC)
        db_session.add(doc)
        await db_session.flush()

        results = await document_crud.get_by_type(
            db_session, doc_type=DocumentType.LEGAL
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_empty_for_unused_type(self, db_session):
        """get_by_type returns empty list when no docs of that type exist."""
        results = await document_crud.get_by_type(
            db_session, doc_type=DocumentType.PHOTO
        )
        assert results == []


# =============================================================================
# _date_range_cutoff
# =============================================================================


class TestDateRangeCutoff:
    """Tests for the static _date_range_cutoff helper."""

    def test_none_returns_none(self):
        assert document_crud._date_range_cutoff(None) is None

    def test_all_returns_none(self):
        assert document_crud._date_range_cutoff("all") is None

    def test_7days(self):
        cutoff = document_crud._date_range_cutoff("7days")
        assert cutoff is not None
        delta = datetime.now(UTC) - cutoff
        assert 6 <= delta.days <= 7

    def test_30days(self):
        cutoff = document_crud._date_range_cutoff("30days")
        assert cutoff is not None
        delta = datetime.now(UTC) - cutoff
        assert 29 <= delta.days <= 30

    def test_90days(self):
        cutoff = document_crud._date_range_cutoff("90days")
        assert cutoff is not None
        delta = datetime.now(UTC) - cutoff
        assert 89 <= delta.days <= 90

    def test_1year(self):
        cutoff = document_crud._date_range_cutoff("1year")
        assert cutoff is not None
        delta = datetime.now(UTC) - cutoff
        assert 364 <= delta.days <= 365

    def test_unknown_range_returns_none(self):
        assert document_crud._date_range_cutoff("2weeks") is None


# =============================================================================
# _build_document_conditions
# =============================================================================


class TestBuildDocumentConditions:
    """Tests for _build_document_conditions."""

    def test_no_filters(self):
        conditions = document_crud._build_document_conditions()
        assert conditions == []

    def test_doc_type_filter(self):
        conditions = document_crud._build_document_conditions(doc_type="lease")
        assert len(conditions) == 1

    def test_doc_type_all_ignored(self):
        conditions = document_crud._build_document_conditions(doc_type="all")
        assert conditions == []

    def test_invalid_doc_type_ignored(self):
        conditions = document_crud._build_document_conditions(
            doc_type="nonexistent_type"
        )
        assert conditions == []

    def test_property_id_filter(self):
        conditions = document_crud._build_document_conditions(property_id=42)
        assert len(conditions) == 1

    def test_search_term_filter(self):
        conditions = document_crud._build_document_conditions(
            search_term="lease agreement"
        )
        assert len(conditions) == 1

    def test_date_range_filter(self):
        conditions = document_crud._build_document_conditions(date_range="7days")
        assert len(conditions) == 1

    def test_multiple_filters(self):
        conditions = document_crud._build_document_conditions(
            doc_type="financial",
            property_id=1,
            search_term="rent",
            date_range="30days",
        )
        assert len(conditions) == 4


# =============================================================================
# get_filtered / count_filtered
# =============================================================================


class TestGetFiltered:
    """Tests for get_filtered and count_filtered."""

    @pytest.mark.asyncio
    async def test_returns_all_when_no_filters(self, db_session):
        """get_filtered returns all non-deleted documents."""
        await _create_document(db_session, "Doc 1")
        await _create_document(db_session, "Doc 2")

        results = await document_crud.get_filtered(db_session)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filters_by_type(self, db_session):
        """get_filtered filters by document type."""
        await _create_document(db_session, "Lease", doc_type="lease")
        await _create_document(db_session, "Financial", doc_type="financial")

        results = await document_crud.get_filtered(db_session, doc_type="lease")
        assert len(results) == 1
        assert results[0].type == "lease"

    @pytest.mark.asyncio
    async def test_filters_by_property(self, db_session, test_property):
        """get_filtered filters by property_id."""
        await _create_document(db_session, "A", property_id=test_property.id)
        await _create_document(db_session, "B", property_id=99999)

        results = await document_crud.get_filtered(
            db_session, property_id=test_property.id
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_filters_by_search_term(self, db_session):
        """get_filtered filters by search term in name or description."""
        await _create_document(
            db_session, "Rent Roll Q4", description="Quarterly rent roll"
        )
        await _create_document(db_session, "Tax Return", description="2024 taxes")

        results = await document_crud.get_filtered(db_session, search_term="rent")
        assert len(results) == 1
        assert "Rent" in results[0].name

    @pytest.mark.asyncio
    async def test_count_filtered_matches(self, db_session):
        """count_filtered returns correct count matching get_filtered."""
        await _create_document(db_session, "Lease 1", doc_type="lease")
        await _create_document(db_session, "Lease 2", doc_type="lease")
        await _create_document(db_session, "Financial", doc_type="financial")

        count = await document_crud.count_filtered(db_session, doc_type="lease")
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_filtered_no_filters(self, db_session):
        """count_filtered returns total when no filters applied."""
        await _create_document(db_session, "A")
        await _create_document(db_session, "B")
        await _create_document(db_session, "C")

        count = await document_crud.count_filtered(db_session)
        assert count == 3

    @pytest.mark.asyncio
    async def test_pagination(self, db_session):
        """get_filtered supports skip and limit."""
        for i in range(5):
            await _create_document(db_session, f"Doc {i}")

        results = await document_crud.get_filtered(db_session, skip=0, limit=2)
        assert len(results) == 2


# =============================================================================
# get_stats
# =============================================================================


class TestGetStats:
    """Tests for get_stats."""

    @pytest.mark.asyncio
    async def test_empty_database(self, db_session):
        """get_stats returns zeros when no documents exist."""
        stats = await document_crud.get_stats(db_session)
        assert stats["total_documents"] == 0
        assert stats["total_size"] == 0
        assert stats["recent_uploads"] == 0
        assert isinstance(stats["by_type"], dict)
        # All document types should be present with 0
        for dt in DocumentType:
            assert stats["by_type"][dt.value] == 0

    @pytest.mark.asyncio
    async def test_counts_and_size(self, db_session):
        """get_stats reports correct totals."""
        await _create_document(db_session, "A", size=1024, doc_type="lease")
        await _create_document(db_session, "B", size=2048, doc_type="financial")
        await _create_document(db_session, "C", size=512, doc_type="lease")

        stats = await document_crud.get_stats(db_session)
        assert stats["total_documents"] == 3
        assert stats["total_size"] == 1024 + 2048 + 512
        assert stats["by_type"]["lease"] == 2
        assert stats["by_type"]["financial"] == 1

    @pytest.mark.asyncio
    async def test_recent_uploads_count(self, db_session):
        """get_stats counts documents uploaded in the last 30 days."""
        now = datetime.now(UTC)
        # Recent upload
        await _create_document(db_session, "Recent", uploaded_at=now)
        # Old upload
        await _create_document(db_session, "Old", uploaded_at=now - timedelta(days=60))

        stats = await document_crud.get_stats(db_session)
        assert stats["total_documents"] == 2
        assert stats["recent_uploads"] == 1

    @pytest.mark.asyncio
    async def test_excludes_soft_deleted(self, db_session):
        """get_stats excludes soft-deleted documents."""
        doc = await _create_document(db_session, "Deleted")
        doc.is_deleted = True
        doc.deleted_at = datetime.now(UTC)
        db_session.add(doc)
        await db_session.flush()

        await _create_document(db_session, "Active")

        stats = await document_crud.get_stats(db_session)
        assert stats["total_documents"] == 1


# =============================================================================
# soft_delete
# =============================================================================


class TestSoftDelete:
    """Tests for soft_delete."""

    @pytest.mark.asyncio
    async def test_marks_as_deleted(self, db_session):
        """soft_delete sets is_deleted=True and deleted_at."""
        doc = await _create_document(db_session, "To Delete")
        result = await document_crud.soft_delete(db_session, id=doc.id)

        assert result is not None
        assert result.is_deleted is True
        assert result.deleted_at is not None

    @pytest.mark.asyncio
    async def test_nonexistent_returns_none(self, db_session):
        """soft_delete returns None for nonexistent document."""
        result = await document_crud.soft_delete(db_session, id=99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_deleted_not_returned_by_get(self, db_session):
        """After soft_delete, get() should not return the document."""
        doc = await _create_document(db_session, "To Delete")
        await document_crud.soft_delete(db_session, id=doc.id)

        found = await document_crud.get(db_session, doc.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_deleted_returned_with_include_deleted(self, db_session):
        """After soft_delete, get(include_deleted=True) returns the document."""
        doc = await _create_document(db_session, "Soft Deleted")
        await document_crud.soft_delete(db_session, id=doc.id)

        found = await document_crud.get(db_session, doc.id, include_deleted=True)
        assert found is not None
        assert found.is_deleted is True


# =============================================================================
# Document.get_size_formatted
# =============================================================================


class TestGetSizeFormatted:
    """Tests for Document.get_size_formatted() model method."""

    def test_bytes(self):
        doc = Document(name="t", type="other", size=500, uploaded_at=datetime.now(UTC))
        assert doc.get_size_formatted() == "500 B"

    def test_kilobytes(self):
        doc = Document(name="t", type="other", size=2048, uploaded_at=datetime.now(UTC))
        assert doc.get_size_formatted() == "2.0 KB"

    def test_megabytes(self):
        doc = Document(
            name="t", type="other", size=5 * 1024 * 1024, uploaded_at=datetime.now(UTC)
        )
        assert doc.get_size_formatted() == "5.0 MB"

    def test_gigabytes(self):
        doc = Document(
            name="t",
            type="other",
            size=2 * 1024 * 1024 * 1024,
            uploaded_at=datetime.now(UTC),
        )
        assert doc.get_size_formatted() == "2.0 GB"

    def test_zero_bytes(self):
        doc = Document(name="t", type="other", size=0, uploaded_at=datetime.now(UTC))
        assert doc.get_size_formatted() == "0 B"

    def test_boundary_1024(self):
        doc = Document(name="t", type="other", size=1024, uploaded_at=datetime.now(UTC))
        assert doc.get_size_formatted() == "1.0 KB"
