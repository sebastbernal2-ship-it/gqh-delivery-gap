# Declared: the council as the combiner of the two evidence blocks

Status: declared before the run, development only. Owner: sebas. Date: 2026-10-04.
Runner: `scripts/run_filing_council.py`.

## Question

Does the council combine filing metadata and document text better than either block alone, better
than the naive concatenation, and better than the training prevalence?

The text A/B (truth T38) showed each block carries information the other does not, and that
concatenating them inside one linear head makes log loss worse. The declared next method was
stacking or gating. The council is this repository's stacking layer: temperature calibration, a
reliability gate and a pool fitted on separate chronological partitions.

## Data and blocks

The 81-label four-firm filing panel with the cached frozen embeddings. Five chronological blocks:

| Block | Rows | Purpose |
|---|---|---|
| training | 34 | fit each block specialist |
| calibration | 8 | specialist temperatures |
| gate | 8 | reliability weights |
| pool | 8 | pool temperature |
| evaluation | 23 | the only scored block |

No row appears in two blocks, and no block crosses a shared timestamp.

## Clocks

Every forecast ends at its reveal: `information_cutoff` is the previous row's availability in the
same block, `forecast_time` is one second before the reveal, `valid_until` is the reveal itself.
The text block is reduced by PCA fitted on the training rows only.

## Comparison

Scored on the evaluation block: training prevalence, metadata alone, text alone, concatenated, and
the council. Metrics: log loss, multiclass Brier, accuracy.

## Falsifier

The council does not beat the better single block on the proper scores. Either outcome is the
result.

## Ceiling

81 labels, PWR dominated, and the three council partitions hold eight rows each, so gate weights
are effectively global and the pool temperature is fitted on very little. A council win here is
suggestive, not established; a council loss may be the sample rather than the method.

## Results

| Model | Log loss | Brier | Accuracy |
|---|---|---|---|
| Training prevalence | 1.728 | 0.841 | 0.000 |
| Metadata alone | 3.130 | 0.988 | 0.300 |
| Text alone | 2.044 | 0.914 | 0.150 |
| Metadata and text concatenated | 2.828 | 0.978 | 0.350 |
| Council | **1.705** | **0.821** | 0.300 |

Blocks: 34 training, 9 calibration, 9 gate, 9 pool, 20 evaluation. Gate weights 0.485 metadata
and 0.515 text, so calibration and pooling carry the gain rather than reliability reweighting.
The council wins on both proper scores and gives up top-class accuracy, which is the expected
shape when the combiner is calibrated. Single-model scores are worse than in the 58/23 text A/B
because the block specialists here train on 34 rows. Thin sample, declared ceiling, no promotion.
