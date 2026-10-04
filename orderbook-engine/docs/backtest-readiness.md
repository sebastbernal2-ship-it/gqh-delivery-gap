# Backtest readiness and strategy handoff

Status: generic daily portfolio runner and artifact pipeline implemented 2026-10-04. Strategy,
real-data adapters and instrument-specific assumptions remain explicit inputs, not defaults
inferred by the engine.

## Daily portfolio backtest (signal/portfolio layer)

This separate runner makes a frozen daily strategy test executable without pretending daily bars
are order-book evidence. It consumes one JSONL row per symbol/session from the strategy's
point-in-time adapter. Rows include the decision/entry/exit times; availability times for signal,
membership, ADV and borrow; fixed-point target weight and forward total return; benchmark; liquidity;
cost and borrow assumptions; source ID/hash; and quality/status. It rejects unavailable-at-decision
features, non-observed or unhealthy data, missing borrow for shorts, malformed source hashes,
imbalanced universes, out-of-order/non-contiguous intervals, and configured risk or participation
breaches. Session date must agree with UTC entry date.

Start from `examples/daily-portfolio-config.template.json`. The config freezes hypothesis/spec IDs,
source/license, cost model and its citation/assumption, historical universe, initial capital, gross,
net, name and participation limits, declared variant count, and annualization frequency. Amounts,
weights, returns and costs are integer wire units (1e-8 USD, bps, 1e-8 return); float input is
rejected. Accounting, compounding, fees, borrow, drawdown and capacity calculations use integer
fixed-point arithmetic. Floating point is limited to conventional statistical summaries.

Example invocation (the explicit flag is a deliberate holdout-opening acknowledgement):

```sh
cd orderbook-engine
opam exec -- dune build examples/daily_portfolio_backtest.exe
opam exec -- dune exec examples/daily_portfolio_backtest.exe -- \
  examples/my-frozen-config.json data/frozen-target-panel.jsonl \
  results/report.json results/equity-curve.csv results/positions.csv \
  results/breakdowns.csv results/dashboard.html --open-oos
```

It emits a metrics report (full gross/net/double-cost, chronological development/test, market and
sector benchmarks, annual and regime groups), equity curve, per-position exposure/capacity and
cost attribution, breakdown CSV, and a standalone SVG dashboard with visible OOS boundary. A
manifest hashes the input, config, executable and outputs. OOS is the latest 20% of sessions or
latest two calendar years, whichever is shorter. `--open-oos` is an acknowledgement, not technical
one-time access control; freeze the strategy and all choices before a team member opens it. Add a
calendar-completeness manifest upstream: the runner detects timestamp discontinuities and panel
holes within supplied sessions but cannot infer an omitted expected exchange session without a
versioned session calendar.

The report includes annualized return/volatility, zero-rate Sharpe, zero-target Sortino, Calmar,
maximum drawdown, fixed-unit total P&L, annualized/total turnover, and period-return diagnostics.
Sortino downside deviation is the root mean square of negative daily returns with all observed
periods in the denominator. Profit factor is summed positive daily net returns divided by the
absolute sum of negative daily net returns; win rate and average win/loss are likewise daily-period
statistics. A period is one portfolio session, not a trade. Consequently these fields must not be
described as trade win rate, average trade P&L, or trade profit factor. Undefined zero-denominator
statistics are null in JSON and blank in CSV.

The included 10-session synthetic fixture exists only to prove plumbing and arithmetic; it is not
evidence of profitability or realistic execution. There is not yet an implemented adapter from the
PWR/ETN/EME/DLR event-study data into this target panel, and no real backtest has been run with this
harness. Daily cost/ADV participation is a proxy, not a fill simulator; it does not model intraday
spread paths, nonlinear impact, queue position, borrow recalls, financing/margin, or executable
liquidation. Those inputs must be sourced and validated before interpreting net results.

## Cost-data ownership and present gap

No audited historical cost panel is currently present in this repository. The evaluator's
`one_way_cost_bps`, ADV, and short-borrow fields are input assumptions/observations; the code does
not fetch or infer them. For the current equity event study, use Massive SIP historical NBBO quotes
to derive timestamped spread and displayed top-of-book context, plus its trades/volume for
participation controls. This is not own-order market impact: test a declared impact/slippage schedule
by volume participation and double it. Add broker/exchange commissions and regulatory fees from
effective-dated official fee schedules as separate components to avoid double-counting spread.

Short borrow is a separate hard dependency for a long/short result. IBKR documents security-level
availability and indicative borrow-rate history in its SLB tool (up to three years in TWS materials);
that does not cover our full 2016-present research window. Do not treat a current borrow quote as a
historical vintage. Until sufficient point-in-time availability/rate history is secured, report
long-only or mark the short leg unvalidated; do not silently assign zero borrow.

For margin: a cash-equity test constrained to gross exposure <= 100% does not need borrowed
financing/margin. Leveraged equity requires the specific broker's dated financing and margin rules.
For futures, use exchange contract specs and effective-dated initial/maintenance margin history
(CME publishes a historical margin archive); broker house add-ons remain separate. For perps,
historical funding is an explicit series, while margin/fee tiers must be timestamped; a current
metadata response is not a historical rulebook. FRED/NY Fed SOFR is a long daily reference rate,
not a substitute for broker financing or stock-loan fees.

