# Live warehouse audit for the information-view prototype

Audited 2026-10-03. These observations describe the accessible `VECTOR_RESEARCH` database at
query time, not every database in the account. No warehouse writes, credential extraction,
permission changes or new cloud allocations were performed.

## Access that actually worked

The GitHub connector returned 404 for workflow artifacts and local `gh` was unauthenticated.
The authenticated browser could dispatch the repository's existing `snowflake-query` workflow
and download its CSV artifacts. Snowflake credentials stayed on the runner. The user explicitly
approved metadata and public-source development exports to these Actions artifacts after the
approval review flagged that the repository is public. A later raw-payload request was blocked;
a narrower BTC book projection was accepted after reviewing the public-mirror acquisition code
and provenance. No account fills, proprietary Massive payloads or full raw manifests were exported.

| Audit | Verified workflow run | Result |
|---|---|---|
| Table inventory | [37152366021](https://github.com/sebastbernal2-ship-it/gqh-delivery-gap/actions/runs/37152366021) | 17 tables/views returned; raw tables populated, point-in-time panel empty |
| Schema and source coverage | [37152578438](https://github.com/sebastbernal2-ship-it/gqh-delivery-gap/actions/runs/37152578438) | 214 column/source metadata records |
| Separate acquisitions | [37152890408](https://github.com/sebastbernal2-ship-it/gqh-delivery-gap/actions/runs/37152890408) | Eight immutable acquisition runs |
| Payload field names only | [37153103530](https://github.com/sebastbernal2-ship-it/gqh-delivery-gap/actions/runs/37153103530) | Workflow succeeded; not used to construct the model inputs |
| Bounded public BTC book export | [37153271030](https://github.com/sebastbernal2-ship-it/gqh-delivery-gap/actions/runs/37153271030) | 3,567 records, safely below the 5,000-row query limit |

The exact bounded export is [snowflake_book_export.sql](snowflake_book_export.sql).
The model receipt records the exported CSV SHA-256, pinned source hash, warehouse run ID and
panel hash. The projected CSV retains upstream row hashes as provenance; the adapter cannot
recompute full raw-record hashes from a projection. It validates its local export hash and
expected source identifier, not original venue-byte equivalence.

## What the live queries establish

- `FEATURES.POINT_IN_TIME_PANEL`: zero rows. `RAW.EQUITY_BARS` and `RAW.FILINGS_8K` are also empty;
  data lives in generic raw landings, so an empty specialized table does not imply no source data.
- `RAW.SOURCE_RECORDS`: 151,198 rows. Of its 21 source IDs, only `sec_filings` has populated
  `AVAILABLE_AT_TEXT` (776/776). Non-null timestamps still require semantic review. Bar start
  clocks, macro observation dates and current retrieval times are not interchangeable with
  historical availability.
- Live `SOURCE_RECORDS` shows 201 `massive_8k` rows in this database. The broader separate
  `filings-all-2022-dev-v1` acquisition has 56,843 records; these counts describe different
  collections. Do not substitute older narrative counts for a query result.
- `RAW.EIA860M_GENERATOR_VINTAGES`: 3,387,221 rows; `RAW.AWS_GPU_SPOT_PRICES`: 1,592,024 rows.
  Large row counts do not establish synchronized labels, publication clocks or independent events.
- Separate acquisitions include ERCOT projects (109,640), annual queues (174,810), Hyperliquid
  tape pilot (86,760), public Ornn benchmark (368), options pilot (5,258), and broader filings.
  Their normalized payloads require individual adapters, not a blanket join on date.

## Why the first real run uses only books

The team's acquisition handoff on `research/handoff-event-readiness`, under
`src/event_readiness/DATASET_HANDOFF.md`, documents public-mirror provenance and the mismatch:
July 2025 account fills versus December 2025 books. Only two marked ETH account-side fills and
no marked BTC liquidations exist in that pilot. Its 86,760 rows cannot honestly become a joint
BTC liquidation/book panel. The public book itself supports a bounded numerical smoke test.

A one-second availability lag is explicitly assumed in the adapter. Neither this lag nor the
third-party archive has been validated for live decision replay. The upstream `server_time`
field exists but its semantics have not been established; it is not silently promoted to a
receive timestamp. The experiment contains no confirmed flow, open-interest change, fills,
transaction costs, queue priority or latency measurement.

## What unlocks a strategy experiment

1. Predeclare several common book/fill dates across market conditions, independently of returns.
2. Acquire both streams for those exact windows; verify clock semantics, duplicates, book gaps,
   liquidation markers and trade-side deduplication. Retain original source objects and hashes.
3. Specify the economically justified decision target, cost/fill model and independent episode
   definition. Register development windows and keep an untouched future evaluation protocol.
4. Feed that validated adapter into the same seven-view API. Add OI/funding or slow strategy context
   only through point-in-time joins with maximum staleness and missingness rules.
5. Use HiPerGator for larger sweeps only after this data gate. The current CPU smoke test does not
   establish remote access, GPU performance, HFT latency, quantum benefit or tradability.

No new credentials are needed for the proven browser/workflow route. Direct automated access can
later use the existing approved GitHub authentication setup or a private Snowflake connection;
credentials should never be copied into this public repository or chat.
