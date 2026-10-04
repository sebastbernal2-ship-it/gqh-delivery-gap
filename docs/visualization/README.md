# Judge-rerunnable research dashboard

The builder creates an offline interactive dashboard from tracked GQH results and, optionally, actual daily portfolio and closed-trade ledgers. It follows the Plotly visual language of the options-momentum prototype: wide plots, restrained dark theme, readable captions, hover/zoom/pan, legend toggles, and PNG export. It does not import that prototype's synthetic market data or present it as competition evidence.

## One-command build

From the repository root, install the pinned dependency once, then run this single command to rebuild the tracked-summary dashboard and explicitly mark missing full-path diagnostics:

```sh
python3 -m pip install -r docs/visualization/requirements.txt
python3 docs/visualization/reproduce.py
```

When the backtest exports source ledgers, pass them to the same command to populate the full visual library (use a predeclared split date only when the ledger has no `sample` labels):

```sh
python3 docs/visualization/reproduce.py --daily-ledger path/to/daily.csv --trade-ledger path/to/trades.csv --split-date 2024-01-01
```

The output is `docs/visualization/dashboard.html`; input hashes are recorded in `reproduction-manifest.json`.

## Ledger schema

Daily CSV: required `date` (ISO date) and either `net_return` or `nav`; optional `baseline`, `sample` (`IS`/`OOS`), `gross_return`, `pnl`, `costs`, `turnover`, and regime label. Returns are decimal fractions (0.01 = 1%). If NAV is provided, plotted NAV is rebased to 100. Baseline groups must have unique dates.

Trade CSV: `baseline`, `net_pnl` (or `pnl` / `realized_pnl`), `entry_date`, and optional `size`, `quantity`, `notional`, `costs`/`fees`, `holding_days`. P&L and size units must be documented by the producing backtest. Only complete closed trades belong in trade outcome statistics.

The optional `--split-date` must be declared before inspecting OOS results. Explicit `sample` labels take precedence. Each sample curve is locally rebased to 100 and presented as a separate comparison, not used to tune the strategy.

## What it visualizes

The tracked-summary view shows the stored sleeve/portfolio table, annualized contribution by year, early/late event-study comparisons, factor association heatmap, regime timeline, and raw-versus-standardized Sharpe comparisons.

With daily/trade ledgers it adds a metric table by baseline (return/P&L index, Sharpe, Sortino, Calmar, max drawdown, profit factor, win rate, average win/loss, trade count, volatility, turnover), full equity and drawdown paths, rolling Sharpe/Sortino and realized volatility, turnover, trade outcome distribution and spread, monthly trade frequency and size distribution, baseline daily-return correlation and trade-feature correlation heatmaps, seeded circular block-bootstrap overlays plus terminal-return/max-drawdown distributions, and chronological IS/OOS equity curves. Missing fields get a specific unavailable panel, not fabricated values.

The bootstrap uses 250 paths per baseline, a fixed seed (2603), 20-session circular blocks and at most a 252-session horizon. It is a sensitivity diagnostic conditional on the observed returns, not a forecast. To compare MC and actual paths it uses a matched latest-history horizon and rebases both to 100.

## Reproducibility boundary

This one command rebuilds the visual output and displayed numbers from hashed tracked result files and any supplied hashed daily/trade ledger. It does **not** rerun data acquisition, point-in-time feature construction, model fitting, or the original strategy. The repository currently lacks the ignored `results/bar-cache/` and a committed daily NAV/return/cost and closed-trade ledger; consequently its summary files cannot reconstruct continuous observed equity/drawdown curves, trade outcomes, Monte Carlo inputs, or OOS/regime path diagnostics. The builder marks those unavailable unless actual source ledgers are supplied.

The tracked three-sleeve result predates the entry-clock correction audit. Treat it as reproducible development research, not validated performance. Full judge reproducibility requires the backtest producer, accessible/versioned input data, configuration, and run hashes in addition to this visualization command.

## Cached culmination results, one file

`culmination.py` loads the cached ledgers under `results/culmination-ledgers/`, prints the exact metrics
from `results/culmination.json`, and builds the dashboard with this section's own builder:

```sh
python3 docs/visualization/culmination.py            # the conditioned best
python3 docs/visualization/culmination.py --all      # every candidate
```

The ledgers show four candidates: the gated charge core, the two-sleeve headline, the same with the
reversed capex hedge, and the conditioned system, each with the equal-weight basket as the baseline
column, in-sample and out-of-sample labels, and the drawdown regime the honest walk-forward chose in all
six years. `dashboard-culmination-C_conditioned.html` is committed so the figures open without running
anything; the other candidates rebuild in seconds with `--all`.
