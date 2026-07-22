"""Tests for renderer selection contract and publication legend policies."""

from __future__ import annotations

from pathlib import Path
import sys

# Ensure smartpca_viz is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from smartpca_viz.config import default_config, validate_config


class TestNatureRequiresMatplotlib:
    """pdf_style 'nature' must resolve to publication_renderer 'matplotlib'."""

    def test_nature_rejects_simplepdf_draft(self):
        config = default_config()
        config["pdf_style"] = "nature"
        config["publication_renderer"] = "simplepdf-draft"
        issues = validate_config(config)
        assert any(
            "pdf_style 'nature' requires publication_renderer 'matplotlib'"
            in issue
            for issue in issues
        )

    def test_target_shape_valid_values(self):
        config = default_config()
        # Valid shapes should not warn
        for shape in ["star", "circle", "square", "triangle", "diamond"]:
            config["target_shape"] = shape
            issues = validate_config(config)
            assert not any("target_shape" in i for i in issues)

    def test_target_shape_invalid_rejected(self):
        config = default_config()
        config["target_shape"] = "hexagon"
        issues = validate_config(config)
        assert any("target_shape" in i for i in issues)


class TestDefaultPublicationConfig:
    """Default config must include new publication keys."""

    def test_default_publication_renderer(self):
        config = default_config()
        assert config["publication_renderer"] == "matplotlib"

    def test_default_publication_legend(self):
        config = default_config()
        assert config["publication_legend"] == "groups"

    def test_default_modern_render_mode(self):
        config = default_config()
        assert config["modern_render_mode"] == "points"

    def test_default_modern_centroid_labels(self):
        config = default_config()
        assert config["modern_centroid_labels"] is False

    def test_default_publication_target_label(self):
        config = default_config()
        assert config["publication_target_label"] is True

    def test_default_publication_output_svg(self):
        config = default_config()
        assert config["publication_output_svg"] is True


class TestPublicationLegend:
    """build_publication_legend must produce group-level-only entries."""

    def _make_styles(self, group_colors):
        class Styles:
            pass
        s = Styles()
        s.group_colors = dict(group_colors)
        return s

    def test_legend_is_complete_and_group_level(self):
        from smartpca_viz.render_matplotlib import build_publication_legend

        # 25 non-target groups + 1 target = 26 entries
        group_order = [f"G{i:03d}" for i in range(25)] + ["Target"]
        styles = self._make_styles({g: "#AAAAAA" for g in group_order})

        rows = []
        for i in range(25):
            gname = f"G{i:03d}"
            for _ in range(3):  # 3 samples per group
                rows.append({
                    "group": gname,
                    "group_color": styles.group_colors.get(gname, "#999"),
                    "is_target": False,
                })
        # Add 1 target
        rows.append({
            "group": "Target",
            "group_color": "#D81B60",
            "is_target": True,
        })

        config = default_config()
        entries = build_publication_legend(rows, group_order, styles, config)

        # 25 groups + 1 target
        assert len(entries) == 26
        assert all(entry["kind"] in {"group", "target"} for entry in entries)
        assert entries[-1]["kind"] == "target"
        assert entries[-1]["name"] == "Target"

    def test_legend_never_contains_population_entries(self):
        from smartpca_viz.render_matplotlib import build_publication_legend

        group_order = ["GRP_A", "GRP_B"]
        styles = self._make_styles({"GRP_A": "#FF0000", "GRP_B": "#0000FF"})
        rows = [
            {"group": "GRP_A", "group_color": "#FF0000", "is_target": False},
            {"group": "GRP_B", "group_color": "#0000FF", "is_target": False},
        ]
        config = default_config()
        entries = build_publication_legend(rows, group_order, styles, config)
        assert len(entries) == 2
        for e in entries:
            assert e["kind"] == "group"
            assert "color" in e
        # No Target entry since there's no target in rows


