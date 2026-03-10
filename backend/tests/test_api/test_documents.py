"""Tests for document API endpoints.

F-035: Tests the Documents API at /api/v1/documents/ including:
- List documents (GET /)
- Get document by ID (GET /{id})
- Create document (POST /)
- Upload requires auth (POST /upload)
- Get by property (GET /property/{property_id})
- Delete (DELETE /{id})
- Auth guards (401 without auth)
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document

# =============================================================================
# Helpers
# =============================================================================


async def _create_document(
    db_session: AsyncSession,
    name: str = "Test Document",
    doc_type: str = "financial",
    property_id: int | None = None,
) -> Document:
    """Insert a document directly into the DB for testing."""
    doc = Document(
        name=name,
        type=doc_type,
        property_id=property_id,
        size=1024,
        uploaded_at=datetime.now(UTC),
        uploaded_by="test@example.com",
        description="Test document",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


# =============================================================================
# Auth Guard Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_documents_requires_auth(client, db_session):
    """GET /documents/ without auth returns 401."""
    response = await client.get("/api/v1/documents/", follow_redirects=True)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_document_requires_auth(client, db_session):
    """GET /documents/{id} without auth returns 401."""
    response = await client.get("/api/v1/documents/1", follow_redirects=True)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_document_requires_auth(client, db_session):
    """POST /documents/ without auth returns 401."""
    payload = {"name": "Test", "type": "financial"}
    response = await client.post(
        "/api/v1/documents/", json=payload, follow_redirects=True
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_document_requires_auth(client, db_session):
    """DELETE /documents/{id} without auth returns 401."""
    response = await client.delete("/api/v1/documents/1", follow_redirects=True)
    assert response.status_code == 401


# =============================================================================
# List Documents (GET /)
# =============================================================================


@pytest.mark.asyncio
async def test_list_documents_empty(client, db_session, auth_headers):
    """GET /documents/ returns empty paginated response when no documents exist."""
    response = await client.get(
        "/api/v1/documents/", headers=auth_headers, follow_redirects=True
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_documents_with_data(client, db_session, auth_headers):
    """GET /documents/ returns documents when they exist."""
    await _create_document(db_session, name="Doc A")
    await _create_document(db_session, name="Doc B")

    response = await client.get(
        "/api/v1/documents/", headers=auth_headers, follow_redirects=True
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_documents_pagination(client, db_session, auth_headers):
    """GET /documents/ respects page and page_size params."""
    for i in range(5):
        await _create_document(db_session, name=f"Doc {i}")

    response = await client.get(
        "/api/v1/documents/",
        params={"page": 1, "page_size": 2},
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert data["total"] == 5


# =============================================================================
# Get Document by ID (GET /{id})
# =============================================================================


@pytest.mark.asyncio
async def test_get_document_by_id(client, db_session, auth_headers):
    """GET /documents/{id} returns the document."""
    doc = await _create_document(db_session)

    response = await client.get(
        f"/api/v1/documents/{doc.id}", headers=auth_headers, follow_redirects=True
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc.id
    assert data["name"] == "Test Document"


@pytest.mark.asyncio
async def test_get_document_not_found(client, db_session, auth_headers):
    """GET /documents/{id} returns 404 for nonexistent document."""
    response = await client.get(
        "/api/v1/documents/99999", headers=auth_headers, follow_redirects=True
    )
    assert response.status_code == 404


# =============================================================================
# Create Document (POST /)
# =============================================================================


@pytest.mark.asyncio
async def test_create_document(client, db_session, auth_headers):
    """POST /documents/ creates a document and returns 201."""
    payload = {
        "name": "New Document",
        "type": "lease",
        "description": "A lease document",
        "uploaded_at": datetime.now(UTC).isoformat(),
    }
    response = await client.post(
        "/api/v1/documents/",
        json=payload,
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Document"
    assert data["type"] == "lease"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_document_invalid_type(client, db_session, auth_headers):
    """POST /documents/ with invalid type returns 422."""
    payload = {"name": "Bad Doc", "type": "invalid_type"}
    response = await client.post(
        "/api/v1/documents/",
        json=payload,
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 422


# =============================================================================
# Upload requires auth (POST /upload)
# =============================================================================


@pytest.mark.asyncio
async def test_upload_requires_auth(client, db_session):
    """POST /documents/upload without auth returns 401."""
    response = await client.post(
        "/api/v1/documents/upload", follow_redirects=True
    )
    assert response.status_code == 401


# =============================================================================
# Get by Property (GET /property/{property_id})
# =============================================================================


@pytest.mark.asyncio
async def test_get_documents_by_property(client, db_session, auth_headers):
    """GET /documents/property/{property_id} returns documents for that property."""
    await _create_document(db_session, name="Prop Doc", property_id=123)
    await _create_document(db_session, name="Other Doc", property_id=456)

    response = await client.get(
        "/api/v1/documents/property/123",
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["property_id"] == 123


@pytest.mark.asyncio
async def test_get_documents_by_property_empty(client, db_session, auth_headers):
    """GET /documents/property/{property_id} returns empty for unknown property."""
    response = await client.get(
        "/api/v1/documents/property/99999",
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


# =============================================================================
# Delete Document (DELETE /{id})
# =============================================================================


@pytest.mark.asyncio
async def test_delete_document(client, db_session, admin_auth_headers):
    """DELETE /documents/{id} soft-deletes the document and returns 204."""
    doc = await _create_document(db_session)

    response = await client.delete(
        f"/api/v1/documents/{doc.id}",
        headers=admin_auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_document_not_found(client, db_session, admin_auth_headers):
    """DELETE /documents/{id} returns 404 for nonexistent document."""
    response = await client.delete(
        "/api/v1/documents/99999",
        headers=admin_auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deleted_document_not_gettable(client, db_session, admin_auth_headers, auth_headers):
    """After soft-delete, GET /documents/{id} should return 404."""
    doc = await _create_document(db_session)

    # Delete it
    await client.delete(
        f"/api/v1/documents/{doc.id}",
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    # Try to get it
    response = await client.get(
        f"/api/v1/documents/{doc.id}",
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 404
