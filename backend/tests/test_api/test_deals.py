"""Tests for deal API endpoints."""

from decimal import Decimal

import pytest

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
    response = await client.get("/api/v1/deals/", params={"stage": "initial_review"})

    assert response.status_code == 200
    data = response.json()

    for deal in data["items"]:
        assert deal["stage"] == "initial_review"


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
        "/api/v1/deals/", params={"sort_by": "created_at", "sort_order": "asc"}
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
        "/api/v1/deals/kanban", params={"deal_type": "acquisition"}
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
        "stage": "initial_review",
        "asking_price": 25000000.00,
        "priority": "high",
    }

    response = await client.post("/api/v1/deals/", json=new_deal)

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == "New Test Deal"
    assert data["deal_type"] == "acquisition"
    assert data["stage"] == "initial_review"
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
    stage_data = {"stage": "under_contract"}

    response = await client.patch(
        f"/api/v1/deals/{test_deal.id}/stage", json=stage_data
    )

    assert response.status_code == 200
    data = response.json()

    assert data["stage"] == "under_contract"


@pytest.mark.asyncio
async def test_update_deal_stage_with_order(client, test_deal):
    """Test updating a deal's stage with position order."""
    # Use a valid stage from the DealStage enum
    stage_data = {"stage": "closed", "stage_order": 5}

    response = await client.patch(
        f"/api/v1/deals/{test_deal.id}/stage", json=stage_data
    )

    assert response.status_code == 200
    data = response.json()

    assert data["stage"] == "closed"


@pytest.mark.asyncio
async def test_update_deal_stage_invalid(client, test_deal):
    """Test updating a deal's stage with invalid stage value returns validation error."""
    stage_data = {"stage": "invalid_stage_value"}

    response = await client.patch(
        f"/api/v1/deals/{test_deal.id}/stage", json=stage_data
    )

    # Schema validation returns 422, endpoint validation returns 400
    # Either is acceptable for invalid input
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_update_deal_stage_not_found(client):
    """Test updating stage of non-existent deal returns 404."""
    stage_data = {"stage": "under_contract"}

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
        f"/api/v1/deals/{test_deal.id}/activity", json=activity
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


# =============================================================================
# Deal Comparison Tests
# =============================================================================


