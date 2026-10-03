# Massive → Snowflake: acquisition and teammate readiness

Assessment: 2026-10-03, against the event-readiness continuation and main through `58adc72`.
Owner: aidanq06. The refresh from `8359a29` did not change `src/central_ingest/`.
The user selected this computer as the ingestion host, with private configuration. Its location
and working authentication have not yet been established. No live provider or warehouse check
was performed for this assessment. This document proposes a release contract; it does not claim
the tables, permissions, repairs or dataset release below have been implemented.

## Verdict

We have a useful manual ingestion foundation. We are **not ready for unattended broad acquisition
or a certified strategy dataset handoff**. Proceed with configuration and inventory first, repair
the acquisition checks, prove a small batch, then expand. Raw collection and permission to analyze
held-out outcomes are separate decisions. Existing raw data may support source discovery after
reconciliation, without becoming approved historical trading features.

The refreshed main adds `src/strategy/` contracts and builders. Reuse and reconcile these interfaces
before creating parallel research schemas. Its `scripts/build_market_control_panel.py` currently
consumes local PWR/SPY/XLI close caches and writes a generic yfinance receipt; that is not a pinned
Massive-to-Snowflake dataset release. The new files do not resolve the acquisition findings below.

Main also records both original holdouts as spent in the
[sealed-test record](../../docs/plan/sealed-test-record.md). This assessment reads that published
record, not a new outcome analysis, and does not rerun its tests. Carry the contamination history
into the teammate package. The existing development fence remains a conservative working boundary;
it cannot recreate an untouched holdout. Any future holdout must be genuinely unexamined and have
an explicit owner/protocol. References below to sealed access concern such future approved windows.

