# VECTOR / Gator Quant Hacks — ultimate continuation handoff

**Purpose:** let a new computer, harness, teammate, or agent continue this work without replaying
the long chat or mistaking a proposal for a verified result. This is an operational handoff and
research memory, not a thesis, alpha claim, license grant, credential store, or replacement for the
repository's canonical records.

**Snapshot date:** 2026-10-03. The repository and cloud can change after this snapshot. Re-check
the branch, cloud inventories, and running jobs before acting. The commit that preceded this
handoff was `999ae6d`; use `git log -1` for the handoff commit itself.

**Repo:** <https://github.com/sebastbernal2-ship-it/gqh-delivery-gap> (public, `main`).

## If you have five minutes

1. `cd` into the repo and run `make sync`; if `hippo` is unavailable, that command prints a
   fallback. Read this file, then `AGENTS.md`, `docs/CURRENT.md`, `docs/brief.md`,
   `docs/decisions.md`, `docs/alignment.md`, `OWNERS.md`, and
   [`memory/SHARED.md`](../../../memory/SHARED.md).
2. The active strategic preference from Vishnu is **equities first**, with a measurable economic
   link to delivery/capacity constraints. PWR, ETN, EME and DLR are candidates; SPY is a benchmark.
   No universe, pair, signal, horizon, or thesis is approved. The thesis ledger is empty.
3. The central question is whether a new, public, source-backed revision in delivery/capacity,
   compared with an earlier public expectation, changes a company's economics and predicts
   subsequent abnormal equity return **after** ordinary news, market/sector exposure and costs.
   That chain is not established. Current project-level hazard factors did not improve out-of-sample
   prediction; the small company event study is not a profitable-strategy result.
4. The most recent team node/edge map records the most promising untested relationship as
   **delivery revision → executed compute rental price**; that path lacks an executed-rental feed.
   This is a candidate for further feasibility work, not a reversal of Vishnu's equity-first
   preference and not a settled team thesis. Do not infer that AWS Spot list/history prices are
   executed rentals.
5. Data has already been loaded into Snowflake and TigerData, but both are **raw shared landing
   layers**, not finished point-in-time strategy features. Use exact `SOURCE_ID` and
   `BATCH_SHA256`; never blend canaries, revised batches, or different vintages.
6. TigerData's last reported footprint was **786,011,839 bytes (~749.6 MiB)** against an observed
   750 MiB allowance. No additional writes to TigerData until its actual limit/headroom is verified.
   Loader defaults were changed to Snowflake for safety.
7. An equity event feature contract and Snowflake DDL now exist, but the DDL has not been applied,
   feature tables are not populated, raw SEC archive work was still running at this snapshot, and
   historical point-in-time analyst expectations are missing. The data are **not strategy-ready**.
8. A kdb+/q HDB prototype for HiPerGator is committed, but has **not** run on HiPerGator. The q
   code is not runtime-validated. No data have been migrated into an HDB. Never delete TigerData
   rows as part of this work.
9. No additional API key is needed for the next local/documentation step. Do not paste credentials
   into chat or Git. Secrets were shared in the earlier conversation; treat those values as
   compromised and rotate them.
10. Start with the ordered action list near the end. Do not train/fine-tune, add GPU workloads,
    buy L2/L3, or create a live order system before the event panel, clocks, market panel and
    baseline are validated.

## Continuation prompt for a fresh assistant

You can give a new assistant this block together with the repository checkout:

> Continue the GQH VECTOR work from this repository. First run `make sync`, read `AGENTS.md`,
> `memory/SHARED.md`, `docs/CURRENT.md`, `docs/brief.md`, `docs/decisions.md`, `docs/alignment.md`,
> `OWNERS.md`, and `docs/inbox/vishnu-2026-10-03/ultimate-handoff.md`. Respect one-writer ownership,
> preserve the empty thesis ledger until a hypothesis is actually approved, and do not claim
> strategy alpha from the current negative/diagnostic research. The user prefers an equity-first,
> economically grounded study of public delivery/capacity revisions versus earlier expectations;
> the candidate basket is PWR/ETN/EME/DLR with SPY benchmark, but no final universe/pair/horizon is
> approved. The exact feature/data-readiness gaps and row schemas are documented in
> `strategy-feature-contract.md`. Snowflake is archival/research, TigerData is operational but near
> its observed quota, and a q HDB on HiPerGator is only a tested-local scaffold. Do not write more
> TigerData data until quota headroom is verified; do not delete any existing rows. SEC raw archive
> completion must be reconciled from Snowflake manifests and stage objects before claiming success.
> Continue in this order: verify actual cloud receipts and SEC archival; complete a source-backed,
> reviewed, availability-safe event panel; pin market/sector controls; test the simple baseline and
> costs; keep the GQH sealed holdout untouched. Do not put credentials, account URLs with passwords,
> raw licensed data, or personal paths in Git. If committing, stage only owned, task-scoped files,
> rebase first, run relevant tests, and push so teammates can see the result.

## Canonical navigation: which file owns what

Do not duplicate a moving fact if the owner file already has it; update that file and link here.

| Topic | Canonical file | Read this for |
|---|---|---|
| Track rules/deadline/holdout/rubric | [`docs/brief.md`](../../brief.md) | Frozen competition constraints; do not edit. |
| Current thesis position | [`docs/CURRENT.md`](../../CURRENT.md) and `docs/theses/index.jsonl` | Generated view; ledger currently has no records. Never edit CURRENT by hand. |
| Accepted decisions and measured research history | [`docs/decisions.md`](../../decisions.md) | Settled calls, negative results and corrections. Append decisions; do not rewrite history. |
| Shared research reasoning | [`docs/alignment.md`](../../alignment.md) | Economic chain and evidence discipline. |
| Method from idea to test | [`docs/plan/edge-search.md`](../../plan/edge-search.md) | Gates against data-mining/co-movement-as-alpha. |
| Strategy input/data feature definition | [`strategy-feature-contract.md`](strategy-feature-contract.md) | Current readiness counts, schema, feature/label separation and acceptance gates. |
| Providers, sources and field coverage | [`source-audit.md`](source-audit.md) | Free/paid source audit, historical range, links, caveats. Older load claims are superseded by the central receipt. |
| Instruments and required market depth | [`data-plan.md`](data-plan.md) | Candidate ticker roles and L1/L2/L3 needs. Candidate list, not an approved universe. |
| Cloud raw-load receipt | [`central-ingest-handoff.md`](central-ingest-handoff.md) | Exact loaded batches/counts and current storage/SEC status. |
| Ingestion commands | [`src/central_ingest/README.md`](../../../src/central_ingest/README.md) | Operator setup, source IDs, target selection and queries. |
| Snowflake layout/DDL | [`src/snowflake/README.md`](../../../src/snowflake/README.md), [`bootstrap.sql`](../../../src/snowflake/bootstrap.sql) | Archive/research boundary and additive, currently unapplied event-feature DDL. |
| kdb+/q on HiPerGator | [`hpc/kdb-timeseries/README.md`](../../../hpc/kdb-timeseries/README.md) | Prototype, unit scale, scripts, jobs, prerequisites and verified status. |
| Earlier rationale and revisions | [`docs/thinking/vishnu-2026-10-03.md`](../../thinking/vishnu-2026-10-03.md) | Why ideas were added, narrowed, rejected or corrected. |
| Team memory | [`memory/SHARED.md`](../../../memory/SHARED.md) | Generated memory. Do not manually edit. |

