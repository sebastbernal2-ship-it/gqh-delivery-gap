# src/event

What a firm's own disclosed revision did to its own price.

The event is a number the firm published, so the attribution is unambiguous and the timestamp is the
filing's own acceptance time. That is why this channel exists: the project-level join does not hold, since
93.8 percent of slipped capacity sits with project companies and private developers.

## the three rules it enforces

1. **Lag every signal.** A revision is usable at its availability timestamp, and the fill is the close of
   the first session strictly after it. Same-bar fills are refused by construction, not by convention.
2. **Abnormal, not raw.** Market and sector movement is the first alternative explanation, so raw and
   benchmark-adjusted returns are reported side by side.
3. **A plateau, not a peak.** Horizons of 1, 2, 5, 10 and 20 sessions are all reported, and nothing here
   elects a winner. The primary horizon must be declared before the sealed test, and picking the best cell
   afterwards would be tuning on the development window.

## Owner

`sebastbernal2-ship-it` claims `src/event/` in `OWNERS.md`.

## Use

```sh
python scripts/run_revision_event_study.py --horizons 1,2,5,10,20
```

It reads `results/obligation-panel.csv` and writes `results/revision-events.csv`.

## What the first pass found, and why it is not a result

Eighty-four timestamped revisions across PWR and ETN. Negative surprises, the direction the mechanism
predicts, show no consistent move at any horizon. Positive surprises drift 3.8 percent at twenty sessions,
but 70 of the 84 events are PWR across 41 weeks, so that is one firm's multi-year run as much as an event
effect. The rubric's own instruction is to check the simple explanation first, and the simple explanation
here is drift.