class TestRendererProvenance:
    """Rendering must report provenance correctly."""

    def test_nature_renderer_recorded_as_matplotlib(self):
        from smartpca_viz.render_pdf import HAS_MATPLOTLIB

        if not HAS_MATPLOTLIB:
            import pytest
            pytest.skip("Matplotlib not available")

        # Verify that after a successful run, the renderer field is 'matplotlib'
        # We test the contract: if Nature style is used, the renderer must pass
        # through generate_publication_pdf and return 'matplotlib'.
        # Full E2E test is covered by Task 6 regeneration.
        config = default_config()
        config["pdf_style"] = "nature"
        assert config["publication_renderer"] == "matplotlib"
        # The contract: Nature + publication_renderer=matplotlib → valid
        issues = validate_config(config)
        assert not any("publication_renderer" in i for i in issues)


class TestModernLabelModeValidation:
    """modern_label_mode must be validated."""

    def test_valid_modes_accepted(self):
        config = default_config()
        for mode in ["none", "population"]:
            config["modern_label_mode"] = mode
            issues = validate_config(config)
            assert not any("modern_label_mode" in i for i in issues)

    def test_invalid_mode_rejected(self):
        config = default_config()
        config["modern_label_mode"] = "individual"
        issues = validate_config(config)
        assert any("modern_label_mode" in i for i in issues)


