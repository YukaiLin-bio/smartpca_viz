"""File parsing and data merging for smartpca results."""

from __future__ import annotations

import csv
import math
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any

from smartpca_viz.model import Sample, Styles
from smartpca_viz.palette import GROUP_PALETTE, POP_PALETTE, SYMBOLS, sanitize_prefix


# ─── Evec parsing ────────────────────────────────────────────────


def find_similar_path(path: Path) -> str | None:
    """Suggest similar existing files if path doesn't exist."""
    if path.exists():
        return None
    parent = path.parent
    if not parent.exists():
        return None
    name = path.name
    candidates = sorted(parent.glob(f"*{path.suffix}"))
    if not candidates:
        return None
    # Score by prefix similarity
    scored = []
    for c in candidates:
        cn = c.name
        # Count matching prefix characters
        match_count = sum(1 for a, b in zip(name, cn) if a == b)
        scored.append((match_count, cn))
    scored.sort(reverse=True)
    best = scored[0][1]
    if best != name:
        return str(candidates[0].absolute())
    return None


def check_file_exists(path: Path, label: str) -> list[str]:
    """Check file exists and return warning with suggestion if not."""
    if not path.exists():
        suggestion = find_similar_path(path)
        msg = f"[parser] {label} not found: {path}"
        if suggestion:
            msg += f"\n  → Did you mean: {suggestion}?"
        return [msg]
    return []


def parse_evec(
    path: Path, num_pc: int | None = None
) -> tuple[list[dict[str, Any]], list[float], list[str]]:
    """Parse smartpca .evec file. Returns (rows, eigvals, warnings).

    Each row dict has keys: sample_id, population, PC1, PC2, ...
    Improved validation with line numbers and suggestions.
    """
    warnings: list[str] = []
    warnings.extend(check_file_exists(path, "Evec file"))

    rows: list[dict[str, Any]] = []
    eigvals: list[float] = []
    seen_evec: Counter[str] = Counter()
    num_pc = num_pc or None

    if not path.exists():
        return rows, eigvals, warnings

    # Quick empty-file check
    try:
        file_size = path.stat().st_size
        if file_size == 0:
            warnings.append(f"[parser] Evec file is empty: {path}")
            return rows, eigvals, warnings
    except OSError:
        pass

    with path.open() as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue

            # Eigvals header
            if line.startswith("#eigvals"):
                eigvals = parse_eigvals_line(line)
                if eigvals:
                    num_pc = len(eigvals)
                continue

            parts = line.split()
            if len(parts) < 4:
                warnings.append(
                    f"[parser] evec line {line_no}: fewer than 4 fields ({len(parts)}), skipping"
                )
                continue

            # Determine PC column count
            n = num_pc if num_pc is not None else len(parts) - 2
            if n is None or n < 2:
                warnings.append(
                    f"[parser] evec line {line_no}: fewer than 2 PC columns detected ({n}), skipping"
                )
                continue

            population = parts[-1]
            pc_tokens = parts[-(n + 1) : -1]
            sample_id = " ".join(parts[: -(n + 1)])

            if len(pc_tokens) < 2:
                warnings.append(
                    f"[parser] evec line {line_no}: expected >= 2 PC columns but got {len(pc_tokens)}, skipping"
                )
                continue

            try:
                pcs = [float(token) for token in pc_tokens]
            except ValueError as exc:
                warnings.append(
                    f"[parser] evec line {line_no}: non-numeric PC value ({exc}), skipping"
                )
                continue

            if not math.isfinite(pcs[0]) or not math.isfinite(pcs[1]):
                warnings.append(
                    f"[parser] evec line {line_no}: PC1/PC2 contains NaN or infinite value, skipping"
                )
                continue

            seen_evec[sample_id] += 1
            row: dict[str, Any] = {"sample_id": sample_id, "population": population}
            for idx, value in enumerate(pcs, 1):
                row[f"PC{idx}"] = value
            rows.append(row)

    # Report duplicates
    for sample_id, count in seen_evec.items():
        if count > 1:
            warnings.append(
                f"[parser] Duplicate sample_id in evec: {sample_id!r} occurs {count} times"
            )

    if not rows:
        warnings.append(f"[parser] No valid rows parsed from evec file: {path}")
    else:
        # Check PC column consistency
        pc_count = sum(1 for k in rows[0] if k.startswith("PC"))
        for idx, row in enumerate(rows[1:], 2):
            this_count = sum(1 for k in row if k.startswith("PC"))
            if this_count != pc_count:
                warnings.append(
                    f"[parser] evec row {idx} has {this_count} PC columns, expected {pc_count} (inconsistent)"
                )

    return rows, eigvals, warnings


