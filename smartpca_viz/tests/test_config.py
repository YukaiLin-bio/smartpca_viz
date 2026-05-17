"""Tests for the config module."""

from __future__ import annotations

from pathlib import Path
from smartpca_viz.config import default_config, load_config, write_yaml, validate_config, parse_scalar


class TestDefaultConfig:
    def test_returns_dict(self):
        cfg = default_config()
        assert isinstance(cfg, dict)

    def test_has_required_keys(self):
        cfg = default_config()
        assert "point_size" in cfg
        assert "color_by" in cfg
        assert "modern_background" in cfg
        assert cfg["point_size"] == 5.0
        assert cfg["color_by"] == "group"


class TestLoadConfig:
    def test_none_path(self):
        cfg, warns = load_config(None)
        assert len(warns) == 0
        assert cfg["color_by"] == "group"

    def test_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.yaml"
        cfg, warns = load_config(missing)
        assert len(warns) == 1
        assert "not found" in warns[0]

    def test_real_config(self):
        cfg, warns = load_config(Path(__file__).parent.parent.parent / "config.yaml")
        assert cfg["color_by"] == "group"
        assert cfg["modern_background"] is True
        assert isinstance(cfg["modern_groups"], list)


class TestValidateConfig:
    def test_valid_config(self):
        cfg = default_config()
        issues = validate_config(cfg)
        assert len(issues) == 0

    def test_invalid_point_size(self):
        cfg = default_config()
        cfg["point_size"] = -1
        issues = validate_config(cfg)
        assert any("point_size" in i for i in issues)


class TestParseScalar:
    def test_bool_true(self):
        assert parse_scalar("true") is True
        assert parse_scalar("True") is True

    def test_bool_false(self):
        assert parse_scalar("false") is False

    def test_int(self):
        assert parse_scalar("42") == 42

    def test_float(self):
        assert parse_scalar("3.14") == 3.14

    def test_string(self):
        assert parse_scalar("hello") == "hello"
