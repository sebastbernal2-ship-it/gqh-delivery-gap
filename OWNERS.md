# Ownership

One writer per path. Two writers on one file is the only way this repo breaks.

## The four of us

| GitHub | Role |
|---|---|
| sebastbernal2-ship-it | repo owner, has push |
| aidanq06 | invited, write permission |
| vshnu1 | invited, write permission |
| lucyrunner | invited, write permission |

An invitation is not access until it is accepted. Each person accepts the GitHub invite, then runs
`make bootstrap` once and `make doctor` to confirm.

## Who takes which workstream

Fill this in tonight, one name per row. Until a row has a name, that path has no owner and nobody
should write to it.

| Workstream | Person | Owns these paths |
|---|---|---|
| W0 Data and harness | TBD | `data/`, `src/common/`, `docs/04-memory.md`, `results/costs.json` |
| W1 Event vol engine | TBD | `src/events/`, `notebooks/e1_*`, `results/e1.json`, `docs/01-idea.md` |
| W2 Coupling engine | TBD | `src/coupling/`, `notebooks/e2_*`, `results/e2.json` |
| W3 Execution and capacity | TBD | `src/exec/`, `notebooks/e3_*`, `results/e3.json` |
| W4 Quantum and compute scaling | TBD | `quantum/`, `results/e4.json` |
| W5 Note assembly | TBD | `docs/note/`, `README.md` |

Fill in the names tonight. Replace `TBD` with a name and commit.

## Interface rules

1. `results/` has exactly one writer per file. Never edit someone else's result file.
2. The JSON schemas in `results/README.md` are frozen. If a schema must change, it is a
   decision, and it goes in `docs/03-decisions.md` first.
3. `src/common/` is shared code. Only W0 writes it. Ask, do not patch.
4. The cost model lives with W3. All engines charge the same costs.
5. `docs/03-decisions.md` is append only. Never rewrite history there.