def parse_eigvals_line(line: str) -> list[float]:
    """Parse eigenvalue line from evec file."""
    tail = line.split(":", 1)[1] if ":" in line else line.replace("#eigvals", "")
    out = []
    for token in tail.split():
        try:
            out.append(float(token))
        except ValueError:
            continue
    return out


# ─── Eval parsing ────────────────────────────────────────────────


def parse_eval(
    path: Path | None, evec_path: Path
) -> tuple[list[float], list[str]]:
    """Parse .eval file for eigenvalues. Tries multiple candidates."""
    warnings: list[str] = []
    candidates: list[Path] = []

    if path is not None:
        if not path.exists():
            warnings.append(f"[parser] Explicit eval path not found: {path}")
        else:
            candidates.append(path)

    # Try common naming patterns
    candidates.append(evec_path.with_suffix(".eval"))
    if evec_path.name.endswith(".evec"):
        candidates.append(evec_path.with_name(evec_path.name[:-5] + ".eval"))

    # Try any .eval file in the same directory
    for sibling in evec_path.parent.glob("*.eval"):
        if sibling not in candidates:
            candidates.append(sibling)

    seen_files: set[Path] = set()
    for candidate in candidates:
        if candidate in seen_files:
            continue
        seen_files.add(candidate)
        if not candidate.exists():
            continue
        eigvals = []
        with candidate.open() as handle:
            for raw in handle:
                token = raw.strip().split()
                if not token:
                    continue
                try:
                    eigvals.append(float(token[0]))
                except ValueError:
                    warnings.append(
                        f"[parser] Ignoring non-numeric eval value in {candidate.name}: {raw.strip()}"
                    )
        if eigvals:
            return eigvals, warnings

    if path is not None:
        warnings.append(f"[parser] No valid eval data found from any candidate file")
    return [], warnings


# ─── Metadata parsing ────────────────────────────────────────────


def detect_meta_format(path: Path) -> str:
    """Detect metadata format (poplist vs csv)."""
    if not path.exists():
        return "poplist"
    with path.open() as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith("====") and stripped.endswith("===="):
                return "poplist"
            if "," in stripped:
                return "csv"
            break
    return "poplist"


def parse_metadata(
    path: Path, meta_format: str = "auto"
) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """Parse metadata (population→group mappings). Returns (mapping, pop_order, group_order, warnings)."""
    warnings: list[str] = []
    warnings.extend(check_file_exists(path, "Metadata file"))

    if not path.exists():
        return {}, [], [], warnings

    if meta_format == "auto":
        meta_format = detect_meta_format(path)
    if meta_format == "csv":
        return parse_metadata_csv(path)
    elif meta_format == "poplist":
        return parse_metadata_poplist(path)
    else:
        raise ValueError(f"Unsupported metadata format: {meta_format}")


def parse_metadata_csv(
    path: Path,
) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """Parse metadata from CSV format (population,group columns)."""
    mapping: dict[str, str] = {}
    pop_order: list[str] = []
    group_order: list[str] = []
    warnings: list[str] = []

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"population", "group"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"Metadata CSV must contain 'population' and 'group' columns. Found: {reader.fieldnames}"
            )
        for row_no, row in enumerate(reader, 2):  # 2 = header is line 1
            population = (row.get("population") or "").strip()
            group = (row.get("group") or "").strip()
            if not population or not group:
                warnings.append(
                    f"[parser] metadata CSV row {row_no}: missing population or group, skipping: {dict(row)}"
                )
                continue
            if population in mapping:
                if mapping[population] != group:
                    warnings.append(
                        f"[parser] Population {population!r} (row {row_no}) in multiple groups: "
                        f"{mapping[population]!r} vs {group!r}; keeping first"
                    )
                continue
            mapping[population] = group
            pop_order.append(population)
            if group not in group_order:
                group_order.append(group)

    if not mapping:
        warnings.append(f"[parser] No valid metadata entries found in: {path}")
    return mapping, pop_order, group_order, warnings


def parse_metadata_poplist(
    path: Path,
) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """Parse metadata from ====Group==== format."""
    mapping: dict[str, str] = {}
    pop_order: list[str] = []
    group_order: list[str] = []
    warnings: list[str] = []
    current_group = "Unknown"
    header_count = 0

    with path.open() as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue

            # Group header
            if line.startswith("====") and line.endswith("===="):
                header_count += 1
                current_group = re.sub(r"^=+|=+$", "", line).strip() or "Unknown"
                if current_group not in group_order:
                    group_order.append(current_group)
                continue

            population = line.split()[0]
            if not population:
                continue

            if population in mapping:
                if mapping[population] != current_group:
                    warnings.append(
                        f"[parser] Population {population!r} (line {line_no}) appears in "
                        f"{mapping[population]!r} and {current_group!r}; keeping first"
                    )
                continue

            if current_group == "Unknown" and header_count == 0:
                warnings.append(
                    f"[parser] Population {population!r} at line {line_no} appears before any ====Group==== header"
                )
                if current_group not in group_order:
                    group_order.append(current_group)

            mapping[population] = current_group
            pop_order.append(population)

    if header_count == 0:
        warnings.append(f"[parser] No '====Group====' headers found in poplist file; all samples assigned to 'Unknown'")

    if not mapping:
        warnings.append(f"[parser] No valid metadata entries found in: {path}")
    return mapping, pop_order, group_order, warnings


