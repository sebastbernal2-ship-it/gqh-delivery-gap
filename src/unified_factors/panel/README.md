# Daily factor panel preparation

This is the next input-preparation stage for the unified exposure model. It keeps the defined development
window at 2016-01-04 through 2022-09-30, before the existing October 2022 sealed window. It does not fit
or tune a model, and it never exports or reads a post-September-2022 label.

## Inputs found and selected

Snowflake currently holds two pinned Massive batch versions of 2,703 daily bars for each of PWR, ETN, EME,
DLR and SPY, plus dividends and split-coverage receipts. The development export query selects those exact
batch hashes and cuts source sessions at 2022-09-30. The separate 20-row PWR canary is excluded. No new
vendor API key is needed; the repository's existing Snowflake query workflow can read the data.

Four public daily archives are retrieved from the official [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html):
FF3, FF5, momentum and value-weighted daily 12-industry portfolios. At retrieval, all four files parsed
with exactly 1,699 XNYS sessions spanning 2016-01-04 to 2022-09-30. Return values are percentage units in
the source and are divided by 100 once. The factor files are separate: FF3 and FF5 keep their distinct SMB
series; Mkt-RF and RF must match exactly before they can be compared. MOM is an additional separate series.
The captured retrieval receipt is `french-snapshot-2026-10-03.json`; its four archive hashes are part of
the reproducibility record. This proves what was parsed for this research run, not the historical publication
time or the exact values available to a trader in 2016–2022.

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
raw vendor data would leave Snowflake and the artifact destination/republication rights were not yet approved.
That query has not been run. The audit used only aggregate Snowflake queries. Before build.py can produce the
panel, the user must either specifically approve raw data egress to the project's Actions artifact and confirm
that sponsor/vendor permission covers storing/downloading those records there, or provide an approved local
read-only Snowflake connection whose owner can export the same pinned development rows to a private local
file. The local exporter uses only this checked-in pinned query, writes outside the repository with mode
0600, refuses to overwrite, and errors if the result exceeds its row cap. Do not put the export or French
archives in Git. It accepts standard `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, and `SNOWFLAKE_WAREHOUSE`
settings with password, key-pair, OAuth token, or authenticator-based local credentials. Configure these
through your private local secret store or shell, not in chat or a tracked file.

```sh
python -m pip install -r src/unified_factors/panel/requirements-local.txt
PYTHONPATH=src python -m unified_factors.panel.export_local \
  --output /private/tmp/development-export.csv
```

The export limit defaults to 20,000 rows and is fetched with a one-row overflow check, so an oversized
result is never silently truncated. Do not use the Actions artifact workflow for raw records unless that
route and its vendor terms are explicitly approved.

Once the authorized CSV is at `development-export.csv` and official French archives are in
`/tmp/french-daily-20261003`:

```sh
python -m pip install -r src/unified_factors/panel/requirements.txt
PYTHONPATH=src python -m unified_factors.panel.french --output /tmp/french-daily-20261003
PYTHONPATH=src python -m unified_factors.panel.build \
  --export /private/path/development-export.csv \
  --french-dir /tmp/french-daily-20261003 \
  --output /tmp/factor-panel-2016-2022
```

The supplied example uses the manually fetched, hash-pinned snapshot. The actual fetch writes archives to the
supplied new directory, so run it once to create a new receipt instead of overwriting a prior snapshot.
The builder validates every warehouse row hash and source batch, bar session and OHLCV, asset/session
completeness, split coverage, dividends, calendar, factor archive hashes, factor dates, FF3/FF5 common
columns and units. It writes separate FF3 and FF5 JSON panels, a 12-industry control CSV and an immutable
manifest with source/code/output hashes. Never edit a panel in place; make a new version/output directory.

## What must happen before these panels can be fitted

1. Resolve the raw export destination/credentials and vendor sharing permissions; inspect exact split receipts
   and hashes on the authorized input.
2. Reconcile exchange sessions and dividend action identities against a second licensed source or the
   provider's official actions data; reconcile all five tickers' total returns before fitting.
3. Pin an actually historical/point-in-time factor vintage or declare a defensible one-bar lag for public
   historical factor snapshots. Current retrieval stamps are not historical publication dates.
4. Name the factor panel's responsible strategy owner, lock its primary outcome, costs, universe and model
   comparisons before examining returns. Keep monthly SEC/event labels as a distinct low-frequency study.
5. Open no sealed window; the existing gate and owner rules remain in force. The present adapter cannot be
   passed to the factor/GARCH development runner because its retrospective status is intentionally refused.

References: [French Data Library and CRSP transition](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html),
[Massive split versus dividend adjustment](https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends).