The `docs/inbox/vishnu-2026-10-03/` folder is a handoff, not the promoted thesis. If a strategy
becomes a real claim, create its own thesis file, append the thesis ledger, and regenerate CURRENT.

## Research direction: what changed and why

### The broad starting brainstorm

Vishnu initially wanted to combine AI/data-center buildout and energy constraints with company
8-Ks, satellite imagery/hearing transcripts, EIA generator vintages, compute prices, AWS Spot,
perpetuals/Hyperliquid, L3/L4 order flow, possible options/ICE/OCPI data, Jev/Laya-style typed
extraction, quantum methods (VQE/QAOA, QGM, sampling), optimal transport, volatility models,
and HiPerGator GPUs. The core concern was right: an attractive collection of APIs and advanced
models is not yet an economic mechanism. The actual strategy must be rooted in a payer, an
observable surprise, a comparable expectation, an instrument, and a falsifiable return/physical
outcome.

### Narrowing that should be preserved

- **Equity-first became the practical preference.** Begin where the market has a long enough return
  history and relevant companies are listed. Use AI/compute/energy as the economic context, not as
  an excuse to force a short-history perp or thin contract into the first backtest.
- **The measurement moved from “AI is big” to a dated delivery/promise revision.** Preserve the
  earlier promised value, the revised value and target period, source publication/availability,
  unit, entity, contractual/economic exposure, and then the return response.
- **A long price history does not solve a young economic thesis.** Count independent project/shock
  clusters, firms, comparable definitions, and episodes per regime. Thousands of documents can
  collapse to a handful of common shocks. The team's “earthquake analogy” is useful: 40 years with
  five large events still gives roughly five event observations, not 40 years of independent
  evidence.
- **Two evaluation questions are legitimate but different.** (1) A chronological deployment
  simulation using only information known then. (2) A development-only regime robustness study.
  Regime thresholds must be learned within earlier data. A retrospectively balanced sample is
  exploratory and is not the competition's OOS simulation.
- **Use management guidance honestly.** The prior public company statement can form a transparent
  management-guidance baseline; it is not the same thing as historical sell-side consensus. A
  current consensus snapshot downloaded today is not point-in-time expectation data.
- **A decline in backlog/RPO is ambiguous.** It can reflect fulfilled work, cancellations, scope
  changes, FX/acquisitions, or revised expectations. Do not make sign = bad news. Compare same
  metric, scope, fiscal/target period and definition; code the event semantics and review the source.
- **The project-to-equity bridge is weak.** The latest records report only about 6.2% of slipped
  capacity can be linked to a large listed owner; 80% is associated with private project/holding
  companies. EIA plant name matching does not establish contractor/vendor exposure. Use verified
  contract/project/customer links or abstain.
- **Initial L2/L3/HFT ambitions were demoted.** A quarterly/monthly event signal and order-book
  execution happen on separate clocks. Daily OHLCV is enough for first event tests. L1/trades may
  later quantify spread and small-order execution; L2 only if size/impact needs it; L3/MBO only if
  queue reconstruction is a specified research question. Crypto “L4” is provider-specific wallet
  attribution, not a universal book level. None is required now.
- **Compute data is a distinct short regime.** AWS Spot offers a useful historical provider price
  archive, but it is not executed rental revenue, full utilization, fulfillment, or an exchange
  quote. It cannot borrow 10+ years from equities. The March–June 2026 hole remains missing, not
  imputed. The archive's event timestamp is not proof of when a trader could observe the quote.
- **Quantum/advanced math are optional experiments.** A quantum simulator on a GPU is classical
  compute. Quantum phenomena do not establish alpha. Optimal transport, spectra, Hawkes/cascade
  models, VQE/QAOA or fine-tuned extraction must answer one named test and beat a simple comparator
  on development data. Langlands, affine Kac–Moody, etc. have no load-bearing use in this strategy.
- **Satellite imagery is not the primary stream.** One eight-site probe produced texture/slippage
  correlation +0.72 and bright-fraction +0.58, but it tested four features on only eight sites
  (five late, three early). This is a pre-registration hint only; run 30–50 labeled sites with
  scene/background controls before claiming a physical-progress signal. Satellite imagery is
  slower/noisier than company disclosure, and imagery brightness is not MW/commissioning.
- **Local hearings/permits may quantify progress** if dates, capacity, transformer milestones,
  interconnection decisions or delay durations can be consistently extracted, but video/transcript
  automation is a secondary path. It needs an archive, first-public timestamps, stable site IDs,
  extraction review and actual company exposure. It is not a binary “permit yes/no” strategy.
- **Long/short is not automatic protection.** Both legs can fall together; beta neutrality leaves
  industry, liquidity, basis, joint-tail, borrow and financing risk. No trade pair is chosen.

See the thinking file for a chronological history. Do not restart the brainstorming from zero.

## Working economic question and evidence chain

The shared framing in `docs/alignment.md` is:

> Can an unexpected, publicly observable revision to delivery or capacity change a company's future
> economics in a way its price does not fully reflect, after ordinary earnings news, demand, sector
> and market exposure, and the cost of trading?

For every candidate, trace and label the chain:

`source observation → physical implication → contractual/cash-flow implication → expected price response → executable decision`

Mark each arrow **observed, inferred, or untested**. Identify the payer and counterparty; write the
ordinary rival (earnings/demand/market/sector, already-anticipated news, liquidity) and falsifier
before examining returns. A plausible delivery story plus a powerful model does not fill a missing
link.

