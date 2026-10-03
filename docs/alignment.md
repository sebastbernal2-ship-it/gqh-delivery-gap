# Alignment: how we think

The single owner of how this team thinks about the problem. Not a plan, not a summary of the idea.
It is what keeps four people making the same kind of decision when nobody is watching.

Owner: the shell author. Change it by proposal plus an entry in `docs/decisions.md`, so the shared
standard stays stable while the idea moves under it.

Synthesised 2026-10-03 from the three handoffs, each of which reached these conclusions
independently: Vishnu's research alignment and thinking log, Aidan's reasoning and implementation
contracts, Lucy's access discipline. Where they differ, the difference is recorded below rather than
smoothed into a consensus nobody holds.

---

## 1. The one question

> Can an unexpected, publicly observable revision to delivery or capacity change a company's future
> economics in a way its price does not fully reflect, after controlling for ordinary earnings news,
> demand, sector and market exposure, and the cost of trading?

Everything else is context. "AI is growing" and "power is scarce" are context, not alpha.

## 2. The vision in one paragraph

**We trade the gap between a promise and a delivery, and we measure it as a revision against an
earlier public expectation.** A named project was expected to do something by a stated time. A public
release says, on a date we can point at, that this changed. We can name whose cash flows move and
why, we can name who is on the other side and why they are not already pricing it, and we can trade
the exposure. Every tool, dataset, language and machine in this repo is subordinate to that
sentence. A method that does not sharpen it is a hobby, and the repo is where hobbies go to die.

## 3. How we process a new idea

Seven steps. If a step fails, narrow the question and say so. More APIs or more parameters do not
repair a missing step.

1. **Name the mechanism and its simplest rival.** What constraint changes, and what ordinary
   explanation (earnings, demand, sector beta, liquidity) would produce the same result?
2. **Name the counterparty.** Who must pay or receive, who is on the other side of the trade, and why
   has the opportunity not been arbitraged away?
3. **Anchor on an earlier expectation.** Find dated, original observations of the forecast and its
   revision. Not today's facts, and not a number discovered later.
4. **Define the measurable quantity**, its units, and what information existed at each decision time.
5. **Audit the evidence**: independent events, comparable exposures, a tradeable instrument.
6. **Write the falsifier, the simple baseline, and the cost model before looking at returns.**
7. **Add complexity only when a development-period comparison justifies it.** Keep the sealed test
   closed.

For every intuition, write the chain and mark each arrow: observation → physical implication →
contractual implication → expected price response → tradable decision. Tag every arrow observed,
inferred, or untested. A stronger physical story does not strengthen the arrows after it.

## 4. What earns confidence, and where it stops

Confidence is local to a claim. These are different things and must never be conflated:

documentation says a capability exists → we have an authenticated entitlement → we downloaded it →
it is a valid point-in-time panel → the label is correct → the forecast is calibrated → the joint
tails are right → it trades after costs.

Most projects fail by skipping the middle. State the last verified step and the next test.

- A passing unit test proves the code runs, not that the economics are right.
- A calibrated distribution of one variable says nothing about dependence between variables.
- A model may extract fields and quote provenance. It cannot certify its own labels or invent
  missing values.
- An appealing histogram, or one strong backtest, is not an economic explanation.
- Reported capability from a vendor is not permission, licence, or accuracy.

## 5. The measurement object: revisions, availability, and labels

- **A realized outcome is a label, never an input.** What happened later is how we grade a forecast,
  not information we could have had. Signals may use two already-public vintages. Lifetime completion
  outcomes may not appear in them.
- **Availability is the binding constraint.** Record when information became public, not only the
  period it describes. Never forward-fill later information backwards. Never fill at the same bar
  the signal is read. Never give the strategy a future label as a feature.
- **A deadline is not a calendar.** A filing deadline does not by itself create a pre-announced
  tradable event. Without an ex-ante trigger, an event study is retrospective.
- **A revision is not automatically a surprise.** A move against management guidance is not a
  surprise relative to market consensus. Those are different baselines, and the difference is the
  point.
