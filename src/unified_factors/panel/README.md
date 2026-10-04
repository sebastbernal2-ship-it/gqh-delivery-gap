# Daily factor panel preparation

This prepares the daily input panel for the unified exposure model. Development uses 2016-01-04 through
2024-10-02. It does not fit or tune a model, and it never exports or parses labels after that date.

The warehouse inventory contains 2,703 XNYS sessions through 2026-10-02. The latest fifth is 541 sessions
(rounding up); the latest two calendar years, 2024-10-03 through 2026-10-02, are 501 sessions. The contest
rule sets aside whichever is shorter, so this factor-panel study reserves those latest two years as its
separate sealed holdout. Only dates/counts from the aggregate inventory were used to set this boundary; the
holdout's daily market values are excluded from the pinned SQL and parser, and have not been inspected.

## Inputs found and selected

Snowflake currently holds two pinned Massive batch versions of 2,703 daily bars for each of PWR, ETN, EME,
DLR and SPY, plus dividends and split-coverage receipts. The development export query selects those exact
batch hashes and cuts source sessions at 2024-10-02. The separate 20-row PWR canary is excluded. The output
limit allows for the 22,020 paired development bars plus corporate-action records.

Four public daily archives are retrieved from the official [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html):
FF3, FF5, momentum and value-weighted daily 12-industry portfolios. The original checked snapshot parsed
with exactly 1,699 XNYS sessions through 2022-09-30. When building the expanded development window, the same
hash-pinned archives are bounded to the 2,202 XNYS sessions through 2024-10-02; no later factor or return
rows are parsed. Return values are percentages in the source and are divided by 100 once. The factor files
are separate: FF3 and FF5 keep their distinct SMB
series; Mkt-RF and RF must match exactly before they can be compared. MOM is an additional separate series.
The captured retrieval receipt is `french-snapshot-2026-10-03.json`; its four archive hashes are part of
the reproducibility record. This proves what was parsed for this research run, not the historical publication
time or the exact values available to a trader in 2016–2024.

The official library uses CRSP FIZ through December 2024 and CIZ beginning with its January 2025 release,
with documented dividend-timing differences. Its histories are reconstructed and revisable. A snapshot
retrieved today therefore does not establish the factor values or revised stock bars that a researcher could
have downloaded on each historical day. Source retrieval dates, filenames and SHA-256 hashes are recorded.
The output is explicitly `retrospective_only` and the normal development runner rejects that role.

## Price and return handling

The Massive historical bars are split-adjusted by default, not dividend-adjusted. This adapter therefore
requires paired adjusted/unadjusted price batches, checks that OHLC agrees on every date and asset, and
requires a per-asset no-split receipt covering the entire selected history. It rejects split events until a
reviewed split-aware total-return implementation exists. A missing date is an error, not a silent intersection.

Use the XNYS exchange calendar for sessions and official session close (including early closes). Massive daily
bar timestamps are bucket markers at midnight America/New_York; they do not assert when the completed bar
first became downloadable. Cash distributions are applied on ex-date as `(close[t] + cash dividend[t]) /
close[t-1] - 1`, with USD, unique dividend IDs and explicit session validation. This approximates simple total
return with dividend cash credited on ex-date; it does not model actual reinvestment, tax, withholding, or
financing. RF is subtracted once from stock returns to produce excess returns. Published Mkt-RF/style series
are not reduced by RF again. Industry portfolio returns are separately expressed above RF as comparison
controls; they are not equity-sector ETF trade histories.

Five surviving tickers do not make a historical point-in-time universe. Report the fixed basket and possible
survivorship bias. Broadening coverage requires historical security identity, delisting returns and licensed
universe membership, not simply adding current tickers.

## Privacy-gated input export

`development_export.sql` exports raw historical vendor bars and dividend records for the named five tickers,
inside the development date bound. A security review blocked the proposed Actions artifact export because
raw vendor data would leave Snowflake and artifact storage rights were not established. The approved local
route uses the checked-in pinned query and writes outside the repository with mode 0600; it refuses to
overwrite and errors if the result exceeds its row cap. Do not put the export or French archives in Git. The
exporter accepts standard `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, and `SNOWFLAKE_WAREHOUSE` settings with
password, key-pair, OAuth token, or authenticator-based local credentials. Configure these through a private
local secret store or shell, not in chat or a tracked file.

```sh
python -m pip install -r src/unified_factors/panel/requirements-local.txt
PYTHONPATH=src python -m unified_factors.panel.export_local \
  --output /private/tmp/development-export.csv
