"""Tests for deal optimistic locking (version column)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deal, DealStage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_deal(db: AsyncSession) -> Deal:
    """Insert a deal directly into the database and return it."""
    deal = Deal(
        name="Locking Test Deal",
        deal_type="acquisition",
        stage=DealStage.INITIAL_REVIEW,
        stage_order=0,
        asking_price=Decimal("10000000.00"),
        priority="medium",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(deal)
    await db.commit()
    await db.refresh(deal)
    return deal


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_new_deal_has_version_1(db_session: AsyncSession) -> None:
    """A newly created deal should have version == 1."""
    deal = await _create_deal(db_session)
    assert deal.version == 1


async def test_update_with_correct_version(
    client: AsyncClient,
    db_session: AsyncSession,
    auto_auth,
) -> None:
    """PUT with matching version should succeed and increment the version."""
    deal = await _create_deal(db_session)

    response = await client.put(
        f"/api/v1/deals/{deal.id}",
        json={
            "version": 1,
            "name": "Updated Name",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["version"] == 2


async def test_update_with_stale_version_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
    auto_auth,
) -> None:
    """PUT with an outdated version should return 409 Conflict."""
    deal = await _create_deal(db_session)

    # First update succeeds (version 1 -> 2)
    resp1 = await client.put(
        f"/api/v1/deals/{deal.id}",
        json={"version": 1, "priority": "high"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["version"] == 2

    # Second update with stale version 1 should fail
    resp2 = await client.put(
        f"/api/v1/deals/{deal.id}",
        json={"version": 1, "priority": "urgent"},
    )
    assert resp2.status_code == 409
    assert "modified by another user" in resp2.json()["detail"]


async def test_version_increments_on_each_update(
    client: AsyncClient,
    db_session: AsyncSession,
    auto_auth,
) -> None:
    """Version should increment by 1 on every successful update."""
    deal = await _create_deal(db_session)

    for expected_version in range(1, 5):
        resp = await client.put(
            f"/api/v1/deals/{deal.id}",
            json={"version": expected_version, "notes": f"Edit #{expected_version}"},
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == expected_version + 1


async def test_concurrent_edits_second_fails(
    client: AsyncClient,
    db_session: AsyncSession,
    auto_auth,
) -> None:
    """Simulate two users reading version 1, then both trying to update.
    The first should succeed, the second should get 409."""
    deal = await _create_deal(db_session)

    # Both users read version 1
    read_version = 1

    # User A updates first — succeeds
    resp_a = await client.put(
        f"/api/v1/deals/{deal.id}",
        json={"version": read_version, "notes": "User A edit"},
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["version"] == 2

    # User B tries with the same stale version — 409
    resp_b = await client.put(
        f"/api/v1/deals/{deal.id}",
        json={"version": read_version, "notes": "User B edit"},
    )
    assert resp_b.status_code == 409


async def test_patch_with_correct_version(
    client: AsyncClient,
    db_session: AsyncSession,
    auto_auth,
) -> None:
    """PATCH endpoint should also enforce optimistic locking."""
    deal = await _create_deal(db_session)

    response = await client.patch(
        f"/api/v1/deals/{deal.id}",
        json={"version": 1, "priority": "urgent"},
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert response.json()["priority"] == "urgent"


async def test_patch_with_stale_version_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
    auto_auth,
) -> None:
    """PATCH with stale version should return 409."""
    deal = await _create_deal(db_session)

    # Advance version to 2
    resp1 = await client.patch(
        f"/api/v1/deals/{deal.id}",
        json={"version": 1, "priority": "high"},
    )
    assert resp1.status_code == 200

    # Stale version 1 on PATCH
    resp2 = await client.patch(
        f"/api/v1/deals/{deal.id}",
        json={"version": 1, "priority": "urgent"},
    )
    assert resp2.status_code == 409


async def test_version_returned_in_get_response(
    client: AsyncClient,
    db_session: AsyncSession,
    auto_auth,
) -> None:
    """GET /deals/{id} should include the version field."""
    deal = await _create_deal(db_session)

    response = await client.get(f"/api/v1/deals/{deal.id}")
    assert response.status_code == 200
    assert response.json()["version"] == 1


async def test_update_missing_version_returns_422(
    client: AsyncClient,
    db_session: AsyncSession,
    auto_auth,
) -> None:
    """PUT without the required version field should return 422."""
    deal = await _create_deal(db_session)

    response = await client.put(
        f"/api/v1/deals/{deal.id}",
        json={"name": "No version provided"},
    )
    assert response.status_code == 422
