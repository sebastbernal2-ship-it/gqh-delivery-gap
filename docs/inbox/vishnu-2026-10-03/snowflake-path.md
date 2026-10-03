# Snowflake research path

Owner: Vishnu. Status: adopted infrastructure boundary and first AWS archive load verified
2026-10-03. This is a research/data design, not a trading thesis.

## Decision

Use Snowflake for historical integration and reproducible feature panels. Keep Snowflake off the
live execution path. TigerData remains the shared operational/time-series store; q/kdb+ and the
local C++/OCaml engine remain responsible for time-series replay, signal/risk arithmetic and any
execution-sensitive work.

## Why each system exists

| Layer | Responsibility | Explicit non-responsibility |
|---|---|---|
| Immutable object storage | Raw AWS archive, filing payloads, exports and manifests | Live queries or strategy decisions |
| Snowflake `RAW` | Versioned source landing for compute, filings, equities and curated order-flow extracts | Per-tick or per-order reads |
| Snowflake `NORMALIZED` | Timestamp/entity/source normalization and provenance | Forward-filling unavailable information |
| Snowflake `FEATURES` | Scheduled compute, filing, equity and order-flow features | Black-box alpha generation |
| Snowflake `RESEARCH` | Point-in-time training/backtest panels and team-wide reproducibility | Live order routing |
| TigerData | Shared recent time series, AWS compute table, order-book aggregates and execution records | Replacing source provenance with silently repaired data |
| q/kdb+ | Fast windows, as-of joins, replay and market-feature calculations | Filing interpretation or account management |
| C++/OCaml | Deterministic strategy, risk, portfolio and arithmetic engine | Fetching Snowflake data on every order |

## First useful slice

Build only a small panel first:

1. AWS GPU Spot observations from `public.aws_gpu_spot_prices` in TigerData.
2. A declared equity basket and benchmark bars.
3. Massive 8-K metadata and document-availability timestamps.
4. Snowflake features: last compute price, price change, age of observation, regional spread,
   filing event fields, volatility, liquidity and exposure controls.
5. A point-in-time panel exported to Parquet/q for chronological backtesting.

Every observation needs `event_time`, `available_at`, `ingested_at`, source identifier and source
version/checksum. A feature may only join information whose `available_at` is no later than the
decision timestamp. Realized delivery outcomes remain labels, never predictors.

## Verified first load and source citation

The signed-in Snowflake browser account successfully ran `src/snowflake/bootstrap.sql` and loaded
the local AWS Spot snapshot to `VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES`; Snowflake reported
1,592,024 rows inserted. The post-load QA query then returned 1,592,024 rows, 31 source files,
`2022-05-31 18:50:49.000 Z` through `2026-09-30 23:00:00.000 Z`, zero null `ingested_at`
values, and zero observations in the source gap. This confirms the imported timestamps decode
to UTC in Snowflake. TigerData's existing `public.aws_gpu_spot_prices` was separately queried:
1,592,024 rows, 31 source files, first time `2022-05-31 18:50:49+00`, last time
`2026-09-30 23:00:00+00`, and zero observations during March–June 2026. Source data files are
local and ignored by git; do not commit raw files or service credentials.

Cite as: Eric Pauley (2026), *AWS Spot Price History* (2026-09 version) [Data set], Zenodo,
https://doi.org/10.5281/zenodo.23082767, CC BY 4.0. Use the dataset DOI/version in reports,
include access date and source-file checksums, and state that it mirrors AWS EC2
`DescribeSpotPriceHistory` with global AZ IDs replacing account-specific AZ names. `price_time`
is the source event time; `ingested_at` is our Snowflake load time, not historical availability.
Keep the Mar–Jun 2026 gap explicit and do not treat the daily view as a tradable point-in-time
feature until original observation/availability semantics are proven.

## Ornn benchmark repo: useful but not a market-data source

