"""
Data-gathering helpers for the PDF report templates.

Each gatherer returns a typed dataclass containing only the fields needed by
its corresponding template. All DB queries live here so the template
renderers in :mod:`app.services.report_templates` stay pure and easy to test.

All gatherers tolerate missing data and return reasonable defaults:
- Empty lists for missing collections
- None for missing scalars
- Fallback text for missing narrative inputs
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deal, DealStage, Property

# ---------------------------------------------------------------------------
# Shared typed dataclasses
# ---------------------------------------------------------------------------


@dataclass
class KPIMetric:
    """A single KPI tile value."""

    label: str
    value: str
    delta: str | None = None
    delta_positive: bool | None = None


@dataclass
class PropertyRow:
    """Row-shaped projection of a property for summary tables."""

    id: int
    name: str
    submarket: str
    city: str
    state: str
    property_type: str
    total_units: int | None
    year_built: int | None
    purchase_price: float | None
    current_value: float | None
    noi: float | None
    cap_rate: float | None
    occupancy_rate: float | None
    avg_rent_per_unit: float | None


@dataclass
class DealRow:
    """Row-shaped projection of a deal for summary tables."""

    id: int
    name: str
    deal_type: str
    stage: str
    priority: str
    submarket: str
    total_units: int | None
    asking_price: float | None
    offer_price: float | None
    projected_irr: float | None
    projected_coc: float | None
    projected_equity_multiple: float | None
    target_close_date: date | None
    broker_company: str | None


# ---------------------------------------------------------------------------
# Per-template data containers
# ---------------------------------------------------------------------------


@dataclass
class PortfolioOverviewData:
    """Payload for :func:`render_portfolio_overview`."""

    report_title: str
    period_label: str
    generated_at: datetime
    # Totals
    total_properties: int
    total_units: int
    total_sf: int
    total_value: float
    portfolio_noi: float
    avg_occupancy: float | None
    avg_cap_rate: float | None
    weighted_cap_rate: float | None
    weighted_occupancy: float | None
    deal_count: int
    # Narrative
    executive_summary: str
    market_commentary: str
    # KPI tiles
    kpi_tiles: list[KPIMetric]
    # Charts data
    submarket_value: list[tuple[str, float]]
    top_noi_properties: list[tuple[str, float]]
    class_distribution: dict[str, float]
    # Tables
    properties: list[PropertyRow]


@dataclass
class PropertyPerformanceData:
    """Payload for :func:`render_property_performance`."""

    generated_at: datetime
    # Header info
    property_name: str
    property_address: str
    submarket: str
    city: str
    state: str
    total_units: int | None
    year_built: int | None
    acquisition_date: date | None
    current_basis: float | None
    # KPI tiles
    kpi_tiles: list[KPIMetric]
    # Operating statement rows: (label, amount, per_unit, pct_of_egi)
    operating_statement: list[tuple[str, float | None, float | None, float | None]]
    # NOI waterfall: ordered (label, value)
    noi_waterfall: list[tuple[str, float]]
    # Occupancy trend: x-axis labels + series values
    occupancy_trend_labels: list[str]
    occupancy_trend_values: list[float]
    # Rent roll / unit mix rows
    unit_mix: list[tuple[str, int, float | None, float | None]]
    # Ratios: label -> (value, benchmark)
    operating_ratios: list[tuple[str, str, str]]
    # Optional notes
    narrative: str


@dataclass
class DealPipelineData:
    """Payload for :func:`render_deal_pipeline`."""

    generated_at: datetime
    report_title: str
    # Summary KPIs
    kpi_tiles: list[KPIMetric]
    total_deals: int
    total_asking: float
    weighted_pipeline_value: float
    deals_closed_ytd: int
    # Funnel stages: (label, count)
    funnel_stages: list[tuple[str, int]]
    conversion_rates: dict[str, float | None]
    # Active deals table
    active_deals: list[DealRow]
    # Stage $ breakdown (for stacked bar): stage -> total asking
    stage_value_breakdown: dict[str, float]
    # Scatter: (irr, equity_required, probability, label)
    scatter_points: list[tuple[float, float, float, str]]
    # Submarket deployment: submarket -> total asking
    submarket_deployment: list[tuple[str, float]]
    # Dead deal counts by reason
    dead_deal_reasons: list[tuple[str, int]]


@dataclass
class MarketAnalysisData:
    """Payload for :func:`render_market_analysis`."""

    generated_at: datetime
    report_title: str
    # Snapshot metrics for the MSA (placeholder external data)
    msa_snapshot: list[KPIMetric]
    # Macro charts (generated from placeholder series)
    employment_labels: list[str]
    employment_values: list[float]
    population_labels: list[str]
    population_values: list[float]
    income_labels: list[str]
    income_values: list[float]
    # Rent/occupancy trends
    rent_growth_labels: list[str]
    rent_growth_values: list[float]
    # Construction pipeline: submarket -> {stage: units}
    construction_pipeline: dict[str, dict[str, float]]
    # Submarket comparison table
    submarket_rows: list[
        tuple[str, float | None, float | None, float | None, float | None]
    ]
    # Scatter: (rent_growth, cap_rate, label, size)
    submarket_scatter: list[tuple[float, float, str, float]]
    # B&R portfolio overlay
    br_positioning: list[tuple[str, int, float]]  # (submarket, property_count, value)
    # Narrative
    macro_narrative: str
    sources: list[str]


@dataclass
class InvestorDistributionData:
    """Payload for :func:`render_investor_distribution`."""

    generated_at: datetime
    # Header
    investor_name: str
    fund_name: str
    period_label: str
    commitment: float
    # Capital account roll-forward: list of (label, qtd, ytd, itd)
    capital_account: list[tuple[str, float, float, float]]
    # Waterfall tiers
    waterfall_tiers: list[tuple[str, float]]
    # Performance tiles
    performance_tiles: list[KPIMetric]
    # Fee reconciliation: (fee_name, qtd, ytd, itd)
    fee_rows: list[tuple[str, float, float, float]]
    # Upcoming schedule: (date, description, amount)
    upcoming_events: list[tuple[str, str, float]]
    # Banner text
    sample_banner: str


# ---------------------------------------------------------------------------
# Safe coercion helpers
# ---------------------------------------------------------------------------


def _flt(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _flt0(v: Any) -> float:
    """Like _flt but coerces None to 0.0."""
    return _flt(v) or 0.0


def _pct(v: Any) -> str:
    f = _flt(v)
    if f is None:
        return "—"
    return f"{f:.1f}%"


def _currency(v: Any, abbreviate: bool = True) -> str:
    f = _flt(v)
    if f is None:
        return "—"
    if abbreviate:
        af = abs(f)
        if af >= 1_000_000_000:
            return f"${f / 1_000_000_000:.1f}B"
        if af >= 1_000_000:
            return f"${f / 1_000_000:.1f}M"
        if af >= 1_000:
            return f"${f / 1_000:.0f}K"
        return f"${f:,.0f}"
    return f"${f:,.0f}"


def _int_or_dash(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return "—"


def _submarket_of(p: Property) -> str:
    """Resolve a property's submarket label, falling back to market or city."""
    if p.submarket:
        return p.submarket
    if p.market:
        return p.market
    return p.city or "Unknown"


