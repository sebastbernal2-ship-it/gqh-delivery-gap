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

---

## 13. The development pipeline: eight stages, not four

The training material's four steps (Hypothesis → Data → Methodology → Backtest) are missing the middle
and missing the aftermath. Two stages sit between Data and Methodology, because that is where the
assumptions come from. One stage follows the first test, because that is where unintended risk is
found. Stages 3, 4 and 7 are the ones nobody in the published framework owns.

| # | Stage | Purpose | Artifact | Gate: cannot proceed without | Rubric |
|---|---|---|---|---|---|
| 1 | Question | What economic thing are we claiming, **and why us** | One paragraph; the mechanism, counterparty, simplest rival, falsifier; **plus the edge channel, expected breadth, expected regime dependence, capacity sketch and latency budget** | All present. Section 16 items are sketched here, not deferred | 01, 02, 04 |
| 2 | Data | Get the world in, with provenance | Data manifest: source, availability time, entitlement, coverage, rejections | A **named approver**; every field's knowable-at time documented | 01, 05 |
| 3 | **Structure** | **Measure the world's joint structure before building on it** | Marginal distributions with tails and censoring; dependence beyond correlation (tail dependence, concordance, copulas where they earn it); association screens with multiple-testing control; shared-shock clusters and their effective breadth; stability across sub-periods; **regime states defined on past-only data**; **cross-sectional variation** across names and events; **liquidity and capacity structure** (ADV, spread, borrow, financing); and a list separating *identified* from merely *associated* | **Every assumption used downstream cites a measurement here.** No free-floating assumptions | 01, 02, 03, 04, 05 |
| 4 | **Identification** | Which relations are causal, and how we know | For each load-bearing arrow: the design (timing, comparison group, instrument, placebo, falsification test), the estimand, and the result | No arrow that drives a trade may remain "inferred". It is evidenced, or the trade is labelled speculative and sized as such | 01, 05 |
| 5 | Design | Turn the mechanism into rules **and a portfolio** | Signal rules, timing, conditioning (all-weather, state-gated or state-scaled), **portfolio construction with correlation-aware risk budgeting and caps**, execution and cost model, exposure budget, **the latency budget against the information half-life** | A baseline to beat, a cost model, a variant plan, one primary horizon, a sealed-test plan, an exposure budget, and a latency budget | 01, 03, 04, 05 |
| 6 | Test | Produce the honest number **and the breadth numbers** | Results artifact, in-sample and out-of-sample separate, net of costs; **IC, decay curve, effective breadth, regime-conditional performance, capacity curve, measured latency chain** | Sealed test opened once, by a named owner, reported whatever it says | 04, 05 |
| 7 | **Decomposition** | Break the strategy back down and remove what we did not intend | Factor and regime attribution of returns *and* risk; realised versus budgeted exposure; residual and idiosyncratic share; fragility by regime; the hedge map; **attribution of the edge to one of the four channels from section 16.1** | Unintended exposure is hedged, sized down, or dropped; the assumptions it contradicts are re-derived; **the edge channel claim is confirmed or withdrawn** | 01, 02, 03, 04 |
| 8 | Writeup | Make it legible and auditable | The note, plus the record, mapped to the five criteria | Every number traces to a result artifact, and a judge can rerun it | all |

Stage 7 loops back to Stage 3. A decomposition that contradicts an assumption sends us back to the
measurement, not to the prose.

## 14. Only intentional exposure

A strategy should hold the exposure it is paid to hold and nothing else. Idiosyncratic risk is
uncompensated: carrying it adds volatility and no expected return, so it is a cost, not a strategy.

**The exposure budget** is a named artifact and the thing that makes this checkable.

- **Intended**: which systematic exposures we are paid to hold, why the mechanism pays for them, and
  the tolerance around each.
- **Neutralised**: exposures we do not intend to hold (market, sector, rates, FX, commodity, crowding),
  and how each is neutralised: hedge, size, or drop the name.
