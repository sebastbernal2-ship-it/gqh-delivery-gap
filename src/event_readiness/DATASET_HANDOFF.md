# Candidate data acquisition and teammate handoff

Owner: aidanq06. Acquisition date: 2026-10-03. These are source and normalization releases,
not strategy results. Start here for the requested options, queue, venue, compute and broader
filing datasets. The earlier [inventory](LIVE_INVENTORY_2026-10-03.md) describes existing shared
tables; this acquisition adds separate tables and leaves those inputs unchanged.

## What this delivers

| Request | Obtained | What remains |
|---|---|---|
| Historical option chains | Complete returned SPY contract cross-section as of 2022-09-01 for expiration 2022-09-16: 566 contracts, 566 last regular-session quotes and 2,994 daily bars through expiration. Original responses and explicit coverage rows retained. | One date and one expiration, not a longitudinal chain panel. Historical open interest, a defensible signed dealer-position proxy, and subsequent full-chain sampling remain necessary for dealer-hedging research. |
| Interconnection history | Six LBNL annual snapshots, 2020–2025, with 174,810 project observations. ERCOT: 100 GIS workbooks covering 94 consecutive report months, 2018-12–2026-09, including six additional versions. The Project Details sheets yield 109,640 observations across 3,348 distinct INR identifiers. | Earlier years, other operators at monthly frequency, original publication/version verification, project splits and an EIA/project/company crosswalk. This is generation interconnection, not a datacenter load-service queue. |
| Hyperliquid order books and liquidation prints | Two public mirror Parquet files downloaded, revision-pinned and matched to publisher SHA-256: 46,171 fill-block rows containing 368,336 account fills, and 786,064 L2 rows. Selected output: 79,626 account fills plus 7,134 BTC/ETH book snapshots; 60 fill records carry explicit liquidation markers. | A synchronized, sufficiently long book/fill window, deduplication, gaps, timestamp semantics and venue-equivalence validation. This is a bounded pilot, not a full archive backfill. AWS is unnecessary for this mirror route. |
| Executed compute rental series | Ornn public benchmark: 92 daily observations for each of H100 SXM, H200, B200 and A100 SXM4; 368 rows spanning source timestamps 2026-07-03–2026-10-02. | Individual executions, volumes, contract terms, contemporaneous availability and a holdable instrument or physical counterparty. An index derived from transactions does not supply those. |
| Wider 8-K coverage | 56,843 disclosure records, covering 34,471 distinct accessions and 6,614 distinct CIKs in the requested Jan–Sep 2022 development partition. Actual returned filing dates: 2022-01-03–2022-09-30. | These are classified disclosures and supporting excerpts, not 34,471 complete source documents. Retain original filings/exhibits and reconstruct first-public timestamps before treating them as historical signals. |

The [machine-readable release receipt](acquisition_release_2026-10-03.json) pins warehouse run identifiers,
record hashes, source receipt counts and the tested implementation hashes. Local `published.json`
receipts are the detailed evidence of archive download-back verification and full ordered row
reconciliation. A completion manifest certifies that storage matches the retained acquisition;
it does not certify historical signal availability, economic identification or executable returns.

## Research universe for this acquisition

