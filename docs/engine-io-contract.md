# Engine interface: input and output

The simulator reads one interchange format and writes one report format. Data sources adapt to the interface, not the other way around.

`src/exec_event.ml` owns the input contract. `docs/adr/ADR-007-execution-units.md` owns the units. Working samples live in `examples/io-contract/`.

## Input: canonical JSONL

One JSON object per line, one event per line, in replay order.

```
examples/io-contract/depth-sample.jsonl     three depth events
examples/io-contract/trades-sample.jsonl    two trades
examples/io-contract/depth-sample.manifest.json
```

### Envelope, every event

| field | type | meaning |
|---|---|---|
| `kind` | string | `depth_snapshot`, `depth_update`, `trade`, `mark`, `funding`, `liquidation`, `observation`, `decision`, `order_intent`, `order_ack`, `order_cancel`, `fill` |
| `venue` | string | venue identity, for example `binance-futures` |
| `symbol` | string | instrument, for example `BTCUSDT` |
| `event_time` | string | venue time, RFC 3339, nine fractional digits, UTC |
| `receive_time` | string | when we observed it, same format. Replay order and latency use this |
| `sequence` | integer or null | optional venue sequence |
| `source_id` | string | provenance identity, not empty |
| `source_path` | string | provenance location, not empty |
| `source_sha256` | string | provenance hash of the source artifact |
| `quality` | string | `healthy`, or `suspect` with `quality_reason` |

### Units, integers only, no floats

| quantity | unit | scale | example |
|---|---|---|---|
| price | ticks | 1e-4 | `847441000` is 84,744.10 |
| quantity | units | 1e-6 | `250000` is 0.250 |
| money | units | 1e-8 | fee `339189200` is 3.39189200 |
| rate | units | 1e-8 | funding `10000` is 0.00010000 |

Decimal strings appear only at ingestion. Convert with the recorded scale and round half away from zero.

### Payload per kind

Depth snapshot:

```
"last_update_id":1000,
"bids":[[847440000,1500000],[847439000,2500000]],
"asks":[[847441000,2000000],[847442000,500000]]
```

Depth update. A level with quantity zero removes that price:

```
"first_update_id":1001,"last_update_id":1002,"previous_update_id":1000,
"bids":[[847440000,0]],
"asks":[[847441000,1200000]]
```

Trade:

```
"trade_id":1,"price_ticks":847441000,"quantity_units":250000,"buyer_is_maker":false
```

The other kinds follow the same shape and are listed in `src/exec_event.ml`: `mark` carries `mark_ticks`, `index_ticks`, `rate`, `next_funding_time`; `funding` carries `rate` and `mark_ticks`; `liquidation` carries `side`, `price_ticks`, `quantity_units`; `observation` carries `data_type` and a JSON `payload` string; `decision` carries `strategy` and `note`; `order_intent` carries `order_id`, `side`, `price_ticks`, `quantity_units`, `tif`, `reduce_only`, `post_only`; `order_ack` carries `order_id`, `accepted`, `reason`; `order_cancel` carries `order_id`; `fill` carries `order_id`, `side`, `price_ticks`, `quantity_units`, `fee`, `liquidity`.

### Two rules that make a capture replayable

1. Update id ranges are not contiguous at this venue. Only `previous_update_id` forms the chain, and a snapshot restores trust when the chain breaks.
2. Fixture order is a contract. Order rows in five-minute buckets of `receive_time`, snapshot first inside its bucket, then by `receive_time`, then by source and line. A window that starts before midnight carries the previous day's label, so selection filters on `receive_time`, never on a file name.

## Output: one report per run

```
examples/io-contract/report-sample.json
```

Command:

```
opam exec -- dune exec examples/fixture_report.exe -- --deterministic \
  depth.jsonl trades.jsonl depth.manifest.json 25 10
```

Top level keys: `events`, `depth_events`, `trade_events`, `snapshots`, `parse_errors`, `chain_gaps`, `chain_pending`, `chain_superseded`, `book_mismatch`, `book_mismatch_note`, `book_checksum`, `book_best_bid`, `book_best_ask`, `book_bid_levels`, `book_ask_levels`, `depth_fixture`, `trades_fixture`, `manifest`, `features`, `modes`, `assumption_gap`, `regimes`, `uncertainty`, `latency_decision_ms`, `latency_cancel_ms`, `throughput`.

- `book_checksum` is the deterministic fingerprint of the replayed book after the last event.
- `modes` is one entry per liquidity mode, conservative, heuristic, and optimistic, each with `fills`, `filled_units`, `fees`, `realized_pnl`, `liquidations`, `rejected`, `reserved_margin`, `collateral`, `book_best_bid`, `book_best_ask`, `heap_bytes`, `seconds`.
- `uncertainty` gives the fill range across the modes.
- `assumption_gap` compares the run against a naive baseline that fills every order in full at the mid with no capital limit.

Sample run on the sample input:

```
events=5 depth_events=3 trade_events=2 snapshots=1
chain_gaps=0 book_mismatch=false
book_checksum=e4a09c8d1a4350395c6d8615cca5781f
book_best_bid=847440500 book_best_ask=847441000 book_bid_levels=2 book_ask_levels=2
```

## Identity

There is no synthetic run id in the format today. Identity is content:

| scope | identity |
|---|---|
| fixture | `manifest.fixture_sha256`, plus `row_count`, `event_time_range`, and `source_hashes` |
| run | `book_checksum` plus the fixture hash, which is reproducible on any machine |
| source row | `source_id`, `source_path`, `source_sha256` on every event |

If an explicit `run_id` field is wanted for lineage, it is a one-line addition to the report. The samples above show the current format, unchanged.

## Adapting other sources

`docs/data-source-matrix.md` records what each source actually holds, checked against the live source. Read it before writing an adapter: Snowflake carries daily bars and macro series and no quotes or depth at all, Massive carries tick trades and tick NBBO quotes but no order book, and Binance carries aggregated depth with no order identity.

- Snowflake export: select the range, convert price and quantity to the recorded scales, and emit these rows with `source_id` set to the table and `source_sha256` to the query result hash. `collector/build_fixture.py` shows the conversion path already used locally.
- Tiger telemetry: the same rows, with `source_id` naming the Tiger table.
- Massive trades and NBBO quotes: trades map directly. Quotes map to `depth_update` rows that carry only the top of book, which the engine replays in the aggregated bounded-fill modes and never as order-level FIFO.