- **Forbidden**: anything we cannot name. An unnamed exposure is a defect, not a residual.
- **Realised**: post-trade attribution of returns *and* risk against the budget, with the unexplained
  share reported. If the strategy's returns load on something outside the budget, we own that
  decision explicitly or remove it.

Rules:

1. Every source of P&L is either the mechanism, a hedge of an unintended exposure, or a defect.
2. Report the factor-attribution residual and say whether it is intended.
3. Decompose by regime, with regime definitions fitted on past information only. State where the
   strategy is fragile rather than averaging it away.
4. Long/short and beta-neutral books can lose on both legs. Joint tails, borrow, financing and basis
   risk are theirs to report, not to assume away.
5. Diversification is not a substitute for removing unwanted exposure. It reduces idiosyncratic
   variance; it does not make an unintended bet intended.

## 15. The rubric map: what earns 10/10, and where the method closes it

The rubric is the acceptance test for this document. If a criterion would not score full marks with a
team that followed the method perfectly, the method is deficient. This table is the audit.

| Criterion | What a 10 requires | What we had | The gap | Closed by |
|---|---|---|---|---|
| **01 Economic foundation** | Exceptional understanding, with **well-evidenced** reasoning | Mechanism, counterparty, rival explanation, arrow tagging | We could only tag arrows observed / inferred / untested. Nothing converted inferred into evidenced | Stages 3 and 4: assumption provenance, then an identification design per arrow. Enforced: every assumption cites a measurement, and no trade-driving arrow may stay inferential |
| **02 Innovation** | Highly innovative, original, distinct from conventional strategies | Nothing. The method never asked what is novel | No novelty claim, no defence against "this is a known anomaly in disguise", and no answer to "why us" | A Novelty section that names the closest known strategy or published factor, states the mechanical difference, locates the innovation in the mechanism or the measurement rather than the model, and **names the edge channel from section 16.1 with evidence**. A strategy with no edge channel has no innovation to defend |
| **03 Risk management** | Highly detailed, effective, **multiple contingencies**, thorough understanding | Risk categories: factor exposure, joint tails, borrow, financing, liquidity, abstention | We listed risks, had no response to any of them, and were **single-name in thinking**: no portfolio-level risk at all | A contingency register (trigger, response, owner) plus **portfolio-level risk**: correlation-aware risk budgeting, per-name and per-cluster caps, effective-breadth reporting, state-conditional fragility, drawdown and de-risking triggers |
| **04 Liquidity & capital** | Excellent, thorough, practical application | Costs in bps, doubling test, participation, impact, capacity in dollars | No capital schedule, no build and exit plan, no borrow or financing specifics, no days-to-liquidate, and **capacity did not constrain the choice of expression** | A liquidity and capital table with those fields, **plus the capacity curve as a design input**: if capacity is below intended capital, the expression changes, not the aspiration. Liquidity and capacity structure are measured in Stage 3, not reported at the end |
| **05 Performance & analytical evidence** | Exceptional rigour, thorough and convincing | Net of costs, in-sample and out-of-sample separate, deflated for variant count, negative results kept | No robustness suite, and **no breadth evidence**: one case cannot show a distribution of outcomes | Stage 6 robustness suite (plateau, subsample and regime stability, placebo, alternative specification, bootstrapped intervals) **plus the breadth set: IC, decay curve, effective breadth after correlation, hit rate, effect-size spread, worst decile, and a capacity curve**. Plus reproducibility: a judge reruns and matches |

**Enforcement.** An active thesis record must carry a section for each criterion — Hypothesis, Data,
Structure, Methodology, Results, Novelty, Risk, Liquidity — and `make check` fails if any is missing.
The rubric becomes a structural requirement rather than an aspiration.

**The honest limit.** A method can guarantee that the evidence is produced, complete and auditable. It
cannot guarantee that the numbers are good, and no method can. Criterion 02 is the other limit: a
template cannot manufacture a real novelty claim, it can only force us to state one and test it. What
the method can promise is that if a claim scores badly, we will know exactly which measurement is
missing rather than discovering it in judging.

