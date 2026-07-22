"""Output file writing: CSV, README, and run log."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from smartpca_viz.model import Sample


CSV_COLUMNS = [
    "sample_id",
    "population",
    "group",
    "PC1",
    "PC2",
    "is_target",
    "target_label",
    "is_modern_background",
]


def write_merged_data(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write merged PCA data as CSV."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_COLUMNS})


def write_readme(
    path: Path,
    project: str,
    command: str,
    config: dict[str, Any],
    output_files: list[Path],
) -> None:
    """Write README text file documenting the run."""
    lines = [
        "smartpca_viz",
        "============",
        "",
        "A command-line tool for visualizing smartpca .evec PC1/PC2 results.",
        "",
        "Example command:",
        command,
        "",
        "Input files:",
        "- .evec: first column sample_id, middle columns PC values, last column population.",
        "- metadata CSV: population,group.",
        "- metadata poplist: ====Group==== headers followed by population names.",
        "- targets CSV: sample_id,label. Target matching is by sample_id.",
        "",
        "Output files:",
    ]
    lines.extend(f"- {out.name}" for out in output_files)
    lines.extend(
        [
            "",
            "Configuration summary:",
        ]
    )
    lines.extend(f"- {key}: {value}" for key, value in config.items())
    # Modern population label note
    if config.get("modern_label_mode") == "population":
        lines.extend([
            "",
            "Modern population label notes:",
            "- The static figures (PDF/SVG) place one centroid-based label per modern",
            "  population. Dense PCA regions may have local label overlap — this is",
            "  an accepted visual design for broad population identification.",
            "- For precise per-population lookup, use the interactive HTML: hover over",
            "  points for tooltips, search by population name, or filter by population",
            "  in the sidebar.",
            "- Population label overlap in dense regions is a natural consequence of",
            "  PCA projection; it does not indicate a data or analysis problem.",
        ])
    lines.extend(
        [
            "",
            "Common warnings:",
            "- Missing metadata: population is assigned to Unknown.",
            "- Duplicate sample_id: reported but processing continues.",
            "- Target not found: target sample_id was absent from the .evec file.",
            "- Conflicting metadata: first population/group mapping is retained.",
            "",
            "Dependencies:",
            "Recommended installation:",
            "python3 -m venv .venv",
            ".venv/bin/python -m pip install -r requirements-smartpca-viz.txt",
            "",
            "Required packages for high-quality outputs: pandas, numpy, plotly, matplotlib, adjustText, PyYAML, kaleido, reportlab.",
            "The script keeps a minimal fallback path, but publication-quality output should use the recommended dependencies.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_log(
    path: Path,
    input_paths: dict[str, Any],
    out_dir: Path,
    rows: list[dict[str, Any]],
    warnings: list[str],
    output_files: list[Path],
    provenance: dict[str, Any] | None = None,
) -> None:
    """Write run log with summary statistics and rendering provenance."""
    group_count = len(set(row["group"] for row in rows))
    pop_count = len(set(row["population"] for row in rows))
    target_count = sum(1 for row in rows if row["is_target"])
    unknown_count = sum(1 for row in rows if row["group"] == "Unknown")

    lines = [
        f"Run time: {datetime.now().isoformat(timespec='seconds')}",
        "Input files:",
    ]
    lines.extend(f"  {key}: {value}" for key, value in input_paths.items())
    lines.extend(
        [
            f"Output directory: {out_dir}",
            f"Sample total: {len(rows)}",
            f"Population count: {pop_count}",
            f"Group count: {group_count}",
            f"Target count: {target_count}",
            f"Unknown group sample count: {unknown_count}",
        ]
    )
    # Rendering provenance
    if provenance:
        lines.append("Rendering:")
        for key in ["renderer", "fallback_reason", "matplotlib_version",
                     "scipy_available", "adjusttext_available", "python_version",
                     "publication_svg_path", "modern_label_mode",
                     "modern_population_label_count"]:
            val = provenance.get(key)
            if val is not None:
                lines.append(f"  {key}: {val}")
        # Note about adjustText
        if provenance.get("modern_label_mode") == "population":
            if not provenance.get("adjusttext_available"):
                lines.append("  [note] adjustText not installed; modern population labels are")
                lines.append("         rendered as direct centroids. Dense PCA regions may have")
                lines.append("         local label overlap — this is an accepted visual design.")
    lines.extend([
        "Warnings:",
    ])
    if warnings:
        lines.extend(f"  WARNING: {message}" for message in warnings)
    else:
        lines.append("  None")
    lines.append("Output files:")
    lines.extend(f"  {out}" for out in output_files)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