### Candidate equity map (not approved)

| Name | Potential economic role | What to source/review | Main trap |
|---|---|---|---|
| PWR (Quanta Services) | Contractor/project execution, power infrastructure | Electric segment backlog, 12-month backlog, margin/guidance, named scope/contract revisions, timing, acquisitions | RPO/backlog may not be project-specific or electricity-only; announcement can precede SEC filing; not every project is PWR risk. |
| ETN (Eaton) | Electrical equipment/orders and conversion of orders to revenue | Electrical orders/backlog/book-to-bill, capacity, supplier constraints, mix/margins, guidance | Broad segment/equipment demand may swamp AI/datacenter share; backlog duration versus delivery can vary. |
| EME (EMCOR) | Electrical/mechanical contractor installation | Segment RPO/backlog, expected revenue timing, margins, project contract events/acquisitions | Current company obligation facts not present in the 130-row panel; construction exposure not automatically data-center specific. |
| DLR (Digital Realty) | Data-center operator, lease/capacity monetization | Signed but not commenced leases, rent/lease commencements, development capacity/cost, guidance | Many developments do not have one public critical-path timestamp; dividends/corporate actions matter. |
| SPY | Broad market benchmark; maybe hedge only if analysis justifies it | Total-return/adjusted return aligned to event; later possibly point-in-time beta | Not presumed short leg; daily panel included, point-in-time universe/adjustment caveats remain. |

Other candidates mentioned: HUBB, POWL, VRT, GEV, EQIX, NVDA, AMD, GOOGL, CEG, etc. These are
watchlist names, not vetted additions. History, exposure, listing identity, acquisitions/spin-offs,
and PIT universe status must be audited first. Don't backfill successor histories.

### Candidate test, if and only if data become eligible

Start with one narrowly specified event family—e.g. a source-reviewed material change in same-scope
management guidance, project completion date, named contract/backlog, or scheduled capacity. Use a
previous publicly available expectation for the **same unit, scope and target period**. Consider
large schedule changes/cancellations separately from one-month nudges (one repo result found that
36% of first revisions are a one-month nudge; an earlier draft proposed 6+ month events). A
threshold cannot be tuned on returns; record why it is economically meaningful and test a declared
nearby plateau only in development.

If the target is equity response: announce-time plus a documented conservative processing lag sets
the earliest decision time. No same-bar close. A conservative first implementation could enter at
the first next eligible session and report a predeclared multi-horizon plateau (the repository
event code currently uses 1/2/5/10/20 sessions as diagnostics; no primary hold is approved). Report
raw, market/sector adjusted, costs, double costs, turnover, drawdown, overlap/cluster count, and
capacity limitations. The event study tests repricing; a portfolio rule still needs allocation,
position, sizing, abstention, exit/invalidation, borrow/financing, and execution rules.

If the target is physical delay or rental price instead, keep that as a separate labeled object.
Do not treat a good physical forecast as a financial strategy until you demonstrate the cash-flow
transmission and price response.

## What exists in the repository now

### Data/mechanics/results that are real on current main

- Central ingestion software exists under `src/central_ingest/`; it is a manual repeatable loader,
  not a scheduler, live connector or strategy feature pipeline.
- The Massive daily price panel and 8-K tags were API-requested and verified in both Snowflake and
  TigerData as described in `central-ingest-handoff.md`. Full daily bar batch:
  `bec91f7c380937d3d647ade8214968c13abd4bde032c9a7cf7741f0ee58306cd`; 13,515 rows for PWR,
  ETN, EME, DLR, SPY in the selected batch. Full 8-K batch:
  `a077dfb0f7948bb5b7de45eb6d1f6ef8f3297df7c4a1aa319fef7da60cb0ff51`; 201 tags. Canary batch
  exists separately; never sum it into the full panel.
- The market package includes adjusted/unadjusted aggregates, split/dividend records, ticker events
  and endpoint snapshots. These are current vendor snapshots; they are not full point-in-time
  security-master history. Adjusted history can reflect current corporate-action processing.
- Public source snapshots were loaded into raw Snowflake/TigerData `SOURCE_RECORDS` batches, with
  source IDs and checksums. Sixteen prior full raw source batches were reported as 137,439 rows
  each-target; more source IDs were added in the follow-up. Use the current inventory query before
  relying on those headline counts.
- AWS GPU Spot source archive is separately in
  Snowflake `VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES` and TigerData
  `public.aws_gpu_spot_prices`: reported 1,592,024 rows, 31 source files,
  2022-05-31 18:50:49 UTC–2026-09-30 23:00:00 UTC, 62 instance types. It is the 2026-09 Zenodo
  version of Eric Pauley's *AWS Spot Price History*, DOI 10.5281/zenodo.23082767, CC BY 4.0.
  March through June 2026 are absent. It resembles AWS EC2 Spot price history, not executed
  provider rentals, fulfillment/utilization, a standardized all-cloud index, or equity prices.
  Do not use event time as known-at time without availability evidence.
- EIA-860M full original monthly XLSX vintages and parsed generator records are reported in
  Snowflake through 2026-08. The index listed 2026-09 but downloads failed three times. TigerData
  has compact state/technology summaries through 2022-12 only. Generator schedules are not data
  center interconnection queues or contractor revenue exposure.
- Census C30, M3, Philly Fed delivery times, NY Fed GSCPI, FRED series, and limited EIA samples
  have raw batches as described in the receipt. Many are revised current snapshots; vintage or
  publication-time treatment is not complete. EIA-930 is a 24-hour parser sample, EIA-923 is PJM
  2024, not a long, complete regional market panel.
- SEC filing accession register is available as 776-row cloud/source artifact (2015–2026). It has
  CIK/accession/form/filed/acceptance fields, but a register is not original source content or
  reviewed financial feature values.
- The newest project-month/model work on `main` tested environmental and supply bottleneck factors
  against generator schedule revisions. The documented OOS results are negative: adding those
  factors made test discrimination worse than controls-only. Do not re-label that as a successful
  equity backtest.
- `docs/plan/node-edge-map.md` is the latest terrain map at the time of writing. It records a
  broad firm-obligation event study (382 firms, 4,634 events) with no association at 1–20 sessions
  and more nominal placebo hits than real data, plus physical factor tests with no OOS gain. It
  labels delivery → executed compute price as untested/blocked by lack of executed rentals.
  Treat that document's figures as the current team's checked report, and read the specific
  generated outputs and scripts before quoting them in the note.
