# Strategy data features: first usable contract

Owner: vshnu1. Status: data/feature contract for the first equity study; not an approved trading
rule, populated feature store, or alpha result. The contract separates information known at a
decision from labels observed afterwards. It is intentionally narrower than the full thesis.

## Readiness in one sentence

The team can begin implementing the point-in-time event panel and validation harness, but the
initial strategy features are **not yet complete or strategy-ready**: the company financial panel
covers only PWR and ETN, raw SEC packages are still being archived, the market event-study code
fetches some benchmarks live, and no frozen typed feature table or point-in-time analyst
expectations exist.

## What exists now

| Input / artifact | Current evidence | Use and limitation |
|---|---|---|
| Company filing register | `results/filings-register.csv`, 776 register rows, 2015–2026; accession and EDGAR acceptance fields | Filing/event clock. A register is metadata, not preserved filing content or a reviewed metric extraction. |
| Company obligations | `results/obligation-panel.csv`, 130 facts: PWR 115, ETN 15; 102 have matched acceptance timestamps, 28 do not | Initial RPO/XBRL feature prototype only. It has no EME or DLR rows; concept/tag/period comparability requires review. |
| Company revisions/events | `results/revision-events.csv`, 84 rows | Diagnostic event study only. It is not a portfolio backtest; horizon results are exploratory, small and concentrated (70/84 PWR per `src/event/README.md`). |
| Daily market bars | Massive adjusted and unadjusted daily aggregates for PWR, ETN, EME, DLR and SPY, 2016-01-01–2026-10-02; 13,515 rows per full-basket batch | Enough to prototype daily returns on these five securities. The current adjustment history is a retrieved snapshot, not a historical point-in-time corporate-action record. |
| Market controls | The current event runner obtains XLI/XLRE and bars through `yfinance` when run | Not a pinned, shared, hash-reconciled input. Replace with a retained dataset and manifest before citing results. |
| Massive 8-K tags | 201 rows for the four operating names, 2022–2026, in the verified batches | Discovery/enrichment only; tags are not the original disclosure, canonical acceptance clock, or a prior expectation. Join to SEC accession and inspect source documents. |
| EIA-860M | Full generator rows and original vintages in Snowflake through 2026-08; TigerData summaries only through 2022-12 | Physical generation-schedule context. Not a data-center or contractor exposure map; keep out of the first equity signal until exposure is defensible. |
| Public macro/supply context | Census C30/M3, Philly Fed, NY Fed GSCPI, FRED/EIA extracts in raw shared tables (see central ingest receipt) | Optional controls/context with vintage caveats; current revised snapshots must not be backdated as first-release values. |
| AWS Spot GPU archive | 1,592,024 rows, 2022-05-31–2026-09-30; March–June 2026 source gap | Compute-market covariate for a separate short modern-era study, not a decade-long signal or security return substitute. |
| Delivery hazard factors | 27,069 project-month rows in the current bottleneck panel; reported out-of-sample AUC is below controls-only | Negative mechanism-stage result. These predictors target schedule revisions, not equity returns; do not pass them directly into a stock strategy. |

Cloud raw batch details, exact batch IDs/hashes, access commands and licensing caveats are owned by
the [central ingestion receipt](central-ingest-handoff.md). TigerData is near/over its previously
observed free storage allowance. Do not append data there until the actual plan/limit is confirmed.
Snowflake is the archival and feature-panel target; kdb+ is a proposed derived time-series layer,
not a current source of truth or a substitute for missing point-in-time facts.

## Minimal first study: features versus labels

Freeze this schema before implementing any strategy. Keep one row per issuer-disclosure event and
one separate row per return label/horizon. Unknown values remain null with a reason; never fill an
unknown exposure with zero.

### Event/features table — inputs available at decision time

| Field | Type / units | Rule |
|---|---|---|
| `event_id`, `event_cluster_id` | stable strings | Event ID identifies one source-backed disclosure; cluster groups repeated updates about the same project/customer/common shock. |
| `issuer_cik`, `ticker`, `security_id` | string | Keep CIK and permanent security identity separately; ticker alone is not historical identity. |
| `accession`, `form`, `source_document_url`, `document_sha256` | string | Link to the original filing/exhibit and immutable content hash. Massive tag is secondary, not a replacement. |
| `filed_at_utc`, `accepted_at_utc`, `first_public_at_utc`, `available_at_utc` | timezone-aware timestamp | Preserve distinct clocks. If first public time is unresolved, use a conservative documented availability and flag the resolution; never infer intraday timing from filed date. |
| `economic_period_start`, `economic_period_end`, `target_period` | date/month or interval | Keep fiscal observation period separate from publication and target/completion periods. |
| `metric_name`, `concept`, `segment`, `project_id`, `customer_id`, `counterparty_id` | string / nullable | Do not pool unlike metrics. Entity/project matches require evidence and effective dates. |
| `value_text`, `value_decimal`, `prior_value_decimal`, `delta_decimal` | decimal text + exact decimal | Preserve source text; normalize only with explicit unit/scale. Avoid binary float for money/capacity extraction. |
| `unit`, `currency`, `scope`, `definition_version` | string | Comparisons require same unit, scope, metric definition and target period; conversions are explicit/versioned. |
| `fact_kind`, `direction`, `change_months`, `change_mw`, `change_usd` | categorical + nullable numeric | Distinguish backlog/RPO, order, guidance, delay, cancellation and delivery. Falling backlog can mean successful delivery; sign alone is not a “bad news” label. |
| `expectation_type`, `expectation_value`, `expectation_available_at` | enum + decimal + timestamp | First baseline: prior public management guidance for the same metric/target period. Label it as management guidance, not analyst consensus. Analyst consensus stays absent unless true historical vintages are licensed and available. |
| `revision_pct`, `revision_abs`, `revision_vs_past_median`, `past_mad_z`, `n_prior_events` | decimal + count | Candidate numeric features only. Compute expanding/rolling statistics from prior events known before this event; require a declared minimum history and retain raw revision beside standardized values. |
| `exposure_status`, `exposure_fraction`, `exposure_evidence_id` | enum + decimal + string | Verified / ambiguous / unmatched. Eligibility requires verified contemporaneous exposure; never treat unmatched as zero. |
| `extractor_version`, `review_status`, `source_span`, `confidence` | string / enum / source offsets | Human review required for facts used in the first result. Low-confidence/unreviewed extraction abstains. |
| `input_batch_sha256`, `retrieved_at_utc`, `feature_version` | string / timestamp | Reproducibility and immutable provenance. |

