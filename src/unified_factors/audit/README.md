# Snowflake factor-readiness audit

Read-only warehouse inspection on 2026-10-03, approximately 16:36–16:45 America/New_York.
These are coverage/quality queries, not a strategy backtest. No return values, model performance,
sealed outcome labels, filing text or credentials are exported by the queries. Query results stayed in
project Actions artifacts and local scratch storage; only aggregate findings and reproducible SQL ship.
The database was actively ingesting: separate query results are not a single immutable snapshot.

## Access and reproduction

The existing main-branch workflow `.github/workflows/snowflake-query.yml` supplies Snowflake credentials
from repository secrets and uploads the CSV result. No new Snowflake, TigerData or vendor key was needed.
Run one SQL file per workflow dispatch, on main, with a unique artifact name and limit_rows=500. Download
only the resulting audit artifact. SQL files contain SELECT/CTE queries only. No new workflow or grants
were created. Retain workflow ID, query text, export time and result hash for each future audit.

| Query | Successful workflow run |
|---|---|
| Information-schema table/column inventory | 37152146254 |
| batches.sql | 37152316556 |
| detail.sql | 37152237221 |
| acquisition.sql | 37152359527 |
| market.sql | 37152420883 |
| coverage.sql | 37152549832 |

The first batch query failed because ROWS was used as an unquoted reserved alias. The retained query
uses N_ROWS and succeeded. No data mutation occurred. Some concurrent workflow runs belong to other
researchers and were not treated as evidence for this audit.

## Confirmed warehouse state

- Three visible data schemas: RAW, NORMALIZED and FEATURES. Fifteen RAW tables.
- RAW.SOURCE_RECORDS: 151,198 rows, 21 source IDs, 22 batches. No invalid JSON, repeated row indices
  or repeated row hashes within the inspected batches. This is not proof of economic-key uniqueness.
- RAW.RESEARCH_ACQUISITION_ROWS: 433,781 records across eight runs. Each run's count reconciles to
  its manifest; row indices and hashes are unique within run.
- RAW.EQUITY_BARS and RAW.FILINGS_8K are empty. Their names do not describe where populated data lives.
- FEATURES.POINT_IN_TIME_PANEL is empty. NORMALIZED.AWS_GPU_SPOT_DAILY is a view, not another raw archive.
- No dedicated FF3/FF5/momentum, daily risk-free return, sector-price or credit-spread dataset was found
  in the visible tables/source IDs/acquisition runs. This is a scoped inventory, not proof that no such
  source exists in a different database, account or uninspected embedded payload.

## Equity and macro: usable raw material, not a finished factor panel

The full adjusted and unadjusted equity batches each contain 13,515 bars: exactly 2,703 unique timestamps
for each of PWR, ETN, EME, DLR and SPY, from 2016-01-04 through 2026-10-02. Basic positive-price, OHLC
ordering and nonnegative-volume checks found zero invalid rows. Exchange-calendar completeness and
corporate-action reconciliation were not proved by these aggregate tests.

Pin adjusted batch bec91f7c380937d3d647ade8214968c13abd4bde032c9a7cf7741f0ee58306cd or unadjusted batch
17c538dd38a3ff939e78ee074934637efca91518db02048410ed088be603ff6c explicitly. A separate 20-row PWR canary
overlaps the full panel; never concatenate every batch. There are also 204 dividend rows, five split
coverage receipts (not five actual splits), five ticker-event receipts and ten metadata snapshots.

Bar timestamps are 04:00/05:00 UTC daily bucket markers, not the time the completed daily bar became
available. Convert with an exchange-session calendar and declare end-of-session/availability logic.
Verify adjusted-price conventions and dividends before calling close-to-close changes total returns.

Macro field-specific numeric coverage differs from outer table ranges:

| Field | Numeric observations | First / last valid |
|---|---:|---|
| DGS10 | 16,173 | 1962-01-02 / 2026-10-01 |
| DGS2 | 12,581 | 1976-06-01 / 2026-10-01 |
| VIXCLS | 9,286 | 1990-01-02 / 2026-10-01 |
| NASDAQCOM | 14,033 | 1971-02-05 / 2026-10-02 |
| FEDFUNDS | 867 | 1954-07-01 / 2026-09-01 |
| IPG3344S | 656 | 1972-01-01 / 2026-08-01 |

