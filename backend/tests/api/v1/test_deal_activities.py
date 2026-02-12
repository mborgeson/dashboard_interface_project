"""
Tests for Deal Activities API endpoints.

Tests the following endpoints:
- GET /api/v1/deals/{id}/activity - List activities for a deal
- POST /api/v1/deals/{id}/activity - Create a new activity

Covers:
- Pagination (page, page_size)
- Filtering by activity_type
- All activity types (view, edit, comment, status_change, document_upload)
- Authentication requirements
- 404 for non-existent deals
- User attribution for activities
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deal, User
from app.models.activity import ActivityType, DealActivity
from app.models.deal import DealStage

# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def deal_with_activities(
    db_session: AsyncSession, test_deal: Deal, test_user: User
) -> Deal:
    """Create a deal with multiple activity records."""
    # Create activities of different types
    activities_data = [
        {
            "activity_type": ActivityType.VIEW,
            "description": "Viewed deal details",
        },
        {
            "activity_type": ActivityType.VIEW,
            "description": "Viewed deal again",
        },
        {
            "activity_type": ActivityType.EDIT,
            "description": "Updated asking price",
            "field_changed": "asking_price",
            "old_value": "5000000",
            "new_value": "4800000",
        },
        {
            "activity_type": ActivityType.COMMENT,
            "description": "Added comment",
            "comment_text": "This deal has strong potential for value-add.",
        },
        {
            "activity_type": ActivityType.STATUS_CHANGE,
            "description": "Changed stage",
            "field_changed": "stage",
            "old_value": "initial_review",
            "new_value": "active_review",
        },
        {
            "activity_type": ActivityType.DOCUMENT_UPLOAD,
            "description": "Uploaded underwriting model",
            "document_name": "underwriting_model_v1.xlsx",
            "document_url": "https://storage.example.com/docs/underwriting_model_v1.xlsx",
        },
    ]

    for data in activities_data:
        activity = DealActivity(
            deal_id=test_deal.id,
            user_id=test_user.id,
            **data,
        )
        db_session.add(activity)

    await db_session.commit()
    return test_deal


@pytest_asyncio.fixture
async def many_deal_activities(
    db_session: AsyncSession, test_deal: Deal, test_user: User
) -> Deal:
    """Create a deal with many activities for pagination testing."""
    for i in range(25):
        activity = DealActivity(
            deal_id=test_deal.id,
            user_id=test_user.id,
            activity_type=ActivityType.VIEW,
            description=f"View activity {i + 1}",
        )
        db_session.add(activity)

    await db_session.commit()
    return test_deal


# =============================================================================
# GET /api/v1/deals/{id}/activity Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_deal_activities_without_auth(client, test_deal):
    """Test that getting deal activities works without auth (public endpoint)."""
    response = await client.get(f"/api/v1/deals/{test_deal.id}/activity")

    # Endpoint does not require authentication
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_deal_activities_success(client, deal_with_activities, auth_headers):
    """Test successfully getting deal activities."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activities.id}/activity",
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
async def test_get_deal_activities_pagination_page(
    client, many_deal_activities, auth_headers
):
    """Test pagination with page parameter."""
    response = await client.get(
        f"/api/v1/deals/{many_deal_activities.id}/activity",
        params={"page": 2, "page_size": 10},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["page"] == 2
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_get_deal_activities_pagination_page_size(
    client, many_deal_activities, auth_headers
):
    """Test pagination with page_size parameter."""
    response = await client.get(
        f"/api/v1/deals/{many_deal_activities.id}/activity",
        params={"page_size": 5},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 5
    assert data["total"] == 25
    assert data["page_size"] == 5


@pytest.mark.asyncio
async def test_get_deal_activities_filter_by_view_type(
    client, deal_with_activities, auth_headers
):
    """Test filtering activities by view type."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activities.id}/activity",
        params={"activity_type": "view"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2  # We created 2 view activities
    for item in data["items"]:
        assert item["activity_type"] == "view"


@pytest.mark.asyncio
async def test_get_deal_activities_filter_by_edit_type(
    client, deal_with_activities, auth_headers
):
    """Test filtering activities by edit type."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activities.id}/activity",
        params={"activity_type": "edit"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["activity_type"] == "edit"
    assert data["items"][0]["field_changed"] == "asking_price"


@pytest.mark.asyncio
async def test_get_deal_activities_filter_by_comment_type(
    client, deal_with_activities, auth_headers
):
    """Test filtering activities by comment type."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activities.id}/activity",
        params={"activity_type": "comment"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["activity_type"] == "comment"
    assert "value-add" in data["items"][0]["comment_text"]


@pytest.mark.asyncio
async def test_get_deal_activities_filter_by_status_change_type(
    client, deal_with_activities, auth_headers
):
    """Test filtering activities by status_change type."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activities.id}/activity",
        params={"activity_type": "status_change"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["activity_type"] == "status_change"
    assert data["items"][0]["old_value"] == "initial_review"
    assert data["items"][0]["new_value"] == "active_review"


@pytest.mark.asyncio
async def test_get_deal_activities_filter_by_document_upload_type(
    client, deal_with_activities, auth_headers
):
    """Test filtering activities by document_upload type."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activities.id}/activity",
        params={"activity_type": "document_upload"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["activity_type"] == "document_upload"
    assert data["items"][0]["document_name"] == "underwriting_model_v1.xlsx"


@pytest.mark.asyncio
async def test_get_deal_activities_not_found(client, auth_headers):
    """Test 404 for non-existent deal."""
    response = await client.get(
        "/api/v1/deals/999999/activity",
        headers=auth_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_deal_activities_response_structure(
    client, deal_with_activities, auth_headers
):
    """Test that activity response has expected structure."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activities.id}/activity",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check at least one item
    assert len(data["items"]) > 0

    item = data["items"][0]
    required_fields = [
        "id",
        "deal_id",
        "user_id",
        "activity_type",
        "created_at",
        "updated_at",
    ]
    for field in required_fields:
        assert field in item


@pytest.mark.asyncio
async def test_get_deal_activities_ordered_by_newest_first(
    client, deal_with_activities, auth_headers
):
    """Test that activities are returned in reverse chronological order."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activities.id}/activity",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify newest is first by checking created_at timestamps
    items = data["items"]
    for i in range(len(items) - 1):
        current_time = items[i]["created_at"]
        next_time = items[i + 1]["created_at"]
        # Current should be >= next (newer or same)
        assert current_time >= next_time


# =============================================================================
# POST /api/v1/deals/{id}/activity Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_activity_requires_auth(client, test_deal):
    """Test that creating activity requires authentication."""
    activity_data = {
        "deal_id": test_deal.id,
        "activity_type": "view",
        "description": "Viewed deal",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity",
        json=activity_data,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_view_activity(client, test_deal, auth_headers):
    """Test creating a view activity."""
    activity_data = {
        "deal_id": test_deal.id,
        "activity_type": "view",
        "description": "Viewed deal details",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["activity_type"] == "view"
    assert data["deal_id"] == test_deal.id
    assert "id" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_create_edit_activity(client, test_deal, auth_headers):
    """Test creating an edit activity with field changes."""
    activity_data = {
        "deal_id": test_deal.id,
        "activity_type": "edit",
        "description": "Updated offer price",
        "field_changed": "offer_price",
        "old_value": "4500000",
        "new_value": "4750000",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["activity_type"] == "edit"
    assert data["field_changed"] == "offer_price"
    assert data["old_value"] == "4500000"
    assert data["new_value"] == "4750000"


@pytest.mark.asyncio
async def test_create_comment_activity(client, test_deal, auth_headers):
    """Test creating a comment activity."""
    activity_data = {
        "deal_id": test_deal.id,
        "activity_type": "comment",
        "description": "Added comment",
        "comment_text": "Excellent location with strong demographics. Recommend moving to active review.",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["activity_type"] == "comment"
    assert "Excellent location" in data["comment_text"]


@pytest.mark.asyncio
async def test_create_status_change_activity(client, test_deal, auth_headers):
    """Test creating a status_change activity."""
    activity_data = {
        "deal_id": test_deal.id,
        "activity_type": "status_change",
        "description": "Deal stage updated",
        "field_changed": "stage",
        "old_value": "initial_review",
        "new_value": "under_contract",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["activity_type"] == "status_change"
    assert data["field_changed"] == "stage"


@pytest.mark.asyncio
async def test_create_document_upload_activity(client, test_deal, auth_headers):
    """Test creating a document_upload activity."""
    activity_data = {
        "deal_id": test_deal.id,
        "activity_type": "document_upload",
        "description": "Uploaded due diligence report",
        "document_name": "due_diligence_report.pdf",
        "document_url": "https://storage.example.com/due_diligence_report.pdf",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["activity_type"] == "document_upload"
    assert data["document_name"] == "due_diligence_report.pdf"
    assert data["document_url"] == "https://storage.example.com/due_diligence_report.pdf"


@pytest.mark.asyncio
async def test_create_activity_deal_not_found(client, auth_headers):
    """Test 404 when creating activity for non-existent deal."""
    activity_data = {
        "deal_id": 999999,
        "activity_type": "view",
        "description": "Viewed deal",
    }

    response = await client.post(
        "/api/v1/deals/999999/activity",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_create_activity_invalid_type(client, test_deal, auth_headers):
    """Test 422 for invalid activity type."""
    activity_data = {
        "deal_id": test_deal.id,
        "activity_type": "invalid_type",
        "description": "Invalid activity",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_activity_persists(client, test_deal, auth_headers):
    """Test that created activity persists and can be retrieved."""
    # Create activity
    activity_data = {
        "deal_id": test_deal.id,
        "activity_type": "comment",
        "description": "Persistence test",
        "comment_text": "Testing persistence of deal activities",
    }

    create_response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity",
        json=activity_data,
        headers=auth_headers,
    )

    assert create_response.status_code == 200
    created = create_response.json()

    # Retrieve activities
    get_response = await client.get(
        f"/api/v1/deals/{test_deal.id}/activity",
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
            assert item["comment_text"] == "Testing persistence of deal activities"
            break

    assert found, "Created activity should be found in list"


@pytest.mark.asyncio
async def test_create_activity_user_attribution(client, test_deal, auth_headers, test_user):
    """Test that activity is attributed to the authenticated user."""
    activity_data = {
        "deal_id": test_deal.id,
        "activity_type": "view",
        "description": "User attribution test",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Activity should be attributed to the authenticated user
    assert "user_id" in data
    assert data["user_id"] == test_user.id


@pytest.mark.asyncio
async def test_create_multiple_activities_different_types(
    client, test_deal, auth_headers
):
    """Test creating multiple activities of different types for the same deal."""
    activities = [
        {"activity_type": "view", "description": "First view"},
        {"activity_type": "edit", "description": "Price update", "field_changed": "asking_price"},
        {"activity_type": "comment", "description": "Comment added", "comment_text": "Looking good"},
    ]

    created_ids = []
    for activity_data in activities:
        activity_data["deal_id"] = test_deal.id
        response = await client.post(
            f"/api/v1/deals/{test_deal.id}/activity",
            json=activity_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        created_ids.append(response.json()["id"])

    # Verify all activities were created
    get_response = await client.get(
        f"/api/v1/deals/{test_deal.id}/activity",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    data = get_response.json()
    assert data["total"] >= 3

    # Verify all created activities are present
    response_ids = [item["id"] for item in data["items"]]
    for created_id in created_ids:
        assert created_id in response_ids
