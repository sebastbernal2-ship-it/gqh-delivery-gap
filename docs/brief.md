# The track brief, frozen

Source: gqhacks.com/tracks/systematic-trading (the participant brief page), gqhacks.devpost.com/rules,
and the Massive bonus page inside the same track. Frozen 2026-10-02.

## Deadline

Hacking ends Sunday 2026-10-04 at 11:00 ET. Systematic Trading submissions are due on Devpost
at **Sunday 2026-10-04, 10:00 ET**. Expo and judging run 13:00 to 15:00.

## Deliverables

Two things, both required. A note without code, or code without a note, is not judged.

1. A quant note PDF, at most 5 pages including figures and tables. References and an optional
   appendix do not count toward the limit, but judges are not required to read the appendix.
   11pt font or larger, standard margins.
2. A link to a public GitHub repo.

## How it is scored

Five criteria, each scored 1 to 10, total out of 50. Code is not scored on its own.

1. **Economic Foundation, strength of the hypothesis.** Who is on the other side, and why the
   opportunity has not gone away.
2. **Creativity and distinctiveness.** A generic strategy scores low even when it works.
3. **Risk Management Plan.** Position limits, de-risking rules, factor exposure, tail and regime risk.
4. **Liquidity and capital.** How much capital the strategy could run before the edge erodes.
5. **Performance and Analytical Evidence.** In-sample and out-of-sample, net of costs.

**The cap rule.** Criterion 5 is capped at 4, no matter how strong the rest, if judges cannot run
the code, if the code gives materially different numbers than the note, if there is lookahead bias,
or if there is tuning on the out-of-sample period.

## The out-of-sample rule

The most recent **20 percent of your history or the most recent 2 years, whichever is shorter**,
set aside and never used to design or tune anything. Open it once, at the end, and report the
result whether it is good or bad.

## Required practice

- Write the hypothesis **before** you look at any results.
- Report every number **net** of transaction costs. State the cost in bps per trade and justify
  the number for the market you chose. Show what happens when costs **double**.
- Report **how many variants** you tried and explain why you tried them.
- Show a **parameter plateau**, not a single peak. Nearby values must also work.
- Lag every signal at least one bar. Never use the same-bar close for signal and fill.
- Use a point-in-time universe, or state the survivorship bias and estimate its size.
- Report in-sample and out-of-sample **separately**, with turnover, max drawdown, and an equity curve.

## Common ways to lose points

Trying many variants on noise and reporting the best one. Too many free parameters. Using future
information. Backtesting only today's survivors. Gross returns. Leaking or tuning the test set.
Not checking the simple explanation first, which is usually a bug, a bias, or exposure to a known
factor such as market beta, momentum, or value.

## The bonus challenge inside this track

Massive runs a bonus, judged separately on research quality rather than on P&L.

- Signal: Massive's Filings and Disclosures dataset, which tags every 8-K since January 2022 with
  one of 119 AI-tagged event types.
- Instrument: the option chain exactly as it existed on the pre-event session, with each leg's
  daily close and volume to expiry, and spot recovered by put-call parity.
- Benchmark: implied move = (ATM call + ATM put) / spot on the pre-event session.
- Scope: one event category, one strategy, one expiry bucket, one written interpretation.
- Five defined strategies are scored: long call, long put, covered call, protective put or collar,
  cash-secured put.
- What separates the top teams: decay across horizons and expiry buckets, combined categories, a
  **placebo control**, and a realistic trade specification.
- Judges rerun the pipeline on dates you never saw.

## Data sponsors

Webull OpenAPI with a backtesting starter kit (track sponsor). Massive. Databento. FRED. Ken
French library. Sponsor data is optional and free public sources are allowed. Every source is
cited in the note.

## What judges reward, in their own words

A modest strategy with a solid rationale scores better than a huge backtest that does not hold up.
A Sharpe above 3 on daily data usually means a bug. Two of the five criteria are about what
happens after the backtest, which is where most teams are thin.