- Results are produced/stored under `results/` and should be regenerated from code. Do not hand-edit
  figures. Check `results/README.md` and each result's script/header for status, scope and label
  semantics.

### Feature readiness (do not skip this section)

The exact current readiness audit and schema lives at
[`strategy-feature-contract.md`](strategy-feature-contract.md). Key counts at its last checked
state:

- `results/filings-register.csv`: 776 rows.
- `results/obligation-panel.csv`: 130 records: PWR 115, ETN 15; 102 have matched EDGAR acceptance,
  28 have no matching filing row; no EME or DLR facts.
- `results/revision-events.csv`: 84 event rows, heavily PWR-concentrated (70 PWR according to
  `src/event/README.md`); exploratory, not an actual portfolio/backtest result.
- Massive full-basket daily panel: 13,515 selected rows, five symbols through 2026-10-02; the
  matched XLI/XLRE market-control bars have not been stored/pinned in the same current batch.
- Current event study reaches XLI/XLRE through live `yfinance` requests. That is not a deterministic
  source/manifest pipeline. It must be replaced with retained, pinned controls or explicitly
  downgraded to a diagnostic.
- There is no verified point-in-time analyst-estimate archive. Prior management guidance may be a
  first-baseline candidate but is not market consensus.
- Snowflake has new DDL for `NORMALIZED.OPERATIONAL_FACTS`,
  `FEATURES.EQUITY_EVENT_FEATURES`, and `FEATURES.EQUITY_EVENT_LABELS`. DDL is not yet applied;
  tables are not populated. The older generic `FEATURES.POINT_IN_TIME_PANEL` is still present for
  compatibility and is not the new event schema.
- Review original filing/exhibit passages, normalize comparable definitions/units, resolve
  availability, map exposure/event clusters, then build the features. Unreviewed extraction is an
  abstention, not an input. Future returns/costs go in labels, never into the feature view.

This means the **data schema and research checklist are ready; the populated strategy features are
not**. Next build the corrected/reviewed panel and its tests, not a complex alpha engine.

## Source map: what each stream contributes, and what it cannot do

| Stream | Potential role | Current useful history | Status/caveat |
|---|---|---|---|
| SEC EDGAR 8-K/10-Q/10-K and exhibits | Original company facts, commitments, guidance, contract changes, filing clocks | EDGAR index from 1994; selected issuer register currently 2015–26 | Raw archive process was started and still running when this handoff was prepared; verify actual cloud manifests/staged objects before claiming complete. A filing may follow an earlier earnings release. Company Facts can be restated; accession versions matter. SEC public API needs no key, but a truthful contact User-Agent and fair-access rate are required. |
| Massive 8-K Disclosures | Vendor AI event categories, event discovery, competition-specific bonus | Tags since 2022 in product; loaded subset four operating firms, 201 tags | Enrichment, not canonical SEC time, not a document replacement, not point-in-time analyst expectation. API key was exposed in chat—rotate. Written rights to redistribute/share must be verified; a project-lead assertion is not a license itself. |
| Massive adjusted/unadjusted daily aggregates | Initial equity return panel | PWR/ETN/EME/DLR/SPY, Jan 2016–Oct 2 2026 | Sufficient to prototype daily event study, not deep execution. No stored historical point-in-time universe; adjusted is a current snapshot. Check source manifest, actions, missing/delist history. |
| Databento | Exchange data: trades/quotes/depth/options/futures where product/schema/venue grants it | Depends on dataset/product; no data selected for the first daily event study | Do not buy MBP-10/L2/L3 for all history absent an execution question/cost estimate. For event alpha, daily prices suffice first; targeted L1/trades later to model bid/ask and fill. Its market feed is not a compute rental API. |
| U.S. Census C30 | Realized national data-center construction spending context | Monthly from 2014 | National aggregate, nominal dollars, not site MW/commissioning/company-specific. Releases revise. |
| Census M3 | Electrical/computer/electronics orders, shipments, inventories, unfilled orders | Monthly from 1992 | Useful long supply-cycle controls; not a vendor's individual transformer/semiconductor lead time. Definitions/revisions need vintage discipline. |
| Census international trade | Import volumes/quantities in selected electrical/compute HS categories | Product/geography-dependent monthly span, often 2010/2013 onward | A broad supply proxy, not named vendor delivery or arrival date; HS code changes and unit mapping. API key may be required by current policy; verify source-audit before implementing. |
| EIA-860M | Planned/operating/cancelled generating-unit schedule vintages | Monthly from 2015, loaded to Aug 2026 in Snowflake | Quantifies generator pipeline status/MW, not data-center load interconnection or named contractor exposure. Keep original release vintage. |
| EIA-860 annual | Long history of generator/plant/owner inventory | Annual to 1990 (form changes) | Useful long-run capacity context; not comparable to monthly 860M without deliberate harmonization. |
| EIA-923 | Plant generation, fuel, heat input, operations | Utility history to 1970; sample currently only PJM 2024 | Current project has one-year parser/coverage test; not yet a complete regional validation stream. |
| EIA-930 | Balancing-authority hourly demand/generation/interchange | July 2015 onward; some fields from 2018 | Current loaded object is only a 24-hour sample. BA-wide stress, not a named site's meter or direct data-center load. |
| EPA CAMPD/CEMS | Unit-hour generation utilization/emissions | Covered fossil sources from 1995 | Bulk data candidate, not yet loaded. Coverage/observed vs substituted data differ; map through plant IDs. |
| Philly Fed manufacturing survey | Delivery-times/unfilled-order diffusion context | Monthly from 1968 | Third District diffusion measure, not literal supplier days or global semiconductors. |
| NY Fed GSCPI | Global supply-chain pressure regime | Monthly from 1997 | Macro composite/control; revision vintage matters, not physical site delay. |
| FRED / ALFRED | Rates, market and macro controls; vintage-aware values for supported series | Series-specific long history | Current FRED values may be revised. Use ALFRED real-time/vintage dates where available and preserve publication lag. |
| AWS Spot archive (Zenodo) | Cloud compute price proxy/cost normalization | May 2022–Sep 2026, ~5–7 hour average observation spacing per prior investigation; March–June 2026 gap | Reputable third-party archive with DOI/CC BY citation, but not official AWS availability vintages, utilization, fulfilled instance hours, all-cloud price index or actual exchange/trader data. Use in a modern-period auxiliary study only. |
| Ornn OCPI/benchmark | Potential rent/index and performance-per-dollar context | Provider product/history and entitlement must be verified | ICE H100/B200 contracts were only planned, no trading date confirmed in the team's correction. Published settlements were hypothetical per recorded decision; no listed forward curve. Ornn benchmarking repo can normalize observed GPU benchmark speed/cost, but not create rental prices. |
| Hyperliquid/other perps | Separate short-history market microstructure/perp funding study | No validated S3 archive or L4 feed in current repo | Not part of equity-first baseline. User considered 0xArchive, gRPC/native node, Bitquery, CoinAPI, etc.; exact historical fields, coverage, and access were not verified here. Wallet-level attribution is provider-specific and legally/data-terms sensitive. |
| Satellite/remote sensing | Physical site progress, corroboration | Sentinel/Landsat/VIIRS vary by site/date | Slow, cloudy/noisy; current 8-site probe is exploratory only. Not evidence of MW or company exposure without labels. |
| FMP / analyst consensus | Historical estimates only if true as-of vintages | Entitlement/coverage unknown | Do not use today's consensus as old expectations. No extra API key is presently required to continue pipeline QA; only source-specific credentials if a verified new source is selected. |

