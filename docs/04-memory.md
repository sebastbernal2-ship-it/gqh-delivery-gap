# Shared memory and sync

## The rule

**The repo is the source of truth.** Local agent memory, editor memory, and chat are caches.
If a fact matters to the team and it is only in a cache, it does not exist.

## Where a fact goes, once

One owner per fact. Never copy a fact into a second file. Link to the owner instead.

| Fact | Owner |
|---|---|
| Track rules, deadline, rubric, out-of-sample rule | `docs/00-brief.md` |
| The strategy and its mechanism | `docs/01-idea.md` |
| Engines, workstreams, timeline, cuts | `docs/02-system.md` |
| Anything settled | `docs/03-decisions.md` |
| Who owns what path | `OWNERS.md` |
| The shape of a result file | `results/README.md` |
| A critique of the idea or the plan | `docs/reviews/` |
| Numbers the note quotes | `results/*.json` |

## Why this beats separate memory stores

Four people with four local memory stores drift. Each one remembers a slightly different version of
the mechanism, the universe, and the cost model. Because the note must match the code exactly, drift
is not a style problem, it is a scoring cap.

So durable knowledge lives in files, in git, with one writer each. Any device that pulls has the same
memory as every other device.

## Local memory stays on the device

Hippo and similar local stores are useful for recall during a session. Keep using them.

They do **not** get committed here. This repo is public, and a local store can hold absolute
paths, error notes, and references to credentials. Shipping that is a leak, and a leaked key
costs more than any scoring criterion.

So the shared memory is the docs, and the local store is private:

```
make memory     # writes memory/<device>.json, which is gitignored
```

Use that export to move recall between your own devices, never as the team's channel. If a
fact matters to the team, it goes in `docs/`, at its owner, in a commit.

## Why this beats separate memory stores

Four people with four local memory stores drift. Each one remembers a slightly different
version of the mechanism, the universe, and the cost model. Because the note must match the
code exactly, drift is not a style problem, it is a scoring cap.

So durable knowledge lives in files, in git, with one writer each. Any device that pulls has
the same memory as every other device.

## Sync protocol

1. `make sync` before you start. Pull before you type.
2. Stay inside the paths you own. `OWNERS.md` is the authority.
3. `make save M="what changed"` when a unit of work is done. One logical change per commit.
4. If you changed a `results/` file, run `make check` first.
5. `make sync` again before you stop for the night. Never leave unsynced work on one machine.

## What never goes in the repo

Credentials, API keys, `.env` files, large data files, and anything under `data/`. See `.gitignore`.
Data is fetched by `make bootstrap` and by the fetch scripts, never committed.
