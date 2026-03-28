"""
API endpoints for Domain Validation warnings.

Surfaces extracted values that were flagged with domain validation
warnings (e.g. cap rate of 500%, negative unit count).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, require_analyst
from app.db.session import get_db
from app.models.extraction import ExtractedValue
from app.schemas.domain_validation import (
    DomainWarningItem,
    DomainWarningListResponse,
)

router = APIRouter(prefix="/domain-warnings", tags=["extraction-validation"])


@router.get("", response_model=DomainWarningListResponse)
async def list_domain_warnings(
    property_name: str | None = Query(None, description="Filter by property name"),
    field_name: str | None = Query(None, description="Filter by field name"),
    run_id: UUID | None = Query(None, description="Filter by extraction run ID"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
) -> DomainWarningListResponse:
    """List extracted values that have domain validation warnings."""
    # Base query: domain_warning IS NOT NULL
    base_filter = ExtractedValue.domain_warning.isnot(None)

    filters: list[Any] = [base_filter]
    if property_name is not None:
        filters.append(ExtractedValue.property_name == property_name)
    if field_name is not None:
        filters.append(ExtractedValue.field_name == field_name)
    if run_id is not None:
        filters.append(ExtractedValue.extraction_run_id == run_id)

    # Count query
    count_stmt = select(func.count(ExtractedValue.id)).where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    # Data query
    data_stmt = (
        select(ExtractedValue)
        .where(*filters)
        .order_by(ExtractedValue.property_name, ExtractedValue.field_name)
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(data_stmt)).scalars().all()

    warnings = [
        DomainWarningItem(
            field_name=row.field_name,
            value=row.value_text,
            property_name=row.property_name,
            domain_warning=row.domain_warning,  # type: ignore[arg-type]
            source_file=row.source_file,
        )
        for row in rows
    ]

    return DomainWarningListResponse(
        warnings=warnings,
        total=total,
        limit=limit,
        offset=offset,
    )
