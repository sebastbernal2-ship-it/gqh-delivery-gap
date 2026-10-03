# Decisions

Append only. Newest at the bottom. Every settled decision goes here, once.

A decision is anything that would be expensive to reverse: the mechanism, the universe, the
out-of-sample cut, the cost model, a schema change, who owns what.

---

## 2026-10-02: Build the full system design before writing engine code

**Decision.** Design all engines and the interface contract first, then distribute across four people.
**Context.** Four people had to work in parallel from the same night.
**Alternatives.** Building Engine 1 end to end first was proposed and rejected.

---

## 2026-10-02: Anchor every trade on one mechanism, and cut the rest

**Decision.** One mechanism (rule-dated disclosure plus forced hedging in the AI capex complex) with
one mathematical spine, the marginal-constrained coupling. Option smiles are the risk-neutral anchor.
**Context.** The track scores Economic Foundation first and the captain rejected blackbox pipelines.
**Alternatives.** A quantum-alpha or ML-forecast thesis was rejected. Langlands, affine Kac-Moody,
and grand unified theory were cut: real mathematical kinship, no testable prediction in the window.

---

## 2026-10-02: The strategy is the delivery gap

**Decision.** The trade is the spread between names that can deliver energized capacity and names
priced on announced capacity that has slipped. The state variable is the transport cost between the
promised and realized delivery-date distributions, computed from EIA-860M vintages.
**Context.** Announced capacity is not energized capacity. Power is the binding constraint: turbine
slots sold out years ahead, transformer lead times around 120 weeks and up to four years. EIA measured
19 percent of planned solar MW slipping in 2023 after 23 percent in 2022. Goldman Sachs put roughly
60 percent of scheduled data center capacity arriving on time. Press reporting said about half of
planned US builds were delayed or canceled.
**Alternatives.** A compute-price-only thesis was rejected because OCPI history is too short for the
mandated out-of-sample rule. A generic short-vol event study was rejected as insufficiently distinct.
**Open risk.** The power-bottleneck theme is well known and the constraint names trade rich. The edge
must be the measurement, not the theme.

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

## 2026-10-03: The delivery-gap state variable is a windowed, fixed-lag measurement

**Decision.** For each cohort (a monthly EIA-860M vintage), measure only units whose promised
arrival falls inside `[cohort, cohort + 12 months]`, and compare against the earliest vintage at
least `horizon + 6 months` later. Report W1, W2, median and p90 delay in months, MW weighted, plus
the cancellation mass per balancing authority.
**Context.** Two bugs were found by sanity checks and fixed. First, including far-future projects
understated the delay and inflated the cancellation share to 32 percent. Second, measuring every
cohort against one latest vintage mixed a measured delay with right-censored observations and made
cohorts incomparable. With the window and a fixed 6 month lag, three comparable cohorts give W1 of
3.11, 2.70 and 2.74 months, with a median of 1 to 2 months and a cancellation share of 2.4 to 4.4
percent. A technology sanity check now passes: with the window applied, natural gas combined cycle
shows no cancellations, which is what the mechanism predicts and what the un-windowed version got
wrong at 52 percent.
**Alternatives.** Using every planned unit regardless of date was rejected. Measuring all cohorts
against a single realization vintage was rejected as not comparable.
**Availability note.** EIA's September 2026 vintage returns HTTP 503, so August 2026 is the latest
usable realization vintage, and the most recent measurable cohort is therefore 2025-01 at a 6 month
lag.

---

## 2026-10-03: `results/` carries two kinds of file

**Decision.** Add `kind` to the results contract. `kind: "state"` files are inputs such as
`e0_state.json` and are checked for `engine`, `generated_at`, `git_commit`, `measure`, `coverage`,
`observations`, `notes`. Strategy files keep the existing full envelope.
**Context.** The state variable is an input to the strategy and cannot report a Sharpe ratio. Without
a second kind, `make check` would either reject it or stop checking anything.
**Alternatives.** Putting the state variable under `data/` was rejected because `data/` is
gitignored and the note must quote a committed number.

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
