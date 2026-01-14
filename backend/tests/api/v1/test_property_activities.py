"""
Tests for Property Activities API endpoints.

Tests the following endpoints:
- GET /api/v1/properties/{id}/activities - List activities for a property
- POST /api/v1/properties/{id}/activities - Create a new activity

Covers:
- Pagination (skip, limit)
- Filtering by activity_type
- All activity types (view, edit, comment, status_change, document_upload)
- Authentication requirements
- 404 for non-existent properties
"""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Property, User
from app.models.activity import ActivityType, PropertyActivity


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def property_with_activities(
    db_session: AsyncSession, test_property: Property, test_user: User
) -> Property:
    """Create a property with multiple activity records."""
    # Create activities of different types
    activities_data = [
        {
            "activity_type": ActivityType.VIEW,
            "description": "Viewed property details",
        },
        {
            "activity_type": ActivityType.VIEW,
            "description": "Viewed property again",
        },
        {
            "activity_type": ActivityType.EDIT,
            "description": "Updated occupancy rate",
            "field_changed": "occupancy_rate",
            "old_value": "95.0",
            "new_value": "97.5",
        },
        {
            "activity_type": ActivityType.COMMENT,
            "description": "Added comment",
            "comment_text": "This property looks promising for acquisition.",
        },
        {
            "activity_type": ActivityType.STATUS_CHANGE,
            "description": "Changed status",
            "field_changed": "status",
            "old_value": "active",
            "new_value": "under_review",
        },
        {
            "activity_type": ActivityType.DOCUMENT_UPLOAD,
            "description": "Uploaded rent roll",
            "document_name": "rent_roll_2024.pdf",
            "document_url": "https://storage.example.com/docs/rent_roll_2024.pdf",
        },
    ]

    for data in activities_data:
        activity = PropertyActivity(
            property_id=test_property.id,
            user_id=test_user.id,
            **data,
        )
        db_session.add(activity)

    await db_session.commit()
    return test_property


@pytest_asyncio.fixture
async def many_activities(
    db_session: AsyncSession, test_property: Property, test_user: User
) -> Property:
    """Create a property with many activities for pagination testing."""
    for i in range(25):
        activity = PropertyActivity(
            property_id=test_property.id,
            user_id=test_user.id,
            activity_type=ActivityType.VIEW,
            description=f"View activity {i + 1}",
        )
        db_session.add(activity)

    await db_session.commit()
    return test_property