- **Identity survives aggregation.** Keep project and unit identity. A distribution distance can hide
  which project slipped. Match units, and report censoring and cancellation separately from delay.

## 6. Adequacy: independent shocks, not calendar length

Long history is a preference, not proof. Adequacy is coverage of **independent** events.

- Thousands of filings can be one project reported many times, or one common shock.
- Report event and issuer counts, shared shocks, and missingness by condition.
- Regimes matter because economics and execution change, not because a histogram has labels. Fit
  regime thresholds on earlier information only.
- Do not claim extreme-tail probabilities from a handful of events, or manufacture evidence by
  sampling a fitted model.
- Surviving today's winners is a selection bias. Choose firms by economic and data eligibility, not
  by returns, and say when we could not.

## 7. What earns a tool

Every component, model, language and machine needs: a named task, a simple comparator, a measured
benefit, and its **full** cost including research time, transfer, calibration and execution latency.

- **No advanced method is mandatory.** Optimal transport, spectral methods, martingale transport,
  typed extraction and quantum algorithms are candidates with jobs to justify. Each must beat a
  simple baseline on a defined task before becoming load-bearing, and each must be removable without
  invalidating the core.
- **Quantum:** simulator access is not quantum hardware. GPU simulation is classical computation.
  Entanglement, anticoncentration or expressivity are not alpha. A bounded optimization or sampling
  benchmark against a strong classical solver is legitimate; a quantum pillar is not.
- **Typed extraction** earns its place through provenance, reproducible fields and human review, not
  by being typed.
- **Language and storage** follow the task: q for time series, a typed language where arithmetic
  exactness matters, one low-level engine if a measured bottleneck needs it. Existing Python stays.
  Strict typing does not make floating point exact, and a columnar store is not a latency advantage.
- **Infrastructure is never an argument.** Credits, GPUs, a cluster allocation, a paid dataset or an
  API are means. "We have it" is not a reason to use it. "It was already on disk" is a red flag.
- **Exactness has a boundary.** Define price/quantity scales, rounding, overflow and null semantics
  before code. Preserve source decimal text. Keep economic exactness and statistical estimation
  separate; one does not give the other.

## 8. Boundaries we do not cross

1. No future information in a signal, ever.
2. The sealed test is opened once, by a named owner, and reported whatever it says.
3. No claim exists until it is promoted into the ledger. Inbox is not evidence.
4. No advanced method as decoration, and no infrastructure as justification.
5. No credentials, account paths, or personal data in this public repo. Access facts are reported
   with their verification status, never with values.
6. Do not rewrite the record. Supersede it, date the correction, and keep the rejected reasoning.
7. Abstention is a valid output. A system that declines to trade an ambiguous event is working.

## 9. How disagreement becomes progress

Record: the prior belief, the objection, the supporting observation, the revision, the retained
uncertainty, and the next test. Reopen a settled decision with a reason, in the ledger, instead of
working around it. Correct an overstatement openly and in place.

A negative result is evidence. It stays in the record, and it changes the research.

## 10. Where the three handoffs agree, differ, and leave gaps

**Strong agreement** (all three reached these independently): mechanism before methods; no mandatory
advanced method; confidence is local to a claim; revisions against earlier expectations rather than
levels; independent shocks rather than calendar length; a named cash-flow channel rather than a
ticker label; infrastructure never justifies a model; costs, borrow and capacity are part of the
mechanism; negative results preserved; separate studies labelled separately.

**Real differences, unresolved and not to be smoothed over:**

| Difference | Positions |
|---|---|
| Component taxonomy | Vishnu: `src/ingest`, `extraction`, `dataset`, `strategy`, `portfolio`, `replay`, `backtest`, `reporting`. Aidan: a flow of adapters → observations → facts → panel → signal → targets → execution → artifacts. Overlapping, not identical |
| Pilot instrument | Vishnu: PWR base case, SPY benchmark, feasibility audit of ETN/EME/DLR. Aidan: the transcript discussed short NVDA/GOOGL market-data pilots |
| Measurement object | Aidan: a project critical path, with phases and sequential dependencies. Vishnu: backlog timing and guidance revisions, reconciled like for like |
| Horizon | Aidan: ten sessions, offered as a guess. Vishnu: unchosen |
| Typed extractor identity | Vishnu: unresolved. Aidan: identified (TypeSafe Jev; Laya separate). Aidan is right; rights and access remain unverified |

