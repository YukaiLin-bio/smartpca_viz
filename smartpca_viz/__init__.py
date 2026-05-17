"""smartpca_viz — Interactive PCA visualization for smartpca results.

Provides:
- Command-line tool: python -m smartpca_viz --evec ... --meta ...
- Python API: PCAVisualizer for programmatic use
"""

from __future__ import annotations

__version__ = "2.0.0"
__all__ = ["PCAVisualizer"]

from pathlib import Path
from typing import Any

from smartpca_viz.config import default_config, load_config, write_yaml, validate_config
from smartpca_viz.parser import (
    parse_evec,
    parse_eval,
    parse_metadata,
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
from smartpca_viz.model import ParsedData, Styles


class PCAVisualizer:
    """Programmatic API for smartpca visualization.

    Usage:
        viz = PCAVisualizer(evec="./smartpca.evec", meta="./poplist.txt")
        viz.run(output_dir="./output", project="MyProject")
    """

    def __init__(
        self,
        evec: str | Path,
        meta: str | Path,
        targets: str | Path | None = None,
        config: str | Path | dict[str, Any] | None = None,
        eval_path: str | Path | None = None,
        meta_format: str = "auto",
        num_pc: int | None = None,
    ) -> None:
        self.evec_path = Path(evec)
        self.meta_path = Path(meta)
        self.targets_path = Path(targets) if targets else None
        self.eval_path = Path(eval_path) if eval_path else None
        self.meta_format = meta_format
        self.num_pc = num_pc

        if isinstance(config, dict):
            self._config = dict(default_config())
            self._config.update(config)
        elif config is not None:
            base = default_config()
            loaded, _warnings = load_config(Path(config), base)
            self._config = loaded
        else:
            self._config = default_config()

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    @config.setter
    def config(self, value: dict[str, Any]) -> None:
        self._config.update(value)

    def run(
        self,
        output_dir: str | Path = Path("output"),
        project: str | None = None,
    ) -> ParsedData:
        """Run the full pipeline: parse, process, generate all outputs."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Parse
        pca_rows, evec_eigvals, _ = parse_evec(self.evec_path, num_pc=self.num_pc)
        eval_eigvals, _ = parse_eval(self.eval_path, self.evec_path)
        eigvals = eval_eigvals or evec_eigvals

        metadata, pop_order, group_order, _ = parse_metadata(self.meta_path, self.meta_format)
        targets, _ = parse_targets(self.targets_path)
        project_prefix = resolve_project_prefix(project, targets)

        # Merge
        merged, _ = merge_data(pca_rows, metadata, targets, self._config)
        group_order, pop_order = build_orders(merged, pop_order, group_order)
        styles = assign_styles(merged, group_order, pop_order, self._config)

        # Output paths
        output_files = [
            out_dir / f"{project_prefix}_pca_interactive.html",
            out_dir / f"{project_prefix}_pca_plot.pdf",
            out_dir / f"{project_prefix}_pca_report.pdf",
            out_dir / f"{project_prefix}_pca_merged_data.csv",
            out_dir / f"{project_prefix}_config.yaml",
            out_dir / f"{project_prefix}_README.txt",
            out_dir / f"{project_prefix}_run.log",
        ]

        write_merged_data(output_files[3], merged)

        kde_image = compute_kde_base64(merged, self._config)
        generate_interactive_html(
            output_files[0], merged, group_order, pop_order, styles, eigvals,
            self._config, project_prefix, kde_image=kde_image,
        )
        generate_publication_pdf(
            output_files[1], merged, group_order, pop_order, styles, eigvals,
            self._config, project_prefix,
        )
        input_paths = {
            "evec": self.evec_path,
            "meta": self.meta_path,
            "targets": self.targets_path,
            "eval": self.eval_path,
        }
        generate_report_pdf(
            output_files[2], output_files[1], merged, group_order, pop_order,
            input_paths, output_files, self._config, project_prefix,
        )
        write_yaml(output_files[4], self._config)
        command = f"python -m smartpca_viz --evec {self.evec_path} --meta {self.meta_path}"
        write_readme(output_files[5], project_prefix, command, self._config, output_files)
        write_log(output_files[6], input_paths, out_dir, merged, [], output_files)

        return ParsedData(
            samples=merged,
            group_order=group_order,
            pop_order=pop_order,
            styles=styles,
            eigvals=eigvals,
            config=self._config,
            project=project_prefix,
            warnings=[],
        )

    def parse_only(self) -> ParsedData:
        """Parse and merge data without generating outputs."""
        pca_rows, evec_eigvals, _ = parse_evec(self.evec_path, num_pc=self.num_pc)
        eval_eigvals, _ = parse_eval(self.eval_path, self.evec_path)
        eigvals = eval_eigvals or evec_eigvals
        metadata, pop_order, group_order, _ = parse_metadata(self.meta_path, self.meta_format)
        targets, _ = parse_targets(self.targets_path)
        project_prefix = resolve_project_prefix(None, targets)
        merged, _ = merge_data(pca_rows, metadata, targets, self._config)
        group_order, pop_order = build_orders(merged, pop_order, group_order)
        styles = assign_styles(merged, group_order, pop_order, self._config)
        return ParsedData(
            samples=merged,
            group_order=group_order,
            pop_order=pop_order,
            styles=styles,
            eigvals=eigvals,
            config=self._config,
            project=project_prefix,
            warnings=[],
        )
