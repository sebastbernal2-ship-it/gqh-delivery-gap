# src/event

What a firm's own disclosed revision did to its own price.

The event is a number the firm published, so the attribution is unambiguous and the timestamp is the
filing's own acceptance time. That is why this channel exists: the project-level join does not hold, since
93.8 percent of slipped capacity sits with project companies and private developers.

## the three rules it enforces

1. **Lag every signal.** A revision is usable at its availability timestamp, and the fill is the close of
   the first session strictly after it. Same-bar fills are refused by construction, not by convention.
2. **Abnormal, not raw.** Market and sector movement is the first alternative explanation, so raw and
   benchmark-adjusted returns are reported side by side.
3. **Expectation first.** `revision_surprise` is current public value minus the earlier public expectation.
   A typical historical change is not a market expectation.
4. **A plateau, not a peak.** Horizons of 1, 2, 5, 10 and 20 sessions are all reported, and nothing here
   elects a winner. The primary horizon must be declared before the sealed test, and picking the best cell
   afterwards would be tuning on the development window.

## Owner

`sebastbernal2-ship-it` claims `src/event/` in `OWNERS.md`.

## Use

```sh
python scripts/run_revision_event_study.py --horizons 1,2,5,10,20
```

It reads `results/obligation-panel.csv` and writes `results/revision-events.csv`.

For a reproducible run using centralized, hash-pinned inputs (no live Yahoo/yfinance fetch), use:

```sh
.venv/bin/python scripts/run_warehouse_revision_event_study.py \
  --event-batch-sha256 7beffd642ed1389829b72fb2a3cda8e0b657f6a10761a56fc0c084350c0846f2
```

This reads the SEC XBRL-derived event batch and Massive adjusted daily bars from Snowflake,
including retained SPY, XLI and XLRE controls. It currently writes
`results/revision-events-snowflake.csv` plus a JSON provenance/limitations receipt. In the pinned
development panel there are 84 eligible event rows but only 52 distinct accessions, across PWR
and ETN; the event facts are RPO and unapproved-change-order amounts. They are **not** analyst
consensus surprises. EME and DLR price series are present, but comparable event facts are not.
The run reports descriptive raw and market/sector abnormal returns at 1/2/5/10/20 sessions; it
does not infer a strategy, significance or causal effect. Overlapping return windows and repeated
issuer/accession exposures make row count larger than independent information.

Both exact output files are also upserted into Snowflake `VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS`,
keyed by artifact name and SHA-256 and linked to the event, price, and dividend batch hashes. The
committed `results/` files are review copies; Snowflake is the shared retrieval point for the run.

The older script above is retained for development comparison. The Snowflake-backed run is the
reproducible shared-data path; do not cite the older yfinance output as if it were sourced from
the warehouse batches.

## What the first pass found, and why it is not a result

Eighty-four timestamped revisions across PWR and ETN. Negative surprises, the direction the mechanism
predicts, show no consistent move at any horizon. Positive surprises drift 3.8 percent at twenty sessions,
but 70 of the 84 events are PWR across 41 weeks, so that is one firm's multi-year run as much as an event
effect. The rubric's own instruction is to check the simple explanation first, and the simple explanation
here is drift.
