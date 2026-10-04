# t-intensity-charge: capex intensity surprises are charged over weeks

Owner: sebas. Status: active. Date: 2026-10-04.

An Investment Proposal in the shape the training material uses. Development only: both sealed windows are
spent, so the split below is early against late, not a sealed test.

## Hypothesis

A capex intensive firm that raises capex as a share of revenue spends ahead of the revenue that spend
serves. Depreciation and funding land inside the measurement window, and the equity market charges the
surprise in relative performance over the following weeks before the cash flow arrives. The payer is the
holder of the capital intensive name whose spending outran its revenue base. The other side is whoever
sells it the equity.

The simplest rival explanation is the long known asset growth effect, where high asset growth
underperforms. That was tested directly and rejected as the explanation: intensity and asset growth are
near orthogonal in this panel (mean within quarter correlation -0.006), and asset growth is rewarded here
(+0.13 at twenty days) while intensity is charged (T29). The second rival is that the effect is one
buildout regime. Three regimes carry the same sign, strongest in the buildout (T30).

Falsifier: the charge carries no forward relative return on a disjoint name set, or its sign flips once
filing timestamps are lagged conservatively, or it lives entirely inside the disclosure names that
produced it (partly true today, see Robustness).

**Why us:** the edge channel is data and processing, not latency. The signal needs point in time
quarterly facts joined to daily prices, with filing dates as the clock. A latency budget is irrelevant:
the information half life is weeks.

## Data

- `results/complex-capex-quarterly.csv`, `results/complex-revenue-quarterly.csv`: SEC XBRL company
  concepts for 59 names across the declared market groups, quarterly durations only, latest filed fact per
  period. Knowable at the `filed` date, which is the clock.
- `results/bar-cache/`: daily closes, 298 series, read only.
- `results/universe-adv-monthly.csv`: monthly median dollar volume per name, 2017-06 to 2026-10, the
  capacity input.
- `results/market-panel.json`: the declared peer groups.
- Data gate: public sources only, no entitlement, no sealed window opened. Everything here is
  development.

## Structure

The world measured before the strategy: 640 name-quarters, 58 names, 2014 to 2026 filings; 231 cohorts
over 2017-08-04 to 2026-10-02; median cohort 14 names. Distributions and associations are in T25 to T31.
Regime states are the three filing windows: pre boom (through 2021), buildout (2022 to 2024), late (2025
onward), all defined on filing dates only. Liquidity: monthly dollar volume per name, with the tenth
percentile cohort binding capacity.

**The graph and the chain.** The chain is `docs/chains/t-intensity-charge.jsonl`: eight edges, two of
them without a measurement (regime moderator, borrow availability), one P&L carrying role (the long short
expression). Nodes are `dig:compute:capex-intensity`, `dig:compute:provider-revenue-line`,
`dig:compute:provider-revenue-line`, `dig:compute:equity-transmission`, `factor:asset-growth` and
`factor:liquidity`.

**The assumption register.** Measured: the charge (T25), its cross sectional limit (T26), asset growth as
a rival (T29), sign stability across regimes (T30), fragility (T31). Proxied: regime moderator (pre boom
window), cost buckets by ADV. Testable: borrow availability and cost for the short leg.

## Methodology

- **Signal**: year over year log change in capex intensity, capex over revenue, known at the later filing
  date, valid 180 days.
- **Universe**: names with both XBRL facts and daily closes, monthly dollar volume at or above the
  declared floor, 10 million dollars in the preferred specification.
- **Conditioning**: all weather at the portfolio level; the regime cut is reported, not traded.
- **Portfolio**: dollar neutral. Scores are demeaned by declared peer group, ranked, and the bottom third
  is bought against the top third, equal weight within each leg, gross 0.5 long and 0.5 short.
- **Clock**: a cohort opens on each new filing, not on a calendar cadence, and holds twenty trading days.
  Cohorts overlap. Rebalancing on a calendar cadence with a quarterly signal pays cost for a portfolio
  that has not changed and is recorded as a rejected decision.
- **Costs**: per name one way buckets by monthly dollar volume: 5 basis points above 50 million, 10 above
  10 million, 20 above 2 million, 40 below; charged at cohort open and close; doubled in the stress run.
- **Baseline**: a dollar neutral portfolio sorted by asset growth, and equal weight industry benchmark.
- **Primary horizon**: twenty trading days, the smallest horizon whose gross clears the cost hurdle with
  room for the doubled cost run.
- **Variant plan and the count**: the declared grid is 72 variants across horizon, quantile, weighting,
  neutralisation and cost multiplier. The decisions taken are all recorded in the chain log, and that
  count is the multiple testing deflation input.
