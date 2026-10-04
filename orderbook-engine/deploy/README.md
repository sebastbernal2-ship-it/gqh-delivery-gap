# Deploy on a virtual machine

The repository is self-sufficient on a fresh Ubuntu 24.04 machine with passwordless sudo. One command installs Docker and opam, builds and tests the engine, starts the collector, installs a daily replay timer, and writes the first report.

## Steps

1. Copy or clone the repository onto the machine.

   ```
   git clone https://github.com/sebastbernal2-ship-it/gqh-delivery-gap.git ~/gqh-delivery-gap
   cd ~/gqh-delivery-gap/orderbook-engine
   ```

2. Put the credentials in the secret store, outside the repository.

   ```
   mkdir -p ~/.config/quanthacks && chmod 700 ~/.config/quanthacks
   cp deploy/quanthacks.env.example ~/.config/quanthacks/env
   chmod 600 ~/.config/quanthacks/env
   ```

   Fill in Tiger, Snowflake, and Massive values. The collector needs none of them, and the engine needs none of them, so a machine with an empty file still collects and replays.

   For Snowflake, place the private key at the path named by `SNOWFLAKE_PRIVATE_KEY_PATH` and keep it at mode 600.

3. Run the setup.

   ```
   bash deploy/setup.sh
   ```

   Expect the OCaml switch to take several minutes on a fresh machine. Everything else is quick.

## What runs after that

- The collector container writes five-minute depth and trade windows under `collector/data`.
- `market-replay.timer` runs `deploy/daily-replay.sh` daily at 00:20 UTC. That job normalizes new windows, builds canonical fixtures, replays them through the engine, and writes `collector/data/reports/report-<day>.json`.
- Each report carries the book checksum, the chain gap count, the fill counters per liquidity mode, and the assumption gap against the naive baseline.

## Checking data access

```
bash deploy/check-data-access.sh
```

Reports whether this machine can reach Massive, Tiger Cloud, and Snowflake, using the secret store and printing no credential value. The first run installs the database client libraries into a local virtual environment. A source with no configured credential is reported as skipped.

## Checking it

```
systemctl list-timers market-replay.timer
journalctl -u market-replay.service -n 40
ls -l collector/data/reports
```

Run the daily job by hand for any day, for example:

```
bash deploy/daily-replay.sh 20261004
```

## Where the data lives

Everything the collector and the replay job write is under `collector/data`, which git ignores. Raw capture windows stay immutable, and every fixture gets a manifest with its SHA-256, source hashes, and row count.