**Gaps nobody has closed:** which disclosure family defines the event; who owns the first thesis and
the first component; the entitlement audit is still unverified; no capacity or cost model for a
chosen instrument exists; and no numbers exist at all. `src/` is empty and the ledger is empty.

## 11. What remains unresolved

Whether delivery revisions predict residual returns net of costs. Which universe has comparable
history. Whether demand and margins explain the whole effect. Event independence. Historical
expectation quality. Borrow feasibility. Whether any advanced model adds information. And whether
the remaining competition time supports the full architecture, which no handoff claims it does.

---

## 12. Cross-check: their method against ours, row by row

Sources: `algogatorstraining.com/qr-home.html` (the Investment Proposal framework and the three-phase
curriculum), captured 2026-10-02 while the site was reachable, plus the public `algogators.com` pages
on training and research workflow, summarised 2026-10-03. Both domains timed out on re-check, so this
is a reading of that material, not a live citation. One discrepancy to resolve before quoting either:
the training site describes a ten-week three-phase curriculum, the society's page an eleven-week one.

**"Silent" in the table below means the published material does not address it, not that their
practice ignores it.** Their internal standard is very likely stricter than their public summary.

### Their method, as they state it

| Section | Their requirement |
|---|---|
| 1 Hypothesis | The economic mechanism. Why does the inefficiency exist? What will the signal predict? |
| 2 Data | 2a sourcing and cleaning. 2b a quality approval gate. **Data must exist before backtest** |
| 3 Methodology | 3a signal rules. 3b model assumptions, each one tested and documented |
| 4 Results | Sharpe, annual return, win rate, profit factor, equity curve, drawdown analysis |

