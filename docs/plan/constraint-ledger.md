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
