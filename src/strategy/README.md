# src/strategy

Input contracts for the PWR-first delivery-gap pilot.

`contracts.py` validates point-in-time revisions, bounded issuer exposure, lagged executable trades, and physical observations.
`tradeability.py` applies explicit entry, exit, and borrow costs to a gross return.
`physical.py` classifies only physical evidence available by the event timestamp.
It does not fetch data or promote a thesis.

## Use

```sh
python3 tests/test_strategy_contracts.py
```

## Owner

`sebastbernal2-ship-it` owns this path.

`ledger.py` wraps the row contracts with provenance requirements and powers
`scripts/check_strategy_ledger.py`. Run it with `make strategy-check EVENTS=...`
before an event study. Missing expectations must remain missing.
