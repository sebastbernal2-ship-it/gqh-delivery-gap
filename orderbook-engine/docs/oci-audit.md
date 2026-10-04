# OCI audit

Audit date: 2026-10-03.

The OCI API reports one running instance named `binance-capture`.

The instance shape is `VM.Standard.A1.Flex` in the Ashburn region, 1 vCPU, 5.8 GB memory, 96 GB disk at 43 percent used.

The OCI API authentication works with the `susquehanna-api` profile.

## Access

SSH works read-only with `~/.ssh/oci-binance-capture.key` as user `ubuntu`.

`~/.ssh/susq-oci` and `~/.ssh/susquehanna-oci-recovery` also authenticate.

## Live workload

The instance runs a second, unrelated competition workload and must not be repurposed or restarted for this project.

Running units include `susq-reactor`, `susq-realtime@0`, `susq-realtime@100`, `susq-realtime@200`, and `susquehanna-realtime-observer`, plus many `susq-*` timers firing every few minutes.

KDB-X is installed at `/home/ubuntu/.kx` with a license file, and `/home/ubuntu/collector/kdbx/db` holds about 1.3 GB of `depth_events.bin` and `trade_events.bin`.

The legacy KDB-X path stays frozen. It receives no new work.

## Capture state

The Docker container `collector-binance-depth-1` has been up for two days and writes to `/home/ubuntu/collector/data` through a bind mount.

Capture files are five-minute windows named `btcusdt-YYYYMMDDTHHMM-...jsonl.gz` for depth and `btcusdt-trades-...` for trades.

Depth is about 900 KB per window and trades about 100 KB per window, from 2026-09-27 to the present, roughly 3.2 GB total.

The collector writes `manifest.jsonl` with per-file `records`, `bytes`, `started`, `ended`, and `sha256`. The recorded hashes match independent local `sha256sum` checks.

## Depth capture finding

The collector fetches the REST snapshot only once at startup and never refreshes it.

Every later depth window therefore contains `depthUpdate` messages with no baseline book.

`collector/normalize_capture.py` correctly rejects such a capture with `capture has no snapshot`.

Consequence: no window on the VM today can be replayed into an authoritative book, and the bootstrap window was rejected as `bootstrap-gap`.

Trades captures stay valid, because they need no snapshot.

Recommended fix, which needs the captain's word because it restarts a live container: fetch a REST snapshot on a fixed interval, for example every five minutes, and keep it inside the capture window.

## Fix deployed

On 2026-10-03 at 23:38 UTC the collector was rebuilt with a periodic snapshot refresh.

The deployed file hashes to `7dee5844b8a18a96a9d14515235c1ba7`, matching the repository copy, and the previous file is backed up at `/tmp/collector-backup-20261003T233826.py` on the VM.

The restarted collector wrote a snapshot into its first window, and every later window starts with one.

The REST snapshot uses `REST_LIMIT=1000`, so a fixture's baseline holds the top 1000 levels per side.
Updates may introduce levels outside that range, and the replay book keeps them.

Capture quality note: Binance futures update id ranges are not contiguous.
Consecutive updates jump ahead by tens of ids, so only the previous-update id chain is authoritative.
The collector, `collector/normalize_capture.py`, and `src/depth_chain.ml` share that rule.

## Slice used for this project

One depth window and one trades window from 2026-10-03T21:55Z were copied to `collector/data/oci-slice/` with their `manifest.jsonl`.

The trades window normalized, loaded into Tiger, and exported as a validated canonical fixture.

The pre-fix depth window was rejected by the normalizer and was not loaded.

After the fix, the 2026-10-03T23:40Z depth window normalized cleanly: 1 snapshot, 1,527 updates, all applied, raw file `sha256 4ea7eca12e36cc9b47f4934c6d91097a836502eb53872ca9cc71bc5d46401f44`.

Those rows loaded into Tiger `depth_events`, and the canonical fixture `collector/data/fixtures/depth-20261003T2340.jsonl` (`sha256 82e9ca08078ec7d6d5bd08393d8945428021d7af30a003fc6aa5b8169621fad0`) validates with the OCaml checker at zero chain breaks.
