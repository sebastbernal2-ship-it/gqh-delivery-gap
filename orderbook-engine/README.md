# Market Simulator

> **Project data boundary (2026-10-04):** The Binance parsers, collector, samples and captured
> BTCUSDT rows are legacy engineering material only. Do not use them in the project strategy,
> claim Hyperliquid replay validation, or mix them with another venue. Perpetuals are deferred until
> a synchronized Hyperliquid source is verified. Daily equity event studies do not use this engine.
> See [`data-source-matrix.md`](orderbook-engine/docs/data-source-matrix.md).

[![CI](https://github.com/sebastbernal2-ship-it/market_simulator/actions/workflows/ci.yml/badge.svg?branch=main&event=push)](https://github.com/sebastbernal2-ship-it/market_simulator/actions/workflows/ci.yml) 
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) 
[![OCaml 5.2](https://img.shields.io/badge/OCaml-5.2-orange.svg)](https://ocaml.org)

An incremental-computation-driven market simulator with a fully
bitemporal order book, written in OCaml.

git clone https://github.com/sebastbernal2-ship-it/gqh-delivery-gap.git ~/gqh-delivery-gap
cd ~/gqh-delivery-gap/orderbook-engine
bash deploy/setup.sh

`orderbook-engine/docs/engine-io-contract.md` owns the input and output format: canonical JSONL in, one report out, with samples in `examples/io-contract/`.

For source-neutral accounting, `Instrument_spec`, `Asset_account`, `Asset_replay`, and `Asset_loop`
provide a tested opt-in library path for a single cash equity, listed future, perpetual, or long
cash-settled option. It consumes the canonical event contract, executes visible-depth IOC/FOK
taker orders, and posts fees, settlement, funding, and expiry to a fixed-point account. It is not
yet wired to the legacy CLI/report and does not certify passive fills, multi-symbol portfolios,
physical option exercise, short stock, or venue liquidation rules. The exact scope and remaining
gates are in `orderbook-engine/docs/adr/ADR-008-instrument-accounting.md`.

## Deploy on a machine

`deploy/README.md` is the runbook. On a fresh Ubuntu host with sudo:

```
git clone https://github.com/sebastbernal2-ship-it/gqh-delivery-gap.git ~/gqh-delivery-gap
cd ~/gqh-delivery-gap/orderbook-engine
bash deploy/setup.sh
```

That installs Docker and opam, builds and tests the engine, starts the depth and trade collector, installs a daily replay timer, and writes the first report under `collector/data/reports`. Credentials live in `~/.config/quanthacks/env`, outside the repository.

## Architecture

```
src/
  incr.ml        — incremental computation engine (custom)
  side.ml        — order side (bid/ask) and action types
  order_id.ml    — order identifier + map
  price.ml       — price with exact decimal arithmetic
  size.ml        — size (integer share count)
  timestamp.ml   — nanosecond-precision timestamps
  market_types.ml — events, orders, snapshots, stats
  order_book.ml  — core order book engine
  bitemporal.ml  — bitemporal (valid + transaction time) model
  market_data.ml — CSV parser + random event generator
  event_loop.ml  — Lwt-driven replay engine
  websocket_server.ml — real-time WebSocket streaming
  metrics.ml     — instrumentation
  cli.ml         — command-line interface
```

## Replay and simulation modes

The event loop replays venue events by default.
Replay applies adds, cancels, amendments, and executions without inventing trades.
Use `Order_book.apply` when simulating new orders and matching crossing flow.
Use `Order_book.apply_replay` when rebuilding a book from an exchange feed.

The repository contains no exchange dataset.
CSV input is a generic event stream, and `Market_data.generate` creates synthetic events for tests and benchmarks.
`Market_data.parse_feed_csv` accepts a strict venue,symbol,sequence,event-time envelope.
`Market_data.validate_feed` checks identity fields and sequence order.
`Market_data.parse_nyse_taq` now maps free NYSE National TAQ Integrated Feed files into this envelope.
It accepts plain CSV and `.gz` files and supports add, modify, delete, execution, refresh, and replace messages.
A real replay still requires selecting one symbol stream at a time.

SonarX publishes CC0 Hyperliquid L2 snapshots with up to 20 levels per side.
`Sonarx.parse_l2_file` reads the published JSON and `.json.gz` files while preserving decimal prices and sizes as strings.
The public bucket is requester-pays, so AWS request and transfer charges can apply.

```bash
aws s3 cp \
  s3://sonarx-hyperliquid-public/market_data/perp/BTC/l2-summary-snapshots/PARTITION/HEIGHT.json.gz \
  data/BTC.json.gz --request-payer requester
```

`Sonarx_replay` emits parsed snapshots to asynchronous strategy handlers.
Use `run_fast` for backtests and `run` for timestamp-paced playback.
The replay layer stays separate from the order-level book because SonarX does not expose individual order IDs.

`Hf_l2.parse_csv` reads the free Hugging Face Hyperliquid sample as a fixture.
It reconstructs absolute prices from derived cumulative depth.
It is not a source for queue-aware replay.

`Nyse_binary.parse_file` decodes raw little-endian NYSE Pillar messages for time references, symbol mappings, add, modify, delete, execute, and replace events.
It accepts both concatenated messages and XDP packet framing with packet message counts.
`Nyse_capture.read_pcap` extracts IPv4 UDP channels from libpcap captures without concatenating unrelated channels.
Packet sequence gaps fail closed before book replay.
`Nyse_binary.read_symbol_mapping` loads the pipe-delimited exchange mapping file.
`nyse_pcap_replay_check PCAP MAPPING YYYY-MM-DD` validates every captured channel with that mapping.
`Binance_l2` parses Tardis Binance Futures incremental L2 updates and generated snapshots.
`Binance_derivatives` parses mark-price, funding-rate, and forced-liquidation streams.
The public Tardis sample endpoint provides raw Binance perpetual data without credentials on its free sample dates.
Use `binance_l2_check BTCUSDT UPDATES SNAPSHOT ...` for strict replay, L2 metrics, and a small execution smoke benchmark.
Use `binance_derivatives_check MARK_PRICE [LIQUIDATIONS]` to validate mark-price, funding, and liquidation files.
The unauthenticated Tardis endpoint exposes short sample windows, not a continuous full-day capture.
Security-status, imbalance, non-displayed-trade, cross-trade, quote, and trade messages are preserved as no-op control events so symbol sequence checks remain intact.
Stock-summary messages are accepted and ignored because they carry no order-book sequence.
Symbol-clear messages fail closed because they require an explicit book reset boundary.
`Event_replay` is the event-level replay boundary.
It keeps separate books per venue and symbol, rejects sequence gaps, rejects backward event or receive times, validates book invariants after every event, and applies venue events through `Order_book.apply_replay`.
`Order_book.validate` checks order ownership, side placement, level totals, prices, and positive sizes.
The strategy and aggregated-L2 execution modules remain experimental and are not part of the authoritative order-book engine.

## Build

```bash
dune build
dune runtest
```

## Usage

```bash
# Generate sample market data
msim generate -n 10000 -o data.csv

# Replay through the order book
msim run -i data.csv

# Serve live via WebSocket
msim serve -p 8080 -i data.csv

# Bitemporal queries
msim query data.csv --valid-at 2026-01-01T00:00:00Z --tx-at 2026-01-01T00:00:00Z

# Book statistics
msim info data.csv
```

## Run benchmarks

```bash
dune exec examples/benchmark.exe
```

Replay several normalized Binance fixtures and report throughput, heap use, sequence gaps, and final book state.

```bash
opam exec -- dune exec examples/binance_replay_benchmark.exe -- \
  BTCUSDT 0.10 0.001 day-1.jsonl day-2.jsonl
```

Run the friend-facing capture, normalization, and replay demo with one command.

```bash
./binance-demo.sh /path/to/capture.jsonl.gz
```

The first argument can also be an HTTPS fixture URL.

Tiger Cloud is the primary queryable research store for Quanthacks.

The accepted backtester architecture, phases, and first build slice are owned by `orderbook-engine/docs/quanthacks-backtester-plan.md`.

KDB-X remains an optional legacy analytics layer during migration.

The raw evidence and OCaml replay boundaries are documented in `orderbook-engine/docs/quanthacks-data-boundaries.md`.

```bash
q collector/kdbx/analytics.q /data/kdbx spread BTCUSDT
q collector/kdbx/analytics.q /data/kdbx depth BTCUSDT
q collector/kdbx/analytics.q /data/kdbx volatility BTCUSDT
q collector/kdbx/analytics.q /data/kdbx trade_flow BTCUSDT
```

## Key design decisions

See `orderbook-engine/docs/adr/` for architecture decision records:
- ADR-001: Custom incremental engine vs. Jane Street's Incremental library
- ADR-002: Lwt over Async/Eio for concurrency
- ADR-003: Bitemporal model with closed-open intervals

## Requirements

- OCaml 5.2.0+
- dune, alcotest, cmdliner, lwt, csv, fmt, logs, ptime, websocket, base, yojson
