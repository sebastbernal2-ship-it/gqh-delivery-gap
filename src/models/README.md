# Delivery hazard model

Owned by sebastbernal2-ship-it. `hazard.py` fits a discrete-time logistic hazard with NumPy, with likelihood, AUC, odds-ratio and bootstrap helpers. `python3 scripts/run_delivery_model.py` consumes the delivery model panel; `python3 tests/test_hazard.py` checks the numerical implementation. Model output measures project-promise revisions, rather than investment returns.
