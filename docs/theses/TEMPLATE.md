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

## Data

What was collected, from where, and **when each field became knowable**. Units, identifier rules,
corporate actions, exclusions, rejections.
**Data gate: approved by <name> on <date>.**

## Structure

The world measured before anything is built on it. Distributions with tails and censoring. Dependence
beyond correlation where it matters. Association screens with multiple-testing control. Which events
and names share shocks. What is stable across sub-periods, and what is not.
Then: **every assumption used downstream cites a measurement here.**

## Methodology

Signal rules, timing, portfolio construction, execution and cost model. The baseline being beaten. The
one primary horizon. The variant plan, and the sealed-test plan.

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

## Robustness

Parameter plateau rather than a single peak. Subsample and regime stability. Placebo control.
Alternative specification. Bootstrapped intervals. What failed.

## Risk and contingencies

Each risk with a trigger and a response: hedge, size down, exit, abstain, pause. Who acts. Joint tails,
borrow, financing, basis, concentration. Fragility by regime.

## Liquidity and capital

Size against ADV. Days to build and to exit. Borrow availability and cost. Financing. Capacity in
dollars before the edge dies. The capital we would actually run.

## Novelty

The closest known strategy or published factor, and the mechanical difference from it. Where the
innovation lives: the mechanism or the measurement, not the model. Why this is not a known anomaly
with a new label.

## Decomposition and exposure budget

Intended exposures, and why the mechanism pays for them. Neutralised exposures and how. Realised
attribution against the budget, with the unexplained share stated. Regime breakdown. The hedge map.

## Limitations

What we could not measure, what failed, and what we would test next.
