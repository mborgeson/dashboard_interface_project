"""Tests for deal API endpoints."""
import pytest
from decimal import Decimal

from app.models import DealStage


# =============================================================================
# List Deals Tests
# =============================================================================

@pytest.mark.asyncio
async def test_list_deals(client, multiple_deals):
    """Test listing all deals with pagination."""
    response = await client.get("/api/v1/deals/")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert len(data["items"]) >= 4
    assert data["total"] >= 4


@pytest.mark.asyncio
async def test_list_deals_with_pagination(client, multiple_deals):
    """Test deal listing with custom pagination."""
    response = await client.get("/api/v1/deals/", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) <= 2
    assert data["page"] == 1
    assert data["page_size"] == 2


@pytest.mark.asyncio
async def test_list_deals_filter_by_stage(client, multiple_deals):
    """Test filtering deals by stage."""
    response = await client.get("/api/v1/deals/", params={"stage": "lead"})

    assert response.status_code == 200
    data = response.json()

    for deal in data["items"]:
        assert deal["stage"] == "lead"


@pytest.mark.asyncio
async def test_list_deals_filter_by_priority(client, multiple_deals):
    """Test filtering deals by priority."""
    response = await client.get("/api/v1/deals/", params={"priority": "medium"})

    assert response.status_code == 200
    data = response.json()

    for deal in data["items"]:
        assert deal["priority"] == "medium"


@pytest.mark.asyncio
async def test_list_deals_sort_order(client, multiple_deals):
    """Test deals sorting."""
    # Sort ascending
    response = await client.get(
        "/api/v1/deals/",
        params={"sort_by": "created_at", "sort_order": "asc"}
    )

    assert response.status_code == 200


# =============================================================================
# Kanban Board Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_kanban_board(client, multiple_deals):
    """Test getting Kanban board data."""
    response = await client.get("/api/v1/deals/kanban")

    assert response.status_code == 200
    data = response.json()

    assert "stages" in data
    assert "total_deals" in data
    assert "stage_counts" in data
    assert data["total_deals"] >= 4


