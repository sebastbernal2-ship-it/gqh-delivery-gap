# Snowflake research path

Owner: Vishnu. Status: adopted infrastructure boundary; account provisioning and Snowflake
credentials are not yet verified. This is a research/data design, not a trading thesis.

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
