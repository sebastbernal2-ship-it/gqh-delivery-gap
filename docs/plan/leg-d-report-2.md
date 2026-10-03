# Leg D: candidate economic chains scored through six gates

## Source and scope

Leg C's association engine produced no cross-family survivor and no lead-lag survivor. Its eight directions surviving at the ten percent FDR threshold were all at lag zero and formed four reciprocal within-family pairs. They do not provide a cross-family economic chain. These candidates therefore come from the measured mechanism facts in `docs/truths.md` and `docs/plan/constraint-ledger.md`, including promise revisions and delays, disclosure lags, survival hazards, compute-family dispersion, the listed-owner attribution ceiling, and the recorded forced-flow candidates. No Leg C survivor is treated as a causal edge.

The chain records are in `docs/market/leg-d-chains.jsonl`. Gate 1 passes for 5 of 8 records. No chain passes all six gates. A gate marked open is unmeasured or unresolved, not a pass.

## Gate score by chain

### 1. Forced liquidation on perpetual venues

- Gate 1, constrained counterparty: **Pass.** Leveraged perpetual longs whose maintenance margin is breached are closed by the venue rule.
- Gate 2, price-insensitive flow: **Pass.** The forced close is mechanical and does not wait for a better price.
- Gate 3, transfer and concentration: **Open.** The transfer is liquidation slippage, but event-level basis points, dollars, and concentration are not measured.
- Gate 4, instrument without dilution: **Pass.** `instrument:perpetual` is the contract in which the liquidation clears.
- Gate 5, economics and capacity: **Open.** Net returns, break-even cost, turnover, and decay by size are unknown. The running tape has 455 samples per market and no trigger yet.
- Gate 6, barrier and removal: **Open.** Execution and inventory risk are plausible barriers. Their binding limits and removal conditions have not been measured.

### 2. Fixed-price contractor schedule-risk absorption

- Gate 1, constrained counterparty: **Pass.** A fixed-price contractor can be required to absorb costs that it cannot bill back. The project-to-firm assignment is missing.
- Gate 2, price-insensitive flow: **Fail.** A schedule revision changes expected costs, but it does not establish a mechanical transaction. Renegotiation may change who pays.
- Gate 3, transfer and concentration: **Fail.** Project-level costs are unmeasured, and only 6.2 percent of slipped capacity is linked to a large listed owner.
- Gate 4, instrument without dilution: **Fail.** `instrument:contractor-equity` is diluted across projects and business lines.
- Gate 5, economics and capacity: **Open.** Net effect, costs, turnover, and investable capacity are unknown.
- Gate 6, barrier and removal: **Open.** Document linking is costly, but evidence that it preserves mispricing and what removes the barrier is absent.

### 3. Completion-covenant project financing

- Gate 1, constrained counterparty: **Pass.** A lender bound by a completion covenant can condition a draw on milestone certification. No measured project is joined to its facility.
- Gate 2, price-insensitive flow: **Fail.** The contract may permit waivers, amendments, or repricing. No mechanical draw response is measured.
- Gate 3, transfer and concentration: **Open.** The possible transfer has units of delayed dollars and loan spread, but size and concentration are unmeasured.
- Gate 4, instrument without dilution: **Fail.** Project debt is private and illiquid; sponsor equity dilutes the project exposure.
- Gate 5, economics and capacity: **Open.** Per-site prices, costs, and capacity are unavailable.
- Gate 6, barrier and removal: **Open.** Document costs may be a barrier, but its effect on price persistence is untested.

### 4. Queue-position delay and local scarcity

- Gate 1, constrained counterparty: **Pass.** A developer with a queue position is constrained by the first-come, first-served procedure. The measured projects are not joined to queue positions.
- Gate 2, price-insensitive flow: **Fail.** Queue order is procedural, but no price-insensitive transaction or transfer to a counterparty is measured.
- Gate 3, transfer and concentration: **Fail.** The rent per project is unknown, and most slipped capacity lacks a listed-owner attribution.
- Gate 4, instrument without dilution: **Fail.** `instrument:generator-and-power-equity` does not isolate queue rent and is diluted by broader operations.
- Gate 5, economics and capacity: **Open.** Local scarcity rent net of costs and instrument capacity are unmeasured.
- Gate 6, barrier and removal: **Open.** Queue history and joins are unavailable here. A data barrier is plausible, but persistence and its removal condition are unverified.

