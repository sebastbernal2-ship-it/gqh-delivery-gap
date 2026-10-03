# Authenticated inventory: 2026-10-03

Owner: aidanq06. This receipt supersedes the access uncertainty in
[DATA_ACQUISITION.md](DATA_ACQUISITION.md). The user supplied private connection configuration
and selected this computer as the ingestion host. Authentication succeeded for Snowflake,
TigerData and Massive. Credentials were saved only in the ignored local configuration with
owner-only permissions. No credential values, database hostnames, account identifiers or raw
licensed observations belong in this document or Git.

All warehouse work was SELECT/LIST only. No table, grant, role, row, stage object or warehouse
configuration was changed. Eight small Massive requests checked access and returned data into
process memory; private receipts retain status/counts, not price values or filing text. No bulk
backfill, source repair, return calculation, model fit or strategy test ran.

Main was refreshed through `5874082` before this receipt was committed. Its
[working intent](../../docs/plan/intent.md) and [missing-edge assessment](../../docs/plan/what-is-missing.md)
still govern candidate selection. In particular, the latest decision closes the compute-equity
relative-value candidate on instrument concentration. Verifying AWS or equity data access does
not reopen that candidate or establish a forced payer. This is a data-readiness receipt only.

## What the live warehouse establishes

The first snapshot began at 19:00:51 UTC. Inventory queries were sequential, not a transactional
snapshot across both services; these are point-in-time observations, not a continuous parity guarantee.

| Object | Observation | Interpretation |
|---|---|---|
| Snowflake `RAW.SOURCE_RECORDS` | 151,198 rows across 22 source/batch pairs | Includes a separate 20-row PWR canary; do not concatenate it into the full price batch. |
| Adjusted and unadjusted full Massive bar batches | 13,515 rows each; PWR, ETN, EME, DLR and SPY each have 2,703 rows, 2016-01-04 through 2026-10-02 | XLI/XLRE are absent from these batches. Equal counts do not prove calendar completeness or correct total returns. |
| Massive dividends | 204 rows | Actions exist; their alignment, share basis and return construction still need validation. |
| Massive disclosures | 201 rows | Tagged disclosures, not 201 verified complete original filing packages. The generic availability field is empty. |
| Massive split/ticker-event source batches | Five records each | Treat the reported empty-result receipts separately from actual corporate events. |
| Massive ticker metadata | Ten records | Start/end snapshots for five symbols, not a complete historical security master. |
| `RAW.INGESTION_MANIFESTS` | Six rows for the full bars, raw bars, dividends, splits, ticker events and metadata batches | Six batch counts match. Sixteen other stored source/batch pairs have no matching manifest. This does not establish data loss; the reason is unverified. |
| SEC selected archive | 703 expected accessions; manifests for 252 distinct accessions, represented by 253 package versions; 8,135 document metadata rows; 252 listed stage objects | 451 selected accessions lack manifests. Completeness is not established. One path is referenced by multiple package versions. |
| EIA-860M | 128 manifest rows covering 2016-01 through 2026-08 | Table metadata reports 3,387,221 generator-vintage rows. Original XLSX byte integrity, release clocks and per-month coverage were not checked here. |
| AWS GPU archive | Table metadata reports 1,592,024 rows | Presence only; this check does not validate prices, economic executability or coverage gaps. |
| `FEATURES.POINT_IN_TIME_PANEL` | Exact `COUNT(*) = 0` | No populated point-in-time panel in this table. |
| `RAW.EQUITY_BARS`, `RAW.FILINGS_8K` | Exact `COUNT(*) = 0` in both | The existing bars and tags live in generic `SOURCE_RECORDS`; teammates could otherwise query an empty placeholder and conclude the data is missing. |
| TigerData | Same 22 source/batch/count triples; database size 786,011,839 bytes, approximately 749.6 MiB | Counts agree, but TigerData payload hashes were not checked. Keep writes deferred under the inherited capacity constraint; current contracted quota was not independently verified. |

The entire generic Snowflake source table passed a server-side JSON/row-hash check: zero JSON
parse failures and zero stored-payload SHA-256 mismatches across all 151,198 rows. Unique
`ROW_INDEX` counts also matched row counts within each batch. This proves internal consistency
with the recorded row hashes, **not provider correctness, completeness, original-response byte
retention, historical availability, numeric validity or economic relevance**. Batch digests were
not independently reconstructed and original provider responses were not available for comparison.

The archive metadata reconciler reports 451 `missing_accession` issues and one
`mutable_stage_path_multiple_versions` issue. No package bytes were downloaded, so zero accessions
are byte-verified by this check. The reused path does not by itself prove which version's bytes
are present. Whether the original computer's archive job is still running is also unknown.