---

## 16. From a case to a system: what makes this a quant strategy

Everything up to here can be satisfied by a single well-researched event. A quant strategy is a
different object: a repeatable relationship traded across a cross-section, under explicit conditioning,
inside risk and capital limits, fast enough to matter. The gaps that separate the two are named here.

### 16.1 Why us: the four edge channels

A mechanism explains why the mispricing exists. It does not explain why **we** capture it. Name at
least one channel and bring evidence for it before building:

| Channel | The claim | Evidence it needs |
|---|---|---|
| **Data** | We hold or can compute something others do not, or not yet | Coverage, cost, rights, and that it is not already in the price at our decision time |
| **Inference speed** | We convert public information into a position faster | The measured pipeline latency against the signal's information half-life |
| **Processing** | We turn messy or wide data into a usable signal others cannot | Extraction accuracy, provenance, and a demonstrated signal that a simple parse cannot produce |
| **Portfolio craft** | We hold the same signal better: only intended exposure, sized properly, cheaper | Exposure budget, attribution residual, realised cost versus modelled |

If we can name none, we do not have an edge and the honest move is to say so rather than proceed.
"AI is growing" and "power is scarce" are not channels.

### 16.2 Breadth: the arithmetic that decides whether this is a strategy

Information ratio scales with the square root of breadth. With IC the correlation between forecast and
outcome, and BR the number of **independent** bets:

> IR ≈ IC × √BR

Consequences we must design around, not discover later:

- A single event family with thirty shocks a year needs an enormous IC to produce a respectable IR.
- Breadth comes from more event types, more names, more horizons, more instruments. Each addition
  must preserve the mechanism, not dilute it.
- **Correlation haircuts breadth.** Fifty names responding to one shock are one bet. Report effective
  breadth after clustering, alongside the raw count, or the IR is a fiction.
- Report the decay curve: how the signal's information decays with time, because decay sets the
  horizon and the latency budget.
- Report the distribution of outcomes, not the average alone: hit rate, effect-size spread, and the
  worst-decile behaviour.

The pilot may stay one case, but it must **measure** these quantities so the generalisation step is
grounded in numbers rather than hope.

### 16.3 Conditioning: regimes as design, not decoration

Regimes are not labels on a histogram. They are the states in which the mechanism pays differently.

- Define states from **past-only** information, with thresholds fitted inside each training window.
- Report the signal's performance, exposure and cost **conditional** on state.
- Decide up front: trade all-weather, trade only in specified states, or scale size with a stated
  state probability. Each is a different strategy with different evidence requirements.
- Name the **failure regime** we expect, and what we do when it arrives.
- An average across regimes that hides a collapse in one of them is not evidence.

### 16.4 Portfolio construction is where the risk lives

A signal is not a strategy. The step from forecasts to positions is where most of the risk is created
or removed:

- Weights from forecast and uncertainty, not from conviction. Size with a risk model, not a feeling.
- **Correlation-aware risk budgeting** across names, clusters and shared shocks, with per-name, per-
  cluster and per-factor caps.
- The **exposure budget** from section 14 binds here: neutralise what we did not intend, and refuse
  what we cannot name.
- Turnover and cost-aware construction: a signal whose edge is smaller than its round-trip cost is not
  a signal.
- Drawdown and de-risking rules with triggers, not intentions, plus the contingency register from
  section 15.
- A portfolio of correlated signal names is **one** position. Size it accordingly.

### 16.5 Capacity is a design constraint, not a report

Capacity decides which expression of the mechanism we are allowed to trade.

- Compute the capacity curve: participation against average daily volume, the square-root impact
  model, and the capital at which net edge reaches zero.
- If capacity is below the capital we intend to run, change the expression: a different instrument, a
  wider basket, a longer horizon, or a smaller book. Do not keep the aspiration and hope.
- Report days to build and days to exit, borrow availability and cost, and financing, because these
  decide whether the position is real.
- Liquidity and capital also constrain the preliminary rationale: a mechanism that only exists in names
  we cannot trade at size is not our strategy.