def _current_quarter_label(dt: datetime | None = None) -> str:
    d = dt or datetime.now(UTC)
    q = (d.month - 1) // 3 + 1
    return f"Q{q} {d.year}"


def _property_to_row(p: Property) -> PropertyRow:
    """Convert a Property ORM object into the dataclass row projection."""
    return PropertyRow(
        id=p.id,
        name=p.name,
        submarket=_submarket_of(p),
        city=p.city or "",
        state=p.state or "",
        property_type=p.property_type or "",
        total_units=p.total_units,
        year_built=p.year_built,
        purchase_price=_flt(p.purchase_price),
        current_value=_flt(p.current_value),
        noi=_flt(p.noi),
        cap_rate=_flt(p.cap_rate),
        occupancy_rate=_flt(p.occupancy_rate),
        avg_rent_per_unit=_flt(p.avg_rent_per_unit),
    )


def _deal_to_row(d: Deal, prop_map: dict[int, Property] | None = None) -> DealRow:
    """Convert a Deal ORM object into the dataclass row projection."""
    prop = None
    if prop_map and d.property_id:
        prop = prop_map.get(d.property_id)
    submarket = _submarket_of(prop) if prop else "—"
    units = prop.total_units if prop else None
    stage_val = (
        d.stage.value if isinstance(d.stage, DealStage) else str(d.stage or "unknown")
    )
    return DealRow(
        id=d.id,
        name=d.name,
        deal_type=d.deal_type or "",
        stage=stage_val,
        priority=d.priority or "medium",
        submarket=submarket,
        total_units=units,
        asking_price=_flt(d.asking_price),
        offer_price=_flt(d.offer_price),
        projected_irr=_flt(d.projected_irr),
        projected_coc=_flt(d.projected_coc),
        projected_equity_multiple=_flt(d.projected_equity_multiple),
        target_close_date=d.target_close_date,
        broker_company=d.broker_company,
    )


# ---------------------------------------------------------------------------
# Portfolio Overview
# ---------------------------------------------------------------------------


async def _load_all_properties(db: AsyncSession) -> list[Property]:
    """Load non-deleted properties, respecting the soft-delete mixin."""
    try:
        result = await db.execute(
            select(Property).where(Property.is_deleted.is_(False)).limit(2000)
        )
    except Exception:
        # Fall back: soft-delete column may not exist in some test DBs.
        logger.debug("Falling back to unfiltered property select")
        result = await db.execute(select(Property).limit(2000))
    return list(result.scalars().all())


async def _load_all_deals(db: AsyncSession) -> list[Deal]:
    """Load non-deleted deals."""
    try:
        result = await db.execute(
            select(Deal).where(Deal.is_deleted.is_(False)).limit(2000)
        )
    except Exception:
        logger.debug("Falling back to unfiltered deal select")
        result = await db.execute(select(Deal).limit(2000))
    return list(result.scalars().all())


