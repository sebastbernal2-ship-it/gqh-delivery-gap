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

## The bridge: local stores, filtered into the repo

Every session recalls from whatever memory store is local to its device. That is the fast path,
and it stays. The problem it does not solve is that four devices have four stores that drift.

So there is a bridge, and it runs in both directions.

**Out, at the end of a session.**

```
make remember M="what you learned"   # tags it gqh, which is the share tag
make share                           # exports, filters, writes the shared files
```

`make share` alone exports the local store, filters it, and writes:

| File | Purpose |
|---|---|
| `memory/shared.json` | Machine readable, importable, committed |
| `memory/SHARED.md` | The same content as readable text, committed |

**In, at the start of every session.** `make sync` pulls and then runs `make absorb`, which imports
`memory/shared.json` into the local store. Now local recall finds the team's memory, with no extra
step for anyone to forget.

### What is allowed into the shared files

Default deny, then redact. A local entry is shared only when:

1. It carries a share tag: `gqh`, `quanthacks`, or `gator-quant-hacks`. Everything else stays local.
2. It survives redaction. Absolute home paths, Windows user paths, and Mac user paths are rewritten
   to portable placeholders. Credential-shaped content is dropped whole: key assignments, known key
   prefixes, private key blocks, and token shapes.

The filter is `scripts/memory_filter.py` and it is tested by `tests/test_memory_filter.py`. Run
`make test`.

`memory/shared.json` and `memory/SHARED.md` are committed. Everything else in `memory/` is
gitignored, because a full local store holds machine state that must not be published.

There is a second gate, `make secrets`, which scans every file in the repo for credential
shapes. `make check` runs it. If it reports a hit, do not push until it is clean. This repo is public, so a failure here is a leak, which is why the rules are enforced
by code and not by good intentions.

If an entry you wanted to share gets dropped, do not loosen the filter. Write the fact into `docs/`,
at its owner, where a person can review it in a diff.

### One time seed

`bash scripts/memory-seed-shared.sh` rebuilds the shared files from every memory in the project
store, ignoring the share tag. Use it once, when a store already holds a body of project memory,
and review the diff before committing.

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
