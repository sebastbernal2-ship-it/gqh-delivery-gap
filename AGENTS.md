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
3. Read, in order: `docs/CURRENT.md` (the live position, regenerated from the ledger),
   `docs/brief.md` (the fixed track rules), `docs/decisions.md` (settled calls), then
   `OWNERS.md` for who owns which path. Add `docs/theses/` for the record behind each live claim.

Do not re-derive what is already settled. `docs/decisions.md` is the record.

## Where a fact goes

One owner per fact. Never copy a fact into a second file, link to the owner instead.

| Fact | Owner |
|---|---|
| Track rules, rubric, deadline, out-of-sample rule | `docs/brief.md` |
| The live position, always regenerated | `docs/CURRENT.md` |
| Each thesis, one file per claim | `docs/theses/` |
| Unfinished drafts, anything not yet a claim | `docs/inbox/` |
| Superseded snapshots | `docs/history/` |
| Anything settled | `docs/decisions.md` |
| Who owns what path | `OWNERS.md` |
| The shape of a result file | `results/README.md` |
| A critique of the idea or the plan | `docs/reviews/` |
| Numbers the note quotes | `results/*.json` |
| How memory is shared | `docs/memory.md` |
| How four people work at once without colliding | `docs/workflow.md` |

## Rules that decide the score

1. Every number in the note comes from a file in `results/`. Regenerate, never hand-edit.
2. The out-of-sample window is opened once, by its owner, and reported whether good or bad.
3. Write the hypothesis and the falsifier before you look at results.
4. Report every number net of costs, and show what happens when costs double.
5. Stay inside the paths your workstream owns, and check `make overlaps` before you edit. If
   another pushed branch touches your file, stop and report it instead of editing.
6. One writer per file. If a task needs two people in one file, split the file instead.
7. Rebase before you commit, not after: `git fetch && git rebase origin/main`.

## End of session

If you learned something durable, share it:

```
make remember M="what you learned"     # tagged gqh, so the team gets it
make share                             # writes memory/SHARED.md and memory/shared.json
make save M="what changed"
```

Never commit credentials, absolute local paths, or anything under `data/`.

<!-- hippo:start -->
## Project Memory (Hippo)

At the start of every session, run:
```bash
hippo context --auto --budget 1500
```
Read the output before writing any code.

On errors or unexpected behaviour:
```bash
hippo remember "<description of what went wrong>" --error
```

On task completion:
```bash
hippo outcome --good
```

When ending a session, capture a brief summary:
```bash
hippo capture --stdin <<< '<decisions, errors, lessons — 2-5 bullets>'
```
<!-- hippo:end -->
