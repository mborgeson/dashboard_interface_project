"""
Chart generation helpers for PDF reports.

Produces matplotlib figures with a consistent B&R Capital visual style and
converts them into ReportLab ``Image`` flowables that can be embedded in
SimpleDocTemplate builds. Also exposes pure-ReportLab flowables such as KPI
tiles and section headers that share the same color palette.

All charts are rendered on the headless ``Agg`` backend so this module is
safe to import from background workers. No GUI / no network.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from io import BytesIO
from typing import Any

import matplotlib

# MUST be set before importing pyplot so the worker runs headlessly.
matplotlib.use("Agg")

import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from loguru import logger  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.colors import HexColor  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle  # noqa: E402
from reportlab.platypus.flowables import Flowable  # noqa: E402

# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------

# Hex strings -- used for both matplotlib and reportlab.
BRAND_NAVY = "#0A1F44"
BRAND_GOLD = "#C9A74C"
BRAND_GOOD = "#2E7D32"
BRAND_BAD = "#C62828"
BRAND_NEUTRAL = "#6B7280"
BRAND_SURFACE = "#F8F9FB"
BRAND_TEXT = "#1F2937"
BRAND_WHITE = "#FFFFFF"

# Categorical palette for multi-series charts (muted, print-friendly).
CATEGORICAL_PALETTE: list[str] = [
    BRAND_NAVY,
    BRAND_GOLD,
    "#4A6FA5",  # lighter navy
    "#8C7029",  # darker gold
    "#5A6B7A",  # slate
    "#9CA3AF",  # warm gray
    BRAND_GOOD,
    BRAND_BAD,
    "#B08D44",  # sand
    "#2B4A74",  # steel blue
]


def _rl(color_hex: str) -> colors.Color:
    """Convert a hex string to a ReportLab Color object."""
    return HexColor(color_hex)


# ReportLab color constants for re-use across the report modules.
RL_NAVY = _rl(BRAND_NAVY)
RL_GOLD = _rl(BRAND_GOLD)
RL_GOOD = _rl(BRAND_GOOD)
RL_BAD = _rl(BRAND_BAD)
RL_NEUTRAL = _rl(BRAND_NEUTRAL)
RL_SURFACE = _rl(BRAND_SURFACE)
RL_TEXT = _rl(BRAND_TEXT)
RL_WHITE = _rl(BRAND_WHITE)


# ---------------------------------------------------------------------------
# Matplotlib style setup
# ---------------------------------------------------------------------------

_STYLE_APPLIED = False


def setup_matplotlib_style() -> None:
    """Configure the global matplotlib rcParams for B&R report charts.

    Idempotent; safe to call repeatedly. Applies a clean, business-grade style:
    no top/right spines, minimal gridlines, Helvetica family, tabular figures.
    """
    global _STYLE_APPLIED
    if _STYLE_APPLIED:
        return

    plt.rcParams.update(
        {
            # Fonts — Helvetica is available via the matplotlib font fallback
            # chain on Windows/Mac/Linux; we fall back to sans-serif.
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Helvetica",
                "Arial",
                "DejaVu Sans",
                "Liberation Sans",
                "sans-serif",
            ],
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.titlecolor": BRAND_NAVY,
            "axes.labelsize": 10,
            "axes.labelcolor": BRAND_TEXT,
            "axes.edgecolor": BRAND_NEUTRAL,
            "axes.linewidth": 0.8,
            "axes.grid": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": BRAND_TEXT,
            "ytick.color": BRAND_TEXT,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.fontsize": 9,
            "legend.frameon": False,
            "legend.facecolor": "white",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.dpi": 150,
            "figure.dpi": 150,
            "axes.titlepad": 14,
            "axes.labelpad": 6,
        }
    )
    _STYLE_APPLIED = True


# ---------------------------------------------------------------------------
# Figure -> ReportLab Image
# ---------------------------------------------------------------------------


def chart_to_image(
    fig: Figure,
    width_inches: float,
    height_inches: float,
) -> Image:
    """Render a matplotlib figure into a ReportLab Image flowable.

    The figure is flushed to an in-memory PNG buffer, the matplotlib figure
    is closed to free resources, and the buffer is wrapped in a ReportLab
    ``Image`` sized to the requested inch dimensions.
    """
    try:
        fig.set_size_inches(width_inches, height_inches)
        buf = BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=150,
            bbox_inches="tight",
            facecolor="white",
        )
        buf.seek(0)
        img = Image(buf, width=width_inches * inch, height=height_inches * inch)
        return img
    finally:
        plt.close(fig)


# ---------------------------------------------------------------------------
# Safe number coercion
# ---------------------------------------------------------------------------


def _to_float(v: Any) -> float:
    """Coerce Decimal / int / float / None into a plain float.

    Returns 0.0 for None or non-numeric values so charts render instead of
    crashing on missing DB data.
    """
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _fmt_abbrev_dollars(value: float) -> str:
    """Format a dollar value as $X.XM / $X.XK for chart labels."""
    if value is None:
        return "—"
    av = abs(value)
    if av >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if av >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if av >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------


def create_treemap(
    labels: Sequence[str],
    values: Sequence[float],
    title: str = "",
    colors_list: Sequence[str] | None = None,
) -> Figure:
    """Create a simple treemap (squarified) of labels -> values.

    Uses a lightweight squarified layout (no external ``squarify`` dep).
    Tiles are colored from the brand categorical palette.
    """
    setup_matplotlib_style()

    float_vals: list[float] = [max(_to_float(v), 0.0) for v in values]
    total = sum(float_vals) or 1.0
    # Sort by value descending for a nicer layout.
    pairs = sorted(
        zip(labels, float_vals, strict=False), key=lambda p: p[1], reverse=True
    )
    sorted_labels = [p[0] for p in pairs]
    sorted_values = [p[1] for p in pairs]

    palette = list(colors_list) if colors_list else CATEGORICAL_PALETTE
    rects = _squarify(sorted_values, 0.0, 0.0, 100.0, 100.0)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for i, (lbl, rect, val) in enumerate(
        zip(sorted_labels, rects, sorted_values, strict=False)
    ):
        x, y, w, h = rect
        color = palette[i % len(palette)]
        ax.add_patch(
            mpatches.Rectangle(
                (x, y), w, h, facecolor=color, edgecolor="white", linewidth=1.5
            )
        )
        if w * h < 40:
            continue  # too small to label
        pct = (val / total) * 100
        cx, cy = x + w / 2, y + h / 2
        label_text = lbl if len(lbl) <= 18 else lbl[:16] + "…"
        ax.text(
            cx,
            cy + 2,
            label_text,
            ha="center",
            va="center",
            color="white",
            fontsize=9,
            fontweight="bold",
        )
        ax.text(
            cx,
            cy - 3,
            f"{_fmt_abbrev_dollars(val)}  ({pct:.1f}%)",
            ha="center",
            va="center",
            color="white",
            fontsize=8,
        )

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig


def _squarify(
    values: Sequence[float],
    x: float,
    y: float,
    width: float,
    height: float,
) -> list[tuple[float, float, float, float]]:
    """Very small squarified treemap layout.

    Not optimal but produces visually reasonable rectangles and is dependency
    free.
    """
    total = sum(values) or 1.0
    scaled = [v * width * height / total for v in values]

    rects: list[tuple[float, float, float, float]] = []
    _layout(scaled[:], x, y, width, height, rects)
    return rects


def _layout(
    values: list[float],
    x: float,
    y: float,
    width: float,
    height: float,
    out: list[tuple[float, float, float, float]],
) -> None:
    if not values:
        return
    if len(values) == 1:
        out.append((x, y, width, height))
        return

    total = sum(values)
    if total <= 0:
        return

    # Split into two halves proportional to value mass.
    running = 0.0
    half_total = total / 2.0
    split_idx = 1
    for i, v in enumerate(values):
        running += v
        if running >= half_total:
            split_idx = i + 1
            break

    first = values[:split_idx]
    second = values[split_idx:]
    first_sum = sum(first)
    ratio = first_sum / total if total > 0 else 0.5

    if width >= height:
        w1 = width * ratio
        _layout(first, x, y, w1, height, out)
        _layout(second, x + w1, y, width - w1, height, out)
    else:
        h1 = height * ratio
        _layout(first, x, y, width, h1, out)
        _layout(second, x, y + h1, width, height - h1, out)


def create_horizontal_bar(
    labels: Sequence[str],
    values: Sequence[float],
    title: str = "",
    value_formatter: Any = None,
    color: str = BRAND_NAVY,
) -> Figure:
    """Horizontal bar chart. Sorted descending by value for readability."""
    setup_matplotlib_style()

    float_vals = [_to_float(v) for v in values]
    pairs = sorted(
        zip(labels, float_vals, strict=False), key=lambda p: p[1], reverse=False
    )
    sorted_labels = [p[0] for p in pairs]
    sorted_values = [p[1] for p in pairs]

    fig, ax = plt.subplots(figsize=(7, max(3.0, 0.35 * len(labels) + 1.5)))
    bars = ax.barh(sorted_labels, sorted_values, color=color, edgecolor="white")

    if title:
        ax.set_title(title, loc="left")

    # Label each bar with its value.
    fmt = value_formatter or _fmt_abbrev_dollars
    max_val = max(sorted_values) if sorted_values else 0
    pad = max_val * 0.01 if max_val else 0.05
    for bar, val in zip(bars, sorted_values, strict=False):
        ax.text(
            bar.get_width() + pad,
            bar.get_y() + bar.get_height() / 2,
            fmt(val),
            va="center",
            ha="left",
            fontsize=9,
            color=BRAND_TEXT,
        )

    ax.spines["bottom"].set_color(BRAND_NEUTRAL)
    ax.spines["left"].set_color(BRAND_NEUTRAL)
    ax.tick_params(axis="x", length=3)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(left=0, right=(max_val * 1.2 if max_val else 1))
    ax.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _pos: fmt(v))  # type: ignore[attr-defined]
    )
    fig.tight_layout()
    return fig


def create_donut(
    labels: Sequence[str],
    values: Sequence[float],
    title: str = "",
    colors_list: Sequence[str] | None = None,
) -> Figure:
    """Donut chart for categorical distribution."""
    setup_matplotlib_style()

    float_vals = [max(_to_float(v), 0.0) for v in values]
    palette = list(colors_list) if colors_list else CATEGORICAL_PALETTE

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    total = sum(float_vals) or 1.0
    if total <= 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12)
        ax.axis("off")
        return fig

    pie_result = ax.pie(
        float_vals,
        labels=None,
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 4 else "",
        pctdistance=0.78,
        colors=palette[: len(labels)],
        startangle=90,
        wedgeprops={"width": 0.4, "edgecolor": "white", "linewidth": 2},
    )
    # ax.pie returns (wedges, texts, autotexts) when autopct is set.
    wedges = pie_result[0]
    if len(pie_result) >= 3:
        for at in pie_result[2]:
            at.set_color("white")
            at.set_fontsize(10)
            at.set_fontweight("bold")

    if title:
        ax.set_title(title)

    # Legend outside with counts.
    legend_labels = [
        f"{lbl}  —  {_fmt_abbrev_dollars(v) if v > 1000 else f'{v:.0f}'}"
        for lbl, v in zip(labels, float_vals, strict=False)
    ]
    ax.legend(
        wedges,
        legend_labels,
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        frameon=False,
        fontsize=9,
    )
    fig.tight_layout()
    return fig


def create_waterfall(
    labels: Sequence[str],
    values: Sequence[float],
    title: str = "",
    y_label: str = "",
) -> Figure:
    """Waterfall chart.

    Values should be signed deltas, with the FIRST and LAST entries treated
    as absolute totals (beginning and ending). Intermediate entries are
    stacked relative to the running total.
    """
    setup_matplotlib_style()

    float_vals = [_to_float(v) for v in values]
    n = len(float_vals)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    if n == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    running = 0.0
    bottoms: list[float] = []
    heights: list[float] = []
    bar_colors: list[str] = []

    for i, v in enumerate(float_vals):
        if i == 0 or i == n - 1:
            # Total bar
            bottoms.append(0.0)
            heights.append(v)
            bar_colors.append(BRAND_NAVY)
            running = v
        else:
            if v >= 0:
                bottoms.append(running)
                heights.append(v)
                bar_colors.append(BRAND_GOOD)
            else:
                bottoms.append(running + v)
                heights.append(-v)
                bar_colors.append(BRAND_BAD)
            running += v

    xs = list(range(n))
    ax.bar(
        xs,
        heights,
        bottom=bottoms,
        color=bar_colors,
        edgecolor="white",
        linewidth=1.2,
        width=0.6,
    )

    # Connector lines
    tops = [bottoms[i] + heights[i] for i in range(n)]
    for i in range(n - 1):
        # Draw a thin connector from top of bar i to bottom of bar i+1 baseline.
        y_line = tops[i]
        ax.plot(
            [i + 0.3, i + 1 - 0.3],
            [y_line, y_line],
            color=BRAND_NEUTRAL,
            linestyle="--",
            linewidth=0.7,
        )

    # Value labels
    for i in range(n):
        v = float_vals[i]
        y_top = tops[i]
        ax.text(
            i,
            y_top + (max(heights) * 0.015 if heights else 0),
            _fmt_abbrev_dollars(v),
            ha="center",
            va="bottom",
            fontsize=8,
            color=BRAND_TEXT,
        )

    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    if title:
        ax.set_title(title, loc="left")
    if y_label:
        ax.set_ylabel(y_label)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _pos: _fmt_abbrev_dollars(v))  # type: ignore[attr-defined]
    )
    ax.axhline(y=0, color=BRAND_NEUTRAL, linewidth=0.6)
    fig.tight_layout()
    return fig


def create_funnel(
    labels: Sequence[str],
    values: Sequence[float],
    title: str = "",
) -> Figure:
    """Funnel chart (horizontal bands) with per-stage conversion rates."""
    setup_matplotlib_style()

    float_vals = [max(_to_float(v), 0.0) for v in values]
    n = len(float_vals)
    fig, ax = plt.subplots(figsize=(7, max(3.0, 0.6 * n + 1.5)))

    if n == 0 or max(float_vals) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    max_val = max(float_vals)

    y_positions = list(range(n - 1, -1, -1))
    for i, (lbl, val) in enumerate(zip(labels, float_vals, strict=False)):
        y = y_positions[i]
        half = (val / max_val) * 0.4
        color = CATEGORICAL_PALETTE[i % len(CATEGORICAL_PALETTE)]
        ax.barh(
            y,
            width=half * 2,
            left=0.5 - half,
            height=0.7,
            color=color,
            edgecolor="white",
        )
        conv = ""
        if i > 0 and float_vals[i - 1] > 0:
            rate = val / float_vals[i - 1] * 100
            conv = f"  ({rate:.0f}% conv)"
        ax.text(
            0.5,
            y,
            f"{lbl}: {int(val)}{conv}",
            ha="center",
            va="center",
            color="white",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.6, n - 0.4)
    ax.axis("off")
    if title:
        ax.set_title(title, loc="left", color=BRAND_NAVY)
    fig.tight_layout()
    return fig


def create_line(
    x_values: Sequence[Any],
    y_values_dict: dict[str, Sequence[float]],
    title: str = "",
    y_label: str = "",
    x_label: str = "",
    y_formatter: Any = None,
) -> Figure:
    """Line chart — supports multiple series via dict of {label: values}."""
    setup_matplotlib_style()

    fig, ax = plt.subplots(figsize=(7, 4))
    for i, (series_label, series_vals) in enumerate(y_values_dict.items()):
        float_vals = [_to_float(v) for v in series_vals]
        color = CATEGORICAL_PALETTE[i % len(CATEGORICAL_PALETTE)]
        ax.plot(
            list(x_values),
            float_vals,
            color=color,
            linewidth=2.0,
            marker="o",
            markersize=4,
            label=series_label,
        )

    if title:
        ax.set_title(title, loc="left")
    if y_label:
        ax.set_ylabel(y_label)
    if x_label:
        ax.set_xlabel(x_label)
    if y_formatter is not None:
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _pos: y_formatter(v))  # type: ignore[attr-defined]
        )
    ax.grid(axis="y", linestyle=":", color=BRAND_NEUTRAL, alpha=0.3)
    if len(y_values_dict) > 1:
        ax.legend(loc="best")
    fig.tight_layout()
    return fig


def create_scatter(
    x_values: Sequence[float],
    y_values: Sequence[float],
    sizes: Sequence[float] | None = None,
    labels: Sequence[str] | None = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    color: str = BRAND_NAVY,
) -> Figure:
    """Bubble / scatter plot."""
    setup_matplotlib_style()

    xs = [_to_float(v) for v in x_values]
    ys = [_to_float(v) for v in y_values]
    if sizes is not None:
        raw = [max(_to_float(s), 0.0) for s in sizes]
        max_raw = max(raw) or 1.0
        bubble_sizes = [40 + (r / max_raw) * 400 for r in raw]
    else:
        bubble_sizes = [80.0] * len(xs)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(
        xs,
        ys,
        s=bubble_sizes,
        color=color,
        alpha=0.55,
        edgecolors=BRAND_NAVY,
        linewidths=0.8,
    )

    if labels is not None:
        for x, y, lbl in zip(xs, ys, labels, strict=False):
            ax.annotate(
                lbl,
                (x, y),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=7,
                color=BRAND_TEXT,
            )

    if title:
        ax.set_title(title, loc="left")
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    ax.grid(axis="both", linestyle=":", color=BRAND_NEUTRAL, alpha=0.3)
    fig.tight_layout()
    return fig


def create_stacked_bar(
    x_labels: Sequence[str],
    series: dict[str, Sequence[float]],
    title: str = "",
    y_label: str = "",
    horizontal: bool = False,
    y_formatter: Any = None,
) -> Figure:
    """Stacked bar chart (vertical by default)."""
    setup_matplotlib_style()

    fig, ax = plt.subplots(figsize=(7, 4.5))
    n = len(x_labels)
    if n == 0 or not series:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    bottoms = [0.0] * n
    for i, (lbl, vals) in enumerate(series.items()):
        fvals = [_to_float(v) for v in vals]
        color = CATEGORICAL_PALETTE[i % len(CATEGORICAL_PALETTE)]
        if horizontal:
            ax.barh(
                list(x_labels),
                fvals,
                left=bottoms,
                label=lbl,
                color=color,
                edgecolor="white",
            )
        else:
            ax.bar(
                list(x_labels),
                fvals,
                bottom=bottoms,
                label=lbl,
                color=color,
                edgecolor="white",
            )
        bottoms = [bottoms[j] + fvals[j] for j in range(n)]

    if title:
        ax.set_title(title, loc="left")
    if y_label and not horizontal:
        ax.set_ylabel(y_label)
    elif y_label and horizontal:
        ax.set_xlabel(y_label)

    if y_formatter is not None:
        if horizontal:
            ax.xaxis.set_major_formatter(
                plt.FuncFormatter(lambda v, _pos: y_formatter(v))  # type: ignore[attr-defined]
            )
        else:
            ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda v, _pos: y_formatter(v))  # type: ignore[attr-defined]
            )

    if not horizontal:
        plt.setp(ax.get_xticklabels(), rotation=25, ha="right", fontsize=8)

    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Pure-ReportLab flowables (no matplotlib)
# ---------------------------------------------------------------------------


def create_kpi_tile(
    label: str,
    value: str,
    delta: str | None = None,
    delta_positive: bool | None = None,
    width: float = 1.8 * inch,
    height: float = 1.0 * inch,
) -> Flowable:
    """Build a KPI tile (big metric + label + optional delta arrow) as a Table.

    Returns a flowable that can be placed inside another Table to form a grid.
    """
    from reportlab.lib.styles import ParagraphStyle

    label_style = ParagraphStyle(
        "KPILabel",
        fontName="Helvetica",
        fontSize=8,
        textColor=RL_NEUTRAL,
        alignment=1,  # center
        leading=10,
    )
    value_style = ParagraphStyle(
        "KPIValue",
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=RL_NAVY,
        alignment=1,
        leading=22,
    )
    delta_color = RL_NEUTRAL
    if delta_positive is True:
        delta_color = RL_GOOD
    elif delta_positive is False:
        delta_color = RL_BAD

    delta_style = ParagraphStyle(
        "KPIDelta",
        fontName="Helvetica",
        fontSize=8,
        textColor=delta_color,
        alignment=1,
        leading=10,
    )

    rows: list[list[Any]] = [
        [Paragraph(label.upper(), label_style)],
        [Paragraph(value, value_style)],
    ]
    if delta:
        arrow = ""
        if delta_positive is True:
            arrow = "▲ "
        elif delta_positive is False:
            arrow = "▼ "
        rows.append([Paragraph(f"{arrow}{delta}", delta_style)])
    else:
        rows.append([Spacer(1, 8)])

    tile = Table(rows, colWidths=[width], rowHeights=None)
    tile.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RL_SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.75, RL_NEUTRAL),
                ("LINEABOVE", (0, 0), (-1, 0), 2.5, RL_GOLD),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    tile._kpi_height = height  # type: ignore[attr-defined]
    return tile


def build_kpi_grid(
    tiles: Sequence[Flowable],
    *,
    columns: int = 3,
    tile_width: float = 1.9 * inch,
    gap: float = 0.15 * inch,
) -> Table:
    """Arrange KPI tiles into a grid of ``columns`` columns."""
    rows: list[list[Any]] = []
    row: list[Any] = []
    for i, tile in enumerate(tiles):
        row.append(tile)
        if (i + 1) % columns == 0:
            rows.append(row)
            row = []
    if row:
        while len(row) < columns:
            row.append(Spacer(1, 1))
        rows.append(row)

    col_widths = [tile_width] * columns
    grid = Table(rows, colWidths=col_widths, hAlign="CENTER")
    grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), gap / 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), gap / 2),
                ("TOPPADDING", (0, 0), (-1, -1), gap / 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), gap / 2),
            ]
        )
    )
    return grid


def safe_render(
    builder_fn: Any, *args: Any, fallback_width: float = 6.5, **kwargs: Any
) -> Flowable:
    """Execute a chart-builder function and wrap it into an Image flowable.

    If the builder raises, returns a small Paragraph describing the failure
    so the rest of the report still renders.
    """
    from reportlab.lib.styles import ParagraphStyle

    width_in = kwargs.pop("width_inches", fallback_width)
    height_in = kwargs.pop("height_inches", 4.0)
    try:
        fig = builder_fn(*args, **kwargs)
        return chart_to_image(fig, width_in, height_in)
    except Exception as e:  # pragma: no cover - defensive
        logger.exception(f"Chart render failed: {e}")
        style = ParagraphStyle(
            "ChartError",
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=RL_NEUTRAL,
        )
        return Paragraph(f"[Chart unavailable: {e}]", style)