### 16.6 The latency budget, stated honestly

Speed is an edge channel only where the half-life is short enough for our pipeline to matter.

- Measure the chain: **public availability → receipt → parse or extract → signal → order**.
- Compare it to the signal's information half-life. If the half-life is days, latency is irrelevant and
  microsecond work is decoration. If the half-life is minutes, the pipeline **is** the edge and must be
  measured as such.
- State which regime we are in. For filings and operational data the half-life is usually hours to
  days, so the honest claim is same-session inference, not colocation.
- Microstructure work (L2, L4, queue position, funding carry) is a **separate study** with its own
  mechanism, data and evidence. It is not a latency upgrade to this one.

### 16.7 What this changes about the pilot

The counter-rule still holds: **one event family, one horizon, one pilot, one result artifact.**
This section does not add scope to the pilot. It adds **measurements** to it: the edge channel claim,
IC, decay, effective breadth, regime splits, the capacity curve, and the measured latency chain. Those
numbers are what make generalisation a decision rather than a hope.

A case study answers "is this real?". A system answers "how much can we make, at what risk, at what
size, for how long, and why us?". The rubric rewards the second, and the second is what we are
building.

---

## 17. Newer and niche markets: perps, compute, and anything else with a short life

The problem is stated precisely: a decade of filings history and a perpetual future that has existed
for two years cannot support the same study. But that is a fact about *venues*, not about the
mechanism, and the mechanism is what we claim.

### 17.1 Why validation does not transfer

A claim in a new venue needs three things to overlap, and for most new markets they do not:

| Requirement | Long-history equity core | Perpetual futures | Compute index |
|---|---|---|---|
| Mechanism existed | Yes, for the whole window | Only since listing | Only since the index began |
| Data with knowable-at times | Yes, with effort | Yes, from the venue's own archive | Vendor dependent; index is recent; licensed futures are **unlisted** |
| Tradable at our size | Usually | Yes, with venue risk | No listed contract to trade |

A short history is not a smaller version of a long one. It is a **different study**, and the correct
response is to design it as one rather than to stretch the long sample until it covers.

### 17.2 What transfers is the contract, not the history

Define the mechanism once, venue-agnostically, and let each venue implement it:

- the economic state variables, and how each is measured;
- the decision rule and its sign;
- the availability requirement: what must be public, and how long before we act;
- the exposure budget: what we intend to hold, and what must be neutralised;
- the cost and impact interface, which the venue supplies.

Transfer is then a **testable claim**: the same rule, the same sign, in a venue with its own costs and
its own participants. Not "we assume it works everywhere".

### 17.3 The paired-shock design: how a two-year venue earns a place in a ten-year study

The unit of observation becomes the **shock**, not the calendar. For every event in the long-history
core, ask whether the same shock is observable in the new venue. Where both exist, we get a paired
observation: the core market's response and the new venue's response to the *same* event.

This is the key move, and it buys three things that a short backtest cannot:

1. **The shock count comes from the long market.** A venue that has existed for two years inherits
   every independent shock that both markets witnessed. We are not asking the venue to supply history;
   we are asking it to supply a second measurement.
2. **The event is held fixed.** Comparing two venues' responses to one shock controls for the shock
   itself. The cross-venue *agreement* is evidence the mechanism is real rather than an artefact of one
   market's microstructure.
3. **The cross-venue *difference* is information.** Different participant populations on the same
   shock (institutional equity holders versus leveraged retail in a perpetual) is exactly the "who is on
   the other side" question, asked separately per venue. A venue that reacts differently is telling us
   about its own participants, and that can be the edge.

Honest limits, stated up front: the overlap subset is small, so it carries **sign and mechanism**
evidence, not statistical weight. Magnitude claims from the new venue are labelled low-power. The long
market carries the sample; the new venue confirms or contradicts.

### 17.4 Four roles a new market can play

