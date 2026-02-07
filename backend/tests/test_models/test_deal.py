"""Tests for the Deal model."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Deal, DealStage


@pytest.mark.asyncio
async def test_create_deal(db_session, test_user):
    """Test creating a new deal."""
    deal = Deal(
        name="Test Acquisition",
        deal_type="acquisition",
        stage=DealStage.INITIAL_REVIEW,
        assigned_user_id=test_user.id,
        asking_price=Decimal("20000000.00"),
        priority="high",
    )
    db_session.add(deal)
    await db_session.commit()
    await db_session.refresh(deal)

    assert deal.id is not None
    assert deal.name == "Test Acquisition"
    assert deal.deal_type == "acquisition"
    assert deal.stage == DealStage.INITIAL_REVIEW
    assert deal.priority == "high"


@pytest.mark.asyncio
async def test_deal_stages(db_session):
    """Test all deal stages can be used."""
    for stage in DealStage:
        deal = Deal(
            name=f"Deal - {stage.value}",
            deal_type="acquisition",
            stage=stage,
            priority="medium",
        )
        db_session.add(deal)

    await db_session.commit()

    result = await db_session.execute(select(Deal))
    deals = result.scalars().all()
    assert len(deals) == len(DealStage)


@pytest.mark.asyncio
async def test_deal_stage_update(test_deal):
    """Test updating a deal's stage."""
    assert test_deal.stage == DealStage.ACTIVE_REVIEW

    test_deal.update_stage(DealStage.UNDER_CONTRACT)

    assert test_deal.stage == DealStage.UNDER_CONTRACT
    assert test_deal.stage_updated_at is not None


@pytest.mark.asyncio
async def test_deal_financial_metrics(db_session, test_user):
    """Test deal financial metrics."""
    deal = Deal(
        name="Financial Test Deal",
        deal_type="acquisition",
        stage=DealStage.ACTIVE_REVIEW,
        asking_price=Decimal("25000000.00"),
        offer_price=Decimal("23500000.00"),
        final_price=Decimal("24000000.00"),
        projected_irr=Decimal("22.500"),
        projected_coc=Decimal("9.250"),
        projected_equity_multiple=Decimal("2.35"),
        hold_period_years=7,
        priority="urgent",
    )
    db_session.add(deal)
    await db_session.commit()
    await db_session.refresh(deal)

    assert deal.asking_price == Decimal("25000000.00")
    assert deal.offer_price == Decimal("23500000.00")
    assert deal.projected_irr == Decimal("22.500")


@pytest.mark.asyncio
async def test_deal_activity_log(test_deal):
    """Test adding activities to deal log."""
    test_deal.add_activity(
        {"type": "note", "user": "Test User", "content": "Initial review completed"}
    )

    assert test_deal.activity_log is not None
    assert len(test_deal.activity_log) == 1
    assert test_deal.activity_log[0]["type"] == "note"
    assert "timestamp" in test_deal.activity_log[0]


@pytest.mark.asyncio
async def test_deal_fixture(test_deal):
    """Test that the test_deal fixture works."""
    assert test_deal.id is not None
    assert test_deal.name == "Test Deal #0001"
    assert test_deal.stage == DealStage.ACTIVE_REVIEW


@pytest.mark.asyncio
async def test_multiple_deals_fixture(multiple_deals):
    """Test that the multiple_deals fixture works."""
    assert len(multiple_deals) == 4
    stages = [d.stage for d in multiple_deals]
    assert DealStage.INITIAL_REVIEW in stages
    assert DealStage.CLOSED in stages


@pytest.mark.asyncio
async def test_deal_repr(test_deal):
    """Test the Deal __repr__ method."""
    assert "<Deal" in repr(test_deal)
    assert test_deal.stage.value in repr(test_deal)
