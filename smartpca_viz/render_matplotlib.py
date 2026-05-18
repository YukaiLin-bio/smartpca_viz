"""Matplotlib-based PDF rendering for PCA plots (fallback and high-quality).

Supports two styles:
- 'sci': standard scientific publication quality (existing)
- 'nature': Nature-grade output with professional typography, layout, and colour
"""

from __future__ import annotations

import os
import sys
import tempfile
import math
from collections import Counter
from pathlib import Path
from typing import Any

# ─── Graceful degradation ────────────────────────────────────────

HAS_MATPLOTLIB = False
try:
    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "smartpca_viz_matplotlib")
    )
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    HAS_MATPLOTLIB = True
except ImportError:
    pass

HAS_ADJUSTTEXT = False
try:
    from adjustText import adjust_text

    HAS_ADJUSTTEXT = True
except ImportError:
    pass

# ─── KDE dependencies ────────────────────────────────────────────
HAS_SCIPY = False
HAS_NUMPY = False
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    pass

try:
    from scipy import stats

    HAS_SCIPY = True
except ImportError:
    pass

MARKER_MAP = {
    "circle": "o",
    "square": "s",
    "triangle": "^",
    "diamond": "D",
    "cross": "P",
    "x": "X",
    "pentagon": "p",
    "hexagon": "h",
}


# ─── KDE on matplotlib axes ──────────────────────────────────────


def _add_kde_to_axes(ax: Any, rows: list[dict[str, Any]], config: dict[str, Any]) -> None:
    """Render per-group KDE density heatmap on a matplotlib axes (under plot points).

    Gracefully skips if scipy/numpy are unavailable.
    """
    if not HAS_SCIPY or not HAS_NUMPY:
        return
    import numpy as np

    modern = [row for row in rows if row.get("is_modern_background") and not row.get("is_target")]
    if len(modern) < 5:
        return

    from collections import OrderedDict

    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for row in modern:
        g = row.get("group", "Unknown")
        groups.setdefault(g, []).append(row)

    from smartpca_viz.parser import bounds

    min_x, max_x, min_y, max_y = bounds(rows)
    grid_size = 200
    xi = np.linspace(min_x, max_x, grid_size)
    yi = np.linspace(min_y, max_y, grid_size)
    X, Y = np.meshgrid(xi, yi)

    for gname, gpoints in groups.items():
        if len(gpoints) < 5:
            continue
        xs = np.array([float(row["PC1"]) for row in gpoints])
        ys = np.array([float(row["PC2"]) for row in gpoints])
        try:
            kde = stats.gaussian_kde([xs, ys], bw_method=0.25)
            zi = kde([X.ravel(), Y.ravel()]).reshape(grid_size, grid_size)
        except Exception:
            continue

        zi = np.log1p(zi)
        zi = (zi - zi.min()) / (zi.max() - zi.min() + 1e-10)

        group_color = gpoints[0].get("group_color", "#6699CC")
        from smartpca_viz.kde_heatmap import _muted_color as muted_color_for_kde

        muted_rgb = muted_color_for_kde(group_color)
        from matplotlib.colors import LinearSegmentedColormap

        colors = [
            (1, 1, 1, 0),
            (muted_rgb[0], muted_rgb[1], muted_rgb[2], 0.10),
            (muted_rgb[0], muted_rgb[1], muted_rgb[2], 0.35),
        ]
        cmap = LinearSegmentedColormap.from_list(f"kde_{gname}", colors)
        ax.imshow(
            zi,
            extent=[min_x, max_x, min_y, max_y],
            origin="lower",
            cmap=cmap,
            aspect="auto",
            zorder=0,
        )


# ─── Nature-style color handling ─────────────────────────────────

from smartpca_viz.palette import muted_color as palette_muted_color


def _nature_modern_color(group_color: str) -> str:
    """Very muted modern background color for Nature style."""
    return palette_muted_color(group_color, strength=0.25)


# ─── Style presets ───────────────────────────────────────────────

