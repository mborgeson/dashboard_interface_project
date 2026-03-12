"""Tests for concrete domain event definitions."""

from datetime import UTC

import pytest

from app.events.bus import DomainEvent
from app.events.definitions import (
    DealCreated,
    DealStageChanged,
    ExtractionCompleted,
    MarketDataRefreshed,
    PropertyUpdated,
    UserLoggedIn,
)


# ---------------------------------------------------------------------------
# Each event should carry the correct default event_type
# ---------------------------------------------------------------------------

_EVENT_TYPES = [
    (DealCreated, "deal.created"),
    (DealStageChanged, "deal.stage_changed"),
    (ExtractionCompleted, "extraction.completed"),
    (MarketDataRefreshed, "market_data.refreshed"),
    (UserLoggedIn, "user.logged_in"),
    (PropertyUpdated, "property.updated"),
]


@pytest.mark.parametrize("cls, expected_type", _EVENT_TYPES)
def test_default_event_type(cls: type, expected_type: str) -> None:
    event = cls()
    assert event.event_type == expected_type


# ---------------------------------------------------------------------------
# Inheritance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cls, _", _EVENT_TYPES)
def test_inherits_domain_event(cls: type, _: str) -> None:
    assert issubclass(cls, DomainEvent)


@pytest.mark.parametrize("cls, _", _EVENT_TYPES)
def test_has_timestamp(cls: type, _: str) -> None:
    event = cls()
    assert event.timestamp is not None
    assert event.timestamp.tzinfo is not None


@pytest.mark.parametrize("cls, _", _EVENT_TYPES)
def test_has_metadata(cls: type, _: str) -> None:
    event = cls()
    assert isinstance(event.metadata, dict)


# ---------------------------------------------------------------------------
# Field assignment
# ---------------------------------------------------------------------------


def test_deal_created_fields() -> None:
    event = DealCreated(deal_id=7, property_name="Sunset Ridge", created_by="matt")
    assert event.deal_id == 7
    assert event.property_name == "Sunset Ridge"
    assert event.created_by == "matt"
    assert event.event_type == "deal.created"


def test_deal_stage_changed_fields() -> None:
    event = DealStageChanged(
        deal_id=3,
        old_stage="screening",
        new_stage="underwriting",
        changed_by="jane",
    )
    assert event.deal_id == 3
    assert event.old_stage == "screening"
    assert event.new_stage == "underwriting"
    assert event.changed_by == "jane"


def test_extraction_completed_fields() -> None:
    event = ExtractionCompleted(run_id="abc-123", property_count=11, value_count=12881)
    assert event.run_id == "abc-123"
    assert event.property_count == 11
    assert event.value_count == 12881


def test_market_data_refreshed_fields() -> None:
    event = MarketDataRefreshed(records_upserted=253_000, source="costar")
    assert event.records_upserted == 253_000
    assert event.source == "costar"


def test_market_data_refreshed_default_source() -> None:
    event = MarketDataRefreshed()
    assert event.source == "fred"


def test_user_logged_in_fields() -> None:
    event = UserLoggedIn(user_id=42, email="matt@bandrcapital.com")
    assert event.user_id == 42
    assert event.email == "matt@bandrcapital.com"


def test_property_updated_fields() -> None:
    event = PropertyUpdated(property_id=99, fields_changed=["noi", "cap_rate"])
    assert event.property_id == 99
    assert event.fields_changed == ["noi", "cap_rate"]


def test_property_updated_default_fields_changed() -> None:
    event = PropertyUpdated(property_id=1)
    assert event.fields_changed == []


# ---------------------------------------------------------------------------
# Metadata pass-through
# ---------------------------------------------------------------------------


def test_metadata_passed_to_subclass() -> None:
    meta = {"request_id": "req-001"}
    event = DealCreated(deal_id=1, metadata=meta)
    assert event.metadata == meta
