# Results

Numbers that the note quotes come from a committed file in this folder, produced by code in this
repo. That is the only rule for now.

The file shape gets defined by the first real result, and recorded in `docs/decisions.md` when
it is. Do not pre-build a schema for engines that do not exist.

## Generated strategy artifacts

These paths are output contracts, not assertions that a run has produced data. Their producers must run before consumers such as the manifest and promotion gate. The path checker permits only the explicitly declared result paths below; it still checks source-code and documentation references.

Produced by `scripts/build_issuer_exposure_ledger.py`:

generated-path: results/issuer-exposure-ledger.csv

Produced by `scripts/build_market_control_panel.py`:

generated-path: results/market-control-panel.csv

Produced by `scripts/build_tradeability_panel.py`:

generated-path: results/tradeability-panel.csv

Produced by `scripts/build_run_manifest.py`:

generated-path: results/run-manifest.json

Produced by `scripts/review_crosswalk.py`:

generated-path: results/crosswalk-review.csv

Produced by `scripts/run_market_control_stress.py`:

generated-path: results/market-control-stress.csv

Produced by `scripts/summarize_capacity_strategy.py`:

generated-path: results/capacity-strategy-summary.json
generated-path: results/capacity-equity.svg

Produced by `scripts/build_queue_panel.py`:

generated-path: results/queue-panel.csv
generated-path: results/queue-summary.json

Produced by `scripts/build_queue_crosswalk.py`:

generated-path: results/queue-crosswalk.csv
generated-path: results/queue-crosswalk-summary.json