Detailed source links/terms and earlier observations are in `source-audit.md`; this table is the
working map, not a claim every listed source is fully downloaded, point-in-time, free for sharing,
or suitable as a predictor.

## Storage, ingestion, and language/compute layout

### Intended roles

```text
original SEC / public source files / vendor batches
                ↓
      Snowflake RAW + immutable stages  ← archival, shared research, PIT joins/features
                ↕ explicit batch export/import (not a live bridge)
      TigerData/Postgres/Timescale        ← operational/query layer, but low quota headroom
                ↓ read-only selected export after QA
      kdb+/q HDB on HiPerGator Blue       ← derived historical time-series research/replay
                ↓ deterministic cross-check
      reference strategy/backtest (typed arithmetic where justified; no engine implemented yet)
```

- **Snowflake:** current raw source archives, SEC document stage target, full EIA panel and feature
  research schemas. Snowflake is not the per-tick/live order path. Bootstrap schema has been run
  for prior AWS/table setup, but the new event-feature DDL remains unapplied and unpopulated. Don't
  create large warehouses or load wide data without a purpose/cost check.
- **TigerData:** shared Timescale/PostgreSQL raw row JSON, AWS price rows and compact EIA summaries;
  loader is manual, idempotent and uses batch/row hashes. Latest reported storage ~749.6 MiB vs
  observed 750 MiB, so freeze writes. Credits are not proof of changed quota. Never assume an
  available space limit just from plan/credit display.
- **kdb+/q:** intended time series/date partitioning, as-of joins, windows and research HDB. The
  new exporter only reads a selected Massive daily-bar batch from TigerData and checks its
  ingestion manifest. HPG HDB is a derived copy; Snowflake remains the canonical/archive backup.
  q isn't a replacement for raw SEC files or a data lake.
- **Python:** keep as ingestion/prototype/testing glue. No wholesale rewrite before measuring
  throughput. Current ingest default target is Snowflake; `--target both` only after verifying
  TigerData headroom.
- **OCaml:** optional for strongly typed signal/risk/accounting contracts if it materially helps.
  OCaml's strict type system does not make floats exact. Use integer-scaled values or Zarith
  rationals where exact arithmetic is required; define rounding/overflow/null/time rules.
- **C++ or Rust:** one low-level engine only if a benchmarked bottleneck demands it. Avoid parallel
  redundant implementations. Cross-check engine outputs against the deterministic reference.
- **Snowflake and TigerData are not live-synced.** Each manual ingest sends a batch to selected
  destinations. The explicit batch hashes, receipts and reconciliation are the bridge; no
  continuous replication/scheduler has been implemented.
- **OCI/AWS/Vultr/Render:** previously discussed possible cloud/orchestration options, not current
  strategy dependencies. No need to add them to the first event study. Use HiPerGator for data/model
  computation only after account/runtime/resource and rights checks. No production cloud trader has
  been established.
- **Laya/Jev:** user described an open-source typed Jev-like system, but repository context says
  model identity is not settled. Treat it as a candidate extractor/evaluator, not a known pre-trained
  model or an alpha engine. Train/fine-tune only after labels, rights, and holdout extraction QA exist.

### HiPerGator resources and kdb HDB current status

User-reported allocation: 250 NCUs, five GPUs and 2 TB Blue shared among participants, with roughly
5 of 50 users expected to actively use them. These are shared allocation figures, not a dedicated
reservation or proof of current available quota/QOS. Verify from HPG before submitting. GPUs are
not needed to start a daily event panel.

Committed scaffold: `hpc/kdb-timeseries/` contains a read-only TigerData batch exporter, exact
scaled-integer normalization, SHA/count manifest, synthetic fixture, q HDB build/smoke scripts,
Slurm jobs, README and six Python tests. Price integer scale is **1e-8 USD**, volume integer shares,
and bar date UTC. Function naming/docs were corrected in this handoff commit; use the exported
manifest as scale authority. Exporter tests passed locally; q scripts have not run under q.

Still required before HPG build:

1. Safe authenticated login and confirmed owner/account/allocation. Do not bypass SSH host-key
   validation. The prior direct SSH stopped at host-key trust; the existing Open OnDemand flow
   redirected to the UF/InCommon login page. User must handle MFA if prompted.
2. UF Research Computing confirmation that team's kdb+ license path may run on the cluster; the
   user said an appropriate license exists, but no license file or remote runtime was verified.
   Do not use Personal Edition on institutional/third-party cloud absent applicable permission.
3. Approved q executable path, Blue directory, `blue_quota`, scheduler partition/QOS and module
   setup. Keep license file outside Git and public/shared path; never copy it into docs.
4. Run synthetic smoke only. Then export 100 rows from a verified batch, transfer via approved
   channel, compare count/hash/date/symbol and input/output receipt; only then consider full panel.
5. Retain independent Snowflake/other archive copy and restore-test before discussing any deletion.
   No delete/drop is automated or approved.

### Implementation does not equal operational readiness

Do not say “kdb is running on HPG,” “database moved,” “clouds are connected,” or “latency improved.”
Current accurate description: the local/testable scaffold and documented architecture are committed;
remote q runtime validation/data migration are pending.

## Secrets, access, costs, and team use

- Earlier chat messages included Massive API key, Alpaca key, Snowflake password, TigerData URL
  and password. Treat all as exposed, even though `.env` is gitignored. Rotate/revoke and install
  new values privately. Do not copy secrets from chat history into a new computer or any new file.
