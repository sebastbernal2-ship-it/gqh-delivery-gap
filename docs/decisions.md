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

---

## 2026-10-03: Integration of the first teammate push, and what the audit changed

**Decision.** Vishnu's handoff landed on `main` while this branch was mid-edit. Integrated by rebase,
not by merge.
**Conflict.** Both branches created `docs/writing/style.md` independently. Resolved by keeping both
halves in one file: how we write about evidence (his, kept as written, and he owns the file) and how
the prose reads. A file cannot have two owners, so the file now names one.
**Audit findings, fixed.** Running the whole path on a fresh clone found six defects: `make check`
failed on a clean clone because an egg-info directory appeared in the filesystem scan, so the
structure check now reads git; `doctor` compared file times, which a clone resets, so it now compares
generated content and the renderer is deterministic; `bootstrap` printed two commands that no longer
exist; `.cursorrules` pointed at two documents deleted in the trim; the credential gate flagged a
variable named `TOKEN` assigned a regex, which would have blocked future pushes; and `pyproject.toml`
carried dependencies for code that no longer exists.
**New gate.** `scripts/check_paths.py` verifies that every path a tracked document references exists.
It found the stale `.cursorrules` references. Its precision matters: it ignores the path part of a URL
and prose that merely looks path-shaped, because a gate that cries wolf gets switched off.
**New area.** `.cursor/` is allowed as a harness configuration area, like `.githooks/`.
**Memory honesty.** Vishnu flagged that shared memory described the archived attempt; that was
correct. Entries asserting the parked attempt's out-of-sample split were removed, and `docs/memory.md`
now states the rule: an entry records what was known when it was written, the branch wins over the
entry, and stale entries are fixed at the source.

---

## 2026-10-03: Publish Aidan research as a linked handoff, preserve proposal status

**Decision.** At Aidan's request, publish the conversation history and proposed implementation contracts in `docs/inbox/aidan-2026-10-03/`, with the historical reasoning in `docs/thinking/aidan-2026-10-03.md`. Link the existing provider audit and writing conventions rather than duplicate their ownership.

**Reason.** The team needs the corrections and intuition behind the design, not just a final slogan. Separate physical forecasts, financial signals, risk, execution and independent cluster workloads through explicit contracts before parallel implementation.

**Boundary.** This adopts the documentation placement, not the proposed trading rule, runtime languages, OOS dates or every advanced method. No active thesis is promoted and the archive stays parked. The generated current-position file is unchanged.

---

## 2026-10-03: Correction: no Ornn compute futures are listed

**Decision.** Record that the compute-price curve is not yet tradeable, and treat the earlier claim
in this repo as wrong.
**Evidence.** ICE Futures U.S. notice, 29 September 2026: the OCPI H100 (HPR) and OCPI B200 (BKL)
contracts are announced as planned, "no listing date or timeline has been set at this time", and
listing waits on a CFTC request-for-comment period. The data available meanwhile is explicitly
**hypothetical** daily settlement, published to let participants build systems.
**What this corrects.** An earlier statement, in the shell author's idea document and in chat, said
ICE had listed an OCPI H100 future and that the complex therefore had a listed forward curve. That
was wrong. Aidan's advanced-method research caught it. The corrected position: OCPI is a published
benchmark index of executed rentals, which is usable as a state variable; there is no listed curve
to trade or to read expectations from.
**Why it matters.** A strategy step that assumed a tradeable forward curve does not exist yet, and
any hedging argument that depends on it is unsupported. The parked attempt sits on
`archive/w0-delivery-gap` and is not rewritten; this entry supersedes the claim for anyone reading
main.

---

## 2026-10-03: One ownership table, and a check to keep it that way

**Decision.** `OWNERS.md` holds one roster and one claim table. Ownership rows are added to it, never
appended as a second section with its own table. `scripts/check_owners.py`, run by `make check`,
enforces it.
**Context.** Three teammates pushed within twenty minutes and `OWNERS.md` grew three separate
ownership blocks, one stale summary paragraph describing only the first push, and two names for one
person (`zifeiliu` in a document, `lucyrunner` in the roster). Nobody did anything wrong; the file had
no shape that resisted growth.
**Alternatives.** Leaving it to review was rejected: this file is read by every agent that opens the
repo, so drift here propagates into editing decisions.
**Open.** Whether `zifeiliu` and `lucyrunner` are the same person on the HiPerGator allocation needs
confirmation from the captain, not a guess by an agent.

