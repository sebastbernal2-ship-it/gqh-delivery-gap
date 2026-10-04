# Quanthacks backtester plan

Status: accepted 2026-10-03.
Owner: this file.
Related: `orderbook-engine/docs/quanthacks-data-boundaries.md`, `orderbook-engine/docs/oci-audit.md`, `orderbook-engine/docs/adr/ADR-006-kdbx-data-layer.md`.

## Goal

Build a venue-faithful, production-grade backtester for Quanthacks.
The backtester must model capital constraints, liquidity, latency, fees, funding, margin, and liquidation closer to reality than a standard vectorized backtester.
The engine must be reusable and embeddable, not only a script.

## Non-goals

- No strategy alpha research in this repository.
- No vectorized indicator backtesting.
- No claim of order-level FIFO accuracy from aggregated L2 data.
- No Rust or C++ port before profiling the corrected OCaml engine.

## Current state (re-audited 2026-10-03)

Strong foundations:

- `Order_book` is the authoritative engine: order IDs, FIFO matching, cancels, executions, sequence checks, `validate`, bitemporal intervals.
- `Event_replay` enforces per-venue and per-symbol isolation, sequence continuity, monotonic event and receive time, and post-event book validation.
- `Binance_l2` performs strict normalized replay with gap detection and unit validation through `Binance_units`.
- `Binance_trades`, `Binance_derivatives` parse aggregate trades, mark price, funding, and liquidations.
- `Binance_units` does exact decimal tick and lot validation.
- Harness: `opam exec -- dune runtest`, `opam exec -- dune build`.
- Performance baseline exists: `examples/binance_replay_benchmark.ml` reports rows/sec, heap, gaps, and final book state.
- Tiger Cloud store and read-only MCP path exist with schema in `collector/tiger/schema.sql`.
- Bounded Tiger export exists: `collector/tiger/export_fixture.py`.

Gaps that block the goal:

- `Binance_account`, `Binance_backtest`, `L2_backtest`, `L2_execution`, and `Binance_maker_model` use `float` for prices, quantity, fees, margin, and P&L.
- The backtest path is snapshot-driven, not event-driven; there is no order lifecycle with submit, ack, cancel, and replace latency.
- No capital reservation model beyond a simple leverage check.
- No fill uncertainty reporting contract; the maker model produces bounds that no report records.
- Replay authority is per-module, not a single declared event contract.
- No Quanthacks fixtures are ingested; Tiger `depth_events`, `trade_events`, `observations`, and `source_manifests` are empty.
- OCI `binance-capture` VM is running but SSH access fails with `Permission denied (publickey)`.
- KDB-X is legacy; it stays as an optional path and receives no new work.

## Target architecture

```text
Raw files and vendor artifacts (immutable, hashed)
        |
        v
Tiger Cloud / TimescaleDB research store
  raw manifests, normalized rows, observations
        |
        v
Bounded, hashed replay fixture (JSONL manifest + rows)
        |
        v
OCaml reference replay and execution kernel
  strict replay -> event-driven execution -> account state
        |
        v
Quanthacks strategy layer and reports
```

Hard rules:

- Tiger stores and joins data. Tiger never decides replay order.
- The OCaml engine remains the correctness authority.
- Strategies never query Tiger inside the replay loop; all features arrive in the fixture.
- Aggregate L2 never proves FIFO; it yields bounded fill modes.

## Phases

### Phase 0: Freeze boundaries

- Preserve the current branch and uncommitted work.
- Create a dedicated Quanthacks Tiger namespace; keep `aws_gpu_spot_prices` untouched.
- Audit the OCI VM with the correct SSH key before any change.
- Record raw versus rebuildable data classes.

Exit: boundaries documented, no data at risk, existing DEV tables untouched.

### Phase 1: Canonical event contract

One declared event type for depth snapshot, depth update, trade, mark price, funding, liquidation, external observation, strategy decision, order intent, cancel, acknowledgement, and fill.

Every event carries venue, symbol, event time, receive time, source ID, source hash, sequence or trade ID when available, and quality status.

Money, price, and quantity use integer ticks, lots, and fixed-point units in the engine; decimal strings stay at the ingestion boundary.

Exit: contract module with round-trip tests and a documented unit policy.
Status: done 2026-10-03. `src/exec_event.ml` owns the event envelope, `src/exec_units.ml` owns the fixed-point arithmetic, and `orderbook-engine/docs/adr/ADR-007-execution-units.md` owns the unit policy.

### Phase 2: Tiger fixture pipeline

