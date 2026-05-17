"""Tests for the parser module."""

from __future__ import annotations

from pathlib import Path
from smartpca_viz.parser import (
    parse_evec,
    parse_eigvals_line,
    parse_eval,
    parse_metadata,
    parse_metadata_csv,
    parse_metadata_poplist,
    parse_targets,
    merge_data,
    build_orders,
    assign_styles,
    bounds,
    explained_variance_labels,
    resolve_project_prefix,
    check_file_exists,
)


class TestCheckFileExists:
    def test_existing_file(self):
        path = Path(__file__)
        warns = check_file_exists(path, "test")
        assert len(warns) == 0

    def test_missing_file(self, tmp_path):
        missing = tmp_path / "nope.txt"
        warns = check_file_exists(missing, "test")
        assert len(warns) == 1
        assert "not found" in warns[0]


class TestParseEvec:
    def test_real_evec(self):
        evec = Path(__file__).parent.parent.parent / "smartpca.evec"
        rows, eigvals, warns = parse_evec(evec)
        assert len(rows) > 0
        assert len(eigvals) > 0
        assert "sample_id" in rows[0]
        assert "population" in rows[0]
        assert "PC1" in rows[0]

    def test_empty_file(self, tmp_path):
        empty = tmp_path / "empty.evec"
        empty.write_text("")
        rows, eigvals, warns = parse_evec(empty)
        assert len(rows) == 0

    def test_missing_file(self, tmp_path):
        missing = tmp_path / "missing.evec"
        rows, eigvals, warns = parse_evec(missing)
        assert len(rows) == 0
        assert any("not found" in w for w in warns)


class TestParseEigvalsLine:
    def test_basic(self):
        assert parse_eigvals_line("#eigvals: 1.0 2.0 3.0") == [1.0, 2.0, 3.0]

    def test_no_colon(self):
        vals = parse_eigvals_line("#eigvals 0.5 1.5")
        assert len(vals) == 2

    def test_mixed_validity(self):
        vals = parse_eigvals_line("#eigvals: 1.0 abc 3.0")
        assert vals == [1.0, 3.0]


class TestParseEval:
    def test_real_eval(self):
        eval_path = Path(__file__).parent.parent.parent / "smartpca.eval"
        evec_path = Path(__file__).parent.parent.parent / "smartpca.evec"
        vals, warns = parse_eval(eval_path, evec_path)
        assert len(vals) > 0

    def test_missing_file(self, tmp_path):
        missing = tmp_path / "missing.eval"
        evec = Path(__file__).parent.parent.parent / "smartpca.evec"
        vals, warns = parse_eval(missing, evec)
        # Should still find from sibling pattern
        assert len(vals) > 0


class TestParseMetadata:
    def test_real_poplist(self):
        path = Path(__file__).parent.parent.parent / "poplist.txt"
        mapping, pop_order, group_order, warns = parse_metadata(path)
        assert len(mapping) > 0
        assert len(group_order) > 0
        assert len(pop_order) > 0

    def test_missing_file(self, tmp_path):
        missing = tmp_path / "missing.txt"
        mapping, pop_order, group_order, warns = parse_metadata(missing)
        assert len(mapping) == 0
        assert any("not found" in w for w in warns)


class TestMetaPoplist:
    def test_basic_structure(self, tmp_path):
        f = tmp_path / "test.poplist"
        f.write_text("====Group1====\nPopA\nPopB\n\n====Group2====\nPopC\n")
        mapping, pop_order, group_order, warns = parse_metadata_poplist(f)
        assert mapping == {"PopA": "Group1", "PopB": "Group1", "PopC": "Group2"}
        assert group_order == ["Group1", "Group2"]

    def test_duplicate_population(self, tmp_path):
        f = tmp_path / "dup.poplist"
        f.write_text("====G1====\nPopA\n====G2====\nPopA\n")
        mapping, pop_order, group_order, warns = parse_metadata_poplist(f)
        assert "PopA" in mapping
        assert len([w for w in warns if "appears in" in w]) == 1

    def test_no_headers(self, tmp_path):
        f = tmp_path / "noheader.poplist"
        f.write_text("PopA\nPopB\n")
        mapping, pop_order, group_order, warns = parse_metadata_poplist(f)
        assert mapping == {"PopA": "Unknown", "PopB": "Unknown"}
        assert any("headers" in w for w in warns)

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.poplist"
        f.write_text("")
        mapping, pop_order, group_order, warns = parse_metadata_poplist(f)
        assert len(mapping) == 0


