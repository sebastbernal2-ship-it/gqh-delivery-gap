# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added
- Replay mode that applies venue events without creating synthetic trades.
- Simulation mode selection for the event loop.
- Strict CSV parsing for data-quality checks.
- Strict feed CSV parsing with venue, symbol, sequence, and receive-time metadata.
- NYSE National TAQ Integrated Feed adapter for CSV and gzip files.
- SonarX Hyperliquid L2 snapshot parser for JSON and gzip files.
- SonarX snapshot replay loop for asynchronous strategy handlers.
- Hugging Face Hyperliquid L2 sample parser for derived depth CSV files.
- L2 visible-liquidity execution model for partial fills and VWAP.
- Snapshot strategy backtest runner with fees, positions, cash, and equity curves.
- Runnable Hugging Face L2 imbalance backtest example.
- Snapshot latency and funding-rate support for experimental L2 backtests.
- Return, drawdown, turnover, fee, and funding metrics.
- Strict event replay with per-symbol books and sequence-gap detection.
- Raw little-endian NYSE Pillar decoder for core order-book messages.
- NYSE XDP packet framing and multi-message packet support.
- NYSE status, imbalance, non-displayed-trade, cross-trade, quote, trade, and stock-summary messages.
- Native replace-order handling with old and new order IDs.
- Order-book invariant validation after strict replay events.
- Corrected separate bid and ask cumulative-size parsing.
- Feed metadata helpers for symbol grouping, validation, and sequence numbering.

### Fixed
- Duplicate order IDs are rejected.
- Cancel and execute events use the stored order location.
- Bitemporal order revisions close the prior interval.
- The benchmark replays feed events and measures a populated book.
- Each order book now owns an independent incremental engine instance.

## [0.2.0] — 2026-02-24

### Fixed
- Amend now correctly removes from the **old** price level before adding to
  the **new** price level. Previously it removed from the new level, causing
  total_size to be wrong when an order moved between price levels.
- Replaced `List.nth` in market data generator with `Array.of_list` + array
  indexing, eliminating O(n) random access.

### Changed
- Extracted duplicate `take` function into `List_utils` module, removing
  copies from `order_book.ml`, `cli.ml`, and `benchmark.ml`.
- Consolidated `run` and `run_fast` in event loop into `run_internal` with
  a `~use_delay` parameter, eliminating ~20 lines of duplication.
- Removed dangerous `module List` shadow in `cli.ml` — replaced `List.count`
  with `List.length (List.filter ...)`.
- `sexp_of_market_event` now serializes full data for `BookSnapshot` and
  `StatsUpdate` instead of emitting empty atoms.
- `Metrics.json_report` now uses `Yojson.Safe.to_string` instead of
  `Printf.sprintf` for JSON construction.
- Benchmark now includes warmup phase, multiple iterations, and
  min/max/mean/stddev reporting.

### Added
- `List_utils` shared module (`src/list_utils.ml` / `.mli`).
- Expect tests for amend-after-cancel error and amend price-level move.

## [0.1.0] — 2026-02-23

### Added
- Custom incremental computation engine (`incr`) with wave-based
  stabilization, map/map2/map3/bind/if_/cutoff combinators.
- Bitemporal order book with `Order_id.Map` per price level (O(log n)
  operations), fully immutable state.
- Lwt-based event loop with array-based O(1) event access.
- WebSocket server with Yojson-based JSON encoding.
- Command-line interface (`msim`): generate, run, serve, query, info.
- Market data CSV parser and random event generator.
- Metrics collector with JSON reporting.
- Complete test suite: Alcotest unit tests, QCheck property tests,
  ppx_expect tests.
- CI pipeline via GitHub Actions with formatting check.
- Architecture Decision Records (docs/adr/).
- `.ocamlformat` configuration.