| Role | What it needs | May it enter performance? |
|---|---|---|
| **Confirmation** | Paired shocks, the same rule | Reported separately, never pooled |
| **Expression or hedge vehicle** | Liquidity, borrow or shortability, cost model, venue risk | Yes, with its own capacity curve and attribution |
| **Execution laboratory** | Venue data at depth | No, it is engineering evidence |
| **Monitor** | A published series | No, it is an input, never a leg |

A monitor is still useful. A funding rate or a compute index can be a state variable that feeds the
core signal, or a live read on crowding, without ever being traded.

### 17.5 Satellite admission gate

A new venue may become a leg only when all of these hold. Fail one, and it stays a monitor or an
execution laboratory:

1. The mechanism applies to that venue, and we say why institutionally.
2. The information arrives at a knowable time, and the venue trades when we need to act.
3. A point-in-time universe exists, including delistings and contract expiries.
4. Costs, funding, borrow, impact and liquidation are modelled **from that venue's own data**.
5. Its life overlaps at least a stated number of independent shocks with the core.
6. It has its own falsifier, with a pre-registered direction.
7. It has its own capacity curve.
8. It writes its own result artifact.

### 17.6 Backtest integrity across venues: the hazards and their controls

This is where naive multi-venue work breaks. Each row is a way to produce a fake result.

| Hazard | Why it corrupts | Control |
|---|---|---|
| Different clocks and calendars | 24/7 perps, 6.5-hour equities, a 16:00 ET index window. Aligning by date silently moves the fill | Canonical event time = first public availability, in UTC. Per-venue response windows in that venue's own bars |
| No official close | Perps have mark prices and hourly funding, not a closing auction | Define marks explicitly (mid or last trade), fund on the contract's actual schedule, and never assume we trade at a mark |
| Carry and funding in P&L | In a perpetual a directional view contains a funding term that can dominate | Model funding separately from the directional component and report both. This is a decomposition requirement, not a footnote |
| Venue risk | Single venue, no consolidated tape, outages, liquidation cascades, oracle manipulation, auto-deleveraging | Model impact from the venue's own book, cap participation, treat downtime and cascade as loss scenarios with stated recovery |
| Survivorship and endogenous listings | Contracts delist; new listings appear when interest peaks | Point-in-time universe, delisted contracts included, never selected by today's availability |
| Timestamp semantics | Exchange time, receive time and public availability are different facts; some volumes are self-reported | Carry all three, cross-check against a second source, treat the distinction as a first-class field |
| One-regime history | A two-year venue may have lived entirely inside one narrative, so every result is conditional by construction | State it, forbid extrapolation to unseen states, and use the core market's state definitions to classify the window as an argument rather than evidence |
| Time-varying liquidity | Perp depth collapses on weekends and holidays | Time-of-day aware cost model, not a single average spread |
| Index as instrument | A benchmark index is not a listed, tradable contract | Use as a state variable. If a contract lists, that is a **new study** with its own specification, not a retrofit |
| Pooling | A satellite's returns folded into the core's headline inflate it | One equity curve per study. A satellite never boosts the core's reported Sharpe |

### 17.7 Sequencing, and the honest cost

Satellites are allowed **after** the core passes its own gates. Before that, a new venue is a
distraction with a real cost: a shorter sample, more venue risk, more modelling, and a rubric score
that gets muddier rather than sharper.

The trade-off is explicit. Including a niche market can raise distinctiveness and can supply a hedge
or a monitor. It can also dilute the evidence and add failure modes. So the order is: prove the
mechanism in the market with the longest overlap, then add venues that strengthen the claim or remove
an exposure, one at a time, each with its own record and its own capacity curve.

Worked shape for our own case:

- **Core**: physical capacity and delivery revisions, equities, the longest overlap, the sample that
  carries statistical weight.
- **Perpetuals**: paired confirmation on shocks since listing, a 24/7 expression vehicle where shorting
  is easy, and funding as a live monitor of crowding.
- **Compute index**: a state variable feeding the core signal, plus a monitor. Not a leg.
- **Compute futures**: nothing to trade until a contract lists. When it does, it is a new study with its
  own specification.