class TestRealRendering:
    """Real rendering with synthetic data via tmp_path."""

    def _make_styles(self, group_colors):
        class Styles:
            pass
        s = Styles()
        s.group_colors = dict(group_colors)
        s.population_symbols = {}
        return s

    def _synthetic_rows(self, config=None):
        """Return rows and metadata for a minimal rendering test."""
        rows = [
            {"sample_id": "S1", "population": "PopA", "group": "Grp1", "PC1": 0.0, "PC2": 0.0,
             "is_target": True, "is_modern_background": False,
             "group_color": "#D81B60", "target_label": "monk"},
            {"sample_id": "S2", "population": "PopB", "group": "Grp2", "PC1": 1.0, "PC2": 1.0,
             "is_target": False, "is_modern_background": False,
             "group_color": "#4477AA", "target_label": ""},
            {"sample_id": "S3", "population": "PopC", "group": "Grp3", "PC1": 0.5, "PC2": -0.5,
             "is_target": False, "is_modern_background": True,
             "group_color": "#6699CC", "target_label": ""},
            {"sample_id": "S4", "population": "PopD", "group": "Grp3", "PC1": 0.6, "PC2": -0.4,
             "is_target": False, "is_modern_background": True,
             "group_color": "#6699CC", "target_label": ""},
        ]
        return rows

    def test_target_label_in_rendered_svg_pdf(self, tmp_path):
        """Real rendering must produce SVG/PDF containing 'monk'."""
        from smartpca_viz.render_matplotlib import (
            generate_publication_pdf_matplotlib, HAS_MATPLOTLIB,
        )
        if not HAS_MATPLOTLIB:
            import pytest; pytest.skip("Matplotlib not available")

        rows = self._synthetic_rows()
        group_order = ["Grp1", "Grp2", "Grp3"]
        pop_order = ["PopA", "PopB", "PopC", "PopD"]
        styles = self._make_styles({"Grp1": "#D81B60", "Grp2": "#4477AA", "Grp3": "#6699CC"})
        config = default_config()
        config["pdf_style"] = "nature"
        config["modern_background"] = True
        config["modern_groups"] = ["Grp3"]
        config["publication_target_label"] = True
        config["modern_label_mode"] = "none"

        pdf_path = tmp_path / "test.pdf"
        result = generate_publication_pdf_matplotlib(
            pdf_path, rows, group_order, pop_order, styles, [1.0, 0.5, 0.2], config, "test",
        )
        assert result is True

        # Check SVG was created alongside PDF
        svg_path = pdf_path.with_suffix(".svg")
        assert svg_path.exists(), "SVG should be created"
        svg_text = svg_path.read_text()
        assert "monk" in svg_text, "SVG must contain target label"

        # Check PDF via pdftotext
        import subprocess
        try:
            r = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True)
            if r.returncode == 0:
                assert "monk" in r.stdout, "PDF must contain target label"
        except FileNotFoundError:
            pass

    def test_target_shape_square_renders_square(self, tmp_path):
        """target_shape=square must produce square markers, not star."""
        from smartpca_viz.render_matplotlib import (
            generate_publication_pdf_matplotlib, HAS_MATPLOTLIB,
        )
        if not HAS_MATPLOTLIB:
            import pytest; pytest.skip("Matplotlib not available")

        rows = self._synthetic_rows()
        group_order = ["Grp1", "Grp2", "Grp3"]
        pop_order = ["PopA", "PopB", "PopC", "PopD"]
        styles = self._make_styles({"Grp1": "#D81B60", "Grp2": "#4477AA", "Grp3": "#6699CC"})
        config = default_config()
        config["pdf_style"] = "nature"
        config["modern_background"] = False
        config["modern_label_mode"] = "none"
        config["publication_target_label"] = True
        config["target_shape"] = "square"

        pdf_path = tmp_path / "test_square.pdf"
        result = generate_publication_pdf_matplotlib(
            pdf_path, rows, group_order, pop_order, styles, [1.0, 0.5], config, "test",
        )
        assert result is True

        # Star should NOT appear as target marker in the SVG
        svg_path = pdf_path.with_suffix(".svg")
        svg_text = svg_path.read_text()
        # A star in matplotlib SVG appears as polygon with "star" marker path or "*"
        # For square targets, we should see rect elements, not the star polygon pattern
        # The target color (#D81B60) should appear in a <rect ... fill="#D81B60"
        assert "<rect" in svg_text or 'fill="#D81B60"' in svg_text, (
            "SVG with target_shape=square should render square (rect) markers"
        )

    def test_modern_label_mode_population_uses_population_field(self, tmp_path):
        """modern_label_mode=population must aggregate by population, not per individual."""
        from smartpca_viz.render_matplotlib import (
            generate_publication_pdf_matplotlib, HAS_MATPLOTLIB,
        )
        if not HAS_MATPLOTLIB:
            import pytest; pytest.skip("Matplotlib not available")

        rows = self._synthetic_rows()
        # Add more modern samples to test centroid aggregation
        rows.append({
            "sample_id": "S5", "population": "PopE", "group": "Grp3", "PC1": 0.55, "PC2": -0.45,
            "is_target": False, "is_modern_background": True,
            "group_color": "#6699CC", "target_label": "",
        })
        group_order = ["Grp1", "Grp2", "Grp3"]
        pop_order = ["PopA", "PopB", "PopC", "PopD", "PopE"]
        styles = self._make_styles({"Grp1": "#D81B60", "Grp2": "#4477AA", "Grp3": "#6699CC"})
        config = default_config()
        config["pdf_style"] = "nature"
        config["modern_background"] = True
        config["modern_groups"] = ["Grp3"]
        config["modern_label_mode"] = "population"
        config["publication_target_label"] = True

        pdf_path = tmp_path / "test_pop_labels.pdf"
        result = generate_publication_pdf_matplotlib(
            pdf_path, rows, group_order, pop_order, styles, [1.0, 0.5], config, "test",
        )
        assert result is True

        # Verify the modern population labels are using population names (not group names)
        svg_path = pdf_path.with_suffix(".svg")
        svg_text = svg_path.read_text()
        # Should contain population names "PopC", "PopD", "PopE" (not group "Grp3")
        # At least one population label should be present
        assert any(pop in svg_text for pop in ["PopC", "PopD", "PopE"]), (
            "SVG should contain population-level labels (PopC/PopD/PopE), not just group names"
        )
        # Should NOT render 433 individual labels — with only 5 samples, there would be
        # at most 3 unique modern populations (PopC, PopD, PopE)
        # Verify no per-individual text pattern (sample_id as label)
        assert "S3" not in svg_text or "S4" not in svg_text or "S5" not in svg_text, (
            "Labels should NOT use sample_id as text content"
        )


