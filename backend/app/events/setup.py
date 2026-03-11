"""Register default event handlers at application startup."""

from app.events import handlers
from app.events.bus import get_event_bus


def register_default_handlers() -> None:
    """Wire up all default event handlers.

    Called once during the FastAPI lifespan startup sequence.
    """
    bus = get_event_bus()
    bus.subscribe("deal.created", handlers.log_deal_created)
    bus.subscribe("deal.stage_changed", handlers.log_stage_change)
    bus.subscribe("extraction.completed", handlers.log_extraction_completed)
    bus.subscribe("market_data.refreshed", handlers.log_market_refresh)