DGS2/DGS10 are yields, not bond returns or the daily risk-free return. FEDFUNDS is not directly a daily
cash-return series. VIX levels and Nasdaq levels need economically declared transformations. M3 orders,
shipments and backlogs span 1992–2026; Census construction spans 2014–2026; GSCPI and Philadelphia Fed
series exist. Their observation histories do not establish historical publication/revision availability.
Philadelphia Fed text dates must be parsed; lexical MIN/MAX gives the meaningless Apr-00 / Sep-99 range.

## Availability and provenance gaps

150,422 of 151,198 SOURCE_RECORDS rows have empty AVAILABLE_AT_TEXT. The 776 SEC register rows are the
exception. All 433,781 acquisition records have missing available_at_utc. This does not mean their data
are worthless: raw prices and source timestamps can support normalization, but do not invent historical
availability or label these complete point-in-time inputs.

Only six of the 22 SOURCE_RECORDS batches match a warehouse INGESTION_MANIFESTS entry: the six extended
Massive price/action/metadata batches. Those six declared counts reconcile. Other rows retain source URLs
and hashes, but lack a matching entry in this specific manifest table; provenance may exist elsewhere.

EIA's loader computes AVAILABLE_AT as the vintage month's last calendar day. That is a convention, not
verified release timing. It does not prove the original workbook was public then. Retain the vintage but
use supported publication evidence or a justified later bound for any historical decision-time feature.

## Physical, compute and filing archives

EIA860M: 128 distinct monthly file manifests, 2016-01 through 2026-08, declaring 3,387,221 generator rows,
matching the table inventory count. Plant/generator/owner fields allow candidate joins, not automatic
contractual exposure. Generator supply queues are distinct from data-center load connections.

AWS: 1,592,024 quotes, 62 instance types, ten zones, 2022-05-31 through 2026-09-30. Quote keys are unique
and prices pass positive/non-null checks. March–June 2026 is a declared missing interval. These are listed
instance-hour prices, not executed compute-futures returns; hardware/product/region composition matters.

SEC: the original register has 776 rows. The archive remains in progress. At one detailed read, PWR had
68 package accessions, ETN 72, EME 60 and DLR 160 distinct accessions (161 manifest rows). Package histories
ended around February/March 2021, despite a later register horizon. DLR document rows included duplicate
accession/document-name keys and counts differed from declared package counts. Do not assert completeness
until reconciliation succeeds on a quiescent snapshot; transient partial loads can explain some differences.

The larger all-market disclosures batch lives in RESEARCH_ACQUISITION_ROWS: 56,843 records. The original
SOURCE_RECORDS massive_8k batch still has 201. The reported 2,530-row expansion in another store must not
be silently treated as a Snowflake SOURCE_RECORDS batch. Different storage layers and acquisition runs
must be explicitly mapped and deduplicated by accession/category before use.

## New acquisition datasets uncovered

| Dataset | Records | What is actually loaded |
|---|---:|---|
| filings-all-2022-dev-v1 | 56,843 | Vendor disclosure records, not original SEC documents or reviewed event labels |
| ercot-gis-v1 | 100 | Workbook listing metadata |
| ercot-projects-v1 | 109,640 | Parsed queue project rows; publication and project-split links unresolved |
| queues-annual-v1 | 174,810 | National queue snapshot rows; not monthly project history |
| options-spy-20220901-v1 | 5,258 | 566 contracts, 566 coverage receipts, 2,994 daily bars and 566 quotes and 566 quote-coverage receipts |
| hyperliquid-tape-pilot-v1 | 86,760 | 79,626 account-fill records and 7,134 L2 snapshots; incomplete pilot, third-party equivalence unverified |
| hyperliquid-mirror-pilot-v1 | 2 | Parquet metadata records, not two full trading-history observations |
| ornn-public-v1 | 368 | Public daily index observations; not automatically tradable futures settlements |

