# Interface v1 — evidence before event features

Owner: aidanq06. Changes to these contracts must be versioned. They do not change the approved
Snowflake schema or another component's API. JSON is the portable boundary; there is no loader
for normalized/feature tables in this implementation.

## Archive snapshot → reconciliation

`archive.reconcile(snapshot, expected_accessions, package_dir=None)` is deterministic. Its inputs:

| Object | Required fields |
|---|---|
| Selected accessions | Nonempty list of SEC accession strings, explicitly selected from a register |
| Manifest | `accession`, `package_sha256`, `package_stage_path`, `package_size_bytes`, `document_count`, `documents` (or original `documents_json`) |
| Manifest document | `name`, `sha256`, `size_bytes` |
| Document table row | `accession`, `package_sha256`, `package_stage_path`, `document_name`, `document_sha256`, `document_size_bytes` |
| Stage listing row | `name`; other LIST fields may be retained but are not original-byte evidence |
| Local packages | A private directory of `<package_sha256>.zip` files, downloaded without modifying content |

The snapshot keys are `manifests`, `documents`, and `stage_objects`. Table fields are lowercase
normalized names. The collector removes text-context excerpts from manifest document metadata.
All selected versions are checked; choosing the latest row is not an implicit repair. Extra
unselected accessions are outside the selected audit scope. Stage paths must resolve in the
specified SEC archive and match accession identity, not merely a filename suffix.

`archive_ready` requires metadata and byte checks for every selected version. An empty selection
raises an error. Missing files, duplicates, orphan document versions and path reuse produce
machine-readable problems. The result is not a feature/strategy approval. Snapshot timestamps
and query IDs describe a bounded series of reads, not an atomic database snapshot; stop the writer
or repeat after stabilization when reconciling an in-flight batch.

Source inventory is separately reconciled by `(source_id, batch_sha256)` and row-index count.
It cannot establish payload integrity, original market availability or exact parity with another
warehouse; preserve that distinction in every UI/report.

## Source fact → comparable revision

`features.Fact.from_dict(record)` rejects unknown columns. Required string fields:

| Concern | Fields |
|---|---|
| Identity | `fact_id`, `event_cluster_id`, `issuer_cik` (ten digits), `ticker`, `security_id`, `accession`, `form` |
| Comparable definition | `metric_name`, `fact_kind`, `unit`, `currency`, `scope`, `definition_version`, `target_period`, `comparability_group` |
| Numeric observation | `value_text` (original numeric token), `value_decimal` (normalized exact decimal string) |
| Original source | `source_document_url`, `document_sha256`, `source_quote`, `input_batch_sha256` |
| Timing | `publication_basis`, `published_at`, `reviewed_at` |
| Review/lineage | `review_status`, `reviewer_id`, `exposure_status`, `exposure_evidence_id`, `extractor_version` |

`source_span_start` and `source_span_end` are integer UTF-8 **byte offsets**, half-open, in the
original document bytes. The byte slice must equal `source_quote.encode('utf-8')` exactly and
include the numeric token. Decimal strings permit signed integer/decimal numeric tokens, optionally
with correctly grouped thousands separators. Signs in parentheses or prose such as “about ten”
are unsupported: review/normalize through an explicitly extended extractor, not a heuristic here.

Optional fields: `expectation_id`, `supersedes_id` (string or null), and `value_scale_decimal`
(default `"1"`). A token `"12.5"` with scale `"1000000"` must give `"12500000"`; passing through
binary float is forbidden. Normalized input values must fit NUMBER(38,12). Derived JSON ratios
are rounded to 12 decimal places, half-even, with 64-digit intermediate context. This is **not** a
SQL export: narrower target column precision and missing market fields must be checked by a future
Snowflake adapter. No rounding of the source measurement is hidden in normalization.

Current implementation supports scalar numeric **management guidance only**. A range forecast,
schedule date, MW event, cancellation category or backlog balance requires a separately versioned
family/parser. In particular, there is no midpoint-of-range choice or “backlog fell, so delay” rule.

`comparison_key` is issuer + security + metric + kind + unit + currency + scope + definition version
+ comparability group + target period. A changed acquisition perimeter/segment definition must
change the comparability group. Matching arbitrary strings is necessary but does not replace a
reviewer establishing genuine comparability. A target-year change is not a revision to the old year.