- **Latency budget**: none required. Entries are end of day.

## Results

Development only, all numbers net of the declared costs unless labelled gross. The preferred
specification: twenty day horizon, terciles, equal weight, group neutral, ten million dollar volume
floor, base costs.

| Metric | Early, 2017-08 to 2024-12 | Late, 2025-01 to 2026-10 |
|---|---|---|
| Sharpe | 0.28 | 0.68 |
| Annual return | 8.4 percent | 32.7 percent |
| Win rate, daily | 32.1 percent | 40.2 percent |
| Profit factor | 1.084 | 1.168 |
| Max drawdown | -59.9 percent | -40.0 percent |

Full window: net annual return 13.1 percent, gross 15.9 percent, annual volatility 34.3 percent, Sharpe
0.381, hit rate 33.6 percent, profit factor 1.111, max drawdown -65.8 percent, 231 cohorts. With doubled
costs: net annual return 10.2 percent, Sharpe 0.299. Status: association strength is modest and positive,
causal status is descriptive, evidence status is development, and promotion status is open.

**Breadth and capacity.** 231 cohorts, median 14 names. Capacity at one percent participation of the
binding name's dollar volume: median 3.87 million dollars, tenth percentile 1.31 million. At five percent:
median 19.4 million. Entry cost median 5.6 basis points of gross per cohort. The binding name in the
tenth percentile cohorts is the constraint, not the average.

## Robustness

- **Parameter plateau**: of 72 declared variants, 21 percent are positive on annual return. The positive
  region is equal weight with group neutralisation at horizons of twenty and sixty days; the failures are
  rank weighting and no neutralisation, at doubled costs. That is a plateau in the intended region, not a
  single peak.
- **Subsamples**: sign is positive in the early and late windows, magnitude larger late.
- **Regime**: three filing windows carry the same sign (T30).
- **Placebo**: the asset growth rival is rewarded rather than charged, so the charge is not generic
  growth sorting (T29).
- **Failed iteration**: a trailing volatility overlay, scaling each cohort to a ten percent target, cut
  the Sharpe from 0.381 to 0.174 because it scales down after losses. Recorded as rejected.
- **Fragility**: removing the ten disclosure names halves the association and removes its significance
  (T31). This is the main threat to the thesis and the reason capacity and cost discipline matter more
  than the headline return.

## Risk

Portfolio risk: dollar neutral, group neutral, but only 14 names median, so idiosyncratic risk is high and
the drawdown is deep (-65.8 percent full window). Cluster caps and a risk overlay are the next declared
iteration; the first overlay attempt failed and is recorded. Borrow: short availability and cost are
unmeasured and are one of the two unmeasured edges in the chain; they bound the short leg. Joint tails:
the names are one complex, so a complex wide shock hits both legs together.

## Liquidity

Size against ADV: capacity is 3.87 million dollars at one percent participation of the binding name, 19.4
million at five percent. Days to build and exit: cohorts hold twenty days, so a five million dollar book
at one percent participation builds over several cohorts. Where capacity constrained the choice: the ten
million dollar volume floor was chosen because the unfloored version has a tenth percentile capacity of
3,844 dollars, which is not a strategy. The floor costs some return and buys usable capacity.

## Novelty

Closest known effect: the asset growth anomaly. The mechanical difference: the signal is capex over
revenue, not total assets, so it measures spending relative to the revenue base rather than balance sheet
growth, and the two are near orthogonal here. The innovation is in the measurement and the mechanism, not
in the model, which is ranks and equal weights. The edge channel is point in time processing of filings
joined to prices; there is no speed channel.

## Decomposition and exposure budget

Intended exposures: short capital intensity surprise, long capital discipline, group neutral, dollar
neutral, no rate or market beta by construction. Realised attribution: the late window carries most of the
return, and within it the compute and AI names contribute most of the short leg. Regime breakdown: sign
stable, magnitude regime dependent. Which edges carried the P&L: the intensity measurement and the
pricing edge. Which register rows downgraded: the ownership split (T27 downgraded by T28), and the
volatility overlay (rejected). What turned out to be proxying something else: nothing measured so far,
but the fragility result says a large part of the association lives in a handful of names.

## Limitations

Asset growth is the only rival factor tested. Borrow cost and short availability are unmeasured. The
price source is a single free vendor. Corporate actions are not separately modelled. Both sealed windows
are spent, so nothing here is a sealed test, and the late window is short. The next tests: a disjoint name
set, a conservative filing lag, borrow data, and a cluster capped risk overlay.