Historical cloud counts belong to the [ingestion receipt](../../docs/inbox/vishnu-2026-10-03/central-ingest-handoff.md).
Do not copy those counts into a new “verified today” report. Start with the read-only snapshot in
[README.md](README.md#step-a-inventory-before-another-sec-archive-run); it inventories batches but
does not itself validate their values, market coverage, source rights or point-in-time availability.

## What to collect, and why

The initial engineering cohort is PWR, ETN, EME and DLR, with SPY plus proposed sector controls XLI
and XLRE. This is a plumbing pilot, not a sufficient or unbiased universe for a broad strategy claim.
Add controls only from their actual inception dates; never fabricate earlier history. Before a wider
study, declare industry/exposure and liquidity selection rules, historical membership and an approach
to inactive/delisted securities. Do not choose peers using subsequent returns or today's survivors.

| Priority / package | Question it answers | Existing support and remaining work |
|---|---|---|
| 1. Daily raw and split-adjusted OHLCV; dividends and splits | What return and liquidity were actually available, including distributions? | Seven Massive source modes exist, including these inputs. Repair validation, pin batches and construct/test a documented total-return series. Controls need coverage checks and acquisition where missing. |
| 1. Historical security master and trading calendar | Which issuer/security does a row refer to, and should it have traded? | Current loader requests start/end ticker metadata and ticker events. Add dated identity/membership intervals, exchange sessions, inactive coverage and explicit delisting/corporate-action treatment. A ticker is not a permanent identifier. |
| 1. SEC 8-K, 10-Q, 10-K, amendments and relevant exhibits; dated IR releases | What did management promise or revise, and when was it first public? | Filing register and SEC archive machinery exist. Reconcile original bytes and repair archive version paths before another bulk archive run. Massive disclosure tags help discovery; original exhibits remain necessary. |
| 1. Reviewed guidance/expectation and company-exposure tables | Is this a comparable change affecting this security? | Existing event-readiness contract supports reviewed facts. Populate actual source-linked records: same metric, target period, unit, scope and earlier expectation. Record contract/project counterparties and review provenance. Missing consensus is missing, not zero surprise. |
| 2. Sector/style/rates controls and earnings/coincident-event flags | Is the move broad-market, sector, interest-rate or company-event exposure? | Pin control prices and separate factor-source versions. Fundamentals require original filing availability. Earnings announcement timing and confounding events require source evidence. Current revised macro histories cannot automatically become historical inputs. |
| 2. EIA generation/project vintages and targeted economic releases | Do physical delivery and demand conditions support the proposed mechanism? | Reuse existing archives after release-clock and company-link validation. A vintage month is not its publication timestamp; a project owner name is not a verified listed-equity exposure. |
| 3. Intraday trades/quotes or compute-market histories | Does a declared execution or emerging-market hypothesis need these observations? | Separate acquisition specification and cost/entitlement check. Daily data cannot validate HFT fills; AWS posted prices cannot establish executable compute-futures P&L. These are not prerequisites for the first daily equity handoff. |

“All important data” should mean coverage of these explicit questions, not every endpoint.
Use all justified, entitled history for a declared universe, with shorter source coverage preserved
honestly. Long equity history does not lengthen a newer filing product or compute market's history.

## Confirmed ingestion gaps

Source: [massive.py](../central_ingest/massive.py) and [sync.py](../central_ingest/sync.py).
These are client validation findings, not evidence that Massive delivered bad data.

| Finding | Evidence / consequence | Required acceptance check |
|---|---|---|
| Nonfinite close and negative volume pass | Mocked `get_bars()` returns rows containing `NaN` close or volume `-1` without error. | Strict finite numeric checks, equity-price domain checks, nonnegative volume/counts, integer count validation, OHLC consistency. |
| Dates outside the request pass | A January 2021 response passes a January 2020 request. | Validate requested dates and response trading dates in the endpoint's ET convention, alongside chronology and duplicate checks. |
| Individual missing symbols can disappear | `get_bars()` can return `[]`; multi-symbol loader checks only whether the combined batch is empty. Action empty receipts are emitted only when the entire batch is empty. | Per-symbol/window receipts, including explicit zero-result outcomes. Compare sessions, listing history and actual rows; investigate gaps instead of filling prices. |
| Response provenance is incomplete | Bars are normalized before retention; server request IDs, response ticker/adjustment mode and original page bytes are not retained. | Retain each original response with a content hash, redacted request parameters, receipt time, provider request ID and page linkage. Verify returned ticker/adjustment mode. |
| Pagination and retries need stronger completion evidence | Loops follow `next_url` without repeated-cursor protection; progress is not checkpointed per page. | Bound pages, detect cursor cycles, retain completed pages, distinguish denied/failed/empty requests and support deterministic resume. |
| Repeat runs update manifest retrieval time | `MERGE` replaces the same batch manifest's `RETRIEVED_AT`. | Append run receipts separately from immutable content identity; preserve first retrieval and later rechecks. Serialize writers and validate stored key uniqueness. |

Compact offline reproduction (no credentials, network or market observations):

```sh
python3 - <<'PY'
import sys
from unittest.mock import patch
sys.path.insert(0, 'src/central_ingest')
import massive
base = dict(t=1609794000000, o=100, h=101, l=99, c=100, v=10)
for label, changes in [('negative_volume', {'v': -1}),
                       ('nonfinite_close', {'c': float('nan')}),
                       ('outside_requested_dates', {})]:
    with patch.object(massive, 'request_json', return_value={'results': [base | changes]}):
        rows = massive.get_bars('TEST', '2020-01-01', '2020-01-31', 'unused')
        print(label, 'ACCEPTED', len(rows))
with patch.object(massive, 'request_json', return_value={'results': []}):
    print('empty_symbol', massive.get_bars('TEST', '2020-01-01', '2020-01-31', 'unused'))
PY
```

Observed: three `ACCEPTED 1` results and `empty_symbol []`. Rerun after repair to demonstrate
rejection, then replace these diagnostic probes with ingestion-owner regression tests.
Existing event-readiness tests do not certify this provider client or a live Snowflake connection.

SEC archive retention defects and EIA timing defects are owned by
[SYSTEM_AUDIT.md](SYSTEM_AUDIT.md#4-material-audit-findings). Do not silently republish the same
invalid assumptions in a new schema. Coordinate repairs in the ingestion owner's component;
this assessment does not change their implementation.

## Proposed Snowflake release contract

Keep the existing `RAW.SOURCE_RECORDS` batches as traceable inputs. Add a separately versioned
research interface after validation; don't silently rewrite old data or blend revised snapshots.

1. **Retained source layer:** immutable response/document objects, content hashes, request/run
   receipts, full request scope, source terms reference, code revision, retrieval failures and
   per-symbol coverage. Secrets never enter URLs recorded in logs, manifests or shared exports.
2. **Normalized layer:** typed security history, market sessions, bars, actions, filings, reviewed
   facts, exposure links and release vintages. Stable keys; explicit units, currencies and nulls;
   source/batch/document references on every row. Do not infer a publication clock from a period.
3. **Released development layer:** a pinned dataset version listing exact source batches, code
   and transformation versions, schema, approved date fence, exclusions, QA receipts and rebuild
   query. Features and outcomes have separate tables/views and access rules. No `latest` batch
   selection in a reproducible research query.

At minimum distinguish `period_or_session`, `first_public_at`, `retrieved_at` and
`decision_available_at` (including a declared processing lag). For bars, window-start time cannot
be the availability of the completed bar. For reconstructed document facts, distinguish original
public evidence from today's extraction/review. Unknown historical availability remains unknown.

The teammate receives read-only SQL views or a permitted, versioned Parquet export; a data
dictionary and join-key map; issuer/date/source coverage; missingness and exclusion reasons;
rebuild instructions; and a small development example tracing original evidence → comparable
revision → security → market session. Counts alone do not qualify the package as usable.
Access to the entire raw warehouse can bypass an OOS view, so the teammate's role must be scoped
to approved development data if a holdout is to remain sealed.

## Execution order on this computer

1. Establish the private configuration location/profile. Existing loader supports a root ignored
   `.env` or process environment: `MASSIVE_API_KEY`, plus `SNOWFLAKE_CONNECTION_NAME` or explicit
   Snowflake account/user/warehouse and authentication. Its `.env` parser accepts plain `KEY=VALUE`,
   not shell syntax; it does not remove surrounding quotes. Never paste credentials into chat.
   Refer to [operator setup](../central_ingest/README.md#operator-setup-and-commands) for alternatives.
   Preserve the existing licensing assertion requirement; record the underlying permission rather
   than setting the flag automatically. Provider documentation is not proof of sponsor-key access.
2. Inventory Snowflake read-only, reconcile historical batches and check whether another ingestion
   job is active. Use separate warehouse writer and teammate reader roles; verify grants and query
   cost controls. No TigerData writes are planned under the inherited headroom constraint.
3. Repair the checks above, then run a small development-window canary. Check both adjustment modes,
   an independently confirmed dividend/split example, empty vs denied responses, pagination and
   returned identities. Confirm endpoint entitlements and earliest accessible coverage on the key.
4. Compare retained source, normalized rows and Snowflake rows/hashes; rerun the identical retained
   input and require no extra logical records while retaining a new run receipt. Failures stay
   explicitly incomplete. Don't call an HTTP success or a MERGE success an accepted dataset.
5. Backfill only missing, approved partitions, initially by symbol/year with deterministic checkpoint
   receipts. Preserve prior provider revisions and label the selected version. Acquisition of sealed
   dates, if authorized, does not authorize reading their outcomes or exposing them to researchers.
6. Publish the development dataset only after the source, coverage, timing, adjustment and access
   checks pass. Broaden the universe and optional datasets through the same process.

## Provider facts checked for this assessment

- [Custom bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars): adjustment is for
  splits; the timestamp marks window start. Eligible-trade rules can leave intervals without a bar,
  and historical access depends on the account plan. These facts motivate separate availability,
  gap classification and entitlement checks.
- [Dividends](https://massive.com/docs/rest/stocks/corporate-actions/dividends): separate action
  records include relevant dates and amounts. Total returns need a consistent share basis;
  adding an unadjusted dividend to a split-adjusted price can be wrong.
- [8-K text](https://massive.com/docs/rest/stocks/filings/8-k-text): parsed core Items content is
  available through a separate beta endpoint. It is not a guarantee that exhibits are retained.
  The current repo's `massive_8k` mode uses disclosure tags, not this text endpoint.
- [All tickers](https://massive.com/docs/rest/stocks/tickers/all-tickers): identity and active-status
  discovery is a separate API from the current two-date ticker-details loop. Historical selection
  still needs explicit, tested reconstruction rules.

These checks describe API semantics. They do not verify this project's entitlements, stored
contents, full archive coverage, redistribution rights or performance of a trading strategy.
