# Data source matrix, verified 2026-10-04

No adapter is built on an assumption. Each row below was checked against the live source on 2026-10-04.

| source | trades | quotes, level 1 | depth, level 2 | span | role |
|---|---|---|---|---|---|
| Snowflake `VECTOR_RESEARCH` | no | no | no | daily and monthly | research and context only |
| Tiger Cloud, our Binance capture | yes, 100,961 rows | no | yes, 42,652 rows, aggregated | 2026-10-03 23:42 to 2026-10-04 00:54 | real depth, span grows with the Vultr collector |
| Binance public history, `data.binance.vision` | yes | no | yes, aggregated, `bookDepth` | daily since 2020 | multi-day fixtures |
| Massive, `api.massive.com` | yes, tick, since 2005 | yes, tick NBBO, since 2010 | no | 20 years | level 1 replay for US equities |

## Evidence

Snowflake: `RAW.EQUITY_BARS` columns are `TICKER, EVENT_TIME, OPEN, HIGH, LOW, CLOSE, VOLUME, SOURCE, SOURCE_VERSION, INGESTED_AT`, and the table holds zero rows. `RAW.SOURCE_RECORDS` is a raw document store whose top sources are `eia860m_full_2024_12`, `eia923_pjm_2024`, `fred_rates`, `fred_market`, `massive_bars`, `massive_bars_unadjusted`, `m3_shipments`, and Census construction data. The only price-shaped tables in the account are `RAW.AWS_GPU_SPOT_PRICES`, which is compute pricing, and `RAW.EQUITY_BARS`. There is no bid, ask, size, or time-in-force anywhere in the account.

Tiger Cloud: `depth_events` holds 42,652 rows from 2026-10-03T23:42:24Z to 2026-10-04T00:54:59Z, with the update-id columns and the level arrays. `trade_events` holds 100,961 rows from 2026-10-03T21:55:00Z to 2026-10-04T00:54:59Z. `observations` holds the book-depth metrics. This is our own capture and it is real depth data.

Binance public history: `BTCUSDT-bookDepth-2026-10-01.zip` downloads, 562,333 bytes. The bucket listing also serves trades. No daily diff-depth files exist, and Binance publishes no order-by-order feed at all, so Binance can never support order-level FIFO, only aggregated depth.

Massive: trades are served for 2026-09-15, 2015-01-05, and 2005-01-03. Quotes are served for 2026-09-15 and 2010-01-04, with bid and ask price, size, and exchange. Order book endpoints do not exist: `/v3/book` and `/v2/l2` return 404, and the crypto level 2 snapshot returns 403 `NOT_AUTHORIZED`.

## What each source can feed

- Level 2, aggregated book and bounded fills: Tiger Cloud, and Binance public `bookDepth` for multi-day fixtures.
- Level 1, top of book only: Massive trades and NBBO quotes. The engine replays these in the aggregated bounded-fill modes and never as order-level FIFO.
- Order-level FIFO: no source here provides it. Binance publishes aggregated depth only, and Massive has no book product. Order-level FIFO stays a property of feeds that carry order identity, not something reconstructed from quotes.
- Research and context, never replay: Snowflake. Daily bars, filings, energy, compute, and macro series drive regime labels, factor inputs, and context. A daily bar is not a depth update and must not be turned into one.

## Consequences for adapters

1. Snowflake gets a feature reader, not a market data reader. Its output is a feature table joined to a run, never depth rows.
2. Tiger gets the recall path that already exists, extended to the full captured span.
3. Binance public history gets a small downloader and the same fixture builder, which gives multi-day aggregated L2 fixtures without a live capture.
4. Massive gets an L1 adapter only, and every fixture it produces must record the mode as aggregated with bounded fills.

A historical quote with a zero ask, which old Massive quote records do contain, must be dropped rather than replayed.
