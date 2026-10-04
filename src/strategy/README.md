# src/strategy

Input contracts for the PWR-first delivery-gap pilot.

`contracts.py` validates point-in-time revisions, bounded issuer exposure, lagged executable trades, and physical observations.
`tradeability.py` applies explicit entry, exit, and borrow costs to a gross return.
`physical.py` classifies only physical evidence available by the event timestamp.
`ledger.py` wraps the row contracts with provenance requirements and powers `scripts/check_strategy_ledger.py`.
`gates.py` owns the promotion gate state, and a missing evidence package keeps a thesis closed.
`leakage.py` owns the point-in-time leakage gates for event packages.
`controls.py` builds the deterministic placebo and negative controls.
`market.py` holds the market controls and the explicit execution stress calculations.
`ownership.py` keeps evidence-backed ownership review separate from issued equity.
`index_mandate.py` holds the point-in-time index reconstitution contracts.
`sources.py` adapts the typed strategy CSV packages.

It does not fetch data or promote a thesis.

## Use

```sh
python3 tests/test_strategy_contracts.py
```

Run `make strategy-check EVENTS=...` before an event study. Missing expectations must remain missing.

## Owner

`sebastbernal2-ship-it` owns this path.
