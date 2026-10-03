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

**Decision.** Two automatic layers, no remembered commands.
1. Agent hook: `hippo hook install pi` and `codex` write capture instructions into the committed
   `AGENTS.md`, so a session injects context at the start and captures a summary at the end.
2. Commit hook: `.githooks/pre-commit` refreshes the shared memory on every commit and stages
   `memory/`, enabled per clone by `make bootstrap` or `git config core.hooksPath .githooks`.
The unattended timer (`make schedule`, committing only the memory files on a 15 minute cron) was
built and then removed as unnecessary surface: the commit hook already runs on every commit.
Restore it from `archive/w0-delivery-gap` if a session ever produces memories without a commit.

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
- `docs/brief.md` is the only frozen document, because it is the track's own rules rather than
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

---

## 2026-10-03: The layout is a fixed set of slots, and `make check` keeps it that way

**Decision.** Every category of work has one named home, and the root stays a short list.

| Category | Home |
|---|---|
| The track's rules | `docs/brief.md`, the only frozen file |
| The live position | `docs/CURRENT.md`, generated from the ledger |
| Claims | `docs/theses/<id>.md` plus one line in `docs/theses/index.jsonl` |
| Settled calls | `docs/decisions.md`, append only |
| Drafts and dumps | `docs/inbox/`, no rules |
| Process, back and forth, revised thinking | `docs/thinking/`, one file per person per day |
| How we think | `docs/alignment.md` |
| The note and the writing | `docs/writing/`, one file per section |
| Code | `src/<component>/` with its own README |
| HiPerGator approaches | `hpc/<approach>/` with its own README, outputs not committed |
| Numbers the note quotes | `results/` |

**Context.** Four people are about to push process logs, revised thinking, strategy code, data
processing, two approaches to HiPerGator, and writing, all at once. Without fixed slots that lands
in the root and becomes unnavigable, and the cost of fixing it later is renames across everyone's
branches.
**Why this shape.** Each slot answers "where does this go" without a conversation, and each
important one has a single writer, so parallelism does not create conflicts. `docs/thinking/` and
`docs/inbox/` deliberately have almost no rules, because a landing zone with rules is a landing
zone people avoid.
**Enforcement.** `scripts/check_structure.py`, run by `make check`: the root accepts only known
entries, and every directory under `src/` and `hpc/` must carry a README. Four tests cover it.
**Alternatives.** Letting the layout emerge was rejected: with four people and a shifting idea, an
emergent layout becomes a mess faster than it becomes a convention. A single schema file describing
every future directory was rejected as speculative.

---

## 2026-10-03: Parallel work is solved by decomposition first, branches second

**Decision.** One writer per file. Components are split by concern with an `INTERFACE.md` as the
seam. Branches are for risky or overlapping work, pushed immediately, rebased often, merged the same
day. An interface change is a decision, because it is the only change that breaks work in flight.
**Context.** Three people editing one file is the concrete case: a strategy implementation, a
low-latency port of it, and cluster integration. Under any branch model that produces a conflict,
because git merges lines rather than intentions.
**Why this shape.** Decomposition removes the conflict instead of scheduling it. With disjoint paths,
four agents run at once and every change lands. The shared artifact is the interface, which changes
rarely and on purpose.
**Tooling.** `make claims` and `make overlaps` read the pushed branches and report collisions and
drift before merge time, using branches rather than a claim file, because a claim file goes stale and
branches do not. `make worktree NAME=...` gives a workstream its own checkout so two agents never
share a directory. `.githooks/pre-push` warns about collisions and never blocks a push.
**Verified.** Two branch push to the same file was detected by `make overlaps` and warned about by the
pre-push hook, without blocking. Seven tests cover the report logic (tests/test_claims.py).
**Alternatives.** Requiring pull requests for every change was rejected: it adds a merge step per
change and the deadline is measured in hours. One long-lived branch per person was rejected: it
delays every conflict to the worst possible moment.
 
---

## 2026-10-03: Vishnu's conversation is captured without promoting a trading thesis

**Decision.** Store this chat's handoff in `docs/inbox/vishnu-2026-10-03/`, its reconstructed
thinking history in `docs/thinking/vishnu-2026-10-03.md`, and writing conventions in
`docs/writing/style.md`. README and agent guidance route readers there. OWNERS names the writer
for those actual documents; proposed code/HPC components remain unassigned and unimplemented.

**Context.** The user asked to push current progress, revisions, intuition and scalable technical
boundaries for other agents. Main has no promoted thesis; shared memory includes archived work.
The handoff distinguishes that historical work from current capabilities and separates reported
access from tested downloads. Earlier missing assistant responses are not fabricated.

**Scope.** This is a documentation/coordination decision, not approval of a universe, signal,
OOS split or trading leg. Alignment content remains a proposal for its shared owner. Frozen brief,
generated CURRENT and the empty thesis ledger are unchanged. No credentials or raw data are added.
