"""Color palettes and symbol list for smartpca visualization."""

from __future__ import annotations

from typing import Any

GROUP_PALETTE = [
    "#4477AA",
    "#EE6677",
    "#228833",
    "#CCBB44",
    "#66CCEE",
    "#AA3377",
    "#BBBBBB",
    "#000000",
    "#994455",
    "#997700",
    "#117733",
    "#882255",
    "#44AA99",
    "#DDCC77",
    "#332288",
    "#6699CC",
    "#AA4466",
    "#44AA88",
    "#DDAA77",
    "#6688AA",
    "#AA7744",
    "#88CCAA",
    "#CC6677",
    "#777711",
    "#1177AA",
    "#AA1177",
    "#77AA11",
    "#CC99BB",
    "#99AACC",
    "#AACC99",
]

POP_PALETTE = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
    "#3366cc",
    "#dc3912",
    "#109618",
    "#990099",
    "#0099c6",
    "#dd4477",
    "#e67320",
    "#329262",
    "#5577aa",
    "#cc3344",
]

SYMBOLS = ["circle", "square", "triangle", "diamond", "cross", "x", "pentagon", "hexagon"]


def muted_color(hex_color: str) -> str:
    """Reduce saturation and increase lightness of a hex color for background rendering."""
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

    rr = hue2(p, q, h + 1 / 3)
    gg = hue2(p, q, h)
    bb = hue2(p, q, h - 1 / 3)

    r_out = max(0, min(1, rr))
    g_out = max(0, min(1, gg))
    b_out = max(0, min(1, bb))

    return "#" + "".join(
        f"{round(c * 255):02x}" for c in (r_out, g_out, b_out)
    )


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