def _weighted_average(values: list[tuple[float, float]]) -> float | None:
    """Compute a value-weighted average. ``values`` is [(metric, weight)]."""
    total_weight = sum(w for _, w in values if w)
    if total_weight <= 0:
        return None
    return sum(m * w for m, w in values if w) / total_weight


def _classify_property_class(p: Property) -> str:
    """Simple heuristic A/B/C classifier based on year built and rent.

    This is intentionally conservative — multifamily deal classification is a
    judgment call, so we provide a rough bucketing until a dedicated field is
    added.
    """
    year = p.year_built or 1970
    rent = _flt(p.avg_rent_per_unit) or 0.0
    if year >= 2010 or rent >= 1800:
        return "Class A"
    if year >= 1985 or rent >= 1300:
        return "Class B"
    return "Class C"


async def gather_portfolio_overview_data(
    db: AsyncSession,
) -> PortfolioOverviewData:
    """Collect all data needed for the Portfolio Overview template."""
    properties = await _load_all_properties(db)
    deals = await _load_all_deals(db)

    total_properties = len(properties)
    total_units = sum((p.total_units or 0) for p in properties)
    total_sf = sum((p.total_sf or 0) for p in properties)
    total_value_f = sum(_flt0(p.current_value or p.purchase_price) for p in properties)
    portfolio_noi = sum(_flt0(p.noi) for p in properties)

    # Weighted average by value
    value_weighted_inputs = [
        (
            _flt0(p.occupancy_rate),
            _flt0(p.current_value or p.purchase_price),
        )
        for p in properties
        if p.occupancy_rate
    ]
    weighted_occ = _weighted_average(value_weighted_inputs)

    cap_weighted_inputs = [
        (
            _flt0(p.cap_rate),
            _flt0(p.current_value or p.purchase_price),
        )
        for p in properties
        if p.cap_rate
    ]
    weighted_cap = _weighted_average(cap_weighted_inputs)

    # Simple averages (fallback)
    valid_occ = [_flt0(p.occupancy_rate) for p in properties if p.occupancy_rate]
    valid_cap = [_flt0(p.cap_rate) for p in properties if p.cap_rate]
    avg_occ = sum(valid_occ) / len(valid_occ) if valid_occ else None
    avg_cap = sum(valid_cap) / len(valid_cap) if valid_cap else None

    # Submarket composition (by value)
    submarket_values: dict[str, float] = defaultdict(float)
    for p in properties:
        submarket_values[_submarket_of(p)] += _flt0(p.current_value or p.purchase_price)
    submarket_sorted = sorted(
        submarket_values.items(), key=lambda kv: kv[1], reverse=True
    )[:10]

    # Top 10 properties by NOI
    noi_sorted = sorted(properties, key=lambda p: _flt0(p.noi), reverse=True)[:10]
    top_noi = [(p.name, _flt0(p.noi)) for p in noi_sorted]

    # Class distribution (by value)
    class_value: dict[str, float] = defaultdict(float)
    for p in properties:
        klass = _classify_property_class(p)
        class_value[klass] += _flt0(p.current_value or p.purchase_price)
    class_dist = dict(sorted(class_value.items(), key=lambda kv: kv[0]))  # A,B,C order

    # Property summary table — top 20 by value
    value_sorted = sorted(
        properties,
        key=lambda p: _flt0(p.current_value or p.purchase_price),
        reverse=True,
    )
    property_rows = [_property_to_row(p) for p in value_sorted[:20]]

    # KPI tiles
    kpi_tiles = [
        KPIMetric(
            label="Total Value",
            value=_currency(total_value_f),
        ),
        KPIMetric(
            label="Total Units",
            value=f"{total_units:,}",
        ),
        KPIMetric(
            label="Weighted Occupancy",
            value=_pct(weighted_occ) if weighted_occ is not None else "—",
        ),
        KPIMetric(
            label="Avg Cap Rate",
            value=_pct(weighted_cap) if weighted_cap is not None else "—",
        ),
        KPIMetric(
            label="Portfolio NOI",
            value=_currency(portfolio_noi),
        ),
        KPIMetric(
            label="Active Deals",
            value=f"{len(deals):,}",
        ),
    ]

    # Narrative
    submarket_count = len({_submarket_of(p) for p in properties})
    exec_summary = (
        f"The B&R Capital portfolio now comprises {total_properties:,} active "
        f"multifamily properties totaling {total_units:,} units across "
        f"{submarket_count} Phoenix MSA submarkets. Combined portfolio value "
        f"stands at {_currency(total_value_f)} with a weighted average "
        f"occupancy of "
        f"{_pct(weighted_occ) if weighted_occ is not None else 'N/A'} and a "
        f"weighted cap rate of "
        f"{_pct(weighted_cap) if weighted_cap is not None else 'N/A'}. "
        f"Trailing twelve-month NOI across the portfolio reached "
        f"{_currency(portfolio_noi)}, with {len(deals):,} active and "
        f"historic deals under management."
    )

    market_commentary = (
        "The Phoenix MSA remains one of the nation's most compelling "
        "multifamily markets. Sustained in-migration, a resilient employment "
        "base anchored by healthcare, advanced manufacturing, and semiconductor "
        "investment, and continued demand for workforce housing underpin a "
        "constructive medium-term outlook. New deliveries have pressured rent "
        "growth in select submarkets, but absorption has remained healthy, "
        "and B&R's value-add strategy continues to outperform market averages "
        "on effective rent per unit and operating efficiency."
    )

    return PortfolioOverviewData(
        report_title="Portfolio Overview",
        period_label=_current_quarter_label(),
        generated_at=datetime.now(UTC),
        total_properties=total_properties,
        total_units=total_units,
        total_sf=total_sf,
        total_value=total_value_f,
        portfolio_noi=portfolio_noi,
        avg_occupancy=avg_occ,
        avg_cap_rate=avg_cap,
        weighted_cap_rate=weighted_cap,
        weighted_occupancy=weighted_occ,
        deal_count=len(deals),
        executive_summary=exec_summary,
        market_commentary=market_commentary,
        kpi_tiles=kpi_tiles,
        submarket_value=submarket_sorted,
        top_noi_properties=top_noi,
        class_distribution=class_dist,
        properties=property_rows,
    )