Account fills require trade identity/side accounting before conversion to a market trade tape. L2 snapshots
cannot reconstruct queue position or every intervening order. A dense short sample is not evidence of
regime coverage. Option quotes contain explicit stale/missing/nonpositive flags. Review timestamps, quote
age, spreads, contract multipliers and underlying alignment before Greeks or surface calibration.

## Ordered integration plan

1. Freeze source/batch IDs and derive a calendar-aligned daily equity panel with reconciled distributions
   and corporate actions. Keep raw price snapshots and derived return conventions separate.
2. Acquire/version the published standard factor series (including daily RF) and momentum. No evidence
   here establishes they are already loaded. Use separate SMB definitions for exact FF3/FF5 replication.
3. Add sector benchmarks and explicit rate/credit/energy transformations; the five-ticker basket alone
   cannot support a global cross-sectional model. Broader universes also require historical membership.
4. Choose the authorized development interval through the strategy owner. Normalize and test adapters
   before fitting; this audit did not open a sealed return holdout or tune a model.
5. Reconcile SEC packages and historical release clocks, then reviewed contract/project links. Use
   economic surprises and pre-event exposures only after first-public and prior-expectation checks.
6. Keep Ornn, options and Hyperliquid pilots in separate feasibility tracks until history length,
   executable instruments and source-specific QA justify integration. No paid API purchase is yet required.

**Access conclusion:** Snowflake is reachable now through the established API/workflow path. No new keys
are needed for the next normalization step. TigerData was not directly queried by this audit, so cross-store
parity is not claimed. If needed, a bounded read-only TigerData query route or a user's read-only connection
would let us reconcile the reported cross-store differences without another ingestion run.

## Final coverage receipt: why row counts are not enough

Workflow 37152549832 established these additional bounds:

- Ornn: four GPU types (A100 SXM4, H100 SXM, H200, B200), 92 observations each, July 3–October 2,
  2026. This is about three months, not 368 days or years of futures-settlement history.
- Hyperliquid account fills: July 29, 2025, 17:00:00.663–17:59:59.037 UTC, about one hour.
  L2 snapshots: December 7, 2025, 04:57:11.953–05:30:46.006 UTC, about 34 minutes. The samples
  do not overlap. They cannot validate joint trade/book execution, queue fills or book-response models.
  Fill block clocks were decoded as nanoseconds; L2 server clocks as milliseconds and timestamps as
  nanoseconds. Exchange-versus-receipt latency and full event continuity remain unverified.
- The 56,843-disclosure acquisition spans January 3–September 30, 2022. It is a broad cross-section
  over nine months, not a continuous all-market history through 2026.
- Options: the declared as-of date is September 1, 2022. Of 566 last regular-session quote records,
  112 carry stale-at-close flags and 109 carry missing/nonpositive quote flags; the groups may overlap.
  Daily-bar records are not a continuous historical options surface or verified executable prices.
- ERCOT project report months span December 2018–September 2026. Annual national-queue snapshot
  labels span 2020–2025. These date bounds do not establish complete monthly files or verified releases.
- The later SEC reconciliation found 366 distinct manifest accessions and 366 document accessions,
  one duplicated manifest accession, one accession with duplicate document names, and one count
  mismatch. No manifest-only or document-only accession was found at that query snapshot. The growth
  since earlier queries confirms active ingestion. Recheck after completion before deduplicating.

### Immediate next deliverable

A deterministic daily equity/standard-factor adapter, with a manifest that pins batches, checks the exchange
calendar, computes validated total/excess returns, assigns supported bar availability, and keeps the authorized
development interval separate. Fetch published daily standard factors/RF/momentum and sector benchmarks
before running the full baseline grid. Macro vintage repairs and company/contract links are separate work;
we should not delay the basic return-risk panel while pretending those harder layers are solved.

No new API credentials are requested now. The verified workflow supplies Snowflake access; the existing
Massive ingestion workflow can obtain additional permitted market series, and standard factor files are
public. This audit did not launch additional ingestion, mutate warehouse tables, repair another owner's
loaders or train on historical returns. Those are the next implementation steps, not completed audit work.