```

The export limit defaults to 30,000 rows and is fetched with a one-row overflow check, so an oversized
result is never silently truncated. Do not use the Actions artifact workflow for raw records unless that
route and its vendor terms are explicitly approved.

## Local execution receipt (2026-10-03)

The pinned local query completed and the builder created a private development panel. The raw export contains
22,189 records: 22,020 adjusted/unadjusted price bars, 164 dividend records and five split-coverage receipts.
Its SHA-256 is `b8225bfa4dcbc5f1fac8a75424fd61c9905e10fdc5cb4e30cc75fe2b4dbfbbac`. The builder validated
2,202 XNYS price sessions and emitted 2,201 daily return rows from 2016-01-05 through 2024-10-02 for PWR,
ETN, EME, DLR and SPY. FF3, FF5, momentum and 12-industry source hashes, output hashes, package versions,
row-level source hashes and the excluded holdout boundary are recorded in the private `manifest.json`.
Raw exports, built panels and a separate descriptive in-sample audit remain under `/private/tmp`; none are
tracked in Git.

This is a retrospective diagnostic run only. The adapter correctly marks the panel `retrospective_only`,
because current French archives and revised historical market bars do not establish what was published or
available on each historical date. The standard model runner rejects this panel for training or evaluation.
An exploratory OLS summary on development dates found that FF5 explains roughly 46%–59% of in-sample daily
excess-return variation in the four operating-company names and about 99.6% for SPY; adding momentum to FF5
changed operating-company R-squared by less than 0.2 percentage points. These descriptive fits are not alpha,
forecast, hedge, or out-of-sample evidence. Unexplained residual variation is not thereby proven diversifiable.

### Broad industry-block sensitivity

To test whether residual co-movement might partly reflect omitted industry movement, the separate
`unified_factors.industry_audit` compares FF5 with FF5 plus all 12 daily French industry portfolio returns
on the exact same 2,201 development rows. This is a broad control-block experiment, not an issuer-matched
sector model: no company was assigned a portfolio by SIC, and the controls are not execution instruments.
The command and report schema are documented in the factor-model README; the JSON result remains private
under `/private/tmp/factor-panel-industry-audit.json`.

| Asset | FF5 R² | FF5 + industry-block R² | Change |
|---|---:|---:|---:|
| PWR | 0.4605 | 0.5307 | +7.02 pp |
| ETN | 0.5935 | 0.6923 | +9.88 pp |
| EME | 0.4898 | 0.5206 | +3.09 pp |
| DLR | 0.2732 | 0.3917 | +11.86 pp |
| SPY | 0.9956 | 0.9960 | +0.05 pp |

The 12-control block adds in-sample fit for the four operating names, most for DLR and least for EME. For
SPY its incremental contribution is negligible. The factors overlap materially: the largest absolute
pairwise correlation in the 17-column standardized factor design is 0.949, and its condition number is
79.4. Coefficients should not be read as cleanly separable economic causes. After adding the block, the
PWR/ETN, PWR/EME, and ETN/EME residual correlations fall from 0.302/0.260/0.220 to 0.175/0.206/0.136,
while the first residual-covariance eigenvalue share only falls from 37.3% to 35.8%. The block absorbs some
measured common movement but leaves substantial unnamed common residual risk.

This does **not** identify which industry or physical channel caused the movement; the 12-industry factors
are broad portfolios, not asset-specific exposures. All figures are in-sample, use revised retrospective
histories whose point-in-time publication status is unverified, and add 12 regressors. There are no p-values,
forecast claims, P&L, hedge claims, or holdout results. Do not select or promote this augmented model based
on these numbers. The next factor-design step is to construct point-in-time asset-to-industry assignments
and keep these separate from asset-specific economic exposures such as project, contract, backlog, energy,
and financing channels. If no defensible historical mapping or dated exposure exists, leave the component
unidentified instead of using statistical fit to name it.

For a correctly dated sector comparison, the French construction assigns stocks by four-digit SIC at each
June-end: Compustat SIC for fiscal year t-1 where available, with CRSP's June SIC as fallback
([official industry specification](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/changes_ind.html)).
This reinforces why a current SIC value or current ETF classification cannot simply be carried backward.

Once the authorized CSV is at `development-export.csv` and official French archives are in
`/tmp/french-daily-20261003`:

```sh
python -m pip install -r src/unified_factors/panel/requirements.txt
PYTHONPATH=src python -m unified_factors.panel.french --output /tmp/french-daily-20261003
PYTHONPATH=src python -m unified_factors.panel.build \
  --export /private/path/development-export.csv \
  --french-dir /tmp/french-daily-20261003 \
  --output /tmp/factor-panel-2016-2024
```

The supplied example uses the manually fetched, hash-pinned snapshot. The actual fetch writes archives to the
supplied new directory, so run it once to create a new receipt instead of overwriting a prior snapshot. The
builder's development and holdout bounds are fixed in code rather than caller-selectable.
The builder validates every warehouse row hash and source batch, bar session and OHLCV, asset/session
completeness, split coverage, dividends, calendar, factor archive hashes, factor dates, FF3/FF5 common
columns and units. It writes separate FF3 and FF5 JSON panels, a 12-industry control CSV and an immutable
manifest with source/code/output hashes and the excluded sealed-window bounds. Never edit a panel in place;
make a new version/output directory.

## What must happen before these panels can be fitted

1. Resolve the raw export destination/credentials and vendor sharing permissions; inspect exact split receipts
   and hashes on the authorized input.
2. Reconcile exchange sessions and dividend action identities against a second licensed source or the
   provider's official actions data; reconcile all five tickers' total returns before fitting.
3. Pin an actually historical/point-in-time factor vintage or declare a defensible one-bar lag for public
   historical factor snapshots. Current retrieval stamps are not historical publication dates.
4. Name the factor panel's responsible strategy owner, lock its primary outcome, costs, universe and model
   comparisons before examining returns. Keep monthly SEC/event labels as a distinct low-frequency study.
5. Keep 2024-10-03 through 2026-10-02 sealed. The prior strategy and compute-era holdouts documented in
   `docs/plan/sealed-test-record.md` are already spent and are separate studies. Name the owner and authorize
   this factor-panel holdout before any evaluation reads its daily values. The present adapter remains
   retrospective-only because historical availability of the source revisions is unverified.

References: [French Data Library and CRSP transition](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html),
[Massive split versus dividend adjustment](https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends).