Storage split: Snowflake is the durable, versioned home for source quote/cost panels and their
vintages/manifests; TigerData is for bounded live/replay telemetry and precomputed time-series
dashboard aggregates. Do not duplicate bulk daily bars/quotes into TigerData merely to make it a
second warehouse.

## Separate the two backtests

The project needs two related but distinct evaluation paths.

1. The equity event study evaluates whether a timestamped information signal predicts returns.
   Use daily prices, point-in-time membership/identity, corporate actions, a one-bar execution lag,
   long/short borrow assumptions where needed, turnover, net costs, drawdown and chronological
   evaluation. It does not require L2. Daily OHLCV cannot support claims about queue position or
   intraday fills. This remains in the research pipeline, not the order-book simulator.
2. The order-book replay evaluates execution and capacity for an instrument with synchronized
   depth/trades. It takes canonical JSONL with explicit `order_intent` events and replays the
   supplied orders against visible depth. It does not create alpha or generate positions. The
   signal layer must produce the intents before replay, using only features available at each
   decision timestamp.

The same strategy may eventually pass through both: the daily event study estimates the signal's
economic return; the book replay tests a separately justified execution policy on data for the
same traded instrument and venue. A crypto book is not execution evidence for an equity order.

## Generic asset replay command

Build from `orderbook-engine/`:

```sh
opam exec -- dune build examples/asset_fixture_report.exe
opam exec -- dune exec examples/asset_fixture_report.exe -- \
  examples/asset-config.json fixture.jsonl report.json equity-curve.jsonl
```

Start from `examples/asset-config.template.json`, replacing venue, symbol, effective interval,
increments, multiplier and terms from the instrument's authoritative specification. All numeric
fields are integer wire units: price increment in 1e-4 price ticks, quantity increment in 1e-6
units, cash in 1e-8 money units. The tool rejects floating-point config values. `kind.type` accepts
`equity`, `future`, `perpetual` or `option`; derivative margin/expiry and option contract terms are
required for the corresponding kind.

Inputs must match the configured venue and symbol, have healthy quality and complete SHA-256
provenance, and be ordered by receive time. The engine fails closed on chain gaps, malformed
prices/quantities, crossed books, expired instruments, unsupported resting GTC/post-only intents,
or positions that breach maintenance without a declared venue liquidation rule. The equity curve
has one marked point per input event. It uses an explicit venue mark when available and otherwise
the latest two-sided book midpoint observed from market data. Simulated own fills do not re-mark the
market, so spread paid remains visible in mark-to-market P&L. A one-sided book with an open position
and no explicit mark fails closed instead of guessing a valuation.

The report records input, config and executable hashes as the run identity components; event-time
and receive-time coverage; source hashes and event-kind counts; order/fill counts; integer net P&L,
net return and maximum drawdown; fees, realized P&L, funding, rejected and unfilled quantities.
The JSONL curve is a separate artifact suitable for plotting or loading into TigerData. Re-running
with byte-identical fixture/config/executable should produce the same accounting values and curve.

## What is ready and what is not

Ready: fixed-point instrument accounting and unit checks; single-instrument visible-depth IOC/FOK
execution; receive-time latency; cash-equity settlement; future/perpetual margin and funding paths;
cash-option accounting guards; fail-closed replay validation; deterministic run metadata; marked
equity curve and integer summary metrics; unit tests for accounting, execution, timing and report
arithmetic.

The daily portfolio evaluator is turnkey for a correctly formed frozen target-weight panel, not yet
for raw source data end-to-end: the strategy-to-target adapter and actual historical input panel are
still missing. The generic book path is single-instrument and taker-only; no passive FIFO
claim is supported from aggregated L2; short cash equities need a borrow/recall and financing model;
physical option exercise, portfolio margin/netting, FX conversion, venue-specific liquidation rules
and multi-instrument cash allocation are not generalized. Equity daily event studies need their own
portfolio ledger with point-in-time tradable universe, delisting/corporate-action treatment, borrow
and cost inputs before being treated as executable long/short performance.

## Strategy readiness gates

Before a strategy run, freeze and record:

- instrument universe and historical membership rules;
- signal definition, event/feature availability timestamps, and minimum lag;
- portfolio formation, gross/net exposure, rebalance, sizing and concentration limits;
- baseline and falsifier, plus the declared variant count and plateau grid;
- fee, spread, slippage, borrow, funding and capacity assumptions with a doubled-cost case;
- chronological train/development and untouched test boundaries from the frozen track brief;
- independent-event/regime counts, not calendar duration alone;
- source/config/code hashes, missingness, quality exclusions and reproducible outputs.

The current thesis/evaluation ledger owns its existing split. Do not reopen, tune on, or relabel a
sealed window while making the generic harness ready. A report generated by this engine is an
execution measurement, not proof of an economic edge.
