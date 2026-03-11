"""Enhanced API response body assertion tests (T-DEBT-007, T-DEBT-008).

Many existing API tests only check status_code == 200. These tests verify
that response bodies contain the expected fields, correct types, and proper
values for:
- Properties API: field presence, types, and values
- Deals API: field presence, types, and values
- Documents API: additional field checks
- Users API: additional field checks
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models import Deal, DealStage, Property, User
from app.models.document import Document

# =============================================================================
# Helpers
# =============================================================================


async def _create_doc(db_session, name="Test Doc", property_id=None):
    doc = Document(
        name=name,
        type="financial",
        property_id=property_id,
        size=2048,
        uploaded_at=datetime.now(UTC),
        uploaded_by="test@example.com",
        description="A financial document",
        tags=["quarterly", "review"],
        url="/docs/test.pdf",
        mime_type="application/pdf",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


# =============================================================================
# Properties: response body field assertions
# =============================================================================


class TestPropertyResponseBodies:
    """Verify property API responses have expected fields and values."""

    @pytest.mark.asyncio
    async def test_get_property_has_all_core_fields(
        self, client, db_session, auth_headers, test_property
    ):
        """GET /properties/{id} returns all core property fields."""
        response = await client.get(
            f"/api/v1/properties/{test_property.id}",
            headers=auth_headers,
            follow_redirects=True,
        )
        assert response.status_code == 200
        data = response.json()

        # Core identification
        assert data["id"] == test_property.id
        assert data["name"] == "Test Property"
        assert data["property_type"] == "multifamily"

        # Location
        assert data["address"] == "123 Test St"
        assert data["city"] == "Phoenix"
        assert data["state"] == "AZ"
        assert data["zip_code"] == "85001"
        assert data["market"] == "Phoenix Metro"

        # Physical
        assert data["year_built"] == 2020
        assert data["total_units"] == 50
        assert data["total_sf"] == 50000

    @pytest.mark.asyncio
    async def test_get_property_financial_fields(
        self, client, db_session, auth_headers, test_property
    ):
        """GET /properties/{id} returns financial fields with correct types."""
        response = await client.get(
            f"/api/v1/properties/{test_property.id}",
            headers=auth_headers,
            follow_redirects=True,
        )
        data = response.json()

        # Financial fields should be present (may be string or numeric)
        assert "purchase_price" in data
        assert "cap_rate" in data
        assert "occupancy_rate" in data

        # Values should be numeric (or string representation of numeric)
        purchase = data["purchase_price"]
        assert purchase is not None
        assert float(purchase) > 0

    @pytest.mark.asyncio
    async def test_list_properties_item_structure(
        self, client, db_session, auth_headers, test_property
    ):
        """GET /properties/ list items have the same fields as single get."""
        response = await client.get(
            "/api/v1/properties/",
            headers=auth_headers,
            follow_redirects=True,
        )
        data = response.json()
        assert len(data["items"]) >= 1

        item = data["items"][0]
        # Must have at least these keys
        required_keys = {"id", "name", "property_type", "city", "state"}
        assert required_keys.issubset(item.keys())

    @pytest.mark.asyncio
    async def test_list_properties_pagination_metadata(
        self, client, db_session, auth_headers, test_property
    ):
        """GET /properties/ pagination metadata has correct types."""
        response = await client.get(
            "/api/v1/properties/",
            headers=auth_headers,
            follow_redirects=True,
        )
        data = response.json()

        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["page_size"], int)
        assert data["total"] >= 1
        assert data["page"] >= 1
        assert data["page_size"] >= 1

    @pytest.mark.asyncio
    async def test_create_property_returns_complete_object(
        self, client, db_session, admin_auth_headers
    ):
        """POST /properties/ returns the created property with all fields."""
        payload = {
            "name": "Created Property",
            "property_type": "multifamily",
            "address": "456 New St",
            "city": "Tempe",
            "state": "AZ",
            "zip_code": "85281",
            "market": "Phoenix Metro",
            "total_units": 120,
            "year_built": 2005,
        }
        response = await client.post(
            "/api/v1/properties/",
            json=payload,
            headers=admin_auth_headers,
            follow_redirects=True,
        )
        assert response.status_code == 201
        data = response.json()

        assert data["id"] is not None
        assert data["name"] == "Created Property"
        assert data["city"] == "Tempe"
        assert data["total_units"] == 120
        assert data["year_built"] == 2005

    @pytest.mark.asyncio
    async def test_update_property_reflects_changes(
        self, client, db_session, admin_auth_headers, test_property
    ):
        """PUT /properties/{id} response reflects the updated values."""
        response = await client.put(
            f"/api/v1/properties/{test_property.id}",
            json={"name": "Renamed Property", "total_units": 75},
            headers=admin_auth_headers,
            follow_redirects=True,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Renamed Property"
        assert data["total_units"] == 75
        # Unchanged fields preserved
        assert data["city"] == "Phoenix"
        assert data["state"] == "AZ"


# =============================================================================
# Deals: response body field assertions
# =============================================================================


class TestDealResponseBodies:
    """Verify deal API responses have expected fields and values."""

    @pytest.mark.asyncio
    async def test_get_deal_has_all_core_fields(
        self, client, test_deal, auth_headers
    ):
        """GET /deals/{id} returns all core deal fields."""
        response = await client.get(
            f"/api/v1/deals/{test_deal.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_deal.id
        assert data["name"] == test_deal.name
        assert data["deal_type"] == "acquisition"
        assert data["stage"] == "active_review"
        assert data["priority"] == "high"

    @pytest.mark.asyncio
    async def test_get_deal_financial_fields(
        self, client, test_deal, auth_headers
    ):
        """GET /deals/{id} returns financial projections."""
        response = await client.get(
            f"/api/v1/deals/{test_deal.id}", headers=auth_headers
        )
        data = response.json()

        # Financial fields present and numeric
        assert "asking_price" in data
        assert "offer_price" in data
        assert data["asking_price"] is not None
        assert float(data["asking_price"]) > 0

    @pytest.mark.asyncio
    async def test_get_deal_projection_fields(
        self, client, test_deal, auth_headers
    ):
        """GET /deals/{id} returns IRR, CoC, equity multiple."""
        response = await client.get(
            f"/api/v1/deals/{test_deal.id}", headers=auth_headers
        )
        data = response.json()

        assert "projected_irr" in data
        assert "projected_coc" in data
        assert "projected_equity_multiple" in data
        assert "hold_period_years" in data

    @pytest.mark.asyncio
    async def test_list_deals_item_structure(
        self, client, multiple_deals, auth_headers
    ):
        """GET /deals/ list items have expected fields."""
        response = await client.get(
            "/api/v1/deals/", headers=auth_headers
        )
        data = response.json()
        assert len(data["items"]) >= 1

        item = data["items"][0]
        required_keys = {"id", "name", "deal_type", "stage"}
        assert required_keys.issubset(item.keys())

    @pytest.mark.asyncio
    async def test_list_deals_pagination_types(
        self, client, multiple_deals, auth_headers
    ):
        """GET /deals/ pagination fields have correct types."""
        response = await client.get(
            "/api/v1/deals/", headers=auth_headers
        )
        data = response.json()

        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["page_size"], int)

    @pytest.mark.asyncio
    async def test_create_deal_returns_complete_object(
        self, client, admin_auth_headers
    ):
        """POST /deals/ returns full deal with all created fields."""
        payload = {
            "name": "Full Body Deal",
            "deal_type": "acquisition",
            "stage": "initial_review",
            "asking_price": 20000000,
            "priority": "medium",
            "source": "Marcus & Millichap",
        }
        response = await client.post(
            "/api/v1/deals/", json=payload, headers=admin_auth_headers
        )
        assert response.status_code == 201
        data = response.json()

        assert data["id"] is not None
        assert data["name"] == "Full Body Deal"
        assert data["deal_type"] == "acquisition"
        assert data["stage"] == "initial_review"
        assert data["priority"] == "medium"

    @pytest.mark.asyncio
    async def test_kanban_board_structure(
        self, client, multiple_deals, auth_headers
    ):
        """GET /deals/kanban response has complete structure."""
        response = await client.get(
            "/api/v1/deals/kanban", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["stages"], dict)
        assert isinstance(data["total_deals"], int)
        assert isinstance(data["stage_counts"], dict)

        # Every DealStage value should be a key
        for stage in DealStage:
            assert stage.value in data["stages"]
            assert stage.value in data["stage_counts"]
            assert isinstance(data["stage_counts"][stage.value], int)

    @pytest.mark.asyncio
    async def test_deal_stage_update_returns_new_stage(
        self, client, test_deal, admin_auth_headers
    ):
        """PATCH /deals/{id}/stage response contains updated stage."""
        response = await client.patch(
            f"/api/v1/deals/{test_deal.id}/stage",
            json={"stage": "under_contract"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["stage"] == "under_contract"
        assert data["id"] == test_deal.id
        assert data["name"] == test_deal.name  # Unchanged

    @pytest.mark.asyncio
    async def test_update_deal_preserves_unchanged_fields(
        self, client, test_deal, admin_auth_headers
    ):
        """PUT /deals/{id} preserves fields not in the update payload."""
        response = await client.put(
            f"/api/v1/deals/{test_deal.id}",
            json={"version": 1, "priority": "low"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["priority"] == "low"
        assert data["name"] == test_deal.name
        assert data["deal_type"] == "acquisition"


# =============================================================================
# Documents: response body field assertions
# =============================================================================


class TestDocumentResponseBodies:
    """Verify document API responses have expected fields and values."""

    @pytest.mark.asyncio
    async def test_get_document_all_fields(
        self, client, db_session, auth_headers
    ):
        """GET /documents/{id} returns all document fields."""
        doc = await _create_doc(db_session)
        response = await client.get(
            f"/api/v1/documents/{doc.id}",
            headers=auth_headers,
            follow_redirects=True,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == doc.id
        assert data["name"] == "Test Doc"
        assert data["type"] == "financial"
        assert data["size"] == 2048
        assert data["uploaded_by"] == "test@example.com"
        assert data["description"] == "A financial document"
        assert data["url"] == "/docs/test.pdf"
        assert data["mime_type"] == "application/pdf"
        assert "uploaded_at" in data

    @pytest.mark.asyncio
    async def test_create_document_response_structure(
        self, client, db_session, auth_headers
    ):
        """POST /documents/ response has full document structure."""
        payload = {
            "name": "New Lease",
            "type": "lease",
            "size": 5000,
            "description": "Building lease",
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

        assert data["id"] is not None
        assert data["name"] == "New Lease"
        assert data["type"] == "lease"

    @pytest.mark.asyncio
    async def test_list_documents_items_complete(
        self, client, db_session, auth_headers
    ):
        """GET /documents/ list items have all expected fields."""
        await _create_doc(db_session, "Doc A")
        await _create_doc(db_session, "Doc B")

        response = await client.get(
            "/api/v1/documents/",
            headers=auth_headers,
            follow_redirects=True,
        )
        data = response.json()

        assert data["total"] == 2
        for item in data["items"]:
            assert "id" in item
            assert "name" in item
            assert "type" in item
            assert "size" in item
            assert "uploaded_at" in item


# =============================================================================
# Users: response body field assertions
# =============================================================================


class TestUserResponseBodies:
    """Verify user API responses have expected fields and values."""

    @pytest.mark.asyncio
    async def test_get_user_all_fields(
        self, client, db_session, admin_auth_headers, admin_user
    ):
        """GET /users/{id} returns all user fields."""
        response = await client.get(
            f"/api/v1/users/{admin_user.id}",
            headers=admin_auth_headers,
            follow_redirects=True,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == admin_user.id
        assert data["email"] == "admin@example.com"
        assert data["full_name"] == "Admin User"
        assert data["role"] == "admin"
        assert data["is_active"] is True
        assert data["department"] == "Executive"
        # Security: password should never be exposed
        assert "password" not in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_list_users_items_have_required_fields(
        self, client, db_session, admin_auth_headers, admin_user
    ):
        """GET /users/ list items have all required user fields."""
        response = await client.get(
            "/api/v1/users/",
            headers=admin_auth_headers,
            follow_redirects=True,
        )
        data = response.json()

        assert len(data["items"]) >= 1
        for user in data["items"]:
            required_keys = {"id", "email", "full_name", "role", "is_active"}
            assert required_keys.issubset(user.keys())
            assert "password" not in user
            assert "hashed_password" not in user

    @pytest.mark.asyncio
    async def test_create_user_returns_all_fields(
        self, client, db_session, admin_auth_headers
    ):
        """POST /users/ returns complete user without secrets."""
        payload = {
            "email": "bodycheck@test.com",
            "password": "SecurePassword123!",
            "full_name": "Body Check User",
            "role": "analyst",
            "department": "Research",
        }
        response = await client.post(
            "/api/v1/users/",
            json=payload,
            headers=admin_auth_headers,
            follow_redirects=True,
        )
        assert response.status_code == 201
        data = response.json()

        assert data["email"] == "bodycheck@test.com"
        assert data["full_name"] == "Body Check User"
        assert data["role"] == "analyst"
        assert data["department"] == "Research"
        assert data["is_active"] is True
        assert "password" not in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_update_user_returns_updated_fields(
        self, client, db_session, admin_auth_headers, test_user
    ):
        """PUT /users/{id} response reflects updated values."""
        response = await client.put(
            f"/api/v1/users/{test_user.id}",
            json={"full_name": "Updated Full Name", "department": "Analytics"},
            headers=admin_auth_headers,
            follow_redirects=True,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["full_name"] == "Updated Full Name"
        assert data["department"] == "Analytics"
        # Unchanged
        assert data["email"] == test_user.email
        assert data["role"] == "analyst"


# =============================================================================
# Error response body assertions
# =============================================================================


class TestErrorResponseBodies:
    """Verify error responses have proper structure."""

    @pytest.mark.asyncio
    async def test_404_has_detail_field(
        self, client, auth_headers
    ):
        """404 responses include a 'detail' field."""
        response = await client.get(
            "/api/v1/properties/99999",
            headers=auth_headers,
            follow_redirects=True,
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

    @pytest.mark.asyncio
    async def test_401_has_detail_field(self, client):
        """401 responses include a 'detail' field."""
        response = await client.get(
            "/api/v1/properties/", follow_redirects=True
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_422_has_detail_array(self, client, admin_auth_headers):
        """422 validation errors include structured detail."""
        response = await client.post(
            "/api/v1/properties/",
            json={"name": "X", "property_type": "invalid_type"},
            headers=admin_auth_headers,
            follow_redirects=True,
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # FastAPI validation errors return a list
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0

    @pytest.mark.asyncio
    async def test_deal_not_found_message(self, client, auth_headers):
        """Deal 404 includes descriptive message."""
        response = await client.get(
            "/api/v1/deals/999999", headers=auth_headers
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
