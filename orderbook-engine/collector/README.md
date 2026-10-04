# Binance Futures live depth capture

This service captures public Binance Futures depth data without API credentials.

It records raw combined-stream messages and REST snapshots as immutable gzip JSONL segments.
It writes a `manifest.jsonl` file with source paths, time bounds, record counts, and compressed sizes.
Segments rotate every five minutes by default so validated data reaches KDB-X without waiting for an hourly file to close.
It reconnects with exponential backoff and takes a new snapshot after each reconnect.
It captures Binance trade events in separate `*-trades-*` segments when `CAPTURE_TRADES` is enabled.
It records exchange instrument metadata, including price tick and quantity step, in `instruments.jsonl`.

## Run on an always-free VM

Use an Oracle Cloud Infrastructure Always Free VM with persistent block storage.
Do not run this in the development checkout.

Copy this directory to the VM, then run:

```sh
docker compose up -d --build
docker compose logs -f
```

The capture files are under `collector/data/` on the VM.
The container health check fails on stale output, corrupt gzip, missing manifest rows, or high disk usage.

## Configuration

Set `SYMBOLS` to a comma-separated list of USDS-M symbols.
Set `DEPTH_SPEED` to `100ms` or `1000ms`.
Set `REST_LIMIT` to the required Binance snapshot depth.
Set `CAPTURE_INTERVAL_SECONDS` to control the immutable segment duration.
Set `CAPTURE_TRADES=0` to disable trade-event capture.
Set `MAX_CAPTURE_AGE_SECONDS` and `MAX_DISK_PERCENT` to tune health thresholds.

## Replay a capture

The files are gzip-compressed Tardis-compatible JSONL.
Decompress a selected segment before passing it to `binance_l2_check`:

```sh
gzip -cd data/binance/btcusdt-YYYYMMDDTHHMM-<capture-id>.jsonl.gz > /tmp/btcusdt.jsonl
```

The first capture file contains updates received while the REST snapshot was fetched.
The strict replay bootstrap logic handles those buffered updates.

A reconnect writes another snapshot marker and gets a new capture ID.
Replay each reconnect segment separately when validating recovery.

## Safety boundary

This collector records market data only.
It does not submit orders and does not use API keys.
A capture is not trusted until the project replay validator accepts its sequence and timestamp checks.

## Tiger Cloud research store

Tiger Cloud is the primary queryable store for Quanthacks research data.

The raw capture files and OCaml replay engine remain separate authorities.

Install and authenticate the Tiger CLI outside this repository:

```sh
curl -fsSL https://cli.tigerdata.com | sh
tiger config set read_only on
tiger auth login
```

Configure the Tiger MCP server after authentication:

```sh
tiger mcp install codex
```

Load a Tardis book-depth metrics file into the observations table:

```sh
python3 collector/tiger/ingest_book_depth.py collector/data/BOOKDEPTH.csv --symbol BTCUSDT
```

Fetch a verified slice of capture windows from the OCI VM, then load it.
`--latest N` counts files, and each five-minute window has a depth file and a trades file, so a day is `--latest 576`:

```sh
python3 collector/oci_fetch_windows.py 20261003T2340 20261004T0015 collector/data/slice-20261004
bash collector/tiger/ingest_slice.sh collector/data/slice-20261004
```

The fetch verifies every file against the VM's own manifest SHA-256 and skips windows that are still open or that carry no snapshot, because such a window cannot be replayed.
The ingest script normalizes each window, switches the CLI to `read_only prod` for the load, and always restores `read_only all`.

Load normalized capture rows into the depth and trade tables:

```sh
python3 collector/tiger/ingest_normalized.py SLICE/trades-normalized.jsonl --kind trades
python3 collector/tiger/ingest_normalized.py SLICE/depth-normalized.jsonl --kind depth
```

Produce the normalized JSONL with `collector/normalize_capture.py` for depth and `collector/normalize_trades.py` for trades.
A depth capture is only replayable when its window contains a REST snapshot; the normalizer rejects windows without one.

The load needs a writable session. Set `read_only prod` so PROD services stay protected while DEV stays writable, then restore `read_only all`.
The script is idempotent and prints the exact rollback statement for the load.

Export a bounded canonical fixture with a provenance manifest:

