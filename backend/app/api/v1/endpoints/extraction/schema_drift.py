"""
API endpoints for Schema Drift Detection alerts.

Provides read access to drift alerts and the ability to resolve them.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, require_analyst, require_manager
from app.crud.schema_drift import SchemaDriftAlertCRUD
from app.db.session import get_db
from app.schemas.schema_drift import (
    SchemaDriftAlertListResponse,
    SchemaDriftAlertResponse,
)

router = APIRouter(prefix="/drift-alerts", tags=["extraction-drift"])


@router.get("", response_model=SchemaDriftAlertListResponse)
async def list_drift_alerts(
    group_name: str | None = Query(None, description="Filter by group name"),
    severity: str | None = Query(
        None, description="Filter by severity (info/warning/error)"
    ),
    resolved: bool | None = Query(None, description="Filter by resolution status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
) -> SchemaDriftAlertListResponse:
    """List schema drift alerts with optional filters."""
    alerts = await SchemaDriftAlertCRUD.get_alerts(
        db,
        group_name=group_name,
        severity=severity,
        resolved=resolved,
        limit=limit,
    )
    return SchemaDriftAlertListResponse(
        alerts=[SchemaDriftAlertResponse.model_validate(a) for a in alerts],
        total=len(alerts),
    )


@router.post("/{alert_id}/resolve", response_model=SchemaDriftAlertResponse)
async def resolve_drift_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
) -> SchemaDriftAlertResponse:
    """Mark a schema drift alert as resolved."""
    alert = await SchemaDriftAlertCRUD.resolve_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return SchemaDriftAlertResponse.model_validate(alert)
