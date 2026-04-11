"""
Template-specific PDF renderers for B&R Capital reporting.

Exposes five renderer functions (one per template category) that consume a
typed dataclass from :mod:`app.services.report_data` and emit a BytesIO
buffer containing a fully composed PDF.

All renderers share:
- The same brand palette / fonts defined in :mod:`app.services.report_charts`
- A common header/footer callback (navy bar + gold accent + page number)
- A cover-page helper that produces a polished LP-facing first page

The renderers never call external services or read from the database — they
are pure layout over data dataclasses.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from loguru import logger
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable

from app.services.report_charts import (
    BRAND_GOLD,
    BRAND_NAVY,
    RL_BAD,
    RL_GOLD,
    RL_NAVY,
    RL_NEUTRAL,
    RL_SURFACE,
    RL_TEXT,
    RL_WHITE,
    build_kpi_grid,
    create_donut,
    create_funnel,
    create_horizontal_bar,
    create_kpi_tile,
    create_line,
    create_scatter,
    create_stacked_bar,
    create_treemap,
    create_waterfall,
    safe_render,
    setup_matplotlib_style,
)
from app.services.report_data import (
    DealPipelineData,
    InvestorDistributionData,
    MarketAnalysisData,
    PortfolioOverviewData,
    PropertyPerformanceData,
)

# ---------------------------------------------------------------------------
# Page geometry
# ---------------------------------------------------------------------------

PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 0.6 * inch
RIGHT_MARGIN = 0.6 * inch
TOP_MARGIN = 0.85 * inch
BOTTOM_MARGIN = 0.6 * inch
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

# ---------------------------------------------------------------------------
# Shared style sheet
# ---------------------------------------------------------------------------


def _build_styles() -> dict[str, ParagraphStyle]:
    """Return a dict of branded paragraph styles.

    We avoid mutating ``getSampleStyleSheet`` directly because it's a global
    singleton and name collisions cause KeyError on later calls in the same
    process.
    """
    base = getSampleStyleSheet()

    return {
        "h1": ParagraphStyle(
            "BRH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=RL_NAVY,
            spaceBefore=8,
            spaceAfter=10,
            alignment=TA_LEFT,
        ),
        "h2": ParagraphStyle(
            "BRH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=RL_NAVY,
            spaceBefore=12,
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "h3": ParagraphStyle(
            "BRH3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=RL_NAVY,
            spaceBefore=8,
            spaceAfter=4,
            alignment=TA_LEFT,
        ),
        "body": ParagraphStyle(
            "BRBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=RL_TEXT,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
        ),
        "body_left": ParagraphStyle(
            "BRBodyLeft",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=RL_TEXT,
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "caption": ParagraphStyle(
            "BRCaption",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=10,
            textColor=RL_NEUTRAL,
            alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            "BRSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=RL_NEUTRAL,
        ),
        "cover_title": ParagraphStyle(
            "BRCoverTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=34,
            leading=40,
            textColor=RL_WHITE,
            alignment=TA_LEFT,
            spaceAfter=10,
        ),
        "cover_subtitle": ParagraphStyle(
            "BRCoverSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=18,
            leading=22,
            textColor=RL_WHITE,
            alignment=TA_LEFT,
        ),
        "cover_period": ParagraphStyle(
            "BRCoverPeriod",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=RL_GOLD,
            alignment=TA_LEFT,
        ),
        "banner": ParagraphStyle(
            "BRBanner",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=RL_WHITE,
            alignment=TA_CENTER,
        ),
    }


# ---------------------------------------------------------------------------
# Header / footer callback
# ---------------------------------------------------------------------------


def _make_header_footer(
    report_type: str,
) -> Callable[[Canvas, BaseDocTemplate], None]:
    """Build a canvas callback that draws the header/footer for a given report."""

    def draw(canvas: Canvas, doc: BaseDocTemplate) -> None:
        # Skip header/footer on the cover page; the cover template handles its
        # own visuals. Downstream page templates pass through here.
        if getattr(doc, "_skip_header", False):
            return

        canvas.saveState()
        width, height = letter

        # Top navy strip
        canvas.setFillColor(RL_NAVY)
        canvas.rect(0, height - 0.45 * inch, width, 0.45 * inch, fill=1, stroke=0)

        # Gold accent line
        canvas.setStrokeColor(RL_GOLD)
        canvas.setLineWidth(2.0)
        canvas.line(
            0,
            height - 0.48 * inch,
            width,
            height - 0.48 * inch,
        )

        # Header text — left side
        canvas.setFillColor(RL_WHITE)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(LEFT_MARGIN, height - 0.28 * inch, "B&R CAPITAL")
        canvas.setFont("Helvetica", 9)
        canvas.drawString(
            LEFT_MARGIN + 1.2 * inch,
            height - 0.28 * inch,
            f"| {report_type}",
        )

        # Header text — right side (date)
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(
            width - RIGHT_MARGIN,
            height - 0.28 * inch,
            datetime.now(UTC).strftime("%B %Y"),
        )

        # Footer
        canvas.setFillColor(RL_NEUTRAL)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(
            width / 2,
            0.35 * inch,
            "CONFIDENTIAL — For authorized recipients only. Not for redistribution.",
        )
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(RL_NAVY)
        canvas.drawRightString(
            width - RIGHT_MARGIN,
            0.35 * inch,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    return draw


# ---------------------------------------------------------------------------
# Cover page builder
# ---------------------------------------------------------------------------


def _build_cover_canvas(
    canvas: Canvas,
    doc: BaseDocTemplate,
    *,
    title: str,
    subtitle: str,
    period: str,
) -> None:
    """Draw the brand cover-page background (navy top + gold accent)."""
    canvas.saveState()
    width, height = letter

    # Navy background covering the top 45%
    canvas.setFillColor(RL_NAVY)
    canvas.rect(0, height * 0.55, width, height * 0.45, fill=1, stroke=0)

    # Gold accent bar
    canvas.setFillColor(RL_GOLD)
    canvas.rect(
        LEFT_MARGIN,
        height * 0.55 + 0.15 * inch,
        3.5 * inch,
        0.09 * inch,
        fill=1,
        stroke=0,
    )

    # B&R Capital wordmark
    canvas.setFillColor(RL_WHITE)
    canvas.setFont("Helvetica-Bold", 26)
    canvas.drawString(LEFT_MARGIN, height * 0.85, "B&R CAPITAL")
    canvas.setFont("Helvetica", 11)
    canvas.drawString(
        LEFT_MARGIN,
        height * 0.85 - 0.25 * inch,
        "Phoenix Multifamily Investments",
    )

    # Title
    canvas.setFont("Helvetica-Bold", 30)
    canvas.setFillColor(RL_WHITE)
    canvas.drawString(LEFT_MARGIN, height * 0.66, title)

    # Subtitle
    canvas.setFont("Helvetica", 16)
    canvas.drawString(LEFT_MARGIN, height * 0.66 - 0.35 * inch, subtitle)

    # Period tag in gold
    canvas.setFont("Helvetica-Bold", 12)
    canvas.setFillColor(RL_GOLD)
    canvas.drawString(LEFT_MARGIN, height * 0.66 - 0.65 * inch, period.upper())

    # Footer on cover
    canvas.setFillColor(RL_NEUTRAL)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(
        width / 2,
        0.5 * inch,
        "CONFIDENTIAL — Prepared by B&R Capital. Not for redistribution.",
    )
    canvas.setFont("Helvetica", 9)
    canvas.drawString(
        LEFT_MARGIN,
        0.9 * inch,
        f"Generated: {datetime.now(UTC).strftime('%B %d, %Y')}",
    )

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------


def _standard_table_style(header: bool = True) -> TableStyle:
    """Branded style: navy header row, alternating off-white/white body."""
    base = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), RL_TEXT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [RL_WHITE, RL_SURFACE],
        ),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, RL_NAVY),
    ]
    if header:
        base.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), RL_NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), RL_WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
            ]
        )
    return TableStyle(base)


def _numeric_align_style(numeric_cols: Sequence[int]) -> list[tuple[Any, ...]]:
    """Right-align the specified column indices."""
    cmds: list[tuple[Any, ...]] = []
    for col in numeric_cols:
        cmds.append(("ALIGN", (col, 1), (col, -1), "RIGHT"))
    return cmds


# ---------------------------------------------------------------------------
# Doc builder wrapper
# ---------------------------------------------------------------------------


class _ReportDoc(BaseDocTemplate):
    """Doc template with a cover-page page template + default content template."""

    def __init__(
        self,
        buffer: BytesIO,
        *,
        report_type: str,
        cover_title: str,
        cover_subtitle: str,
        cover_period: str,
        show_cover: bool = True,
    ) -> None:
        super().__init__(
            buffer,
            pagesize=letter,
            leftMargin=LEFT_MARGIN,
            rightMargin=RIGHT_MARGIN,
            topMargin=TOP_MARGIN,
            bottomMargin=BOTTOM_MARGIN,
            title=f"B&R Capital {report_type}",
            author="B&R Capital",
            subject=cover_subtitle,
        )
        self._report_type = report_type

        content_frame = Frame(
            LEFT_MARGIN,
            BOTTOM_MARGIN,
            PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN,
            PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN,
            id="content",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )

        # Full-page frame for cover content
        cover_frame = Frame(
            LEFT_MARGIN,
            BOTTOM_MARGIN,
            PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN,
            PAGE_HEIGHT - BOTTOM_MARGIN - 0.3 * inch,
            id="cover",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )

        def _on_cover(canvas: Canvas, doc: BaseDocTemplate) -> None:
            _build_cover_canvas(
                canvas,
                doc,
                title=cover_title,
                subtitle=cover_subtitle,
                period=cover_period,
            )

        self.addPageTemplates(
            [
                PageTemplate(id="Cover", frames=[cover_frame], onPage=_on_cover),
                PageTemplate(
                    id="Content",
                    frames=[content_frame],
                    onPage=_make_header_footer(report_type),
                ),
            ]
        )

    def afterFlowable(self, flowable: Flowable) -> None:
        """Track section headings for a TOC (future-proofing)."""
        return None


def _open_doc(
    *,
    report_type: str,
    cover_title: str,
    cover_subtitle: str,
    cover_period: str,
) -> tuple[BytesIO, _ReportDoc]:
    buf = BytesIO()
    doc = _ReportDoc(
        buf,
        report_type=report_type,
        cover_title=cover_title,
        cover_subtitle=cover_subtitle,
        cover_period=cover_period,
    )
    return buf, doc


def _section_rule(text: str, styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    """Return a section heading + thin gold rule."""
    rule = Table(
        [[""]],
        colWidths=[CONTENT_WIDTH],
        rowHeights=[2],
    )
    rule.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RL_GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [
        Paragraph(text, styles["h2"]),
        rule,
        Spacer(1, 6),
    ]


def _banner(
    text: str,
    bg: colors.Color,
    styles: dict[str, ParagraphStyle],
) -> Flowable:
    """Full-width colored banner paragraph (used for sample disclaimers)."""
    table = Table([[Paragraph(text, styles["banner"])]], colWidths=[CONTENT_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _kpi_tiles_from_metrics(
    metrics: Sequence[Any],
    *,
    tile_width: float | None = None,
    columns: int = 3,
) -> Flowable:
    """Turn a sequence of KPIMetric into a KPI grid flowable."""
    if tile_width is None:
        # Fit the grid exactly to the content width with gaps.
        total_gap = (columns - 1) * 0.15 * inch
        tile_width = (CONTENT_WIDTH - total_gap) / columns
    tiles = [
        create_kpi_tile(
            label=m.label,
            value=m.value,
            delta=m.delta,
            delta_positive=m.delta_positive,
            width=tile_width,
        )
        for m in metrics
    ]
    return build_kpi_grid(tiles, columns=columns, tile_width=tile_width)


# ---------------------------------------------------------------------------
# Template 1: Portfolio Overview
# ---------------------------------------------------------------------------


def render_portfolio_overview(data: PortfolioOverviewData) -> BytesIO:
    """Render the Portfolio Overview report.

    LP-facing quarterly summary. 12-20 pages when populated.
    """
    setup_matplotlib_style()
    styles = _build_styles()

    buf, doc = _open_doc(
        report_type="Portfolio Overview",
        cover_title="Portfolio\nOverview",
        cover_subtitle="B&R Capital Phoenix Multifamily Fund",
        cover_period=data.period_label,
    )

    story: list[Flowable] = []

    # ---------- Page 1: Cover ----------
    # Cover frame just needs a dummy flowable to advance; the canvas draws
    # everything.
    story.append(Spacer(1, 0.1 * inch))
    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # ---------- Executive Summary ----------
    story.extend(_section_rule("Executive Summary", styles))
    story.append(Paragraph(data.executive_summary, styles["body"]))
    story.append(Spacer(1, 0.15 * inch))

    # Quick snapshot row
    summary_table = Table(
        [
            [
                Paragraph(
                    f"<b>Period:</b> {data.period_label}",
                    styles["body_left"],
                ),
                Paragraph(
                    f"<b>Properties:</b> {data.total_properties:,}",
                    styles["body_left"],
                ),
                Paragraph(
                    f"<b>Units:</b> {data.total_units:,}",
                    styles["body_left"],
                ),
            ],
        ],
        colWidths=[CONTENT_WIDTH / 3] * 3,
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RL_SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.5, RL_NEUTRAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(summary_table)
    story.append(PageBreak())

    # ---------- KPI Dashboard ----------
    story.extend(_section_rule("Key Performance Indicators", styles))
    story.append(Spacer(1, 6))
    story.append(_kpi_tiles_from_metrics(data.kpi_tiles, columns=3))
    story.append(Spacer(1, 0.25 * inch))

    story.append(
        Paragraph(
            "The tiles above reflect the portfolio's current position across "
            "our key metrics. Value-weighted occupancy and cap rate capture "
            "the true economic exposure of the portfolio, giving higher "
            "weight to larger assets.",
            styles["body"],
        )
    )
    story.append(PageBreak())

    # ---------- Portfolio Composition (treemap) ----------
    story.extend(_section_rule("Portfolio Composition by Submarket", styles))
    if data.submarket_value:
        labels = [s[0] for s in data.submarket_value]
        values = [s[1] for s in data.submarket_value]
        story.append(
            safe_render(
                create_treemap,
                labels,
                values,
                title="Value by Submarket (Top 10)",
                width_inches=7.0,
                height_inches=4.2,
            )
        )
    else:
        story.append(Paragraph("No submarket data available.", styles["body"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(
        Paragraph(
            "Composition is calculated using current value where available and "
            "purchase price as a fallback. Concentration is consistent with "
            "B&R's workforce-housing thesis across the Phoenix MSA.",
            styles["caption"],
        )
    )
    story.append(PageBreak())

    # ---------- Top 10 NOI Contribution ----------
    story.extend(_section_rule("Top 10 Properties by NOI Contribution", styles))
    if data.top_noi_properties:
        labels = [p[0][:28] for p in data.top_noi_properties]
        values = [p[1] for p in data.top_noi_properties]
        story.append(
            safe_render(
                create_horizontal_bar,
                labels,
                values,
                title="Trailing 12-Month NOI",
                color=BRAND_NAVY,
                width_inches=7.0,
                height_inches=4.5,
            )
        )
    else:
        story.append(Paragraph("No NOI data available.", styles["body"]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(PageBreak())

    # ---------- Property Class Distribution ----------
    story.extend(_section_rule("Distribution by Property Class", styles))
    if data.class_distribution:
        story.append(
            safe_render(
                create_donut,
                list(data.class_distribution.keys()),
                list(data.class_distribution.values()),
                title="Portfolio Value by Class",
                width_inches=6.5,
                height_inches=4.0,
            )
        )
        story.append(Spacer(1, 0.1 * inch))
        story.append(
            Paragraph(
                "Property class is inferred from vintage and in-place rent. "
                "Class A: post-2010 construction or rents above $1,800. "
                "Class B: 1985-2009 or rents $1,300-$1,799. "
                "Class C: older vintage / value-add positioning.",
                styles["caption"],
            )
        )
    else:
        story.append(Paragraph("No class data available.", styles["body"]))
    story.append(PageBreak())

    # ---------- Property Summary Table ----------
    story.extend(_section_rule("Property Summary (Top 20 by Value)", styles))
    header = ["Property", "Submarket", "Units", "Value", "NOI", "Cap", "Occ"]
    rows: list[list[Any]] = [header]
    for p in data.properties:
        rows.append(
            [
                p.name[:28],
                p.submarket[:18],
                f"{p.total_units:,}" if p.total_units else "—",
                _currency(p.current_value or p.purchase_price),
                _currency(p.noi),
                _pct(p.cap_rate),
                _pct(p.occupancy_rate),
            ]
        )

    col_widths = [
        CONTENT_WIDTH * 0.26,
        CONTENT_WIDTH * 0.17,
        CONTENT_WIDTH * 0.09,
        CONTENT_WIDTH * 0.13,
        CONTENT_WIDTH * 0.13,
        CONTENT_WIDTH * 0.11,
        CONTENT_WIDTH * 0.11,
    ]
    prop_table = Table(rows, colWidths=col_widths, repeatRows=1)
    style = _standard_table_style()
    # Right-align numeric columns
    for col in (2, 3, 4, 5, 6):
        style.add("ALIGN", (col, 1), (col, -1), "RIGHT")
    prop_table.setStyle(style)
    story.append(prop_table)
    story.append(PageBreak())

    # ---------- Market Commentary ----------
    story.extend(_section_rule("Market Commentary", styles))
    story.append(Paragraph(data.market_commentary, styles["body"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(
        Paragraph(
            "Methodology & Glossary",
            styles["h3"],
        )
    )
    glossary_rows = [
        ["Metric", "Definition"],
        [
            "Weighted Cap Rate",
            "Sum of (cap rate * property value) / Sum of property values.",
        ],
        [
            "Weighted Occupancy",
            "Sum of (occupancy * property value) / Sum of property values.",
        ],
        [
            "Property Class",
            "A/B/C bucketing based on year built and in-place rent per unit.",
        ],
        [
            "T12 NOI",
            "Net operating income across the trailing twelve months, sourced "
            "from latest operating statements.",
        ],
    ]
    gt = Table(
        glossary_rows,
        colWidths=[CONTENT_WIDTH * 0.25, CONTENT_WIDTH * 0.75],
        repeatRows=1,
    )
    gt.setStyle(_standard_table_style())
    story.append(gt)

    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "This report is generated from B&R Capital's asset management "
            "database and reflects data as of the generation date. Figures are "
            "unaudited. Past performance is not indicative of future results.",
            styles["small"],
        )
    )

    _safe_build(doc, story, report_label="Portfolio Overview")
    buf.seek(0)
    logger.info(
        "Generated Portfolio Overview PDF",
        size_bytes=len(buf.getvalue()),
        properties=data.total_properties,
    )
    return buf


# ---------------------------------------------------------------------------
# Template 2: Property Performance
# ---------------------------------------------------------------------------


def render_property_performance(data: PropertyPerformanceData) -> BytesIO:
    """Render the Property Performance report for a single property."""
    setup_matplotlib_style()
    styles = _build_styles()

    buf, doc = _open_doc(
        report_type="Property Performance",
        cover_title="Property\nPerformance",
        cover_subtitle=data.property_name,
        cover_period=f"{data.submarket} — {data.city}, {data.state}".strip(" —"),
    )

    story: list[Flowable] = []

    # Cover
    story.append(Spacer(1, 0.1 * inch))
    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # ---------- Property Header ----------
    story.extend(_section_rule(data.property_name, styles))
    header_rows = [
        [
            Paragraph("<b>Address:</b>", styles["body_left"]),
            Paragraph(data.property_address or "—", styles["body_left"]),
            Paragraph("<b>Submarket:</b>", styles["body_left"]),
            Paragraph(data.submarket or "—", styles["body_left"]),
        ],
        [
            Paragraph("<b>Units:</b>", styles["body_left"]),
            Paragraph(
                f"{data.total_units:,}" if data.total_units else "—",
                styles["body_left"],
            ),
            Paragraph("<b>Year Built:</b>", styles["body_left"]),
            Paragraph(
                str(data.year_built) if data.year_built else "—",
                styles["body_left"],
            ),
        ],
        [
            Paragraph("<b>Acquired:</b>", styles["body_left"]),
            Paragraph(
                data.acquisition_date.strftime("%b %Y")
                if data.acquisition_date
                else "—",
                styles["body_left"],
            ),
            Paragraph("<b>Current Basis:</b>", styles["body_left"]),
            Paragraph(
                _currency(data.current_basis) if data.current_basis else "—",
                styles["body_left"],
            ),
        ],
    ]
    header_table = Table(
        header_rows,
        colWidths=[
            CONTENT_WIDTH * 0.15,
            CONTENT_WIDTH * 0.35,
            CONTENT_WIDTH * 0.2,
            CONTENT_WIDTH * 0.30,
        ],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RL_SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.5, RL_NEUTRAL),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, RL_NEUTRAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 0.2 * inch))

    # ---------- KPI Tiles ----------
    story.append(Paragraph("Key Operating Metrics", styles["h3"]))
    story.append(_kpi_tiles_from_metrics(data.kpi_tiles, columns=3))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(data.narrative, styles["body"]))
    story.append(PageBreak())

    # ---------- Operating Statement Table ----------
    story.extend(_section_rule("T12 Operating Statement", styles))

    op_rows: list[list[Any]] = [["Line Item", "Amount", "Per Unit", "% of EGI"]]
    for label, amount, per_unit, pct in data.operating_statement:
        op_rows.append(
            [
                label,
                _currency(amount) if amount is not None else "—",
                _currency(per_unit, abbreviate=False) if per_unit is not None else "—",
                f"{pct:.1f}%" if pct is not None else "—",
            ]
        )
    op_table = Table(
        op_rows,
        colWidths=[
            CONTENT_WIDTH * 0.40,
            CONTENT_WIDTH * 0.22,
            CONTENT_WIDTH * 0.20,
            CONTENT_WIDTH * 0.18,
        ],
        repeatRows=1,
    )
    style = _standard_table_style()
    for col in (1, 2, 3):
        style.add("ALIGN", (col, 1), (col, -1), "RIGHT")
    # Bold NOI row if present
    if data.operating_statement:
        for i, row in enumerate(data.operating_statement, start=1):
            if "Net Operating" in row[0]:
                style.add("FONTNAME", (0, i), (-1, i), "Helvetica-Bold")
                style.add("BACKGROUND", (0, i), (-1, i), RL_GOLD)
                style.add("TEXTCOLOR", (0, i), (-1, i), RL_NAVY)
    op_table.setStyle(style)
    story.append(op_table)
    story.append(PageBreak())

    # ---------- NOI Waterfall ----------
    story.extend(_section_rule("Year-over-Year NOI Bridge", styles))
    if data.noi_waterfall:
        labels = [w[0] for w in data.noi_waterfall]
        values = [w[1] for w in data.noi_waterfall]
        story.append(
            safe_render(
                create_waterfall,
                labels,
                values,
                title="NOI Change Drivers",
                y_label="NOI",
                width_inches=7.0,
                height_inches=4.2,
            )
        )
        story.append(Spacer(1, 0.1 * inch))
        story.append(
            Paragraph(
                "Prior year NOI is decomposed into three drivers: rent growth, "
                "physical vacancy change, and operating expense change. "
                "Drivers shown as approximate decomposition.",
                styles["caption"],
            )
        )
    story.append(Spacer(1, 0.2 * inch))

    # ---------- Occupancy Trend ----------
    story.extend(_section_rule("Trailing 12-Month Occupancy", styles))
    if data.occupancy_trend_values:
        story.append(
            safe_render(
                create_line,
                data.occupancy_trend_labels,
                {"Physical Occupancy": data.occupancy_trend_values},
                title="Monthly Physical Occupancy",
                y_label="%",
                y_formatter=lambda v: f"{v:.0f}%",
                width_inches=7.0,
                height_inches=3.8,
            )
        )
    story.append(PageBreak())

    # ---------- Rent Roll / Unit Mix ----------
    story.extend(_section_rule("Unit Mix Summary", styles))
    if data.unit_mix:
        mix_rows: list[list[Any]] = [["Unit Type", "Units", "Avg Rent", "Rent / SF"]]
        for name, count, rent, rent_sf in data.unit_mix:
            mix_rows.append(
                [
                    name,
                    f"{count:,}" if count else "—",
                    _currency(rent, abbreviate=False) if rent else "—",
                    f"${rent_sf:.2f}" if rent_sf else "—",
                ]
            )
        mix_table = Table(
            mix_rows,
            colWidths=[
                CONTENT_WIDTH * 0.30,
                CONTENT_WIDTH * 0.20,
                CONTENT_WIDTH * 0.25,
                CONTENT_WIDTH * 0.25,
            ],
            repeatRows=1,
        )
        style = _standard_table_style()
        for col in (1, 2, 3):
            style.add("ALIGN", (col, 1), (col, -1), "RIGHT")
        mix_table.setStyle(style)
        story.append(mix_table)
    else:
        story.append(Paragraph("No unit mix data available.", styles["body"]))
    story.append(Spacer(1, 0.3 * inch))

    # ---------- Operating Ratios ----------
    story.extend(_section_rule("Operating Ratios & Benchmarks", styles))
    if data.operating_ratios:
        ratio_rows: list[list[Any]] = [["Ratio", "Value", "Benchmark"]]
        for label, value, benchmark in data.operating_ratios:
            ratio_rows.append([label, value, benchmark])
        ratio_table = Table(
            ratio_rows,
            colWidths=[
                CONTENT_WIDTH * 0.45,
                CONTENT_WIDTH * 0.25,
                CONTENT_WIDTH * 0.30,
            ],
            repeatRows=1,
        )
        style = _standard_table_style()
        style.add("ALIGN", (1, 1), (1, -1), "RIGHT")
        ratio_table.setStyle(style)
        story.append(ratio_table)

    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            "Operating statement figures are derived from current period "
            "management reports. Decomposition of NOI drivers and unit mix "
            "are estimated where detail-level data is not yet integrated.",
            styles["small"],
        )
    )

    _safe_build(doc, story, report_label="Property Performance")
    buf.seek(0)
    logger.info(
        "Generated Property Performance PDF",
        size_bytes=len(buf.getvalue()),
        property=data.property_name,
    )
    return buf


# ---------------------------------------------------------------------------
# Template 3: Deal Pipeline
# ---------------------------------------------------------------------------


def render_deal_pipeline(data: DealPipelineData) -> BytesIO:
    """Render the Deal Pipeline report."""
    setup_matplotlib_style()
    styles = _build_styles()

    buf, doc = _open_doc(
        report_type="Deal Pipeline",
        cover_title="Deal\nPipeline",
        cover_subtitle="Investment Committee Report",
        cover_period=data.generated_at.strftime("%B %Y"),
    )

    story: list[Flowable] = []

    # Cover
    story.append(Spacer(1, 0.1 * inch))
    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # ---------- Summary Tiles ----------
    story.extend(_section_rule("Pipeline Snapshot", styles))
    story.append(_kpi_tiles_from_metrics(data.kpi_tiles, columns=4))
    story.append(Spacer(1, 0.2 * inch))

    story.append(
        Paragraph(
            f"The pipeline currently tracks {data.total_deals:,} non-dead deals "
            f"representing {_currency(data.total_asking)} of total asking price. "
            f"Weighted by stage-probability, expected value is "
            f"{_currency(data.weighted_pipeline_value)}. "
            f"{data.deals_closed_ytd:,} deals have reached closed or realized "
            "stage year-to-date.",
            styles["body"],
        )
    )
    story.append(PageBreak())

    # ---------- Sourcing Funnel ----------
    story.extend(_section_rule("Sourcing Funnel", styles))
    if data.funnel_stages:
        labels = [s[0] for s in data.funnel_stages]
        values = [float(s[1]) for s in data.funnel_stages]
        story.append(
            safe_render(
                create_funnel,
                labels,
                values,
                title="Deal Stages",
                width_inches=7.0,
                height_inches=4.5,
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        # Conversion rates table
        conv_rows: list[list[Any]] = [["Transition", "Conversion Rate"]]
        for transition, rate in data.conversion_rates.items():
            conv_rows.append([transition, f"{rate:.0f}%" if rate is not None else "—"])
        conv_table = Table(
            conv_rows,
            colWidths=[CONTENT_WIDTH * 0.6, CONTENT_WIDTH * 0.4],
            repeatRows=1,
        )
        style = _standard_table_style()
        style.add("ALIGN", (1, 1), (1, -1), "RIGHT")
        conv_table.setStyle(style)
        story.append(conv_table)
    story.append(PageBreak())

    # ---------- Active Deals Table ----------
    story.extend(_section_rule("Active Deals", styles))
    if data.active_deals:
        header = [
            "Deal",
            "Submarket",
            "Units",
            "Ask",
            "Stage",
            "IRR",
            "Close",
        ]
        rows: list[list[Any]] = [header]
        for d in data.active_deals:
            rows.append(
                [
                    d.name[:24],
                    d.submarket[:14],
                    f"{d.total_units:,}" if d.total_units else "—",
                    _currency(d.asking_price),
                    d.stage.replace("_", " ").title()[:14],
                    _pct(d.projected_irr) if d.projected_irr is not None else "—",
                    d.target_close_date.strftime("%b %Y")
                    if d.target_close_date
                    else "—",
                ]
            )
        col_widths = [
            CONTENT_WIDTH * 0.23,
            CONTENT_WIDTH * 0.14,
            CONTENT_WIDTH * 0.09,
            CONTENT_WIDTH * 0.13,
            CONTENT_WIDTH * 0.14,
            CONTENT_WIDTH * 0.10,
            CONTENT_WIDTH * 0.13,
        ]
        deal_table = Table(rows, colWidths=col_widths, repeatRows=1)
        style = _standard_table_style()
        for col in (2, 3, 5):
            style.add("ALIGN", (col, 1), (col, -1), "RIGHT")
        deal_table.setStyle(style)
        story.append(deal_table)
    else:
        story.append(Paragraph("No active deals.", styles["body"]))
    story.append(PageBreak())

    # ---------- Pipeline by Stage (stacked / horizontal) ----------
    story.extend(_section_rule("Pipeline Value by Stage", styles))
    if data.stage_value_breakdown:
        # Sort stages in logical order
        preferred_order = [
            "Sourced",
            "Screened",
            "Under Contract",
            "Closed",
            "Realized",
        ]
        ordered_items = sorted(
            data.stage_value_breakdown.items(),
            key=lambda kv: (
                preferred_order.index(kv[0]) if kv[0] in preferred_order else 99
            ),
        )
        labels = [k for k, _ in ordered_items]
        values = [v for _, v in ordered_items]
        story.append(
            safe_render(
                create_horizontal_bar,
                labels,
                values,
                title="Asking $ by Stage",
                color=BRAND_NAVY,
                width_inches=7.0,
                height_inches=3.8,
            )
        )
    story.append(Spacer(1, 0.15 * inch))

    # ---------- Scatter: IRR vs Equity ----------
    if data.scatter_points:
        story.extend(_section_rule("IRR vs. Equity Required", styles))
        xs = [p[0] for p in data.scatter_points]
        ys = [p[1] for p in data.scatter_points]
        sizes = [p[2] for p in data.scatter_points]
        labels = [p[3] for p in data.scatter_points]
        story.append(
            safe_render(
                create_scatter,
                xs,
                ys,
                sizes=sizes,
                labels=labels,
                title="Active Deals (bubble size = stage probability)",
                x_label="Projected IRR (%)",
                y_label="Equity Required ($M)",
                width_inches=7.0,
                height_inches=4.2,
            )
        )
    story.append(PageBreak())

    # ---------- Submarket Deployment ----------
    story.extend(_section_rule("Deployment by Submarket", styles))
    if data.submarket_deployment:
        labels = [s[0] for s in data.submarket_deployment]
        values = [s[1] for s in data.submarket_deployment]
        story.append(
            safe_render(
                create_horizontal_bar,
                labels,
                values,
                title="Asking $ by Submarket",
                color=BRAND_GOLD,
                width_inches=7.0,
                height_inches=4.0,
            )
        )
    else:
        story.append(Paragraph("No submarket deployment data.", styles["body"]))
    story.append(Spacer(1, 0.2 * inch))

    # ---------- Dead Deal Analysis ----------
    if data.dead_deal_reasons:
        story.extend(_section_rule("Dead Deal Analysis", styles))
        dead_rows: list[list[Any]] = [["Reason", "Count"]]
        for reason, count in data.dead_deal_reasons:
            dead_rows.append([reason, str(count)])
        dead_table = Table(
            dead_rows,
            colWidths=[CONTENT_WIDTH * 0.7, CONTENT_WIDTH * 0.3],
            repeatRows=1,
        )
        style = _standard_table_style()
        style.add("ALIGN", (1, 1), (1, -1), "RIGHT")
        dead_table.setStyle(style)
        story.append(dead_table)

    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            "Stage probabilities used to compute weighted pipeline value: "
            "Sourced 10%, Screened 25%, Under Contract 75%, Closed 100%. "
            "Equity requirement is estimated at 30% of asking price.",
            styles["small"],
        )
    )

    _safe_build(doc, story, report_label="Deal Pipeline")
    buf.seek(0)
    logger.info(
        "Generated Deal Pipeline PDF",
        size_bytes=len(buf.getvalue()),
        deals=data.total_deals,
    )
    return buf


# ---------------------------------------------------------------------------
# Template 4: Market Analysis
# ---------------------------------------------------------------------------


def render_market_analysis(data: MarketAnalysisData) -> BytesIO:
    """Render the Phoenix MSA Market Analysis report."""
    setup_matplotlib_style()
    styles = _build_styles()

    buf, doc = _open_doc(
        report_type="Market Analysis",
        cover_title="Phoenix MSA\nMarket Analysis",
        cover_subtitle="Multifamily Intelligence",
        cover_period=data.generated_at.strftime("%B %Y"),
    )

    story: list[Flowable] = []

    # Cover
    story.append(Spacer(1, 0.1 * inch))
    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # ---------- Snapshot ----------
    story.extend(_section_rule("Phoenix MSA Snapshot", styles))
    story.append(_kpi_tiles_from_metrics(data.msa_snapshot, columns=3))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "The Phoenix MSA is the 10th largest metro in the United States "
            "and one of the most actively traded multifamily markets in the "
            "country. The snapshot above summarizes current headline metrics "
            "across population, employment, and apartment fundamentals.",
            styles["body"],
        )
    )
    story.append(PageBreak())

    # ---------- Macro Drivers ----------
    story.extend(_section_rule("Macro Drivers", styles))
    story.append(Paragraph(data.macro_narrative, styles["body"]))
    story.append(Spacer(1, 0.15 * inch))

    # Three small charts in a row: employment, population, income
    row1 = [
        safe_render(
            create_line,
            data.employment_labels,
            {"Employment (M)": data.employment_values},
            title="Employment (Millions)",
            y_formatter=lambda v: f"{v:.2f}",
            width_inches=3.3,
            height_inches=2.4,
        ),
        safe_render(
            create_line,
            data.population_labels,
            {"Population (M)": data.population_values},
            title="Population (Millions)",
            y_formatter=lambda v: f"{v:.2f}",
            width_inches=3.3,
            height_inches=2.4,
        ),
    ]
    macro_table = Table([row1], colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2])
    macro_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(macro_table)
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        safe_render(
            create_line,
            data.income_labels,
            {"Median HH Income ($)": data.income_values},
            title="Median Household Income",
            y_formatter=lambda v: f"${v / 1000:.0f}K",
            width_inches=7.0,
            height_inches=2.8,
        )
    )
    story.append(PageBreak())

    # ---------- Rent & Occupancy Trends ----------
    story.extend(_section_rule("Rent Growth Trend (YoY %)", styles))
    story.append(
        safe_render(
            create_line,
            data.rent_growth_labels,
            {"Rent Growth YoY": data.rent_growth_values},
            title="Asking Rent Growth",
            y_formatter=lambda v: f"{v:.1f}%",
            width_inches=7.0,
            height_inches=3.5,
        )
    )
    story.append(
        Paragraph(
            "Post-pandemic peak rent growth has normalized alongside a "
            "wave of new deliveries. Stabilization and recovery expected as "
            "supply moderates.",
            styles["caption"],
        )
    )
    story.append(PageBreak())

    # ---------- Construction Pipeline ----------
    story.extend(_section_rule("Construction Pipeline by Submarket", styles))
    if data.construction_pipeline:
        submarkets = list(data.construction_pipeline.keys())[:12]
        stage_labels = ["Planned", "Under Construction", "Delivered (LTM)"]
        series: dict[str, list[float]] = {s: [] for s in stage_labels}
        for sub in submarkets:
            data_sub = data.construction_pipeline.get(sub, {})
            for s in stage_labels:
                series[s].append(float(data_sub.get(s, 0)))
        story.append(
            safe_render(
                create_stacked_bar,
                submarkets,
                series,
                title="Units by Stage",
                y_label="Units",
                y_formatter=lambda v: f"{int(v):,}",
                width_inches=7.0,
                height_inches=4.5,
            )
        )
    story.append(PageBreak())

    # ---------- Submarket Comparison Table ----------
    story.extend(_section_rule("Submarket Comparison", styles))
    if data.submarket_rows:
        header = ["Submarket", "Rent", "Occupancy", "New Supply", "Cap Rate"]
        rows: list[list[Any]] = [header]
        for sub, rent, occ, supply, cap in data.submarket_rows:
            rows.append(
                [
                    sub[:22],
                    _currency(rent, abbreviate=False) if rent else "—",
                    _pct(occ),
                    f"{int(supply):,}" if supply else "—",
                    _pct(cap),
                ]
            )
        comp_table = Table(
            rows,
            colWidths=[
                CONTENT_WIDTH * 0.30,
                CONTENT_WIDTH * 0.18,
                CONTENT_WIDTH * 0.17,
                CONTENT_WIDTH * 0.17,
                CONTENT_WIDTH * 0.18,
            ],
            repeatRows=1,
        )
        style = _standard_table_style()
        for col in (1, 2, 3, 4):
            style.add("ALIGN", (col, 1), (col, -1), "RIGHT")
        comp_table.setStyle(style)
        story.append(comp_table)
    story.append(PageBreak())

    # ---------- Scatter Plot: Rent Growth vs Cap Rate ----------
    story.extend(_section_rule("Rent Growth vs. Cap Rate", styles))
    if data.submarket_scatter:
        xs = [p[0] for p in data.submarket_scatter]
        ys = [p[1] for p in data.submarket_scatter]
        labels = [p[2] for p in data.submarket_scatter]
        sizes = [p[3] for p in data.submarket_scatter]
        story.append(
            safe_render(
                create_scatter,
                xs,
                ys,
                sizes=sizes,
                labels=labels,
                title="Submarket Positioning",
                x_label="Rent Growth (%)",
                y_label="Cap Rate (%)",
                width_inches=7.0,
                height_inches=4.5,
            )
        )
    story.append(Spacer(1, 0.2 * inch))

    # ---------- B&R Positioning ----------
    story.extend(_section_rule("B&R Capital Positioning", styles))
    if data.br_positioning:
        header = ["Submarket", "B&R Properties", "B&R Value"]
        rows = [header]
        for sub, count, value in data.br_positioning:
            rows.append(
                [
                    sub,
                    str(count),
                    _currency(value),
                ]
            )
        positioning_table = Table(
            rows,
            colWidths=[
                CONTENT_WIDTH * 0.50,
                CONTENT_WIDTH * 0.25,
                CONTENT_WIDTH * 0.25,
            ],
            repeatRows=1,
        )
        style = _standard_table_style()
        style.add("ALIGN", (1, 1), (1, -1), "RIGHT")
        style.add("ALIGN", (2, 1), (2, -1), "RIGHT")
        positioning_table.setStyle(style)
        story.append(positioning_table)
    else:
        story.append(
            Paragraph("No portfolio positioning data available.", styles["body"])
        )

    story.append(PageBreak())

    # ---------- Sources ----------
    story.extend(_section_rule("Sources & Methodology", styles))
    for src in data.sources:
        story.append(Paragraph(f"• {src}", styles["body_left"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(
        Paragraph(
            "Macro data flagged as 'placeholder' uses illustrative figures "
            "and will be replaced by live feeds in a future release. "
            "Portfolio data (live) is sourced from B&R Capital's internal "
            "asset management database.",
            styles["small"],
        )
    )

    _safe_build(doc, story, report_label="Market Analysis")
    buf.seek(0)
    logger.info(
        "Generated Market Analysis PDF",
        size_bytes=len(buf.getvalue()),
    )
    return buf


# ---------------------------------------------------------------------------
# Template 5: Investor Distribution
# ---------------------------------------------------------------------------


def render_investor_distribution(data: InvestorDistributionData) -> BytesIO:
    """Render the Investor Distribution / Capital Account report."""
    setup_matplotlib_style()
    styles = _build_styles()

    buf, doc = _open_doc(
        report_type="Capital Account Statement",
        cover_title="Capital Account\nStatement",
        cover_subtitle=data.fund_name,
        cover_period=data.period_label,
    )

    story: list[Flowable] = []

    # Cover
    story.append(Spacer(1, 0.1 * inch))
    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # ---------- Sample Banner ----------
    story.append(_banner(data.sample_banner, RL_BAD, styles))
    story.append(Spacer(1, 0.2 * inch))

    # ---------- Header Info ----------
    story.extend(_section_rule("Investor Summary", styles))
    header_rows = [
        [
            Paragraph("<b>Investor:</b>", styles["body_left"]),
            Paragraph(data.investor_name, styles["body_left"]),
        ],
        [
            Paragraph("<b>Fund:</b>", styles["body_left"]),
            Paragraph(data.fund_name, styles["body_left"]),
        ],
        [
            Paragraph("<b>Period:</b>", styles["body_left"]),
            Paragraph(data.period_label, styles["body_left"]),
        ],
        [
            Paragraph("<b>Commitment:</b>", styles["body_left"]),
            Paragraph(_currency(data.commitment), styles["body_left"]),
        ],
    ]
    header_table = Table(
        header_rows,
        colWidths=[CONTENT_WIDTH * 0.25, CONTENT_WIDTH * 0.75],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RL_SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.5, RL_NEUTRAL),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, RL_NEUTRAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(header_table)
    story.append(PageBreak())

    # ---------- Capital Account Roll-Forward ----------
    story.extend(_section_rule("Capital Account Roll-Forward", styles))
    if data.capital_account:
        rows: list[list[Any]] = [["Line Item", "QTD", "YTD", "ITD"]]
        for label, qtd, ytd, itd in data.capital_account:
            rows.append([label, _currency(qtd), _currency(ytd), _currency(itd)])
        ca_table = Table(
            rows,
            colWidths=[
                CONTENT_WIDTH * 0.40,
                CONTENT_WIDTH * 0.20,
                CONTENT_WIDTH * 0.20,
                CONTENT_WIDTH * 0.20,
            ],
            repeatRows=1,
        )
        style = _standard_table_style()
        for col in (1, 2, 3):
            style.add("ALIGN", (col, 1), (col, -1), "RIGHT")
        # Bold beginning / ending NAV
        for i, (label, *_rest) in enumerate(data.capital_account, start=1):
            if "NAV" in label:
                style.add("FONTNAME", (0, i), (-1, i), "Helvetica-Bold")
                style.add("BACKGROUND", (0, i), (-1, i), RL_GOLD)
                style.add("TEXTCOLOR", (0, i), (-1, i), RL_NAVY)
        ca_table.setStyle(style)
        story.append(ca_table)
    story.append(PageBreak())

    # ---------- Distribution Waterfall ----------
    story.extend(_section_rule("Distribution Waterfall (ITD)", styles))
    if data.waterfall_tiers:
        labels = [t[0] for t in data.waterfall_tiers]
        values = [t[1] for t in data.waterfall_tiers]
        story.append(
            safe_render(
                create_waterfall,
                labels,
                values,
                title="ILPA Waterfall",
                y_label="Dollars",
                width_inches=7.0,
                height_inches=4.2,
            )
        )
        story.append(
            Paragraph(
                "Waterfall tiers follow a standard ILPA structure: return "
                "of capital, preferred return at 8% compounded, catch-up to "
                "manager, and 80/20 promote split thereafter.",
                styles["caption"],
            )
        )
    story.append(Spacer(1, 0.2 * inch))

    # ---------- Performance Tiles ----------
    story.extend(_section_rule("Performance Metrics", styles))
    story.append(_kpi_tiles_from_metrics(data.performance_tiles, columns=4))
    story.append(PageBreak())

    # ---------- Fee Reconciliation ----------
    story.extend(_section_rule("Fee Reconciliation", styles))
    if data.fee_rows:
        rows = [["Fee", "QTD", "YTD", "ITD"]]
        total_qtd = 0.0
        total_ytd = 0.0
        total_itd = 0.0
        for name, qtd, ytd, itd in data.fee_rows:
            rows.append([name, _currency(qtd), _currency(ytd), _currency(itd)])
            total_qtd += qtd
            total_ytd += ytd
            total_itd += itd
        rows.append(
            [
                "Total Fees",
                _currency(total_qtd),
                _currency(total_ytd),
                _currency(total_itd),
            ]
        )
        fee_table = Table(
            rows,
            colWidths=[
                CONTENT_WIDTH * 0.40,
                CONTENT_WIDTH * 0.20,
                CONTENT_WIDTH * 0.20,
                CONTENT_WIDTH * 0.20,
            ],
            repeatRows=1,
        )
        style = _standard_table_style()
        for col in (1, 2, 3):
            style.add("ALIGN", (col, 1), (col, -1), "RIGHT")
        style.add("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")
        style.add("BACKGROUND", (0, -1), (-1, -1), RL_SURFACE)
        fee_table.setStyle(style)
        story.append(fee_table)
    story.append(Spacer(1, 0.3 * inch))

    # ---------- Upcoming Schedule ----------
    story.extend(_section_rule("Upcoming Schedule", styles))
    if data.upcoming_events:
        rows = [["Date", "Description", "Amount"]]
        for dt, desc, amt in data.upcoming_events:
            rows.append([dt, desc, _currency(amt)])
        sched_table = Table(
            rows,
            colWidths=[
                CONTENT_WIDTH * 0.25,
                CONTENT_WIDTH * 0.50,
                CONTENT_WIDTH * 0.25,
            ],
            repeatRows=1,
        )
        style = _standard_table_style()
        style.add("ALIGN", (2, 1), (2, -1), "RIGHT")
        sched_table.setStyle(style)
        story.append(sched_table)
    else:
        story.append(Paragraph("No scheduled events.", styles["body"]))

    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            "This statement is for illustrative purposes only. Actual capital "
            "account statements will be produced from LP subscription data once "
            "the investor subledger is integrated.",
            styles["small"],
        )
    )

    _safe_build(doc, story, report_label="Investor Distribution")
    buf.seek(0)
    logger.info(
        "Generated Investor Distribution PDF",
        size_bytes=len(buf.getvalue()),
    )
    return buf


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _safe_build(
    doc: _ReportDoc,
    story: list[Flowable],
    report_label: str,
) -> None:
    """Build the doc, surfacing a helpful error if layout fails."""
    try:
        doc.build(story)
    except Exception as e:
        logger.exception(f"Failed to build {report_label} PDF: {e}")
        # Re-raise so the worker marks the report as failed.
        raise


def _currency(value: Any, abbreviate: bool = True) -> str:
    """Format a numeric value as a currency string (dash fallback)."""
    if value is None:
        return "—"
    try:
        f = float(value)
    except (TypeError, ValueError):
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


def _pct(value: Any) -> str:
    """Format a numeric percentage value with one decimal."""
    if value is None:
        return "—"
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{f:.1f}%"
