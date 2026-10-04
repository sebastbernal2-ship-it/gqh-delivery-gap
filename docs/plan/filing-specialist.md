# Declared: the filing specialist v0, the equity bridge

Status: declared before the run, development only. Owner: sebas. Date: 2026-10-04.
Runners: `scripts/build_filing_specialist_panel.py`, then `scripts/run_filing_specialist.py`.

## Question

Given a filing that is public at a known time, what is the distribution over the sign and size of
the **next obligation revision's surprise** for the same issuer and concept?

This is the expectation gap in its smallest testable form: the filing is the public act, the
revision is the later delivery fact, and the label is the revision measured against its own
previous value. It does not test the equity response; that is a later gate.

## Decision and label

- **Decision time**: the availability of the latest filing strictly before the revision's
  availability. A filing at or after the label is not usable.
- **Label**: the relative surprise, `surprise / |previous_value|`, of the revision, binned with
  left-closed edges `(-0.05, -0.01, 0.01, 0.05)` into
  `slip-large, slip-small, flat, beat-small, beat-large`.
- **Clocks**: `earliest_availability_utc` where present; otherwise acceptance, otherwise the filed
  date read as end of day UTC and flagged as coarse. The `decision_clock_coarse` column carries
  the flag.

## Features

All known strictly before the decision time, from the filings register and the obligation panel:
form flags, 8-K item flags, filings in the last 90 days, days since the previous filing, the last
and trailing obligation changes relative to their own previous values, the prior revision count,
the last revision's relative surprise, days since the last obligation, and a concept flag.

An unknown feature stays null and carries a missingness flag. The model imputes with the training
median and standardises with training-only statistics. No future row can enter a feature.

## Data

- `results/filings-register.csv`: 776 filings for PWR, ETN, EME and DLR, 2015 to 2026, with
  acceptance clocks and 8-K item codes.
- `results/obligation-panel.csv`: 130 obligation facts for PWR and ETN, with availability clocks.
- `results/revision-events.csv`: the label source, 84 revisions with `surprise` and
  `typical_change`, published 2015 to 2024. EME and DLR have no obligation facts, so the panel is
  PWR dominated and the effective breadth is smaller than the row count.

## Split and comparison

Chronological split at 70 percent of the label dates. Two models on the same split:

1. the training prevalence, Laplace smoothed;
2. a multinomial logistic regression with an L2 penalty, fitted on training rows only.

Metrics: log loss, multiclass Brier, accuracy, and per-class support. Both models are reported
whether or not the fit wins.

## Falsifier

The fitted baseline does not beat the training prevalence on the later rows, or the panel cannot
be built with every feature strictly earlier than its label. Either outcome is reported as is.

## Ceiling

84 revisions, one issuer dominates, metadata-only features, both competition windows spent. This
is a point-in-time plumbing result and a baseline, not a trading claim. The declared next step is
the filing text and the JevLike scorer on the same rows, with this baseline as the equal-budget
comparator.

## Results so far, all on the same 58/23 split

| Model | Log loss | Brier | Accuracy |
|---|---|---|---|
| Training prevalence | 1.599 | 0.782 | 0.435 |
| Metadata softmax (15 features) | 1.679 | 0.750 | 0.478 |
| JevLike tiny byte encoder, scratch, 30 epochs | 1.847 | 0.861 | 0.391 |
| Frozen all-MiniLM-L6-v2 encoder, 75k trainable head, 30 epochs | 1.853 | 0.848 | 0.217 |

Both text variants lose to prevalence on log loss, and the frozen encoder loses on every metric. With 58 training rows and a dominant flat class, the text representation does not carry learnable signal for this task yet. Recorded levers, in order: point-in-time expectation vintages to raise the label count, a calibrated head with fewer free parameters, and a class-balanced objective. Neither text run is a claim of failure for the mechanism; both are recorded negatives at this sample size.

## Text versus metadata, three ways on one split

| Model | Log loss | Brier | Accuracy |
|---|---|---|---|
| Training prevalence | 1.599 | 0.782 | 0.435 |
| Metadata only, 15 features | 1.679 | 0.750 | 0.478 |
| Frozen text only, 8 PCA components | **1.508** | **0.741** | 0.391 |
| Metadata and text concatenated | 1.746 | 0.748 | 0.478 |

The text alone carries information that the metadata does not, on both proper scores, while giving
up accuracy. Concatenating the two blocks inside one linear head makes log loss worse, so the next
method is a stacking or gating layer, not more features. Runner:
`hpc/probabilistic-council/run_filing_text_ab.py`; result: `results/filing-text-ab.json`.
