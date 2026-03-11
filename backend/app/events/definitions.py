"""Concrete domain event types used throughout the application."""

from dataclasses import dataclass, field

from app.events.bus import DomainEvent


@dataclass
class DealCreated(DomainEvent):
    """Published when a new deal is created."""

    event_type: str = "deal.created"
    deal_id: int = 0
    property_name: str = ""
    created_by: str = ""


@dataclass
class DealStageChanged(DomainEvent):
    """Published when a deal moves to a different pipeline stage."""

    event_type: str = "deal.stage_changed"
    deal_id: int = 0
    old_stage: str = ""
    new_stage: str = ""
    changed_by: str = ""


@dataclass
class ExtractionCompleted(DomainEvent):
    """Published when an extraction run finishes successfully."""

    event_type: str = "extraction.completed"
    run_id: str = ""
    property_count: int = 0
    value_count: int = 0


@dataclass
class MarketDataRefreshed(DomainEvent):
    """Published after a market-data ingestion cycle."""

    event_type: str = "market_data.refreshed"
    records_upserted: int = 0
    source: str = "fred"


@dataclass
class UserLoggedIn(DomainEvent):
    """Published on successful user authentication."""

    event_type: str = "user.logged_in"
    user_id: int = 0
    email: str = ""


@dataclass
class PropertyUpdated(DomainEvent):
    """Published when a property record is modified."""

    event_type: str = "property.updated"
    property_id: int = 0
    fields_changed: list[str] = field(default_factory=list)
