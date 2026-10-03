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
