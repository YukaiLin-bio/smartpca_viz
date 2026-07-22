"""CLI argument parsing and pipeline orchestration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from smartpca_viz.config import default_config, load_config, write_yaml, validate_config
from smartpca_viz.parser import (
    parse_evec,
    parse_eval,
    parse_metadata,
    parse_poplist_groups,
    parse_targets,
    merge_data,
    build_orders,
    assign_styles,
    resolve_project_prefix,
)
from smartpca_viz.exporter import write_merged_data, write_readme, write_log
from smartpca_viz.render_html import generate_interactive_html
from smartpca_viz.render_pdf import generate_publication_pdf, generate_report_pdf
from smartpca_viz.kde_heatmap import compute_kde_base64
from smartpca_viz.warnings import WarningCollector


def info(message: str) -> None:
    """Print informational message."""
    print(f"✓ {message}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Visualize smartpca PCA results as publication-grade PDF and interactive HTML.",
        epilog="""
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
EXAMPLES

  # Minimal (auto-detects evec/eval in current dir):
  cd /your/data/dir
  python3 -m smartpca_viz --modern-poplist modern.poplist \\
      --ancient-poplist ancient.poplist --project my_pca

  # Full control:
  python3 -m smartpca_viz --evec smartpca.evec --eval smartpca.eval \\
      --modern-poplist modern.poplist --ancient-poplist ancient.poplist \\
      --project my_pca --out output

  # Modern as text labels:
  echo 'modern_background_labels: true' > /tmp/nature.yaml
  python3 -m smartpca_viz --modern-poplist modern.poplist \\
      --ancient-poplist ancient.poplist --project my_pca \\
      --config /tmp/nature.yaml

OUTPUT
  *_pca_plot.pdf          Publication-grade PCA figure (Nature style)
  *_pca_interactive.html  Interactive SVG plot (zoom, hover, export)
  *_pca_report.pdf        Report with sample/population statistics

