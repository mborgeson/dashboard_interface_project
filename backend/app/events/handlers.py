"""Default event handlers -- registered at app startup via ``setup.py``."""

from loguru import logger

from app.events.bus import DomainEvent


async def log_deal_created(event: DomainEvent) -> None:
    """Log deal creation to activity log."""
    logger.info(
        f"Deal created: {event.deal_id} - {event.property_name}"  # type: ignore[attr-defined]
    )


async def log_stage_change(event: DomainEvent) -> None:
    """Log deal stage transitions."""
    logger.info(
        f"Deal {event.deal_id} stage: "  # type: ignore[attr-defined]
        f"{event.old_stage} -> {event.new_stage}"  # type: ignore[attr-defined]
    )


async def log_extraction_completed(event: DomainEvent) -> None:
    """Log extraction completion."""
    logger.info(
        f"Extraction {event.run_id}: "  # type: ignore[attr-defined]
        f"{event.property_count} properties, "  # type: ignore[attr-defined]
        f"{event.value_count} values"  # type: ignore[attr-defined]
    )


async def log_market_refresh(event: DomainEvent) -> None:
    """Log market data refresh."""
    logger.info(
        f"Market data refreshed from {event.source}: "  # type: ignore[attr-defined]
        f"{event.records_upserted} records"  # type: ignore[attr-defined]
    )
