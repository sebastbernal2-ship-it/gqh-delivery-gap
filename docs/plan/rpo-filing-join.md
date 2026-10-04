# Declared: does what a firm filed add anything to what it already disclosed?

Status: declared before the run, development only. Owner: sebas. Date: 2026-10-04.
Runner: `scripts/run_rpo_filing_panel.py`.

## Question

For an issuer's next RPO surprise, do the features of its latest filing add information beyond
the issuer's own disclosure history?

This is the equity bridge at its narrowest. If filings add nothing to the history, the filing
route into the expectation gap is decoration; if they add something, the bridge earns its place.

## Data

- `results/rpo-vintages.csv`: 2,803 measured point-in-time expectations across 236 issuers.
- `results/filings-register-rpo.csv`: 27,673 filings across 197 of those issuers, with acceptance
  clocks, built by `scripts/build_filings_register.py` for the RPO name list.

## Join rule

For each decision, the latest filing for the same ticker **strictly before** the disclosure's
availability, and only from the filing metadata: form, 8-K item flags, filings in the last 90
days, days since the last filing, days since the last 8-K, and a `has_filing` flag. An issuer
with no filing keeps nulls and a zero flag. No document text is used in this comparison.

## Comparison

Two models on the same rows and the same chronological split at 70 percent, never across a shared
timestamp: the history features alone, and the history plus the filing features. Training
prevalence is reported beside both. Metrics: log loss, multiclass Brier, accuracy.

## Falsifier

The filing features do not improve the proper scores over the history-only model. Either outcome
is the result.

## Ceiling

Metadata only, one filing per decision, no returns and no costs, both competition windows spent.
The text side of the bridge is tested separately on the four-firm panel.
