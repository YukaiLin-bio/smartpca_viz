"""Minimal PDF rendering for PCA plots and reports."""

from __future__ import annotations

import html
import math
import sys
import os
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from smartpca_viz.palette import hex_to_rgb
from smartpca_viz.parser import (
    bounds,
    explained_variance_labels,
    build_grouped_population_legend,
)
from smartpca_viz.render_matplotlib import (
    generate_publication_pdf_matplotlib,
    MARKER_MAP,
    HAS_MATPLOTLIB,
)


# ─── Simple PDF (minimal, no deps) ──────────────────────────────


class SimplePDF:
    """Minimal PDF writer with no external dependencies."""

    def __init__(self) -> None:
        self.pages: list[tuple[float, float, list[str]]] = []
        self.current: list[str] = []
        self.width = 612.0
        self.height = 792.0

    def new_page(self, width: float = 612.0, height: float = 792.0) -> None:
        if self.current:
            self.pages.append((self.width, self.height, self.current))
        self.width = width
        self.height = height
        self.current = []

    def finish(self) -> None:
        if self.current:
            self.pages.append((self.width, self.height, self.current))
            self.current = []

    def raw(self, cmd: str) -> None:
        self.current.append(cmd)

    def color(self, hex_color: str) -> None:
        r, g, b = hex_to_rgb(hex_color)
        self.raw(f"{r:.3f} {g:.3f} {b:.3f} rg {r:.3f} {g:.3f} {b:.3f} RG")

    def alpha_note(self, _alpha: float) -> None:
        return

    def text(self, x: float, y: float, value: str, size: float = 10, bold: bool = False) -> None:
        font = "/F2" if bold else "/F1"
        escaped = pdf_escape(value)
        self.raw(f"BT {font} {size:.1f} Tf {x:.2f} {y:.2f} Td ({escaped}) Tj ET")

    def line(self, x1: float, y1: float, x2: float, y2: float, width: float = 0.8) -> None:
        self.raw(f"{width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def circle(self, x: float, y: float, r: float, fill: bool = True) -> None:
        c = 0.5522847498 * r
        self.raw(
            f"{x+r:.2f} {y:.2f} m {x+r:.2f} {y+c:.2f} {x+c:.2f} {y+r:.2f} {x:.2f} {y+r:.2f} c "
            f"{x-c:.2f} {y+r:.2f} {x-r:.2f} {y+c:.2f} {x-r:.2f} {y:.2f} c "
            f"{x-c:.2f} {y-r:.2f} {x-c:.2f} {y-r:.2f} {x:.2f} {y-r:.2f} c "
            f"{x+c:.2f} {y-r:.2f} {x+r:.2f} {y-c:.2f} {x+r:.2f} {y:.2f} c {'f' if fill else 'S'}"
        )

    def rect(self, x: float, y: float, w: float, h: float, fill: bool = True) -> None:
        self.raw(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {'f' if fill else 'S'}")

    def polygon(self, pts: list[tuple[float, float]], fill: bool = True) -> None:
        if not pts:
            return
        cmds = [f"{pts[0][0]:.2f} {pts[0][1]:.2f} m"]
        cmds.extend(f"{x:.2f} {y:.2f} l" for x, y in pts[1:])
        cmds.append("h")
        cmds.append("f" if fill else "S")
        self.raw(" ".join(cmds))

    def save(self, path: Path) -> None:
        self.finish()
        objects: list[bytes] = []
        catalog_id = 1
        pages_id = 2
        font1_id = 3
        font2_id = 4
        next_id = 5
        page_ids = []
        content_ids = []
        for _page in self.pages:
            page_ids.append(next_id)
            content_ids.append(next_id + 1)
            next_id += 2
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join(f"{pid} 0 R" for pid in page_ids)
        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode())
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        for (width, height, commands), page_id, content_id in zip(self.pages, page_ids, content_ids):
            resources = "<< /Font << /F1 3 0 R /F2 4 0 R >> >>"
            page_obj = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width:.2f} {height:.2f}] "
                f"/Resources {resources} /Contents {content_id} 0 R >>"
            )
            stream = "\n".join(commands).encode("latin-1", "replace")
            content_obj = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
            objects.append(page_obj.encode())
            objects.append(content_obj)
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for idx, obj in enumerate(objects, 1):
            offsets.append(len(out))
            out.extend(f"{idx} 0 obj\n".encode())
            out.extend(obj)
            out.extend(b"\nendobj\n")
        xref = len(out)
        out.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
        for offset in offsets[1:]:
            out.extend(f"{offset:010d} 00000 n \n".encode())
        out.extend(
            f"trailer\n<< /Size {len(objects)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        )
        path.write_bytes(out)


# ─── PDF helpers ─────────────────────────────────────────────────


def pdf_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def plot_transform(
    rows: list[dict[str, Any]], x0: float, y0: float, w: float, h: float
) -> tuple:
    min_x, max_x, min_y, max_y = bounds(rows)

    def tx(x: float) -> float:
        return x0 + (x - min_x) / (max_x - min_x) * w

    def ty(y: float) -> float:
        return y0 + (y - min_y) / (max_y - min_y) * h

    return tx, ty


def draw_marker_pdf(
    pdf: SimplePDF, row: dict[str, Any], x: float, y: float, r: float, color: str, target: bool = False
) -> None:
    pdf.color(color)
    symbol = "star" if target else row.get("symbol", "circle")
    if symbol == "square":
        pdf.rect(x - r, y - r, 2 * r, 2 * r, True)
    elif symbol == "triangle":
        pdf.polygon([(x, y + r), (x - r, y - r), (x + r, y - r)], True)
    elif symbol == "diamond":
        pdf.polygon([(x, y + r), (x - r, y), (x, y - r), (x + r, y)], True)
    elif symbol == "star":
        pts = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            rr = r * 1.35 if i % 2 == 0 else r * 0.55
            pts.append((x + math.cos(angle) * rr, y + math.sin(angle) * rr))
        pdf.polygon(pts, True)
        pdf.color("#000000")
        pdf.polygon(pts, False)
    else:
        pdf.circle(x, y, r, True)


# ─── Publication PDF ─────────────────────────────────────────────


def generate_publication_pdf(
    path: Path,
    rows: list[dict[str, Any]],
    group_order: list[str],
    pop_order: list[str],
    styles: Any,
    eigvals: list[float],
    config: dict[str, Any],
    project: str,
) -> None:
    """Generate publication-quality PDF. Tries matplotlib first, falls back to SimplePDF."""
    if generate_publication_pdf_matplotlib(
        path, rows, group_order, pop_order, styles, eigvals, config, project
    ):
        return

    # Fallback: SimplePDF
    pdf = SimplePDF()
    width = float(config.get("pdf_width_in", 8.0)) * 72
    height = float(config.get("pdf_height_in", 6.5)) * 72
    pdf.new_page(width, height)
    pdf.color("#FFFFFF")
    pdf.rect(0, 0, width, height, True)
    pdf.color("#111111")
    pdf.text(36, height - 32, f"{project}: PCA (PC1 vs PC2)", 12, True)
    x0, y0, w, h = 58, 58, width - 210, height - 118
    pdf.color("#111111")
    pdf.line(x0, y0, x0 + w, y0, 0.8)
    pdf.line(x0, y0, x0, y0 + h, 0.8)
    tx, ty = plot_transform(rows, x0, y0, w, h)
    point_size = float(config.get("point_size", 5.0))

    normal = [row for row in rows if not row["is_target"]]
    targets = [row for row in rows if row["is_target"]]
    normal.sort(key=lambda row: 0 if row["is_modern_background"] else 1)

    for row in normal:
        if row["is_modern_background"]:
            c = config.get("modern_background_color", "#B8B8B8")
            r = point_size * float(config.get("modern_background_size_multiplier", 0.75))
        else:
            c = row["group_color"]
            r = point_size
        draw_marker_pdf(pdf, row, tx(row["PC1"]), ty(row["PC2"]), r, c)

    for row in targets:
        draw_marker_pdf(
            pdf,
            row,
            tx(row["PC1"]),
            ty(row["PC2"]),
            point_size * float(config.get("target_size_multiplier", 1.8)),
            config.get("target_color", "#D81B60"),
            True,
        )
        if config.get("label_targets", True):
            pdf.color("#111111")
            pdf.text(
                tx(row["PC1"]) + 7,
                ty(row["PC2"]) + 7,
                row["target_label"] or row["sample_id"],
                7,
                True,
            )

    x_label, y_label = explained_variance_labels(eigvals)
    pdf.color("#111111")
    pdf.text(x0 + w / 2 - 32, 24, x_label, 9)
    pdf.text(12, y0 + h / 2, y_label, 9)

    legend_x = x0 + w + 22
    legend_y = height - 70
    pdf.text(legend_x, legend_y, "Group colors", 9, True)
    y = legend_y - 15
    for group in group_order[:22]:
        if group in set(row["group"] for row in rows):
            pdf.color(styles.group_colors.get(group, "#999999"))
            pdf.circle(legend_x + 4, y + 3, 3, True)
            pdf.color("#111111")
            pdf.text(legend_x + 12, y, group[:24], 6.5)
            y -= 10
    y -= 8
    pdf.text(legend_x, y, "Population shapes", 9, True)
    y -= 14
    for pop in pop_order[:22]:
        if pop in set(row["population"] for row in rows):
            draw_marker_pdf(pdf, {"symbol": styles.population_symbols.get(pop, "circle")}, legend_x + 4, y + 3, 3, "#555555")
            pdf.color("#111111")
            pdf.text(legend_x + 12, y, pop[:24], 6.3)
            y -= 9
            if y < 30:
                break
    pdf.save(path)


# ─── Report PDF ──────────────────────────────────────────────────


def generate_report_pdf(
    path: Path,
    plot_pdf_path: Path,
    rows: list[dict[str, Any]],
    group_order: list[str],
    pop_order: list[str],
    input_paths: dict[str, Any],
    output_files: list[Path],
    config: dict[str, Any],
    project: str,
) -> None:
    """Generate report PDF. Tries reportlab first, falls back to SimplePDF."""
    if generate_report_pdf_reportlab(
        path, rows, group_order, pop_order, input_paths, output_files, config, project
    ):
        return

    pdf = SimplePDF()
    pdf.new_page(612, 792)
    pdf.color("#FFFFFF")
    pdf.rect(0, 0, 612, 792, True)
    pdf.color("#111111")
    pdf.text(42, 748, f"{project} smartpca visualization report", 16, True)
    pdf.text(42, 724, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 9)
    y = 694
    pdf.text(42, y, "Input files", 12, True)
    y -= 18
    for key, value in input_paths.items():
        if value:
            pdf.text(54, y, f"{key}: {value}", 8)
            y -= 12
    y -= 8
    pdf.text(42, y, "Summary", 12, True)
    y -= 18
    stats = [
        ("Samples", len(rows)),
        ("Populations", len(set(row["population"] for row in rows))),
        ("Groups", len(set(row["group"] for row in rows))),
        ("Targets", sum(1 for row in rows if row["is_target"])),
        ("Unknown group samples", sum(1 for row in rows if row["group"] == "Unknown")),
        ("Modern background samples", sum(1 for row in rows if row["is_modern_background"])),
    ]
    for label, value in stats:
        pdf.text(54, y, f"{label}: {value}", 9)
        y -= 13
    y -= 8
    pdf.text(42, y, "Configuration", 12, True)
    y -= 18
    for key in ["color_by", "modern_background", "label_targets", "target_shape", "pdf_style"]:
        pdf.text(54, y, f"{key}: {config.get(key)}", 8)
        y -= 12
    y -= 8
    pdf.text(42, y, "Output files", 12, True)
    y -= 18
    for out in output_files:
        pdf.text(54, y, str(out), 7)
        y -= 10
        if y < 50:
            break
    pdf.text(42, 40, f"Publication plot PDF: {plot_pdf_path.name}", 8)

    pdf.new_page(612, 792)
    pdf.color("#FFFFFF")
    pdf.rect(0, 0, 612, 792, True)
    pdf.color("#111111")
    pdf.text(42, 748, "Group sample counts", 13, True)
    y = 724
    group_counts = Counter(row["group"] for row in rows)
    for group in group_order:
        if group in group_counts:
            pdf.text(54, y, f"{group}: {group_counts[group]}", 8)
            y -= 11
            if y < 50:
                break
    pdf.text(320, 748, "Population sample counts", 13, True)
    y = 724
    pop_counts = Counter(row["population"] for row in rows)
    for pop in pop_order:
        if pop in pop_counts:
            pdf.text(332, y, f"{pop}: {pop_counts[pop]}", 7)
            y -= 9
            if y < 50:
                break
    pdf.save(path)


# ─── Report PDF (reportlab) ──────────────────────────────────────


HAS_REPORTLAB = False
try:
    from reportlab.lib import colors  # noqa: F401
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    HAS_REPORTLAB = True
except ImportError:
    pass


def generate_report_pdf_reportlab(
    path: Path,
    rows: list[dict[str, Any]],
    group_order: list[str],
    pop_order: list[str],
    input_paths: dict[str, Any],
    output_files: list[Path],
    config: dict[str, Any],
    project: str,
) -> bool:
    """Generate report PDF using reportlab. Returns True if successful."""
    global HAS_REPORTLAB  # noqa: PLW0602
    if not HAS_REPORTLAB:
        return False

    direct_imports: Any = None
    try:
        import importlib

        direct_imports = importlib.import_module("reportlab.lib.colors")
    except Exception:
        HAS_REPORTLAB = False
        return False

    tmp_png = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            tmp_png = Path(handle.name)

        styles_for_plot = {
            "group_colors": {row["group"]: row.get("group_color", "#999999") for row in rows},
            "population_symbols": {row["population"]: row.get("symbol", "circle") for row in rows},
        }

        generate_publication_pdf_matplotlib(
            path.with_suffix(".report_plot_tmp.pdf"),
            rows,
            group_order,
            pop_order,
            styles_for_plot,  # type: ignore[arg-type]
            [],
            config,
            project,
            png_path=tmp_png,
        )

        doc = SimpleDocTemplate(
            str(path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
        )
        styles = getSampleStyleSheet()
        story = []
        story.append(
            Paragraph(f"{html.escape(project)} smartpca visualization report", styles["Title"])
        )
        story.append(
            Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]
            )
        )
        story.append(Spacer(1, 0.18 * inch))

        summary = [
            ["Metric", "Value"],
            ["Samples", str(len(rows))],
            ["Populations", str(len(set(row["population"] for row in rows)))],
            ["Groups", str(len(set(row["group"] for row in rows)))],
            ["Targets", str(sum(1 for row in rows if row["is_target"]))],
            ["Unknown group samples", str(sum(1 for row in rows if row["group"] == "Unknown"))],
            [
                "Modern background samples",
                str(sum(1 for row in rows if row["is_modern_background"])),
            ],
        ]
        story.append(Paragraph("Summary", styles["Heading2"]))
        story.append(_reportlab_table(summary, direct_imports))
        story.append(Spacer(1, 0.14 * inch))

        input_table = [["Input", "Path"]]
        for key, value in input_paths.items():
            if value:
                input_table.append([key, str(value)])
        story.append(Paragraph("Input files", styles["Heading2"]))
        story.append(
            _reportlab_table(input_table, direct_imports, col_widths=[1.2 * inch, 5.2 * inch])
        )
        story.append(Spacer(1, 0.14 * inch))

        if tmp_png and tmp_png.exists() and tmp_png.stat().st_size > 0:
            story.append(Paragraph("PC1 vs PC2 plot", styles["Heading2"]))
            story.append(
                Image(str(tmp_png), width=6.6 * inch, height=5.2 * inch, kind="proportional")
            )

        story.append(PageBreak())
        story.append(Paragraph("Group sample counts", styles["Heading2"]))
        group_counts = Counter(row["group"] for row in rows)
        group_table = [["Group", "N"]] + [
            [group, str(group_counts[group])] for group in group_order if group in group_counts
        ]
        story.append(
            _reportlab_table(group_table, direct_imports, col_widths=[4.5 * inch, 1.0 * inch])
        )
        story.append(Spacer(1, 0.18 * inch))

        story.append(Paragraph("Population sample counts", styles["Heading2"]))
        pop_counts = Counter(row["population"] for row in rows)
        pop_table = [["Population", "N"]] + [
            [pop, str(pop_counts[pop])] for pop in pop_order if pop in pop_counts
        ]
        story.append(
            _reportlab_table(pop_table, direct_imports, col_widths=[4.5 * inch, 1.0 * inch])
        )

        story.append(PageBreak())
        story.append(Paragraph("Parameters", styles["Heading2"]))
        config_table = [["Parameter", "Value"]] + [[key, str(value)] for key, value in config.items()]
        story.append(
            _reportlab_table(config_table, direct_imports, col_widths=[2.5 * inch, 3.8 * inch])
        )
        story.append(Spacer(1, 0.18 * inch))
        story.append(Paragraph("Output files", styles["Heading2"]))
        output_table = [["File"]] + [[str(out)] for out in output_files]
        story.append(
            _reportlab_table(output_table, direct_imports, col_widths=[6.4 * inch])
        )
        story.append(Spacer(1, 0.18 * inch))
        story.append(Paragraph("Legend notes", styles["Heading2"]))
        story.append(
            Paragraph(
                "Colors encode groups. Marker shapes encode populations. "
                "Target samples are drawn as large star markers with black outlines and labels. "
                "When modern_background is enabled, configured modern groups are rendered as "
                "a low-visibility gray background layer.",
                styles["BodyText"],
            )
        )

        doc.build(story)
        return True
    except Exception as exc:
        print(
            f"WARNING: reportlab report generation failed, falling back to minimal PDF: {exc}",
            file=sys.stderr,
        )
        return False
    finally:
        if tmp_png and tmp_png.exists():
            try:
                tmp_png.unlink()
            except OSError:
                pass
        tmp_pdf = path.with_suffix(".report_plot_tmp.pdf")
        if tmp_pdf.exists():
            try:
                tmp_pdf.unlink()
            except OSError:
                pass


def _reportlab_table(
    data: list[list[str]],
    colors_module: Any,
    col_widths: list[float] | None = None,
) -> Any:
    """Create a reportlab Table with default styling."""
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors_module.HexColor("#E9EEF3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors_module.HexColor("#111111")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors_module.HexColor("#D5DDE5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors_module.white, colors_module.HexColor("#FAFBFC")],
                ),
            ]
        )
    )
    return table
