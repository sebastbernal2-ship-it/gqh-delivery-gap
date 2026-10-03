# Delivery-gap strategy protocol

Owner: `sebastbernal2-ship-it`.

This protocol fixes the non-data work needed to identify one executable delivery-gap strategy.
It applies to the PWR-first daily pilot and keeps ETN, EME, and DLR as feasibility candidates.
It does not open either sealed window.

## Pilot boundary

- The primary candidate is PWR.
- ETN, EME, and DLR remain feasibility candidates until their exposure histories pass review.
- The first study uses daily event windows.
- The predeclared primary horizon is five sessions; 1, 2, 5, 10, and 20 sessions remain reported as a plateau.
- The benchmark is market and sector adjusted abnormal return.
- The signal is a new public value minus an earlier public expectation.
- The fill is the first session strictly after the usable signal timestamp.
- Every reported return is net of costs and repeated at doubled costs.

## Expectation measurement

Keep management guidance, analyst consensus, market-implied expectation, and public-plan vintages as separate baselines.
A revision row must contain the earlier value, current value, units, expectation kind, source, entity key, observed timestamp, available timestamp, usable timestamp, and evidence status.
The earlier value must be public before the revision and must describe the same metric and target period.
A later realized outcome is a label and cannot be used as an input.
An uncertain or incompatible baseline is missing, not zero.

Gate: every event is manually auditable to original source text and has an ordered timestamp chain.

## Issuer exposure

The exposure chain is project or contract to owner, operator, supplier, or counterparty to issuer and security to segment to backlog or RPO to revenue timing to margin, capex, or cash flow.
Each mapping must name its direction, weight, evidence, status, and identity vintage.
Only verified mappings can carry a position.
Proposed, ambiguous, and unmatched mappings remain visible but cannot carry P&L.
A position without an exposure edge is a defect.

Gate: every tested event has a bounded issuer mapping and an explicit economic direction.

## Identification design

The primary estimand is net abnormal return after a dated delivery or capacity revision.
The development design reports 1, 2, 5, 10, and 20-session windows without electing a winner after results.
Controls include market, sector, size, value, momentum, reversal, volatility, rates, ordinary earnings news, and event clusters where available.
The development tests include a matched event study, calendar placebo, sector placebo, negative-control disclosure set, cross-sectional exposure test, and doubled-cost stress.
The sealed holdout is opened once under `docs/plan/sealed-test.md`.

Falsifiers are no response after controls, disappearance after ordinary earnings controls, disappearance after doubled costs, one-issuer dependence, one-common-shock dependence, or no improvement from physical confirmation.

Gate: horizon, universe, benchmark, controls, event clustering, falsifiers, and cost model are frozen before the sealed test opens.

## Tradeability

The trade ledger must include point-in-time security identity, side, signal timestamp, fill timestamp, quantity, price, spread or slippage cost, borrow cost, corporate-action treatment, and capacity limit.
A fill cannot occur at or before the signal timestamp.
A short trade requires a borrow assumption or a recorded borrow failure.
Position sizing must respect liquidity and cluster limits.
Daily data is sufficient for the first pass.
Options, intraday depth, and crypto overlays wait for a surviving equity signal.

Gate: the strategy produces net P&L, turnover, drawdown, capacity, cost-doubling results, and no-trade reasons.

## Physical confirmation

The physical branch is planned capacity to queue or permit status to equipment or construction status to energization to commercial operation to realized delivery.
Each observation keeps project and unit identity, capacity, observed timestamp, available timestamp, source, evidence, and status.
Physical confirmation is a classifier or mechanism test, not a financial outcome.
Missing physical evidence remains missing.

Gate: physical confirmation either improves the event classification or is reported as a non-useful monitor.

## Evidence contract

Every feature and edge carries source, document or accession, entity key, observation timestamp, publication timestamp, usable timestamp, vintage, units, transformation, missingness reason, and evidence status.
The validators reject timezone-free timestamps, future availability, unbounded exposure, same-bar fills, negative capacities, and unsupported evidence states.

