# kdb+/q time-series system on HiPerGator

Owner: vshnu1. This is the shared historical research store and query layer for validated
numeric time series. It is separate from the existing JevLike workloads and does not assert any
trading edge.

## System boundary

- **Snowflake** remains the canonical cloud archive for raw source files, filings, EIA vintages,
  provenance manifests, and the full source history.
- **TigerData** remains the shared PostgreSQL/Timescale operational/query service. Its database
  is already near the reported allowance; no loader here writes to TigerData.
- **kdb+/q HDB on HiPerGator Blue** is the active research copy for selected numeric time-series
  tables (initially daily equity bars and corporate actions). It is built from explicit,
  checksummed source batches. It does not hold SEC document archives or raw source JSON by default.
- **Git** contains code, schemas, tests and manifests only. Do not commit data, license files,
  credentials, or account-specific absolute paths.

The migration is copy → reconcile → restore-test → cut over → delete the exact redundant TigerData
objects. No TigerData deletion is automated. A completed HDB does not replace Snowflake as the
archive or backup.

## First slice

`massive_bars` (adjusted daily bars) is the first candidate because its full five-symbol batch is
identified in the handoff (`bec91f7c380937d3d647ade8214968c13abd4bde032c9a7cf7741f0ee58306cd`).
The unadjusted batch must be selected by its own verified batch SHA-256; do not union batches or
canaries. Export is explicit by `source_id` plus `batch_sha256` and normalizes prices to integer
units of `1e-8 USD`, volume to integer shares, and event date to UTC session date. This avoids treating
binary floating-point display as exact decimal arithmetic. Source row hashes are retained.

Prices are stored as signed 64-bit integer units of `1e-8 USD` (exactly representable values only),
volume as integer shares, and event date as UTC session date. The first deployment should be a
synthetic smoke job, then a 100-row real-data canary, followed by
the complete daily-bar batch. Corporate actions come after bar reconciliation. The system does not
yet migrate the large AWS spot table or broad macro/EIA tables; those require a separate scope and
capacity decision.

## HiPerGator prerequisites

1. The project owner confirmed an appropriate KX license path for this shared educational
   research use. Do not use kdb+ Personal Edition on HiPerGator; its published terms exclude
   third-party cloud and educational-institution benefit use. Keep the approved license file
   outside Git and outside shared/public paths.
2. UF Research Computing confirms the licensed runtime can be installed/used by the allocation.
3. `Q_BIN` points to the approved executable; `HPG_BLUE_DIR` points to the existing team Blue
   directory. Neither value belongs in Git.
4. Blue quota is checked with `blue_quota`. UF states Blue is not backed up by default, so a
   durable second copy and restore path must exist before any TigerData deletion.

No KX binary/license is included in this repo. Installation is intentionally manual and follows
the approved KX package and license delivery method.

## Local/offline tests

The exporter and job wrappers can be tested without credentials, Slurm or a live database:

```sh
python3 -m unittest discover -s hpc/kdb-timeseries/tests -v
```

Wrapper tests use a stub q process to check spooled-script execution, receipt provenance,
checksum/row-count rejection, failed-loader behavior and version protection. They do **not**
execute the q loader or verify an HDB. See [VALIDATION.md](VALIDATION.md) for root causes,
evidence boundaries and the remaining cluster acceptance steps.

## HiperGator smoke and build

From a HiPerGator login node after software approval and installation:

```sh
export Q_BIN=/approved/path/to/q
export HPG_BLUE_DIR=/blue/<allocation>/<shared-project-path>
export GQH_REPO_ROOT=/absolute/shared/path/to/gqh-delivery-gap
blue_quota
mkdir -p "$HPG_BLUE_DIR/gqh-kdb/logs"
cd "$HPG_BLUE_DIR/gqh-kdb/logs"
sbatch "$GQH_REPO_ROOT/hpc/kdb-timeseries/slurm/smoke.slurm"
```

The smoke job creates a small synthetic date-partitioned HDB under Blue and checks its schema,
partition dates, rows and integer price fields. It writes logs to the submission directory and
does not need TigerData, Snowflake, a Massive key, or market data.

Both Slurm wrappers require exported `GQH_REPO_ROOT`, pointing to a checkout visible on compute
nodes. They reject missing, relative or wrong-component paths. The script location is a Slurm
spool copy and the submission directory may contain only logs, so neither locates the repository.

After the smoke job passes, stage a verified export TSV under Blue and use `slurm/build-bars.slurm`
with `GQH_KDB_INPUT_TSV` and `GQH_KDB_OUTPUT_DIR`. Build destinations must be new/empty paths;
never rebuild in place. Keep the export manifest beside the HDB. The matching validator must pass
before the HDB is published read-only to teammates.

Example once the export TSV and manifest have been transferred to Blue:

```sh
export GQH_KDB_INPUT_TSV="$HPG_BLUE_DIR/gqh-kdb/staging/massive-bars.tsv"
export GQH_KDB_OUTPUT_DIR="$HPG_BLUE_DIR/gqh-kdb/hdb/massive-bars-v001"
sbatch "$GQH_REPO_ROOT/hpc/kdb-timeseries/slurm/build-bars.slurm"
```

The build verifies input body hash and row count before claiming the version directory. If q
fails, its partial output is retained and no success receipt is written; investigate it and choose
a fresh version for retry. A receipt means the loader exited successfully, not that restore or
source reconciliation passed. The wrapper never overwrites an existing version or receipt.

The current batch export command is:

```sh
python3 hpc/kdb-timeseries/scripts/export_tiger_bars.py \
  --batch massive_bars=bec91f7c380937d3d647ade8214968c13abd4bde032c9a7cf7741f0ee58306cd \
  --output /local/private/staging/massive-bars.tsv
```

This reads TigerData read-only, checks the selected batch against its shared ingestion manifest,
and writes a private TSV plus `.manifest.json`. Transfer both files to the HPG team Blue directory
using the institution-approved transfer method. Do not place the export under Git. To start an
interactive q reader after a validated build, load the HDB directory with the approved q binary;
for example, `"$Q_BIN" "$GQH_KDB_OUTPUT_DIR/"`, then query `bars` by date/symbol. The read path is
shared-filesystem based; no unauthenticated q TCP service is opened by this prototype.

## Data integrity contract

- Primary row identity: `(date, sym, source_id, batch_sha256)`; revisions remain separate.
- Session date is derived from the source UTC bar timestamp, not local machine timezone.
- Prices are signed 64-bit integer units of `1e-8 USD`; volume is signed 64-bit integer shares.
- A source batch is never mixed with a canary or a different retrieval vintage.
- Compare count by date/symbol, date range, duplicate key count, nulls, source row hashes and
  canonical output SHA-256 before publication.
- q floats may be used for statistical operations, but exact inputs and accounting quantities
  remain scaled integers until an explicitly tested conversion boundary.
- Data correction means rebuilding a new HDB version, validating it, then atomically changing a
  `current` pointer; it does not silently rewrite published partitions.

## Current implementation status

The repository scaffold, exporter, q scripts, unit tests and Slurm templates are present. Actual
HiPerGator installation and q runtime validation are pending: this workstation currently does not
have a trusted HPG host-key entry/verified SSH session or an approved q executable available in
PATH. Do not bypass SSH host-key verification to force remote access.