@pytest.mark.asyncio
async def test_get_kanban_board_with_filter(client, multiple_deals):
    """Test Kanban board with deal type filter."""
    response = await client.get(
        "/api/v1/deals/kanban",
        params={"deal_type": "acquisition"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "stages" in data


# =============================================================================
# Get Single Deal Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_deal_by_id(client, test_deal):
    """Test getting a specific deal by ID."""
    response = await client.get(f"/api/v1/deals/{test_deal.id}")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == test_deal.id
    assert data["name"] == test_deal.name


@pytest.mark.asyncio
async def test_get_deal_not_found(client):
    """Test getting a non-existent deal returns 404."""
    response = await client.get("/api/v1/deals/999999")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


# =============================================================================
# Create Deal Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_deal(client, test_user):
    """Test creating a new deal."""
    new_deal = {
        "name": "New Test Deal",
        "deal_type": "acquisition",
        "stage": "lead",
        "asking_price": 25000000.00,
        "priority": "high",
    }

    response = await client.post("/api/v1/deals/", json=new_deal)

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == "New Test Deal"
    assert data["deal_type"] == "acquisition"
    assert data["stage"] == "lead"
    assert data["priority"] == "high"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_deal_minimal(client):
    """Test creating a deal with minimal required fields."""
    new_deal = {
        "name": "Minimal Deal",
        "deal_type": "acquisition",
    }

    response = await client.post("/api/v1/deals/", json=new_deal)

    # May succeed or fail validation depending on required fields
    assert response.status_code in [201, 422]


@pytest.mark.asyncio
async def test_create_deal_missing_required_field(client):
    """Test creating a deal without required name fails."""
    new_deal = {
        "deal_type": "acquisition",
        "priority": "high",
    }

    response = await client.post("/api/v1/deals/", json=new_deal)

    assert response.status_code == 422


# =============================================================================
# Update Deal Tests (PUT)
# =============================================================================

@pytest.mark.asyncio
async def test_update_deal(client, test_deal):
    """Test updating an existing deal."""
    update_data = {
        "name": "Updated Deal Name",
        "priority": "low",
    }

    response = await client.put(f"/api/v1/deals/{test_deal.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Updated Deal Name"
    assert data["priority"] == "low"


@pytest.mark.asyncio
async def test_update_deal_not_found(client):
    """Test updating a non-existent deal returns 404."""
    update_data = {"name": "Won't Work"}

    response = await client.put("/api/v1/deals/999999", json=update_data)

    assert response.status_code == 404


# =============================================================================
# Patch Deal Tests (PATCH)
# =============================================================================

@pytest.mark.asyncio
async def test_patch_deal(client, test_deal):
    """Test partially updating an existing deal."""
    patch_data = {"priority": "low"}

    response = await client.patch(f"/api/v1/deals/{test_deal.id}", json=patch_data)

    assert response.status_code == 200
    data = response.json()

    assert data["priority"] == "low"
    assert data["name"] == test_deal.name  # Unchanged


@pytest.mark.asyncio
async def test_patch_deal_not_found(client):
    """Test patching a non-existent deal returns 404."""
    patch_data = {"priority": "low"}

    response = await client.patch("/api/v1/deals/999999", json=patch_data)

    assert response.status_code == 404


# =============================================================================
# Update Deal Stage Tests
# =============================================================================

@pytest.mark.asyncio
async def test_update_deal_stage(client, test_deal):
    """Test updating a deal's stage (Kanban drag-and-drop)."""
    stage_data = {"stage": "due_diligence"}

    response = await client.patch(
        f"/api/v1/deals/{test_deal.id}/stage",
        json=stage_data
    )

    assert response.status_code == 200
    data = response.json()

    assert data["stage"] == "due_diligence"


@pytest.mark.asyncio
async def test_update_deal_stage_with_order(client, test_deal):
    """Test updating a deal's stage with position order."""
    # Use a valid stage from the DealStage enum
    stage_data = {"stage": "closed", "stage_order": 5}

    response = await client.patch(
        f"/api/v1/deals/{test_deal.id}/stage",
        json=stage_data
    )

    assert response.status_code == 200
    data = response.json()

    assert data["stage"] == "closed"


@pytest.mark.asyncio
async def test_update_deal_stage_invalid(client, test_deal):
    """Test updating a deal's stage with invalid stage value returns validation error."""
    stage_data = {"stage": "invalid_stage_value"}

    response = await client.patch(
        f"/api/v1/deals/{test_deal.id}/stage",
        json=stage_data
    )

    # Schema validation returns 422, endpoint validation returns 400
    # Either is acceptable for invalid input
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_update_deal_stage_not_found(client):
    """Test updating stage of non-existent deal returns 404."""
    stage_data = {"stage": "due_diligence"}

    response = await client.patch("/api/v1/deals/999999/stage", json=stage_data)

    assert response.status_code == 404


# =============================================================================
# Delete Deal Tests
# =============================================================================

@pytest.mark.asyncio
async def test_delete_deal(client, test_deal):
    """Test deleting a deal."""
    response = await client.delete(f"/api/v1/deals/{test_deal.id}")

    assert response.status_code == 204

    # Verify deal is gone
    get_response = await client.get(f"/api/v1/deals/{test_deal.id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_deal_not_found(client):
    """Test deleting a non-existent deal returns 404."""
    response = await client.delete("/api/v1/deals/999999")

    assert response.status_code == 404


# =============================================================================
# Activity Log Tests
# =============================================================================

@pytest.mark.asyncio
async def test_add_deal_activity(client, test_deal):
    """Test adding an activity log entry to a deal."""
    activity = {
        "type": "note",
        "message": "Follow-up call scheduled",
        "user_id": 1,
    }

    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/activity",
        json=activity
    )

    assert response.status_code == 200
    data = response.json()

    assert "activity" in data
    assert data["activity"]["type"] == "note"
    assert "timestamp" in data["activity"]


@pytest.mark.asyncio
async def test_add_deal_activity_not_found(client):
    """Test adding activity to non-existent deal returns 404."""
    activity = {"type": "note", "message": "Test"}

    response = await client.post("/api/v1/deals/999999/activity", json=activity)

    assert response.status_code == 404
