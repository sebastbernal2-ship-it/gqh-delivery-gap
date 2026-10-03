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

**Loaded and verified:** AWS Spot archive is in TigerData and Snowflake (1,592,024 rows each).
The SEC filing accession register is in Snowflake `VECTOR_RESEARCH.RAW.SEC_FILINGS_REGISTER`
(776 rows); it is not yet in TigerData. Census C30 is in
`VECTOR_RESEARCH.RAW.CENSUS_C30_AI_INFRA_NSA` (152 rows), and the EIA-860M proposed/canceled
capacity slice is in `VECTOR_RESEARCH.RAW.EIA860M_2024_12_PROPOSED` (3,404 rows). The broader
EIA-860M CSV (36,949 rows), EIA-930 sample and other macro/context CSVs remain local only. A
Snowflake browser upload attempt for the full 6.9 MB EIA-860M CSV stalled with a fetch failure
before schema preview; no full-vintage EIA table was created. There is no scheduled or continuous
TigerData↔Snowflake connector yet. Do not describe this as an automated bridge. The next shared
ingestion tool should
fetch each provider batch once into a private, immutable landing file plus a manifest (endpoint or
source version, request window, fetched-at, schema, row count, bounds, checksum, license status),
then fan out that same validated batch: `MERGE` into Snowflake `RAW` as the historical/provenance
copy and idempotent `INSERT ... ON CONFLICT` into TigerData for only the compact operational/as-of
series. Reconcile natural keys, counts and timestamp bounds across both stores before marking a
manifest complete. Keep credentials in local secrets or GitHub Actions secrets, never in this
repository. A `sync-source` command/workflow should take a named source and window, use pagination,
retry/backoff, deduplicate on stable natural keys, and stop before any destination write if the
license gate is unresolved. This is a reproducible two-target ingestion run, not a live or
continuous Snowflake↔Tiger connector. Never send Snowflake reads into the live order path.

On 2026-10-03, two teammate invitations were sent with the `ACCOUNTADMIN` role at the owner's
explicit direction. Snowflake showed both as pending; access is not active until each person
accepts the invitation email. Their addresses are intentionally not repeated in this public repo.

The next data onboarding is deliberately phased:

1. **First research panel:** original SEC EDGAR filings for PWR, ETN, EME and DLR (8-K plus
   10-Q/10-K and relevant exhibits), plus Massive adjusted daily OHLCV for those names and SPY.
   Massive was tested 2026-10-03: every ticker returned 2,703 rows from 2016-01-04 through
   2026-10-02, one API page each, with no OHLCV consistency failures. Its 8-K classification API
   returned 67 PWR, 53 ETN, 16 EME and 65 DLR disclosures from 2022 onward. These responses were
   inspected in memory only; no data were stored. Land original accession/versioned source metadata
   and reviewed numeric disclosures in Snowflake; use Massive tags as separately labeled
   enrichment, never as canonical filing timing or a substitute for source documents. Publish
   selected bars and compact event/features to TigerData only if q needs as-of replay. Key access
   is verified for this window; the sponsor is confirming the separate permission needed for
   team-shared retention and non-display strategy use. A retrieval entry point now exists at
   `scripts/pull_massive_daily_bars.py`. It reads `MASSIVE_API_KEY` only from the process
   environment, requires `GQH_MASSIVE_TEAM_STRATEGY_LICENSE=confirmed`, paginates and validates
   either adjusted daily bars or 8-K AI event labels, and writes a local CSV plus SHA-256 manifest.
   It does not log the key, make database writes, or run automatically. The license flag is an
   operator gate, not evidence that permission exists. No Massive bars or tags have been stored.
   The pasted key should be rotated. Alpaca was
   also tested but is unnecessary as a fallback if the sponsor confirms the intended Massive use.
   After sponsor confirmation, the local invocation is:

   ```sh
   export MASSIVE_API_KEY='(set in your private shell secret store)'
   export GQH_MASSIVE_TEAM_STRATEGY_LICENSE=confirmed
   python3 scripts/pull_massive_daily_bars.py --from 2016-01-01 --to 2026-10-02 \
     --output data/private/massive-daily-bars.csv
   ```

   For the AI-tagged SEC event series, add `--dataset 8k-disclosures` and use a separate output
   path. The request covers filing dates from Jan 2022 onward; this is an event-tag series, not
   the canonical filing history or a replacement for SEC accessions/acceptance timestamps.

   Do not place either value in a shell history, tracked file, issue or public GitHub Actions
   configuration. The sponsor-provided team key should be installed as a private local secret by
   each authorized operator; do not send the key around the team chat. A separate sink step is
   still needed to load licensed data into Snowflake/TigerData with row-count/checksum QA.
