"""Tests for default event handlers."""

from unittest.mock import patch

import pytest

from app.events.definitions import (
    DealCreated,
    DealStageChanged,
    ExtractionCompleted,
    MarketDataRefreshed,
)
from app.events.handlers import (
    log_deal_created,
    log_extraction_completed,
    log_market_refresh,
    log_stage_change,
)


@pytest.mark.asyncio
async def test_log_deal_created() -> None:
    event = DealCreated(deal_id=5, property_name="Sunrise Villas", created_by="matt")
    with patch("app.events.handlers.logger") as mock_logger:
        await log_deal_created(event)
        msg = mock_logger.info.call_args[0][0]
        assert "5" in msg
        assert "Sunrise Villas" in msg


@pytest.mark.asyncio
async def test_log_stage_change() -> None:
    event = DealStageChanged(
        deal_id=3,
        old_stage="screening",
        new_stage="underwriting",
        changed_by="jane",
    )
    with patch("app.events.handlers.logger") as mock_logger:
        await log_stage_change(event)
        msg = mock_logger.info.call_args[0][0]
        assert "3" in msg
        assert "screening" in msg
        assert "underwriting" in msg


@pytest.mark.asyncio
async def test_log_extraction_completed() -> None:
    event = ExtractionCompleted(run_id="run-42", property_count=11, value_count=12881)
    with patch("app.events.handlers.logger") as mock_logger:
        await log_extraction_completed(event)
        msg = mock_logger.info.call_args[0][0]
        assert "run-42" in msg
        assert "11" in msg
        assert "12881" in msg


@pytest.mark.asyncio
async def test_log_market_refresh() -> None:
    event = MarketDataRefreshed(records_upserted=253000, source="costar")
    with patch("app.events.handlers.logger") as mock_logger:
        await log_market_refresh(event)
        msg = mock_logger.info.call_args[0][0]
        assert "costar" in msg
        assert "253000" in msg


@pytest.mark.asyncio
async def test_log_market_refresh_default_source() -> None:
    event = MarketDataRefreshed(records_upserted=100)
    with patch("app.events.handlers.logger") as mock_logger:
        await log_market_refresh(event)
        msg = mock_logger.info.call_args[0][0]
        assert "fred" in msg
