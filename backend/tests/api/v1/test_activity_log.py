"""
Tests for Deal Activity Log API endpoints.

Tests the following endpoints:
- GET /api/v1/deals/{deal_id}/activity-log - List activity logs for a deal
- POST /api/v1/deals/{deal_id}/activity-log - Create a new activity log entry

Covers:
- Pagination (page, page_size)
- Filtering by action type
- All activity action types
- Authentication requirements
- 404 for non-existent deals
- Response structure validation
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deal, User
from app.models.activity_log import ActivityAction, ActivityLog


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def deal_with_activity_logs(
    db_session: AsyncSession, test_deal: Deal, test_user: User
) -> Deal:
    """Create a deal with multiple activity log records."""
    # Create activity logs of different action types
    logs_data = [
        {
            "action": ActivityAction.CREATED,
            "description": "Deal created",
            "meta": {"deal_name": test_deal.name},
        },
        {
            "action": ActivityAction.STAGE_CHANGED,
            "description": "Stage changed from initial_review to active_review",
            "meta": {"old_stage": "initial_review", "new_stage": "active_review"},
        },
        {
            "action": ActivityAction.UPDATED,
            "description": "Updated fields: asking_price, offer_price",
            "meta": {
                "changed_fields": ["asking_price", "offer_price"],
                "old_values": {"asking_price": 10000000},
                "new_values": {"asking_price": 12000000},
            },
        },
        {
            "action": ActivityAction.DOCUMENT_ADDED,
            "description": "Added rent roll document",
            "meta": {"document_name": "rent_roll_2024.pdf"},
        },
        {
            "action": ActivityAction.NOTE_ADDED,
            "description": "Added note about property condition",
        },
        {
            "action": ActivityAction.VIEWED,
            "description": "Deal viewed",
        },
    ]

    for data in logs_data:
        # For SQLite, explicitly convert UUID to string
        log = ActivityLog(
            id=str(uuid.uuid4()),  # SQLite needs string ID
            deal_id=test_deal.id,
            user_id=str(test_user.id),
            **data,
        )
        db_session.add(log)

    await db_session.commit()
    return test_deal


@pytest_asyncio.fixture
async def many_activity_logs(
    db_session: AsyncSession, test_deal: Deal, test_user: User
) -> Deal:
    """Create a deal with many activity logs for pagination testing."""
    for i in range(25):
        log = ActivityLog(
            id=str(uuid.uuid4()),  # SQLite needs string ID
            deal_id=test_deal.id,
            user_id=str(test_user.id),
            action=ActivityAction.VIEWED,
            description=f"View activity {i + 1}",
        )
        db_session.add(log)

    await db_session.commit()
    return test_deal


# =============================================================================
# GET /api/v1/deals/{deal_id}/activity-log Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_activity_logs_without_auth(client, test_deal):
    """Test that getting activity logs works without auth (public endpoint)."""
    response = await client.get(f"/api/v1/deals/{test_deal.id}/activity-log")

    # Endpoint does not require authentication
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_activity_logs_success(
    client, deal_with_activity_logs, auth_headers
):
    """Test successfully getting activity logs."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activity_logs.id}/activity-log",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["total"] == 6  # We created 6 activity logs
    assert len(data["items"]) == 6


