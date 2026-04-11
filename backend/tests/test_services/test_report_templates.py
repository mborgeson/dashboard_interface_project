"""
Unit tests for the branded PDF report templates.

Covers the five renderer functions in :mod:`app.services.report_templates`
and their data gatherers in :mod:`app.services.report_data`. The tests
verify:

* each renderer produces a valid PDF (magic bytes ``%PDF``)
* each renderer tolerates empty / minimal data
* each renderer produces a non-trivial file (> 10 KB) when given live data
* the chart helper module renders all primary chart types without errors
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deal, DealStage, Property
from app.services import report_data, report_templates
from app.services.report_charts import (
    chart_to_image,
    create_donut,
    create_funnel,
    create_horizontal_bar,
    create_kpi_tile,
    create_line,
    create_scatter,
    create_stacked_bar,
    create_treemap,
    create_waterfall,
    setup_matplotlib_style,
)

PDF_MAGIC = b"%PDF"
MIN_PDF_SIZE = 10_000  # 10 KB minimum for a non-trivial document


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def seeded_db(db_session: AsyncSession) -> AsyncSession:
    """Insert a small realistic dataset (5 properties + 4 deals)."""
    submarkets = ["Tempe", "Chandler", "Gilbert", "Tempe", "Glendale"]
    for i in range(5):
        prop = Property(
            name=f"Phoenix Asset {i+1}",
            property_type="multifamily",
            address=f"{100 + i} Test Street",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
            market="Phoenix Metro",
            submarket=submarkets[i],
            year_built=2015 + i,
            total_units=200 + i * 25,
            total_sf=150_000 + i * 15_000,
            purchase_price=Decimal(str(40_000_000 + i * 5_000_000)),
            current_value=Decimal(str(45_000_000 + i * 5_000_000)),
            cap_rate=Decimal(f"{5.5 + i * 0.1:.3f}"),
            occupancy_rate=Decimal(f"{93.0 + i:.2f}"),
            noi=Decimal(str(2_500_000 + i * 300_000)),
            avg_rent_per_unit=Decimal(f"{1500 + i * 50}.00"),
            acquisition_date=date(2020 + (i % 3), 1 + (i % 12), 1),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            is_deleted=False,
        )
        db_session.add(prop)

    stages = [
        DealStage.INITIAL_REVIEW,
        DealStage.ACTIVE_REVIEW,
        DealStage.UNDER_CONTRACT,
        DealStage.CLOSED,
    ]
    for i, stg in enumerate(stages):
        deal = Deal(
            name=f"Deal #{i+1:04d}",
            deal_type="acquisition",
            stage=stg,
            stage_order=i,
            asking_price=Decimal(str(25_000_000 + i * 3_000_000)),
            offer_price=Decimal(str(24_000_000 + i * 3_000_000)),
            projected_irr=Decimal(f"{15.0 + i:.3f}"),
            projected_coc=Decimal(f"{7.5 + i * 0.5:.3f}"),
            projected_equity_multiple=Decimal(f"{1.9 + i * 0.1:.2f}"),
            hold_period_years=5,
            target_close_date=date(2026, 6 + i, 15),
            priority="high",
            competition_level="medium",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            is_deleted=False,
        )
        db_session.add(deal)

    await db_session.commit()
    return db_session


# ---------------------------------------------------------------------------
# Chart helper tests
# ---------------------------------------------------------------------------


class TestReportCharts:
    """Sanity checks for the chart helpers."""

    def test_setup_matplotlib_style_idempotent(self) -> None:
        setup_matplotlib_style()
        setup_matplotlib_style()  # safe to call twice

    def test_create_horizontal_bar(self) -> None:
        fig = create_horizontal_bar(
            ["Alpha", "Bravo", "Charlie"],
            [1_000_000, 2_500_000, 1_800_000],
            title="Bar Test",
        )
        img = chart_to_image(fig, 6, 4)
        assert img is not None

    def test_create_treemap(self) -> None:
        fig = create_treemap(
            ["A", "B", "C", "D"],
            [500, 300, 200, 100],
            title="Tree Test",
        )
        img = chart_to_image(fig, 6, 4)
        assert img is not None

    def test_create_donut(self) -> None:
        fig = create_donut(
            ["X", "Y", "Z"],
            [50_000_000, 30_000_000, 20_000_000],
            title="Donut Test",
        )
        img = chart_to_image(fig, 5, 4)
        assert img is not None

    def test_create_waterfall(self) -> None:
        fig = create_waterfall(
            ["Start", "+Rent", "-Vac", "+Fees", "End"],
            [1000, 200, -50, 30, 1180],
            title="Waterfall Test",
        )
        img = chart_to_image(fig, 6, 4)
        assert img is not None

    def test_create_funnel(self) -> None:
        fig = create_funnel(
            ["Sourced", "Screened", "LOI", "Closed"],
            [1000, 250, 80, 20],
            title="Funnel Test",
        )
        img = chart_to_image(fig, 6, 4)
        assert img is not None

    def test_create_line_multi_series(self) -> None:
        fig = create_line(
            x_values=["2021", "2022", "2023", "2024"],
            y_values_dict={
                "Portfolio": [100, 110, 125, 140],
                "Benchmark": [95, 104, 113, 122],
            },
            title="Line Test",
            y_label="Index",
        )
        img = chart_to_image(fig, 6, 4)
        assert img is not None

    def test_create_scatter(self) -> None:
        fig = create_scatter(
            x_values=[1, 2, 3, 4, 5],
            y_values=[5, 3, 4, 2, 6],
            sizes=[100, 200, 300, 250, 150],
            labels=["A", "B", "C", "D", "E"],
            title="Scatter",
            x_label="X",
            y_label="Y",
        )
        img = chart_to_image(fig, 6, 4)
        assert img is not None

    def test_create_stacked_bar(self) -> None:
        fig = create_stacked_bar(
            x_labels=["Sub1", "Sub2", "Sub3"],
            series={
                "Planned": [1000, 800, 1200],
                "UC": [500, 600, 400],
            },
            title="Stacked",
        )
        img = chart_to_image(fig, 6, 4)
        assert img is not None

    def test_create_kpi_tile(self) -> None:
        tile = create_kpi_tile(
            label="TOTAL VALUE",
            value="$3.5B",
            delta="+4.2%",
            delta_positive=True,
        )
        assert tile is not None


# ---------------------------------------------------------------------------
# Data-gatherer tests (seeded DB)
# ---------------------------------------------------------------------------


class TestReportDataGatherers:
    """Verify data gatherers against a seeded SQLite DB."""

    @pytest.mark.asyncio
    async def test_gather_portfolio_overview_data(
        self, seeded_db: AsyncSession
    ) -> None:
        data = await report_data.gather_portfolio_overview_data(seeded_db)
        assert data.total_properties == 5
        assert data.total_units > 0
        assert data.total_value > 0
        assert data.portfolio_noi > 0
        assert len(data.kpi_tiles) == 6
        assert len(data.properties) <= 20
        assert len(data.submarket_value) >= 1
        assert data.executive_summary
        assert data.market_commentary

    @pytest.mark.asyncio
    async def test_gather_property_performance_data(
        self, seeded_db: AsyncSession
    ) -> None:
        data = await report_data.gather_property_performance_data(seeded_db)
        assert data.property_name
        assert len(data.kpi_tiles) == 6
        assert len(data.operating_statement) > 0
        assert len(data.noi_waterfall) >= 3
        assert len(data.occupancy_trend_values) == 12
        assert len(data.unit_mix) > 0

    @pytest.mark.asyncio
    async def test_gather_deal_pipeline_data(
        self, seeded_db: AsyncSession
    ) -> None:
        data = await report_data.gather_deal_pipeline_data(seeded_db)
        assert data.total_deals > 0
        assert len(data.kpi_tiles) == 4
        assert len(data.funnel_stages) == 5
        assert len(data.conversion_rates) == 4
        # Some active deals (non-closed) should exist
        assert len(data.active_deals) > 0

    @pytest.mark.asyncio
    async def test_gather_market_analysis_data(
        self, seeded_db: AsyncSession
    ) -> None:
        data = await report_data.gather_market_analysis_data(seeded_db)
        assert len(data.msa_snapshot) == 6
        assert len(data.employment_values) > 0
        assert len(data.submarket_rows) > 0
        assert len(data.sources) > 0

    @pytest.mark.asyncio
    async def test_gather_investor_distribution_data(
        self, seeded_db: AsyncSession
    ) -> None:
        data = await report_data.gather_investor_distribution_data(seeded_db)
        assert data.commitment > 0
        assert len(data.capital_account) > 0
        assert len(data.waterfall_tiers) > 0
        assert len(data.performance_tiles) == 4
        assert "SAMPLE" in data.sample_banner


# ---------------------------------------------------------------------------
# Empty / minimal data tests
# ---------------------------------------------------------------------------


class TestEmptyDataSafety:
    """Each gatherer should run against an empty DB without raising."""

    @pytest.mark.asyncio
    async def test_portfolio_overview_empty(self, db_session: AsyncSession) -> None:
        data = await report_data.gather_portfolio_overview_data(db_session)
        assert data.total_properties == 0
        # Should still render
        buf = report_templates.render_portfolio_overview(data)
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC
        assert len(content) > 5_000  # still has cover + sections

    @pytest.mark.asyncio
    async def test_property_performance_empty(
        self, db_session: AsyncSession
    ) -> None:
        data = await report_data.gather_property_performance_data(db_session)
        buf = report_templates.render_property_performance(data)
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC

    @pytest.mark.asyncio
    async def test_deal_pipeline_empty(self, db_session: AsyncSession) -> None:
        data = await report_data.gather_deal_pipeline_data(db_session)
        buf = report_templates.render_deal_pipeline(data)
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC

    @pytest.mark.asyncio
    async def test_market_analysis_empty(
        self, db_session: AsyncSession
    ) -> None:
        data = await report_data.gather_market_analysis_data(db_session)
        buf = report_templates.render_market_analysis(data)
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC

    @pytest.mark.asyncio
    async def test_investor_distribution_empty(
        self, db_session: AsyncSession
    ) -> None:
        data = await report_data.gather_investor_distribution_data(db_session)
        buf = report_templates.render_investor_distribution(data)
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC


# ---------------------------------------------------------------------------
# End-to-end renderer tests (seeded DB)
# ---------------------------------------------------------------------------


class TestRendererOutputs:
    """Verify each renderer produces a valid, non-trivial PDF from live data."""

    @pytest.mark.asyncio
    async def test_portfolio_overview_pdf(self, seeded_db: AsyncSession) -> None:
        data = await report_data.gather_portfolio_overview_data(seeded_db)
        buf = report_templates.render_portfolio_overview(data)
        assert isinstance(buf, BytesIO)
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC
        assert len(content) > MIN_PDF_SIZE

    @pytest.mark.asyncio
    async def test_property_performance_pdf(
        self, seeded_db: AsyncSession
    ) -> None:
        data = await report_data.gather_property_performance_data(seeded_db)
        buf = report_templates.render_property_performance(data)
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC
        assert len(content) > MIN_PDF_SIZE

    @pytest.mark.asyncio
    async def test_deal_pipeline_pdf(self, seeded_db: AsyncSession) -> None:
        data = await report_data.gather_deal_pipeline_data(seeded_db)
        buf = report_templates.render_deal_pipeline(data)
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC
        assert len(content) > MIN_PDF_SIZE

    @pytest.mark.asyncio
    async def test_market_analysis_pdf(self, seeded_db: AsyncSession) -> None:
        data = await report_data.gather_market_analysis_data(seeded_db)
        buf = report_templates.render_market_analysis(data)
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC
        assert len(content) > MIN_PDF_SIZE

    @pytest.mark.asyncio
    async def test_investor_distribution_pdf(
        self, seeded_db: AsyncSession
    ) -> None:
        data = await report_data.gather_investor_distribution_data(seeded_db)
        buf = report_templates.render_investor_distribution(data)
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC
        assert len(content) > MIN_PDF_SIZE


# ---------------------------------------------------------------------------
# Worker dispatch test
# ---------------------------------------------------------------------------


class TestReportWorkerDispatch:
    """Exercise the category-based routing in report_worker._generate_pdf."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "category,name,min_size",
        [
            ("portfolio", "Portfolio Report", MIN_PDF_SIZE),
            ("executive", "Weekly Pipeline", MIN_PDF_SIZE),
            ("market", "Phoenix MSA", MIN_PDF_SIZE),
            ("financial", "Investor Capital Statement", MIN_PDF_SIZE),
            ("financial", "Property Performance Report", MIN_PDF_SIZE),
            ("custom", "Ad-hoc", MIN_PDF_SIZE),
        ],
    )
    async def test_dispatch_routes_by_category(
        self,
        seeded_db: AsyncSession,
        category: str,
        name: str,
        min_size: int,
    ) -> None:
        from app.services.report_worker import ReportWorker

        worker = ReportWorker()
        buf = await worker._generate_pdf(
            report_name="Test",
            template_name=name,
            template_category=category,
            template_sections=[],
            db=seeded_db,
        )
        content = buf.getvalue()
        assert content[:4] == PDF_MAGIC
        assert len(content) > min_size
