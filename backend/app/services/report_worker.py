"""
Background worker for processing queued report generation.

Polls the queued_reports table for pending reports every 30 seconds,
generates the report (PDF or Excel), and updates the status.

Integration with app lifecycle (main.py lifespan):
    report_worker = get_report_worker()
    await report_worker.start()
    yield
    await report_worker.stop()
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.report_template import (
    QueuedReport,
    ReportFormat,
    ReportStatus,
    ReportTemplate,
)

# Output directory for generated reports
REPORTS_OUTPUT_DIR = Path("generated_reports")

# Poll interval in seconds
POLL_INTERVAL = 30


class ReportWorker:
    """Background worker that processes the queued_reports table."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the background worker loop."""
        if self._running:
            logger.warning("Report worker already running")
            return

        # Ensure output directory exists
        REPORTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        self._running = True
        self._task = asyncio.create_task(self._loop(), name="report-worker")
        logger.info(
            "Report worker started",
            poll_interval=POLL_INTERVAL,
            output_dir=str(REPORTS_OUTPUT_DIR),
        )

    async def stop(self) -> None:
        """Stop the background worker loop gracefully."""
        if not self._running:
            return

        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        logger.info("Report worker stopped")

    async def _loop(self) -> None:
        """Main polling loop — checks for pending reports every POLL_INTERVAL seconds."""
        while self._running:
            correlation_id = f"report-poll-{uuid.uuid4().hex[:8]}"
            try:
                with logger.contextualize(correlation_id=correlation_id):
                    await self._process_pending()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Report worker encountered an error in poll loop")

            try:
                await asyncio.sleep(POLL_INTERVAL)
            except asyncio.CancelledError:
                break

    async def _process_pending(self) -> None:
        """Find and process all pending reports."""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(QueuedReport)
                    .where(QueuedReport.status == ReportStatus.PENDING)
                    .order_by(QueuedReport.requested_at.asc())
                    .limit(10)
                )
                pending = list(result.scalars().all())

                if not pending:
                    return

                logger.info(f"Report worker found {len(pending)} pending report(s)")

                for report in pending:
                    await self._process_one(db, report)
            except Exception:
                logger.exception("Error querying pending reports")
                await db.rollback()

    async def _process_one(self, db: AsyncSession, report: QueuedReport) -> None:
        """Process a single queued report: generate output file and update status."""
        report_id = report.id
        report_name = report.name

        try:
            # Mark as generating
            report.status = ReportStatus.GENERATING  # type: ignore[assignment]
            report.progress = 10
            db.add(report)
            await db.commit()
            await db.refresh(report)

            logger.info(
                f"Generating report: {report_name} (ID: {report_id}, format: {report.format})"
            )

            # Load the associated template
            template_result = await db.execute(
                select(ReportTemplate).where(ReportTemplate.id == report.template_id)
            )
            template = template_result.scalar_one_or_none()
            template_name = template.name if template else "Unknown"
            template_category = template.category if template else "custom"
            template_sections = template.sections if template else []

            # Update progress
            report.progress = 30
            db.add(report)
            await db.commit()

            # Generate the report content
            buffer = await self._generate_content(
                report_format=report.format,
                report_name=report_name,
                template_name=template_name,
                template_category=template_category,
                template_sections=template_sections,
                db=db,
            )

            report.progress = 80
            db.add(report)
            await db.commit()

            # Write output file
            ext = "pdf" if report.format == ReportFormat.PDF else "xlsx"
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            safe_name = (
                "".join(c if c.isalnum() or c in "-_ " else "" for c in report_name)
                .strip()
                .replace(" ", "_")
            )
            filename = f"{safe_name}_{report_id}_{timestamp}.{ext}"
            output_path = REPORTS_OUTPUT_DIR / filename

            content_bytes = buffer.getvalue()
            output_path.write_bytes(content_bytes)

            file_size = _format_file_size(len(content_bytes))
            download_url = f"/api/v1/reporting/downloads/{filename}"

            # Mark as completed
            report.status = ReportStatus.COMPLETED  # type: ignore[assignment]
            report.progress = 100
            report.completed_at = datetime.now(UTC)
            report.download_url = download_url
            report.file_size = file_size
            db.add(report)
            await db.commit()

            logger.info(
                f"Report completed: {report_name} (ID: {report_id}, "
                f"size: {file_size}, path: {output_path})"
            )

        except Exception as e:
            logger.exception(
                f"Report generation failed: {report_name} (ID: {report_id})"
            )

            # Mark as failed — use a fresh query to avoid stale state
            try:
                await db.rollback()
                result = await db.execute(
                    select(QueuedReport).where(QueuedReport.id == report_id)
                )
                failed_report = result.scalar_one_or_none()
                if failed_report:
                    failed_report.status = ReportStatus.FAILED  # type: ignore[assignment]
                    failed_report.progress = 0
                    failed_report.error = str(e)[:1000]
                    db.add(failed_report)
                    await db.commit()
            except Exception:
                logger.exception(f"Failed to mark report {report_id} as failed")
                await db.rollback()

    async def _generate_content(
        self,
        *,
        report_format: str,
        report_name: str,
        template_name: str,
        template_category: str,
        template_sections: list[str],
        db: AsyncSession,
    ) -> BytesIO:
        """
        Generate report content using the existing PDF/Excel services.

        Delegates to PDFReportService or ExcelExportService based on the
        requested format. Falls back to a simple placeholder if the
        required libraries are unavailable.
        """
        if report_format == ReportFormat.PDF:
            return await self._generate_pdf(
                report_name=report_name,
                template_name=template_name,
                template_category=template_category,
                template_sections=template_sections,
                db=db,
            )
        else:
            # Excel (and PPTX falls back to Excel for now)
            return await self._generate_excel(
                report_name=report_name,
                template_name=template_name,
                template_category=template_category,
                template_sections=template_sections,
                db=db,
            )

    async def _generate_pdf(
        self,
        *,
        report_name: str,
        template_name: str,
        template_category: str,
        template_sections: list[str],
        db: AsyncSession,
    ) -> BytesIO:
        """Generate a PDF report using the template-specific renderers.

        Dispatches on the template category (and template name for financial
        reports) to route to one of the five branded templates in
        :mod:`app.services.report_templates`. Falls back to the portfolio
        overview renderer for unknown categories, and to the legacy
        PDFReportService if any renderer raises.
        """
        from app.services import report_data, report_templates

        name_lower = (template_name or "").lower()
        category_lower = (template_category or "").lower()

        try:
            # Financial reports: branch on name contents
            if category_lower == "financial":
                if "investor" in name_lower or "distribution" in name_lower:
                    data = await report_data.gather_investor_distribution_data(db)
                    return report_templates.render_investor_distribution(data)
                # Default financial -> property performance
                prop_data = await report_data.gather_property_performance_data(db)
                return report_templates.render_property_performance(prop_data)

            if category_lower == "executive":
                deal_data = await report_data.gather_deal_pipeline_data(db)
                return report_templates.render_deal_pipeline(deal_data)

            if category_lower == "market":
                market_data = await report_data.gather_market_analysis_data(db)
                return report_templates.render_market_analysis(market_data)

            # portfolio / custom / fallback
            portfolio_data = await report_data.gather_portfolio_overview_data(db)
            return report_templates.render_portfolio_overview(portfolio_data)

        except Exception:
            # If template renderer fails, fall back to the legacy portfolio
            # dump so the job doesn't die outright. The error is still logged
            # by the renderer.
            logger.exception(
                "Template renderer failed, falling back to legacy portfolio report",
                template_name=template_name,
                template_category=template_category,
            )
            from app.services.pdf_service import get_pdf_service

            pdf_service = get_pdf_service()
            metrics, analytics, properties, deals = await _gather_portfolio_data(db)
            return pdf_service.generate_portfolio_report(
                metrics, analytics, properties, deals
            )

    async def _generate_excel(
        self,
        *,
        report_name: str,
        template_name: str,
        template_category: str,
        template_sections: list[str],
        db: AsyncSession,
    ) -> BytesIO:
        """Generate an Excel report using the existing export service."""
        from app.services.export_service import get_excel_service

        excel_service = get_excel_service()

        # Gather analytics data and generate the analytics report
        metrics, analytics, pipeline = await _gather_analytics_data(db)
        return excel_service.export_analytics_report(metrics, analytics, pipeline)


