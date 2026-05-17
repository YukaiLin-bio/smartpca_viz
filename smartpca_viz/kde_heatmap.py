"""KDE density heatmap for modern background visualization.

Computes per-group KDE heatmaps, each colored with that group's muted color,
so density overlays visually align with modern background text labels.

Gracefully degrades if scipy or matplotlib is not available.
"""

from __future__ import annotations

import base64
import io
import sys
from collections import OrderedDict
from typing import Any

# ─── Graceful degradation ────────────────────────────────────────

HAS_SCIPY = False
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from scipy import stats

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

HAS_MATPLOTLIB = False
try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    HAS_MATPLOTLIB = True
except ImportError:
    pass


def _muted_color(hex_color: str) -> tuple[float, float, float]:
    """Desaturate and lighten a hex color, returning (R, G, B) in 0-1 range."""
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return (r, g, b)  # gray, return as-is
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    # Reduce saturation and increase lightness
    s = min(s, 0.38)
    l = max(l, 0.75)

    def hue2(p, q, t):
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    # Determine hue from original color
    if mx == r:
        h = ((g - b) / d + (g < b and 6 or 0)) / 6
    elif mx == g:
        h = ((b - r) / d + 2) / 6
    else:
        h = ((r - g) / d + 4) / 6

    return (
        max(0, min(1, hue2(p, q, h + 1 / 3))),
        max(0, min(1, hue2(p, q, h))),
        max(0, min(1, hue2(p, q, h - 1 / 3))),
    )


def compute_kde_base64(rows: list[dict[str, Any]], config: dict[str, Any]) -> str | None:
    """Compute per-group KDE heatmap for modern background points.

    Each modern group gets its own KDE rendered in that group's muted color.
    Returns base64-encoded PNG, or None if computation fails.
    """
    if not HAS_SCIPY or not HAS_NUMPY or not HAS_MATPLOTLIB:
        missing = []
        if not HAS_SCIPY:
            missing.append("scipy")
        if not HAS_NUMPY:
            missing.append("numpy")
        if not HAS_MATPLOTLIB:
            missing.append("matplotlib")
        print(
            f"WARNING: {', '.join(missing)} not installed, skipping KDE heatmap",
            file=sys.stderr,
        )
        return None

    import numpy as np

    modern = [row for row in rows if row.get("is_modern_background") and not row.get("is_target")]
    if len(modern) < 5:
        return None

    # Group modern points by group
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

    # Render per-group KDE on a single figure
    fig, ax = plt.subplots(figsize=(grid_size / 100, grid_size / 100), dpi=100)

    for gname, gpoints in groups.items():
        if len(gpoints) < 5:
            continue

        xs = np.array([float(row["PC1"]) for row in gpoints])
        ys = np.array([float(row["PC2"]) for row in gpoints])

        try:
            kde = stats.gaussian_kde([xs, ys], bw_method=0.25)
            zi = kde([X.ravel(), Y.ravel()]).reshape(grid_size, grid_size)
        except Exception as exc:
            print(f"WARNING: KDE failed for group {gname}: {exc}", file=sys.stderr)
            continue

        # Log-transform
        zi = np.log1p(zi)
        zi = (zi - zi.min()) / (zi.max() - zi.min() + 1e-10)

        # Get group's muted color
        group_color = gpoints[0].get("group_color", "#6699CC")
        muted_rgb = _muted_color(group_color)

        # Build single-hue colormap: transparent → muted_color
        colors = [
            (1, 1, 1, 0),  # fully transparent at low density
            (muted_rgb[0], muted_rgb[1], muted_rgb[2], 0.10),  # faint at mid
            (muted_rgb[0], muted_rgb[1], muted_rgb[2], 0.35),  # stronger at peak
        ]
        cmap = LinearSegmentedColormap.from_list(f"kde_{gname}", colors)

        ax.imshow(
            zi,
            extent=[min_x, max_x, min_y, max_y],
            origin="lower",
            cmap=cmap,
            aspect="auto",
        )

    ax.set_xlim(min_x, max_x)
    ax.set_ylim(min_y, max_y)
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, dpi=100, pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()
