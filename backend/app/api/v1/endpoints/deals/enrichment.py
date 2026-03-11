"""
Extraction enrichment helpers for deal responses.

Shared utility functions that enrich deal response objects with data
from the extraction pipeline (units, owner, IRR, cap rates, etc.).
"""

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache, make_cache_key
from app.models.extraction import ExtractedValue, ExtractionRun
from app.schemas.deal import DealResponse

slog = structlog.get_logger("app.api.deals")

# Fields fetched from extracted_values for deal enrichment
_ENRICHMENT_FIELDS = [
    "TOTAL_UNITS",
    "AVERAGE_UNIT_SF",
    "CURRENT_OWNER",
    "LAST_SALE_PRICE_PER_UNIT",
    "LAST_SALE_DATE",
    "T12_RETURN_ON_COST",
    "LP_RETURNS_IRR",
    "LP_RETURNS_MOIC",
    "UNLEVERED_RETURNS_IRR",
    "UNLEVERED_RETURNS_MOIC",
    "LEVERED_RETURNS_IRR",
    "LEVERED_RETURNS_MOIC",
    "PROPERTY_CITY",
    "SUBMARKET",
    "YEAR_BUILT",
    "YEAR_RENOVATED",
    "VACANCY_LOSS_YEAR_1_RATE",
    "BAD_DEBTS_YEAR_1_RATE",
    "OTHER_LOSS_YEAR_1_RATE",
    "CONCESSIONS_YEAR_1_RATE",
    "NET_OPERATING_INCOME_MARGIN",
    "PURCHASE_PRICE",
    "TOTAL_ACQUISITION_BUDGET",
    "BASIS_UNIT_AT_CLOSE",
    "T12_RETURN_ON_PP",
    "T3_RETURN_ON_PP",
    # TOTAL_RETURN_ON_COST_AT_EXIT and PURCHASE_PRICE_RETURN_ON_COST_AT_EXIT
    # are exit metrics, not going-in cap rates — no longer used for TC cap rates
    "LOAN_AMOUNT",
    "EQUITY_LP_CAPITAL",
    "EXIT_PERIOD_MONTHS",
    "EXIT_CAP_RATE",
    "T3_RETURN_ON_COST",
    "PROPERTY_LATITUDE",
    "PROPERTY_LONGITUDE",
]

# ── Extraction enrichment cache key prefix ───────────────────────────
# Used for targeted invalidation when extraction data changes.
EXTRACTION_CACHE_PREFIX = "deal_extraction_*"

# Fields that only exist in Proforma/group-extraction runs
PROFORMA_FIELDS = {
    # Year-specific IRR / MOIC
    "LEVERED_RETURNS_IRR_YR2",
    "LEVERED_RETURNS_IRR_YR3",
    "LEVERED_RETURNS_IRR_YR7",
    "LEVERED_RETURNS_MOIC_YR2",
    "LEVERED_RETURNS_MOIC_YR3",
    "LEVERED_RETURNS_MOIC_YR7",
    "UNLEVERED_RETURNS_IRR_YR2",
    "UNLEVERED_RETURNS_IRR_YR3",
    "UNLEVERED_RETURNS_IRR_YR7",
    "UNLEVERED_RETURNS_MOIC_YR2",
    "UNLEVERED_RETURNS_MOIC_YR3",
    "UNLEVERED_RETURNS_MOIC_YR7",
    # NOI per unit by year
    "NOI_PER_UNIT_YR2",
    "NOI_PER_UNIT_YR3",
    "NOI_PER_UNIT_YR5",
    "NOI_PER_UNIT_YR7",
    # Cap rates
    "CAP_RATE_ALL_IN_YR3",
    "CAP_RATE_ALL_IN_YR5",
    # Cash-on-cash / DSCR
    "COC_YR5",
    "DSCR_T3",
    "DSCR_YR5",
    # Proforma NOI / DSCR / Debt Yield
    "PROFORMA_NOI_YR1",
    "PROFORMA_NOI_YR2",
    "PROFORMA_NOI_YR3",
    "PROFORMA_DSCR_YR1",
    "PROFORMA_DSCR_YR2",
    "PROFORMA_DSCR_YR3",
    "PROFORMA_DEBT_YIELD_YR1",
    "PROFORMA_DEBT_YIELD_YR2",
    "PROFORMA_DEBT_YIELD_YR3",
}