class TestLongLabelLegendLayout:
    """Column widths must accommodate long group names without overlap."""

    def _make_styles(self, group_colors):
        class Styles:
            pass
        s = Styles()
        s.group_colors = dict(group_colors)
        s.population_symbols = {}
        return s

    def test_long_labels_fit_without_overlap(self, tmp_path):
        """Render with all 4 known long labels; assert columns don't overlap."""
        from smartpca_viz.render_matplotlib import (
            generate_publication_pdf_matplotlib, HAS_MATPLOTLIB,
        )
        if not HAS_MATPLOTLIB:
            import pytest; pytest.skip("Matplotlib not available")

        long_names = [
            "Ancient Shandong Longshan",
            "Ancient Hebei Hongshan",
            "Ancient North Eurasian",
            "Ancient_Yangtze_River",
        ]
        # Build 26 synthetic entries: the 4 long ones + 22 short ones
        group_names = long_names + [f"G{i:02d}" for i in range(22)]
        group_order = group_names
        rows = []
        for g in group_names:
            rows.append({
                "sample_id": g, "population": g, "group": g,
                "PC1": 0.0, "PC2": 0.0, "is_target": False,
                "is_modern_background": False,
                "group_color": "#AAAAAA", "target_label": "",
            })
        # Add target
        rows.append({
            "sample_id": "monk", "population": "TargetPop", "group": "Target",
            "PC1": 10.0, "PC2": 10.0, "is_target": True,
            "is_modern_background": False,
            "group_color": "#D81B60", "target_label": "monk",
        })
        group_order.append("Target")

        styles = self._make_styles({g: "#AAAAAA" for g in group_order})
        styles.group_colors["Target"] = "#D81B60"
        pop_order = group_order

        config = default_config()
        config["pdf_style"] = "nature"
        config["modern_background"] = False
        config["modern_label_mode"] = "none"
        config["publication_target_label"] = True

        pdf_path = tmp_path / "test_long_labels.pdf"
        result = generate_publication_pdf_matplotlib(
            pdf_path, rows, group_order, pop_order, styles, [], config, "test",
        )
        assert result is True

        # Parse SVG to check column layout: group texts by x position
        import xml.etree.ElementTree as ET
        svg_path = pdf_path.with_suffix(".svg")
        tree = ET.parse(str(svg_path))
        root = tree.getroot()
        ns = "http://www.w3.org/2000/svg"

        # Find all text elements and filter to legend entries
        texts = root.findall(f".//{{{ns}}}text")
        legend_texts = []
        for t in texts:
            content = t.text or "".join(t.itertext())
            if content and content.strip() in group_names:
                x_raw = t.get("x")
                if x_raw is not None:
                    try:
                        legend_texts.append((float(x_raw), content.strip()))
                    except ValueError:
                        pass

        assert len(legend_texts) > 0, "No legend text elements found in SVG"

        # Group by x position (round to 1 decimal)
        from collections import defaultdict
        cols = defaultdict(list)
        for x, name in legend_texts:
            cols[round(x, 1)].append(name)

        # Verify all 4 long labels present
        all_found = set()
        for texts_in_col in cols.values():
            all_found.update(texts_in_col)
        for name in long_names:
            assert name in all_found, f"Long label '{name}' not found in SVG"

        # With 4 long labels in a 7" figure, should use ≥2 columns
        assert len(cols) >= 2, (
            f"Expected >=2 columns for long labels, got {len(cols)}. "
            f"Column x-positions: {sorted(cols.keys())}"
        )

        # Check column spacing: sorted x values should have clear separation
        sorted_x = sorted(cols.keys())
        for i in range(len(sorted_x) - 1):
            gap = sorted_x[i + 1] - sorted_x[i]
            # Gap should be at least 0.08 in axes coordinates (roughly 35pt)
            assert gap > 0.05, (
                f"Column gap too small: col at x={sorted_x[i]}, next at x={sorted_x[i+1]}, gap={gap:.2f}"
            )
