# GQH 2026 Systematic Trading: the delivery gap

Entry for Gator Quant Hacks 2026, Systematic Trading track (callsign VECTOR, sponsored by Webull).

Two deliverables, both required, due Sunday 2026-10-04 at 10:00 ET:

1. A quant note as PDF, at most 5 pages including figures and tables.
2. A link to this public repo.

There is no P&L leaderboard. Judges score reasoning on five criteria, 10 points each, and
they rerun the code. Criterion 5 is capped at 4 if the code does not run, does not match the
note, or shows lookahead or out-of-sample tuning. The frozen brief facts are in
`docs/00-brief.md`.

## The idea, in three sentences

The AI capex complex is priced on announced capacity. Capacity is only deliverable once it
is energized, and power is the binding constraint, so the announced schedule slips in a way
that is published every month and read by almost nobody. We measure the slip as a transport
cost between promised and realized delivery dates, and we trade the spread between the
names that can deliver and the names priced as if they already had.

Full statement in `docs/01-idea.md`. Execution plan in `docs/02-system.md`.

## Layout

| Path | Owner | Holds |
|---|---|---|
| `docs/00-brief.md` | fixed | The track facts: deadline, rubric, out-of-sample rule |
| `docs/01-idea.md` | W1 | The strategy and its mechanism |
| `docs/02-system.md` | W1 | Engines, workstreams, timeline, cuts |
| `docs/03-decisions.md` | append only | Every settled decision, newest at the bottom |
| `docs/04-memory.md` | W0 | How shared memory and sync work |
| `docs/reviews/` | everyone | Critiques of the idea and the plan |
| `docs/note/` | assembler | The 5 page note source |
| `data/` | W0 | Fetched data. Not committed. See `data/README.md` |
| `src/` | per module README | Engine code |
| `notebooks/` | per engine | Exploration and figures |
| `quantum/` | W4 | QUBO and sampling experiments |
| `results/` | one writer per file | Every number the note quotes. Schema in `results/README.md` |

## How we work

1. `make sync` before you start. Always.
2. Work only in the paths your workstream owns. See `OWNERS.md`. One writer per path.
3. Commit small and push often. One logical change per commit.
4. If it is not in this repo, it is not shared. Local memory and chat are caches.
5. Every number in the note comes from a file in `results/`.
6. Never open the out-of-sample window except on the one run that reports it.

## New device, first time here

```
git clone https://github.com/sebastbernal2-ship-it/gqh-delivery-gap.git
cd gqh-delivery-gap
make bootstrap
```

`make bootstrap` checks your tooling, creates the virtual environment, installs the
dependencies, and prints the sync protocol.