- `.env`, `.venv`, raw `data/`, SEC zips, EIA cache, and output downloads are gitignored. Confirm
  `git status --short --ignored` and `make secrets` before commit. Never put keys in source, sample
  commands, logs, or notebooks.
- Teammates should get database IAM/query grants with their own identities; they should not share
  the owner's passwords, database connection URL containing auth, API key, cloud root user, or kdb
  license.
- The Massive loader has a sponsor-confirmation environment gate. It records a project assertion;
  it does not itself prove written terms. Verify license scope for shared cloud copies, team query,
  judge reruns and public repo artifacts before publishing any vendor data. Keep raw restricted
  data private; publish code/synthetic fixtures and retrieval instructions if redistribution is not
  permitted.
- The kdb export can incur TigerData reads but does not write rows. EIA-860M and generic source
  loader defaults are Snowflake-only due TigerData capacity. Explicitly avoid `--target both` or
  `--target tigerdata` until the actual quota is inspected and enough margin budgeted.
- The previous Databento screenshot indicated around $559 and 1.5 TB for a selected deep MBP-10
  request; that selection/entitlement was not verified. It is not universal. Do not spend credits
  for full-depth long history without a specified, measured execution test.

## Current research record: measured negatives and constraints

Read the full entries in `docs/decisions.md`; this list is a guide to the signposts:

- A broad market-series co-movement scan found mostly asset-family correlation, not an actionable
  causal/economic edge. FDR cannot repair dependence or bad node definitions.
- Five abstract directions were retained as structured records: physical progress imagery,
  threshold/cascade processes, promise survival hazard, options distributional mispricing (blocked
  on data entitlement), and protocol/risk formalization. They're research directions, not all
  strategies.
- Variant accounting found 135 comparisons, six survivors vs 5.5 expected by chance; a 50-test
  placebo had seven survivors vs 2.5 expected. Multiplicity and a weak autocorrelation null were
  real problems. Do not cite nominal hits alone.
- EIA generator panel: 6,407 generators; 69% had first promise revision, median five months; 36%
  of first revisions were one-month nudges; 44% were >=2-month moves. Revisions rise with age;
  revision is not automatically a failure or independent event.
- Stage A environmental features did not improve OOS hazard classification. Largest coefficients
  were missingness indicators, warning about missing-data process confounding.
- Stage A2/A3 relevant macro/supply factors also failed to improve holdout; the exposure interaction
  result wasn't robust. The repo decision is to stop fitting market-wide factors to that coarse
  delivery outcome; consider large revisions/cancellations or a different price-side mechanism.
- Public generator delay to a listed owner is limited by attribution (~6.2% large listed owner).
  Name matching can misattribute parent/utility/subsidiary. The crosswalk requires human evidence.
- 8-K tags: useful discovery surface only. A filing's form deadline isn't an event calendar; an
  earnings release could disclose earlier. Source dissemination must be audited.
- Compute families may be weakly related: the latest map reports median pairwise daily-change
  correlation around -0.01 for the compute price family, and no proven relation between compute
  prices and energised capacity. Provider price series may measure different products/regions/GPU
  tiers. Don't merge into a global spot index without methodology.
- OCPI / ICE H100/B200 future claim was corrected: ICE notice said planned contracts, no listing
  date set and regulatory process remained; described OCPI daily settlements are hypothetical in
  the cited report. Do not call it an active traded futures curve or use it as a futures hedge.
- Hyperliquid S3/archive, perps, and 0xArchive data depth are not verified in the current repo.
  Older messages about free API/L4 should not be promoted to facts. Treat separately with current
  official docs and downloaded sample/schema.

Negative results are useful project output. Do not erase them to make the narrative sound stronger.

## Backtesting / track rules that are non-negotiable

The frozen brief is authoritative:

- Systematic Trading submission due **2026-10-04 10:00 ET**; hacking ends 11:00 ET. Five-page
  quant note PDF maximum (11pt+ / standard margins) plus public GitHub repository.
- Most recent **20% of history or latest two years, whichever shorter** is a sealed OOS set. Owner
  opens once at end and reports regardless of outcome. It is not a “nice to have”; never use it to
  choose an event type, thresholds, universe, signs, horizon, cost assumptions, features or models.
- Hypothesis before results. Every number net of cost; state bps/trade and justify; show doubled
  cost. Count all variants. Show parameter plateau. At least one bar lag; never same bar close
  signal/fill. Point-in-time universe or disclose survivorship bias. Report IS/OOS separately,
  turnover, max drawdown and equity curve.
- Result files under `results/` are generated from code; note numbers must be traceable to these
  results and match the code. Code and note must rerun consistently or performance criterion is
  capped.
- Chronological validation and event grouping: overlapping labels/common shocks cannot be counted
  as independent; purge or group where windows overlap.
- A regime analysis can enrich development research; it does not supplant chronological test.
- Performance is not the only score: economic foundation, distinctiveness, risk, liquidity/capital,
  analytical evidence. “We have GPUs / many APIs” earns no points.

## First strategy-ready feature data contract

The table contract is in `strategy-feature-contract.md` and `src/snowflake/bootstrap.sql`.
The minimum conceptual layout:

1. **Raw observation:** immutable accession/document/batch ID, URL, byte hash, source times,
   retrieved time, original text/package, license/status.
2. **Reviewed operational fact:** CIK/security ID, project/counterparty/segment, metric and exact
   unit/scope/target period, text and numeric values, prior comparable value, original source span,
   extractor/version, human review and confidence.
3. **Availability:** filed time, EDGAR accepted time, earliest verified public time, conservative
   actionable `available_at`, decision timestamp, method and uncertainty flag—all timezone aware.
   Do not treat period end, filing date, download time or vendor tag time as interchangeable.
4. **Expectation:** prior management statement for same scope/target period (clearly called
   `management_guidance`) or true historical consensus vintage if obtained. No lookahead.
5. **Derived candidate features:** absolute/% revision, past-only deviation from that firm's
   historical revisions, robust scale and `n_prior`; event-cluster count; verified exposure. Keep
   raw and derived values together; missing/ambiguous gets explicit reason and often abstain.
6. **Market-state features:** trailing split/dividend-consistent 1/5/20-day returns, prior beta,
   realized volatility, dollar volume, missing bar and action flags, SPY/sector controls. All from
   pinned manifests and strictly before event decision.