---

## 2026-10-03: The unitary alignment document, synthesised from three handoffs

**Decision.** `docs/alignment.md` is rewritten as the single statement of how this team thinks,
synthesised from all three handoffs plus what building the shell taught us. Vishnu's proposal, Aidan's
reasoning and Lucy's access discipline are absorbed into one voice rather than left as three
competing alignment documents.
**Owner.** The shell author, changed by proposal plus an entry here. Vishnu's proposal correctly
declined to overwrite the shared file unilaterally, so this is the review it asked for.
**What the synthesis adds beyond any single handoff.** A single sentence vision (we trade the gap
between a promise and a delivery, measured as a revision against an earlier public expectation) with
everything else declared subordinate to it; the confidence ladder stated as a sequence that must not
be skipped; revisions-versus-labels and availability stated as hard rules; and a section that records
where the three handoffs genuinely disagree.
**Divergences recorded, not resolved.** Component taxonomy, pilot instrument, measurement object
(critical path versus backlog timing), horizon, and the typed-extractor identity. Each is listed in
`docs/alignment.md` with both positions. Resolving them is a captain decision, not an agent's.
**Correction carried in.** Vishnu was right that no compute future is listed; Aidan was right that
Jev and Laya are identified. Both are in the record.
**Alternatives.** Keeping three alignment documents was rejected: three statements of method is how a
team ends up with none. Averaging the differences away was rejected for the same reason.

---

## 2026-10-03: Adopt the training material's Investment Proposal shape, keep our gates inside it

**Decision.** A thesis record is an Investment Proposal with four required sections: Hypothesis,
Data, Methodology, Results. Ours adds Falsifiers, Costs and capacity, and Limitations. A record
template lives at `docs/theses/TEMPLATE.md`, and `make check` fails an **active** thesis whose record
is missing a section. Non-active records are exempt.
**Source.** `algogatorstraining.com/qr-home.html`, captured 2026-10-02 while the site was reachable:
the four-section Investment Proposal, the 2b data approval gate, and the performance metric list.
Both training domains timed out on re-check, so the comparison in `docs/alignment.md` is a reading of
that capture plus the public `algogators.com` summaries, not a live citation. Their ten-week
three-phase curriculum and the society's eleven-week curriculum disagree; neither is quoted here as
current without a check.
**What we adopt.** Their record shape; a **named data gate approver** on an active thesis; their
metric list reported alongside ours; "optimise cautiously" as an explicit step inside development
folds with the variant count recorded; and a deployment stage, which maps to execution feasibility
and capacity because this track has no live P&L.
**What we keep.** The confidence ladder, the named counterparty, revisions against an earlier public
expectation, availability times, labels-are-not-features, pre-registered falsifiers, independent
shocks, costs and joint tails as part of the mechanism, and tools that must earn their place.
**What their method criticises in ours.** Their framework is short and produces a result; ours is long
and prevents being fooled. Ours can win the argument and lose the weekend. Adopted counter-rule: one
event family, one horizon, one pilot, one result artifact, and if a choice arises between another
governance improvement and the first honest number, take the number.
**Enforcement.** Four new tests on the ledger check (15 total in that suite).

---

## 2026-10-03: Insert the two missing stages, and make the rubric structural

**Decision.** The development pipeline is eight stages, not four. Stage 3 **Structure** and stage 4
**Identification** sit between Data and Methodology, and stage 7 **Decomposition** follows the first
test. `docs/alignment.md` sections 13 to 15 own them, with the exposure budget as a named artifact.
**The gap this closes.** Both the training material's four sections and our earlier method jumped from
Data to Methodology. Nothing measured the world's joint structure, so assumptions were asserted rather
than derived, and nothing checked afterwards whether the strategy was holding only the exposure it
intended. The captain's reading of the framework was right, and it was our gap too.
**What stage 3 produces.** Marginal distributions with tails and censoring; dependence beyond
correlation; association screens with multiple-testing control; shared-shock clusters; sub-period
stability; and an explicit split between what is identified and what is merely associated. Its gate:
**every assumption downstream cites a measurement here.**
**What stage 4 produces.** For each load-bearing arrow, an identification design and an estimand. Its
gate: no trade-driving arrow may remain merely inferred.
**What stage 7 produces.** Factor and regime attribution of returns and risk, realised exposure versus
the budget, the residual share, fragility by regime, and the hedge map. Unintended exposure is hedged,
sized down, or dropped. Its output loops back to stage 3.
**Rubric enforcement.** An active thesis record must carry one section per criterion — Hypothesis,
Data, Structure, Methodology, Results, Novelty, Risk, Liquidity — and `make check` fails if any is
missing. The rubric is now a structural requirement, not an aspiration.
**Honest limit, recorded.** A method can guarantee the evidence is produced and auditable. It cannot
guarantee the numbers are good. Criterion 02 is the second limit: the template forces a novelty claim
and the anti-imitation check, but cannot manufacture a real novelty.