Pipeline: **Hypothesis → Data → Methodology → Backtest → Writeup**, versioned, optimise cautiously,
add risk controls, deploy only what survives, monitor live. Curriculum: foundations ("what defines a
research edge", contract mechanics, FX/commodities, fixed income and equity factors), then tooling and
hypothesis writing, then execution: data, signal construction, model assumptions, results.

### The comparison

Legend: **match** = equivalent; **ours is stricter** = same idea, carried further; **ours only** =
absent from their published material; **theirs only** = we adopted it; **tension** = a real conflict.

**Framing**

| Dimension | Theirs | Ours | Verdict |
|---|---|---|---|
| What starts the work | A market hypothesis and a research opportunity | A revision against an earlier public expectation with a nameable cash-flow channel | Theirs is broader as an entry point; ours is the filter it must pass |
| Mechanism named | Yes: why does the inefficiency exist | Yes, plus the simplest rival explanation | Ours is stricter |
| Who pays, who is on the other side | Implied, not required | Required and named | Ours only |
| Simplest rival explanation | Silent | Required | Ours only |
| Tag every reasoning arrow observed, inferred, untested | Silent | Required | Ours only |

**Data**

| Dimension | Theirs | Ours | Verdict |
|---|---|---|---|
| Data settled before any backtest | Explicit gate (2b) | Same rule, enforced through the confidence ladder | Match |
| Who approves the data | A quality gate | A named approver on an active thesis | Theirs, named |
| Availability: when was it knowable | Silent | Hard rule: availability binds, no forward fill, no same-bar fill | Ours only |
| A realized outcome is a label, never an input | Silent | Hard rule | Ours only |
| Entitlement versus coverage | Silent | An explicit rung: capable, entitled, downloaded, point-in-time | Ours only |
| Corporate actions, identifier mapping, delistings | Under "sourcing and cleaning" | Explicit requirements | Ours is stricter |

**Methodology**

| Dimension | Theirs | Ours | Verdict |
|---|---|---|---|
| Signal rules | IP 3a | Same, plus units, eligibility and abstention | Match |
| Assumptions tested and documented | IP 3b, explicit | Same, plus scales, rounding, overflow and null semantics | Ours is stricter |
| A baseline to beat | Silent | Required before looking at returns | Ours only |
| A falsifier pre-registered | Silent | Required | Ours only (the brief rewards it) |
| One primary horizon chosen before testing | Silent | Required | Ours only (Aidan's update agrees) |

**Evidence**

| Dimension | Theirs | Ours | Verdict |
|---|---|---|---|
| Backtest protocol | Backtest historically | Sealed test opened once by a named owner, reported whatever it says | Ours is stricter (the brief mandates a split) |
| Optimisation | "Optimise cautiously" | Only inside development folds, variant count recorded, never on the sealed test | Ours operationalises theirs |
| Multiple testing | Silent | Deflated for the number of variants, and the count is reported | Ours only (the brief cites Deflated Sharpe) |
| Metrics reported | Sharpe, annual return, win rate, profit factor, equity curve, drawdown | Their list, plus net-of-cost, in-sample and out-of-sample separately, turnover, capacity | Ours adopts theirs and adds |
| Negative results | Silent | Kept in the record, and they change the research | Ours only |
| Adequacy | Silent | Independent shocks, not calendar length; report event and issuer counts | Ours only |

**Risk and capacity**

| Dimension | Theirs | Ours | Verdict |
|---|---|---|---|
| Risk controls | "Add risk controls" | Factor exposure, joint tails, borrow, financing, liquidity, and abstention as an output | Ours is stricter |
| Costs | Silent in the Results section | Every number net, bps justified, doubling test | Ours only |
| Capacity and market impact | Silent | Participation, impact, and the capital at which the edge dies | Ours only (the brief scores it) |

**Tools and infrastructure**

| Dimension | Theirs | Ours | Verdict |
|---|---|---|---|
| Why a tool is used | Silent | Named task, simple comparator, measured benefit, full cost, and removable | Ours only |
| Advanced methods, including quantum | Not addressed | No method is mandatory; quantum has no standing role; GPU simulation is classical computation | Ours only |
| Language and storage | Teaches programming, does not prescribe | Follows the task; existing Python stays; one low-level engine only for a measured bottleneck | Ours, and theirs is silent |

**Process and collaboration**

| Dimension | Theirs | Ours | Verdict |
|---|---|---|---|
| Record structure | The Investment Proposal, four sections, versioned research | The same four sections, now required of an active thesis, plus the ledger and decision log | Theirs, adopted |
| Who writes what | Mentorship model | One writer per path, claims in OWNERS, a named integrator | Ours only |
| Review | Weekly work, senior-member mentorship | Adversarial reviewer traces claims to sources; mechanical gates on every push | Ours is stricter and mechanical |
| Knowledge persistence | Versioned research | Append-only ledger, generated views, shared memory across four devices | Ours only |
| Time to first result | The framework exists to produce one | At risk of over-engineering it | **Tension.** Theirs wins, and we adopted the rule below |

### Verdict summary

Their published material is a **producer's** framework: short, ordered, and built to get an honest
result out of the door. Ours is a **skeptic's** framework: it adds availability discipline,
pre-registered falsifiers, multiple-testing correction, cost and capacity modelling, tool
justification, and governance. Every one of those additions is a way of not fooling ourselves, and
none of them produces a number.

Three things were genuinely theirs and are now ours: the **record shape**, the **named data gate**
and the **result orientation**. Everything else in the table is either a match, or us carrying their
idea further.

### The correction their method implies for us

A governed repo with no measurement is a failure, and no amount of process fixes that. Adopted as a
standing rule:

> **One event family, one horizon, one pilot, one result artifact. Process exists to make that result
> trustworthy, not to be the result. If a choice arises between another governance improvement and
> the first honest number, take the number.**

### The merged shape we work to

Their skeleton, our gates inside it: a thesis record is an Investment Proposal with four required
sections, plus Falsifiers, Costs and capacity, and Limitations; the ledger line stays as it is; the
data gate is a named person; results print their metric list, produced our way.