# ─── Poplist group extraction ────────────────────────────────────


def parse_poplist_groups(path: Path) -> tuple[list[str], list[str]]:
    """Parse a poplist file and return all group names (====Group==== headers).

    Returns (groups, warnings).
    """
    warnings: list[str] = []
    if not path.exists():
        warnings.append(f"[parser] Poplist not found: {path}")
        return [], warnings

    groups: list[str] = []
    with path.open() as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("====") and line.endswith("===="):
                group = re.sub(r"^=+|=+$", "", line).strip()
                if group:
                    groups.append(group)

    if not groups:
        warnings.append(f"[parser] No ====Group==== headers found in poplist: {path}")
    else:
        info(f"Parsed {len(groups)} groups from {path.name}")

    return groups, warnings


def info(message: str) -> None:
    """Print informational message (local helper, mirrors cli.info)."""
    print(f"✓ {message}")


# ─── Targets parsing ─────────────────────────────────────────────


def parse_targets(
    path: Path | None,
) -> tuple[list[dict[str, str]], list[str]]:
    """Parse targets CSV file. Returns (targets, warnings)."""
    warnings: list[str] = []
    if path is None:
        return [], warnings

    if not path.exists():
        warnings.append(f"[parser] Targets file not found: {path}")
        return [], warnings

    targets: list[dict[str, str]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "sample_id" not in reader.fieldnames:
            raise ValueError(
                f"Targets CSV must contain 'sample_id' column. Found: {reader.fieldnames}"
            )
        for row_no, row in enumerate(reader, 2):
            sample_id = (row.get("sample_id") or "").strip()
            if not sample_id:
                warnings.append(
                    f"[parser] Targets CSV row {row_no}: missing sample_id, skipping: {dict(row)}"
                )
                continue
            label = (row.get("label") or "").strip() or sample_id
            targets.append({"sample_id": sample_id, "target_label": label})

    if not targets:
        warnings.append(f"[parser] No valid target entries found in: {path}")
    return targets, warnings


# ─── Data merging ────────────────────────────────────────────────


def merge_data(
    pca_rows: list[dict[str, Any]],
    metadata: dict[str, str],
    targets: list[dict[str, str]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Merge PCA data with metadata and targets. Returns (merged_rows, warnings)."""
    warnings: list[str] = []

    target_map: dict[str, str] = {}
    for target in targets:
        if target["sample_id"] in target_map:
            warnings.append(
                f"[parser] Duplicate target sample_id: {target['sample_id']!r}; keeping first label"
            )
            continue
        target_map[target["sample_id"]] = target["target_label"]

    sample_ids = {row["sample_id"] for row in pca_rows}
    for sample_id in target_map:
        if sample_id not in sample_ids:
            warnings.append(
                f"[parser] Target sample_id {sample_id!r} not found in evec data"
            )

    missing_pops: set[str] = set()
    target_groups = set(config.get("target_groups", ["Target"]))
    modern_groups = set(config.get("modern_groups", []))
    modern_background = bool(config.get("modern_background", False))

    merged: list[dict[str, Any]] = []
    for row in pca_rows:
        population = row["population"]
        group = metadata.get(population)
        if group is None:
            group = "Unknown"
            missing_pops.add(population)

        metadata_target = group in target_groups
        target_label = target_map.get(
            row["sample_id"], row["sample_id"] if metadata_target else ""
        )
        is_target = row["sample_id"] in target_map or metadata_target
        is_modern_background = modern_background and group in modern_groups and not is_target

        merged.append(
            {
                "sample_id": row["sample_id"],
                "population": population,
                "group": group,
                "PC1": row["PC1"],
                "PC2": row["PC2"],
                "is_target": is_target,
                "target_label": target_label,
                "is_modern_background": is_modern_background,
            }
        )

    for population in sorted(missing_pops):
        warnings.append(
            f"[parser] Population {population!r} missing from metadata; assigned group 'Unknown'"
        )

    return merged, warnings


# ─── Ordering and style assignment ──────────────────────────────


def ordered_unique(values: list[str]) -> list[str]:
    """Return unique values preserving first-occurrence order."""
    return list(OrderedDict.fromkeys(values))


def build_orders(
    rows: list[dict[str, Any]],
    pop_order: list[str],
    group_order: list[str],
) -> tuple[list[str], list[str]]:
    """Build final group and population orders, incorporating observed data."""
    observed_groups = ordered_unique([row["group"] for row in rows])
    observed_pops = ordered_unique([row["population"] for row in rows])
    groups = (
        [g for g in group_order if g in observed_groups]
        + [g for g in observed_groups if g not in group_order]
    )
    pops = (
        [p for p in pop_order if p in observed_pops]
        + [p for p in observed_pops if p not in pop_order]
    )
    return groups, pops


def assign_styles(
    rows: list[dict[str, Any]],
    group_order: list[str],
    pop_order: list[str],
    config: dict[str, Any],
) -> Styles:
    """Assign colors and symbols to each row based on group/population order."""
    group_colors = {
        group: GROUP_PALETTE[idx % len(GROUP_PALETTE)]
        for idx, group in enumerate(group_order)
    }
    if len(group_order) > len(GROUP_PALETTE):
        print(
            f"WARNING: {len(group_order)} groups but only {len(GROUP_PALETTE)} palette colors; colors will repeat",
            file=sys.stderr,
        )

    for group in config.get("target_groups", ["Target"]):
        group_colors[group] = config.get("target_color", "#D81B60")

    pop_colors = {
        pop: POP_PALETTE[idx % len(POP_PALETTE)]
        for idx, pop in enumerate(pop_order)
    }
    if len(pop_order) > len(POP_PALETTE):
        print(
            f"WARNING: {len(pop_order)} populations but only {len(POP_PALETTE)} palette colors; colors will repeat",
            file=sys.stderr,
        )

    pop_symbols = {
        pop: SYMBOLS[idx % len(SYMBOLS)]
        for idx, pop in enumerate(pop_order)
    }

    if "Unknown" not in group_colors:
        group_colors["Unknown"] = "#999999"

    for row in rows:
        row["group_color"] = group_colors.get(row["group"], "#999999")
        row["population_color"] = pop_colors.get(row["population"], "#999999")
        row["symbol"] = pop_symbols.get(row["population"], "circle")

    return Styles(
        group_colors=group_colors,
        population_colors=pop_colors,
        population_symbols=pop_symbols,
    )


# ─── Legend / Summary helpers ────────────────────────────────────


def build_shape_legend(
    population_symbols: dict[str, str],
    pop_order: list[str],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build shape legend data for HTML rendering."""
    observed = {row["population"] for row in rows if not row.get("is_target")}
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for pop in pop_order:
        if pop not in observed:
            continue
        symbol = population_symbols.get(pop, "circle")
        grouped.setdefault(symbol, []).append(pop)
    return [{"symbol": symbol, "populations": pops} for symbol, pops in grouped.items()]


def build_grouped_population_legend(
    rows: list[dict[str, Any]],
    group_order: list[str],
    pop_order: list[str],
    population_symbols: dict[str, str],
) -> list[dict[str, Any]]:
    """Build grouped population legend (group → [populations]) for HTML."""
    pop_to_group: dict[str, str] = {}
    for row in rows:
        if row.get("is_target"):
            continue
        pop_to_group.setdefault(row["population"], row["group"])

    result = []
    for group in group_order:
        pops = [
            {"population": pop, "symbol": population_symbols.get(pop, "circle")}
            for pop in pop_order
            if pop_to_group.get(pop) == group
        ]
        if pops:
            result.append({"group": group, "populations": pops})
    return result


# ─── Bounds / Labels ─────────────────────────────────────────────


def bounds(rows: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    """Compute plot bounds with 6% padding."""
    xs = [float(row["PC1"]) for row in rows]
    ys = [float(row["PC2"]) for row in rows]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    dx = max(max_x - min_x, 1e-9)
    dy = max(max_y - min_y, 1e-9)
    return min_x - dx * 0.06, max_x + dx * 0.06, min_y - dy * 0.06, max_y + dy * 0.06


def explained_variance_labels(eigvals: list[float]) -> tuple[str, str]:
    """Generate axis labels with variance percentages."""
    if len(eigvals) >= 2 and sum(eigvals) > 0:
        total = sum(eigvals)
        return (
            f"PC1 ({eigvals[0] / total * 100:.2f}%)",
            f"PC2 ({eigvals[1] / total * 100:.2f}%)",
        )
    return "PC1", "PC2"


def resolve_project_prefix(project: str | None, targets: list[dict[str, str]]) -> str:
    """Determine project prefix from CLI arg or first target label."""
    if project:
        return sanitize_prefix(project)
    if targets and targets[0].get("target_label"):
        return sanitize_prefix(targets[0]["target_label"])
    return "smartpca_viz"