[`Ornn-AI/ornn-benchmarking`](https://github.com/Ornn-AI/ornn-benchmarking) is an MIT-licensed
GPU qualification CLI, not a historical compute-price feed, training corpus, or alpha model. It
runs compute (MAMF), memory (`nvbandwidth`) and interconnect (`NCCL`) tests; produces machine-
readable JSON with hardware/software inventory, per-section metrics, Ornn-I/Ornn-T scores and a
manifest; it can optionally submit that report to Ornn's API. A team use would be to run pinned,
repeatable qualification on our GPU hardware, preserve the JSON locally, and—only after verifying
instance GPU model/count—join that measured performance to AWS Spot prices as an experimental
`USD / Ornn-I` or `USD / Ornn-T` efficiency measure. This is a hardware-normalized *current*
cost comparison, not historical performance or proof of deployable cloud capacity. Do not upload
reports to Ornn by default: they contain system/GPU inventory, and the user has not asked to send
that metadata to the service. Repository README documents scores and MIT license; CLI guide
documents JSON reports, benchmark sections and opt-in API uploads.

## Latency boundary

Snowflake batch refresh latency is acceptable for compute-price and filing signals that operate on
minute-to-day horizons. It must not be inserted between a market update and an order. The live
path is:

```text
provider feed -> C++/Rust ingestion -> TigerData/q -> C++/OCaml strategy/risk -> execution
```

The research path is:

```text
TigerData exports + Massive + equity history -> Snowflake -> point-in-time panel -> q/C++/OCaml
```

## What is loaded now, and when the remaining sources enter

**Today:** only the AWS Spot archive is loaded in both stores. It was loaded independently from
the same normalized local snapshot; there is no scheduled or continuous TigerData↔Snowflake
connector yet. Do not describe this as an automated bridge. The first bridge should be a
reproducible, idempotent batch handoff (TigerData export/Parquet with a manifest, then Snowflake
`COPY INTO`/stage), keyed by source version and natural key, and compared row-for-row with the
source export. It should run when a dataset's access, timestamps, schema and license are checked,
not simply because a URL is in the source audit. Never send Snowflake reads into the live order
path.

The next data onboarding is deliberately phased:

1. **First research panel (next, before a backtest):** original SEC EDGAR filings for PWR, ETN,
   EME and DLR (8-K plus 10-Q/10-K and relevant exhibits), plus a small adjusted daily OHLCV panel
   for those names and SPY. Land accession/versioned source metadata and extracted numeric
   disclosures in Snowflake; put only compact, dated event/features and the selected market bars
   into TigerData if q needs as-of joins/replay. SEC text is not sent wholesale to TigerData.
   Massive's competition 8-K event tags stay a separately labeled enrichment/benchmark, not the
   canonical filing timestamp or replacement for source documents. Equity bars remain gated on a
   real entitlement/date-range/licensing check of one free provider; no bars are currently loaded.
2. **Second (only if the company/region mapping is defensible):** Census C30 data-center
   construction spend and M3 electrical-equipment/computer orders; EIA-860M planned/operating
   generators and EIA-930 hourly balancing-area grid demand/forecast. Preserve release vintages
   in Snowflake. Publish only the small as-of series needed by q to TigerData; monthly/national
   context can remain Snowflake-only. These are context/proxies, not direct company delivery data.
3. **Third (after a predeclared confounder or exposure needs it):** EIA-923, EPA CAMPD/CEMS,
   Census trade, ALFRED/FRED, grid queues, weather/water, permits/hearing transcripts, patents,
   or satellite products. The source audit has the links and limits; none of these are loaded now.
   Add one stream at a time only if a feature definition says what it measures, when it became
   available, and what falsifiable hypothesis it tests.

Each phase starts with one small ticker/time window and a manifest (provider, exact endpoint or
file vintage, extraction timestamp, units/schema, source URL, checksum, row count, date coverage,
missingness and license). Then validate event-time versus publication/available-at time, duplicate
and revision behavior, stable identifiers, and a row-count/reproducibility comparison between
local export, Snowflake, and (only for operational series) TigerData. No claim of pipeline
completion until this comparison passes. This sequence makes the sources useful rather than
turning the warehouse into a dump of every interesting link.

## Why this helps the track entry

The project is not claiming an HFT advantage from these slow operational disclosures. The
candidate mechanism is that *numeric, dated revisions* in capacity/backlog/delivery indicators
may change the relative near-term cash-flow outlook of firms exposed to bottlenecks. A focused
panel can test whether those revisions predict subsequent relative equity returns after market,
sector, size/momentum and liquidity controls, and whether the effect survives conservative
availability lags and plausible costs. The spot archive is a candidate cost/availability proxy,
not a confirmed leading signal; the first test must include an equity-only baseline and an
ablation without compute prices.

Freeze hypothesis, universe, signal definition, event clustering and cost model before opening
the track's final holdout (most recent 20% of history or most recent 2 years, whichever is
shorter). Report the holdout once, net of costs, alongside placebo/event-shuffle controls,
nearby parameter plateaus, doubled costs, turnover, drawdown, liquidity capacity and the count of
independent shocks. A long equity history does not turn today's AI build-out into decades of
independent AI-era events. This makes the novelty a measurable supply-chain surprise mechanism,
not a claim that adding Snowflake, TigerData, GPUs or AI itself creates alpha.

## Acceptance tests before scaling

- Snowflake panel reproduces the same rows and timestamps as the local export.
- No row with `available_at > decision_time` enters a feature set.
- The same feature query is deterministic across reruns and source versions.
- A chronological backtest can run entirely from an exported panel without Snowflake access.
- The baseline is compared with a simpler TigerData/q-only implementation before adding Snowpark
  ML, Cortex, Laya or GPU training.

The MLH Snowflake partner page advertises a 120-day trial and Snowflake resources; this does not
prove our account, edition, credits or entitlements. Feature Store use is optional because its
edition requirements must be checked after account creation.
