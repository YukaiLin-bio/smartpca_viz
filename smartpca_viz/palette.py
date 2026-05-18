"""Color palettes and symbol list for smartpca visualization.

Nature-publication-grade color schemes.
Uses colorblind-safe palettes inspired by:
- Tol (Paul Tol, SRON) — 12-color scheme for Nature Communications
- Wong (Bang Wong, Nature Methods) — colorblind-friendly palette
- IBM Carbon Design color tokens
"""

from __future__ import annotations

from typing import Any

# ─── Nature-grade group palette ────────────────────────────────────
# Colorblind-safe, publication-quality colors.
# Based on Tol's 12-color scheme + extended with Wong / IBM / custom muted colors.
# Suitable for up to ~30 groups. Saturation is deliberately modest.

GROUP_PALETTE = [
    # Tol bright (Nature Communications default) — 12 colors
    "#EE7733",  # Orange
    "#0077BB",  # Blue
    "#33BBEE",  # Cyan
    "#EE3377",  # Magenta
    "#CC3311",  # Red
    "#009988",  # Teal
    "#BBBBBB",  # Grey
    "#000000",  # Black
    "#66CCEE",  # Light cyan
    "#CCBB44",  # Yellow-olive
    "#AA3377",  # Purple
    "#228833",  # Green
    # Extended with Wong palette colors
    "#56B4E9",  # Sky blue
    "#E69F00",  # Gold
    "#F0E442",  # Yellow
    "#D55E00",  # Vermillion
    "#CC79A7",  # Pink
    "#0072B2",  # Dark blue
    "#009E73",  # Bluish green
    # Additional muted colors for more groups
    "#6699CC",  # Steel blue
    "#994455",  # Maroon
    "#997700",  # Olive
    "#882255",  # Wine red
    "#44AA99",  # Sea green
    "#DDCC77",  # Sand
    "#332288",  # Indigo
    "#AA4466",  # Rose
    "#44AA88",  # Jade
    "#DDAA77",  # Tan
]

POP_PALETTE = [
    "#4477AA",
    "#EE6677",
    "#228833",
    "#CCBB44",
    "#66CCEE",
    "#AA3377",
    "#BBBBBB",
    "#332288",
    "#6699CC",
    "#994455",
    "#997700",
    "#117733",
    "#882255",
    "#44AA99",
    "#DDCC77",
    "#56B4E9",
    "#E69F00",
    "#D55E00",
    "#CC79A7",
    "#0072B2",
]

SYMBOLS = ["circle", "square", "triangle", "diamond", "cross", "x", "pentagon", "hexagon"]

# ─── Modern background color (single muted tone) ──────────────────
MODERN_BACKGROUND_COLOR = "#B0B8C4"  # Neutral grey-blue, minimal visual weight


def muted_color(hex_color: str, strength: float = 1.0) -> str:
    """Reduce saturation and increase lightness for background rendering.

    Args:
        hex_color: Hex color string (e.g. "#4477AA")
        strength: How much to mute (0.0 = fully grey, 1.0 = muted preserving hint of original)

    Returns muted hex color string.
    """
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255

    mx = max(r, g, b)
    mn = min(r, g, b)
    l = (mx + mn) / 2

    if mx == mn:
        s = 0.0
        h = 0.0
    else:
        d = mx - mn
        s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h = ((g - b) / d + (g < b and 6 or 0)) / 6
        elif mx == g:
            h = ((b - r) / d + 2) / 6
        else:
            h = ((r - g) / d + 4) / 6

    # Mute more aggressively for Nature style
    s = min(s, 0.28 * strength)
    l = max(l, 0.78 + (1.0 - strength) * 0.10)

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

    rr = hue2(p, q, h + 1 / 3)
    gg = hue2(p, q, h)
    bb = hue2(p, q, h - 1 / 3)

    r_out = max(0, min(1, rr))
    g_out = max(0, min(1, gg))
    b_out = max(0, min(1, bb))

    return "#" + "".join(
        f"{round(c * 255):02x}" for c in (r_out, g_out, b_out)
    )


def nature_modern_color(group_color: str) -> str:
    """Generate a very muted background color for modern groups in Nature style.

    Low saturation, high lightness — barely discernible hue hint.
    """
    return muted_color(group_color, strength=0.3)


def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color (#RRGGBB) to (R, G, B) in 0-1 range."""
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        return 0.5, 0.5, 0.5
    return int(value[0:2], 16) / 255, int(value[2:4], 16) / 255, int(value[4:6], 16) / 255


def sanitize_prefix(value: str) -> str:
    """Sanitize a string for use as a filename prefix."""
    import re

    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned or "smartpca_viz"