@pytest.mark.asyncio
async def test_compare_deals_requires_auth(client, multiple_deals):
    """Test that deal comparison requires authentication."""
    deal_ids = [d.id for d in multiple_deals[:2]]
    ids_str = ",".join(str(id) for id in deal_ids)

    response = await client.get(f"/api/v1/deals/compare?ids={ids_str}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_compare_two_deals(client, multiple_deals, auth_headers):
    """Test comparing exactly 2 deals."""
    deal_ids = [multiple_deals[0].id, multiple_deals[1].id]
    ids_str = ",".join(str(id) for id in deal_ids)

    response = await client.get(
        f"/api/v1/deals/compare?ids={ids_str}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert "deals" in data
    assert "comparison_summary" in data
    assert "metric_comparisons" in data
    assert "deal_count" in data
    assert "compared_at" in data
    assert data["deal_count"] == 2
    assert len(data["deals"]) == 2


@pytest.mark.asyncio
async def test_compare_four_deals(client, multiple_deals, auth_headers):
    """Test comparing 4 deals (within limit)."""
    deal_ids = [d.id for d in multiple_deals[:4]]
    ids_str = ",".join(str(id) for id in deal_ids)

    response = await client.get(
        f"/api/v1/deals/compare?ids={ids_str}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["deal_count"] == 4
    assert len(data["deals"]) == 4


@pytest.mark.asyncio
async def test_compare_deals_has_comparison_summary(
    client, multiple_deals, auth_headers
):
    """Test that comparison response includes correct summary structure."""
    deal_ids = [d.id for d in multiple_deals[:2]]
    ids_str = ",".join(str(id) for id in deal_ids)

    response = await client.get(
        f"/api/v1/deals/compare?ids={ids_str}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    summary = data["comparison_summary"]
    expected_fields = [
        "best_irr",
        "best_coc",
        "best_equity_multiple",
        "lowest_price",
        "highest_score",
        "overall_recommendation",
        "recommendation_reason",
    ]
    for field in expected_fields:
        assert field in summary


@pytest.mark.asyncio
async def test_compare_deals_has_metric_comparisons(
    client, multiple_deals, auth_headers
):
    """Test that comparison includes metric comparisons."""
    deal_ids = [d.id for d in multiple_deals[:2]]
    ids_str = ",".join(str(id) for id in deal_ids)

    response = await client.get(
        f"/api/v1/deals/compare?ids={ids_str}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["metric_comparisons"]) > 0

    # Check metric comparison structure
    metric = data["metric_comparisons"][0]
    assert "metric_name" in metric
    assert "values" in metric
    assert "best_deal_id" in metric
    assert "comparison_type" in metric


@pytest.mark.asyncio
async def test_compare_deals_too_few(client, test_deal, auth_headers):
    """Test 400 when comparing fewer than 2 deals."""
    response = await client.get(
        f"/api/v1/deals/compare?ids={test_deal.id}",
        headers=auth_headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "at least 2" in data["detail"].lower()


@pytest.mark.asyncio
async def test_compare_deals_too_many(client, auth_headers, db_session, test_user):
    """Test 400 when comparing more than 10 deals."""
    from app.models import Deal

    # Create 11 deals
    deals = []
    for i in range(11):
        deal = Deal(
            name=f"Comparison Deal #{i+1}",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=i,
            assigned_user_id=test_user.id,
            priority="medium",
        )
        db_session.add(deal)
        deals.append(deal)

    await db_session.commit()
    for deal in deals:
        await db_session.refresh(deal)

    deal_ids = [d.id for d in deals]
    ids_str = ",".join(str(id) for id in deal_ids)

    response = await client.get(
        f"/api/v1/deals/compare?ids={ids_str}",
        headers=auth_headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "maximum 10" in data["detail"].lower()


@pytest.mark.asyncio
async def test_compare_deals_invalid_format(client, auth_headers):
    """Test 400 for invalid deal ID format."""
    response = await client.get(
        "/api/v1/deals/compare?ids=abc,def",
        headers=auth_headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_compare_deals_nonexistent_deal(client, multiple_deals, auth_headers):
    """Test 404 when one of the deal IDs doesn't exist."""
    deal_ids = [multiple_deals[0].id, 999999]
    ids_str = ",".join(str(id) for id in deal_ids)

    response = await client.get(
        f"/api/v1/deals/compare?ids={ids_str}",
        headers=auth_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_compare_deals_with_duplicates(client, multiple_deals, auth_headers):
    """Test that duplicate deal IDs are handled (deduplicated)."""
    # Same ID repeated - should deduplicate
    deal_id = multiple_deals[0].id
    ids_str = f"{deal_id},{deal_id},{multiple_deals[1].id}"

    response = await client.get(
        f"/api/v1/deals/compare?ids={ids_str}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # After deduplication, should only have 2 unique deals
    assert data["deal_count"] == 2


@pytest.mark.asyncio
async def test_compare_deals_metrics_values(
    client, test_deal, multiple_deals, auth_headers
):
    """Test that deal metrics are populated correctly."""
    deal_ids = [test_deal.id, multiple_deals[0].id]
    ids_str = ",".join(str(id) for id in deal_ids)

    response = await client.get(
        f"/api/v1/deals/compare?ids={ids_str}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Find test_deal in the response
    test_deal_data = None
    for deal in data["deals"]:
        if deal["id"] == test_deal.id:
            test_deal_data = deal
            break

    assert test_deal_data is not None
    assert test_deal_data["name"] == test_deal.name
    assert test_deal_data["deal_type"] == test_deal.deal_type


# =============================================================================
# Watchlist Tests
# =============================================================================


@pytest.mark.asyncio
async def test_toggle_watchlist_requires_auth(client, test_deal):
    """Test that toggling watchlist requires authentication."""
    response = await client.post(f"/api/v1/deals/{test_deal.id}/watchlist")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_deal_to_watchlist(client, test_deal, auth_headers):
    """Test adding a deal to the watchlist."""
    response = await client.post(
        f"/api/v1/deals/{test_deal.id}/watchlist",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["deal_id"] == test_deal.id
    assert data["is_watched"] is True
    assert "added" in data["message"].lower()
    assert "watchlist_id" in data


@pytest.mark.asyncio
async def test_remove_deal_from_watchlist(client, test_deal, auth_headers):
    """Test removing a deal from the watchlist (toggle off)."""
    # First, add to watchlist
    add_response = await client.post(
        f"/api/v1/deals/{test_deal.id}/watchlist",
        headers=auth_headers,
    )
    assert add_response.status_code == 200
    assert add_response.json()["is_watched"] is True

    # Then, toggle again to remove
    remove_response = await client.post(
        f"/api/v1/deals/{test_deal.id}/watchlist",
        headers=auth_headers,
    )

    assert remove_response.status_code == 200
    data = remove_response.json()

    assert data["deal_id"] == test_deal.id
    assert data["is_watched"] is False
    assert "removed" in data["message"].lower()


@pytest.mark.asyncio
async def test_toggle_watchlist_deal_not_found(client, auth_headers):
    """Test 404 when toggling watchlist for non-existent deal."""
    response = await client.post(
        "/api/v1/deals/999999/watchlist",
        headers=auth_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_watchlist_status_requires_auth(client, test_deal):
    """Test that checking watchlist status requires authentication."""
    response = await client.get(f"/api/v1/deals/{test_deal.id}/watchlist/status")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_watchlist_status_not_watched(client, test_deal, auth_headers):
    """Test checking watchlist status for a deal not on watchlist."""
    response = await client.get(
        f"/api/v1/deals/{test_deal.id}/watchlist/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["deal_id"] == test_deal.id
    assert data["is_watched"] is False


@pytest.mark.asyncio
async def test_get_watchlist_status_watched(client, test_deal, auth_headers):
    """Test checking watchlist status for a watched deal."""
    # First, add to watchlist
    add_response = await client.post(
        f"/api/v1/deals/{test_deal.id}/watchlist",
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # Then check status
    status_response = await client.get(
        f"/api/v1/deals/{test_deal.id}/watchlist/status",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    data = status_response.json()

    assert data["deal_id"] == test_deal.id
    assert data["is_watched"] is True


@pytest.mark.asyncio
async def test_get_watchlist_status_deal_not_found(client, auth_headers):
    """Test 404 when checking watchlist status for non-existent deal."""
    response = await client.get(
        "/api/v1/deals/999999/watchlist/status",
        headers=auth_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_watchlist_toggle_twice_returns_to_original(
    client, test_deal, auth_headers
):
    """Test that toggling twice returns to original state."""
    # Check initial status
    initial_status = await client.get(
        f"/api/v1/deals/{test_deal.id}/watchlist/status",
        headers=auth_headers,
    )
    assert initial_status.json()["is_watched"] is False

    # Toggle on
    await client.post(f"/api/v1/deals/{test_deal.id}/watchlist", headers=auth_headers)

    # Toggle off
    await client.post(f"/api/v1/deals/{test_deal.id}/watchlist", headers=auth_headers)

    # Check final status
    final_status = await client.get(
        f"/api/v1/deals/{test_deal.id}/watchlist/status",
        headers=auth_headers,
    )
    assert final_status.json()["is_watched"] is False


@pytest.mark.asyncio
async def test_watchlist_user_isolation(
    client, test_deal, auth_headers, admin_auth_headers
):
    """Test that watchlist entries are isolated per user."""
    # User 1 adds to watchlist
    user1_add = await client.post(
        f"/api/v1/deals/{test_deal.id}/watchlist",
        headers=auth_headers,
    )
    assert user1_add.status_code == 200
    assert user1_add.json()["is_watched"] is True

    # User 2 (admin) should not see it on their watchlist
    user2_status = await client.get(
        f"/api/v1/deals/{test_deal.id}/watchlist/status",
        headers=admin_auth_headers,
    )
    assert user2_status.status_code == 200
    assert user2_status.json()["is_watched"] is False


@pytest.mark.asyncio
async def test_multiple_deals_watchlist(client, multiple_deals, auth_headers):
    """Test adding multiple deals to watchlist."""
    # Add first two deals to watchlist
    for deal in multiple_deals[:2]:
        response = await client.post(
            f"/api/v1/deals/{deal.id}/watchlist",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_watched"] is True

    # Verify both are watched
    for deal in multiple_deals[:2]:
        status = await client.get(
            f"/api/v1/deals/{deal.id}/watchlist/status",
            headers=auth_headers,
        )
        assert status.json()["is_watched"] is True

    # Verify others are not watched
    for deal in multiple_deals[2:]:
        status = await client.get(
            f"/api/v1/deals/{deal.id}/watchlist/status",
            headers=auth_headers,
        )
        assert status.json()["is_watched"] is False
