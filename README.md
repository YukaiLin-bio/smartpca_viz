# smartpca_viz

`smartpca_viz` turns smartpca PC1/PC2 results into an interactive HTML plot and publication-ready PDF/SVG outputs.

This release is a clean source snapshot of the accepted rev4 renderer. It includes source code, templates, tests, a reusable configuration example, and a stable target CSV example. It intentionally does not bundle PCA inputs, population metadata, or generated figures.

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

For an installable command-line tool:

```bash
.venv/bin/python -m pip install .
smartpca-viz --help
```

## Run

```bash
python -m smartpca_viz \
  --evec smartpca.evec \
  --eval smartpca.eval \
  --modern-poplist modern.poplist \
  --ancient-poplist ancient.poplist \
  --targets examples/monk_targets.csv \
  --config examples/rev4_config.yaml \
  --project monk_pca \
  --out output
```

Required inputs are a matched smartpca `.evec`/`.eval` pair, metadata supplied as a CSV or poplist, and optionally a target CSV with columns `sample_id,label`.

## Outputs

- `*_pca_plot.pdf` — static publication figure.
- `*_pca_plot.svg` — editable vector version of the static figure.
- `*_pca_interactive.html` — searchable, hoverable interactive figure.
- `*_pca_report.pdf` — run summary report.
- `*_pca_merged_data.csv` — data rendered by the figures.
- `*_config.yaml`, `*_README.txt`, and `*_run.log` — reproducibility records.

## Rev4 visual policy

The Nature static renderer uses one direct centroid label per modern `population`; it does not label individual modern samples. Dense PCA regions may have local population-label overlap. This is an accepted readability trade-off for broad background identification; use the interactive HTML hover, search, and population filters for exact lookup. The lower legend is sized from actual Matplotlib text measurements to avoid long group-name collisions.

## Verify

```bash
python -m compileall smartpca_viz
PYTHONPATH=. python -m smartpca_viz --help
PYTHONPATH=. python -m pytest -q smartpca_viz/tests
python -m build --wheel
```

The `RELEASE_MANIFEST.sha256` file records the release-tree source hashes. See `REV4_REPRODUCTION.md` for the release scope and reproduction notes.
