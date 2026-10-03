# Decisions

Append only. Newest at the bottom. Every settled decision goes here, once.

Decisions about a parked attempt belong on that attempt's branch, not here.

A decision is anything that would be expensive to reverse: the mechanism, the universe, the
out-of-sample cut, the cost model, a schema change, who owns what.

---

## 2026-10-02: One public repo is the source of truth for shared memory

**Decision.** `github.com/sebastbernal2-ship-it/gqh-delivery-gap` is public and holds the shared
memory, the decision ledger, the ownership map, and the artifact schema. Local agent memory and chat
are caches. If it is not in the repo, it is not shared.
**Context.** Four devices, four people, one deadline. Chat and local memory stores do not converge on
their own.
**Alternatives.** A private repo until submission was offered and rejected: a broken link at the
deadline is a bigger risk than early visibility.

---

## 2026-10-03: Memory capture is mechanical, not a habit

**Decision.** Three automatic layers, no remembered commands.
1. Agent hook: `hippo hook install pi` and `codex` write capture instructions into the committed
   `AGENTS.md`, so a session injects context at the start and captures a summary at the end.
2. Commit hook: `.githooks/pre-commit` refreshes the shared memory on every commit and stages
   `memory/`, enabled per clone by `make bootstrap` or `git config core.hooksPath .githooks`.
3. Opt-in timer: `make schedule` runs `scripts/autoshare.sh` every 15 minutes, which commits and
   pushes only the memory files, never work in progress.

**Context.** The captain rejected relying on anyone remembering `make remember`. Capture had to
happen without a human step.
**Alternatives.** Requiring a share tag on every memory was rejected as the primary rule: it makes
capture depend on discipline. Replaced by the scope rule: if the store lives inside the repo, every
entry in it is project scope by construction. The tag remains the rule only when the store lives
outside the repo.
**Evidence.** An untagged memory written at 04:32 travelled into commit `1f68040` through a plain
`git commit` with no memory command run by hand. The hook exits 0 when hippo is absent or when
there is nothing to share, so it can never block a teammate.

---

## 2026-10-03: Teammates get write access as collaborators, not forks

**Decision.** aidanq06, vshnu1, and lucyrunner are invited to `gqh-delivery-gap` with write
permission. They push to `main` inside the paths they own, which is what the one-writer-per-path
rule assumes.
**Context.** The workflow is built around direct commits with `make sync` before and `make save`
after. A fork and pull request flow would add a merge step per change with a deadline inside 30
hours.
**Alternatives.** Fork and pull request was offered and rejected. Pushing everything through one
account was rejected because it breaks authorship and creates merge races.
**Open.** Workstream ownership in `OWNERS.md` is still unassigned. Until a row has a name, nobody
writes to that path.

---

## 2026-10-03: The knowledge layer is a ledger with generated views, not a set of documents

**Decision.** The idea lives in records, not in documents that must be kept current.

- `docs/theses/index.jsonl` is an append-only ledger, one line per thesis: id, title, status,
  owner, date, note, falsifiers, evidence, supersedes.
- `docs/theses/<id>.md` is the record itself, one file per thesis, one writer per file.
- `docs/CURRENT.md` is **generated** from the ledger by `make current`. It is the live position and
  it cannot go stale, because nobody maintains it by hand.
- `docs/inbox/` takes anything: drafts, half ideas, critiques, dumps. No template, no rules.
- `docs/history/` keeps superseded snapshots as evidence of what the team rejected.
- `docs/00-brief.md` is the only frozen document, because it is the track's own rules rather than
  our thinking.

**Context.** The captain's direction moved completely within a day, which would have left a
conventional set of documents stale and misleading. A structure that must be kept current by
discipline will not survive a shifting idea with four people working at once.
**Why this shape.** Appending a line to a JSONL file is conflict free, so two people can move the
idea at the same time without editing one shared document. Records are never overwritten, only
superseded, which preserves the rejected reasoning that the note is scored on. Adding a thesis
costs one file and one line, so the structure scales with the idea rather than constraining it.
**Alternatives.** A single idea document kept current by discipline was rejected: it is exactly the
bible this replaced. A wiki-style index with many writers was rejected because concurrent edits to
one file are the main source of conflicts.
**Enforcement.** `make check` validates the ledger: required fields, unique ids, resolvable
`supersedes`, a falsifier and an owner on every active thesis, and an existing note file.
`make doctor` reports the active count and flags `CURRENT.md` older than the ledger.
**Snapshot.** The 2026-10-02 idea and system documents moved to `docs/history/` with a superseded
banner. Nothing was deleted.
