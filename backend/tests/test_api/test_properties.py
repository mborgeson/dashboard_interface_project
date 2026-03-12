"""Tests for property API endpoints.

Tests the Properties API endpoints including:
- List properties with pagination, filtering, and sorting
- Get property by ID
- Create, update, and delete properties
- Property analytics
- Auth guards (require_analyst for reads, require_manager for mutations)
"""

import pytest

# =============================================================================
# Auth Guard Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_properties_requires_auth(client, db_session):
    """Test that listing properties without auth returns 401."""
    response = await client.get("/api/v1/properties/", follow_redirects=True)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_property_requires_manager(client, db_session, auth_headers):
    """Test that creating a property with analyst role returns 403."""
    new_property = {
        "name": "Test Property",
        "property_type": "multifamily",
        "address": "123 Test Street",
        "city": "Phoenix",
        "state": "AZ",
        "zip_code": "85001",
        "market": "Phoenix Metro",
        "total_units": 100,
        "year_built": 2020,
    }
    response = await client.post(
        "/api/v1/properties/",
        json=new_property,
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 403


# =============================================================================
# List Properties Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_properties(client, db_session, auth_headers):
    """Test listing all properties with default pagination."""
    response = await client.get(
        "/api/v1/properties/", headers=auth_headers, follow_redirects=True
    )

    assert response.status_code == 200
    data = response.json()

    # Should return paginated response
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_properties_pagination(client, db_session, auth_headers):
    """Test listing properties with custom pagination."""
    response = await client.get(
        "/api/v1/properties/",
        params={"page": 1, "page_size": 2},
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_list_properties_filter_by_type(
    client, db_session, auth_headers, test_property
):
    """Test filtering properties by property type."""
    response = await client.get(
        "/api/v1/properties/",
        params={"property_type": "multifamily"},
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    # All returned properties should be multifamily
    for prop in data["items"]:
        assert prop["property_type"] == "multifamily"


@pytest.mark.asyncio
async def test_list_properties_filter_by_city(
    client, db_session, auth_headers, test_property
):
    """Test filtering properties by city."""
    response = await client.get(
        "/api/v1/properties/",
        params={"city": "Phoenix"},
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    for prop in data["items"]:
        assert prop["city"].lower() == "phoenix"


@pytest.mark.asyncio
async def test_list_properties_filter_by_state(
    client, db_session, auth_headers, test_property
):
    """Test filtering properties by state."""
    response = await client.get(
        "/api/v1/properties/",
        params={"state": "AZ"},
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    for prop in data["items"]:
        assert prop["state"].upper() == "AZ"


@pytest.mark.asyncio
async def test_list_properties_sorting(client, db_session, auth_headers):
    """Test sorting properties by name."""
    response = await client.get(
        "/api/v1/properties/",
        params={"sort_by": "name", "sort_order": "asc"},
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    if len(data["items"]) > 1:
        names = [p["name"] for p in data["items"]]
        assert names == sorted(names)


# =============================================================================
# Get Property Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_property_by_id(client, db_session, auth_headers, test_property):
    """Test getting a specific property by ID."""
    response = await client.get(
        f"/api/v1/properties/{test_property.id}",
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == test_property.id
    assert "name" in data
    assert "property_type" in data
    assert "address" in data


@pytest.mark.asyncio
async def test_get_property_not_found(client, db_session, auth_headers):
    """Test getting a non-existent property returns 404."""
    response = await client.get(
        "/api/v1/properties/99999", headers=auth_headers, follow_redirects=True
    )

    assert response.status_code == 404


# =============================================================================
# Create Property Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_property(client, db_session, admin_auth_headers):
    """Test creating a new property."""
    new_property = {
        "name": "Test Property",
        "property_type": "multifamily",
        "address": "123 Test Street",
        "city": "Phoenix",
        "state": "AZ",
        "zip_code": "85001",
        "market": "Phoenix Metro",
        "total_units": 100,
        "year_built": 2020,
    }

    response = await client.post(
        "/api/v1/properties/",
        json=new_property,
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["name"] == "Test Property"
    assert data["property_type"] == "multifamily"
    assert data["city"] == "Phoenix"


@pytest.mark.asyncio
async def test_create_property_invalid_type(client, db_session, admin_auth_headers):
    """Test creating a property with invalid property type fails validation."""
    invalid_property = {
        "name": "Invalid Property",
        "property_type": "invalid_type",  # Not in allowed values
        "address": "123 Test Street",
        "city": "Phoenix",
        "state": "AZ",
        "zip_code": "85001",
    }

    response = await client.post(
        "/api/v1/properties/",
        json=invalid_property,
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    # Should fail validation
    assert response.status_code == 422


# =============================================================================
# Update Property Tests
# =============================================================================


@pytest.mark.asyncio
async def test_update_property(client, db_session, admin_auth_headers, test_property):
    """Test updating an existing property."""
    update_data = {
        "name": "Updated Property Name",
        "occupancy_rate": 98.5,
    }

    response = await client.put(
        f"/api/v1/properties/{test_property.id}",
        json=update_data,
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Updated Property Name"


@pytest.mark.asyncio
async def test_update_property_not_found(client, db_session, admin_auth_headers):
    """Test updating a non-existent property returns 404."""
    update_data = {"name": "Updated Name"}

    response = await client.put(
        "/api/v1/properties/99999",
        json=update_data,
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 404


# =============================================================================
# Delete Property Tests
# =============================================================================


@pytest.mark.asyncio
async def test_delete_property(client, db_session, admin_auth_headers, test_property):
    """Test deleting a property."""
    response = await client.delete(
        f"/api/v1/properties/{test_property.id}",
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    # Successful delete returns 204 No Content
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_property_not_found(client, db_session, admin_auth_headers):
    """Test deleting a non-existent property returns 404."""
    response = await client.delete(
        "/api/v1/properties/99999",
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 404


# =============================================================================
# Property Analytics Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_property_analytics(client, db_session, auth_headers, test_property):
    """Test getting analytics data for a property."""
    response = await client.get(
        f"/api/v1/properties/{test_property.id}/analytics",
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert "property_id" in data
    assert data["property_id"] == test_property.id
    assert "metrics" in data
    assert "trends" in data
    assert "comparables" in data

    # F-031: Verify trend metadata fields are present
    trends = data["trends"]
    assert "data_points" in trends
    assert "trend_type" in trends
    assert trends["trend_type"] in ("projected", "historical", "current_only")
    assert isinstance(trends["data_points"], int)


@pytest.mark.asyncio
async def test_get_property_analytics_metrics(
    client, db_session, auth_headers, test_property
):
    """Test that property analytics returns expected metrics."""
    response = await client.get(
        f"/api/v1/properties/{test_property.id}/analytics",
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    metrics = data.get("metrics", {})
    assert "ytd_rent_growth" in metrics
    assert "ytd_noi_growth" in metrics
    assert "avg_occupancy_12m" in metrics
    assert "rent_vs_market" in metrics