class TestMetaCsv:
    def test_basic_csv(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("population,group\nPopA,Group1\nPopB,Group2\n")
        mapping, pop_order, group_order, warns = parse_metadata_csv(f)
        assert mapping == {"PopA": "Group1", "PopB": "Group2"}

    def test_missing_column(self, tmp_path):
        f = tmp_path / "bad.csv"
        f.write_text("name,value\nx,1\n")
        import pytest
        with pytest.raises(ValueError, match="must contain"):
            parse_metadata_csv(f)


class TestParseTargets:
    def test_basic(self, tmp_path):
        f = tmp_path / "targets.csv"
        f.write_text("sample_id,label\nS1,Target1\nS2,Target2\n")
        targets, warns = parse_targets(f)
        assert len(targets) == 2
        assert targets[0]["sample_id"] == "S1"
        assert targets[0]["target_label"] == "Target1"

    def test_missing_file(self, tmp_path):
        targets, warns = parse_targets(tmp_path / "missing.csv")
        assert len(targets) == 0
        assert any("not found" in w for w in warns)

    def test_none_path(self):
        targets, warns = parse_targets(None)
        assert len(targets) == 0
        assert len(warns) == 0

    def test_missing_id_uses_self(self, tmp_path):
        f = tmp_path / "targets.csv"
        f.write_text("sample_id\nS1\n")
        targets, warns = parse_targets(f)
        assert targets[0]["target_label"] == "S1"


class TestMergeData:
    def test_basic_merge(self):
        rows = [{"sample_id": "S1", "population": "PopA", "PC1": 0.1, "PC2": -0.2}]
        metadata = {"PopA": "Group1"}
        config = {"target_groups": ["Target"], "modern_groups": [], "modern_background": False}
        merged, warns = merge_data(rows, metadata, [], config)
        assert len(merged) == 1
        assert merged[0]["group"] == "Group1"
        assert merged[0]["is_target"] is False

    def test_target_group(self):
        rows = [{"sample_id": "S1", "population": "PopA", "PC1": 0.1, "PC2": -0.2}]
        metadata = {"PopA": "Target"}
        config = {"target_groups": ["Target"], "modern_groups": [], "modern_background": False}
        merged, warns = merge_data(rows, metadata, [], config)
        assert merged[0]["is_target"] is True

    def test_missing_population(self):
        rows = [{"sample_id": "S1", "population": "MissingPop", "PC1": 0.1, "PC2": -0.2}]
        metadata = {"PopA": "Group1"}
        config = {"target_groups": ["Target"], "modern_groups": [], "modern_background": False}
        merged, warns = merge_data(rows, metadata, [], config)
        assert merged[0]["group"] == "Unknown"
        assert any("missing from metadata" in w for w in warns)


class TestBounds:
    def test_basic(self):
        rows = [{"PC1": 0.0, "PC2": 0.0}, {"PC1": 1.0, "PC2": 1.0}]
        min_x, max_x, min_y, max_y = bounds(rows)
        assert min_x < 0  # padding
        assert max_x > 1

    def test_single_point(self):
        rows = [{"PC1": 0.5, "PC2": 0.5}]
        min_x, max_x, min_y, max_y = bounds(rows)
        assert max_x > min_x


class TestExplainedVariance:
    def test_with_eigvals(self):
        x_l, y_l = explained_variance_labels([30.0, 20.0, 10.0])
        assert "50.00%" in x_l  # 30/60
        assert "33.33%" in y_l  # 20/60

    def test_empty(self):
        x_l, y_l = explained_variance_labels([])
        assert x_l == "PC1"

    def test_single(self):
        x_l, y_l = explained_variance_labels([10.0])
        assert x_l == "PC1"


class TestResolveProject:
    def test_cli_arg(self):
        assert resolve_project_prefix("MyProject", []) == "MyProject"

    def test_from_target(self):
        targets = [{"target_label": "Sample1"}]
        assert "Sample1" in resolve_project_prefix(None, targets)

    def test_fallback(self):
        assert resolve_project_prefix(None, []) == "smartpca_viz"
