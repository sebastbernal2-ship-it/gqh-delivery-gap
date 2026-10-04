# Constraint ledger: candidates scored against the six gates

One row per candidate. Each is judged by whether a constrained counterparty can be named, whether the flow is
price insensitive, whether the transfer is concentrated, whether an instrument expresses it without dilution,
whether the economics clear costs, and whether a barrier explains why it survives. Blank cells are open
questions, not victories.

## 1. Forced liquidation on perpetual venues

| Gate | Value |
|---|---|
| Constrained counterparty | leveraged longs whose maintenance margin is breached; the engine closes them mechanically |
| Flow | price insensitive by rule, arrives in bursts |
| Transfer | liquidation slippage, paid to whoever absorbs it inside the burst |
| Instrument | the perpetual itself, which is directly holdable, plus the venue's own order book |
| Economics | unknown; needs the tape, plus taker fee and slippage |
| Barrier | operational: absorbing cascades requires fast, disciplined execution and inventory risk tolerance |
| Falsifier | post trigger reversion disappears after costs, or the flow is anticipated |
| Data needed | forward tape (running), historical book archive (blocked) |
| Status | **passes gates 1, 2, 4. 3 to be measured. The cleanest candidate we have.** |

## 2. Relative value across compute inventories

| Gate | Value |
|---|---|
| Constrained counterparty | provider inventory commitments; lessors with fleets that cannot be reallocated quickly; buyers with deployment deadlines |
| Flow | provider list pricing under inventory conditions, updated on policy not on clearing |
| Transfer | rental differential between families, which we measured as real and independent |
| Instrument | **weak.** Equity of compute owners and providers, all diversified, so the family signal is diluted |
| Economics | unknown; the dispersion is large, but the holding is equity, not rent |
| Barrier | the instrument, not the opportunity |
| Falsifier | a provider whose revenue is concentrated in one family shows no sensitivity |
| Data needed | segment revenue by family where disclosures allow, plus third party lessors |
| Status | fails gate 4 as stated. Survives only if a concentrated entity exists. |

## 3. Delivery revision, expressed in the tail

| Gate | Value |
|---|---|
| Constrained counterparty | whoever holds schedule risk under contract: fixed price contractors, owners with financing milestones, lenders with completion covenants |
| Flow | not a market flow; a planning revision that changes cash timing |
| Transfer | revenue and cost timing, concentrated only if one project dominates one firm |
| Instrument | equity of the bearing party, diluted unless the firm is small and single project heavy |
| Economics | unknown; needs the tail object and a name set |
| Barrier | the work: joining project identity to firm exposure across filings, which nobody does cheaply |
| Falsifier | no firm level sensitivity once dilution and sector are controlled |
| Data needed | project to firm mapping, which is the attribution ceiling |
| Status | passes 1 and 2, fails 3 and 4 without a concentrated name set. |

## 4. Dealer hedging flow around a known event

| Gate | Value |
|---|---|
| Constrained counterparty | option dealers with delta and gamma limits |
| Flow | mandated hedging, derivable from open interest across strikes |
| Transfer | the cost of the hedge, paid by whoever is on the other side of the dealer's flow |
| Instrument | options and the underlying; directly holdable |
| Economics | unknown |
| Barrier | inference cost: requires a calibrated surface and fast evaluation |
| Falsifier | no measurable flow effect beyond spot movement |
| Data needed | **historical option chains, entitlement missing** |
| Status | passes 1, 2 and 4; cannot be tested without data. |

## 5. Queue gated capacity

| Gate | Value |
|---|---|
| Constrained counterparty | whoever needs power at a site and cannot substitute; the operator deciding who energises |
| Flow | procedural, queued, first come first served |
| Transfer | the value of being early versus late; local scarcity rent |
| Instrument | unclear: equity, contract, or physical capacity |
| Economics | unknown |
| Barrier | the data, plus the work of joining queue to site |
| Falsifier | queue position has no relation to energisation timing |
| Data needed | **queue history, requested, not reached** |
| Status | the mechanism is real and the data is missing. |

## 6. Event driven equity, from filings that name parties

| Gate | Value |
|---|---|
| Constrained counterparty | the party that just signed the obligation, which must now deliver |
| Flow | not a flow; a disclosure that changes a firm's obligation |
| Transfer | the value of the obligation, and who bears its slippage |
| Instrument | equity of both parties |
| Economics | unknown |
| Barrier | linking counterparties across filings at scale, which is a model problem not a data problem |
| Falsifier | no sensitivity once dilution and sector are controlled |
| Data needed | wider 8-K coverage (four firms today) |
| Status | passes 1 and 4; needs coverage. |

## What the ledger says

Two candidates pass every gate we can currently evaluate: **forced liquidation**, where the instrument is the
perpetual itself, and **dealer hedging**, which is blocked only by an entitlement. Everything else fails on the
instrument, the dilution, or the data. That is a much shorter list than the relation map, and it is the list that
matters.

## 7. Per site project credit