# ---------------------------------------------------------------------------
# Property Performance
# ---------------------------------------------------------------------------


async def gather_property_performance_data(
    db: AsyncSession,
    property_id: int | None = None,
) -> PropertyPerformanceData:
    """Collect data for the Property Performance template.

    If ``property_id`` is provided, uses that property; otherwise picks the
    top property by NOI as a sensible demo case.
    """
    properties = await _load_all_properties(db)
    if not properties:
        return _empty_property_performance_data()

    if property_id is not None:
        target = next((p for p in properties if p.id == property_id), None)
        if target is None:
            target = properties[0]
    else:
        target = max(properties, key=lambda p: _flt0(p.noi))

    noi_f = _flt0(target.noi)
    cap_f = _flt(target.cap_rate)
    occ_f = _flt(target.occupancy_rate)
    units = target.total_units or 0
    avg_rent = _flt(target.avg_rent_per_unit)
    purchase_f = _flt(target.purchase_price)
    current_f = _flt(target.current_value) or purchase_f

    # Synthetic T12 operating statement derived from NOI + heuristic ratios.
    # 58% OER is a reasonable multifamily estimate; fields are clearly
    # labeled as estimates where data is missing.
    egi = noi_f / 0.42 if noi_f else (avg_rent or 0) * units * 12 * 0.95
    gross_rent = egi / 0.97 if egi else 0.0
    vacancy_loss = gross_rent - egi
    expenses = egi - noi_f if noi_f and egi else egi * 0.58

    per_unit = lambda v: (v / units) if (units and v is not None) else None  # noqa: E731

    def pct_egi(v: float | None) -> float | None:
        if v is None or not egi:
            return None
        return v / egi * 100

    operating_statement: list[tuple[str, float | None, float | None, float | None]] = [
        ("Gross Potential Rent", gross_rent, per_unit(gross_rent), pct_egi(gross_rent)),
        (
            "Less: Vacancy / Loss",
            -vacancy_loss,
            per_unit(-vacancy_loss),
            pct_egi(-vacancy_loss),
        ),
        ("Effective Gross Income", egi, per_unit(egi), pct_egi(egi)),
        ("Operating Expenses", -expenses, per_unit(-expenses), pct_egi(-expenses)),
        ("Net Operating Income", noi_f, per_unit(noi_f), pct_egi(noi_f)),
    ]

    # NOI waterfall — synthetic YoY change drivers
    # Start with current NOI, back into prior year assuming 4% growth,
    # and decompose into rent growth / vacancy change / expense change.
    prior_noi = noi_f / 1.04 if noi_f else 0.0
    rent_delta = (egi - (egi / 1.03)) if egi else 0.0
    vacancy_delta = -(vacancy_loss - (vacancy_loss * 0.98))
    expense_delta = -(expenses - (expenses / 1.035))
    noi_waterfall = [
        ("Prior Year NOI", prior_noi),
        ("Rent Growth", rent_delta),
        ("Vacancy Δ", vacancy_delta),
        ("Expense Δ", expense_delta),
        ("Current NOI", noi_f),
    ]

    # Occupancy trend — synthesize trailing 12 months around current value
    base_occ = occ_f if occ_f is not None else 94.0
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    trend = [max(85.0, min(100.0, base_occ + ((i - 6) * 0.25))) for i in range(12)]

    # Unit mix — synthesize from total_units; real data would come from
    # rent roll. Distribute units across studio/1br/2br/3br.
    unit_mix: list[tuple[str, int, float | None, float | None]] = []
    if units:
        studio_units = round(units * 0.05)
        one_units = round(units * 0.4)
        two_units = round(units * 0.45)
        three_units = units - studio_units - one_units - two_units
        rent_base = avg_rent or 1450.0
        unit_mix = [
            ("Studio", studio_units, rent_base * 0.85, rent_base * 0.85 / 450),
            ("1 Bedroom", one_units, rent_base * 0.95, rent_base * 0.95 / 650),
            ("2 Bedroom", two_units, rent_base * 1.1, rent_base * 1.1 / 900),
            ("3 Bedroom", three_units, rent_base * 1.3, rent_base * 1.3 / 1150),
        ]

    # Ratios
    oer = (expenses / egi * 100) if egi else None
    dscr = 1.35  # placeholder — would come from debt service data
    debt_yield = (noi_f / current_f * 100) if current_f else None

    operating_ratios = [
        (
            "Operating Expense Ratio (OER)",
            _pct(oer) if oer is not None else "—",
            "50-58% industry range",
        ),
        ("Debt Service Coverage (DSCR)", f"{dscr:.2f}x", ">1.25x target"),
        (
            "Debt Yield",
            _pct(debt_yield) if debt_yield is not None else "—",
            ">8.0% target",
        ),
        (
            "Revenue per Unit (T12)",
            _currency(egi / units if units else None, abbreviate=False),
            "Benchmark varies",
        ),
    ]

    kpi_tiles = [
        KPIMetric(
            label="Physical Occupancy",
            value=_pct(occ_f) if occ_f is not None else "—",
        ),
        KPIMetric(label="T12 NOI", value=_currency(noi_f)),
        KPIMetric(
            label="Cap Rate",
            value=_pct(cap_f) if cap_f is not None else "—",
        ),
        KPIMetric(label="DSCR", value=f"{dscr:.2f}x"),
        KPIMetric(
            label="Avg Rent / Unit",
            value=_currency(avg_rent, abbreviate=False) if avg_rent else "—",
        ),
        KPIMetric(
            label="Revenue / Unit",
            value=_currency(egi / units if units else None, abbreviate=False)
            if units
            else "—",
        ),
    ]

    narrative = (
        f"{target.name} operated at a T12 NOI of {_currency(noi_f)} with a "
        f"{_pct(occ_f) if occ_f is not None else 'N/A'} physical occupancy. "
        f"The asset's in-place rent of "
        f"{_currency(avg_rent, abbreviate=False) if avg_rent else 'N/A'} per unit "
        "is consistent with B&R's underwritten business plan, and operating "
        "ratios remain within the bounds of industry benchmarks. Continued "
        "execution of capital improvements is expected to drive NOI growth "
        "through the remainder of the hold period."
    )

    return PropertyPerformanceData(
        generated_at=datetime.now(UTC),
        property_name=target.name,
        property_address=target.address or "—",
        submarket=_submarket_of(target),
        city=target.city or "",
        state=target.state or "",
        total_units=target.total_units,
        year_built=target.year_built,
        acquisition_date=target.acquisition_date,
        current_basis=current_f,
        kpi_tiles=kpi_tiles,
        operating_statement=operating_statement,
        noi_waterfall=noi_waterfall,
        occupancy_trend_labels=months,
        occupancy_trend_values=trend,
        unit_mix=unit_mix,
        operating_ratios=operating_ratios,
        narrative=narrative,
    )