```sh
python3 collector/tiger/export_fixture.py \
  --kind observations --format canonical \
  --symbol BTCUSDT \
  --start 2024-01-01T00:00:00Z \
  --end 2024-01-01T00:10:00Z \
  --output fixture.jsonl --manifest fixture.manifest.json
opam exec -- dune exec examples/exec_event_check.exe -- fixture.jsonl
```

Use `--format normalized` with `--kind depth` for the legacy Binance normalized JSONL that `Binance_l2` consumes:

```sh
python3 collector/tiger/export_fixture.py \
  --service SERVICE_ID \
  --symbol BTCUSDT \
  --start 2024-01-01T00:00:00Z \
  --end 2024-01-02T00:00:00Z \
  --output /tmp/btcusdt-tiger.jsonl
opam exec -- dune exec examples/binance_normalized_check.exe -- \
  --json-report BTCUSDT 0.10 0.001 /tmp/btcusdt-tiger.jsonl
```

See `orderbook-engine/docs/quanthacks-data-boundaries.md` and `orderbook-engine/collector/tiger/schema.sql` for the storage contract.
The backtester phases built on this store are owned by `orderbook-engine/docs/quanthacks-backtester-plan.md`.

## KDB-X data layer

KDB-X is an optional analytical store beside the collector.
It does not replace the raw files or the OCaml replay engine.

KDB-X Community Edition requires a license from the KX Developer Center.
Install the ARM64 KDB-X build on the OCI VM after obtaining that license.
Do not put the license or KDB-X binaries in this repository.

Validate a completed capture segment and create normalized JSONL:

```sh
python3 normalize_capture.py data/btcusdt-YYYYMMDDTHH.jsonl.gz /tmp/btcusdt-normalized.jsonl
```

Load the normalized rows from the `kdbx` directory:

```sh
q load.q /tmp/btcusdt-normalized.jsonl /data/kdbx
```

The OCI VM runs `binance-kdbx-ingest.timer` every five minutes.
It waits for completed gzip segments, validates them, and loads them into `/home/ubuntu/collector/kdbx/db/depth_events.bin`.
The timer validates depth and trade segments with their matching normalizer.
It skips files whose validation or checksum does not pass.

The loader stores update IDs as integers, event time as milliseconds, received time as a KDB timestamp, and level changes as nested bid and ask columns.
Every row includes the raw source path and SHA-256 digest.

Export validated rows for OCaml replay:

```sh
cd collector/kdbx && q export.q /home/ubuntu/collector/kdbx/db BTCUSDT > /tmp/btcusdt-normalized.jsonl
cd ../.. && dune exec examples/binance_normalized_check.exe -- --json-report BTCUSDT 0.10 0.001 /tmp/btcusdt-normalized.jsonl > /tmp/btcusdt-ocaml-report.json
```

The export is an interchange path, not a replacement for raw gzip evidence.
Run `cd collector/kdbx && ./smoke.sh /tmp/btcusdt-normalized.jsonl /tmp/btcusdt-trades.jsonl` after installing licensed KDB-X.
The smoke test checks that KDB-X round-trips both row counts.
Certify a complete boundary chain with:

```sh
python3 certify_replay.py data/btcusdt-YYYYMMDDTHHMM-<capture-id>.jsonl.gz \
  /tmp/btcusdt-normalized.jsonl \
  --kdb-export /tmp/btcusdt-kdb-export.jsonl \
  --ocaml-report /tmp/btcusdt-ocaml-report.json
```

The certificate checks the raw SHA-256, row counts, normalized source hashes, exact KDB-X row equality, and the OCaml replay report when supplied.
Use `backup.sh` with OCI Object Storage credentials to copy raw segments and manifests off the VM.
Install `binance-backup.service` and `binance-backup.timer` after placing `OCI_NAMESPACE` and `OCI_BUCKET` in `/etc/market-simulator-backup.env`.
Do not delete local evidence until the backup command succeeds.
Trade segments use `normalize_trades.py` and load into the KDB-X `trade_events` table.
Export them with `cd collector/kdbx && q trade_export.q /home/ubuntu/collector/kdbx/db BTCUSDT > /tmp/btcusdt-trades.jsonl`.
Replay the export with `cd ../.. && dune exec examples/binance_trades_check.exe -- /tmp/btcusdt-trades.jsonl`.