_NATURE_RCPARAMS = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "pdf.fonttype": 42,  # Type 42 (TrueType) — ensures text is searchable
    "ps.fonttype": 42,
    "axes.linewidth": 0.5,        # Nature uses thin axes
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "xtick.major.width": 0.4,
    "ytick.major.width": 0.4,
    "xtick.major.size": 3.0,
    "ytick.major.size": 3.0,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "xtick.direction": "in",      # Nature uses inward ticks
    "ytick.direction": "in",
    "legend.fontsize": 6.5,
    "legend.title_fontsize": 7.5,
    "figure.dpi": 300,
    "savefig.dpi": 600,
}

_SCI_RCPARAMS = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica"],
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.linewidth": 0.8,
    "axes.labelsize": 10,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7,
}


# ─── Star marker matching HTML ────────────────────────────────────
import math

STAR_PATH = None
try:
    from matplotlib.path import Path
    # Build star vertices matching HTML starPoints() exactly
    # HTML 16x16 viewBox: outer r≈6.25, inner r≈2.85 → ratio 0.456
    verts = []
    codes = [Path.MOVETO]
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 1.0 if i % 2 == 0 else 0.456
        verts.append([math.cos(a) * r, math.sin(a) * r])
        codes.append(Path.LINETO)
    codes[-1] = Path.CLOSEPOLY
    STAR_PATH = Path(verts, codes)
except Exception:
    pass


# ─── Publication PDF ─────────────────────────────────────────────


