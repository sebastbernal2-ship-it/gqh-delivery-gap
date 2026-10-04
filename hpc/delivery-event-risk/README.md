# Delivery revision event risk on HiPerGator

Owner: `lucyrunner`. This CPU-only C++17 research runner measures stock and benchmark returns around
reviewed, public delivery/capacity revisions, attaches past-only volatility states, and reports
historical severe-stress observations. It does not fetch data, place trades, predict black-swan
probabilities, or establish alpha.

## Research question

Does a source-backed revision to an earlier public expectation have a different subsequent return
and downside profile when market volatility was already high? The event return is the outcome. The
volatility and liquidity measurements use only daily bars before the event's UTC calendar date. A
severe-stress label means that the last completed SPY session before the event was in the lower 1%
of its preceding 252 daily returns. This is a past-only historical stress marker, not a forecast.

The output is exploratory. The existing event sample is small and concentrated in PWR, and the
existing project-level delivery hazard is not an equity-return signal. Report the number of distinct
event clusters for every regime; repeated company disclosures about one shared shock do not become
independent observations.

## Inputs

The job accepts private, explicitly staged files. It never connects to Snowflake, TigerData, SEC,
Massive, or the public internet from a compute node.

`events.csv` has one row per source-reviewed company disclosure and these columns:

```text
event_id,event_cluster_id,ticker,metric_key,unit,available_at_utc,
expectation_available_at_utc,expectation_type,prior_expectation,current_value,
review_status,exposure_status,sector_symbol,document_sha256,in_sealed_window
```

The expectation must be comparable to the current value in metric, unit, scope, and target period.
The first supported baseline is prior public management guidance, so `expectation_type` must be
`management_guidance`; analyst consensus is not inferred. `review_status` must be `reviewed`,
`exposure_status` must be `verified`, and the document hash must be lowercase SHA-256. Unqualified
rows are retained in the event output with an exclusion reason. A row marked `in_sealed_window=true`
is skipped before its outcome fields are read.

`bars.tsv` is a retained daily close export with the KDB exporter columns:

```text
date sym source_id batch_sha256 row_index open_px_e8usd high_px_e8usd \
low_px_e8usd close_px_e8usd volume row_sha256
```

Prices are integer `1e-8 USD` values. Each symbol must come from one source/batch pair; duplicate
symbol/date rows and malformed row or batch hashes are rejected. Include each event ticker and `SPY`.
Include its `sector_symbol` too to get sector-adjusted outcomes. If a sector series is absent, the
runner leaves sector results blank and says so; it never substitutes another benchmark silently.
Only rows dated before the supplied sealed cutoff are parsed for prices.

`bars.tsv.manifest.json` is produced by the included
[`export_event_bars.py`](export_event_bars.py), which reads one explicitly selected TigerData batch,
checks it against the ingestion manifest, validates the source prices and provenance, and preserves
the source volume value as a decimal. Volume is not used by this analysis; the shared KDB exporter
requires integer volume and therefore rejects some adjusted-bar rows. `events.manifest.json` is
created with the included helper after the reviewed development event panel is frozen. Both input
files are hash-checked before analysis. The event manifest records the development role, explicit
date fences, source document hashes, row count and full file SHA-256.

Export a verified bar batch on a machine with the project’s TigerData read access and
`psycopg[binary]` installed:

```sh
python3 hpc/delivery-event-risk/export_event_bars.py \
  --batch massive_bars=<selected-batch-sha256> \
  --output /private/staging/bars.tsv
```

Provide `TIGERDATA_URL` and `TIGERDATA_PASSWORD` through the local environment or an ignored `.env`
file. The exporter writes the TSV and sidecar outside Git; transfer both to the approved Blue
staging directory before submitting the compute job.

Create the event manifest once the upstream event rows have passed human review and the development
cutoff is frozen:

```sh
python3 hpc/delivery-event-risk/make_event_manifest.py \
  --events /private/staging/events.csv \
  --development-start 2015-07-01 --sealed-start 2022-10-01 \
  --out /private/staging/events.manifest.json
```

The command records file integrity and the declared role; it does not certify the underlying
expectation, review, or exposure judgments. Create it beside the source export, then transfer both
files together. The bar export must also contain only dates before the sealed cutoff.