# =============================================================================
# GET /api/v1/properties/{id}/activities Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_property_activities_requires_auth(client, test_property):
    """Test that getting property activities requires authentication."""
    response = await client.get(f"/api/v1/properties/{test_property.id}/activities")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_property_activities_success(
    client, property_with_activities, auth_headers
):
    """Test successfully getting property activities."""
    response = await client.get(
        f"/api/v1/properties/{property_with_activities.id}/activities",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["total"] == 6  # We created 6 activities
    assert len(data["items"]) == 6


@pytest.mark.asyncio
async def test_get_property_activities_pagination_skip(
    client, many_activities, auth_headers
):
    """Test pagination with skip parameter."""
    response = await client.get(
        f"/api/v1/properties/{many_activities.id}/activities",
        params={"skip": 10, "limit": 10},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["page"] == 2  # skip=10, limit=10 means page 2


@pytest.mark.asyncio
async def test_get_property_activities_pagination_limit(
    client, many_activities, auth_headers
):
    """Test pagination with limit parameter."""
    response = await client.get(
        f"/api/v1/properties/{many_activities.id}/activities",
        params={"limit": 5},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 5
    assert data["total"] == 25
    assert data["page_size"] == 5


@pytest.mark.asyncio
async def test_get_property_activities_filter_by_view_type(
    client, property_with_activities, auth_headers
):
    """Test filtering activities by view type."""
    response = await client.get(
        f"/api/v1/properties/{property_with_activities.id}/activities",
        params={"activity_type": "view"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2  # We created 2 view activities
    for item in data["items"]:
        assert item["activity_type"] == "view"


@pytest.mark.asyncio
async def test_get_property_activities_filter_by_edit_type(
    client, property_with_activities, auth_headers
):
    """Test filtering activities by edit type."""
    response = await client.get(
        f"/api/v1/properties/{property_with_activities.id}/activities",
        params={"activity_type": "edit"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["activity_type"] == "edit"
    assert data["items"][0]["field_changed"] == "occupancy_rate"


@pytest.mark.asyncio
async def test_get_property_activities_filter_by_comment_type(
    client, property_with_activities, auth_headers
):
    """Test filtering activities by comment type."""
    response = await client.get(
        f"/api/v1/properties/{property_with_activities.id}/activities",
        params={"activity_type": "comment"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["activity_type"] == "comment"
    assert "promising" in data["items"][0]["comment_text"]


@pytest.mark.asyncio
async def test_get_property_activities_filter_by_status_change_type(
    client, property_with_activities, auth_headers
):
    """Test filtering activities by status_change type."""
    response = await client.get(
        f"/api/v1/properties/{property_with_activities.id}/activities",
        params={"activity_type": "status_change"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["activity_type"] == "status_change"
    assert data["items"][0]["old_value"] == "active"
    assert data["items"][0]["new_value"] == "under_review"


@pytest.mark.asyncio
async def test_get_property_activities_filter_by_document_upload_type(
    client, property_with_activities, auth_headers
):
    """Test filtering activities by document_upload type."""
    response = await client.get(
        f"/api/v1/properties/{property_with_activities.id}/activities",
        params={"activity_type": "document_upload"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["activity_type"] == "document_upload"
    assert data["items"][0]["document_name"] == "rent_roll_2024.pdf"


@pytest.mark.asyncio
async def test_get_property_activities_invalid_filter_type(
    client, property_with_activities, auth_headers
):
    """Test filtering with invalid activity type returns 400."""
    response = await client.get(
        f"/api/v1/properties/{property_with_activities.id}/activities",
        params={"activity_type": "invalid_type"},
        headers=auth_headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "Invalid activity_type" in data["detail"]


@pytest.mark.asyncio
async def test_get_property_activities_not_found(client, auth_headers):
    """Test 404 for non-existent property."""
    response = await client.get(
        "/api/v1/properties/999999/activities",
        headers=auth_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_property_activities_response_structure(
    client, property_with_activities, auth_headers
):
    """Test that activity response has expected structure."""
    response = await client.get(
        f"/api/v1/properties/{property_with_activities.id}/activities",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check at least one item
    assert len(data["items"]) > 0

    item = data["items"][0]
    required_fields = [
        "id",
        "property_id",
        "user_id",
        "activity_type",
        "created_at",
        "updated_at",
    ]
    for field in required_fields:
        assert field in item


# =============================================================================
# POST /api/v1/properties/{id}/activities Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_activity_requires_auth(client, test_property):
    """Test that creating activity requires authentication."""
    activity_data = {
        "property_id": test_property.id,
        "activity_type": "view",
        "description": "Viewed property",
    }

    response = await client.post(
        f"/api/v1/properties/{test_property.id}/activities",
        json=activity_data,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_view_activity(client, test_property, auth_headers):
    """Test creating a view activity."""
    activity_data = {
        "property_id": test_property.id,
        "activity_type": "view",
        "description": "Viewed property details",
    }

    response = await client.post(
        f"/api/v1/properties/{test_property.id}/activities",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["activity_type"] == "view"
    assert data["property_id"] == test_property.id
    assert "id" in data


@pytest.mark.asyncio
async def test_create_edit_activity(client, test_property, auth_headers):
    """Test creating an edit activity with field changes."""
    activity_data = {
        "property_id": test_property.id,
        "activity_type": "edit",
        "description": "Updated rent",
        "field_changed": "avg_rent_per_unit",
        "old_value": "1500",
        "new_value": "1600",
    }

    response = await client.post(
        f"/api/v1/properties/{test_property.id}/activities",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["activity_type"] == "edit"
    assert data["field_changed"] == "avg_rent_per_unit"
    assert data["old_value"] == "1500"
    assert data["new_value"] == "1600"


@pytest.mark.asyncio
async def test_create_comment_activity(client, test_property, auth_headers):
    """Test creating a comment activity."""
    activity_data = {
        "property_id": test_property.id,
        "activity_type": "comment",
        "description": "Added comment",
        "comment_text": "Great investment opportunity with strong fundamentals.",
    }

    response = await client.post(
        f"/api/v1/properties/{test_property.id}/activities",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["activity_type"] == "comment"
    assert data["comment_text"] == "Great investment opportunity with strong fundamentals."


@pytest.mark.asyncio
async def test_create_status_change_activity(client, test_property, auth_headers):
    """Test creating a status_change activity."""
    activity_data = {
        "property_id": test_property.id,
        "activity_type": "status_change",
        "description": "Property status updated",
        "field_changed": "status",
        "old_value": "available",
        "new_value": "under_contract",
    }

    response = await client.post(
        f"/api/v1/properties/{test_property.id}/activities",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["activity_type"] == "status_change"
    assert data["field_changed"] == "status"


@pytest.mark.asyncio
async def test_create_document_upload_activity(client, test_property, auth_headers):
    """Test creating a document_upload activity."""
    activity_data = {
        "property_id": test_property.id,
        "activity_type": "document_upload",
        "description": "Uploaded appraisal report",
        "document_name": "appraisal_2024.pdf",
        "document_url": "https://storage.example.com/appraisal_2024.pdf",
    }

    response = await client.post(
        f"/api/v1/properties/{test_property.id}/activities",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["activity_type"] == "document_upload"
    assert data["document_name"] == "appraisal_2024.pdf"
    assert data["document_url"] == "https://storage.example.com/appraisal_2024.pdf"


@pytest.mark.asyncio
async def test_create_activity_property_not_found(client, auth_headers):
    """Test 404 when creating activity for non-existent property."""
    activity_data = {
        "property_id": 999999,
        "activity_type": "view",
        "description": "Viewed property",
    }

    response = await client.post(
        "/api/v1/properties/999999/activities",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_create_activity_property_id_mismatch(client, test_property, auth_headers):
    """Test 400 when body property_id doesn't match URL."""
    activity_data = {
        "property_id": 99999,  # Different from URL
        "activity_type": "view",
        "description": "Viewed property",
    }

    response = await client.post(
        f"/api/v1/properties/{test_property.id}/activities",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "must match" in data["detail"].lower()


@pytest.mark.asyncio
async def test_create_activity_invalid_type(client, test_property, auth_headers):
    """Test 422 for invalid activity type."""
    activity_data = {
        "property_id": test_property.id,
        "activity_type": "invalid_type",
        "description": "Invalid activity",
    }

    response = await client.post(
        f"/api/v1/properties/{test_property.id}/activities",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_activity_persists(
    client, test_property, auth_headers
):
    """Test that created activity persists and can be retrieved."""
    # Create activity
    activity_data = {
        "property_id": test_property.id,
        "activity_type": "comment",
        "description": "Persistence test",
        "comment_text": "Testing persistence",
    }

    create_response = await client.post(
        f"/api/v1/properties/{test_property.id}/activities",
        json=activity_data,
        headers=auth_headers,
    )

    assert create_response.status_code == 200
    created = create_response.json()

    # Retrieve activities
    get_response = await client.get(
        f"/api/v1/properties/{test_property.id}/activities",
        params={"activity_type": "comment"},
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    data = get_response.json()

    # Find our created activity
    found = False
    for item in data["items"]:
        if item["id"] == created["id"]:
            found = True
            assert item["comment_text"] == "Testing persistence"
            break

    assert found, "Created activity should be found in list"
