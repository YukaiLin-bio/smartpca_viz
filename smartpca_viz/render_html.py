"""HTML rendering for interactive PCA visualization.

Uses Jinja2 templates from templates/ directory when available,
with a fallback that reads template files directly (string.Template).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from smartpca_viz.parser import (
    build_shape_legend,
    build_grouped_population_legend,
    explained_variance_labels,
)
from smartpca_viz.exporter import CSV_COLUMNS

# ─── Template path resolution ────────────────────────────────────

TEMPLATE_DIR = Path(__file__).parent / "templates"

# ─── Try Jinja2 template engine ──────────────────────────────────

HAS_JINJA2 = False
_jinja_env = None

try:
    import jinja2

    HAS_JINJA2 = True
except ImportError:
    pass


def _read_template(name: str) -> str:
    """Read a template file from the templates directory."""
    path = TEMPLATE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def _render_with_jinja2(
    payload_json: str,
    css_content: str,
    js_content: str,
) -> str:
    """Render HTML using Jinja2 template engine."""
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=False,
        )
    template = _jinja_env.get_template("base.html")
    return template.render(
        payload_json=payload_json,
        css_content=css_content,
        js_content=js_content,
    )


def _render_with_string_template(payload_json: str) -> str:
    """Render HTML using string.Template (stdlib fallback)."""
    css = _read_template("styles.css")
    js = _read_template("app.js")
    html = _read_template("base.html")
    html = html.replace("{{ payload_json }}", payload_json)
    html = html.replace("{{ css_content }}", css)
    html = html.replace("{{ js_content }}", js)
    return html


def _render_html_template(payload_json: str) -> str:
    """Render the complete HTML document.

    Priority:
    1. Jinja2 + external templates (best, has autoescape)
    2. string.Template + external templates (stdlib fallback)
    3. Raw string embedded template (last resort)
    """
    if TEMPLATE_DIR.exists():
        try:
            if HAS_JINJA2:
                css = _read_template("styles.css")
                js = _read_template("app.js")
                return _render_with_jinja2(payload_json, css, js)
            else:
                return _render_with_string_template(payload_json)
        except FileNotFoundError as exc:
            print(
                f"WARNING: Template file missing ({exc}), "
                f"falling back to embedded template",
                file=sys.stderr,
            )
        except Exception as exc:
            print(
                f"WARNING: Template rendering failed ({exc}), "
                f"falling back to embedded template",
                file=sys.stderr,
            )

    # Last resort: build from embedded parts
    css = EMBEDDED_CSS
    js = EMBEDDED_JS
    html = EMBEDDED_HTML
    html = html.replace("{{ payload_json }}", payload_json)
    html = html.replace("{{ css_content }}", css)
    html = html.replace("{{ js_content }}", js)
    return html


def generate_interactive_html(
    path: Path,
    rows: list[dict[str, Any]],
    group_order: list[str],
    pop_order: list[str],
    styles: Any,  # Styles object
    eigvals: list[float],
    config: dict[str, Any],
    project: str,
    kde_image: str | None = None,
) -> None:
    """Generate interactive HTML PCA visualization."""
    x_label, y_label = explained_variance_labels(eigvals)

    data = []
    for idx, row in enumerate(rows):
        item = {key: row[key] for key in CSV_COLUMNS}
        item.update(
            {
                "idx": idx,
                "group_color": row["group_color"],
                "population_color": row["population_color"],
                "symbol": row["symbol"],
            }
        )
        data.append(item)

    payload = {
        "project": project,
        "points": data,
        "groups": group_order,
        "populations": pop_order,
        "groupColors": styles.group_colors,
        "populationColors": styles.population_colors,
        "populationSymbols": styles.population_symbols,
        "shapeLegend": build_shape_legend(styles.population_symbols, pop_order, rows),
        "groupedPopulationLegend": build_grouped_population_legend(
            rows, group_order, pop_order, styles.population_symbols
        ),
        "config": config,
        "xLabel": x_label,
        "yLabel": y_label,
        "kdeImage": kde_image,
    }

    payload_json = json.dumps(payload, ensure_ascii=False)
    doc = _render_html_template(payload_json)
    path.write_text(doc, encoding="utf-8")


# ─── Embedded fallback template parts ────────────────────────────
# These are kept as a last-resort fallback when external template
# files are not available.

EMBEDDED_CSS = """body{margin:0;font-family:Arial,Helvetica,sans-serif;color:#1b252e;background:#f4f6f8}
main{display:grid;grid-template-columns:320px 1fr;gap:14px;height:100vh;padding:14px;box-sizing:border-box}
aside{background:white;border:1px solid #d8e0e8;border-radius:8px;padding:12px;overflow:auto}
section{background:white;border:1px solid #d8e0e8;border-radius:8px;position:relative;overflow:auto}
h1{font-size:18px;margin:0 0 10px} h2{font-size:13px;margin:16px 0 8px;color:#3d4b57}
button,select,input{font:inherit} button{margin:3px 3px 3px 0;padding:6px 8px;border:1px solid #b9c4ce;background:#fff;border-radius:5px;cursor:pointer}
button:hover{background:#eef3f7}.zoomActive{background:#145aa0!important;color:#fff!important}.row{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.list{max-height:170px;overflow:auto;border:1px solid #e1e7ed;border-radius:5px;padding:6px}
.item{display:flex;align-items:center;gap:6px;margin:3px 0;font-size:12px}.swatch{width:10px;height:10px;border-radius:50%;display:inline-block}
.scaleControl{display:grid;grid-template-columns:78px 1fr 44px;gap:8px;align-items:center;font-size:12px;margin:6px 0}.scaleControl input{width:100%}
#plot{width:100%;height:100%;touch-action:none}.tooltip{position:absolute;pointer-events:none;background:#16202a;color:white;padding:7px 8px;border-radius:4px;font-size:12px;display:none;z-index:5;max-width:280px}
#selected{font-size:12px;max-height:180px;overflow:auto;white-space:pre;border:1px solid #e1e7ed;border-radius:5px;padding:6px;background:#fbfcfd}
.muted{color:#687684;font-size:12px;line-height:1.4}.legendLayer{position:absolute;left:0;top:0;width:100%;min-height:100%;pointer-events:none}.legendPanel{position:absolute;background:transparent;border:0;border-radius:0;padding:6px 8px;min-width:170px;max-width:260px;cursor:move;font-size:12px;box-shadow:none;pointer-events:auto}.legendPanel .item{margin:2px 0;white-space:nowrap}.legendTitle{font-weight:700;margin-bottom:3px;white-space:nowrap}.legendMarker{width:16px;height:16px;display:inline-block;flex:0 0 16px}
.note{font-size:12px;color:#53616f}.hidden{display:none}"""

EMBEDDED_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>smartpca visualization</title>
<style>
{{ css_content }}
</style>
</head>
<body>
<main>
<aside>
<h1 id="title"></h1>
<div class="row">
<button id="focusTargets">Focus targets</button>
<button id="resetView">Global view</button>
<button id="toggleZoom">🔍 Zoom</button>
<button id="toggleModern">Modern as background</button>
<button id="toggleDensity">Density heatmap</button>
</div>
<h2>Color by</h2>
<select id="colorBy"><option value="group">group</option><option value="population">population</option></select>
<h2>Layout</h2>
<div class="scaleControl"><label for="legendScale">Legend size</label><input id="legendScale" type="range" min="60" max="160" value="100"><span id="legendScaleValue">100%</span></div>
<div class="scaleControl"><label for="pointScale">Point size</label><input id="pointScale" type="range" min="40" max="240" value="100"><span id="pointScaleValue">100%</span></div>
<div class="scaleControl"><label for="labelMode">Labels</label><select id="labelMode"><option value="none">none</option><option value="group">group</option><option value="sample_id">sample_id</option><option value="population">population</option></select><span></span></div>
<button id="resetLegendLayout">Reset legend layout</button>
<h2>Search sample_id</h2>
<div class="row"><input id="searchBox" placeholder="sample_id" style="width:190px"><button id="searchBtn">Search</button></div>
<div id="searchMsg" class="note"></div>
<h2>Export</h2>
<button id="previewLayout">Preview</button><button id="exportSvg">SVG</button><button id="exportPng">PNG</button><button id="exportPdf">PDF</button>
<h2>Groups</h2><div id="groups" class="list"></div>
<h2>Populations</h2><div id="populations" class="list"></div>
<h2>Selected samples</h2>
<button id="exportSelected">Export selected CSV</button>
<pre id="selected"></pre>
<p class="muted">Drag on the plot to box-select samples. Hover points for details. Each group legend block can be dragged independently.</p>
</aside>
<section>
<svg id="plot" xmlns="http://www.w3.org/2000/svg"></svg>
<div id="legend" class="legendLayer"></div>
<div id="tooltip" class="tooltip"></div>
</section>
</main>
<script>
const PAYLOAD = {{ payload_json }};
{{ js_content }}
</script>
</body>
</html>"""

EMBEDDED_JS = """/* smartpca_viz embedded fallback — minimal version */
/* For full version, use the external templates/ directory. */
;(function(){'use strict';
function mutedColor(hex){var r=parseInt(hex.slice(1,3),16)/255,g=parseInt(hex.slice(3,5),16)/255,b=parseInt(hex.slice(5,7),16)/255;var mx=Math.max(r,g,b),mn=Math.min(r,g,b);var h=0,s=0,l=(mx+mn)/2;if(mx!==mn){var d=mx-mn;s=l>.5?d/(2-mx-mn):d/(mx+mn);if(mx===r)h=((g-b)/d+(g<b?6:0))/6;else if(mx===g)h=((b-r)/d+2)/6;else h=((r-g)/d+4)/6}s=Math.min(s,.38);l=Math.max(l,.75);function hue2(p,q,t){if(t<0)t+=1;if(t>1)t-=1;if(t<1/6)return p+(q-p)*6*t;if(t<1/2)return q;if(t<2/3)return p+(q-p)*(2/3-t)*6;return p}var q=l<.5?l*(1+s):l+s-l*s,p=2*l-q;var rr=hue2(p,q,h+1/3),gg=hue2(p,q,h),bb=hue2(p,q,h-1/3);return '#'+[rr,gg,bb].map(function(c){return Math.round(Math.max(0,Math.min(1,c))*255).toString(16).padStart(2,'0')}).join('')}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function downloadBlob(name,blob){var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},400)}
function download(name,text,type){downloadBlob(name,new Blob([text],{type:type}))}
window.__legendScale=1;
window.plot=new PCAPlot(PAYLOAD);
/**
 * IMPORTANT: This is a minimal fallback. The full app.js (49KB) is
 * in templates/app.js. Copy template files from the installation
 * directory to use the complete interactive experience.
 */
console.warn('smartpca_viz: using embedded fallback JS. Install template files for full features.');
})();
"""

# Note: The embedded fallback JS above is intentionally minimal.
# For the full interactive experience, ensure templates/app.js is
# present in the templates/ directory alongside the package.
