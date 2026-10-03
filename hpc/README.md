# HiPerGator

Job scripts and environments for the cluster. One directory per approach, so two ideas can be
tried in parallel without fighting over the same files.

```
hpc/<approach>/          job scripts, environment spec, and a README saying what it computes
hpc/<approach>/README.md what it runs, what it needs, what it produced
```

## Rules

1. Scripts are committed. Outputs are not. Keep runs, logs, and result blobs outside the repo or
   in an ignored path.
2. Only summaries come back: a small JSON or markdown in `results/` that the note can quote.
3. Every job records what it needs: modules, GPU type, wall time, allocation.
4. A job that produced a number in the note is named in the note, so a judge can find it.

`make check` fails if a directory here has no README.
