"""Data models for smartpca visualization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Sample:
    """A single sample with its PCA coordinates and metadata."""

    sample_id: str
    population: str
    group: str
    pc1: float
    pc2: float
    is_target: bool = False
    target_label: str = ""
    is_modern_background: bool = False
    group_color: str = "#999999"
    population_color: str = "#999999"
    symbol: str = "circle"

    def to_dict(self) -> dict[str, Any]:
        """Convert to flat dict for JSON serialization."""
        return {
            "sample_id": self.sample_id,
            "population": self.population,
            "group": self.group,
            "PC1": self.pc1,
            "PC2": self.pc2,
            "is_target": self.is_target,
            "target_label": self.target_label,
            "is_modern_background": self.is_modern_background,
            "group_color": self.group_color,
            "population_color": self.population_color,
            "symbol": self.symbol,
        }

    def csv_dict(self) -> dict[str, Any]:
        """Convert to dict for CSV export (subset of fields)."""
        return {
            "sample_id": self.sample_id,
            "population": self.population,
            "group": self.group,
            "PC1": self.pc1,
            "PC2": self.pc2,
            "is_target": self.is_target,
            "target_label": self.target_label,
            "is_modern_background": self.is_modern_background,
        }


@dataclass
class Styles:
    """Precomputed style mappings for groups and populations."""

    group_colors: dict[str, str] = field(default_factory=dict)
    population_colors: dict[str, str] = field(default_factory=dict)
    population_symbols: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedData:
    """Container for all parsed and processed data."""

    samples: list[dict[str, Any]]
    group_order: list[str]
    pop_order: list[str]
    styles: Styles
    eigvals: list[float]
    config: dict[str, Any]
    project: str
    warnings: list[str]
