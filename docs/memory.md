# Shared memory and sync

## The rule

**The repo is the source of truth.** Local agent memory, editor memory, and chat are caches.
If a fact matters to the team and it is only in a cache, it does not exist.

## Where a fact goes, once

One owner per fact. Never copy a fact into a second file. Link to the owner instead.

| Fact | Owner |
|---|---|
| Track rules, deadline, rubric, out-of-sample rule | `docs/brief.md` |
| Each thesis, one file per claim | `docs/theses/` |
| Each thesis, one file per claim | `docs/theses/` |
| Anything settled | `docs/decisions.md` |
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

### Capture is mechanical

Nothing here depends on a person remembering a command.

1. **The agent.** `make hooks` (once per machine) wires the wrapper for whichever harnesses you
   have. Two halves, and the split matters:

   | Harness | Committed instruction file | Per-machine wrapper |
   |---|---|---|
   | pi, codex, opencode, openclaw | `AGENTS.md` | settings or plugin in your home directory |
   | Claude Code | `CLAUDE.md` | `~/.claude/settings.json` entry |
   | Cursor | `.cursorrules` | rule file, no wrapper needed |

   The instruction files are committed, so a teammate who clones and reads their harness file has
   the protocol even before they run `make hooks`. The wrapper is what makes capture automatic on
   that machine. A teammate without hippo installed still gets `memory/SHARED.md` and `docs/`,
   because those are plain files in the clone.
2. **The commit.** `.githooks/pre-commit` runs the share step on every commit and stages
   `memory/`. Enable it once per clone with `make bootstrap`, or by hand:
   `git config core.hooksPath .githooks`. It never blocks a commit.
3. **Scope, not tags.** If the store lives inside the repo, every entry in it is project scope by
   construction, so an untagged memory is shared without anyone tagging anything. If the store
   lives outside the repo, the default is deny and only project-tagged entries are shared.

Redaction and the credential rules apply in both modes.

### Why not `hippo import --file`

Because it does not do what the name suggests. Import parses the JSON as plain text and writes one
memory per line, so the store fills with fragments such as a bare `"id": ...` string. Absorb
therefore compares normalized content against the local export and calls `hippo remember` once per
missing entry. It is idempotent. `tests/test_memory_absorb.py` covers the diff logic.

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

If a fact matters to the team, it goes in `docs/`, at its owner, in a commit. The local store is
for your own recall during a session, and `make share` publishes the part that belongs to the team.

## Why this beats separate memory stores

Four people with four local memory stores drift. Each one remembers a slightly different
version of the mechanism, the universe, and the cost model. Because the note must match the
code exactly, drift is not a style problem, it is a scoring cap.

So durable knowledge lives in files, in git, with one writer each. Any device that pulls has
the same memory as every other device.

## Why one project's memories can show up in another project's session

This happened, and it is worth naming so it does not happen again.

Hippo can install machine-wide hooks. The Claude Code setup on the captain's machine runs, on
every prompt in every project:

```
hippo context --pinned-only --include-recent 5
```

That injects the most recently written memories **from the store resolved at that session's
working directory**. So any project memory written into a shared parent store surfaces in whatever
session resolves that same store, including sessions for other projects entirely.

Two consequences, both now handled:

1. Project memories must live in a store at the repo root, never in a shared parent store.
   `make doctor` checks this and reports `scope: this repo only` when it is right.
2. Installing machine-wide wrappers is not part of the normal setup here.
   `make hooks` only touches committed instruction files. `make hooks-global` is the explicit
   opt-in for the wrappers that edit your home directory, and it says so before it runs.

## The one rule that keeps stores from mixing

A memory belongs to the store at the **repo root**, and hippo resolves the store from the
directory you are in. Write project memories from inside the repo, never from a parent
directory, or they land in the parent store and a session in a different project will recall
them.

That error did happen once and was cleaned up on 2026-10-03: two quanthacks memories written
before this repo had its own store landed in the workspace store, where any other project's
session could recall them. They were removed. The check is cheap:

```
cd <repo> && hippo status        # should show only this project's memories
```

`make share` prints the store it resolved and the mode it used, so a wrong store is visible in
the output rather than silent.

## Sync protocol

1. `make sync` before you start. Pull before you type. Shared memory arrives with it.
2. Stay inside the paths you own. `OWNERS.md` is the authority.
3. `make save M="what changed"` when a unit of work is done. One logical change per commit.
4. If you changed a `results/` file, run `make check` first.
5. `make sync` again before you stop for the night. Never leave unsynced work on one machine.

## What never goes in the repo

Credentials, API keys, `.env` files, large data files, and anything under `data/`. See `.gitignore`.
Data is fetched by `make bootstrap` and by the fetch scripts, never committed.