7. **Outcome labels, separate table:** next eligible entry time, forward 1/2/5/10/20 session raw,
   market/sector returns, abnormal return, assumed/observed costs, net return, label end/time.
   Never expose these fields to feature-generation or fit features from future information.
8. **Run manifest:** code commit, feature/strategy config version, provider batch hashes, universe
   and date split identity, environment, seed, event/exclusion/cluster counts, units and costs.

Use `NORMALIZED.OPERATIONAL_FACTS` then
`FEATURES.EQUITY_EVENT_FEATURES` and `FEATURES.EQUITY_EVENT_LABELS` as proposed Snowflake table
names. DDL on disk isn't a cloud table. Apply only after source facts and loader tests are ready;
don't create an empty table and report the pipeline done.

## What should be built next (ordered, with stop conditions)

### A. Establish the ground truth of the current cloud state

1. Pull latest main. Check the old SEC archive process is not still active before launching another
   fetch. A new computer may not inherit its shell/session; check Snowflake first.
2. Query Snowflake `VECTOR_RESEARCH.RAW.SEC_FILING_PACKAGE_MANIFESTS` and
   `RAW.SEC_FILING_DOCUMENTS` for accession count, doc count, distinct tickers, first/last dates,
   packages whose docs count does not equal manifest, missing stage objects, package/doc hashes.
   Compare against the selected accession list/register. A script log of many success lines is not
   full reconciliation.
3. Check Snowflake EIA manifest row/vintage coverage and TigerData database/table size read-only.
   Do not append to TigerData.
4. Inventory source IDs/batch hashes/row counts in both platforms. Never infer cloud state from
   an earlier assistant message; cite a fresh query receipt with retrieval timestamp.
5. If SEC run failed partway, make the loader idempotent at `(accession, package_sha256)` and
   rerun only verified missing accessions; retain prior versions rather than overwrite history.

**Stop if:** credentials are unavailable, a raw package cannot be verified, storage/rights are
unclear, or duplicate fetches risk uncontrolled provider load. Ask for user action only for login,
MFA or new credentials; don't ask for another API key unless a selected source genuinely needs one.

### B. Finish an honest event panel before a strategy

1. Use four candidate firms (PWR, ETN, EME, DLR) and each issuer's official filing/exhibit set.
   Pull earnings press releases/investor materials too where they precede 8-K; SEC alone can be
   late. Preserve all original exhibits.
2. Resolve CIK/ticker/security ID through time and verify corporate actions/listing history.
3. For each numeric field, track metric definition, segment, unit/currency, target period and
   entity/project. Do not combine RPO, backlog, unapproved change orders, capex and delivery dates.
4. Parse both the prior promise and changed promise. Use original source spans; human-review all
   events entering first test. Store firm-specific disclosure data in the row, not only an LLM
   summary.
5. Establish a same-scope earlier expectation and event cluster. Guidance is not analyst
   consensus. If a prior expectation cannot be reconstructed, mark no usable surprise and exclude
   or run a separately identified descriptive subset.
6. Resolve first public time, earliest SEC acceptance and potential press release. For uncertain
   timestamp apply a clear conservative rule (e.g. after-close/next session) and sensitivity; don't
   use the date-only 23:59 timestamp as a precise intraday time.
7. Report coverage per ticker/metric/year, matched acceptance fraction, independent shock/event
   clusters, missing/unreviewed fraction, definitions changed, counts excluded and reasons. If
   sample too small/clustered, state that and do not backtest it as thousands of independent events.

**Stop if:** only current restated facts exist, no prior comparable public expectation exists, the
event's economic exposure is not defensible, or a one-company/one-shock result drives the finding.

### C. Pin the daily market data and controls

1. Use the verified Massive full bar batch, not a PWR canary. Validate trading-day coverage by
   ticker, duplicates, missing intervals, corporate actions and symbol events.
2. Store/pin SPY total return and proper sector benchmarks (e.g. XLI for industrial/equipment,
   XLRE for data-center REIT) from a licensed source. Avoid live `yfinance` calls inside a
   reproducible test. If benchmark data can't be retained/licensed, clearly downgrade to an
   exploratory SPY-only result and don't report it as sector adjusted.
3. Daily bars first. Do not acquire deep MBP/L2/L3 history now. L1/trades event windows are the
   next market-data layer only after signal survives simple daily baseline.
4. Use an availability timestamp → next eligible trade/reference price rule. Corporate action
   and dividends must be handled consistently. Do not claim a closing-price fill if you could not
   act at that close.
5. Log manifests for every input: source, endpoint/schema, exact requested and actual ranges,
   retrieved and publication/available times, license, counts, file/batch checksum, exclusions.

**Stop if:** point-in-time security identity or return adjustment can't be reconstructed enough
to trust the labels, or a selected vendor dataset can't be used/shared under terms.

### D. Build/fill the feature schema and deterministic tests

1. Implement code under an owned/claimed feature component or coordinate with the current owner
   before touching another agent's `src/event`, `scripts/`, `tests/` or `results/` paths.
2. Create source-backed observation/fact records separately from feature table and label table. Keep
   exact numeric source strings; `Decimal`/integer scale in Python boundary, `NUMBER`/scaled
   integers in SQL/q. Never parse currency via float then back to decimal.
3. Past-only normalizer: compute revisions vs same-firm/metric history using only earlier
   `available_at`; record baseline sample count; avoid fake z-scores if no history/zero MAD.
4. Add golden tests for time zones, after-close/holiday, no acceptance, source date without time,
   earlier PR than SEC, duplicate accession, amendment, missing prior, denominator zero/negative,
   unit/scope mismatch, acquisition/segment break, split/dividend, missing bar, label horizon past
   data end, event-cluster dependence and OOS fence. Test an explicit look-ahead adversary: a future
   record must not enter a feature.
5. Validate `available_at <= decision_at`, expectation available by decision, no label fields in
   features, no overlapping label leaks, and feature row hash/idempotence. Run schemas against
   Snowflake types before creating any new tables.
6. Compare a deterministic Python baseline with q only for the actual time-series workload. Later
   implement typed strategy/accounting in OCaml/C++ only after output contracts exist. Unit test and
   cross-check each port on exact small fixtures.

### E. Only after A–D, preregister and test a simple candidate

In a named thesis file, record: mechanism, payer/counterparty, why mispricing can persist, exact
event/factor, sign, entry, holding period, exit/abstention, universe criteria, baseline, benchmark,
costs, risk/size cap, falsifier, independent sample count, variant grid and data split. Use
development-only chronological folds. Evaluate the no-signal/control model first; do not fish for
best horizon or company. Use cluster-aware permutation/placebo or matched controls appropriate to
the mechanism; control the declared family of tests.

