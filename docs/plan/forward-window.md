# The frozen forward window

Status: declared 2026-10-04, before any window observation exists. Owner: sebas. Runner:
`scripts/run_forward_snapshot.py`. Evaluator: `scripts/evaluate_forward_window.py`.

Both sealed windows are spent and every number in the repository is development evidence. This is the
only instrument that can produce a new claim, because the clock starts now and nothing can be
backfilled.

## Window

- Starts at the first trading session after this declaration. Every prediction is stamped with its
  run time in UTC before the outcome can exist.
- Ends when 250 scored events accumulate or twelve months elapse, whichever comes first. The
  evaluation is run once, at the end.

## Frozen elements

1. **Universe.** The declared AI-capex complex register. No name is added or removed during the
   window; a register change is a new window.
2. **Sleeves and construction.** Revenue surprise, capex surprise and the gated intensity
   expression, exactly as implemented: twenty-session holds, conviction weights, gross-normalised
   daily returns, inverse-volatility weights over trailing sixty sessions, ten percent volatility
   target, equal event handling. The recipes are frozen; the model parameters are refitted on data
   available at each snapshot and their digest is recorded.
3. **Gate.** The revenue expected bin confirms a long at or above expectation and a short below.
   Missing surprise data never confirms.
4. **Costs.** Twenty basis points round trip on the driver sleeves, the engine's volume-bucket costs
   on the intensity sleeve, plus a doubled-cost report.
5. **Evaluation metrics.** Net annualised return, volatility, Sharpe, maximum drawdown, hit rate,
   per sleeve and for the composite, each with a month-blocked bootstrap interval, plus the
   in-sample arm for the record.

## Falsifiers, declared before the window

1. The composite nets zero or less over the window.
2. The composite Sharpe is 0.5 or below.
3. The composite maximum drawdown exceeds twenty percent.
4. The capex hedge turns positive and significant, which would contradict the T43 sign story.
5. Any snapshot's predictions change after the fact, which would void the window.

## Rules that make it honest

1. **Append only.** A snapshot is never overwritten. The runner refuses to write over an existing
   file.
2. **Immature outcomes are not scored.** The evaluator refuses any event whose exit session is not
   yet in the price cache.
3. **The manifest is hashed.** Every snapshot records the SHA-256 of its inputs and its fitted
   parameters, so a later change to a recipe is visible.
4. **No re-fitting to the window.** Model fitting uses only data available at the snapshot time.
5. **One evaluation.** The window is scored once, at the end, and reported whether good or bad.

## What is not claimed

Nothing about the window until it closes. The development numbers, including the best measured
configuration at Sharpe 1.549 and a -9.0 percent drawdown, are not evidence about the window, and
T49 already says why: the recent era was favorable by construction.
