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
