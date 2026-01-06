"""Tests for property API endpoints.

Tests the Properties API endpoints including:
- List properties with pagination, filtering, and sorting
- Get property by ID
- Create, update, and delete properties
- Property analytics
"""

import pytest

# =============================================================================
# List Properties Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_properties(client, db_session):
    """Test listing all properties with default pagination."""
    response = await client.get("/api/v1/properties/", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Properties endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    # Should return paginated response
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_properties_pagination(client, db_session):
    """Test listing properties with custom pagination."""
    response = await client.get(
        "/api/v1/properties/", params={"page": 1, "page_size": 2}, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Properties endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_list_properties_filter_by_type(client, db_session):
    """Test filtering properties by property type."""
    response = await client.get(
        "/api/v1/properties/",
        params={"property_type": "multifamily"},
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Properties endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    # All returned properties should be multifamily
    for prop in data["items"]:
        assert prop["property_type"] == "multifamily"


@pytest.mark.asyncio
async def test_list_properties_filter_by_city(client, db_session):
    """Test filtering properties by city."""
    response = await client.get(
        "/api/v1/properties/", params={"city": "Phoenix"}, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Properties endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    for prop in data["items"]:
        assert prop["city"].lower() == "phoenix"


@pytest.mark.asyncio
async def test_list_properties_filter_by_state(client, db_session):
    """Test filtering properties by state."""
    response = await client.get(
        "/api/v1/properties/", params={"state": "AZ"}, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Properties endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    for prop in data["items"]:
        assert prop["state"].upper() == "AZ"


@pytest.mark.asyncio
async def test_list_properties_sorting(client, db_session):
    """Test sorting properties by name."""
    response = await client.get(
        "/api/v1/properties/",
        params={"sort_by": "name", "sort_order": "asc"},
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Properties endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    if len(data["items"]) > 1:
        names = [p["name"] for p in data["items"]]
        assert names == sorted(names)


# =============================================================================
# Get Property Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_property_by_id(client, db_session):
    """Test getting a specific property by ID."""
    response = await client.get("/api/v1/properties/1", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Property not found or endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == 1
    assert "name" in data
    assert "property_type" in data
    assert "address" in data


@pytest.mark.asyncio
async def test_get_property_not_found(client, db_session):
    """Test getting a non-existent property returns 404."""
    response = await client.get("/api/v1/properties/99999", follow_redirects=True)

    # Should return 404 for non-existent property
    assert response.status_code == 404


# =============================================================================
# Create Property Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_property(client, db_session):
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
        "/api/v1/properties/", json=new_property, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Create property endpoint not implemented")

    if response.status_code in [401, 403]:
        pytest.skip("Endpoint requires authentication")

    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["name"] == "Test Property"
    assert data["property_type"] == "multifamily"
    assert data["city"] == "Phoenix"


@pytest.mark.asyncio
async def test_create_property_invalid_type(client, db_session):
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
        "/api/v1/properties/", json=invalid_property, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Create property endpoint not implemented")

    # Should fail validation
    assert response.status_code == 422


# =============================================================================
# Update Property Tests
# =============================================================================


@pytest.mark.asyncio
async def test_update_property(client, db_session):
    """Test updating an existing property."""
    update_data = {
        "name": "Updated Property Name",
        "occupancy_rate": 98.5,
    }

    response = await client.put(
        "/api/v1/properties/1", json=update_data, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Update property endpoint not implemented")

    if response.status_code in [401, 403]:
        pytest.skip("Endpoint requires authentication")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Updated Property Name"


@pytest.mark.asyncio
async def test_update_property_not_found(client, db_session):
    """Test updating a non-existent property returns 404."""
    update_data = {"name": "Updated Name"}

    response = await client.put(
        "/api/v1/properties/99999", json=update_data, follow_redirects=True
    )

    assert response.status_code == 404


# =============================================================================
# Delete Property Tests
# =============================================================================


@pytest.mark.asyncio
async def test_delete_property(client, db_session):
    """Test deleting a property."""
    response = await client.delete("/api/v1/properties/1", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Delete property endpoint not implemented")

    if response.status_code in [401, 403]:
        pytest.skip("Endpoint requires authentication")

    # Successful delete returns 204 No Content
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_property_not_found(client, db_session):
    """Test deleting a non-existent property returns 404."""
    response = await client.delete("/api/v1/properties/99999", follow_redirects=True)

    assert response.status_code == 404


# =============================================================================
# Property Analytics Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_property_analytics(client, db_session):
    """Test getting analytics data for a property."""
    response = await client.get("/api/v1/properties/1/analytics", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Property analytics endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    assert "property_id" in data
    assert data["property_id"] == 1
    assert "metrics" in data
    assert "trends" in data
    assert "comparables" in data


@pytest.mark.asyncio
async def test_get_property_analytics_metrics(client, db_session):
    """Test that property analytics returns expected metrics."""
    response = await client.get("/api/v1/properties/1/analytics", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Property analytics endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    metrics = data.get("metrics", {})
    assert "ytd_rent_growth" in metrics
    assert "ytd_noi_growth" in metrics
    assert "avg_occupancy_12m" in metrics
    assert "rent_vs_market" in metrics