## Promotion gates

1. The event ledger passes timestamp and unit checks.
2. The issuer crosswalk passes identity and exposure review.
3. The development event study passes its placebo and clustering checks.
4. The trade ledger passes cost, borrow, capacity, and corporate-action checks.
5. The physical branch is either useful or explicitly rejected.
6. The sealed holdout opens once and is reported without redesign.
7. A thesis is promoted only after all gates pass or the failure is recorded as the result.

## Closure checklist

- Reconcile `docs/chains/t-capacity-revision.jsonl` with this protocol.
- Replace the undecided horizon with the predeclared five-session primary horizon and the full 1, 2, 5, 10, and 20-session plateau.
- Replace the undecided pilot universe with PWR as primary and ETN, EME, and DLR as feasibility candidates.
- Remove or park the options P&L expression until the equity expression survives.
- Build the point-in-time event ledger from original filings, exhibits, guidance, and consensus vintages.
- Populate and verify `docs/entity-crosswalk.csv` before any exposure can carry P&L.
- Wire the row validators into event, exposure, physical, and trade ingestion outputs.
- Run the matched event study with controls, placebos, clustering, and doubled costs.
- Build the liquidity, borrow, spread, impact, capacity, and corporate-action report.
- Integrate physical confirmation and report whether it improves event classification.
- Reconcile provenance receipts, timestamps, units, vintages, missingness, and hashes.
- Treat all existing proxy results as historical diagnostics until regenerated under this protocol.
- Keep both sealed windows closed until the development gates pass.

## Closure status

Closed in this phase:

- The chain log now records the five-session primary horizon and the PWR-first universe.
- The options expression is parked outside the active pilot.
- `scripts/build_capacity_event_ledger.py` creates and validates public-plan revision events.
- `scripts/build_physical_ledger.py` creates and validates point-in-time physical observations.
- `scripts/check_strategy_ledger.py` validates typed provenance packages and crosswalk gates.
- Capacity strategy output now stores net 10-basis-point and net 20-basis-point results.
- Legacy RPO proxy surprises are retained as `legacy_surprise` and cannot drive the study.
- The direct PWR crosswalk and 97-row exposure ledger are verified for issuer-owned RPO observations.
- The market-control panel has 86 lagged PWR rows.
- The tradeability panel has 86 explicit no-trade rows because borrow, spread, and liquidity evidence is absent.
- The imagery probe has eight validated scene pairs.

Closed mechanical work:

- `src/strategy/sources.py` defines typed source schemas and local CSV adapters.
- `src/strategy/leakage.py` rejects future labels, late controls, and sealed rows.
- `scripts/run_market_control_stress.py` reports market and sector controls, doubled costs, capacity, and no-trade reasons.
- `scripts/review_crosswalk.py` writes the crosswalk review report without promoting mappings.
- `src/imagery/validation.py` validates labels, scenes, and probe rows before measurement. The current probe has eight validated scene pairs.
- The selected PDF renderer order is `chrome-headless-shell`, `chromium`, `google-chrome`, `.venv-pdf/bin/weasyprint`, `weasyprint`, then `wkhtmltopdf`; WeasyPrint is installed in the ignored local PDF environment.

Blocked by missing verified inputs:

- `docs/entity-crosswalk.csv` now has one verified direct-issuer mapping for PWR. Project and supplier mappings remain absent.
- Historical guidance, analyst consensus, and market-implied expectation vintages are not present.
- The lagged PWR market-control panel now exists. Borrow, impact, execution, and point-in-time liquidity panels are still absent.
- The imagery probe now has eight validated scene pairs. It remains descriptive until its classifier value is tested.
- The existing PDF still needs protocol-compliant results before it can become the final note.
- Promotion remains closed. `make gate-status` reports no primary PWR expectation vintages and no tradeable execution rows.

The next execution command after compaction is: `Proceed to close all gaps`.
