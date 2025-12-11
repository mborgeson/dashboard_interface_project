"""
PDF report generation service.

Provides functionality to generate professional PDF reports including:
- Property detail reports
- Deal summaries
- Portfolio analytics reports
- Executive dashboards
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Optional

from loguru import logger

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        Image,
        PageBreak,
        PageTemplate,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.graphics.shapes import Drawing, Line, Rect
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.piecharts import Pie

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed - PDF export will be limited")


class PDFReportService:
    """Service for generating professional PDF reports."""

    # B&R Capital branding colors - initialized when reportlab is available
    COLORS = {}
    STAGE_COLORS = {}

    def __init__(self):
        """Initialize the PDF report service."""
        self._styles = None
        if REPORTLAB_AVAILABLE:
            self._init_colors()
            self._init_styles()

    def _init_colors(self) -> None:
        """Initialize branding colors when reportlab is available."""
        from reportlab.lib import colors

        # B&R Capital branding colors
        self.COLORS = {
            "primary": colors.HexColor("#1E3A5F"),
            "secondary": colors.HexColor("#2E5090"),
            "accent": colors.HexColor("#4A90D9"),
            "success": colors.HexColor("#28A745"),
            "warning": colors.HexColor("#FFC107"),
            "danger": colors.HexColor("#DC3545"),
            "text": colors.HexColor("#333333"),
            "muted": colors.HexColor("#6C757D"),
            "light": colors.HexColor("#F8F9FA"),
            "white": colors.white,
        }

        # Stage colors for deal pipeline
        self.STAGE_COLORS = {
            "lead": colors.HexColor("#E3F2FD"),
            "initial_review": colors.HexColor("#BBDEFB"),
            "underwriting": colors.HexColor("#90CAF9"),
            "due_diligence": colors.HexColor("#64B5F6"),
            "loi_submitted": colors.HexColor("#42A5F5"),
            "under_contract": colors.HexColor("#2196F3"),
            "closed": colors.HexColor("#28A745"),
            "dead": colors.HexColor("#DC3545"),
        }

    def _init_styles(self) -> None:
        """Initialize paragraph styles."""
        self._styles = getSampleStyleSheet()

        # Add custom styles
        self._styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=self._styles["Title"],
                fontSize=24,
                textColor=self.COLORS["primary"],
                spaceAfter=30,
                alignment=TA_CENTER,
            )
        )

        self._styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self._styles["Heading1"],
                fontSize=16,
                textColor=self.COLORS["primary"],
                spaceBefore=20,
                spaceAfter=12,
                borderPadding=5,
            )
        )

        self._styles.add(
            ParagraphStyle(
                name="SubSectionHeader",
                parent=self._styles["Heading2"],
                fontSize=12,
                textColor=self.COLORS["secondary"],
                spaceBefore=15,
                spaceAfter=8,
            )
        )

        # Modify existing BodyText style (already exists in getSampleStyleSheet)
        body_style = self._styles["BodyText"]
        body_style.fontSize = 10
        body_style.textColor = self.COLORS["text"]
        body_style.spaceAfter = 6

        self._styles.add(
            ParagraphStyle(
                name="MetricValue",
                parent=self._styles["Normal"],
                fontSize=18,
                textColor=self.COLORS["primary"],
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        self._styles.add(
            ParagraphStyle(
                name="MetricLabel",
                parent=self._styles["Normal"],
                fontSize=9,
                textColor=self.COLORS["muted"],
                alignment=TA_CENTER,
            )
        )

        self._styles.add(
            ParagraphStyle(
                name="Footer",
                parent=self._styles["Normal"],
                fontSize=8,
                textColor=self.COLORS["muted"],
                alignment=TA_CENTER,
            )
        )

    def _create_header_footer(self, canvas, doc) -> None:
        """Add header and footer to each page."""
        canvas.saveState()

        # Header
        canvas.setFillColor(self.COLORS["primary"])
        canvas.rect(0, letter[1] - 50, letter[0], 50, fill=True, stroke=False)

        canvas.setFillColor(self.COLORS["white"])
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(30, letter[1] - 32, "B&R Capital")

        canvas.setFont("Helvetica", 10)
        canvas.drawRightString(
            letter[0] - 30, letter[1] - 32, datetime.now().strftime("%Y-%m-%d")
        )

        # Footer
        canvas.setFillColor(self.COLORS["muted"])
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(
            letter[0] / 2,
            30,
            f"Page {doc.page} | Confidential - B&R Capital Real Estate Analytics",
        )

        canvas.restoreState()

    def _create_table_style(self, header_color=None) -> TableStyle:
        """Create a standard table style."""
        if header_color is None:
            header_color = self.COLORS["primary"]

        return TableStyle(
            [
                # Header styling
                ("BACKGROUND", (0, 0), (-1, 0), header_color),
                ("TEXTCOLOR", (0, 0), (-1, 0), self.COLORS["white"]),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                # Body styling
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                # Grid
                ("GRID", (0, 0), (-1, -1), 0.5, self.COLORS["muted"]),
                # Alternating row colors
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [self.COLORS["white"], self.COLORS["light"]],
                ),
            ]
        )

    def _format_currency(self, value: float) -> str:
        """Format a number as currency."""
        if value >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        elif value >= 1_000:
            return f"${value / 1_000:.0f}K"
        else:
            return f"${value:,.2f}"

    def _format_percent(self, value: float) -> str:
        """Format a number as percentage."""
        if value > 1:
            return f"{value:.1f}%"
        else:
            return f"{value * 100:.1f}%"

    def generate_property_report(
        self,
        property_data: dict[str, Any],
        analytics: Optional[dict[str, Any]] = None,
    ) -> BytesIO:
        """
        Generate a detailed property report.

        Args:
            property_data: Property details
            analytics: Optional analytics data

        Returns:
            BytesIO buffer containing the PDF
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=70,
            bottomMargin=50,
            leftMargin=40,
            rightMargin=40,
        )

        elements = []

        # Title
        elements.append(
            Paragraph(
                f"Property Report: {property_data.get('name', 'Unknown')}",
                self._styles["ReportTitle"],
            )
        )
        elements.append(Spacer(1, 20))

        # Property Overview
        elements.append(Paragraph("Property Overview", self._styles["SectionHeader"]))

        overview_data = [
            ["Property Type", property_data.get("property_type", "N/A").title()],
            ["Address", property_data.get("address", "N/A")],
            [
                "City, State",
                f"{property_data.get('city', 'N/A')}, {property_data.get('state', 'N/A')}",
            ],
            ["Market", property_data.get("market", "N/A")],
            ["Year Built", str(property_data.get("year_built", "N/A"))],
        ]

        # Add units or SF based on property type
        if property_data.get("total_units"):
            overview_data.append(
                ["Total Units", str(property_data.get("total_units", 0))]
            )
        if property_data.get("total_sf"):
            overview_data.append(["Total SF", f"{property_data.get('total_sf', 0):,}"])

        overview_table = Table(overview_data, colWidths=[2 * inch, 4 * inch])
        overview_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, self.COLORS["light"]),
                ]
            )
        )
        elements.append(overview_table)
        elements.append(Spacer(1, 20))

        # Financial Metrics
        elements.append(Paragraph("Financial Metrics", self._styles["SectionHeader"]))

        financial_data = [
            ["Metric", "Value"],
            [
                "Occupancy Rate",
                self._format_percent(property_data.get("occupancy_rate", 0)),
            ],
            ["Cap Rate", self._format_percent(property_data.get("cap_rate", 0))],
            ["NOI", self._format_currency(property_data.get("noi", 0))],
        ]

        if property_data.get("avg_rent_per_unit"):
            financial_data.append(
                [
                    "Avg Rent/Unit",
                    self._format_currency(property_data.get("avg_rent_per_unit", 0)),
                ]
            )
        if property_data.get("avg_rent_per_sf"):
            financial_data.append(
                [
                    "Avg Rent/SF",
                    f"${property_data.get('avg_rent_per_sf', 0):.2f}",
                ]
            )

        financial_table = Table(financial_data, colWidths=[3 * inch, 3 * inch])
        financial_table.setStyle(self._create_table_style())
        elements.append(financial_table)

        # Analytics section if available
        if analytics:
            elements.append(Spacer(1, 30))
            elements.append(
                Paragraph("Performance Analytics", self._styles["SectionHeader"])
            )

            metrics = analytics.get("metrics", {})
            analytics_data = [
                ["Metric", "Value"],
                [
                    "YTD Rent Growth",
                    self._format_percent(metrics.get("ytd_rent_growth", 0)),
                ],
                [
                    "YTD NOI Growth",
                    self._format_percent(metrics.get("ytd_noi_growth", 0)),
                ],
                [
                    "Avg 12M Occupancy",
                    self._format_percent(metrics.get("avg_occupancy_12m", 0)),
                ],
                ["Rent vs Market", f"{metrics.get('rent_vs_market', 1):.0%}"],
            ]

            analytics_table = Table(analytics_data, colWidths=[3 * inch, 3 * inch])
            analytics_table.setStyle(self._create_table_style())
            elements.append(analytics_table)

        # Build PDF
        doc.build(
            elements,
            onFirstPage=self._create_header_footer,
            onLaterPages=self._create_header_footer,
        )

        buffer.seek(0)
        logger.info(f"Generated property report for: {property_data.get('name')}")
        return buffer

    def generate_deal_report(
        self,
        deal_data: dict[str, Any],
        property_data: Optional[dict[str, Any]] = None,
    ) -> BytesIO:
        """
        Generate a detailed deal report.

        Args:
            deal_data: Deal details
            property_data: Optional associated property data

        Returns:
            BytesIO buffer containing the PDF
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=70,
            bottomMargin=50,
            leftMargin=40,
            rightMargin=40,
        )

        elements = []

        # Title
        elements.append(
            Paragraph(
                f"Deal Report: {deal_data.get('name', 'Unknown')}",
                self._styles["ReportTitle"],
            )
        )
        elements.append(Spacer(1, 20))

        # Deal Status Badge
        stage = deal_data.get("stage", "unknown")
        stage_color = self.STAGE_COLORS.get(stage, self.COLORS["muted"])
        elements.append(
            Paragraph(
                f"<font color='white'><b> {stage.replace('_', ' ').upper()} </b></font>",
                ParagraphStyle(
                    "StatusBadge",
                    parent=self._styles["Normal"],
                    fontSize=10,
                    backColor=stage_color,
                    alignment=TA_CENTER,
                ),
            )
        )
        elements.append(Spacer(1, 20))

        # Deal Overview
        elements.append(Paragraph("Deal Overview", self._styles["SectionHeader"]))

        overview_data = [
            ["Deal Type", deal_data.get("deal_type", "N/A").title()],
            ["Priority", deal_data.get("priority", "N/A").title()],
            ["Source", deal_data.get("source", "N/A")],
            ["Broker", deal_data.get("broker_name", "N/A")],
            ["Hold Period", f"{deal_data.get('hold_period_years', 'N/A')} years"],
        ]

        overview_table = Table(overview_data, colWidths=[2 * inch, 4 * inch])
        overview_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, self.COLORS["light"]),
                ]
            )
        )
        elements.append(overview_table)
        elements.append(Spacer(1, 20))

        # Financial Terms
        elements.append(Paragraph("Financial Terms", self._styles["SectionHeader"]))

        financial_data = [
            ["Term", "Value"],
            ["Asking Price", self._format_currency(deal_data.get("asking_price", 0))],
        ]

        if deal_data.get("offer_price"):
            financial_data.append(
                ["Offer Price", self._format_currency(deal_data.get("offer_price", 0))]
            )

        if deal_data.get("projected_irr"):
            financial_data.append(
                [
                    "Projected IRR",
                    self._format_percent(deal_data.get("projected_irr", 0)),
                ]
            )

        if deal_data.get("projected_coc"):
            financial_data.append(
                [
                    "Projected Cash-on-Cash",
                    self._format_percent(deal_data.get("projected_coc", 0)),
                ]
            )

        if deal_data.get("projected_equity_multiple"):
            financial_data.append(
                [
                    "Equity Multiple",
                    f"{deal_data.get('projected_equity_multiple', 0):.2f}x",
                ]
            )

        financial_table = Table(financial_data, colWidths=[3 * inch, 3 * inch])
        financial_table.setStyle(self._create_table_style())
        elements.append(financial_table)

        # Associated Property if available
        if property_data:
            elements.append(Spacer(1, 30))
            elements.append(
                Paragraph("Associated Property", self._styles["SectionHeader"])
            )

            property_info = [
                ["Property Name", property_data.get("name", "N/A")],
                ["Type", property_data.get("property_type", "N/A").title()],
                [
                    "Location",
                    f"{property_data.get('city', 'N/A')}, {property_data.get('state', 'N/A')}",
                ],
                [
                    "Occupancy",
                    self._format_percent(property_data.get("occupancy_rate", 0)),
                ],
            ]

            property_table = Table(property_info, colWidths=[2 * inch, 4 * inch])
            property_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("LINEBELOW", (0, 0), (-1, -2), 0.5, self.COLORS["light"]),
                    ]
                )
            )
            elements.append(property_table)

        # Build PDF
        doc.build(
            elements,
            onFirstPage=self._create_header_footer,
            onLaterPages=self._create_header_footer,
        )

        buffer.seek(0)
        logger.info(f"Generated deal report for: {deal_data.get('name')}")
        return buffer

    def generate_portfolio_report(
        self,
        dashboard_metrics: dict[str, Any],
        portfolio_analytics: dict[str, Any],
        properties: list[dict[str, Any]],
        deals: list[dict[str, Any]],
    ) -> BytesIO:
        """
        Generate a comprehensive portfolio report.

        Args:
            dashboard_metrics: Dashboard summary metrics
            portfolio_analytics: Portfolio analytics data
            properties: List of properties
            deals: List of deals

        Returns:
            BytesIO buffer containing the PDF
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=70,
            bottomMargin=50,
            leftMargin=40,
            rightMargin=40,
        )

        elements = []

        # Title Page
        elements.append(Spacer(1, 100))
        elements.append(
            Paragraph(
                "Portfolio Report",
                self._styles["ReportTitle"],
            )
        )
        elements.append(
            Paragraph(
                f"Generated: {datetime.now().strftime('%B %d, %Y')}",
                ParagraphStyle(
                    "DateStyle",
                    parent=self._styles["Normal"],
                    fontSize=12,
                    textColor=self.COLORS["muted"],
                    alignment=TA_CENTER,
                ),
            )
        )
        elements.append(PageBreak())

        # Executive Summary
        elements.append(Paragraph("Executive Summary", self._styles["SectionHeader"]))

        portfolio_summary = dashboard_metrics.get("portfolio_summary", {})

        # Key metrics grid
        summary_data = [
            ["Total Properties", "Total Units", "Total Value", "Avg Occupancy"],
            [
                str(portfolio_summary.get("total_properties", 0)),
                f"{portfolio_summary.get('total_units', 0):,}",
                self._format_currency(portfolio_summary.get("total_value", 0)),
                self._format_percent(portfolio_summary.get("avg_occupancy", 0)),
            ],
        ]

        summary_table = Table(summary_data, colWidths=[1.5 * inch] * 4)
        summary_table.setStyle(self._create_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 30))

        # KPIs
        elements.append(
            Paragraph("Key Performance Indicators", self._styles["SubSectionHeader"])
        )

        kpis = dashboard_metrics.get("kpis", {})
        kpi_data = [
            ["KPI", "Value"],
            ["YTD NOI Growth", self._format_percent(kpis.get("ytd_noi_growth", 0))],
            ["YTD Rent Growth", self._format_percent(kpis.get("ytd_rent_growth", 0))],
            ["Deals in Pipeline", str(kpis.get("deals_in_pipeline", 0))],
            ["Deals Closed YTD", str(kpis.get("deals_closed_ytd", 0))],
            [
                "Capital Deployed YTD",
                self._format_currency(kpis.get("capital_deployed_ytd", 0)),
            ],
        ]

        kpi_table = Table(kpi_data, colWidths=[3 * inch, 3 * inch])
        kpi_table.setStyle(self._create_table_style())
        elements.append(kpi_table)
        elements.append(PageBreak())

        # Portfolio Performance
        elements.append(
            Paragraph("Portfolio Performance", self._styles["SectionHeader"])
        )

        perf = portfolio_analytics.get("performance", {})
        perf_data = [
            ["Metric", "Value"],
            ["Total Return", self._format_percent(perf.get("total_return", 0))],
            ["Income Return", self._format_percent(perf.get("income_return", 0))],
            [
                "Appreciation Return",
                self._format_percent(perf.get("appreciation_return", 0)),
            ],
            ["Benchmark Return", self._format_percent(perf.get("benchmark_return", 0))],
            ["Alpha", self._format_percent(perf.get("alpha", 0))],
        ]

        perf_table = Table(perf_data, colWidths=[3 * inch, 3 * inch])
        perf_table.setStyle(self._create_table_style())
        elements.append(perf_table)
        elements.append(Spacer(1, 30))

        # Property Summary
        elements.append(Paragraph("Property Summary", self._styles["SectionHeader"]))

        if properties:
            prop_headers = ["Name", "Type", "Location", "Occupancy", "NOI"]
            prop_data = [prop_headers]

            for prop in properties[:10]:  # Limit to 10 properties
                prop_data.append(
                    [
                        prop.get("name", "N/A")[:25],
                        prop.get("property_type", "N/A").title(),
                        f"{prop.get('city', 'N/A')}, {prop.get('state', 'N/A')}",
                        self._format_percent(prop.get("occupancy_rate", 0)),
                        self._format_currency(prop.get("noi", 0)),
                    ]
                )

            prop_table = Table(
                prop_data,
                colWidths=[1.8 * inch, 1 * inch, 1.5 * inch, 0.9 * inch, 1 * inch],
            )
            prop_table.setStyle(self._create_table_style())
            elements.append(prop_table)

            if len(properties) > 10:
                elements.append(
                    Paragraph(
                        f"... and {len(properties) - 10} more properties",
                        self._styles["BodyText"],
                    )
                )

        elements.append(PageBreak())

        # Deal Pipeline
        elements.append(Paragraph("Deal Pipeline", self._styles["SectionHeader"]))

        if deals:
            deal_headers = ["Name", "Type", "Stage", "Asking Price", "IRR"]
            deal_data = [deal_headers]

            for deal in deals[:10]:  # Limit to 10 deals
                deal_data.append(
                    [
                        deal.get("name", "N/A")[:25],
                        deal.get("deal_type", "N/A").title(),
                        deal.get("stage", "N/A").replace("_", " ").title(),
                        self._format_currency(deal.get("asking_price", 0)),
                        (
                            self._format_percent(deal.get("projected_irr", 0))
                            if deal.get("projected_irr")
                            else "N/A"
                        ),
                    ]
                )

            deal_table = Table(
                deal_data,
                colWidths=[1.8 * inch, 1 * inch, 1.3 * inch, 1.1 * inch, 0.9 * inch],
            )
            deal_table.setStyle(self._create_table_style())
            elements.append(deal_table)

            if len(deals) > 10:
                elements.append(
                    Paragraph(
                        f"... and {len(deals) - 10} more deals",
                        self._styles["BodyText"],
                    )
                )

        # Build PDF
        doc.build(
            elements,
            onFirstPage=self._create_header_footer,
            onLaterPages=self._create_header_footer,
        )

        buffer.seek(0)
        logger.info("Generated portfolio report")
        return buffer


# Service singleton
_pdf_service: Optional[PDFReportService] = None


def get_pdf_service() -> PDFReportService:
    """Get the PDF report service singleton."""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFReportService()
    return _pdf_service
