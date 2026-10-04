[Pricing-the-Buildout (4).pdf](https://github.com/user-attachments/files/33027927/Pricing-the-Buildout.4.pdf)

# Pricing the Buildout

**A point-in-time study of the AI buildout: what the delivery chain promised, what it delivered, and which equity signals survive our own controls.**

Gator Quant Hacks 2026, Systematic Trading track (callsign VECTOR).

## What this is

Two studies on one question: when infrastructure is sold before it is built, who pays for the gap between promise and delivery?

- **The delivery study.** 6,407 generators across monthly plan vintages, 3,783 schedule revisions with their disclosure clocks, every number dated to when it was knowable.
- **The intensity study.** 55 issuers in six peer groups paid by the same capital cycle. The signal is the year-over-year change in investment intensity (capex / revenue), ranked inside each peer group, gated on whether revenue confirmed the spending.

Every result is net of costs, and cost sensitivity is shown at double rates. The equity work uses daily data; no intraday claims are made anywhere.

## What we measured

The delivery chain is slow, and the slowness is countable:

- **3,783 promise revisions** across nine annual vintages; the modal slip is exactly **twelve months** (worst 120).
- **64 percent** of the generators promised for 2015 were late, by up to 83 months.
- Disclosure lags of **33 to 94 days** between a period end and the filing that makes it public. A reader who waits for the headline never sees the revision.
- Promised next-year capacity grew **+41.7 percent a year** at the median, one-signed in 89 percent of months, 2016 to 2024.
- **44 percent** of tracked generators revise, and the hazard rises with age. A promise is not safer for having survived.

The attribution limit is measured, not assumed: only **6.2 percent** of slipped capacity sits with a large listed owner. That closed the project-level route at a number.

## What we tested

The intensity expression loses **9.49 percent a year** ungated. Confirmed by the revenue gate over the same window, it earns **+10.48 percent net** at Sharpe 0.971 (doubled costs: +9.96 percent). The month-blocked interval on the difference runs **+7.75 to +35.30 percentage points**, positive in 99.9 percent of resamples. The preferred rolling-origin portfolio returns **+11.95 percent at Sharpe 1.100** with a **-15.1 percent** maximum drawdown. These are development results, and everything is labeled that way.

Two findings come first, because they shape how the rest should be read:

- **The strategy does not beat the basket on raw return.** The equal-weight long basket earns +33.77 percent a year. Ours earns less. Its case is risk, not return: a third of the basket's drawdown, a 0.21 beta, and a dollar-neutral book that does not need the theme to keep working.
- **The best number we found is the one we threw away.** A drawdown-conditioned overlay reports Sharpe 1.793. It reads the same session's close, and our lookahead battery caught it: lagged one session, it falls to 0.655, below the 0.931 unconditioned. Reported as rejected in the note, kept in the record.


## How we built it

One pipeline, four sponsors, everything committed: capture at the edge, an exchange-grade replay engine, a hot and cold data layer, and two databases that archive the same validated batches.

### Vultr: the live host

- The OCaml engine and the depth and trade collector run in Docker on Vultr, on host `gqh-book-engine-01`. One command sets the machine up: installs Docker and opam, builds and tests the engine, starts the collector, installs the daily replay timer, and writes the first report.
- The collector writes immutable five-minute depth and trade windows, each with a manifest of time bounds, record counts, and compressed sizes. Its health check fails on stale output, corrupt gzip, missing manifest rows, or high disk use.
- A daily timer replays every captured day at 00:20 UTC.
- First full day on Vultr: 19,662 events, 5 snapshots, zero chain gaps, no book mismatch, replay checksum `ae92c1786a91bf8c8a3e8379cb7d27d7`.
- Cross-machine determinism: replaying the same Vultr fixture on a development machine produces the same checksum and the same counters, so capture, normalization, fixture building, and replay agree across hosts.
- A live Hyperliquid WebSocket capture (171 aggregated L2 snapshots and 1,706 trade prints over about fifteen minutes, zero parser errors, zero chain gaps) replayed clean through the same path.

### The engine: an exchange-grade order book, in OCaml

- A custom incremental computation engine drives a fully bitemporal order book (valid time and transaction time), with exact price arithmetic, nanosecond timestamps, and an Lwt event loop that also serves the book to multiple WebSocket clients.
- It executes visible-depth IOC/FOK taker orders and posts fees and settlement to fixed-point accounts. A separate daily path evaluates the equity portfolio from frozen target weights.
- Why it matters, with numbers: on a ninety-minute slice, a naive fill model fabricated 251 fills where the engine allowed one, and turned a flat strategy into a 51 percent loss. Fill realism is the difference between a backtest and a story.
- The engine studies execution mechanics. It does not create the equity signal, and we say so out loud, not just privately.

### TigerData and TimescaleDB: the operational backplane

- The shared PostgreSQL/Timescale service holds source landings and operational telemetry: collector health, event counts, sequence quality, latency, throughput, and execution summaries. It runs near its allowance, so every loader writes as a budgeted, idempotent batch.
- An engine-output bridge lands run rows and flattened report metrics in Timescale hypertables, with a continuous aggregate ready for SQL dashboards. Full immutable reports live in Snowflake, referenced by hash.
- The same validated batch that lands in Snowflake lands in `public.gqh_source_records` with identical row and batch hashes.

### kdb+/q and KDB-X: hot and cold

- The hot path: the five-minute capture windows feed a KDB-X ingest, with schema, loader, export, smoke test, and systemd units all committed.
- The cold research path: a partitioned HDB in kdb+/q on HiPerGator Blue, built from checksummed TigerData exports by Slurm jobs. Every build gets a version directory and a receipt, with input body hash and row count verified before the claim. Prices are signed 64-bit integers in units of 1e-8 USD, row identity is `(date, sym, source_id, batch_sha256)`, and a validator must pass before the copy is published read-only to teammates.
- The read path goes over shared storage and opens no unauthenticated q service. The wrapper harness was tested against a stub q process for spooled scripts, receipt provenance, checksum and row-count rejection, and failed-loader behavior.

### Snowflake: the archive of record

- The canonical cloud archive for raw source files, filings, EIA vintages, and provenance manifests. The 1.59 million row AWS GPU spot archive was loaded with its provenance cited and its source gaps recorded in their own table.
- Point-in-time discipline is a schema property here, not a convention: `event_time`, `available_at`, and `ingested_at` travel with batch and row hashes, and repeated runs are idempotent.
- One workflow runs a single read-only query on a runner using the repository credential, which never leaves the runner, and returns the result as a CSV artifact.
- `src/central_ingest` writes the same validated batch to Snowflake and TigerData with identical hashes; 16 full batches landed in both stores on 2026-10-03.

## Our evidence standards

This is the part of the project we stand behind hardest.

- **Every survivor is counted against chance.** 135 searched comparisons produced 6 survivors against 5.5 expected by chance; the shuffled-date control is reported beside it. A survivor starts a mechanism conversation and is never called a strategy.
- **Falsifiers are declared before the test.** The forward window is pre-registered with zero scored observations and five written falsifiers: a composite at or below zero, Sharpe at or below 0.5, a drawdown beyond twenty percent, a capex hedge that turns positive and significant, or predictions that change after the fact.
- **Our own batteries catch our own artifacts.** The clock audit on the earlier work turned a published +2.94 percent into -4.89 percent; we published the correction. The lookahead battery killed our best overlay. That is the process working, in the open.
- **Reproduction is exact.** Committed inputs, a SHA-256 manifest, and an offline path that a judge can run from a fresh clone.

## Risk, capacity, costs

- Volatility targeted at 10 percent; a hedged composite was tested and is reported as dilutive.
- Costs are stated in bps and every result is shown at double cost.
- Capacity is bounded by the short leg: a median of five names, single-digit millions at one percent of ADV. Borrow is not yet checked, and we say so.
- The book is dollar-neutral with a 0.21 beta to the complex, and the drawdown budget is roughly a third of the basket's.

## Reproduce

No network needed:

```sh
make check      # structure, ledgers, path integrity
make test       # the full suite
make reproduce  # the offline artifacts, hashes compared
```

The dashboard the judge path renders:

```sh
python3 docs/visualization/culmination.py
```

Frozen inputs are committed, including the 66-series price subset the results actually touch. The network tier exists for live re-fetches and is intentionally not exact.

## What happens next

- Correct the conditioning overlay's information timing and test it lagged, without touching the forward window.
- Run the pre-registered forward window and report whatever it says.
- Add borrow and implementation costs for the short leg, then a capacity model.

## Where things live

- Submitted note: the linked PDF above, source in [docs/note.md](docs/note.md).
- Earlier delivery study, kept as evidence: [docs/note.pdf](docs/note.pdf).
- Result artifacts and per-file reproduce commands: [results/README.md](results/README.md).
- Study-level record, including every negative result: [docs/plan/](docs/plan/), [docs/truths.md](docs/truths.md), [docs/variants.md](docs/variants.md).

**Built with**: Snowflake, TigerData / TimescaleDB, Vultr, kdb+/q (KX), OCaml, Python, Massive, SEC EDGAR, EIA-860M.
