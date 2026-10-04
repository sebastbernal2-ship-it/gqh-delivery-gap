# Declared: four-firm filing decisions labelled by point-in-time obligation surprises

Status: declared before the run, development only. Owner: sebas. Date: 2026-10-04.
Runners: `scripts/build_filing_obligation_panel.py`, `scripts/run_filing_obligation_panel.py`.

## Question

Does filing metadata forecast the next point-in-time obligation surprise for the four candidate
firms, against the training prevalence?

## Data

- `results/obligation-vintages.csv`: point-in-time seasonal expectations for the obligation panel,
  built by the same vintage machinery as the RPO panel with the concept added to the grouping key.
- `results/filings-register.csv`: the four-firm filing register with acceptance clocks.
- `results/filing-obligation-decisions.csv`: one row per filing that precedes a measured
  obligation vintage, labelled by that vintage's relative surprise in five declared bins with
  edges `(-0.10, -0.02, 0.02, 0.10)`.

## Views and why there are two

Filings map many-to-one onto disclosures, so the primary metric uses only the deciding filing per
disclosure: 87 rows over about 50 distinct disclosure periods. The every-filing view, 8,185 rows,
reuses each label many times and is reported as a robustness row with its distinct-label count,
never as independent evidence.

## Features

Known strictly before each decision: prior obligation count, last and trailing relative change,
days since the last obligation, a missingness flag, form and item flags, and a concept flag.

## Split and comparison

Chronological split at 70 percent of label times, never across a shared timestamp. Training
prevalence beside the fitted multinomial logistic regression on log loss, Brier and accuracy.

## Falsifier

The fitted model does not beat prevalence on the later rows of the deciding view.

## Ceiling

PWR and ETN only; EME and DLR file no measured obligation facts. About 50 effective disclosure
periods, metadata only, no text, no returns and no costs.

## Text results

| View | Model | Log loss | Brier | Accuracy |
|---|---|---|---|---|
| Deciding, 61/26 | Prevalence | 1.558 | 0.763 | 0.577 |
| | Metadata | 1.238 | 0.650 | 0.538 |
| | Text | 1.290 | 0.659 | 0.538 |
| | Both | **1.214** | 0.658 | 0.462 |
| Every filing, 4,157/1,734 | Prevalence | 1.287 | 0.656 | 0.561 |
| | Metadata | 1.196 | 0.629 | 0.556 |
| | Text | 1.290 | 0.650 | 0.561 |
| | Both | **1.192** | **0.627** | 0.561 |

Text adds a little on top of metadata and loses as a standalone block here, unlike the revision
panel where text alone won. Runner: `hpc/probabilistic-council/run_filing_obligation_text.py`.