The current checked-in `results/obligation-panel.csv` is not directly eligible as `events.csv`: its
prior-period value is not automatically an earlier management expectation, and it does not itself
contain the reviewed exposure and event-cluster decisions required here. This runner therefore
produces only synthetic smoke output until the data owner supplies a qualifying event panel and
manifest.

## Calculations

- `surprise = current_value - prior_expectation`. A robust surprise score is reported only after at
  least five earlier eligible, distinct clusters for the same ticker, metric and unit. Its median and
  median absolute deviation are computed from those earlier events only.
- 20-session realized volatility for the issuer and SPY is annualized from daily log returns through
  the last completed session strictly before the event's UTC date.
- `high_vol` means SPY realized volatility exceeds the 80th percentile of up to 252 earlier daily
  realized-volatility observations, with at least 126 required. Otherwise the regime is `warmup`.
- Event entry is conservatively the first available daily session whose date is later than the event's
  UTC date. Return horizons are 1, 2, 5, 10 and 20 sessions. Outcomes that reach the sealed cutoff
  are blank and excluded from summary statistics.
- The runner reports raw, market-adjusted (`stock - SPY`), and, when supplied, sector-adjusted
  returns. Adjusted returns are blank unless the instrument and benchmark have matching entry and
  exit sessions, so missing or halted bars cannot silently compare different windows. It also
  reports unadjusted Pearson association between the past-only surprise score and
  subsequent benchmark-adjusted returns. This is descriptive, not a fitted trading rule. Long and
  short stock-return cost sensitivities at five sessions are shown at the configured cost per
  execution side and at twice that cost. The cost is an assumption, not a measured spread or a
  validated strategy cost; short borrow is not included.
- Tail-shock tagging uses the SPY return at the last completed session and a lower-tail 1% threshold
  from its prior 252 sessions. Too little history yields `unknown`, not a guessed label.

No model chooses a horizon, predicts rare-event frequency, or opens a sealed window. A small count of
independent event clusters in a regime is reported as a limitation, not repaired with synthetic data.

## HiPerGator run

The Slurm scripts compile with the system `g++` using C++17 and the standard library only. They use a
single CPU, require no GPU or package installation, and make no network calls. Transfer the frozen
events CSV, its manifest, the selected bars TSV, and the KDB exporter manifest to approved Blue
storage before submission. Do not put these inputs or outputs in Git.

From the login node, set absolute paths visible to compute nodes:

```sh
export GQH_REPO_ROOT=/absolute/shared/path/to/gqh-delivery-gap
export GQH_EVENT_CSV=/blue/<allocation>/<project>/staging/events.csv
export GQH_EVENT_MANIFEST=/blue/<allocation>/<project>/staging/events.manifest.json
export GQH_BARS_TSV=/blue/<allocation>/<project>/staging/bars.tsv
export GQH_BARS_MANIFEST=/blue/<allocation>/<project>/staging/bars.tsv.manifest.json
export GQH_DEVELOPMENT_START=2015-07-01
export GQH_SEALED_START=2022-10-01
export GQH_OUTPUT_DIR=/blue/<allocation>/<project>/runs/event-risk-v001
sbatch "$GQH_REPO_ROOT/hpc/delivery-event-risk/run.slurm"
```

Use the actual cut dates frozen for the selected study; the example dates above are illustrative and
must not be copied without checking its protocol. The job rejects missing, relative, invalid, or
already-used paths. Slurm logs go to the submission directory. A successful run writes
`event-outcomes.csv`, `regime-summary.csv`, `surprise-association.csv`, `report.md`,
`run-metadata.json`, and a verified `input-receipt.json` into the new output directory. The metadata
records cutoffs, thresholds, exclusions, cost assumptions and bar batch IDs.

## Synthetic HPG smoke check

This validates compilation, file contracts, the sealed fence, as-of volatility, and output creation;
it is not market evidence. Run from the login node:

```sh
export GQH_REPO_ROOT=/absolute/shared/path/to/gqh-delivery-gap
sbatch "$GQH_REPO_ROOT/hpc/delivery-event-risk/smoke.slurm"
```

The job generates all fixtures in `$SLURM_TMPDIR`, compiles there, and removes them at job end. It
does not touch real inputs or `results/`.
