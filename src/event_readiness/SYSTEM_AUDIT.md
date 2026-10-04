# Cross-computer continuation audit — 2026-10-03

Scope: source history and implementation at `6da2e4b`, rebased to `8359a29` before delivery, following Vishnu's
[ultimate handoff](../../docs/inbox/vishnu-2026-10-03/ultimate-handoff.md).
The user explicitly pivoted away from the factor-model branch and authorized research,
implementation, detailed documentation, commit and push. The two existing worktrees contained
other work and were preserved. This continuation uses a separate branch and a new owned component.

This is a code/data-contract audit and engineering delivery. No strategy performance was rerun,
no sealed return window was opened, no live orders were placed, and no cloud completion is claimed.
The shared thesis ledger is empty. Do not promote this audit into a strategy claim.

## 1. The system we actually have

| Layer | Existing implementation | What the evidence supports | Missing seam |
|---|---|---|---|
| Research governance | brief, thesis/decision/variant ledgers, chain and idea graph, window code | Detailed economic rationale and declared research history | Some current prose disagrees with executable gates; split ownership and promotion remain open |
| Raw ingress | `src/central_ingest/`, AWS loader, EDGAR and EIA clients | Manual loaders, hashes, selected-batch manifests, reported cloud receipts | Fresh cloud reconciliation; no shared scheduler or continuous replication |
| Evidence extraction | filings register and XBRL facts | Accession-linked discovery and reported balances | Original source spans, identical-period expectations, reviewed economic exposure, first-public clocks |
| Historical market data | Massive batch package, separate actions; older yfinance callers | Reported five-symbol daily landing | Retained/pinned sector controls, verified adjustment conventions and historical security identity |
| Mechanism research | EIA panel, delivery hazard, imagery, company event studies, scans | Useful measurements and recorded negative/exploratory findings | Several implementation defects prevent strong causal/forecast conclusions; relation is not tradable edge |
| Event interface (this change) | archive reconciliation plus reviewed guidance feature builder | Tested integrity, decimal, timing, eligibility and exclusion contracts | Real reviewed input population, cloud receipts and approved market/label bridge |
| Time-series/HPC | kdb exporter and q/Slurm scaffold | Six local Python exporter tests pass | q runtime, license/allocation and remote HDB restore validation unverified |
| Probabilistic research | Python council, synthetic calibration, C++ council, vendored JevLike | Recorded C++ HiPerGator synthetic smoke and local model interfaces | Financial labels, predictive benefit, serving latency and full JevLike parity receipts |
| Quantum | bounded QCBM experiments in council lane | Optional simulator research, separate from source/economic validity | No demonstrated quantum advantage, no basis to require quantum in the strategy |
| Live research | public perpetual tape collector | Collection code, protocol and previously reported tape activity | This computer cannot verify remote process; book history, synchronized observations and net economics remain open |

The correct integration direction is source bytes → reviewed fact → comparable prior expectation →
economic exposure → decision-time features → market/label contract → falsifiable study. Infrastructure
cannot supply a missing arrow. Features should be swappable inputs to the existing council only after
meaningful labels exist; the council should not become the data cleaning or evidence-certification layer.

## 2. Commit history and how the reasoning changed

These are selected transition commits, read with their current source and downstream records,
not a claim that every historical line was independently validated.

| Commit(s) | Change | Continuation implication |
|---|---|---|
| `649ac94`, `1437a9e` | EDGAR timestamp register and operational XBRL measurements | Reuse identifiers/clocks; do not confuse balances with forward promises |
| `b66e008`, `03aa98b` | EIA promise comparison and project-to-firm join | Physical schedule evidence exists; public-owner attribution is weak and name matching is insufficient |
| `765e705`, `d9cfdd5` | Broader obligation event study and aggregate pair strategy | Preserve the negative record; a new guidance family requires a genuinely different measurement and hypothesis |
| `48aefc7`, `8b44637`, `435fcd0` | Declared scans, two windows/firewall, compute archive study | AWS provider prices are their own object; use existing containment fences, do not borrow old-equity sample length |
| `19190b0`, `cae2bad`, `781554d`, `fe6d111`, `2207e4d`, `527ef92` | Council, parallel inference, C++ and JevLike integration | Synthetic systems progress is separate from an economically validated predictor |
| `1599679`, `91ed86f`, `3c3bc80` | Shared cloud loaders, receipts and operator handoff | Exact source/batch selection is essential; credentials and processes do not travel in Git |
| `709a955`, `3a3a49a`, `2dae0c5` | Imagery work, integration repairs and return to last-good main | There is actual branch/gate debt; do not repair missing files with placeholders or sweep unrelated changes into a commit |
| `96b3eb6`, `a4f1a6c`, `dc81400` | Environmental, bottleneck and exposure-interaction hazard tests | Reported failures are not a trading backtest; inspect time alignment and preprocessing before interpreting coefficients |
| `09b6385`, `e417d0d`, `00dca8f` | Node/edge map, relation-to-edge gates and continuity page | The team still lacks a surviving edge; handoff equity preference coexists with other research candidates |
| `999ae6d`, `9d3b876` | Feature contract and comprehensive cross-machine handoff | Archive reconciliation and reviewed event features are the next concrete data work |
| `6da2e4b` | Large-revision/suspected-exit outcomes | This supersedes “tail redefinition never tried” text in older maps, but inherits panel defects below |
| `9d2f583`, `ca49ee7`, `8359a29` | JevLike parity module invocation fix; Hippo task packet; merge | Integrated during continuation. The invocation fix is not proof of a completed parity run; Hippo is absent here, so generated memory was not hand-edited |