- Load validated source data into Tiger with manifests and hashes.
- Join market data with external observations.
- Export a bounded time range sorted by the replay clock.
- Emit an immutable fixture plus a manifest containing row count, time range, source hashes, query version, and configuration hash.

`collector/tiger/export_fixture.py` is the starting point and must grow trade, funding, liquidation, and manifest export.

Exit: one real multi-day fixture exported and hash-verified.
Every fixture is validated with `opam exec -- dune exec examples/exec_event_check.exe -- FIXTURE.jsonl`.
Status: ingest and canonical export are live 2026-10-03.
`collector/tiger/ingest_book_depth.py` loads book-depth observations with a manifest, and `collector/tiger/export_fixture.py --format canonical` emits canonical events plus a provenance manifest.
The observations path is proven end to end on 2024-01-01 BTCUSDT data.
Status update 2026-10-03: the trade path is proven end to end on a real capture slice from the OCI VM (2,613 trades, manifest-verified hashes, canonical fixture validated by the checker).
The depth path is now proven too: the collector refreshes its REST snapshot at every window, and the first post-fix window produced a canonical depth fixture that validates with zero chain breaks.
Fixture hashes and the capture-quality rule live in `orderbook-engine/docs/oci-audit.md`.

### Phase 3: OCaml replay kernel

Two explicit modes:

- Order-level replay for feeds with order identity.
- Aggregated L2 replay for Binance and similar feeds.

Strict handling for snapshot boundaries, sequence gaps, event time versus receive time, trade and book ordering, funding timing, symbol resets, and stale or missing data.

Exit: both modes replay a multi-day fixture with zero gaps and a validated final book.

Status: the aggregated mode is live 2026-10-03. `src/l2_book.ml` owns the price-level book with exact integer units and a deterministic checksum, and `examples/l2_replay_check.ml` replays a canonical fixture and reports the final book.
The first real depth fixture replays with zero gaps: best bid 84,744.0, best ask 84,744.1, 1 snapshot, 1,527 applied updates, checksum `e2b383a97157fe099a701016440cf921`.

### Phase 4: Realistic execution model

Replace snapshot-only backtesting with event-driven simulation covering strategy decision time, network and venue latency, submission, acknowledgement, cancel and replace latency, resting order state, taker fills against visible depth, maker fill bounds, partial fills, fees, funding, leverage, margin, liquidation, and capital reservation.

For aggregated L2, expose three fill modes: conservative, heuristic, optimistic. Every result records which mode produced it.

Exit: deterministic golden scenario tests for each invariant class.

Status: the account core is live 2026-10-03. `src/exec_account.ml` owns fixed-point margin reservation, fees, funding, P&L, leverage checks, reduce-only rules, and liquidation, with golden scenarios in `test/exec_account_test.ml` and exact rounding helpers in `src/exec_units.ml`.
Fill modes are live: `src/exec_fills.ml` walks visible depth for taker fills and bounds maker fills under three modes (conservative, heuristic, optimistic), and `examples/quote_maker_demo.ml` quotes a resting bid against a real depth and trade fixture, applies inferred maker fills to the account, and reports the mode with its uncertainty statement.
A real paired window (2026-10-03T2340Z) replays at 1,528 depth events and 688 trades, and the inferred fill ordering holds on that data: conservative 0, heuristic 0, optimistic 0.1 BTC.
Latency is live too: `src/exec_loop.ml` runs the merged stream in receive-time order, applies a `decision_ns` delay before a submit becomes live and a `cancel_ns` delay before a cancel takes effect, so a cancel leaves the order exposed and fillable, and a market or crossing limit takes visible depth at once while a market remainder is cancelled like an IOC order.
Exit is met: `test/exec_account_test.ml`, `test/exec_fills_test.ml`, and `test/exec_loop_test.ml` cover the invariant classes with golden scenarios.
Next in the plan: the strategy interface and the deterministic fixture report (Phase 5 and 6).

### Phase 5: Quanthacks strategy interface

A strategy receives replay time, book state, recent trades, account state, and prefetched features, and returns order intents.

All features are prefetched into the fixture.

Exit: one quote-driven strategy runs end to end without touching Tiger during replay.

Status: done 2026-10-03. `src/exec_strategy.ml` prefetches an exact feature set in one pass (trade count, buy and sell aggressor volume, buy share in basis points, mid range in ticks, book imbalance in basis points) and hands each strategy the features for its own event index. `skewed_quote` quotes at the touch while buy pressure holds and cancels under sell pressure, driven only by prefetched features.