async def enrich_deals_with_extraction(
    db: AsyncSession, deal_responses: list[DealResponse]
) -> list[DealResponse]:
    """Add extraction-derived fields (units, owner, IRR, etc.) to deal responses.

    Caching strategy (F-044):
    ─────────────────────────
    Extraction data changes only when a new extraction run completes, which is
    infrequent (manual trigger).  We cache the per-property enrichment lookup
    under a ``deal_extraction_enrichment:<sorted_prop_ids_hash>`` key with a
    30-minute TTL.  This avoids re-running the expensive subquery on every
    kanban board load or deal list request.

    Cache invalidation paths:
    * Any deal mutation (create/update/delete/stage-change) calls
      ``cache.invalidate_deals()`` which clears all ``deal_*`` keys.
    * New extraction runs should call ``cache.invalidate_pattern("deal_extraction_*")``
      to force a fresh lookup (see extraction endpoints).
    * The 30-min TTL acts as a safety net so stale data self-expires even if
      explicit invalidation is missed.
    """
    # Collect property IDs
    prop_ids = [d.property_id for d in deal_responses if d.property_id]
    if not prop_ids:
        return deal_responses

    # ── Extraction enrichment cache ──────────────────────────────────
    # Cache TTL: 30 minutes.  Extraction data changes infrequently (only on
    # new extraction runs), so a longer TTL is safe.  The key is based on the
    # sorted set of property IDs so different page/filter combos that share
    # the same properties can reuse the cache.
    ENRICHMENT_TTL = 1800  # 30 minutes

    sorted_ids = sorted(set(prop_ids))
    cache_key = make_cache_key(
        "deal_extraction_enrichment",
        ":".join(str(pid) for pid in sorted_ids),
    )

    cached_lookup = await cache.get(cache_key)
    if cached_lookup is not None:
        slog.debug(
            "extraction_enrichment_cache_hit",
            property_count=len(sorted_ids),
        )
        lookup: dict[int, dict[str, dict[str, str | float | None]]] = {
            int(k): v for k, v in cached_lookup.items()
        }
    else:
        slog.debug(
            "extraction_enrichment_cache_miss",
            property_count=len(sorted_ids),
        )
        lookup = await _fetch_extraction_lookup(db, prop_ids)
        # Store serializable version in cache
        await cache.set(cache_key, lookup, ttl=ENRICHMENT_TTL)

    _apply_extraction_fields(deal_responses, lookup)
    return deal_responses


async def invalidate_extraction_enrichment_cache() -> int:
    """Invalidate all cached extraction enrichment data.

    Call this after extraction runs complete to ensure the next kanban/deal-list
    request fetches fresh extraction values from the database.

    Returns:
        Number of cache keys invalidated.
    """
    count = await cache.invalidate_pattern(EXTRACTION_CACHE_PREFIX)
    if count:
        slog.info("extraction_enrichment_cache_invalidated", keys_cleared=count)
    return count


