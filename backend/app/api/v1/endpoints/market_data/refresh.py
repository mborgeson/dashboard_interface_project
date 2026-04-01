"""
Market data refresh endpoint — analyst+ FRED extraction trigger.

Note: market_data_service is accessed via sys.modules to support test mocking.
Tests patch ``app.api.v1.endpoints.market_data.market_data_service``, so all
sub-modules must resolve the service through the package namespace.
"""

import sys

from fastapi import APIRouter, Depends
from loguru import logger

from app.core.permissions import CurrentUser, require_analyst

router = APIRouter()


def _svc():
    """Resolve market_data_service through the package namespace for mock support."""
    return sys.modules["app.api.v1.endpoints.market_data"].market_data_service


@router.post("/refresh")
async def refresh_market_data(
    _current_user: CurrentUser = Depends(require_analyst),
):
    """
    Trigger an incremental FRED extraction to refresh market data.

    Runs synchronously so the frontend knows when the refresh is complete
    and can re-fetch updated data.

    Returns:
        Status summary with records upserted count and updated timestamp.
    """
    try:
        from app.services.data_extraction.fred_extractor import (
            run_fred_extraction_async,
        )
        from app.services.data_extraction.scheduler import _get_engine

        engine = _get_engine()
        result = await run_fred_extraction_async(engine=engine, incremental=True)
        # Update the last refreshed timestamp in the service
        new_timestamp = _svc().update_last_refreshed()
        logger.info("Market data refresh completed", result=result)
        return {
            "status": result.get("status", "success"),
            "records_upserted": result.get("records_upserted", 0),
            "message": "Market data refresh completed successfully",
            "last_updated": new_timestamp,
        }
    except RuntimeError as exc:
        logger.warning(f"Market refresh skipped — DB not configured: {exc}")
        return {
            "status": "error",
            "records_upserted": 0,
            "message": f"Database not configured: {exc}",
        }
    except Exception as exc:
        logger.error(f"Market data refresh failed: {exc}")
        return {
            "status": "error",
            "records_upserted": 0,
            "message": str(exc),
        }