def generate_publication_pdf_matplotlib(
    path: Path,
    rows: list[dict[str, Any]],
    group_order: list[str],
    pop_order: list[str],
    styles: Any,
    eigvals: list[float],
    config: dict[str, Any],
    project: str,
    png_path: Path | None = None,
) -> bool:
    """Generate publication-quality PDF using matplotlib. Returns True if successful.

    Supports two styles via config['pdf_style']:
    - 'sci' : standard scientific (default)
    - 'nature' : Nature-grade output
    """
    if not HAS_MATPLOTLIB:
        return False

    style = str(config.get("pdf_style", "sci")).lower()
    is_nature = style == "nature"

    # Apply style-specific rcParams
    plt.rcParams.update(_NATURE_RCPARAMS if is_nature else _SCI_RCPARAMS)

    if is_nature:
        # Nature: square PCA plot (left) + group legend (right)
        plot_side = float(config.get("pdf_nature_col_width", 3.5))  # square side (in)
        legend_width = float(config.get("pdf_nature_legend_width", 2.2))
        fig_height = plot_side + 0.6       # vertical space with margins
        fig_width = plot_side + legend_width + 0.5  # horizontal space with margins

        fig = plt.figure(figsize=(fig_width, fig_height), dpi=300)
        # Plot: left, square
        pw = plot_side / fig_width
        ph = plot_side / fig_height
        ax = fig.add_axes([0.10, 0.08, pw, ph])
        # Legend: right, same height
        lx = 0.10 + pw + 0.03
        lw = 1.0 - lx - 0.03
        legend_ax = fig.add_axes([lx, 0.08, lw, ph])
        legend_ax.set_axis_off()
    else:
        combine_legend = bool(config.get("pdf_combine_plot_and_legend", True))
        if combine_legend:
            fig = plt.figure(
                figsize=(
                    float(config.get("pdf_combined_width_in", 12.0)),
                    float(config.get("pdf_combined_height_in", 14.2)),
                ),
                dpi=300,
            )
            grid = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.28], hspace=0.16)
            ax = fig.add_subplot(grid[0, 0])
            legend_ax = fig.add_subplot(grid[1, 0])
        else:
            fig, ax = plt.subplots(
                figsize=(
                    float(config.get("pdf_width_in", 8.0)),
                    float(config.get("pdf_height_in", 6.5)),
                ),
                dpi=300,
            )
            legend_ax = None

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.grid(False)

    # Axis styling — Nature: only bottom and left spines
    if is_nature:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_linewidth(0.5)
        ax.spines["left"].set_linewidth(0.5)
        ax.tick_params(pad=2.5)
    else:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Density heatmap layer (under points)
    if config.get("modern_background", False):
        _add_kde_to_axes(ax, rows, config)

    modern_rows = [row for row in rows if row["is_modern_background"] and not row["is_target"]]
    other_rows = [row for row in rows if not row["is_modern_background"] and not row["is_target"]]
    target_rows = [row for row in rows if row["is_target"]]

    # ── Modern background ──────────────────────────────────────
    if modern_rows:
        modern_groups_in_data = sorted(set(row["group"] for row in modern_rows))
        modern_alpha = float(config.get("modern_background_alpha", 0.55))
        # For Nature style, background is even more subtle
        if is_nature:
            modern_alpha *= 0.45
        for mg in modern_groups_in_data:
            mg_rows = [row for row in modern_rows if row["group"] == mg]
            mg_color = mg_rows[0].get("group_color", config.get("modern_background_color", "#B0B8C4"))
            # In Nature style, compute extra-muted per-group colour
            if is_nature:
                mg_color = _nature_modern_color(mg_color)
            ax.scatter(
                [row["PC1"] for row in mg_rows],
                [row["PC2"] for row in mg_rows],
                s=(
                    float(config.get("point_size", 5.0))
                    * 4.0
                    * float(config.get("modern_background_size_multiplier", 0.75))
                ),
                c=mg_color,
                alpha=modern_alpha,
                marker="o",
                linewidths=0,
                rasterized=len(mg_rows) > 500,
                zorder=1,
            )

        # Modern group text labels (if enabled)
        if is_nature and config.get("modern_background_labels", False) and modern_rows:
            for mg in modern_groups_in_data:
                mg_rows = [row for row in modern_rows if row["group"] == mg]
                if not mg_rows:
                    continue
                mg_color = mg_rows[0].get("group_color", "#999999")
                muted_text_color = _nature_modern_color(mg_color)
                mean_pc1 = sum(float(r["PC1"]) for r in mg_rows) / len(mg_rows)
                mean_pc2 = sum(float(r["PC2"]) for r in mg_rows) / len(mg_rows)
                ax.text(
                    mean_pc1, mean_pc2, mg,
                    fontsize=5.5, color=muted_text_color, alpha=0.8,
                    weight="normal", ha="center", va="center",
                    zorder=6,
                )

    # ── Non-modern, non-target (ancient groups) ─────────────────
    for pop in pop_order:
        subset = [row for row in other_rows if row["population"] == pop]
        if not subset:
            continue
        marker = MARKER_MAP.get(styles.population_symbols.get(pop, "circle"), "o")
        colors = [row["group_color"] for row in subset]
        point_size_base = float(config.get("point_size", 5.0)) * 4.0
        # Nature: slightly smaller points
        if is_nature:
            point_size_base *= 0.75
        ax.scatter(
            [row["PC1"] for row in subset],
            [row["PC2"] for row in subset],
            s=point_size_base,
            c=colors,
            alpha=0.85 if not is_nature else 0.78,
            marker=marker,
            linewidths=0.25 if is_nature else 0.25,
            edgecolors="white" if not is_nature else "none",
            zorder=2,
        )

    # ── Target samples ──────────────────────────────────────────
    texts = []
    if target_rows:
        target_color = config.get("target_color", "#D81B60")
        target_outline = config.get("target_outline_color", "black")
        target_s = float(config.get("point_size", 5.0)) * 20.0 * float(config.get("target_size_multiplier", 1.8))
        if is_nature:
            target_s *= 1.2  # More prominent in Nature style
            target_outline = "#222222"
        ax.scatter(
            [row["PC1"] for row in target_rows],
            [row["PC2"] for row in target_rows],
            s=target_s,
            c=target_color,
            alpha=1.0,
            marker="*",
            linewidths=0.9 if is_nature else 0.9,
            edgecolors=target_outline if is_nature else "black",
            zorder=4,
        )
        if config.get("label_targets", True):
            label_fontsize = int(config.get("target_label_fontsize", 8))
            for row in target_rows:
                texts.append(
                    ax.text(
                        row["PC1"],
                        row["PC2"],
                        row["target_label"] or row["sample_id"],
                        fontsize=8 if not is_nature else 7,
                        weight="bold",
                        color="black" if not is_nature else "#1a1a1a",
                        zorder=5,
                    )
                )
            if HAS_ADJUSTTEXT:
                arrow_lw = 0.3 if is_nature else 0.4
                try:
                    adjust_text(
                        texts, ax=ax,
                        arrowprops=dict(arrowstyle="-", color="#555555" if is_nature else "black", lw=arrow_lw),
                    )
                except Exception:
                    pass  # adjust_text may fail on some inputs

    # ── Axis labels ─────────────────────────────────────────────
    from smartpca_viz.parser import explained_variance_labels

    x_label, y_label = explained_variance_labels(eigvals)
    if is_nature:
        ax.set_xlabel(x_label, fontsize=9, labelpad=3)
        ax.set_ylabel(y_label, fontsize=9, labelpad=3)
        # Title: Nature papers don't put titles on figures (they're in captions)
        # but keep a minimal one for the file
        ax.set_title(f"{project}", fontsize=10, weight="bold", pad=6, loc="left")
    else:
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
        ax.tick_params(labelsize=8)
        ax.set_title(f"{project}: PC1 vs PC2", fontsize=11, weight="bold")

    # ── Legend ──────────────────────────────────────────────────
    if is_nature:
        # Right panel: group names as colored dots
        legend_ax.set_axis_off()
        target_color = config.get("target_color", "#D81B60")

        # Collect unique non-target groups from plot data
        all_groups = []
        for row in other_rows:
            g = row.get("group", "Unknown")
            if g not in all_groups:
                all_groups.append(g)

        # Add Target at the end
        if target_rows:
            all_groups.append("Target")

        # Calculate spacing to avoid stacking
        n_grp = len(all_groups)
        n_cols = 1
        grp_per_col = (n_grp + n_cols - 1) // n_cols
        ry_step = min(0.050, 0.88 / (grp_per_col + 1))
        for idx, gname in enumerate(all_groups):
            col_idx = 0
            row_idx = idx
            cx = 0.02
            ry = 0.95 - row_idx * ry_step

            if gname == "Target":
                gc = target_color
                legend_ax.scatter(
                    [cx + 0.03], [ry],
                    s=28, c=gc, marker="*",
                    transform=legend_ax.transAxes, clip_on=False,
                    edgecolors=config.get("target_outline_color", "#222222"),
                    linewidths=0.3, zorder=3,
                )
            else:
                gc = styles.group_colors.get(gname, "#999999")
                legend_ax.scatter(
                    [cx + 0.03], [ry],
                    s=16, c=gc, marker="o",
                    transform=legend_ax.transAxes,
                    clip_on=False, linewidths=0, zorder=3,
                )
            legend_ax.text(
                cx + 0.08, ry, gname,
                transform=legend_ax.transAxes,
                fontsize=5.5, va="center", ha="left",
            )
    elif legend_ax is not None:
        draw_population_legend_axes(legend_ax, rows, group_order, pop_order, styles, config)
        fig.subplots_adjust(left=0.08, right=0.98, top=0.96, bottom=0.035, hspace=0.16)
    else:
        # sci style without combined legend — place legend inside plot
        used_groups = list(dict.fromkeys(r["group"] for r in other_rows))
        handles, labels_list = [], []
        for g in group_order:
            if g in used_groups:
                g_rows = [r for r in other_rows if r["group"] == g]
                if g_rows:
                    gc = g_rows[0]["group_color"]
                    handles.append(plt.Line2D([0], [0], marker="o", color="w",
                                              markerfacecolor=gc, markersize=5, linewidth=0))
                    labels_list.append(g)
        if target_rows:
            handles.append(plt.Line2D([0], [0], marker="*", color="w",
                                      markerfacecolor=target_color,
                                      markeredgecolor="black",
                                      markersize=7, linewidth=0))
            labels_list.append("Target")
        if handles:
            ax.legend(handles, labels_list, loc="best", frameon=False, fontsize=6.5)
        fig.tight_layout()

    # ── Save ────────────────────────────────────────────────────
    if png_path is not None:
        fig.savefig(png_path, dpi=600 if is_nature else 300, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
    with PdfPages(path) as pdf_pages:
        pdf_pages.savefig(fig, dpi=600 if is_nature else 300)
    plt.close(fig)
    return True


def draw_population_legend_axes(
    ax: Any,
    rows: list[dict[str, Any]],
    group_order: list[str],
    pop_order: list[str],
    styles: Any,
    config: dict[str, Any],
) -> None:
    """Draw grouped population legend on a matplotlib axes."""
    from smartpca_viz.parser import build_grouped_population_legend
    import matplotlib.pyplot as plt

    grouped = build_grouped_population_legend(rows, group_order, pop_order, styles.population_symbols)

    entries: list[tuple[str, str, str, str]] = []
    for block in grouped:
        entries.append(
            ("__GROUP__", block["group"], styles.group_colors.get(block["group"], "#999999"), "")
        )
        for pop in block["populations"]:
            entries.append(
                (
                    "POP",
                    pop["population"],
                    styles.group_colors.get(block["group"], "#999999"),
                    pop["symbol"],
                )
            )

    target_rows = [row for row in rows if row.get("is_target")]
    if target_rows:
        entries.append(("__GROUP__", "Target", config.get("target_color", "#FFD400"), ""))
        for row in target_rows:
            entries.append(("TARGET", row["population"], config.get("target_color", "#FFD400"), "star"))

    columns = 4
    rows_per_col = math.ceil(len(entries) / columns)
    ax.set_axis_off()
    ax.add_patch(
        plt.Rectangle(
            (0.035, 0.035),
            0.93,
            0.90,
            transform=ax.transAxes,
            fill=False,
            edgecolor="black",
            linewidth=0.8,
        )
    )

    for idx, (kind, label, color, symbol) in enumerate(entries):
        col = idx // rows_per_col
        row = idx % rows_per_col
        x = 0.06 + col * 0.235
        y = 0.91 - row * (0.86 / max(rows_per_col - 1, 1))

        if kind == "__GROUP__":
            ax.text(x + 0.020, y, label, transform=ax.transAxes, fontsize=7.3, va="center", color="black")
        elif kind == "TARGET":
            ax.scatter(
                [x + 0.006],
                [y],
                s=30,
                c=[config.get("target_color", "#FFD400")],
                marker="o",
                transform=ax.transAxes,
                clip_on=False,
                edgecolors=config.get("target_outline_color", "#FF0000"),
                linewidths=0.8,
            )
            ax.text(x + 0.022, y, label[:32], transform=ax.transAxes, fontsize=6.1, va="center")
        else:
            ax.scatter(
                [x + 0.006],
                [y],
                s=24,
                c="none",
                marker=MARKER_MAP.get(symbol, "o"),
                transform=ax.transAxes,
                clip_on=False,
                edgecolors=color,
                linewidths=0.85,
            )
            ax.text(x + 0.022, y, label[:32], transform=ax.transAxes, fontsize=6.1, va="center")


def add_population_legend_pages(
    pdf_pages: Any,
    rows: list[dict[str, Any]],
    group_order: list[str],
    pop_order: list[str],
    styles: Any,
    config: dict[str, Any],
    project: str,
) -> None:
    """Add population legend pages to a PDF file."""
    if not HAS_MATPLOTLIB:
        return
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    fig.patch.set_facecolor("white")
    draw_population_legend_axes(ax, rows, group_order, pop_order, styles, config)
    pdf_pages.savefig(fig)
    plt.close(fig)