@pytest.mark.asyncio
async def test_get_activity_logs_pagination(
    client, many_activity_logs, auth_headers
):
    """Test pagination with page parameter."""
    # Get page 2
    response = await client.get(
        f"/api/v1/deals/{many_activity_logs.id}/activity-log",
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
async def test_get_activity_logs_page_size(
    client, many_activity_logs, auth_headers
):
    """Test pagination with page_size parameter."""
    response = await client.get(
        f"/api/v1/deals/{many_activity_logs.id}/activity-log",
        params={"page_size": 5},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 5
    assert data["total"] == 25
    assert data["page_size"] == 5


@pytest.mark.asyncio
async def test_get_activity_logs_filter_by_created_action(
    client, deal_with_activity_logs, auth_headers
):
    """Test filtering activity logs by created action."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activity_logs.id}/activity-log",
        params={"action": "created"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    for item in data["items"]:
        assert item["action"] == "created"


@pytest.mark.asyncio
async def test_get_activity_logs_filter_by_stage_changed_action(
    client, deal_with_activity_logs, auth_headers
):
    """Test filtering activity logs by stage_changed action."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activity_logs.id}/activity-log",
        params={"action": "stage_changed"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["action"] == "stage_changed"
    assert data["items"][0]["metadata"]["old_stage"] == "initial_review"
    assert data["items"][0]["metadata"]["new_stage"] == "active_review"


@pytest.mark.asyncio
async def test_get_activity_logs_filter_by_updated_action(
    client, deal_with_activity_logs, auth_headers
):
    """Test filtering activity logs by updated action."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activity_logs.id}/activity-log",
        params={"action": "updated"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["action"] == "updated"
    assert "changed_fields" in data["items"][0]["metadata"]


@pytest.mark.asyncio
async def test_get_activity_logs_filter_by_document_added_action(
    client, deal_with_activity_logs, auth_headers
):
    """Test filtering activity logs by document_added action."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activity_logs.id}/activity-log",
        params={"action": "document_added"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["action"] == "document_added"
    assert data["items"][0]["metadata"]["document_name"] == "rent_roll_2024.pdf"


@pytest.mark.asyncio
async def test_get_activity_logs_filter_by_viewed_action(
    client, deal_with_activity_logs, auth_headers
):
    """Test filtering activity logs by viewed action."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activity_logs.id}/activity-log",
        params={"action": "viewed"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["action"] == "viewed"


@pytest.mark.asyncio
async def test_get_activity_logs_invalid_action_filter(
    client, deal_with_activity_logs, auth_headers
):
    """Test filtering with invalid action type returns 400."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activity_logs.id}/activity-log",
        params={"action": "invalid_action_type"},
        headers=auth_headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "Invalid action type" in data["detail"]


@pytest.mark.asyncio
async def test_get_activity_logs_deal_not_found(client, auth_headers):
    """Test 404 for non-existent deal."""
    response = await client.get(
        "/api/v1/deals/999999/activity-log",
        headers=auth_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_activity_logs_response_structure(
    client, deal_with_activity_logs, auth_headers
):
    """Test that activity log response has expected structure."""
    response = await client.get(
        f"/api/v1/deals/{deal_with_activity_logs.id}/activity-log",
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
        "action",
        "description",
        "created_at",
    ]
    for field in required_fields:
        assert field in item

    # ID should be a valid UUID
    try:
        uuid.UUID(item["id"])
    except ValueError:
        pytest.fail("id should be a valid UUID")


@pytest.mark.asyncio
async def test_get_activity_logs_ordered_by_created_at_desc(
    client, many_activity_logs, auth_headers
):
    """Test that activity logs are returned in reverse chronological order."""
    response = await client.get(
        f"/api/v1/deals/{many_activity_logs.id}/activity-log",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check that timestamps are in descending order
    timestamps = [item["created_at"] for item in data["items"]]
    assert timestamps == sorted(timestamps, reverse=True)


# =============================================================================
# POST /api/v1/deals/{deal_id}/activity-log Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_activity_log_requires_auth(client, test_deal):
    """Test that creating activity log requires authentication."""
    activity_data = {
        "action": "viewed",
        "description": "Viewed deal details",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        json=activity_data,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_viewed_activity_log(client, test_deal, auth_headers):
    """Test creating a viewed activity log."""
    activity_data = {
        "action": "viewed",
        "description": "Viewed deal details",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["action"] == "viewed"
    assert data["deal_id"] == test_deal.id
    assert data["description"] == "Viewed deal details"
    assert "id" in data
    # Verify it's a valid UUID
    uuid.UUID(data["id"])


@pytest.mark.asyncio
async def test_create_note_added_activity_log(client, test_deal, auth_headers):
    """Test creating a note_added activity log."""
    activity_data = {
        "action": "note_added",
        "description": "Added a note about property condition",
        "metadata": {"note_preview": "Property needs roof repair..."},
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["action"] == "note_added"
    assert data["metadata"]["note_preview"] == "Property needs roof repair..."


@pytest.mark.asyncio
async def test_create_stage_changed_activity_log(client, test_deal, auth_headers):
    """Test creating a stage_changed activity log."""
    activity_data = {
        "action": "stage_changed",
        "description": "Stage changed from initial_review to under_contract",
        "metadata": {
            "old_stage": "initial_review",
            "new_stage": "under_contract",
        },
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["action"] == "stage_changed"
    assert data["metadata"]["old_stage"] == "initial_review"
    assert data["metadata"]["new_stage"] == "under_contract"


@pytest.mark.asyncio
async def test_create_document_added_activity_log(client, test_deal, auth_headers):
    """Test creating a document_added activity log."""
    activity_data = {
        "action": "document_added",
        "description": "Added appraisal report",
        "metadata": {
            "document_name": "appraisal_report.pdf",
            "document_size": 2048576,
        },
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["action"] == "document_added"
    assert data["metadata"]["document_name"] == "appraisal_report.pdf"


@pytest.mark.asyncio
async def test_create_activity_log_deal_not_found(client, auth_headers):
    """Test 404 when creating activity log for non-existent deal."""
    activity_data = {
        "action": "viewed",
        "description": "Viewed deal",
    }

    response = await client.post(
        "/api/v1/deals/999999/activity-log",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_create_activity_log_invalid_action(client, test_deal, auth_headers):
    """Test 422 for invalid action type."""
    activity_data = {
        "action": "invalid_action",
        "description": "Invalid activity",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_activity_log_missing_description(client, test_deal, auth_headers):
    """Test 422 when description is missing."""
    activity_data = {
        "action": "viewed",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_activity_log_empty_description(client, test_deal, auth_headers):
    """Test 422 when description is empty."""
    activity_data = {
        "action": "viewed",
        "description": "",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_activity_log_persists(client, test_deal, auth_headers):
    """Test that created activity log persists and can be retrieved."""
    # Create activity log
    activity_data = {
        "action": "note_added",
        "description": "Persistence test note",
        "metadata": {"test_key": "test_value"},
    }

    create_response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        json=activity_data,
        headers=auth_headers,
    )

    assert create_response.status_code == 200
    created = create_response.json()

    # Retrieve activity logs
    get_response = await client.get(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        params={"action": "note_added"},
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    data = get_response.json()

    # Find our created activity log
    found = False
    for item in data["items"]:
        if item["id"] == created["id"]:
            found = True
            assert item["description"] == "Persistence test note"
            assert item["metadata"]["test_key"] == "test_value"
            break

    assert found, "Created activity log should be found in list"


@pytest.mark.asyncio
async def test_create_activity_log_has_user_id(client, test_deal, auth_headers, test_user):
    """Test that created activity log has user_id from authenticated user."""
    activity_data = {
        "action": "viewed",
        "description": "Test user tracking",
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity-log",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_create_all_action_types(client, test_deal, auth_headers):
    """Test creating activity logs for all valid action types."""
    valid_actions = [
        "created",
        "updated",
        "stage_changed",
        "document_added",
        "document_removed",
        "note_added",
        "assigned",
        "unassigned",
        "price_changed",
        "viewed",
    ]

    for action in valid_actions:
        activity_data = {
            "action": action,
            "description": f"Test {action} action",
        }

        response = await client.post(
            f"/api/v1/deals/{test_deal.id}/activity-log",
            json=activity_data,
            headers=auth_headers,
        )

        assert response.status_code == 200, f"Failed for action: {action}"
        data = response.json()
        assert data["action"] == action