The continuity document names a separate `close-all-gaps-20261003` branch. It was not present in
this checkout's fetched remote refs at audit time. Its mentioned strategy components therefore
cannot be treated as installed on main. No unverified branch was merged.

## 3. Freshly verified local state versus inherited cloud claims

Local CSV metadata checks reproduced 776 filing-register rows across PWR/ETN/EME/DLR and 130
obligation facts (PWR 115, ETN 15), with 102 populated acceptance fields. The obligation schema
contains no human-review field, original document SHA/span, permanent security ID, target-period
expectation contract, or reviewed exposure link. These observations are coverage QA, not an OOS
return analysis. They explain why blindly converting the old panel would manufacture eligibility.

The cloud counts in the original handoff remain **reported historical receipts**. This computer's
project environment and standard Snowflake configuration locations had no configured connection;
Snowflake/SnowSQL/Tiger CLIs were absent. No fresh warehouse query, stage download, database-size
measurement or remote-job check occurred. The user was asked for an existing profile/location,
without requesting secret values. Local implementation continued independently.

TigerData stays read-only under the handoff's quota constraint. An old database-byte count does
not establish today's headroom, and database size alone does not establish the contracted limit.
The collector added here uses only Snowflake SELECT/LIST and never creates a table or warehouse.

## 4. Material audit findings

### A. SEC package manifests can outlive their original stage bytes — confirmed in code

`src/central_ingest/sec_archive.py` uses `(ACCESSION, PACKAGE_SHA256)` for manifest versions, but
`save_and_upload()` constructs a stage filename from accession alone and uses `OVERWRITE=TRUE`.
A new version can overwrite bytes referenced by an old manifest. ZIP entries also receive creation
times by default, so repeated packaging can change the ZIP digest even if document contents match.
Manifest insertion precedes document completion, and the loop has no reconciled-missing-only mode.
A log line or a successful MERGE does not prove complete retained content.

**This change:** detects reused mutable paths, duplicate manifest/document keys, count/membership
mismatches, missing stage objects, mismatched ZIP and document bytes. Metadata-only status cannot
become archive-ready. It does not patch the other owner's loader or mutate cloud state.

**Required repair before another archive batch:** stable archive member order/timestamps; original
bytes retained; accession plus content-hash stage paths; verify upload/download outcomes; mark a
package complete only after all document rows and bytes reconcile; retry only reconciled missing
accessions after checking the existing operator. Keep old versions and never delete to repair.
A hash-addressed path is necessary even where a provider's overwrite flag behaves differently.