| Gate | Value |
|---|---|
| Constrained counterparty | the project issuer that must service its own debt after the completion test, and the lender mandate that must hold the rated paper |
| Flow | mandate driven, not view driven: insurance, pension and CLO mandates hold rated paper on mandate, and refinancing is a calendar event rather than a decision |
| Transfer | the spread paid over the risk free rate for one deal's schedule and completion risk, concentrated in that deal |
| Instrument | **the gate that fails.** Per site the instrument is the bond or the tranche, and a small book may not reach the minimum. At the parent it is diluted by everything else the parent does |
| Economics | unknown, and unreachable until the instrument question is answered. The denominator is now measurable per deal: annualised adjusted net operating income of 217.6 to 415.4 million dollars across portfolios of 28 to 40 data centers and 96 to 297 megawatts of critical load, for the four deals whose agency releases state it |
| Barrier | the payer cannot reprice a completed deal, and reading the loan documentation for one deal takes work that nobody does at scale |
| Falsifier | the site level yield does not move when that site's own delivery or counterparty news changes |
| Data needed | **per site prices**, and the FINRA catalogue serves aggregates only, so the trade tape is a separate licensed product; the free alternatives are EDGAR deal level disclosure and holder marks, both mapped in docs/plan/per-deal-credit-sources.md |
| Status | **passes 1, 3 and 6 in principle, 2 is plausible and unmeasured, 4 fails as stated, 5 is blank.** The mechanism is real and the instrument is the obstruction, which is the same shape as the compute relative value row above |

Measured 2026-10-03, in `docs/plan/credit-gauntlet.md`: the aggregate version of this candidate, credit
conditions against the complex's equity, produced 48 declared tests, seven nominal hits against 2.40 expected,
and **zero survivors after rate control across the grid**. Effective breadth was 0.47 bets from four names. The
aggregate door is closed at this window and frequency. The per site door is open and needs the registration.

Measured again 2026-10-03 on the long window, in `docs/plan/credit-gauntlet.md` section 6.8 to 6.10. The FRED
API key was tried and it does **not** widen the ICE BofA window, which is capped at three years by ICE
licensing on FRED. It does unlock the Moody's family, so the same declared grid was rerun with full history:
3 measures x 4 names x 2 horizons = 24 tests over 2016-01-04 to 2026-02-24, 2,462 observations per test.
Nine nominal hits against 1.20 expected, **six survive Benjamini-Hochberg**, and the Baa minus Aaa quality gap
carries four of the six, so the weakest link reading did survive that first pass. Then the stability and cost
gates, declared after the grid on purpose, killed it: half the effect lives in ten days, the two carrying
measures are mechanically related and load with opposite signs on the same names, effective breadth is 0.62
bets, and at a two legged 20 bps round trip **none of the six clear costs**. Status unchanged and now better
supported: gate 4 fails as stated, gate 5 fails on the aggregate expression, and the per site route stays the
only one that could answer gate 4.

### Update, 2026-10-04: two of the blanks above are now filled

**Queue gated capacity, row 5, the data blocker is open.** MISO, SPP and CAISO serve their generator
interconnection queue pages to an ordinary fetch: `misoenergy.org/planning/resource-utilization/GI_Queue/`,
`spp.org/engineering/generator-interconnection/`, `caiso.com/planning/Pages/GeneratorInterconnection/`, and
ERCOT serves its resource adequacy pages. PJM's planning path did not answer from this host and needs a
different route. So the queue history is reachable, free, at four of the five largest markets, and the fix
recorded as "requested, not reached" can be replaced with an ingest.

**Per site project credit, row 7, the covenant is no longer blank.** The holding trust files its credit
agreements as exhibits, and they state the constraint: a debt service coverage test defined as consolidated net
operating income over debt service, remedies on event of default, and a **cash sweep trigger that can fire on a
single tenant condition**. Concentration is therefore a contractual trigger and not only a measurement, which
strengthens gate 3 for this candidate and leaves gate 4, reachability, as the one that still decides it.

### Update, 2026-10-04: the numbers behind the two blanks

**The coverage test has a threshold: 1.25 to 1.00.** From the trust's revolving credit facility, verbatim:
*"the Borrower shall be in compliance on a Pro Forma Basis with (A) an LTV that does not exceed the Maximum LTV,
(B) a Debt Service Coverage Ratio of not less than 1.25 to 1.00 and (C) a Net Asset Value of not less than the
Minimum NAV."* So gate one now reads: the constrained counterparty is a ring fenced borrower, the test is a
coverage ratio of at least 1.25 times debt service, and it is bound together with an LTV ceiling and a net asset
value floor. `make indenture-covenants` writes `results/dscr-thresholds.csv`.

**The queue ingest has begun, at one market of four.** CAISO's cluster fifteen request list parsed into **86
queue rows** with queue number, capacity in megawatts and fuel type, writing `results/queue-panel.csv`. MISO
serves its queue behind an account login and its interactive queue is script driven, SPP publishes through
`marketplace.spp.org` rather than as files on the page, and ERCOT's workbook links timed out from this host.
Each is recorded with its reason rather than dropped, and PJM still needs a route.

