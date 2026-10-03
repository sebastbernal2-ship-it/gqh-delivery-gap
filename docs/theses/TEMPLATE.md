# t-short-slug: <the claim in one line>

Owner: <github handle>. Status: <active | parked | superseded | retired>. Date: <YYYY-MM-DD>.
Supersedes: <t-other-id, or nothing>.

An Investment Proposal in the shape the training material uses, extended where that shape has gaps.
The eight sections below are the pipeline stages in `docs/alignment.md` sections 13 to 15: they are
required for an **active** thesis, and `make check` fails if one is missing. Keep it readable in ten
minutes. A record that cannot be read is not finished.

## Hypothesis

The mechanism. Why the inefficiency exists. Who pays, and who is on the other side. What the signal
predicts. The simplest rival explanation, and why it is not the whole story. The falsifier.

**Why us, sketched here and evidenced later:** which edge channel we have (data, inference speed,
processing, or portfolio craft), the breadth we expect, the regime dependence we expect, a capacity
sketch, and the latency budget. These belong to the rationale, not the aftermath. See
`docs/alignment.md` section 16.

## Data

What was collected, from where, and **when each field became knowable**. Units, identifier rules,
corporate actions, exclusions, rejections.
**Data gate: approved by <name> on <date>.**

## Structure

The world measured before anything is built on it. Distributions with tails and censoring. Dependence
beyond correlation where it matters. Association screens with multiple-testing control. Which events
and names share shocks, and the resulting **effective breadth**. What is stable across sub-periods.
**Regime states defined on past-only data.** Cross-sectional variation across names and events.
**Liquidity and capacity structure**: ADV, spread, borrow, financing.

Then: **every assumption used downstream cites a measurement here.**

## Methodology

Signal rules and timing. **Conditioning**: all-weather, state-gated, or state-scaled, decided up front.
**Portfolio construction**: weights from forecast and uncertainty, correlation-aware risk budgeting,
per-name and per-cluster caps, turnover and cost-aware. Execution and cost model. The baseline being
beaten. The one primary horizon. The variant plan, the sealed-test plan, and the **latency budget**
against the signal's information half-life.

## Results

Their metric list, produced our way: reported in-sample and out-of-sample separately, every number net
of costs, deflated for the number of variants.

| Metric | In sample | Out of sample |
|---|---|---|
| Sharpe | | |
| Annual return | | |
| Win rate | | |
| Profit factor | | |
| Max drawdown | | |

**Breadth.** IC, decay curve, effective breadth after correlation, hit-rate distribution, effect-size
spread, worst decile, and the capacity curve. A single case cannot show a distribution, so these
measurements are what make generalisation a decision rather than a hope.

## Robustness

Parameter plateau rather than a single peak. Subsample and regime stability. Placebo control.
Alternative specification. Bootstrapped intervals. What failed.

## Risk and contingencies

**Portfolio-level risk**: correlation-aware budgeting, per-name and per-cluster caps, effective
breadth, state-conditional fragility, drawdown and de-risking triggers. Each risk with a trigger and a
response: hedge, size down, exit, abstain, pause. Who acts. Joint tails, borrow, financing, basis,
concentration.

## Liquidity and capital

Size against ADV. Days to build and to exit. Borrow availability and cost. Financing. The capacity
curve in dollars before the edge dies. The capital we would actually run. **State where capacity
constrained the choice of expression**: which instrument, basket, horizon or book size we chose because
of it.

## Novelty

The closest known strategy or published factor, and the mechanical difference from it. Where the
innovation lives: the mechanism or the measurement, not the model. Why this is not a known anomaly with
a new label. **The edge channel, with evidence**: data, inference speed, processing, or portfolio craft.
If we can name none, say so rather than proceeding.

## Decomposition and exposure budget

Intended exposures, and why the mechanism pays for them. Neutralised exposures and how. Realised
attribution against the budget, with the unexplained share stated. Regime breakdown. The hedge map.
**Edge-channel confirmation**: after seeing the numbers, which channel actually produced the return,
and whether the original claim survives.

## Limitations

What we could not measure, what failed, and what we would test next.
