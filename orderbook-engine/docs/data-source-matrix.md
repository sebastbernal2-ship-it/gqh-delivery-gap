# Data-source eligibility matrix — verified 2026-10-04

This matrix separates data that exists from data eligible for a strategy replay. The current first
deliverable is a daily equity event study; it needs no order book. Perpetuals remain deferred until
the team has a verified, synchronized Hyperliquid source and adapter.

| Source | Actually present now | Data level | Eligible use |
|---|---|---|---|
| Massive daily equities | PWR, ETN, EME, DLR, SPY, XLI, XLRE in Snowflake `RAW.SOURCE_RECORDS` | Split-adjusted daily OHLCV; separate dividend/split actions | Equity event outcomes and market/sector controls. No L2 required. |
| SEC / company facts | Filing register and SEC XBRL-derived obligation facts; original filing archive is being backfilled | Filing metadata, XBRL and source documents; availability clocks vary | Point-in-time event construction after accession/document reconciliation. Not order-book input. |
| AWS GPU Spot | 1,592,024 rows in Snowflake and TigerData; source gap March–June 2026 | Irregular price-history observations, USD per instance-hour | Separate descriptive compute study. Not equity L2 or an order-book feed. |
| TigerData `depth_events` / `trade_events` | 42,652 depth updates and 100,961 trades for BTCUSDT, captured from Binance | Aggregated L2 and trades; short capture | **Quarantined: do not use for this project’s strategy, Hyperliquid replay, or evidence.** |
| TigerData `observations` | 28,800 BTCUSDT observations, separate legacy capture | Derived book-depth metrics | **Quarantined with the Binance capture; not a replacement for synchronized venue events.** |
| Hyperliquid | No validated project batch in Snowflake/TigerData at this inventory check | Official archive can provide aggregate L2 snapshots; no verified receipt-time capture here | Future A/perp work only after source provenance, gaps, event/receive clocks, and adapter are certified. |
| Binance public archive / engine Binance parsers | Legacy project data, fixtures and code remain in the repository | Aggregated depth, trades and Binance-specific formats | Software compatibility tests only if needed; never treat these as strategy inputs or Hyperliquid proxies. |
| TigerData engine outputs (target; not yet populated) | Proposed `engine_run_reports`, `engine_metric_points`, and hourly continuous aggregate in `collector/tiger/engine_output_schema.sql` | Compact per-run quality, latency/throughput, execution/accounting/risk metrics | Operational retrieval and dashboard only, after service capacity is verified; never the research archive. |

## Warehouse facts and caveats

- Snowflake's typed `RAW.EQUITY_BARS` and `RAW.FILINGS_8K` tables exist but are empty. The usable
  equity data is presently in the generic `VECTOR_RESEARCH.RAW.SOURCE_RECORDS` landing table and
  must be selected by exact `SOURCE_ID` plus `BATCH_SHA256`. `NORMALIZED.AWS_GPU_SPOT_DAILY` is a
  daily rollup view, not a second raw archive.
- TigerData's `public.gqh_source_records` mirrors most raw sources, but it also has a separate
  2,329-row `massive_8k` batch not reconciled to the Snowflake 201-row batch. Do not silently merge
  or count these as one dataset.
- The live TigerData database size was approximately 888 MB at the audit, above the previously
  observed 750 MiB allowance. No additional TigerData writes are approved by this data plan until
  the active service limit is verified. Snowflake is the destination for the new historical equity
  panel and SEC originals.
- Massive aggregates are split-adjusted, **not dividend-adjusted**. The event-study runner uses
  the separate dividend adjustment factors for total-return outcomes. Those realized outcomes are
  labels, never decision-time features.
- Massive NBBO/tick data is not in the current daily event study, and no equity order-book feed is
  needed for it. The engine must not synthesize depth or trades from OHLCV.
- No source verified here supplies order-level FIFO/L4 for Hyperliquid. Do not claim queue position,
  maker fill probability, own market impact, or a live latency edge from aggregate L2 snapshots.

## Adapter decision

1. **Now — equity event study:** query pinned daily bars, dividend factors, SEC facts and filings
   from Snowflake. Keep outcomes and source timestamps distinct. The exact CSV/JSON outputs are
   centrally stored in Snowflake `RAW.RESEARCH_ARTIFACTS`. Do not route equity bars through the
   order-book simulator or TigerData.
2. **Now — compute study:** use the existing AWS spot history as a separate measured context
   experiment, with the March–June 2026 hole and irregular observation times preserved. Do not
   promote it to an equity signal without a predeclared exposure mechanism and independent tests.
3. **Later — order-book engine / perps:** select Hyperliquid as the target venue, not Binance.
   Acquire a bounded, source-documented Hyperliquid batch or forward capture; certify sequence,
   event-time/receive-time semantics, gaps, and market metadata; then build a one-way adapter into
   the fixed JSONL contract. Keep source fixtures and immutable reports in Snowflake; send only
   compact engine output time series to TigerData after verifying headroom. Until those gates pass,
   the legacy Binance datasets stay quarantined.

The accounting library currently supports a single instrument with visible-depth IOC/FOK fills;
it does not establish passive FIFO fills or a synchronized Hyperliquid replay. See
[`ADR-008-instrument-accounting.md`](adr/ADR-008-instrument-accounting.md) for the remaining
accounting and execution gates.
