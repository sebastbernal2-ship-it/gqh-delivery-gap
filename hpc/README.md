# HiPerGator

Cluster access and compute work live here. Shared account/setup notes belong in `hpc/setup/`;
job scripts and environments belong in one directory per research approach, so two ideas can be
tried in parallel without fighting over the same files.

```
hpc/setup/               non-secret cluster access and setup handoff
hpc/<approach>/          job scripts, environment spec, and a README saying what it computes
hpc/<approach>/README.md what it runs, what it needs, what it produced
```

The first probabilistic-council pilot is in [`probabilistic-council/`](probabilistic-council/README.md).
It is CPU-only and synthetic; it validates the distribution and job interfaces, not the trading
idea or any model's predictive value.

## Rules

1. Scripts are committed. Outputs are not. Keep runs, logs, and result blobs outside the repo or
   in an ignored path.
2. Only summaries come back: a small JSON or markdown in `results/` that the note can quote.
3. Every job records what it needs: modules, GPU type, wall time, allocation.
4. A job that produced a number in the note is named in the note, so a judge can find it.

`make check` fails if a directory here has no README.