Snowflake's [PUT documentation](https://docs.snowflake.com/en/sql-reference/sql/put) explains overwrite
behavior and notes that query execution success is not proof of successful file transfer. Its
[LIST documentation](https://docs.snowflake.com/en/sql-reference/sql/list) states that internal-stage
encryption can make listed MD5 differ from the original file. Therefore the verifier checks actual
retrieved bytes with SHA256 instead of comparing an incompatible stage checksum.

### B. Delivery panel month arithmetic is wrong — reproduced without data

At the audited commit, `month_index()` uses `year*12 + month`, but `shift_month()` converts back
as though month were zero-based. A synthetic AST-isolated probe returned:

| Input | Actual | Correct |
|---|---|---|
| January 2020 shifted -2 | December 2019 | November 2019 |
| January 2020 shifted -1 | January 2020 | December 2019 |
| January 2020 shifted 0 | February 2020 | January 2020 |
| January 2020 shifted +1 | March 2020 | February 2020 |

This affects both lag selection and the row-generation loop. It can expose contemporaneous values
where the comment promises a lag, and skip project months. The tail/exit results introduced by
`6da2e4b` inherit this machinery. Preserve the reported negative findings as history, but do not
claim they establish that public factors categorically cannot predict delivery. The component
owner must correct and regenerate development-only panels before that stronger conclusion.

### C. Hazard preprocessing and null do not identify the claimed comparison — code inspection

`run_delivery_model.build()` estimates technology medians using all input rows before applying its
2020 split. Standardizing only on training rows later does not undo this imputation leakage.
“Controls only” zeros main factor columns but retains missing flags and, when enabled, factor
interactions. The comparison therefore is not a clean controls-only ablation. A within-month
shuffle of a national factor cannot perturb a factor that is constant within each month; interaction
and missingness blocks also need joint treatment. Row bootstrap intervals ignore repeated-project
and shared-time dependence. No corrected results were computed here.

The new large-revision target also conditions on the *first* revision: a project that first nudges
and later slips six months is removed at the nudge. It is not an estimator of time to any eventual
six-month slip. “Suspected exit” uses disappearance from planned records, not independently verified
cancellation; commissioning, sheet coverage and missing vintages are rival explanations. These are
measurement questions to resolve before trying a larger model.

### D. Raw period/vintage dates are not publication timestamps — confirmed boundary problem

`src/central_ingest/eia860m.py:record_rows()` sets availability to month-end of the data vintage.
That only says the observation period ended. The official [EIA-860M page](https://www.eia.gov/electricity/data/eia860m/)
separates release date from reference month, labels the inventory preliminary and notes revisions.
At retrieval it listed August 2026 data with a September 24 release. August month-end is therefore
not a conservative public-availability timestamp for that vintage. Historical release evidence or
an explicitly later availability bound is required for features. No cloud dates were silently
rewritten in this change.

### E. The XBRL/event seam is descriptive, not a reviewed expectation panel — confirmed

`src/edgar/xbrl.py:revisions()` groups by concept/unit and sorts by period end then filing date.
That is useful exploratory accounting history, but repeated amended facts can become adjacent and
current-payload/restated observations are not necessarily the original live vintage. The function's
key does not itself include issuer; callers must isolate issuers to prevent cross-company mixing.
An earlier period's backlog balance is not a same-target forecast. The existing event runner calls
live yfinance and lacks a pinned common-session/action manifest.

**This change:** explicit issuer/security/definition/scope/target keys, distinct amended IDs, an
explicit prior management-guidance link, original source-byte spans and hashes, reviewed exposure,
and immutable feature identities. It refuses to auto-upgrade the old RPO panel into guidance.

The [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
says the XBRL APIs aggregate non-custom, entity-wide facts across submissions. Consequently,
company-specific segment guidance and contractual timing still need original filings/exhibits;
Company Facts is a discovery surface, not a complete extractor for the proposed study.

### F. Holding-period and holdout conventions need owner reconciliation — inspected/reproduced

`run_capacity_strategy.py` hardcodes 24 sealed months while its comment says “shorter of one fifth
or two years.” The declared 111-month study has a fifth shorter than 24 months. Keeping a larger
set closed is conservative, but that is not the same as implementing the stated calculation.
Do not shrink/reopen a previously sealed region to repair prose after research has occurred.

`leg_return()` applies indices from a global date array to an already filtered per-name window;
the date basis must be checked and replaced by explicit timestamp joins before trusting returns.
The new component does not call that strategy. It retains the existing development fence solely
for containment, and has no sealed override. A named owner still must reconcile the final split
and report the already-disclosed design-time exposure honestly.

### G. Gate claims in prose are stale on current main — freshly executed

`make test` passes the first 13 listed test programs, then stops because
the missing `test_strategy_contracts.py` test program does not exist. `make check` reports the existing `.vscode`
area and missing READMEs under `src/factors/` and `src/models/`. The new component has its own README.
The continuity statement “38 test suites pass” does not describe this checked-out executable gate.
Do not recreate empty test files to turn a missing implementation into a green result. The owner
must resolve the intended unlanded branch versus the current Makefile/repo structure.

## 5. Economic interpretation: one narrower candidate, still unapproved

The useful next hypothesis is **a same-target guidance/schedule revision by a party with evidenced,
concentrated contractual exposure**, separated from ordinary earnings, orders and sector moves.
The key unresolved question is who absorbs the delay cost or revenue-timing change, under which
contract, and whether that information has already reached investors. The present builder measures
only the revision; it asserts neither a price sign nor underreaction.

The source families need different definitions:

- Quanta's [Q2 2025 release](https://investors.quantaservices.com/news-events/press-releases/detail/379/quanta-services-reports-second-quarter-2025-results)
  distinguishes non-GAAP backlog from RPO and points to reconciliations/guidance materials. Keep
  those metrics and any acquisition/segment changes separate.
- Eaton's [Q1 2025 materials](https://www.eaton.com/content/dam/eaton/company/investor-relations/quarterly-earnings/filings/2025/q1/1Q-2025-earnings-complete.pdf)
  describe rolling-order comparisons including a large multi-year order adjustment. That denominator
  and comparison basis cannot be pooled with backlog dollars or used as a delivery-duration measure.
- EMCOR's [Q2 2025 filing](https://www.sec.gov/Archives/edgar/data/105634/000010563425000046/eme-20250630.htm)
  reports RPO and acquisition accounting. A larger balance can reflect business perimeter, not slower
  delivery. Scope continuity must be sourced before comparing revisions.
- Digital Realty's [Q1 2025 release](https://investor.digitalrealty.com/news-releases/news-release-details/digital-realty-reports-first-quarter-2025-results)
  measures signed-but-not-commenced leases in annualized GAAP base rent at its share, and separately
  describes contractual commencement lag. Neither is interchangeable with MW or contractor RPO.

These public examples were read for schema semantics; no return response, model fit or recent-period
signal was measured. They must not become historical training observations merely because links
exist. Candidate economic falsifiers remain: ordinary demand/earnings explain the effect; a change
is fulfillment rather than delay; acquisition changes the perimeter; prior expectations were already
obsolete; exposure is too diluted; or costs exceed the response.

Do not infer a universal impossibility from the prior nulls. Conversely, repairing code cannot be
assumed to produce an edge. The measured quantities and their uncertainty must survive the same
predeclared baseline and cost tests after repairs.

## 6. Why this implementation, and what it deliberately does not duplicate

The handoff orders cloud reconciliation before feature population. Cloud access is blocked on this
computer, so the independent deliverable is an executable verifier and feature contract, exercised on
synthetic evidence. It neither fabricates successful cloud reconciliation nor bypasses it by
training on the old unreviewed CSV. Step C market/sector controls remains a real dependency for labels.

The new code is standard-library only, with an optional Snowflake connector at the I/O boundary.
No new databases, model stacks, schedulers, q rewrite, GPU queue or graph deployment is needed for
this data volume. Raw source stores remain authoritative; the report files are reproducible artifacts.
Feature and label separation is structural: the builder has no forward-return input or label output.
A future label builder must consume pinned price/actions/calendar manifests and own its own tests.

## 7. Ordered continuation, with concrete acceptance criteria

1. **Authenticated originating host:** SELECT/LIST metadata, retain query IDs/times, verify the SEC
   process state and database headroom. Reconcile every selected accession/version against downloaded
   bytes. Do not claim success on counts alone.
2. **Archive owner:** repair immutable package storage and incomplete-load recovery before rerunning.
   Keep all accessible earlier versions; investigate overwritten bytes rather than replacing history.
3. **Research/data reviewers:** populate one clearly named management-guidance family in development
   data, with a prior same-target statement, exact quote/scale, source clock, security/scope identity,
   exposure evidence and cluster. The new builder emits all exclusions. Count independent clusters,
   not documents. No silent substitutions for missing EME/DLR coverage.
4. **Market owner:** pin licensed daily firm/SPY/sector batches, exchange calendar, actions and security
   identities. Test missing sessions, split/dividend treatment and data-end horizons. Do not select
   the benchmark or horizon by the best outcome.
5. **Strategy owner:** approve a thesis, cost/borrow/capacity assumptions, one primary outcome and
   development folds. Build labels separately, purge overlapping label periods and related clusters,
   freeze the comparison family and report negative results. Sealed opening remains separately owned.
6. **Component owners:** address the audited calendar/preprocessing/market-index/gate defects with
   targeted regressions before regenerating affected results. Preserve the original record as
   superseded rather than rewriting it.
7. **Only after an identified bottleneck:** use HiPerGator/q/council/quantum experiments against the
   same evidence/feature/label contract and a measured classical baseline.
