# Declared study: do compute rental prices lead queue withdrawals

**Status: development only, declared before the run.** Both sealed windows are spent. This is the missing
link inside thesis C: compute demand is the demand side of the power buildout, and the queue is the
supply side. The question is whether rental price moves lead project withdrawals in the interconnection
queue, which is what would let the compute feed act as a phase marker for the queue work.

## The object

Monthly withdrawal hazard by technology against lagged compute rental change.

- Withdrawals: projects with a withdrawal date in the month, from `results/queue-panel.csv`.
- Alive base: projects in the queue that month (requested by then, not yet withdrawn and not yet online by
  then), reconstructed from request and withdrawal dates.
- Hazard: withdrawals divided by the alive base, per month and per technology group.
- Compute signal: the cross-family median rental price, monthly, from `results/compute-price-monthly.csv`,
  expressed two ways: the three month log change, and the level against its trailing twelve month mean
  (a boom or bust reading).

## Tests, all reported

1. **Primary**: Spearman between the rental three month change three months earlier and the withdrawal
   hazard this month, pooled and per technology group (Solar, Wind, Battery, Gas, Other).
2. **Secondary**: the same with the level reading instead of the change.
3. **Placebo contrast**: speculative technologies (Solar, Battery) against firm ones (Gas, Coal, Nuclear),
   declared in advance. A phase marker should act more on the speculative tail.

Direction is declared as ambiguous and both readings are legitimate: rising rentals mean the AI buildout is
tight (more power demand, fewer withdrawals is one story), falling rentals mean the buildout is cooling
(projects lose their offtake rationale, more withdrawals is the other). The study reports the sign it
finds and does not pick the story after the fact.

## Null

Circular shifts of the rental series against the hazard, all shifts from one to thirty, reported as the
shift distribution and the share of shifts beyond the observed value.

## Falsifier

No association at any lag, or the association is the same in the placebo technologies, which would say the
compute feed carries nothing the queue does not already know.

## Ceiling

One queue snapshot with recalled dates, thirty two overlapping months, compute prices that are policy
prices in ten separate markets (T8, T9), and no controlling for power prices or policy. This is a phase
marker test, not a causal claim, and it opens no sealed window.

## Reproduce

    python3 scripts/build_compute_queue_study.py

## Result, 2026-10-04

Thirty two overlapping months, 28 with a three month change and 25 with a level reading.

The clean finding is the level reading at a six month lag. The cross family median rental price against
its trailing twelve month mean is negatively associated with the withdrawal hazard six months later:
pooled rho -0.60 (19 observations, observed beyond every one of the 19 circular shifts), solar -0.57,
wind -0.42, battery -0.61, gas -0.21. Every group carries the same sign at that lag. Said plainly: when
rentals are strong, power projects withdraw less about two quarters later, and when rentals fall under
trend, the queue starts shedding projects.

The shorter lags are mixed and the three month change flips sign with the lag (positive at one and three
months, negative at six), so the level reading is the one to keep and the change reading is not a clean
phase marker.

The placebo contrast behaves: speculative technologies (solar, battery) carry a mean hazard of 0.00156
against 0.0001 for firm ones, fifteen times the risk, so a marker that acts on the speculative tail is
acting where the risk actually sits.

The fact this leaves: compute rental levels behave like a phase marker for the physical queue with a two
quarter lead, at the edge of significance (the shift test has 19 shifts, so the attainable share is 0.05)
and with thirty cells tested across lags, groups and readings. Development evidence, not established.
Keep the level reading, drop the change reading, and treat this as the demand side sensor for thesis C.