---

## 2026-10-03: The system view enters the rationale, not the aftermath

**Decision.** `docs/alignment.md` section 16 ("From a case to a system") is added, and stages 1, 3, 5,
6 and 7 now require the system measurements. Risk, regimes, liquidity and capacity are considered in the
preliminary rationale rather than reported afterwards.
**The gap.** Our method could be satisfied by one well-researched event. That is a case study, not a
quant strategy. It never asked why we get paid, ignored breadth, treated risk as categories instead of
portfolio-level controls, treated capacity as a report rather than a constraint on which expression we
trade, and had no latency budget.
**Four edge channels, now required with evidence.** Data, inference speed, processing, portfolio craft.
If none can be named, the honest position is that we have no edge and we say so. This is the question
the rubric's Innovation criterion is really asking, and it is the anti-blackbox anchor.
**Breadth arithmetic.** IR ≈ IC × √BR, with effective breadth after clustering. A single event family
with thirty shocks a year needs an enormous IC to matter, so breadth is a design lever, not a hope.
**Regimes are design.** States defined on past-only data; performance, exposure and cost reported
conditionally; the trade rule (all-weather, state-gated, state-scaled) chosen up front; a named failure
regime.
**Portfolio construction is where risk is made.** Weights from forecast and uncertainty, correlation-
aware risk budgeting, per-name and per-cluster caps, the exposure budget binding, turnover and
cost-aware. A portfolio of correlated signal names is one bet.
**Capacity constrains the expression.** If capacity is below intended capital, change the instrument,
basket, horizon or book size rather than keeping the aspiration.
**Latency stated honestly.** Measure public availability → receipt → parse → signal → order against the
signal's information half-life. For filings and operational data the half-life is hours to days, so the
claim is same-session inference, not colocation. Microstructure work stays a separate study with its own
mechanism and evidence.
**Reconciliation.** The counter-rule (one event family, one horizon, one pilot, one artifact) still
governs pilot scope. Section 16 adds measurements to the pilot, not scope: the edge-channel claim, IC,
decay, effective breadth, regime splits, the capacity curve and the measured latency chain.
**Enforcement.** The eight required record sections are unchanged, but their content requirements are
deepened, and `docs/theses/TEMPLATE.md` carries the new requirements.

---

## 2026-10-03: Newer markets enter by paired shocks and by role, never by pooled history

**Decision.** `docs/alignment.md` section 17 defines how perpetuals, compute markets and other
short-history venues take part.
**The problem, stated.** A decade-plus filings core and a two-year perpetual cannot be one study.
Validation does not transfer across venues. A four-step or eight-stage pipeline that ignores this
either excludes the interesting markets or fakes their history.
**The move.** The unit of observation becomes the **shock**, not the calendar. Each independent shock
in the core is also measured in the new venue where both exist. The shock count is inherited from the
long market, the event is held fixed, cross-venue agreement is evidence the mechanism is real, and the
cross-venue difference is information about each venue's participants. Limits stated: the overlap subset
carries sign and mechanism evidence, not statistical weight.
**Four roles.** Confirmation, expression or hedge vehicle, execution laboratory, monitor. Only the
expression role enters performance, with its own capacity curve and attribution. A compute index is a
state variable, not a leg; a compute future that does not list cannot be traded, and if it lists it is a
new study.
**Admission gate.** Eight checks, including a point-in-time universe with delistings, venue-specific
cost and liquidation modelling, a stated number of overlapping shocks, its own falsifier, and its own
result artifact.
**Backtest integrity.** Ten named hazards with controls: clocks and calendars, no official close,
funding in P&L, venue risk, survivorship and endogenous listings, timestamp semantics, one-regime
history, time-varying liquidity, treating an index as an instrument, and pooling. Each is a way to
produce a fake result, so each gets an explicit control.
**Sequencing.** Satellites come after the core passes its own gates. Inclusion has a real cost in
sample, venue risk and rubric clarity, and that trade-off is written down rather than wished away.