The [systematic track](https://www.gqhacks.com/tracks/systematic-trading) allows liquid publicly
traded markets and lists equities, ETFs, futures, FX, options and crypto. The published page and
its linked application asset were retrieved directly from the official site. The competition is
not restricted to equities. Sponsor bonus conditions are separate from the main track.

Our working data scope is **U.S. listed equities/ETFs/options and BTC/ETH perpetuals**. Actual
options acquisition here is only SPY; no implied claim of coverage for the whole scope. Futures
and FX remain eligible under the general rules but have no acquisition mandate without a named
mechanism. Physical compute remains a distinct instrument-access problem. This scope is a
data-work decision, not a promoted trading thesis or authorization to trade on any venue.

## Snowflake interface

All new objects are in `VECTOR_RESEARCH.RAW`:

| Object | Meaning |
|---|---|
| `RESEARCH_ACQUISITION_RUNS` | One completed, verified manifest per immutable source bundle. Includes dataset name, full run ID, normalized file hash, row count and stage prefix. |
| `RESEARCH_ACQUISITION_ROWS` | Canonical JSON payloads, zero-based row index and SHA-256 per row, bound to a run ID. |
| `RESEARCH_ACQUISITION_STAGE` | Content-addressed ZIP archives containing original source objects, receipts, normalization output and manifests; plus compressed transport files. |

The existing `SOURCE_RECORDS`, old SEC archive, feature tables and TigerData are unchanged.
No strategy-ready view is created. Do not use an unpinned `latest` run in research.
The latest [other-computer access inventory](../../docs/plan/data-access.md) says that computer
currently reads only TigerData. It must configure a private Snowflake connection or receive an
approved bounded export before these new rows are accessible there. No bulk TigerData replication
was attempted under the inherited storage-headroom constraint.

Find the release, then copy its **full run ID** from the receipt into a session variable:

```sql
SELECT DATASET_NAME, RUN_ID, ROW_COUNT, RECORDS_SHA256, STAGE_PREFIX, VERIFIED_AT
FROM VECTOR_RESEARCH.RAW.RESEARCH_ACQUISITION_RUNS
ORDER BY DATASET_NAME, VERIFIED_AT;

-- Bind the exact run from the release receipt, not a date-selected latest version.
SET chosen_run = '<full run ID from the release receipt>';
SELECT ROW_INDEX, ROW_SHA256, PARSE_JSON(PAYLOAD_JSON) AS RECORD
FROM VECTOR_RESEARCH.RAW.RESEARCH_ACQUISITION_ROWS
WHERE RUN_ID = $chosen_run
ORDER BY ROW_INDEX;
```

Example queue extraction, usable for source review and crosswalk work:

```sql
WITH selected AS (
  SELECT PARSE_JSON(PAYLOAD_JSON) AS P
  FROM VECTOR_RESEARCH.RAW.RESEARCH_ACQUISITION_ROWS
  WHERE RUN_ID = $chosen_run
)
SELECT P:normalized:operator::VARCHAR AS OPERATOR,
       P:normalized:project_id::VARCHAR AS PROJECT_ID,
       P:context:report_month::VARCHAR AS REPORT_MONTH,
       P:context:snapshot_as_of::VARCHAR AS ANNUAL_SNAPSHOT_AS_OF,
       P:reported_posted_at_utc::TIMESTAMP_TZ AS REPORTED_POSTED_AT,
       P:available_at_utc::TIMESTAMP_TZ AS VERIFIED_AVAILABLE_AT,
       P:normalized:proposed_service_date::DATE AS PROPOSED_SERVICE_DATE,
       P:normalized:submission_date::DATE AS SUBMISSION_DATE,
       P:source_sha256::VARCHAR AS SOURCE_SHA256,
       P:quality_flags AS QUALITY_FLAGS
FROM selected;
```

For original workbooks, select the `ercot-gis-v1` inventory: each record contains `DocID`,
`FriendlyName`, `PublishDate`, the original download URL, source hash and listing hash. Download
the pinned run's ZIP from its `STAGE_PREFIX`, verify its SHA-256 against `BUNDLE_SHA256`, and
open `objects/<source_sha256>` as an XLSX file. The normalized ERCOT run retains those same
workbooks, including sheets not flattened into project rows. Do not export proprietary Massive
content into this public Git repository. Teammate access depends on their existing Snowflake
role; this work does not assign users or grant new account privileges.

## Clocks, identities and quality limits

Every row includes a record type, context, source URL/hash, retrieval clock, raw data and an
explicit `available_at_utc: null` unless historical availability has separately been verified.
Retrieval time is not publication time. A report month is not a release date. These sources
cannot enter historical model features simply because they have dates.

**Options.** Contracts were selected using historical `as_of` and `expired=false`, meaning active
at that historical date. The corresponding `expired=true` probe returned zero and is not evidence
of missing entitlement. This release has all strikes returned for one expiration, both calls and
puts. It is not every expiration. Of 566 contracts, 414 returned eligible-trade daily bars and 152
returned none. Empty results are explicit coverage records, not invented zero prices. Among the
last-session quotes, 112 were over five minutes old at 16:00 ET and 109 had missing/nonpositive
sides; these counts can overlap. Quotes with flags need an explicit exclusion/staleness policy.
The selected cutoff is 16:00 ET, not a claim that SPY options stop trading then. Bars after the
as-of date are labeled outcomes and must not enter that day's features. OI is explicitly absent.
OI alone would still not identify dealers' signed inventories or prove their hedging flow.

**LBNL.** Original annual workbooks are retained, including their different schemas. The 2020
active, withdrawn and completed sheets are read separately; later editions use their full data
sheet. Fully blank rows are excluded. Dates represented as dates or full date strings are parsed;
unformatted numbers are decoded using the workbook's Excel epoch only when the companion year
matches, and that conversion is flagged. Other ambiguous numbers and year-only values remain
unparsed. Raw cells survive every conversion. Source status/fuel vocabularies are not silently
merged. Geographic values include non-state tokens, so a distinct-token count is not a U.S.
state count. Candidate keys `operator:project_id` can repeat or be missing; duplicates remain
in the release. Publication dates for these downloaded versions are not verified. The HTTP
Last-Modified clock can reflect a website migration and must not become a historical feature date.

**ERCOT.** Both large- and small-generator Project Details layouts are supported. Only these
sheets are flattened; inactive, cancellation and commissioning sheets remain available in the
original workbooks for further extraction. Project rows carry workbook ID, sheet and row number.
There are no duplicate INR identifiers within a workbook's individual detail sheet in this release.
109,637 rows have a parsed proposed COD. The source's 1900 missing-date marker is null, not a
real milestone. Capacity may legitimately be negative for net repowering changes and is retained.
Screening/FIS dates are kept under their own names, not relabeled as submission dates.

The listing provides reported posting clocks, but some old files were reposted together in 2020.
Revisions remain separate, including multiple files for a single report month. Original-publication
verification and a declared conservative vintage-selection policy are still required. Published
notes describe omissions for confidentiality, exclusion of inactive projects from detail sheets,
and project splits whose new IDs may not inherit prior milestones. Do not interpret disappearance
as withdrawal or a blank milestone as proof that it never occurred.

**8-K disclosures.** Pagination covers the requested provider partition without a ticker filter;
exact duplicate rows are suppressed, while distinct classifications/excerpts for an accession are
retained. Provider coverage is not demonstrated to equal every SEC issuer/filing. Today's tags
are retrospective annotations. They do not prove that the same classifications existed in 2022.
The primary next use is identifying candidate disclosures and source documents for reviewed
expectation-versus-revision pairs. A filing's occurrence date and its first-public time differ.

**Hyperliquid.** The source fill partition covers 2025-07-29 17:00 UTC approximately; its first
block timestamp is just before the hour. The book partition covers 2025-12-07 04:57–05:30 UTC.
They do not overlap. The selection was made for bounded access/schema verification before reading
returns: the smallest of the first 30 dated fill partitions and the first listed L2 partition.
It cannot estimate forced-flow economics jointly. The full Parquet sources remain accessible in
the stage. Normalized output selects BTC/ETH account fills, every explicit liquidation marker
across all coins in that fill file, and BTC/ETH book rows. Sixty marked account-side records are
not asserted to be sixty distinct economic liquidations. Both sides of trades may appear among
account fills, so summing them can double-count market volume.
Of the sixty marked records, 42 name PENGU, 16 XRP, two ETH and none BTC. That is inadequate
evidence for the BTC/ETH forced-flow strategy; a larger predeclared sample is required.

Book fields contain up to 20 price/size levels per side. Arrow timestamps remain exact integer
nanoseconds, without conversion through floating-point seconds or microsecond datetimes. The
normalizer flags nonfinite fields and locked/crossed top quotes; original Parquet bytes are
retained. Snapshot data does not establish order queue priority or an HFT fill model. These are
third-party datasets without a verified original venue-byte comparison or complete provenance
card; acquisition proves access and integrity against the publisher hash, not full tape fidelity.
The team's newer [mirror correction](../../docs/plan/pull-capability.md) supersedes the earlier AWS
credential request. No new AWS account, API key or requester-pays download was used.

**Ornn.** Vendor documentation describes a transaction-derived benchmark. The public endpoint
returns index values and source timestamps, not executed contract records, sizes or tradable
bid/ask histories. No commercial plan has been purchased and no vendor message sent. This does
not reopen the closed compute-equity thesis or manufacture a compute-futures backtest.

No strategy outcomes were tested in this acquisition. Prior opened holdouts remain spent under
the [sealed-test record](../../docs/plan/sealed-test-record.md). Raw acquisition of later queue
snapshots is not permission to call a reused window fresh out-of-sample evidence.

## Reproduce and extend

Install optional dependencies from [acquisition-requirements.txt](acquisition-requirements.txt).
Commands run from the repository root with Python 3.11+, tested here with Python 3.12. Supply
private credentials through the process environment; the existing `load_local_env()` helper in
`src/central_ingest/sync.py` can load the ignored local configuration without shell evaluation.
Never place credential values in commands, receipts or Git.

```sh
python -m pip install -r src/event_readiness/acquisition-requirements.txt
PYTHONPATH=src python -m unittest event_readiness.test_acquisition -v
PYTHONPATH=src python -m event_readiness.pull_candidates options \
  --ticker SPY --as-of 2022-09-01 --expiry 2022-09-16 --out data/acquisition/options
PYTHONPATH=src python -m event_readiness.pull_candidates filings \
  --start 2022-01-01 --end 2022-09-30 --out data/acquisition/filings
PYTHONPATH=src python -m event_readiness.public_candidates queues --out data/acquisition/queues
PYTHONPATH=src python -m event_readiness.public_candidates ornn --out data/acquisition/ornn
PYTHONPATH=src python -m event_readiness.public_candidates ercot --out data/acquisition/ercot
PYTHONPATH=src python -m event_readiness.ercot_data data/acquisition/ercot data/acquisition/ercot-projects
PYTHONPATH=src python -m event_readiness.mirror_candidates \
  src/event_readiness/hyperliquid_pilot_plan.json data/acquisition/mirror
PYTHONPATH=src python -m event_readiness.mirror_data data/acquisition/mirror data/acquisition/tape
PYTHONPATH=src python -m event_readiness.warehouse_candidates data/acquisition/options
# Explicit additive warehouse write, after local preparation passes:
PYTHONPATH=src python -m event_readiness.warehouse_candidates data/acquisition/options --publish
```

New requests observe the provider's current version; use retained source objects to reproduce this
specific release. Completed acquisition directories refuse replacement. Interrupted requests resume
from hash-verified receipts; use a new output directory when changing scope or recording revisions.
Do not run concurrent writers for the same dataset or Snowflake release. Primary-key uniqueness
is checked by the loader but is not enforced by Snowflake standard-table constraints.

The loader validates all source bytes, provenance links, normalized counts and SHA-256 values
before writing. It uploads a content-addressed archive, downloads it back and checks its hash,
copies rows into a temporary table, checks every row and the ordered whole-file hash, and commits
data plus the completion manifest in one transaction. An identical retry verifies the existing
batch without appending rows. Failed preparation or reconciliation produces no completed run.
Interrupted transfers may leave unmanifested stage objects; these are not accepted datasets.

Validation: 64 scoped tests pass (47 existing readiness tests plus 17 acquisition tests), including
corrupted-source rejection, missing provenance, nanosecond preservation, duplicate/missing warehouse
rows, date-encoding ambiguity and deterministic local packaging. The live Ornn retry verified
idempotency. The first Snowflake canary exposed a missing trailing slash in COPY's stage prefix;
that was fixed before publishing any rows, then source download-back and full row reconciliation
passed. The repository-wide `make check` still fails on pre-existing structure issues: `.vscode`
is unrecognized, and `src/factors/` and `src/models/` lack READMEs. The separate path checker also
reports existing strategy-builder references to ungenerated result files. Those owned paths were
not changed. The credential scan and scoped tests pass; the full repository gate is not green.

## Remaining access requests

1. **Options:** obtain licensed historical OI at contract/day resolution for the declared universe,
   with its publication convention. [Cboe Option EOD Summary](https://datashop.cboe.com/option-eod-summary)
   documents historical OI; [open/close data](https://datashop.cboe.com/cboe-options-open-close-volume-summary)
   is a separate possible input for participant-flow research. Neither entitlement is established here.
   First expand the mechanism specification and contract/day coverage plan, rather than treating
   one expiry as sufficient to test dealer hedging.
2. **Queues:** the [existing request](../../docs/inbox/data-request-queue-2026-10-03.md) is partially
   satisfied by this landing. Its remaining core asks are earlier monthly/quarterly vintages, other
   operators, exact original publication evidence and stable linkage across projects and splits.
3. **Hyperliquid:** use the public
   [fill mirror](https://huggingface.co/datasets/gionuibk/hyperliquid-node-fills-by-block) and
   [book collection](https://huggingface.co/datasets/gionuibk/hyperliquidL2Book-v2). The committed
   pilot plan pins exact repository revisions, paths, sizes and publisher hashes. Expand by
   a declared common date window after inspecting timestamps and validating schemas; filenames
   alone are not sufficient. The official AWS archive remains a separate requester-pays route,
   but its anonymous 403 is not a blocker for these public files. No paid account is needed to
   reproduce the mirror pilot. Do not assume every file in the large collection is an L2 book;
   it also contains catalog inventories, trades and other record families.
4. **Compute:** request executed rental records or a physical counterparty, including GPU model,
   region, contract duration/start, quantity, delivered unit, realized price, settlement terms,
   cancellation/default status and timestamped original versions. Confirm team/cloud-storage
   rights before accepting commercial data. [Ornn access tiers](https://data.ornn.com/docs/access-tiers)
   and [methodology](https://data.ornn.com/methodology) distinguish its benchmark offering from the
   executed series the strategy actually needs. More index history alone does not fix the instrument gate.

Source catalogs: [LBNL Queued Up](https://emp.lbl.gov/queues),
[ERCOT GIS Report](https://www.ercot.com/mp/data-products/data-product-details?id=PG7-200-ER),
[Massive options documentation](https://massive.com/docs/rest/options). Exact download URLs,
source hashes and request timestamps reside in each retained bundle rather than in this narrative.
