# ADR-008: Instrument terms and asset accounting

Status: implementation slice, 2026-10-04. Owner: `orderbook-engine/`.

## Decision

Every account is bound to an effective-dated `Instrument_spec.t`. The spec declares venue, symbol,
currency, 1e-4 price increment, 1e-6 quantity increment, contract multiplier, and asset class.
The fixed-point wire scales remain unchanged. Missing or invalid terms reject fills.

`Asset_account` is an exact accounting reference implementation for one instrument and one
currency. It uses checked int64 arithmetic and returns errors on unsupported lifecycle actions.
`Asset_replay` consumes canonical fills and lifecycle observations in receive-time order, rejecting
mixed instruments and reordered events. `Asset_loop.run` executes IOC/FOK taker orders against
visible canonical L2 depth and posts the resulting fills to `Asset_account`. The equity settlement
calendar is an explicit callback. The new asset loop is an opt-in library path; it does not replace
`Exec_account` in the existing CLI/report path. Consequently the old `Exec_loop.run` remains a
perpetual-style execution path and must not be used to claim equity, listed-future, or option P&L.

## Implemented semantics

- Long-only cash equity debits purchases immediately, holds sale proceeds as receivables until an
  explicitly supplied settlement timestamp, and includes receivables in equity. Exact split and
  dividend events update the share count, basis, and cash receivables. Fractional split cash-in-lieu
  requires a separate event and fails closed here. Unlocated shorts fail closed.
- Listed futures use a contract multiplier, initial and maintenance margin rates, daily variation
  settlement, and final cash settlement at expiry. A venue adapter must supply official settlement
  events; the module does not infer them from a last trade or midpoint.
- Perpetuals use a contract multiplier, margin rates, and signed funding cash flows. The rate and
  mark come from explicit source events.
- Long cash-settled options pay their premium and receive intrinsic value at expiry using the
  exercise multiplier, which can differ from the premium multiplier. Physical
  exercise fails until an atomic underlying delivery ledger is connected. Short options fail until
  their venue-specific collateral and assignment rules are declared.
- The asset loop preserves receive-time ordering and explicit submit latency. It depletes only
  visible depth, rejects crossed books, malformed provenance, suspect records, sequence gaps,
  mixed instruments, and duplicate order IDs. It settles equity receivables as replay time
  advances. IOC may fill partially; FOK is atomic. GTC/passive queue execution is rejected because
  its fill cannot be certified from a visible-depth snapshot alone.

## Remaining integration gate

1. Expose the opt-in asset loop through the canonical replay CLI/report without changing the old
   report's values. A multi-instrument run requires separate books and accounts plus a declared
   cash/FX and portfolio-margin policy; this implementation intentionally has one instrument.
2. Post physical option exercise/assignment atomically to cash and underlying share positions.
   The spec separates premium multiplier from deliverable shares because adjusted contracts can
   differ from the standard 100-share contract.
3. Add an explicit short-equity borrow/locate and margin model before allowing short fills.
4. Add effective-dated corporate actions, exchange calendars, fee schedules, tick schedules,
   symbol mappings, and instrument spec hashes to source manifests and run identity.
5. Supply venue-specific liquidation policy and fees. A maintenance breach currently stops replay
   instead of inventing a liquidation price or quantity.
6. Test full replay with real, properly licensed equity/future/option fixtures. Golden account and
   loop tests prove only their declared scenarios, not feed quality or historical executability.

Run the source-neutral golden suite with `opam exec -- dune runtest test/asset_account_test.exe
test/asset_loop_test.exe` from `orderbook-engine/`. The full `dune runtest` suite must also pass.

## Primary reference points

- OCC equity options specifications: https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications
- OCC contract adjustments: https://www.theocc.com/clearance-and-settlement/corporate-action-information-submission-form
- CME daily futures marking and variation: https://www.cmegroup.com/education/courses/introduction-to-futures/mark-to-market.hideHeader.hideFooter.hideSubnav.hideThis.html
- FINRA equity T+1 settlement timing: https://www.finra.org/investors/insights/understanding-settlement-cycles

The accounting implementation uses externally supplied official settlement prices.
