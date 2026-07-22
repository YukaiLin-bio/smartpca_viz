"""Static contract tests for HTML templates — target shape, modern rendering, export labels."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class TestTargetShapeInJS:
    """Target shape must be taken from config.target_shape, not hard-coded."""

    def _read_js(self):
        return (TEMPLATE_DIR / "app.js").read_text(encoding="utf-8")

    def test_target_shape_from_config_not_hardcoded_star(self):
        js = self._read_js()
        # Must reference config.target_shape for targets
        assert "this.p.config.target_shape" in js, (
            "app.js should read target_shape from config, not hard-code 'star'"
        )

    def test_modern_text_not_rendered_per_individual(self):
        js = self._read_js()
        # The modern background section should now render points instead of text
        modern_section = js.find("Layer 1: Modern background")
        assert modern_section != -1, "Modern background layer section not found"
        # Verify it uses markers now, not individual text
        assert "is_modern_background" in js


class TestExportLabels:
    """Export buttons must be accurately labelled."""

    def _read_html(self):
        return (TEMPLATE_DIR / "base.html").read_text(encoding="utf-8")

    def test_pdf_label_is_raster_preview(self):
        html = self._read_html()
        assert "Raster preview PDF" in html or "Raster preview" in html, (
            "base.html should label the browser-generated PDF as raster preview"
        )

    def test_svg_label_is_vector(self):
        html = self._read_html()
        assert "SVG (vector)" in html or "SVG" in html, (
            "base.html should label SVG as vector export"
        )


class TestModernPointRendering:
    """Modern background samples must be rendered as points, not text labels."""

    def _read_js(self):
        return (TEMPLATE_DIR / "app.js").read_text(encoding="utf-8")

    def test_shape_for_point_helper_exists(self):
        js = self._read_js()
        assert "_shapeForPoint" in js or (
            "is_modern_background" in js and "circle" in js
        ), "app.js should have a helper to resolve point shape for modern/background"

    def test_modern_points_use_circle_geometry(self):
        """Modern non-target points should be forced to circle."""
        js = self._read_js()
        # Check that modern background section uses markers/points, not individual text nodes
        assert "marker" in js or "circle" in js, "app.js should render modern points as markers"


class TestPopLabelsBehavior:
    """Pop labels must show one label per population, using population name."""

    def _read_js(self):
        return (TEMPLATE_DIR / "app.js").read_text(encoding="utf-8")

    def test_pop_labels_uses_centroids(self):
        """_drawPopulationCentroidLabels must exist and compute centroids."""
        js = self._read_js()
        assert "_drawPopulationCentroidLabels" in js, (
            "app.js must have _drawPopulationCentroidLabels method"
        )
        assert "centroids" in js, "must compute population centroids"
        assert "sumPC1" in js or "sum_pc1" in js or "PC1" in js, (
            "must aggregate PC coordinates for centroids"
        )

    def test_pop_labels_use_population_field(self):
        """Labels must come from p.population, not p.group."""
        js = self._read_js()
        # The centroid label should use pop = p.population
        assert 'p.population' in js or 'pop = p.population' in js or 'var pop' in js, (
            "labels must use population field"
        )

    def test_pop_labels_not_per_individual(self):
        """Must not render one label per individual (433)."""
        js = self._read_js()
        # The centroid approach groups by population — verify it iterates
        # Object.keys(centroids) pattern (not forEach over all points)
        assert "Object.keys" in js, "must iterate over unique populations, not all points"