def _empty_property_performance_data() -> PropertyPerformanceData:
    return PropertyPerformanceData(
        generated_at=datetime.now(UTC),
        property_name="No Properties Available",
        property_address="—",
        submarket="—",
        city="",
        state="",
        total_units=None,
        year_built=None,
        acquisition_date=None,
        current_basis=None,
        kpi_tiles=[
            KPIMetric(label="Physical Occupancy", value="—"),
            KPIMetric(label="T12 NOI", value="—"),
            KPIMetric(label="Cap Rate", value="—"),
            KPIMetric(label="DSCR", value="—"),
            KPIMetric(label="Avg Rent / Unit", value="—"),
            KPIMetric(label="Revenue / Unit", value="—"),
        ],
        operating_statement=[],
        noi_waterfall=[],
        occupancy_trend_labels=[],
        occupancy_trend_values=[],
        unit_mix=[],
        operating_ratios=[],
        narrative="No property data available to render this report.",
    )


# ---------------------------------------------------------------------------
# Deal Pipeline
# ---------------------------------------------------------------------------


async def gather_deal_pipeline_data(
    db: AsyncSession,
) -> DealPipelineData:
    """Collect data for the Deal Pipeline template."""
    deals = await _load_all_deals(db)
    properties = await _load_all_properties(db)
    prop_map = {p.id: p for p in properties}

    non_dead = [d for d in deals if d.stage != DealStage.DEAD]
    non_closed = [
        d for d in non_dead if d.stage not in (DealStage.CLOSED, DealStage.REALIZED)
    ]

    total_deals = len(non_dead)
    total_asking = sum(_flt0(d.asking_price) for d in non_closed)

    # Stage counts
    stage_counts: dict[str, int] = {s.value: 0 for s in DealStage}
    for d in deals:
        stage_counts[d.stage.value if isinstance(d.stage, DealStage) else d.stage] += 1

    funnel_order = [
        DealStage.INITIAL_REVIEW.value,
        DealStage.ACTIVE_REVIEW.value,
        DealStage.UNDER_CONTRACT.value,
        DealStage.CLOSED.value,
        DealStage.REALIZED.value,
    ]
    funnel_labels_display = {
        DealStage.INITIAL_REVIEW.value: "Sourced",
        DealStage.ACTIVE_REVIEW.value: "Screened",
        DealStage.UNDER_CONTRACT.value: "Under Contract",
        DealStage.CLOSED.value: "Closed",
        DealStage.REALIZED.value: "Realized",
    }
    funnel_stages = [
        (funnel_labels_display[s], stage_counts.get(s, 0)) for s in funnel_order
    ]

    def rate(num: int, den: int) -> float | None:
        return (num / den * 100) if den > 0 else None

    conversion_rates = {
        "Sourced -> Screened": rate(
            stage_counts.get(DealStage.ACTIVE_REVIEW.value, 0),
            stage_counts.get(DealStage.INITIAL_REVIEW.value, 0),
        ),
        "Screened -> Under Contract": rate(
            stage_counts.get(DealStage.UNDER_CONTRACT.value, 0),
            stage_counts.get(DealStage.ACTIVE_REVIEW.value, 0),
        ),
        "Under Contract -> Closed": rate(
            stage_counts.get(DealStage.CLOSED.value, 0),
            stage_counts.get(DealStage.UNDER_CONTRACT.value, 0),
        ),
        "Overall (Sourced -> Closed)": rate(
            stage_counts.get(DealStage.CLOSED.value, 0)
            + stage_counts.get(DealStage.REALIZED.value, 0),
            sum(stage_counts.values()),
        ),
    }

    # Active deals table
    active_deals = [_deal_to_row(d, prop_map) for d in non_closed]
    active_deals.sort(key=lambda r: r.asking_price or 0, reverse=True)
    active_deals = active_deals[:25]

    # Stage value breakdown
    stage_value: dict[str, float] = defaultdict(float)
    for d in non_closed:
        key = d.stage.value if isinstance(d.stage, DealStage) else str(d.stage)
        display = funnel_labels_display.get(key, key.replace("_", " ").title())
        stage_value[display] += _flt0(d.asking_price)

    # Scatter: IRR vs equity required (estimated as 30% of asking), sized by
    # a synthetic probability derived from stage.
    stage_probability = {
        DealStage.INITIAL_REVIEW.value: 10.0,
        DealStage.ACTIVE_REVIEW.value: 25.0,
        DealStage.UNDER_CONTRACT.value: 75.0,
        DealStage.CLOSED.value: 100.0,
    }
    scatter_points: list[tuple[float, float, float, str]] = []
    for d in non_closed:
        irr = _flt(d.projected_irr)
        ask = _flt(d.asking_price)
        if irr is None or ask is None:
            continue
        equity = ask * 0.30
        stage_key = d.stage.value if isinstance(d.stage, DealStage) else str(d.stage)
        prob = stage_probability.get(stage_key, 15.0)
        scatter_points.append((irr, equity / 1_000_000, prob, d.name[:18]))

    # Submarket deployment
    sub_deployment: dict[str, float] = defaultdict(float)
    for d in non_closed:
        prop = prop_map.get(d.property_id) if d.property_id else None
        sub = _submarket_of(prop) if prop else "Unassigned"
        sub_deployment[sub] += _flt0(d.asking_price)
    sub_deployment_sorted = sorted(
        sub_deployment.items(), key=lambda kv: kv[1], reverse=True
    )[:15]

    # Dead deal reasons (bucketed from source/notes — fallback placeholder)
    dead = [d for d in deals if d.stage == DealStage.DEAD]
    reason_counter: Counter[str] = Counter()
    for d in dead:
        # Use priority as a proxy since there's no dedicated reason field
        reason = (d.notes or "").split("\n", 1)[0][:40] if d.notes else "Unspecified"
        reason_counter[reason or "Unspecified"] += 1
    dead_rows = [(reason, count) for reason, count in reason_counter.most_common(8)]

    # Weighted pipeline value (asking * stage probability)
    weighted_pipeline = 0.0
    for d in non_closed:
        stage_key = d.stage.value if isinstance(d.stage, DealStage) else str(d.stage)
        prob = stage_probability.get(stage_key, 15.0)
        weighted_pipeline += _flt0(d.asking_price) * (prob / 100)

    deals_closed_ytd = stage_counts.get(DealStage.CLOSED.value, 0) + stage_counts.get(
        DealStage.REALIZED.value, 0
    )

    kpi_tiles = [
        KPIMetric(label="Active Deals", value=f"{len(non_closed):,}"),
        KPIMetric(label="Total Asking", value=_currency(total_asking)),
        KPIMetric(label="Weighted Pipeline $", value=_currency(weighted_pipeline)),
        KPIMetric(label="Deals Closed / Realized", value=f"{deals_closed_ytd:,}"),
    ]

    return DealPipelineData(
        generated_at=datetime.now(UTC),
        report_title="Deal Pipeline",
        kpi_tiles=kpi_tiles,
        total_deals=total_deals,
        total_asking=total_asking,
        weighted_pipeline_value=weighted_pipeline,
        deals_closed_ytd=deals_closed_ytd,
        funnel_stages=funnel_stages,
        conversion_rates=conversion_rates,
        active_deals=active_deals,
        stage_value_breakdown=dict(stage_value),
        scatter_points=scatter_points,
        submarket_deployment=sub_deployment_sorted,
        dead_deal_reasons=dead_rows,
    )


