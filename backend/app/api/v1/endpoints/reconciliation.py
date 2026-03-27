"""
Reconciliation API endpoints.

Provides endpoints for comparing SharePoint folder contents with database
state and viewing reconciliation history.

All endpoints require analyst-level authentication.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_analyst
from app.db.session import get_db
from app.schemas.reconciliation import (
    ReconciliationHistoryItem,
    ReconciliationReport,
    ReconciliationTriggerResponse,
)

router = APIRouter()


@router.get(
    "/latest",
    response_model=ReconciliationReport | None,
    summary="Get the most recent reconciliation report",
)
async def get_latest_reconciliation(
    _user: Any = Depends(require_analyst),
) -> ReconciliationReport | None:
    """Return the most recent reconciliation report.

    Returns ``null`` if no reconciliation has been run yet.
    """
    from app.services.reconciliation import get_latest_report

    return get_latest_report()


@router.get(
    "/history",
    response_model=list[ReconciliationHistoryItem],
    summary="Get reconciliation report history",
)
async def get_reconciliation_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _user: Any = Depends(require_analyst),
) -> list[ReconciliationHistoryItem]:
    """Return abbreviated summaries of past reconciliation runs."""
    from app.services.reconciliation import get_report_history

    return get_report_history(limit=limit, offset=offset)


@router.post(
    "/trigger",
    response_model=ReconciliationTriggerResponse,
    summary="Trigger a new reconciliation run",
)
async def trigger_reconciliation(
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_analyst),
) -> ReconciliationTriggerResponse:
    """Run a reconciliation between SharePoint and database state.

    Compares the current SharePoint folder contents with the database
    ``MonitoredFile`` table and returns a detailed discrepancy report.

    This operation may take several seconds if SharePoint discovery is slow.
    If SharePoint is unavailable, the report will indicate that and still
    return database-side information.
    """
    from app.services.reconciliation import run_reconciliation

    logger.info("reconciliation_triggered_via_api")
    report = await run_reconciliation(db)
    return ReconciliationTriggerResponse(
        message="Reconciliation completed",
        report=report,
    )
