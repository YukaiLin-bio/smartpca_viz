# Rev4 reproduction notes

This source release corresponds to the accepted rev4 `smartpca_viz` renderer and its lower legend layout. It preserves the rev4 policy that target samples are directly labelled in Nature mode and modern background labels are aggregated by `population` centroid.

## Included examples

- `examples/rev4_config.yaml` is the configuration emitted by the accepted rev4 Monk PCA run.
- `examples/monk_targets.csv` uses the stable two-column target contract: `sample_id,label`.

## Inputs deliberately not included

The source release does not include the smartpca `.evec`, `.eval`, poplists, population metadata, generated PCA figures, merged data tables, or run logs. Those are analysis-specific inputs/outputs and should be preserved with their own provenance.

## Reproduction contract

Use a matched `.evec`/`.eval` pair and the same population metadata, population lists, configuration, and targets file that define the analysis. Confirm that the generated run log records the input paths, sample count, population count, target count, renderer, modern label mode, and output paths before interpreting the figure.

The example configuration is not evidence that a different PCA dataset shares the same PC orientation, population placement, or genetic interpretation. Align axes and preserve the smartpca input provenance before comparing PCA outputs.