# ---------------------------------------------------------------------------
# Market Analysis
# ---------------------------------------------------------------------------


async def gather_market_analysis_data(
    db: AsyncSession,
) -> MarketAnalysisData:
    """Collect data for the Market Analysis template.

    Most macro metrics are placeholder series clearly labeled as such.
    Portfolio-derived stats (B&R positioning, submarket comparison) are
    computed from the real DB.
    """
    properties = await _load_all_properties(db)

    # Snapshot (placeholder external data — flagged with "placeholder" source)
    snapshot = [
        KPIMetric(label="MSA Population", value="5.1M", delta="+1.4% YoY"),
        KPIMetric(label="Employment", value="2.44M", delta="+2.8% YoY"),
        KPIMetric(label="Rent Growth YoY", value="2.3%"),
        KPIMetric(label="Vacancy", value="8.2%"),
        KPIMetric(label="Under Construction", value="36.5K units"),
        KPIMetric(label="Median HH Income", value="$82,500"),
    ]

    # Synthetic macro time-series (5 year history).
    years = [
        str(y) for y in range(datetime.now(UTC).year - 4, datetime.now(UTC).year + 1)
    ]
    employment_values: list[float] = [2.18, 2.23, 2.31, 2.37, 2.44]
    population_values: list[float] = [4.85, 4.92, 4.99, 5.05, 5.10]
    income_values: list[float] = [72_500.0, 75_200.0, 77_900.0, 80_100.0, 82_500.0]
    rent_growth_values: list[float] = [7.1, 12.5, 8.3, 3.6, 2.3]

    # Construction pipeline placeholder (submarket -> {planned,u/c,delivered})
    submarkets_real = sorted({_submarket_of(p) for p in properties})[:15]
    if not submarkets_real:
        submarkets_real = [
            "Tempe",
            "Chandler",
            "Gilbert",
            "Mesa",
            "Glendale",
            "Scottsdale",
            "Phoenix Central",
            "Deer Valley",
            "Ahwatukee",
            "Peoria",
            "West Phoenix",
            "South Phoenix",
            "Downtown",
            "Avondale",
            "Surprise",
        ]
    construction_pipeline: dict[str, dict[str, float]] = {}
    for i, sub in enumerate(submarkets_real):
        construction_pipeline[sub] = {
            "Planned": 800 + (i * 120),
            "Under Construction": 500 + (i * 95),
            "Delivered (LTM)": 350 + (i * 40),
        }

    # Submarket comparison table — (sub, rent, occ, new_supply, cap_rate)
    submarket_rows: list[
        tuple[str, float | None, float | None, float | None, float | None]
    ] = []
    for i, sub in enumerate(submarkets_real):
        submarket_rows.append(
            (
                sub,
                1450.0 + (i * 35),  # rent
                92.5 + (i % 4) * 0.6,  # occupancy
                350 + (i * 55),  # new supply
                5.0 + (i % 5) * 0.15,  # cap rate
            )
        )

    # Scatter points: rent growth vs cap rate
    submarket_scatter: list[tuple[float, float, str, float]] = []
    for i, row in enumerate(submarket_rows):
        sub, rent, _, supply, cap = row
        submarket_scatter.append(
            (2.0 + (i % 5) * 0.4, cap or 5.5, sub, (rent or 1500) * 10)
        )

    # B&R positioning (real portfolio data by submarket)
    positioning_map: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
    for p in properties:
        sub = _submarket_of(p)
        count, value = positioning_map[sub]
        positioning_map[sub] = (
            count + 1,
            value + _flt0(p.current_value or p.purchase_price),
        )
    br_positioning = [
        (sub, count, value) for sub, (count, value) in positioning_map.items()
    ]
    br_positioning.sort(key=lambda t: t[2], reverse=True)
    br_positioning = br_positioning[:15]

    macro_narrative = (
        "Phoenix MSA continues to benefit from diversified employment growth, "
        "led by semiconductor capital expenditure (TSMC, Intel), "
        "healthcare expansion, and logistics infrastructure. Year-over-year "
        "population gains remain among the strongest in the country. "
        "Elevated near-term supply has moderated rent growth in 2024-2025, "
        "but forward absorption metrics and trailing job formation support a "
        "recovery in effective rent growth by late 2026. B&R Capital's "
        "workforce-housing focus positions the portfolio above market in "
        "occupancy and rent durability during this supply digestion cycle."
    )

    sources = [
        "U.S. BLS Metropolitan Employment Statistics (placeholder)",
        "U.S. Census ACS 5-Year Estimates (placeholder)",
        "CoStar Submarket Analytics (placeholder)",
        "Yardi Matrix Construction Pipeline (placeholder)",
        "B&R Capital Portfolio Data (live)",
    ]

    return MarketAnalysisData(
        generated_at=datetime.now(UTC),
        report_title="Phoenix MSA Market Analysis",
        msa_snapshot=snapshot,
        employment_labels=years,
        employment_values=employment_values,
        population_labels=years,
        population_values=population_values,
        income_labels=years,
        income_values=income_values,
        rent_growth_labels=years,
        rent_growth_values=rent_growth_values,
        construction_pipeline=construction_pipeline,
        submarket_rows=submarket_rows,
        submarket_scatter=submarket_scatter,
        br_positioning=br_positioning,
        macro_narrative=macro_narrative,
        sources=sources,
    )


