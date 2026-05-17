"""Configuration loading, validation, and defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def default_config() -> dict[str, Any]:
    return {
        "color_by": "group",
        "label_targets": True,
        "target_shape": "star",
        "target_color": "#FFD400",
        "target_size_multiplier": 1.8,
        "target_outline_color": "#FF0000",
        "legend_order": "metadata",
        "html_default_view": "global",
        "focus_targets_button": True,
        "enable_lasso": True,
        "enable_export_selected_csv": True,
        "enable_search": True,
        "enable_population_highlight": True,
        "enable_group_highlight": True,
        "pdf_style": "sci",
        "pdf_language": "english",
        "target_groups": ["Target"],
        "modern_background": False,
        "modern_groups": [
            "Han",
            "Austronesian",
            "Austroasiatic",
            "Hmong-Mien",
            "Japanese-Korean",
            "Mongolian",
            "Tai-Kadai",
            "Tibetan-Burman",
        ],
        "modern_background_color": "#6699CC",
        "modern_background_alpha": 0.55,
        "modern_background_size_multiplier": 3.0,
        "modern_background_show_legend": False,
        "html_use_webgl_threshold": 2000,
        "point_size": 5.0,
        "target_label_fontsize": 12,
        "pdf_width_in": 8.0,
        "pdf_height_in": 6.5,
        "pdf_combine_plot_and_legend": True,
        "pdf_combined_width_in": 12.0,
        "pdf_combined_height_in": 14.2,
    }


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "yes", "y", "1", "on"}


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.lower() in {"true", "false"}:
        return parse_bool(value)
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip('"').strip("'")


def load_config(
    path: Path | None,
    base_config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Load config from YAML-like file. Returns (config, warnings).

    Improved error messages include line numbers and file context.
    """
    config = dict(base_config) if base_config is not None else default_config()
    warnings: list[str] = []

    if path is None:
        return config, warnings
    if not path.exists():
        warnings.append(f"Config file not found: {path}")
        return config, warnings

    current_list_key: str | None = None
    with path.open() as handle:
        lines = list(handle)

    for line_no, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item continuation
        if stripped.startswith("- ") and current_list_key is not None:
            config.setdefault(current_list_key, []).append(parse_scalar(stripped[2:]))
            continue

        current_list_key = None

        if ":" not in stripped:
            warnings.append(
                f"[config] Line {line_no}: no colon found — ignoring: {line!r}"
            )
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            warnings.append(f"[config] Line {line_no}: empty key — ignoring: {line!r}")
            continue

        if value == "":
            config[key] = []
            current_list_key = key
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            config[key] = [parse_scalar(item) for item in inner.split(",") if item.strip()]
        else:
            config[key] = parse_scalar(value)

    return config, warnings


def write_yaml(path: Path, config: dict[str, Any]) -> None:
    """Write configuration dict to a YAML-style file."""
    with path.open("w", encoding="utf-8") as handle:
        handle.write("---\n")
        for key, value in config.items():
            if isinstance(value, list):
                handle.write(f"{key}:\n")
                for item in value:
                    handle.write(f"  - {item}\n")
            elif isinstance(value, bool):
                handle.write(f"{key}: {'true' if value else 'false'}\n")
            elif isinstance(value, str):
                # Quote strings that might be ambiguous
                if any(c in value for c in ": #"):
                    handle.write(f'{key}: "{value}"\n')
                else:
                    handle.write(f"{key}: {value}\n")
            else:
                handle.write(f"{key}: {value}\n")


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate config values and return list of warnings/errors."""
    warnings: list[str] = []
    if not isinstance(config.get("target_groups"), list):
        warnings.append("[config] target_groups should be a list")
    if not isinstance(config.get("modern_groups"), list):
        warnings.append("[config] modern_groups should be a list")
    if not isinstance(config.get("point_size"), (int, float)) or config["point_size"] <= 0:
        warnings.append("[config] point_size must be a positive number")
    if not isinstance(config.get("target_size_multiplier"), (int, float)) or config["target_size_multiplier"] <= 0:
        warnings.append("[config] target_size_multiplier must be a positive number")
    if not isinstance(config.get("modern_background_alpha"), (int, float)) or not (0 <= config["modern_background_alpha"] <= 1):
        warnings.append("[config] modern_background_alpha must be between 0 and 1")
    return warnings