Then quantify costs: bid/ask, slippage, brokerage/fees, borrow availability/rate, financing and
turnover. Stress doubled costs and event delays. Include liquidity/capacity from actual volume and
spreads; do not label instruments categorically liquid. Size/abstain based on uncertainty, exposure,
drawdown, correlation/joint losses. Keep variant plateau and risk output. Never open official OOS
until the designated owner confirms all rules frozen.

### F. Scale infrastructure only when a measured bottleneck demands it

- After the input rows/feature view are defined, apply appropriate Snowflake schemas and store
  batches/receipts. Snowflake compute is for batch joins/research, not a presumed speed advantage
  over local/q. If the data set is small (the current daily panel is small), test runtime before
  using extra services.
- Run the kdb synthetic smoke on HPG only when safe HPG access and license/runtime confirmed. Then
  canary export. The system is not a TigerData reduction until HDB is restored/verified **and** an
  exact selected redundant TigerData batch is deliberately deleted with authorization. No such
  deletion is in scope or implemented.
- Use HiPerGator CPU for parsing/features/backtests where available; use GPU only for a named
  extraction/inference/optimization workload with measurement and human-verified labels. Avoid
  expensive finetune on a few event labels.
- kdb+/q is not TigerGraph: TigerData refers here to a managed PostgreSQL/Timescale database. The
  GitHub repo has no graph database deployment in this data lane.
- Keep experimental quantum/HFT/Hyperliquid/imagery pipelines separately optional; same frozen
  event/feature/result contracts, distinct README/owner, no forked strategy logic.

## Git, testing, memory and handoff etiquette

### On a fresh computer

```sh
git clone https://github.com/sebastbernal2-ship-it/gqh-delivery-gap.git
cd gqh-delivery-gap
make sync
git status --short --branch
```

If already cloned, prefer `make sync` before edits. Then `make overlaps` to see pushed path claims.
Read `AGENTS.md`. Repo rules: one writer per path, owners in `OWNERS.md`; keep code component
README, claim new paths before implementation, rebase before commit, results generated from code,
never commit credentials/raw licensed data/absolute local paths/anything under `data/`.

### Validation state at snapshot

- Last dedicated local kdb exporter run: `python3 -m unittest discover -s
  hpc/kdb-timeseries/tests -v` — **6/6 passed**.
- `python3 -m py_compile` of central-ingestion and kdb exporter/fixture scripts passed.
- `bash -n` on HDB builder and Slurm scripts passed.
- `git diff --check`, secret scanner and `scripts/check_owners.py` passed at prior commit.
- q runtime not installed locally; q scripts not validated on HPG.
- Full `make test` failed because current `Makefile` names missing tests/scripts, including
  `tests/test_strategy_contracts.py`, `tests/test_market_runner.py`, `tests/test_market_control_panel.py`,
  `tests/test_tradeability_panel.py`, `tests/test_crosswalk_review.py`, `tests/test_pdf_renderer.py`,
  `tests/test_strategy_builders.py`, `tests/test_strategy_sources.py`, `tests/test_strategy_e2e.py`,
  `tests/test_run_manifest.py`, `tests/test_controls_metrics.py`, `tests/test_strategy_identification.py`,
  `scripts/check_strategy_ledger.py`, `scripts/build_run_manifest.py`,
  `scripts/report_promotion_gate.py`, `scripts/check_pdf_renderer.py`. Treat as current main
  integration/gate debt, not a failure of the kdb exporter.
- `make check` failed in `check_structure.py`: `.vscode` unknown area, `src/factors/` and
  `src/models/` missing README. `scripts/check_paths.py` also flags missing references from the
  Makefile listed above. These are latest-main repo/gate issues; don't modify teammate-owned shell
  or component files without checking `OWNERS.md` and claim/coordination.
- `make overlaps` last said no branches in flight; re-run each session.
- `make sync` says `hippo` is not installed on this workstation and tells us to read
  `memory/SHARED.md`. `make remember` fails with `hippo: command not found`. Do not hand-edit
  generated `memory/SHARED.md` or misuse `hippo import --file memory/shared.json` (it can split the
  JSON into fragments). Durable shared knowledge in this turn is published in this handoff and
  thinking log; if a later computer has Hippo, follow `docs/memory.md` and the official memory
  workflow to add a concise tagged memory and `make share`.

### Commit/push latest state

This handoff itself must be added to the Vishnu handoff index and thinking history, checked,
committed and pushed. Stage only owned paths—do not use `git add -A` if other work may be present.
Use `git fetch origin`, `git rebase origin/main` (stash only if needed), `make overlaps`, relevant
tests, `make secrets`, `git diff --cached --check`, then commit and push. Re-check `git status` and
record exact commit in the final chat reply. Do not claim repo gate passes when it doesn't.

## Open questions, explicitly not answered by this handoff

- Does a PWR/ETN/EME/DLR delivery-related signal predict a tradable residual return after costs?
- Is user priority the narrowed equity mechanism or should next development test the newly mapped
  delivery-to-compute-rental relation? Ask/record this only if it changes the first model materially;
  until then keep the equity feature readiness on track while the executed-rental access is audited.
- Can Management guidance facts be normalized comparably for four firms? Is there enough
  independent event count after clustering?
- Which sector/benchmark history can be lawfully stored and deterministically rerun with no extra
  cost? Massive entitlement is product-specific; free yfinance is not a substitute license proof.
- Is there licensed, historical, published-at-time compute rental data versus AWS Spot list/history?
- Can SEC archive load finish end-to-end? What are missing accession/exhibit sets and staged bytes?
- Does Snowflake user's team role permit read access to raw SEC archive and stage? Each teammate's
  login/grants must be checked separately.
- Is HiPerGator kdb+ runtime covered by an approved license and allowed under the team allocation?
- Which code owner will claim/create a point-in-time feature builder/backtest component, and which
  inputs/results will it write? Coordinate before editing `scripts/`, `tests/`, `results/` or another
  component.
- Which work is intended for the imminent hackathon submission versus longer multi-month testing?
  A “few months of unit testing” cannot be a prerequisite to the next-day competition deliverable;
  distinguish engineering confidence from alpha validation and meet the published deadline.

If any one of these remains unresolved, do not fill the gap with inference. Put a marked `unknown`,
log a decision/question with an owner, and keep the strategy from overstating the evidence.