The source inventory's min/max values are raw text. In particular, the Philadelphia survey's
`Apr-00` / `Sep-99` lexical extrema do not describe chronological coverage. Normalize dates before
presenting any cross-source date matrix. All Massive generic `AVAILABLE_AT_TEXT` fields are empty;
derive defensible decision clocks from the source contract, not from bar-window start or download time.

## Massive access actually tested

All eight requests returned HTTP 200, provider status `OK` and nonempty results:

| Check | Requested sample | Returned rows |
|---|---|---|
| Unadjusted daily prices | PWR, 2020-01-06 to 2020-01-07 | 2 |
| Dated ticker metadata | PWR, as of 2020-01-06 | 1 object |
| Dividend history | PWR, calendar 2020, limit one | 1, additional page advertised |
| 8-K disclosure tags | PWR, January–September 2022, limit one | 1, additional page advertised |
| Older unadjusted prices | PWR, 2006-01-03 to 2006-01-04 | 2 |
| Industrial control prices | XLI, 2020-01-06 to 2020-01-07 | 2 |
| Real-estate control prices | XLRE, 2020-01-06 to 2020-01-07 | 2 |
| Separate parsed 8-K text endpoint | PWR, January–September 2022, limit one | 1 |

The 2006 sample is evidence that this key can retrieve some prices older than the currently loaded
2016 start. It does not certify complete twenty-year coverage, every symbol, every endpoint or
historical filing-product availability. Successful access to XLI/XLRE makes the missing control
backfill feasible in principle. These probes do not bypass the acquisition validation work.
The provider's current disclosures/text also do not prove its classification existed in 2022.

## Concrete next work

1. Use Snowflake as the primary store. Do not repeat the already present full-batch downloads.
2. Reconcile the 16 missing manifests against original private run receipts. If reconstructing a
   receipt today, label it as reconstructed and leave unknown original retrieval times unknown.
   Never invent provenance merely to make a completeness check pass.
3. Repair the client validation and SEC archive-version path issues in coordination with the
   ingestion owner. Check the original archive operator before retrying missing accessions.
4. Verify one small, known-action development example end to end, add XLI/XLRE controls from their
   actual trading histories, then backfill declared missing partitions with immutable run receipts.
5. Populate and release a documented development interface to the teammate: source-linked facts,
   comparable earlier expectations, security/exposure mappings, prices/actions, controls, timing,
   missingness and exclusion reasons. Preserve the published spent-holdout history. Source presence
   and valid JSON alone are insufficient for a strategy-ready release.

## Reproduction and private receipts

The existing [read-only snapshot procedure](README.md#step-a-inventory-before-another-sec-archive-run)
and [inventory SQL](operations.sql) cover source, SEC and EIA metadata. This run additionally grouped
Massive records by source, exact batch and JSON ticker, and compared source/batch/count triples
between stores. Source integrity was checked with:

```sql
SELECT SOURCE_ID, BATCH_SHA256, COUNT(*) AS ROW_COUNT,
       COUNT_IF(ROW_SHA256 IS NULL OR SHA2(PAYLOAD_JSON, 256) <> ROW_SHA256) AS HASH_FAILURES,
       COUNT_IF(TRY_PARSE_JSON(PAYLOAD_JSON) IS NULL) AS JSON_FAILURES
FROM VECTOR_RESEARCH.RAW.SOURCE_RECORDS
GROUP BY SOURCE_ID, BATCH_SHA256;
```

Integrity query ID: `01c77d17-0108-c7f7-0011-64ca0003c026`. Exact empty-table count query ID:
`01c77d17-0108-c7f7-0011-64ca0003c02a`. Query IDs identify receipts, not authorization to access them.

Private local artifacts under ignored `data/readiness/`:

| File | SHA-256 |
|---|---|
| `access-inventory-20261003T190051Z.json` | `16c2ee96384ba55af8191d735e6c3157016f2725004c6f2a5d60adfc3beef77c` |
| `archive-metadata-audit-20261003T190051Z.json` | `979562a646c4aabcf21447e93b65b236b849b08e61f82e9f5d24d33f7c13ceb7` |
| `inventory-integrity-20261003.json` | `9c64c27843704b85275cea5cdc1a88ccbdb85e69c41126989361fb9608d0e62d` |

These files are intentionally not committed. The operational scripts and local Python environment
are private staging aids, not a new production loader. A teammate can rerun the documented queries
using their own account. No test in this receipt certifies or promotes a trading strategy.