### 5. Compute-family scarcity rent

- Gate 1, constrained counterparty: **Pass, conditional.** A buyer with a binding deployment deadline and no timely substitute could be compelled to pay. The measured rental archive contains listed prices, not verified buyer contracts or transactions.
- Gate 2, price-insensitive flow: **Open.** The deadline could make demand inelastic, but no executed flow is observed.
- Gate 3, transfer and concentration: **Fail.** Family price dispersion is measured, but the corresponding executed rent and its concentration are not.
- Gate 4, instrument without dilution: **Fail.** `instrument:host-equity` is diluted. Reviewed issuers do not isolate revenue by GPU family.
- Gate 5, economics and capacity: **Open.** Executed rental economics, costs, and capacity are unknown.
- Gate 6, barrier and removal: **Open.** Slow inventory reallocation may be a barrier, but persistence in executed rent and its removal condition are untested.

### 6. Filing disclosure lag

- Gate 1, constrained counterparty: **Fail.** A 33 to 94 day reporting lag does not name a payer or a party required to transact.
- Gate 2, price-insensitive flow: **Fail.** No flow is identified, and no price-insensitive trade is measured.
- Gate 3, transfer and concentration: **Fail.** No transfer amount or concentration is measured.
- Gate 4, instrument without dilution: **Fail.** The contractor-equity proxy does not link the disclosed fact to a particular loss bearer.
- Gate 5, economics and capacity: **Fail.** No event-level return, cost threshold, turnover, or capacity is established for this transfer.
- Gate 6, barrier and removal: **Open.** Filing extraction takes attention, but price persistence and the event that removes this barrier are unknown.

### 7. Age-conditioned promise survival hazard

- Gate 1, constrained counterparty: **Fail.** The hazard gradient does not identify which contract party bears each project's cost.
- Gate 2, price-insensitive flow: **Fail.** A revision hazard is not itself a forced transaction.
- Gate 3, transfer and concentration: **Fail.** Cash transfer by payer and project is unmeasured.
- Gate 4, instrument without dilution: **Fail.** The current records do not link project exposure to facility debt or sponsor equity.
- Gate 5, economics and capacity: **Fail.** No net economics, costs, turnover, or capacity are available.
- Gate 6, barrier and removal: **Open.** Project-level document work may be costly, but no price-persistence mechanism or removal condition is established.

### 8. Listed-owner attribution ceiling

- Gate 1, constrained counterparty: **Fail.** Eighty percent of slipped capacity sits in project or holding companies, so the contract bearer is unnamed for most projects.
- Gate 2, price-insensitive flow: **Fail.** The attribution ceiling is a coverage fact, not a forced flow.
- Gate 3, transfer and concentration: **Fail.** The transfer cannot be assigned for most projects; only 6.2 percent of slipped capacity maps to a large listed owner.
- Gate 4, instrument without dilution: **Fail.** Listed equity is diluted and absent as an expression for most projects.
- Gate 5, economics and capacity: **Fail.** Attributable transfer magnitude, net economics, and capacity are unknown.
- Gate 6, barrier and removal: **Open.** Entity resolution and contract reading may create an information barrier, but persistence and a removal condition are untested.

## Result

Five of eight chains pass gate one because their mechanism facts name a constrained payer class: forced sellers, fixed-price contractors, completion-covenant lenders, queued developers, and deadline-constrained compute buyers. The compute buyer remains conditional because the measured prices are listings, not executed rentals. Three chains fail gate one: disclosure lag alone, the aggregate survival hazard without contract attribution, and the measured attribution ceiling itself. None passes all six gates. The strongest chain is forced liquidation: its payer is a leveraged perpetual long closed by a maintenance-margin rule, and its instrument is `instrument:perpetual`. Gates 3, 5, and 6 remain open, so this is a candidate chain, not a validated edge or a strategy.