### Phase 6: Validation contract

Acceptance for a run requires matching final book state, final account state, fees, funding, liquidation state, order results, and fixture hashes.

Exit: a reproducible report with throughput, memory, gap count, fill-uncertainty bounds, and failure reasons.

Status: done 2026-10-03. `examples/fixture_report.ml` replays a fixture under all three modes with one feature-driven strategy and prints one JSON report: fixture paths and manifest provenance, event and row counts, parse errors, chain gaps, superseded and pending counts, the validated book checksum, latency settings, per-mode account summaries, the fill-uncertainty bounds, throughput, and heap. `--deterministic` omits timing and heap so two runs are byte-identical.

### Phase 7: Performance

Profile the corrected OCaml engine first.
If the hot path is too slow, keep OCaml as the reference and port only the profiled replay kernel to Rust using exact integer arithmetic, with golden-fixture parity between both implementations.

The OCI VM may run collection and batch jobs. It is not the primary development or correctness environment.

## First build slice

1. Add the Quanthacks Tiger namespace.
2. Ingest one real market-data fixture.
3. Export it through Tiger with a manifest.
4. Replay it in OCaml with strict validation.
5. Run one quote-driven strategy.
6. Produce a deterministic report with fills, capital, fees, funding, and uncertainty bounds.

This slice exposes the real missing pieces faster than a broad rewrite.

## Verification

Every phase ends with a runnable check that fails when the phase invariant breaks:

- Phase 0 to 2: fixture and manifest hash checks.
- Phase 3: replay gap and book-invariant checks.
- Phase 4: golden scenario tests for leverage, reduce-only, liquidation, fees, and funding.
- Phase 5 and 6: end-to-end deterministic report comparison.

Repository-wide gate: `opam exec -- dune runtest && opam exec -- dune build`.

## Resolved: multi-window snapshot alignment

Resolved 2026-10-04.

The strict replay and the execution loop now agree exactly on a fixture that spans eight capture windows: 3,492 bid levels, 7,149 ask levels, zero chain gaps, one checksum, and it is not crossed.

The fix is ordering, not a contract change: `collector/tiger/export_fixture.py` orders depth rows by the five-minute wall-clock bucket with the snapshot first inside its bucket, so a fixture replays in file order and no consumer has to infer which updates were buffered during a snapshot fetch.

The row's own `segment` column cannot do this, because it restarts in every per-window normalized file.

## Resolved: fill price sanity in multi-window runs

Resolved 2026-10-04.

The fee on the slice run belongs to a taker fill, not a maker fill. The conservative and heuristic fills took liquidity when the quote crossed the touch, so 338,860,400 is the four basis point taker fee on 100,000 units at 84,715.1, which sits inside the window's range of 84,670.6 to 84,816.8. The optimistic fill rested and paid the two basis point maker fee at 84,744.1.

My first reading of that number assumed maker pricing and produced a false alarm.

Every mode summary now reports the best bid and ask range it saw, so any fill price can be checked against the book the run actually had.

## Slice runs

Recorded 2026-10-04.

A ninety-minute slice (2026-10-03T23:20Z to 2026-10-04T00:55Z) is validated end to end:

- 34 windows fetched and hash-verified, 8 skipped as open or unreplayable.
- 42,652 depth events with 15 snapshots and 98,348 trades, 141,000 events in total.
- Zero chain gaps, no book mismatch, byte-identical runs.
- One checksum from the strict replay and all three modes: `c633fdfd5857d39369094bbb97725cf1`.
- All three modes fill 100,000 units; the uncertainty range is 100,000 to 100,000.
- 3,373 bid levels and 3,277 ask levels.

Correction, 2026-10-04: earlier runs of this slice reported 8,290 ask levels and a different checksum. `L2_book.apply_snapshot` cleared only the bid side, so stale asks accumulated across snapshots and crossed the book. A snapshot now replaces both sides, which removed 5,013 stale ask levels. The single-window checksum is unchanged, because that fixture opens with one snapshot and the bug needed a second one to show.

A second bug came from the same work: `Timestamp.add_ns` mishandled negative offsets, because a Ptime span stores days plus nonnegative picoseconds. A trailing window built with a negative offset never expired, so the regime measure stayed stuck at its latest value.

Procedure for a longer run, for example a full day once capture accumulates for one:

```sh
python3 collector/oci_fetch_windows.py --latest 576 collector/data/slice-day
bash collector/tiger/ingest_slice.sh collector/data/slice-day
python3 collector/tiger/export_fixture.py --kind depth --format canonical --symbol BTCUSDT \
  --start START --end END --output depth.jsonl --manifest depth.manifest.json
python3 collector/tiger/export_fixture.py --kind trades --format canonical --symbol BTCUSDT \
  --start START --end END --output trades.jsonl --manifest trades.manifest.json
opam exec -- dune exec examples/exec_event_check.exe -- --json-report depth.jsonl
opam exec -- dune exec examples/fixture_report.exe -- --deterministic depth.jsonl trades.jsonl depth.manifest.json 25 10
```

Two numbers are expected rather than alarming. The fixture's file order puts each snapshot before the updates that were buffered during its fetch, so `out_of_order_receive` from the checker equals the snapshot count by construction. `superseded` in the checker counts updates a later snapshot already contains.

A full day needs the capture to accumulate: the snapshot refresh was deployed on 2026-10-03 at 23:38 UTC, so replayable windows only exist from that point on.

## Direction: realism gap, regimes, and data recall

Recorded 2026-10-04, from the captain.

The engine is the product, and its first job is to expose where simple risk and portfolio assumptions break: liquidity, capital constraints, latency.

The measured realism gap is live. `src/naive_backtest.ml` reproduces the textbook baseline (every order fills in full at the mid, no capital limit) and `examples/fixture_report.ml` reports the difference per mode.

On the ninety-minute slice the gap is stark:

- naive: 251 orders, 25,100,000 units filled, 851 USDT of fees, equity 488.5 USDT from 1,000.
- realistic, conservative and heuristic: 100,000 units filled, equity 996.6 USDT.
- realistic, optimistic: 100,000 units filled, equity 998.3 USDT.
- fill ratio: 39 basis points of the intended size.
- 89 of the naive orders would have been refused by the capital rule.

The naive model does not merely overstate fills. It fabricates 251 fills where the engine allowed one, and turns a flat strategy into a 51 percent loss. Both directions of error matter, and only the engine sees the second.

Next for the engine:

1. Regime and factor conditioning. Classify volatility and other regimes from the fixture, attribute results per regime, and emit a conditioning rule, so a strategy that only earns in calm conditions can be told to trade only then.
2. Factor and machine learning inputs, only through prefetched features, never during replay.
3. Fast recall of the Quanthacks data that lives on Snowflake, with Tiger and local fixtures as the replay-side cache.

Deployment: Vultr hosts the engine and the collector. The OCI collector stops once Vultr has produced a proven day of replayable windows.

## Regimes

Recorded 2026-10-04.

`src/regime.ml` owns volatility regimes. The measure is trailing mid-price travel in ticks over a wall-clock window, with a test that pins the rise and the decay. The threshold is the median of the first half of a run, and the same threshold is then applied to the whole run and to each half, so the holdout half shows whether a conditioning rule survives out of sample. Regime attribution folds the fill blotter, so a fill is counted in the regime in force at its time.

First results on the ninety-minute slice: threshold 371,000 ticks, one fill, in the low-volatility regime, netting minus the taker fee. The conditioning rule is empty because nothing paid. That is an honest result for a quote strategy that traded once, and it says the next step is a strategy that actually trades in both regimes before any conditioning rule means anything.

## Deployment, 2026-10-04

The repository is clone-and-go. `deploy/README.md` is the runbook, `deploy/setup.sh` is the one command, and `deploy/quanthacks.env.example` lists the secret names with no values in the repository.

Running on Vultr, host `gqh-book-engine-01`, user `linuxuser`: the collector container is healthy and writing five-minute depth and trade windows, `market-replay.timer` replays daily at 00:20 UTC, and the first report is at `collector/data/reports/report-20261004.json`.

First Vultr day report: 19,662 events, 5 snapshots, zero chain gaps, no book mismatch, checksum `ae92c1786a91bf8c8a3e8379cb7d27d7`, one fill per liquidity mode with fees 339,189,200 for conservative and heuristic and 169,585,600 for optimistic.

Cross-machine check: the Vultr fixture replayed on the development machine gives the same checksum and the same counters, so capture, normalization, fixture building, and replay agree across hosts.

Three defects were found and fixed while making the clone work. Docker created the data directory as root, so the service now runs as the invoking user. A capture window still being written has no snapshot, so the daily job skips it and retries next run instead of failing. Day selection follows receive time rather than the label in the file name, because a window starting before midnight carries the previous day's label.

The OCI collector stays up until Vultr has produced a full day of replayable windows.