async def _fetch_extraction_lookup(
    db: AsyncSession, prop_ids: list[int]
) -> dict[int, dict[str, dict[str, str | float | None]]]:
    """Query the DB for extraction values and return a JSON-serializable lookup.

    Returns:
        ``{property_id: {field_name: {value_numeric, value_text}}}``
    """
    # Subquery: latest completed extraction_run_id per property_id
    latest_run_subq = (
        select(
            ExtractedValue.property_id,
            func.max(ExtractionRun.completed_at).label("max_completed"),
        )
        .join(ExtractionRun, ExtractedValue.extraction_run_id == ExtractionRun.id)
        .where(
            ExtractedValue.property_id.in_(prop_ids),
            ExtractionRun.status == "completed",
        )
        .group_by(ExtractedValue.property_id)
        .subquery()
    )

    stmt = (
        select(ExtractedValue)
        .join(ExtractionRun, ExtractedValue.extraction_run_id == ExtractionRun.id)
        .join(
            latest_run_subq,
            (ExtractedValue.property_id == latest_run_subq.c.property_id)
            & (ExtractionRun.completed_at == latest_run_subq.c.max_completed),
        )
        .where(
            ExtractedValue.property_id.in_(prop_ids),
            ExtractedValue.field_name.in_(_ENRICHMENT_FIELDS),
        )
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    # Build a JSON-serializable lookup: {property_id: {field_name: {value_numeric, value_text}}}
    lookup: dict[int, dict[str, dict[str, str | float | None]]] = {}
    for row in rows:
        if row.property_id is not None:
            lookup.setdefault(row.property_id, {})[row.field_name] = {
                "value_numeric": float(row.value_numeric)
                if row.value_numeric is not None
                else None,
                "value_text": row.value_text,
            }

    return lookup


def _apply_extraction_fields(
    deal_responses: list[DealResponse],
    lookup: dict[int, dict[str, dict[str, str | float | None]]],
) -> None:
    """Apply cached extraction lookup values onto deal response objects.

    The lookup uses plain dicts (not ORM objects) so it can be
    serialized/deserialized from the cache layer.

    Lookup shape: ``{property_id: {field_name: {"value_numeric": ..., "value_text": ...}}}``
    """

    def _num(ev: dict[str, str | float | None] | None) -> float | None:
        """Extract numeric value from an enrichment dict entry."""
        if ev is None:
            return None
        v = ev.get("value_numeric")
        return float(v) if v is not None else None

    def _text(ev: dict[str, str | float | None] | None) -> str | None:
        """Extract text value from an enrichment dict entry."""
        if ev is None:
            return None
        v = ev.get("value_text")
        return str(v) if v else None

    for deal in deal_responses:
        if not deal.property_id:
            continue
        fields = lookup.get(deal.property_id, {})

        n = _num(fields.get("TOTAL_UNITS"))
        if n is not None:
            deal.total_units = int(n)

        n = _num(fields.get("AVERAGE_UNIT_SF"))
        if n is not None:
            deal.avg_unit_sf = n

        t = _text(fields.get("CURRENT_OWNER"))
        if t:
            deal.current_owner = t

        n = _num(fields.get("LAST_SALE_PRICE_PER_UNIT"))
        if n is not None:
            deal.last_sale_price_per_unit = n

        t = _text(fields.get("LAST_SALE_DATE"))
        if t:
            deal.last_sale_date = t

        n = _num(fields.get("T12_RETURN_ON_COST"))
        if n is not None:
            deal.t12_return_on_cost = n

        n = _num(fields.get("LP_RETURNS_IRR"))
        if n is not None:
            deal.lp_irr = n

        n = _num(fields.get("LP_RETURNS_MOIC"))
        if n is not None:
            deal.lp_moic = n

        n = _num(fields.get("LEVERED_RETURNS_IRR"))
        if n is not None:
            deal.levered_irr = n

        n = _num(fields.get("LEVERED_RETURNS_MOIC"))
        if n is not None:
            deal.levered_moic = n

        t = _text(fields.get("PROPERTY_CITY"))
        if t:
            deal.property_city = t

        t = _text(fields.get("SUBMARKET"))
        if t:
            deal.submarket = t

        n = _num(fields.get("YEAR_BUILT"))
        if n is not None:
            deal.year_built = int(n)

        n = _num(fields.get("YEAR_RENOVATED"))
        if n is not None:
            deal.year_renovated = int(n)

        n = _num(fields.get("VACANCY_LOSS_YEAR_1_RATE"))
        if n is not None:
            deal.vacancy_rate = n

        n = _num(fields.get("BAD_DEBTS_YEAR_1_RATE"))
        if n is not None:
            deal.bad_debt_rate = n

        n = _num(fields.get("OTHER_LOSS_YEAR_1_RATE"))
        if n is not None:
            deal.other_loss_rate = n

        n = _num(fields.get("CONCESSIONS_YEAR_1_RATE"))
        if n is not None:
            deal.concessions_rate = n

        n = _num(fields.get("NET_OPERATING_INCOME_MARGIN"))
        if n is not None:
            deal.noi_margin = n

        n = _num(fields.get("PURCHASE_PRICE"))
        if n is not None:
            deal.purchase_price_extracted = n

        n = _num(fields.get("TOTAL_ACQUISITION_BUDGET"))
        if n is not None:
            deal.total_acquisition_budget = n

        n = _num(fields.get("BASIS_UNIT_AT_CLOSE"))
        if n is not None and n > 0:
            deal.basis_per_unit = n
        elif deal.total_units and deal.total_units > 0:
            # Calculate basis/unit from total acquisition budget / units
            budget = deal.total_acquisition_budget or deal.purchase_price_extracted
            if budget and budget > 0:
                deal.basis_per_unit = budget / deal.total_units

        n = _num(fields.get("T12_RETURN_ON_PP"))
        if n is not None and n > 0:
            deal.t12_cap_on_pp = n

        n = _num(fields.get("T3_RETURN_ON_PP"))
        if n is not None and n > 0:
            deal.t3_cap_on_pp = n

        # Cap Rate on Total Cost: use T12_RETURN_ON_COST (going-in, not exit)
        n = _num(fields.get("T12_RETURN_ON_COST"))
        if n is not None and n > 0:
            deal.total_cost_cap_t12 = n

        # T3 Cap Rate on Total Cost: cell G27 on Assumptions (Summary)
        n = _num(fields.get("T3_RETURN_ON_COST"))
        if n is not None and n > 0:
            deal.total_cost_cap_t3 = n

        n = _num(fields.get("LOAN_AMOUNT"))
        if n is not None:
            deal.loan_amount = n

        n = _num(fields.get("EQUITY_LP_CAPITAL"))
        if n is not None:
            deal.lp_equity = n

        n = _num(fields.get("EXIT_PERIOD_MONTHS"))
        if n is not None:
            deal.exit_months = n

        n = _num(fields.get("EXIT_CAP_RATE"))
        if n is not None:
            deal.exit_cap_rate = n

        n = _num(fields.get("UNLEVERED_RETURNS_IRR"))
        if n is not None:
            deal.unlevered_irr = n

        n = _num(fields.get("UNLEVERED_RETURNS_MOIC"))
        if n is not None:
            deal.unlevered_moic = n

        n = _num(fields.get("PROPERTY_LATITUDE"))
        if n is not None:
            deal.latitude = n

        n = _num(fields.get("PROPERTY_LONGITUDE"))
        if n is not None:
            deal.longitude = n

        # Equity commitment: use LP capital from extraction
        n = _num(fields.get("EQUITY_LP_CAPITAL"))
        if n is not None:
            deal.total_equity_commitment = n
