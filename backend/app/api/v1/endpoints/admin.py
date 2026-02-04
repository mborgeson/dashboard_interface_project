"""
Admin endpoints for market data extraction management.
"""

from fastapi import APIRouter, BackgroundTasks

from app.services.data_extraction.scheduler import (
    get_data_freshness,
    trigger_census_extraction,
    trigger_costar_extraction,
    trigger_fred_extraction,
)

router = APIRouter()


@router.post("/extract/fred")
async def extract_fred(background_tasks: BackgroundTasks, incremental: bool = True):
    """Trigger FRED data extraction (runs in background)."""
    background_tasks.add_task(trigger_fred_extraction, incremental=incremental)
    return {"status": "started", "source": "fred", "incremental": incremental}


@router.post("/extract/costar")
async def extract_costar(background_tasks: BackgroundTasks):
    """Trigger CoStar data extraction (runs in background)."""
    background_tasks.add_task(trigger_costar_extraction)
    return {"status": "started", "source": "costar"}


@router.post("/extract/census")
async def extract_census(background_tasks: BackgroundTasks):
    """Trigger Census data extraction (runs in background)."""
    background_tasks.add_task(trigger_census_extraction)
    return {"status": "started", "source": "census"}


@router.get("/market-data-status")
async def market_data_status():
    """Get data freshness and extraction status for all market data sources."""
    return get_data_freshness()
