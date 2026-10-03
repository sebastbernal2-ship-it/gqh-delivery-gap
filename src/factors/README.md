# Delivery factors

Owned by sebastbernal2-ship-it. Builds weather, drought, supplier backlog, market and state pipeline covariates for project-delivery research. Availability timestamps and lagged monthly inputs belong to the individual factor implementations. Build the joined input with `python3 scripts/build_delivery_model_panel.py`; run factor regressions with `python3 tests/test_factors.py`. These are economic delivery covariates, distinct from the return-exposure framework in `src/unified_factors/` when that component is present.