2. **Second (only if the company/region mapping is defensible):** Census C30 data-center
   construction spend, Philly Fed delivery-times survey, NY Fed GSCPI, EIA-860M planned/operating
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

## Current public data inventory / loading status

| Stream | Verified local data | Snowflake | TigerData | Research purpose |
|---|---|---|---|---|
| AWS GPU Spot archive | 1,592,024 rows, source gap preserved | Loaded + QA | Loaded + QA | Compute-cost/availability proxy |
| SEC accession register (PWR/ETN/EME/DLR) | 776 rows, 2015–2026 | `RAW.SEC_FILINGS_REGISTER` loaded | Not loaded | Public point-in-time filing index |
| Census C30 data-center construction | 152 rows, 2014-01–2026-08 | `RAW.CENSUS_C30_AI_INFRA_NSA` loaded | Not loaded | National monthly spend; nominal, revised history |
| EIA-860M proposed/canceled subset | 3,404 rows, 2024-12 vintage | `RAW.EIA860M_2024_12_PROPOSED` loaded | Not loaded | Planned/canceled capacity, dates, fuel, location |
| EIA-860M full Dec-2024 vintage | 36,949 rows, 27 fields | Not loaded; upload stalled | Not loaded | Broader operating/retired context if needed |
| EIA-930 PJM sample | 24 hourly rows for 2024-01-01 | Not loaded | Not loaded | Demand-versus-forecast smoke test; extend before modeling |
| Philly Fed delivery-time survey | 701 monthly observations, 1968–2026 | Local only | Local only | Long-run diffusion proxy for delivery conditions |
| NY Fed GSCPI | 344 months, 1998-01–2026-08 | Local only | Local only | Global supply-chain regime control |
| FRED controls | Daily/monthly rates, VIX, Nasdaq Composite, semiconductor IP | Local only | Local only | Market and supply-cycle controls; series rights/vintages vary |
| Massive daily bars / 8-K tags | Read-only API probes only; responses not retained | Not loaded | Not loaded | Pull script ready; run after sponsor grant is confirmed |

Public extracts are ignored by git under `data/`; local manifests record source, schema, coverage,
checksums and caveats. Load only whitelisted compact series after choosing a table schema, vintage
timestamp and purpose.

Snowflake load receipts (2026-10-03): Census received all 152 rows from
`census_c30_ai_infra_nsa.csv`; EIA received all 3,404 rows from the normalized 2024-12 Planned +
Canceled or Postponed subset. The source EIA manifest records the original workbook URL, attribution,
whole-vintage row counts and caveats. The filtered EIA CSV SHA-256 is
`01319f7e5e2242634fd91a68049c7de0753af249df8bcf0ccff03d4e35467dae`. These are RAW ingestions;
date/vintage normalization, revision-aware availability, duplicate plant-generator review and
TigerData parity are still required before using them as strategy features.

## Stack handoff

```text
Public APIs / licensed Massive API
          ↓ pagination + schema/timestamp checks
private immutable CSV/Parquet + source manifest
          ├── Snowflake RAW → NORMALIZED → FEATURES → RESEARCH (slow research, vintage-safe)
          └── TigerData (compact as-of/event series and replay inputs)
                    ↓ export
              kdb+/q replay and as-of joins
                    ↓ deterministic feature contract
            C++/OCaml strategy, sizing and risk arithmetic
```

The Massive extraction command currently implements only the first two boxes through local CSV;
it is not yet a remote job or two-database bridge. Snowflake's browser account and TigerData
service are ready, but the Snowflake SQL connector/service-auth configuration and TigerData
connection secret have not been wired into a repeatable ingestion client. Do not claim the API→DB
flow is live until a small canary batch has matching source/local/Snowflake/TigerData counts,
timestamps and checksums. Keep order execution independent of Snowflake.

The MLH Snowflake partner page advertises a 120-day trial and Snowflake resources; this does not
prove our account, edition, credits or entitlements. Feature Store use is optional because its
edition requirements must be checked after account creation.