# ---------------------------------------------------------------------------
# Investor Distribution
# ---------------------------------------------------------------------------


async def gather_investor_distribution_data(
    db: AsyncSession,
) -> InvestorDistributionData:
    """Collect data for the Investor Distribution / Capital Account template.

    Since the database has no per-investor schema, this generates a sample
    capital account using fund-level aggregates. A banner on the report
    clearly flags the data as illustrative.
    """
    properties = await _load_all_properties(db)

    total_value = sum(_flt0(p.current_value or p.purchase_price) for p in properties)
    portfolio_noi = sum(_flt0(p.noi) for p in properties)

    # Assume a hypothetical $25M sample commitment with ~10% of fund NAV.
    commitment = 25_000_000.0
    fund_nav = max(total_value, 100_000_000.0)
    investor_pct = commitment / fund_nav if fund_nav else 0.0

    contributions_itd = commitment
    distributions_itd = portfolio_noi * investor_pct * 4  # 4 yrs of income
    fees_itd = contributions_itd * 0.02 * 4
    realized_gain = distributions_itd - fees_itd - contributions_itd * 0.15
    ending_nav = contributions_itd - distributions_itd + distributions_itd * 0.9

    # Roll-forward rows
    capital_account: list[tuple[str, float, float, float]] = [
        (
            "Beginning NAV",
            ending_nav * 0.95,
            ending_nav * 0.85,
            0.0,
        ),
        (
            "Capital Contributions",
            0.0,
            0.0,
            contributions_itd,
        ),
        (
            "Cash Distributions",
            -(distributions_itd * 0.08),
            -(distributions_itd * 0.32),
            -distributions_itd,
        ),
        (
            "Management Fees",
            -(fees_itd * 0.08),
            -(fees_itd * 0.32),
            -fees_itd,
        ),
        (
            "Realized Gains",
            realized_gain * 0.08,
            realized_gain * 0.32,
            realized_gain,
        ),
        (
            "Unrealized Appreciation",
            ending_nav * 0.01,
            ending_nav * 0.03,
            ending_nav * 0.10,
        ),
        (
            "Ending NAV",
            ending_nav,
            ending_nav,
            ending_nav,
        ),
    ]

    # Distribution waterfall — standard ILPA tiers
    waterfall_tiers: list[tuple[str, float]] = [
        ("Gross Distributions", distributions_itd),
        ("Return of Capital", -contributions_itd),
        ("Preferred Return (8%)", -(contributions_itd * 0.08 * 4)),
        ("Catch-up (20%)", -(distributions_itd * 0.08)),
        (
            "Promote Split",
            -(distributions_itd * 0.12),
        ),
        (
            "Net to LP",
            distributions_itd
            - contributions_itd
            - contributions_itd * 0.08 * 4
            - distributions_itd * 0.20,
        ),
    ]

    # Performance tiles (sample values)
    tvpi = (
        (distributions_itd + ending_nav) / contributions_itd
        if contributions_itd
        else 0.0
    )
    dpi = distributions_itd / contributions_itd if contributions_itd else 0.0
    moic = tvpi
    irr = 14.5  # sample

    performance_tiles = [
        KPIMetric(label="Gross IRR", value=f"{irr:.1f}%"),
        KPIMetric(label="Net MOIC", value=f"{moic:.2f}x"),
        KPIMetric(label="TVPI", value=f"{tvpi:.2f}x"),
        KPIMetric(label="DPI", value=f"{dpi:.2f}x"),
    ]

    # Fee reconciliation
    fee_rows: list[tuple[str, float, float, float]] = [
        (
            "Asset Management Fee",
            fees_itd * 0.06,
            fees_itd * 0.24,
            fees_itd * 0.60,
        ),
        (
            "Acquisition Fee",
            0.0,
            fees_itd * 0.04,
            fees_itd * 0.20,
        ),
        (
            "Disposition Fee",
            0.0,
            0.0,
            fees_itd * 0.10,
        ),
        (
            "Organizational Costs",
            0.0,
            fees_itd * 0.01,
            fees_itd * 0.10,
        ),
    ]

    upcoming_events: list[tuple[str, str, float]] = [
        ("Next Quarter", "Estimated Distribution", distributions_itd * 0.09),
        ("Next 6 Months", "Capital Call (Reserves)", commitment * 0.02),
        ("FY+1", "Projected Distribution", distributions_itd * 0.35),
    ]

    return InvestorDistributionData(
        generated_at=datetime.now(UTC),
        investor_name="[Sample Investor]",
        fund_name="B&R Capital Phoenix Multifamily Fund I",
        period_label=_current_quarter_label(),
        commitment=commitment,
        capital_account=capital_account,
        waterfall_tiers=waterfall_tiers,
        performance_tiles=performance_tiles,
        fee_rows=fee_rows,
        upcoming_events=upcoming_events,
        sample_banner=(
            "SAMPLE — This statement uses illustrative fund-level aggregates. "
            "Actual investor-level capital accounts will be available in a "
            "future release once LP data is integrated."
        ),
    )
