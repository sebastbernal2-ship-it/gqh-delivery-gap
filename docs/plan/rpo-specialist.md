# Declared: the RPO surprise specialist on point-in-time vintages

Status: declared before the run, development only. Owner: sebas. Date: 2026-10-04.
Runner: `scripts/run_rpo_specialist.py`.

## Why this panel and not the four-firm filing panel

The four candidate firms have only 44 measured RPO vintages between them (PWR 22, EME 22, and
none for ETN or DLR), fewer than the 81 labels the filing panel already had. The larger sample
lives in the RPO names themselves: 2,803 measured vintages across 236 issuers, led by the
datacenter group. The filing-based bridge keeps its own panel; this study tests whether the
expectation gap is predictable at all, at a sample that can support the question.

## Question

Given an issuer's own disclosure history, what is the distribution over the sign and size of its
next RPO surprise, measured against a point-in-time expectation?

## Decision, label and clocks

- **Decision**: one RPO disclosure, with its `earliest_availability_utc` as the clock.
- **Label**: the relative point-in-time surprise, `surprise_pit / |previous_value|`, binned with
  left-closed edges `(-0.10, -0.02, 0.02, 0.10)` into
  `surprise-down-large, surprise-down-small, flat, surprise-up-small, surprise-up-large`.
  The edges were chosen from the observed distribution: the five bins hold 460, 584, 591, 634
  and 513 rows, so no class is starved.

## Features

All strictly earlier than the decision: the last and trailing mean relative surprises, the last
and trailing mean relative changes, the volatility of the last four relative changes, days since
the prior disclosure, the count of prior disclosures, the seasonal history count and span from
the vintage record, the log prior value, the quarter number, four group flags, and two
missingness flags. Missing values stay null and are imputed with training medians only.

## Split and comparison

Chronological split at 70 percent of the decision times, never across a shared timestamp. The
training prevalence is reported beside the fitted multinomial logistic regression, on log loss,
multiclass Brier, accuracy and per-class support.

## Falsifier

The fitted model does not beat the training prevalence on the later rows. Either outcome is the
result.

## Ceiling

No returns, no costs, no trading claim. Availability is end-of-day for most disclosures, ticker
identity is the current ticker, and both competition windows are spent. A pass here would mean
the expectation gap is predictable and worth carrying into the council; a fail would mean the
gap is real but not forecastable from a name's own history alone.
