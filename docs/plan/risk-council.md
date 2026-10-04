# Collecting the dates the risk-track council experiment needs

Status: collection protocol, development only. Owner: sebas. Date: 2026-10-04.
Plan builder: `scripts/build_live_risk_plan.py`. Plan format owner:
`hpc/probabilistic-council/LIVE_EXECUTION_RISK.md`.

## Why dates, not hours

The risk-track comparison (`docs/plan/jev-council-comparison.md`) needs an execution-risk cache
with five whole UTC dates assigned to five roles, and the trainer's engineering floor is at least
three dates each in training, gate fit and evaluation. Repeated connections inside one date are
one session, so a longer block on one day cannot fill the roles. The binding constraint is
calendar days, not bytes.

## The sequence for each date

1. Record one bounded block with `record_execution_tape.py` into its own directory. The recorder
   writes `capture.json` with the receipt and a journal with per-message receipt clocks.
2. Export with `export_execution_capture.py --capture <dir> --output <objects>`, producing
   segment-separated Parquet objects and `inventory.json`.
3. Freeze the role plan with `build_live_risk_plan.py`, which checks that every captured receive
   date has exactly one role, that roles advance chronologically, and that both pins are real
   hashes. Freeze the plan before any labels are read.
4. Prepare with `prepare_live_execution_risk.py --plan <json> --output <cache>`. If any role has
   no usable cases, the output is `coverage.json` only; no partial cache is packaged.

## Readiness conditions before the comparison runs

- All five roles present with usable cases; one date per role at minimum, three per fitting role
  for the trainer's floor.
- Every captured date carries a role, and the roles are chronological.
- The plan's hashes match the bytes on disk at preparation time.
- The comparison protocol is already declared and frozen.

## What runs when ready

```sh
python3 scripts/build_live_risk_plan.py --pair CAPTURE:OBJECTS ... --output /local/risk-plan.json
# then, from hpc/probabilistic-council:
python3 prepare_live_execution_risk.py --plan /local/risk-plan.json --output /local/risk-cache
python3 council_comparison.py --cache /local/risk-cache \
  --checkpoints checkpoints/hpg-44665003 --output /local/comparison-001
```

The comparison recomputes each checkpoint's published evaluation pinball as its reproducibility
anchor, so a mismatched cache fails loudly rather than scoring quietly.

## Current status

One six-hour block is recording today. It supplies training-date volume only; four further UTC
dates are needed before the role set is complete, and the collection is passive from here. The
capability itself is validated: the record, export, plan and prepare path is implemented, and the
plan builder's contracts pass.
