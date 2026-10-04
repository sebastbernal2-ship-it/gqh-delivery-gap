# Trained Jev movement-risk checkpoints

These nine files are the actual saved neural checkpoints from HiPerGator training
job 44665003. No HiPerGator account is needed to load them. Each contains learned
weights, architecture configuration, feature order, training normalization,
target scaling and quantile levels. The matching code is included in this repo.

**Research and shadow use only.** Every neural variant lost to empirical quantiles
on the reused development evaluation. They are uncalibrated. Downloading them
does not establish trading value, quantum capabilities or HFT latency.

## Install and verify

From a fresh checkout of main:

```sh
git clone https://github.com/sebastbernal2-ship-it/gqh-delivery-gap.git
cd gqh-delivery-gap
python3 -m venv .venv
source .venv/bin/activate
python -m pip install torch==2.8.0 numpy==2.3.2
cd hpc/probabilistic-council
python verify_downloaded_checkpoints.py
```

Use Python 3.12 or 3.13. The download ran with PyTorch 2.8.0 on an NVIDIA L4.
Local CPU parity was also verified with PyTorch 2.14.1 and NumPy 2.5.3.
The verifier checks every checkpoint SHA-256, the original training report and
pinned runtime code, then compares local CPU predictions with HPG GPU predictions.
The expected tolerance is absolute/relative 1e-5. The fixture is synthetic and
exists only to test portability, not to demonstrate a valid live trading state.

Publication validation: all nine checkpoint hashes and CPU/GPU comparisons passed;
the largest absolute prediction difference was below 0.000001 basis points.
The council test suite passed 87 tests and 19 subtests. To rerun it from
`hpc/probabilistic-council`, install `pytest` and run
`PYTHONPATH=. python -m pytest -q tests`.

## Load the trained model

Run this from `hpc/probabilistic-council`:

```python
import json
from pathlib import Path
from execution_risk_predict import ExecutionRiskPredictor

release = Path("checkpoints/hpg-44665003")
manifest = json.loads((release / "manifest.json").read_text())
name = "AB_scratch6.pt"  # Combined book/trade model; not the gate winner.
model = ExecutionRiskPredictor(release / name,
                              manifest["checkpoints"][name]["sha256"],
                              device="cpu")
# sequence: finite 16x24 raw features in the order saved in the checkpoint.
# The predictor applies saved normalization. Do not normalize a second time.
# risk = model.risk(sequence)
```

Output shape is `(3, 2, 2, 3)`: horizons 5/15/60 seconds; buy/sell; terminal
loss/observed adverse excursion; q10/q50/q90, all in basis points. These are
marginal quantiles, not buy/sell probabilities or a calibrated joint distribution.
The full `predict` API adds analytical costs for proposed marketable orders using
a synchronized current book. See [EXECUTION_RISK.md](../../EXECUTION_RISK.md) and
[LIVE_EXECUTION_RISK.md](../../LIVE_EXECUTION_RISK.md) for the input contract.

`A_*` uses book channels, `B_*` uses trade channels, and `AB_*` uses both.
`scratch3` has three supervised epochs, `scratch6` has six, and
`masked3_supervised3` has three training-only masked epochs plus three supervised
epochs. A B-only view still receives the same complete raw feature schema;
the predictor masks unavailable channels after saved normalization.
All nine are preserved so the team can reproduce the declared comparison.
Choosing a neural file here is not a new model-selection or promotion decision.
The gate winner was empirical quantiles, not one of these nine neural files.

## Provenance and publication

[manifest.json](manifest.json) owns file sizes/hashes, export job, runtime pins
and the training-validator difference. [training-report.json](training-report.json)
is the byte-identical report downloaded from HPG, with report digest checked
against the prior inspected receipt. The current dataset validator additionally
accepts audited local-receipt data; that change does not alter inference. The
trained architecture, normalization and scoring code match the staged training code.
[parity.json](parity.json) holds synthetic inputs and HPG reference predictions.
[portability-result.json](portability-result.json) records actual local verification.

The user explicitly requested publication on main. The local `.gitignore` makes
an exception only for the nine named checkpoints in this directory. Other model
weights and raw data remain ignored. The archive itself, raw captures, training
arrays and evaluation arrays are not published here. The original weights remain
on HPG; this is a verified copy, not a move or a retraining run.

The JevLike option scorer's MIT notice remains in [jevlike/LICENSE](../../jevlike/LICENSE).