async def _gather_portfolio_data(
    db: AsyncSession,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Gather data needed for a portfolio-style report."""
    from sqlalchemy import func as sa_func

    from app.crud import deal as deal_crud
    from app.crud import property as property_crud
    from app.models import Deal, DealStage, Property

    analytics_summary = await property_crud.get_analytics_summary(db)

    value_result = await db.execute(select(sa_func.sum(Property.purchase_price)))
    total_value = value_result.scalar()

    deals_closed = await deal_crud.count_filtered(db, stage="closed")
    deals_realized = await deal_crud.count_filtered(db, stage="realized")

    active_stages = ["initial_review", "active_review", "under_contract"]
    deals_in_pipeline = 0
    for stg in active_stages:
        deals_in_pipeline += await deal_crud.count_filtered(db, stage=stg)

    capital_result = await db.execute(
        select(sa_func.sum(Deal.final_price)).where(
            Deal.stage.in_([DealStage.CLOSED, DealStage.REALIZED]),
            Deal.is_deleted.is_(False),
        )
    )
    capital_deployed = capital_result.scalar()

    dashboard_metrics: dict[str, Any] = {
        "portfolio_summary": {
            "total_properties": analytics_summary["total_properties"],
            "total_units": analytics_summary["total_units"] or 0,
            "total_sf": analytics_summary["total_sf"] or 0,
            "total_value": float(total_value) if total_value else 0,
            "avg_occupancy": (
                round(analytics_summary["avg_occupancy"], 2)
                if analytics_summary["avg_occupancy"]
                else None
            ),
            "avg_cap_rate": (
                round(analytics_summary["avg_cap_rate"], 2)
                if analytics_summary["avg_cap_rate"]
                else None
            ),
        },
        "kpis": {
            "ytd_noi_growth": None,
            "ytd_rent_growth": None,
            "deals_in_pipeline": deals_in_pipeline,
            "deals_closed_ytd": deals_closed + deals_realized,
            "capital_deployed_ytd": float(capital_deployed) if capital_deployed else 0,
        },
    }

    portfolio_analytics: dict[str, Any] = {
        "time_period": "ytd",
        "performance": {
            "total_return": None,
            "income_return": None,
            "appreciation_return": None,
            "benchmark_return": None,
            "alpha": None,
        },
    }

    # Properties data
    all_properties = await property_crud.get_multi_filtered(db, limit=1000)
    properties_data = [
        {
            "id": p.id,
            "name": p.name,
            "property_type": p.property_type,
            "city": p.city,
            "state": p.state,
            "total_units": p.total_units,
            "total_sf": p.total_sf,
        }
        for p in all_properties
    ]

    # Deals data
    all_deals = await deal_crud.get_multi_filtered(db, limit=1000)
    deals_data = [
        {
            "id": d.id,
            "name": d.name,
            "deal_type": d.deal_type,
            "stage": d.stage.value if hasattr(d.stage, "value") else str(d.stage),
            "asking_price": float(d.asking_price) if d.asking_price else None,
            "priority": d.priority,
        }
        for d in all_deals
    ]

    return dashboard_metrics, portfolio_analytics, properties_data, deals_data


async def _gather_analytics_data(
    db: AsyncSession,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Gather data needed for an analytics-style Excel report."""
    from sqlalchemy import func as sa_func

    from app.crud import deal as deal_crud
    from app.crud import property as property_crud
    from app.models import Deal, DealStage, Property

    analytics_summary = await property_crud.get_analytics_summary(db)

    value_result = await db.execute(select(sa_func.sum(Property.purchase_price)))
    total_value = value_result.scalar()

    deals_closed = await deal_crud.count_filtered(db, stage="closed")
    deals_realized = await deal_crud.count_filtered(db, stage="realized")

    active_stages = ["initial_review", "active_review", "under_contract"]
    deals_in_pipeline = 0
    for stg in active_stages:
        deals_in_pipeline += await deal_crud.count_filtered(db, stage=stg)

    capital_result = await db.execute(
        select(sa_func.sum(Deal.final_price)).where(
            Deal.stage.in_([DealStage.CLOSED, DealStage.REALIZED]),
            Deal.is_deleted.is_(False),
        )
    )
    capital_deployed = capital_result.scalar()

    dashboard_metrics: dict[str, Any] = {
        "portfolio_summary": {
            "total_properties": analytics_summary["total_properties"],
            "total_units": analytics_summary["total_units"] or 0,
            "total_sf": analytics_summary["total_sf"] or 0,
            "total_value": float(total_value) if total_value else 0,
            "avg_occupancy": (
                round(analytics_summary["avg_occupancy"], 2)
                if analytics_summary["avg_occupancy"]
                else None
            ),
            "avg_cap_rate": (
                round(analytics_summary["avg_cap_rate"], 2)
                if analytics_summary["avg_cap_rate"]
                else None
            ),
        },
        "kpis": {
            "ytd_noi_growth": None,
            "ytd_rent_growth": None,
            "deals_in_pipeline": deals_in_pipeline,
            "deals_closed_ytd": deals_closed + deals_realized,
            "capital_deployed_ytd": float(capital_deployed) if capital_deployed else 0,
        },
    }

    portfolio_analytics: dict[str, Any] = {
        "time_period": "ytd",
        "performance": {
            "total_return": None,
            "income_return": None,
            "appreciation_return": None,
            "benchmark_return": None,
            "alpha": None,
        },
    }

    # Build deal pipeline
    stage_counts: dict[str, int] = {}
    for stage_enum in DealStage:
        stage_counts[stage_enum.value] = await deal_crud.count_filtered(
            db, stage=stage_enum.value
        )

    funnel_total = sum(stage_counts.values())

    def _rate(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator * 100, 1) if denominator > 0 else None

    deal_pipeline: dict[str, Any] = {
        "funnel": stage_counts,
        "conversion_rates": {
            "review_to_active": _rate(
                stage_counts.get("active_review", 0),
                stage_counts.get("initial_review", 0),
            ),
            "active_to_contract": _rate(
                stage_counts.get("under_contract", 0),
                stage_counts.get("active_review", 0),
            ),
            "contract_to_close": _rate(
                stage_counts.get("closed", 0),
                stage_counts.get("under_contract", 0),
            ),
            "overall": _rate(
                stage_counts.get("closed", 0) + stage_counts.get("realized", 0),
                funnel_total,
            ),
        },
    }

    return dashboard_metrics, portfolio_analytics, deal_pipeline


def _format_file_size(size_bytes: int) -> str:
    """Format byte count into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# Singleton
_report_worker: ReportWorker | None = None


def get_report_worker() -> ReportWorker:
    """Get or create the singleton report worker."""
    global _report_worker
    if _report_worker is None:
        _report_worker = ReportWorker()
    return _report_worker
