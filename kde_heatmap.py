#!/usr/bin/env python3
"""Extend smartpca_viz.py with KDE density heatmap for modern background."""

import base64
import io
import sys

import numpy as np
from scipy import stats


def compute_kde_base64(rows, config):
    """Compute KDE heatmap for modern background points, return base64 PNG or None."""
    modern = [row for row in rows if row.get("is_modern_background") and not row.get("is_target")]
    if len(modern) < 5:
        return None

    xs = np.array([float(row["PC1"]) for row in modern])
    ys = np.array([float(row["PC2"]) for row in modern])

    # plot bounds via smartpca_viz.bounds
    from smartpca_viz import bounds as viz_bounds
    min_x, max_x, min_y, max_y = viz_bounds(rows)

    grid_size = 200
    xi = np.linspace(min_x, max_x, grid_size)
    yi = np.linspace(min_y, max_y, grid_size)
    X, Y = np.meshgrid(xi, yi)

    try:
        kde = stats.gaussian_kde([xs, ys], bw_method=0.25)
        zi = kde([X.ravel(), Y.ravel()]).reshape(grid_size, grid_size)
    except Exception as exc:
        print(f"WARNING: KDE computation failed: {exc}", file=sys.stderr)
        return None

    # Log-transform for better visual dynamic range
    zi = np.log1p(zi)
    zi = (zi - zi.min()) / (zi.max() - zi.min() + 1e-10)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    # Semi-transparent blue-white gradient
    colors = [(1, 1, 1, 0), (0.2, 0.4, 0.7, 0.08), (0.1, 0.3, 0.6, 0.40)]
    cmap = LinearSegmentedColormap.from_list("kde", colors)

    fig, ax = plt.subplots(figsize=(grid_size / 100, grid_size / 100), dpi=100)
    ax.imshow(
        zi, extent=[min_x, max_x, min_y, max_y],
        origin="lower", cmap=cmap, aspect="auto",
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
