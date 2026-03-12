"""Tests for admin audit log functionality.

Uses standard auth fixtures from conftest.py:
- admin_auth_headers: Admin JWT token (for admin-only endpoints)
- viewer_auth_headers: Viewer JWT token (for testing 403 on admin endpoints)
- auth_headers: Analyst JWT token (for standard read endpoints)
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.core.permissions import CurrentUser, Role
from app.models.audit_log import AuditLog
from app.services import audit_service


@pytest_asyncio.fixture
async def seed_audit_logs(db_session):
    """Seed the database with sample audit log entries."""
    now = datetime.now(UTC)
    entries = []
    for i in range(5):
        entry = AuditLog(
            timestamp=now - timedelta(hours=5 - i),
            user_id=1,
            user_email="admin@example.com",
            action="extract.trigger" if i % 2 == 0 else "settings.update",
            resource_type="extraction" if i % 2 == 0 else "settings",
            resource_id=f"resource-{i}",
            details=json.dumps({"index": i}),
            ip_address="127.0.0.1",
            user_agent="test-agent",
            created_at=now - timedelta(hours=5 - i),
        )
        db_session.add(entry)
        entries.append(entry)

    # Add one entry from a different user
    entry = AuditLog(
        timestamp=now,
        user_id=3,
        user_email="other-admin@example.com",
        action="user.create",
        resource_type="user",
        resource_id="99",
        details=json.dumps({"created_user": "new@example.com"}),
        ip_address="10.0.0.1",
        user_agent="other-agent",
        created_at=now,
    )
    db_session.add(entry)
    entries.append(entry)

    await db_session.commit()
    for e in entries:
        await db_session.refresh(e)
    return entries


# =============================================================================
# Audit Service Tests
# =============================================================================


@pytest.mark.asyncio
async def test_audit_service_log_action(db_session):
    """Test that audit_service.log_action creates a database entry."""
    user = CurrentUser(
        id=1,
        email="admin@example.com",
        role=Role.ADMIN,
        full_name="Admin User",
        is_active=True,
    )

    await audit_service.log_action(
        db=db_session,
        user=user,
        action="extract.trigger",
        resource_type="extraction",
        resource_id="fred",
        details={"source": "fred", "incremental": True},
        request=None,
    )
    await db_session.commit()

    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entries = result.scalars().all()

    assert len(entries) == 1
    entry = entries[0]
    assert entry.user_id == 1
    assert entry.user_email == "admin@example.com"
    assert entry.action == "extract.trigger"
    assert entry.resource_type == "extraction"
    assert entry.resource_id == "fred"
    assert '"source": "fred"' in entry.details
    assert entry.ip_address is None  # No request object
    assert entry.timestamp is not None


@pytest.mark.asyncio
async def test_audit_service_swallows_errors(db_session):
    """Test that audit logging never raises exceptions."""
    user = CurrentUser(
        id=1,
        email="admin@example.com",
        role=Role.ADMIN,
        full_name="Admin User",
        is_active=True,
    )

    # Pass a broken db session to trigger an error
    class BrokenSession:
        def add(self, obj):
            raise RuntimeError("Database is down")

        async def flush(self):
            pass

    # Should not raise
    await audit_service.log_action(
        db=BrokenSession(),
        user=user,
        action="test.action",
        resource_type="test",
    )


# =============================================================================
# Audit Log List Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_audit_log_list_returns_entries(
    client, admin_auth_headers, seed_audit_logs
):
    """Test GET /admin/audit-log returns paginated entries."""
    response = await client.get("/api/v1/admin/audit-log", headers=admin_auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data
    assert data["total"] == 6  # 5 seeded + 1 from different user
    assert len(data["items"]) == 6


@pytest.mark.asyncio
async def test_audit_log_list_pagination(client, admin_auth_headers, seed_audit_logs):
    """Test audit log pagination works correctly."""
    response = await client.get(
        "/api/v1/admin/audit-log?page=1&per_page=2", headers=admin_auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 6
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert data["pages"] == 3  # ceil(6/2) = 3


@pytest.mark.asyncio
async def test_audit_log_list_ordered_newest_first(
    client, admin_auth_headers, seed_audit_logs
):
    """Test audit log entries are ordered newest first."""
    response = await client.get("/api/v1/admin/audit-log", headers=admin_auth_headers)
    assert response.status_code == 200

    data = response.json()
    items = data["items"]
    timestamps = [item["timestamp"] for item in items]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.asyncio
async def test_audit_log_filter_by_action(client, admin_auth_headers, seed_audit_logs):
    """Test filtering audit log by action."""
    response = await client.get(
        "/api/v1/admin/audit-log?action=extract.trigger",
        headers=admin_auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3  # indices 0, 2, 4
    for item in data["items"]:
        assert item["action"] == "extract.trigger"


@pytest.mark.asyncio
async def test_audit_log_filter_by_user_id(client, admin_auth_headers, seed_audit_logs):
    """Test filtering audit log by user_id."""
    response = await client.get(
        "/api/v1/admin/audit-log?user_id=3", headers=admin_auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["user_email"] == "other-admin@example.com"


@pytest.mark.asyncio
async def test_audit_log_filter_by_resource_type(
    client, admin_auth_headers, seed_audit_logs
):
    """Test filtering audit log by resource_type."""
    response = await client.get(
        "/api/v1/admin/audit-log?resource_type=user", headers=admin_auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["action"] == "user.create"


@pytest.mark.asyncio
async def test_audit_log_empty_result(client, admin_auth_headers, db_session):
    """Test audit log returns empty result when no entries exist."""
    response = await client.get("/api/v1/admin/audit-log", headers=admin_auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["pages"] == 0


# =============================================================================
# Access Control Tests
# =============================================================================


@pytest.mark.asyncio
async def test_audit_log_denied_for_non_admin(client, viewer_auth_headers):
    """Test that non-admin (viewer) users cannot access audit logs."""
    response = await client.get("/api/v1/admin/audit-log", headers=viewer_auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_denied_for_analyst(client, auth_headers):
    """Test that analyst users cannot access admin audit logs."""
    response = await client.get("/api/v1/admin/audit-log", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_denied_for_unauthenticated(client):
    """Test that unauthenticated users cannot access audit logs."""
    response = await client.get("/api/v1/admin/audit-log")
    assert response.status_code == 401


# =============================================================================
# Admin Endpoint Audit Logging Integration Tests
# =============================================================================


@pytest.mark.asyncio
@patch(
    "app.api.v1.endpoints.admin.trigger_fred_extraction",
    new_callable=AsyncMock,
)
async def test_extract_fred_creates_audit_entry(
    mock_fred, client, admin_auth_headers, db_session
):
    """Test that triggering FRED extraction creates an audit log entry."""
    response = await client.post(
        "/api/v1/admin/extract/fred?incremental=true",
        headers=admin_auth_headers,
    )
    assert response.status_code == 200

    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entries = result.scalars().all()

    assert len(entries) == 1
    entry = entries[0]
    assert entry.action == "extract.trigger"
    assert entry.resource_type == "extraction"
    assert entry.resource_id == "fred"


@pytest.mark.asyncio
@patch(
    "app.api.v1.endpoints.admin.trigger_costar_extraction",
    new_callable=AsyncMock,
)
async def test_extract_costar_creates_audit_entry(
    mock_costar, client, admin_auth_headers, db_session
):
    """Test that triggering CoStar extraction creates an audit log entry."""
    response = await client.post(
        "/api/v1/admin/extract/costar", headers=admin_auth_headers
    )
    assert response.status_code == 200

    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entries = result.scalars().all()

    assert len(entries) == 1
    assert entries[0].resource_id == "costar"


@pytest.mark.asyncio
@patch(
    "app.api.v1.endpoints.admin.trigger_census_extraction",
    new_callable=AsyncMock,
)
async def test_extract_census_creates_audit_entry(
    mock_census, client, admin_auth_headers, db_session
):
    """Test that triggering Census extraction creates an audit log entry."""
    response = await client.post(
        "/api/v1/admin/extract/census", headers=admin_auth_headers
    )
    assert response.status_code == 200

    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entries = result.scalars().all()

    assert len(entries) == 1
    assert entries[0].resource_id == "census"
