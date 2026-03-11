"""
Deal analytics endpoints — proforma returns and extraction-derived metrics.
"""

from collections.abc import Sequence

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Row, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, require_analyst
from app.crud import deal as deal_crud
from app.db.session import get_db
from app.models.extraction import ExtractedValue

from .enrichment import PROFORMA_FIELDS

router = APIRouter()
slog = structlog.get_logger("app.api.deals")


@router.get(
    "/{deal_id}/proforma-returns",
    summary="Get proforma returns",
    description="Retrieve proforma-specific extracted values for a deal including year-specific "
    "IRR, MOIC, NOI per unit, cap rates, DSCR, and debt yield. Values are grouped by category "
    "and sourced from the extraction pipeline.",
    responses={
        200: {"description": "Proforma return metrics grouped by category"},
        404: {"description": "Deal not found"},
    },
)
async def get_deal_proforma_returns(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get Proforma-specific extracted values for a deal.

    Queries extracted_values for year-specific IRR, MOIC, NOI, cap rates,
    DSCR, and other fields that exist only in Proforma/group extraction runs.
    Returns values grouped by category.
    """
    # Get the deal to find its name (used as property_name in extracted_values)
    deal = await deal_crud.get(db, deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    deal_name = deal.name

    # Prefer property_id FK join over string matching on names
    rows: Sequence[Row] = []
    if deal.property_id is not None:
        stmt = (
            select(
                ExtractedValue.field_name,
                ExtractedValue.field_category,
                ExtractedValue.value_numeric,
                ExtractedValue.value_text,
                ExtractedValue.source_file,
            )
            .where(
                ExtractedValue.property_id == deal.property_id,
                ExtractedValue.field_name.in_(PROFORMA_FIELDS),
                ExtractedValue.is_error.is_(False),
            )
            .order_by(ExtractedValue.field_category, ExtractedValue.field_name)
        )
        result = await db.execute(stmt)
        rows = result.all()

    # Fall back to name-matching if no property_id link or no results found
    if not rows:
        import re as _re

        from sqlalchemy import or_

        base_name_match = _re.match(r"^(.+?)\s*\([^)]+,\s*[A-Z]{2}\)", deal_name)
        names_to_search = [deal_name]
        if base_name_match:
            names_to_search.append(base_name_match.group(1).strip())

        stmt = (
            select(
                ExtractedValue.field_name,
                ExtractedValue.field_category,
                ExtractedValue.value_numeric,
                ExtractedValue.value_text,
                ExtractedValue.source_file,
            )
            .where(
                or_(*[ExtractedValue.property_name == n for n in names_to_search]),
                ExtractedValue.field_name.in_(PROFORMA_FIELDS),
                ExtractedValue.is_error.is_(False),
            )
            .order_by(ExtractedValue.field_category, ExtractedValue.field_name)
        )
        result = await db.execute(stmt)
        rows = result.all()

    if not rows:
        return {"deal_id": deal_id, "deal_name": deal_name, "groups": [], "total": 0}

    # Group by category
    groups: dict[str, list[dict]] = {}
    for row in rows:
        cat = row.field_category or "Proforma"
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(
            {
                "field_name": row.field_name,
                "value_numeric": float(row.value_numeric)
                if row.value_numeric is not None
                else None,
                "value_text": row.value_text,
            }
        )

    return {
        "deal_id": deal_id,
        "deal_name": deal_name,
        "groups": [
            {"category": cat, "fields": fields} for cat, fields in groups.items()
        ],
        "total": len(rows),
    }
