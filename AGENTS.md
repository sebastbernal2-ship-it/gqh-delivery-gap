# Working in this repo

Read this before you touch anything. It applies to every agent and every person on any device.

## What this is

The GQH 2026 Systematic Trading entry (track callsign VECTOR, sponsored by Webull). Due Sunday
2026-10-04 at 10:00 ET. Two deliverables: a quant note PDF of at most 5 pages, and this public repo.
There is no P&L leaderboard. Judges score reasoning and rerun the code.

## Start of every session

1. `make sync`. This pulls the team's work and loads their shared memory into your local store,
   so ordinary recall finds what the team already knows.
2. Read `memory/SHARED.md`. It is the team's memory, filtered and redacted for this public repo.
3. Read, in order: `docs/00-brief.md`, `docs/01-idea.md`, `docs/02-system.md`,
   `docs/03-decisions.md`. Then `OWNERS.md` for who owns which path.

Do not re-derive what is already settled. `docs/03-decisions.md` is the record.

## Where a fact goes

One owner per fact. Never copy a fact into a second file, link to the owner instead.

| Fact | Owner |
|---|---|
| Track rules, rubric, deadline, out-of-sample rule | `docs/00-brief.md` |
| The strategy and its mechanism | `docs/01-idea.md` |
| Engines, workstreams, timeline, cuts | `docs/02-system.md` |
| Anything settled | `docs/03-decisions.md` |
| Who owns what path | `OWNERS.md` |
| The shape of a result file | `results/README.md` |
| A critique of the idea or the plan | `docs/reviews/` |
| Numbers the note quotes | `results/*.json` |
| How memory is shared | `docs/04-memory.md` |

## Rules that decide the score

1. Every number in the note comes from a file in `results/`. Regenerate, never hand-edit.
2. The out-of-sample window is opened once, by its owner, and reported whether good or bad.
3. Write the hypothesis and the falsifier before you look at results.
4. Report every number net of costs, and show what happens when costs double.
5. Stay inside the paths your workstream owns.

## End of session

If you learned something durable, share it:

```
make remember M="what you learned"     # tagged gqh, so the team gets it
make share                             # writes memory/SHARED.md and memory/shared.json
make save M="what changed"
```

Never commit credentials, absolute local paths, or anything under `data/`.