### Market features — decision-time state, not the thesis itself

For the first event study, construct these from retained daily bars and actions. Store the input
batch hash and bar convention with every output.

- `return_1d`, `return_5d`, `return_20d`: split/dividend-consistent close-to-close returns; no
  price after `available_at` may enter a feature.
- `market_return_20d` and sector return: matching-session benchmark return. Use retained,
  manifest-backed SPY and appropriate sector series; do not depend on live `yfinance` calls.
- `beta_market_past`, `beta_sector_past`: estimate betas only from a trailing window ending before
  the event. Forward abnormal returns belong only in outcome labels, never in this feature table.
- `realized_vol_20d`, `dollar_volume_20d`, and `missing_bar_flag`: past-only volatility/liquidity
  state and explicit coverage. These support controls and sizing; they are not presumed alpha.
- `corporate_action_flag` and `bar_adjustment_version`: identify where adjustment conventions
  can affect measured returns.

### Outcome labels — never features

Create a separate `event_labels` table keyed to `event_id`, `label_horizon_sessions`, and
`label_version`: next-session entry reference, 1/2/5/10/20-session raw return, benchmark return,
abnormal return, estimated spread/cost, and label end time. Keep labels out of the event-feature
view. Do not tune the primary horizon from development labels; the holdout rule is in
[`docs/brief.md`](../../brief.md).

## Eligibility and first implementation order

1. **Source-backed facts:** finish the original SEC accession/exhibit archive and reconcile package
   count/hash against the register. Build/extend comparable fields for PWR, ETN, EME and DLR;
   retain unreviewed/unavailable status. Repeated quarterly observations are not independent
   project shocks.
2. **First-public clock:** match each metric to its accession and exhibit; resolve press releases
   or other earlier dissemination where possible. If unresolved, use a conservative lag or exclude.
3. **Expectations:** use the firm's prior public guidance for the same metric/target period as the
   pilot baseline. Label this `management_guidance`, not analyst consensus. Analyst PIT estimates
   remain a known gap.
4. **Market panel:** materialize a versioned, warehouse-queryable daily panel for
   PWR/ETN/EME/DLR/SPY plus XLI/XLRE (or predeclared alternatives) with corporate actions, row
   counts and hashes. Then use only a past-only beta window and labels strictly after availability.
5. **Company/event crosswalk:** manually verify CIK, ticker/security ID, metric, project/counterparty,
   exposure, segment and event-cluster links. No name-only joins.
6. **Feature QA:** add golden fixtures for timezone/after-close events, missing acceptance,
   duplicate accessions, revised filings, unit mismatch, zero/negative denominators, first event
   with no baseline, overlapping labels, splits/dividends and missing sessions. Assert that an
   observation with `available_at > decision_at` cannot enter features.
7. **Only then fit:** freeze the hypothesis, one primary feature family, target horizon, baseline,
   costs, capacity and falsifiers in the strategy owner's thesis/contract. Do not append EIA,
   compute spot, imagery or L2 because they exist. Add them only if an exposure-mapped ablation
   shows the same predeclared decision improves.

## Explicit readiness gates

“Ready for strategy research” means all are true, not just that tables have rows:

- Original raw document bytes and hashes reconcile to each selected accession; data rights/citation
  are documented for team use and public reproducibility.
- Every usable feature has an explicit unit, time basis, availability rule, null reason and code
  version; no current snapshot is represented as point-in-time history.
- Selected event facts have prior comparable expectations and a reviewed source span; first-public
  time is resolved or conservatively lagged.
- Four candidate firms and benchmark/sector panels have adequate market coverage, pinned input
  batches and corporate-action handling.
- Exposure and event clusters are reviewed; effective independent shock count is reported.
- Feature/label separation and chronological/OOS fences have tests, and the run manifest hashes all
  inputs/configuration/code.

Until these gates pass, the honest status is **pipeline prototype / descriptive event study**, not
a validated strategy. Present data is adequate to implement the contract and test plumbing; it is
not adequate to make performance claims.