AUTO-DETECTION
  --evec / --eval   Default to smartpca.evec / smartpca.eval in cwd
  --meta            Auto-merged from modern+ancient poplists if omitted
  --config          Publication-ready Nature defaults if omitted
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--evec", type=Path, default=Path("smartpca.evec"), help="Path to smartpca .evec file (default: smartpca.evec in current dir)")
    parser.add_argument("--meta", type=Path, help="Path to metadata file (CSV or poplist). If omitted and both --modern-poplist and --ancient-poplist are given, they are merged automatically.")
    parser.add_argument("--targets", type=Path, help="Path to targets CSV (sample_id,label)")
    parser.add_argument("--project", help="Project name for output filenames")
    parser.add_argument("--out", type=Path, default=Path("output"), help="Output directory")
    parser.add_argument("--config", type=Path, help="Path to YAML config file")
    parser.add_argument("--eval", type=Path, dest="eval_path", default=Path("smartpca.eval"), help="Path to .eval file (eigenvalues); default: smartpca.eval in current dir")
    parser.add_argument(
        "--meta-format",
        choices=["auto", "csv", "poplist"],
        default="auto",
        help="Metadata format (auto-detect by default)",
    )
    parser.add_argument("--modern-background", action="store_true", help="Enable modern background mode")
    parser.add_argument(
        "--modern-groups",
        help="Comma-separated group names to render as background",
    )
    parser.add_argument(
        "--modern-poplist",
        type=Path,
        help="Poplist file (====Group==== format) listing modern groups; auto-enables --modern-background",
    )
    parser.add_argument(
        "--ancient-poplist",
        type=Path,
        help="Poplist file (====Group==== format) listing ancient groups (informational / cross-validation)",
    )
    parser.add_argument(
        "--target-groups",
        help="Comma-separated metadata group names to treat as target samples; default: Target",
    )
    parser.add_argument(
        "--num-pc",
        type=int,
        help="Number of PC columns in evec (auto-detected from eigvals line if available)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the full smartpca visualization pipeline."""
    args = parse_args(argv)
    warnings = WarningCollector()

    # ── Load config ──────────────────────────────────────────
    base_config = default_config()
    config, config_warnings = load_config(args.config, base_config)
    warnings.extend(config_warnings)

    # Auto-set nature defaults if no config file provided
    if args.config is None:
        config["pdf_style"] = "nature"
        config["pdf_nature_col_width"] = 3.5
        config["pdf_nature_legend_width"] = 2.2
        config["point_size"] = 4.5
        config["target_color"] = "#D81B60"
        config["target_outline_color"] = "#222222"
        config["target_size_multiplier"] = 1.2
        config["label_targets"] = False
        config["modern_background_color"] = "#B0B8C4"
        config["modern_background_alpha"] = 0.45
        config["modern_background_size_multiplier"] = 2.5
        config["modern_label_mode"] = "population"
        config["publication_target_label"] = True
        info("No config file given; using publication-ready Nature defaults")

    # CLI overrides
    if args.modern_background:
        config["modern_background"] = True
    if args.modern_groups:
        config["modern_groups"] = [
            item.strip() for item in args.modern_groups.split(",") if item.strip()
        ]
    if args.target_groups:
        config["target_groups"] = [
            item.strip() for item in args.target_groups.split(",") if item.strip()
        ]

    # Auto-classify from modern/ancient poplists
    if args.modern_poplist:
        modern_groups, poplist_warnings = parse_poplist_groups(args.modern_poplist)
        warnings.extend(poplist_warnings)
        if modern_groups:
            config["modern_groups"] = modern_groups
            config["modern_background"] = True
            info(f"Auto-classified {len(modern_groups)} modern groups from {args.modern_poplist.name}")
            # Cross-validate against modern-groups CLI arg
            if args.modern_groups:
                cli_groups = [g.strip() for g in args.modern_groups.split(",") if g.strip()]
                missing = set(cli_groups) - set(modern_groups)
                if missing:
                    warnings.append(
                        f"[cli] --modern-groups lists groups not found in --modern-poplist: {missing}"
                    )
    if args.ancient_poplist:
        ancient_groups, poplist_warnings = parse_poplist_groups(args.ancient_poplist)
        warnings.extend(poplist_warnings)
        if ancient_groups:
            config["ancient_groups"] = ancient_groups
            info(f"Parsed {len(ancient_groups)} ancient groups from {args.ancient_poplist.name}")

    # Auto-merge modern + ancient poplists if no --meta given
    meta_path = args.meta
    if meta_path is None:
        if args.modern_poplist and args.ancient_poplist:
            import tempfile
            modern_bytes = args.modern_poplist.read_bytes()
            ancient_bytes = args.ancient_poplist.read_bytes()
            merged = modern_bytes.rstrip(b"\n\r") + b"\n" + ancient_bytes
            tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".poplist", delete=False)
            tmp.write(merged)
            tmp.close()
            meta_path = Path(tmp.name)
            warnings.add(f"[cli] Auto-merged modern+ancient poplists to {meta_path.name}")
        else:
            print("ERROR: --meta is required when neither --modern-poplist nor --ancient-poplist is given.", file=sys.stderr)
            return 1

    # Validate config
    config_issues = validate_config(config)
    warnings.extend(config_issues)

    # ── Parse inputs ─────────────────────────────────────────
    pca_rows, evec_eigvals, evec_warnings = parse_evec(args.evec, num_pc=args.num_pc)
    warnings.extend(evec_warnings)
    if not pca_rows:
        print("ERROR: No valid samples parsed from evec file. Aborting.", file=sys.stderr)
        return 1
    info("Read evec file")

    eval_eigvals, eval_warnings = parse_eval(args.eval_path, args.evec)
    warnings.extend(eval_warnings)
    eigvals = eval_eigvals or evec_eigvals

    metadata, pop_order, group_order, meta_warnings = parse_metadata(meta_path, args.meta_format)
    warnings.extend(meta_warnings)
    info("Read metadata")

    targets, target_warnings = parse_targets(args.targets)
    warnings.extend(target_warnings)
    info("Read target samples")

    # ── Preflight renderer availability ──────────────────────
    if config.get("pdf_style") == "nature":
        from smartpca_viz.render_pdf import HAS_MATPLOTLIB
        if not HAS_MATPLOTLIB:
            print(
                "ERROR: Nature publication output requires Matplotlib; no PDF was written",
                file=sys.stderr,
            )
            return 1
        if config.get("publication_renderer") != "matplotlib":
            print(
                "ERROR: Nature publication output requires Matplotlib; "
                f"publication_renderer is {config.get('publication_renderer')!r}",
                file=sys.stderr,
            )
            return 1

    # ── Process data ──────────────────────────────────────────
    project = resolve_project_prefix(args.project, targets)
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    merged, merge_warnings = merge_data(pca_rows, metadata, targets, config)
    warnings.extend(merge_warnings)
    info("Merged PCA data")

    group_order, pop_order = build_orders(merged, pop_order, group_order)
    styles = assign_styles(merged, group_order, pop_order, config)

    # ── Generate outputs ──────────────────────────────────────
    output_files = [
        out_dir / f"{project}_pca_interactive.html",
        out_dir / f"{project}_pca_plot.pdf",
        out_dir / f"{project}_pca_report.pdf",
        out_dir / f"{project}_pca_merged_data.csv",
        out_dir / f"{project}_config.yaml",
        out_dir / f"{project}_README.txt",
        out_dir / f"{project}_run.log",
    ]

    write_merged_data(output_files[3], merged)
    info("Wrote merged data")

    kde_image = compute_kde_base64(merged, config)
    if kde_image:
        info("Computed KDE heatmap")

    generate_interactive_html(
        output_files[0], merged, group_order, pop_order, styles, eigvals, config, project,
        kde_image=kde_image,
    )
    info("Generated interactive HTML")

    render_result = generate_publication_pdf(
        output_files[1], merged, group_order, pop_order, styles, eigvals, config, project,
    )
    info(f"Generated publication PDF (renderer: {render_result.get('renderer', 'unknown')})")

    # Build provenance dict
    from smartpca_viz.render_pdf import HAS_MATPLOTLIB
    from smartpca_viz.render_matplotlib import HAS_SCIPY, HAS_ADJUSTTEXT
    import sys as _sys
    try:
        import matplotlib as _mpl
        _mpl_version = _mpl.__version__
    except ImportError:
        _mpl_version = None

    provenance = {
        "renderer": render_result.get("renderer", "unknown"),
        "fallback_reason": render_result.get("fallback_reason"),
        "matplotlib_version": _mpl_version,
        "scipy_available": HAS_SCIPY,
        "adjusttext_available": HAS_ADJUSTTEXT,
        "python_version": _sys.version.split()[0],
        "publication_svg_path": str(output_files[1].with_suffix(".svg"))
            if config.get("pdf_style") == "nature" and config.get("publication_output_svg", True)
            else None,
        "modern_label_mode": config.get("modern_label_mode", "none"),
        "modern_population_label_count": len(set(
            row["population"] for row in merged if row.get("is_modern_background")
        )),
    }

    input_paths = {
        "evec": args.evec,
        "meta": meta_path,
        "targets": args.targets,
        "eval": args.eval_path,
        "config": args.config,
    }

    generate_report_pdf(
        output_files[2], output_files[1], merged, group_order, pop_order,
        input_paths, output_files, config, project,
        provenance=provenance,
    )
    info("Generated report PDF")

    write_yaml(output_files[4], config)
    info("Wrote config")

    command = "python -m smartpca_viz " + " ".join(sys.argv[1:] if argv is None else argv[1:])
    write_readme(output_files[5], project, command, config, output_files)
    info("Wrote README")

    write_log(output_files[6], input_paths, out_dir, merged, warnings.messages, output_files,
              provenance=provenance)
    info("Wrote log")

    return 0
