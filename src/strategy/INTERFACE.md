# Strategy interface

The strategy layer receives validated revision, exposure, trade, and physical-observation rows.
It returns accepted rows or a validation error.

`contracts.py` owns the row-level checks.
It does not fetch data, infer identity, calculate returns, size a portfolio, or open a sealed window.

Every timestamp must be timezone-aware.
Every signal must have a strictly later fill.
Every issuer exposure must have a bounded weight and evidence status.
Every physical observation remains separate from financial outcomes.
