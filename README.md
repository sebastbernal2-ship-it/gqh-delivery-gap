# GQH 2026 Systematic Trading: the delivery gap

Entry for Gator Quant Hacks 2026, Systematic Trading track (callsign VECTOR, sponsored by Webull).

Two deliverables, both required, due Sunday 2026-10-04 at 10:00 ET:

1. A quant note as PDF, at most 5 pages including figures and tables.
2. A link to this public repo.

There is no P&L leaderboard. Judges score reasoning on five criteria, 10 points each, and
they rerun the code. Criterion 5 is capped at 4 if the code does not run, does not match the
note, or shows lookahead or out-of-sample tuning. The frozen brief facts are in
`docs/00-brief.md`.

## Where we are

Nothing is settled. The direction moved on 2026-10-03 and the earlier attempt is parked on the
`archive/w0-delivery-gap` branch, so this branch holds no claim about what we are building.

`docs/CURRENT.md` is the live position. It is generated from `docs/theses/index.jsonl`, which is
empty until someone records a thesis. Drop rough work in `docs/inbox/`.

## Layout

| Path | Owner | Holds |
|---|---|---|
| `docs/00-brief.md` | fixed | The track facts: deadline, rubric, out-of-sample rule |
| `docs/CURRENT.md` | generated | The live position, regenerated from the ledger |
| `docs/theses/` | one writer per file | One record per thesis, append-only ledger |
| `docs/inbox/` | anyone | Drafts and half ideas. No rules, no template |
| `docs/history/` | nobody | Superseded snapshots, kept as evidence of what we rejected |
| `docs/03-decisions.md` | append only | Every settled decision, newest at the bottom |
| `docs/04-memory.md` | W0 | How shared memory and sync work |
| `memory/SHARED.md` | generated | The team's memory, readable |
| `AGENTS.md` | W5 | Session start rules for any agent |
| `docs/reviews/` | everyone | Critiques of the idea and the plan |
| `docs/note/` | assembler | The 5 page note source |
| `data/` | W0 | Fetched data. Not committed. See `data/README.md` |
| `src/` | per module README | Engine code |
| `notebooks/` | per engine | Exploration and figures |
| `quantum/` | W4 | QUBO and sampling experiments |
| `results/` | one writer per file | Every number the note quotes. Schema in `results/README.md` |

## How we work

Memory capture is mechanical. You do not have to remember a command.

- An agent session in this repo runs `hippo context --auto` at the start and captures a summary
  at the end. The instructions are committed in `AGENTS.md`.
- `.githooks/pre-commit` refreshes the shared memory on every commit and stages it, so your
  commits carry what you learned. `make bootstrap` enables it once per clone.
- If the memory store lives inside the repo, everything in it is project scope, so nothing needs
  a tag. Redaction and the credential scan still apply.
- `make schedule` adds an unattended share every 15 minutes if you want the belt and braces.

The rest:

1. `make sync` before you start. It pulls the team's work and loads their shared memory.
2. Work only in the paths your workstream owns. See `OWNERS.md`. One writer per path.
3. Commit small and push often. One logical change per commit.
4. If it is not in this repo, it is not shared. Local memory and chat are caches.
5. Every number in the note comes from a file in `results/`.
6. Never open the out-of-sample window except on the one run that reports it.
7. Before you stop, run `make share` if you learned something durable. See `docs/04-memory.md`.

### Branches

Default: commit straight to `main` inside the paths you own. Four people, one writer per path,
so `main` stays runnable and the repro check keeps working.

Use a branch for an attempt that is not yet a claim, the way `archive/w0-delivery-gap` is. An
attempt lives on its own branch so `main` never looks more settled than it is.

Any agent that opens this repo reads `AGENTS.md` first. It holds the session start rules.

## New device, first time here

```
git clone https://github.com/sebastbernal2-ship-it/gqh-delivery-gap.git
cd gqh-delivery-gap
make bootstrap
```

`make bootstrap` checks your tooling, creates the virtual environment, installs the
dependencies, and prints the sync protocol.