The explicit earlier expectation must match this key and be strictly earlier in source time.
An intervening same-key statement blocks stale-baseline selection, even if unreviewed. Identical
input rows are deduplicated by fact ID; conflicting ID reuse is fatal. Multiple fact IDs for the
same accession/comparison key are ambiguous duplicates and fatal. Amendments use new IDs and a
`supersedes_id` whose source time is earlier and cluster matches. They never rewrite earlier rows.

Review status: `reviewed`, `unreviewed`, `rejected`. Exposure status: `verified`, `ambiguous`,
`unmatched`. Only reviewed facts with a reviewer/time and verified exposure evidence qualify.
Review time cannot precede source publication; review performed now is permitted only as explicitly
labelled retrospective reconstruction. Evidence IDs are attestations, not software-verified legal
contract links or user authentication.

## Timing and the development fence

| `publication_basis` | Meaning | Treatment |
|---|---|---|
| `verified_public_time` | Exact first-public time reviewed against the cited original release | Requires timezone-aware ISO time |
| `sec_acceptance` | The cited fact is known no later than its verified SEC acceptance | Requires timezone-aware ISO time; does not claim SEC was first dissemination |
| `date_upper_bound` | Source is known to have appeared on this New York calendar date, time unresolved | Available at following local midnight, converted with DST to UTC |

A period-end, current download time or an undated document has no publication basis and fails.
`decision_at` adds an explicit positive processing lag (default 60 seconds) to the availability
bound. The CLI admits source times in `[2015-07-01, 2022-10-01)` UTC only; it also excludes
rows whose decision crosses the end. There is no sealed override. A time-zone-less timestamp fails.
Header checks fence later records before interpreting their numerical values or loading their
source documents. They do not protect a user who already examined a whole sealed dataset elsewhere.
The input package itself must be an upstream development-only export.

The `next_session_close()` helper takes a **pinned** caller-supplied exchange calendar: ordered
unique `date`, `open`, `close` records with zone-aware instants. It selects the first session whose
New York date is strictly later than availability's New York date, including for pre-open releases.
This is a conservative full-day-bar lag. A date-only bound can add an extra session. It does not
invent holidays, impute a missing bar, validate the calendar provider or promise a closing fill.
A future market-label join must reject incomplete calendars and missing prices explicitly.

## Normalization and clustering

Raw difference = current normalized value − prior normalized value. Relative revision is defined
only for a strictly positive prior; zero/negative denominators retain absolute revision with an
explicit null reason for percentage. No arbitrary denominator floor is introduced.

Past baseline: one latest strictly earlier eligible revision per other cluster, within the same
series key (target period omitted so reviewed comparable years can contribute). Simultaneous
publications and the current cluster contribute nothing. Median deviation is reported when any
history exists. Robust z uses `1.4826 * MAD` only after the declared minimum cluster count and
positive MAD; otherwise null. This scale is a feature convention, not an assumption of Gaussian
returns. Cluster identifiers do not prove independence; common-shock review and sample-size
adequacy remain necessary. No bootstrap or confidence interval is manufactured.

Feature hashes include current/prior fact hashes, original document hashes, selected prior-history
IDs, units, source clocks and the definition version. Changes in reviewer/source metadata change
lineage. The output separates `features`, `exclusions`, reason counts and ticker/metric/year coverage.
The first public statement has no prior guidance and is excluded as an event but can serve as a
later event's baseline. That exclusion is expected.

## Downstream boundary

The new JSON is an input-side reference for the handoff's proposed operational-facts/features
schema. It is not claimed to populate all its columns: market beta/volatility/liquidity, price
batch/action metadata, exposures as numerical fractions and return labels remain unimplemented.
No database DDL runs and there is no strategy promotion. The existing canonical feature contract
continues to own those broader requirements.

The eventual label component must consume immutable event row IDs plus pinned market, action and
calendar manifests. It must test split/dividend math, common sessions, missing bars, entry/exit
reference definitions, costs/borrow, label end availability and purging of overlapping/shared-shock
windows. It may never feed forward values back into this builder. Model, council, q and native
implementations should consume the same frozen artifacts, with numerical parity tests at the seam.
