"""Tests for ReminderDismissal model."""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder_dismissal import ReminderDismissal


@pytest.mark.asyncio
async def test_create_reminder_dismissal(db_session: AsyncSession):
    """Test creating a reminder dismissal record."""
    now = datetime.now(UTC)
    dismissal = ReminderDismissal(
        user_identifier="test-user",
        dismissed_month="2026-02",
        dismissed_at=now,
    )
    db_session.add(dismissal)
    await db_session.commit()
    await db_session.refresh(dismissal)

    assert dismissal.id is not None
    assert dismissal.user_identifier == "test-user"
    assert dismissal.dismissed_month == "2026-02"
    # Compare timestamps (SQLite may strip timezone info)
    assert dismissal.dismissed_at.replace(tzinfo=None) == now.replace(tzinfo=None)
    assert dismissal.created_at is not None
    assert dismissal.updated_at is not None


@pytest.mark.asyncio
async def test_unique_constraint_user_month(db_session: AsyncSession):
    """Test that user_identifier + dismissed_month is unique."""
    now = datetime.now(UTC)

    # Create first dismissal
    dismissal1 = ReminderDismissal(
        user_identifier="test-user",
        dismissed_month="2026-02",
        dismissed_at=now,
    )
    db_session.add(dismissal1)
    await db_session.commit()

    # Try to create duplicate
    dismissal2 = ReminderDismissal(
        user_identifier="test-user",
        dismissed_month="2026-02",
        dismissed_at=now,
    )
    db_session.add(dismissal2)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_different_months_same_user(db_session: AsyncSession):
    """Test that same user can dismiss different months."""
    now = datetime.now(UTC)

    dismissal1 = ReminderDismissal(
        user_identifier="test-user",
        dismissed_month="2026-01",
        dismissed_at=now,
    )
    dismissal2 = ReminderDismissal(
        user_identifier="test-user",
        dismissed_month="2026-02",
        dismissed_at=now,
    )
    db_session.add_all([dismissal1, dismissal2])
    await db_session.commit()

    result = await db_session.execute(
        select(ReminderDismissal).where(
            ReminderDismissal.user_identifier == "test-user"
        )
    )
    dismissals = result.scalars().all()
    assert len(dismissals) == 2


@pytest.mark.asyncio
async def test_different_users_same_month(db_session: AsyncSession):
    """Test that different users can dismiss the same month."""
    now = datetime.now(UTC)

    dismissal1 = ReminderDismissal(
        user_identifier="user-1",
        dismissed_month="2026-02",
        dismissed_at=now,
    )
    dismissal2 = ReminderDismissal(
        user_identifier="user-2",
        dismissed_month="2026-02",
        dismissed_at=now,
    )
    db_session.add_all([dismissal1, dismissal2])
    await db_session.commit()

    result = await db_session.execute(
        select(ReminderDismissal).where(
            ReminderDismissal.dismissed_month == "2026-02"
        )
    )
    dismissals = result.scalars().all()
    assert len(dismissals) == 2


@pytest.mark.asyncio
async def test_repr(db_session: AsyncSession):
    """Test the __repr__ method."""
    dismissal = ReminderDismissal(
        user_identifier="test-user",
        dismissed_month="2026-02",
        dismissed_at=datetime.now(UTC),
    )
    db_session.add(dismissal)
    await db_session.commit()
    await db_session.refresh(dismissal)

    repr_str = repr(dismissal)
    assert "ReminderDismissal" in repr_str
    assert "test-user" in repr_str
    assert "2026-02" in repr_str
