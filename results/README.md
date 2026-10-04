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

Produced by `scripts/build_queue_tail_study.py`:

generated-path: results/queue-tail-study.json

Produced by `scripts/probe_queue_slip.py`:

generated-path: results/queue-slip-probe.json

Produced by `scripts/fetch_provider_capex.py` and `scripts/build_compute_lead_study.py`:

generated-path: results/provider-capex-quarterly.csv
generated-path: results/compute-lead-study.json

Produced by `scripts/build_queue_exit_study.py`:

generated-path: results/queue-exit-study.json

Produced by `scripts/build_graph_propagation.py`:

generated-path: results/graph-propagation-summary.json

Produced by `scripts/build_provider_transmission_study.py`:

generated-path: results/provider-transmission-study.json

Produced by `scripts/build_cascade_reversion_study.py`:

generated-path: results/cascade-reversion-study.json

Produced by `scripts/fetch_provider_revenue.py`:

generated-path: results/provider-revenue-quarterly.csv

Produced by `scripts/build_provider_family_tests.py`:

generated-path: results/provider-family-tests.json

Produced by `scripts/build_provider_family_tests.py --mode relative`:

generated-path: results/provider-family-tests-relative.json

Produced by `scripts/build_maker_entry_study.py`:

generated-path: results/maker-entry-study.json

Produced by `scripts/build_capex_revenue_gap.py`:

generated-path: results/capex-revenue-gap.json

Produced by `scripts/build_spillover_study.py`:

generated-path: results/spillover-study.json

Produced by `scripts/build_intensity_pricing_study.py`:

generated-path: results/intensity-pricing-study.json

Produced by `scripts/build_intensity_factor_study.py`:

generated-path: results/intensity-factor-study.json

Produced by `scripts/fetch_complex_fundamentals.py`:

generated-path: results/complex-capex-quarterly.csv

Produced by `scripts/fetch_complex_fundamentals.py`:

generated-path: results/complex-revenue-quarterly.csv

Produced by `scripts/build_intensity_segment_study.py`:

generated-path: results/intensity-segment-study.json

Produced by `scripts/build_intensity_timesplit_study.py`:

generated-path: results/intensity-timesplit-study.json

Produced by `scripts/build_intensity_vs_assetgrowth_study.py`:

generated-path: results/intensity-vs-assetgrowth-study.json

Produced by `scripts/fetch_complex_assets.py`:

generated-path: results/complex-assets-quarterly.csv

Produced by `scripts/build_intensity_preboom_study.py`:

generated-path: results/intensity-preboom-study.json

Produced by `scripts/build_intensity_robustness_study.py`:

generated-path: results/intensity-robustness-study.json

Produced by `scripts/fetch_universe_volume.py`:

generated-path: results/universe-adv-monthly.csv

Produced by `scripts/run_intensity_strategy.py`:

generated-path: results/intensity-strategy.json

Produced by `scripts/run_intensity_strategy.py --cost-mult 2.0 --output results/intensity-strategy-doubled.json`:

generated-path: results/intensity-strategy-doubled.json

Produced by `scripts/build_intensity_controls_study.py`:

generated-path: results/intensity-controls-study.json

Produced by `scripts/fetch_complex_margins.py`:

generated-path: results/complex-margins-quarterly.csv

Produced by `scripts/build_compute_queue_study.py`:

generated-path: results/compute-queue-study.json

Produced by `scripts/build_regime_state.py`:

generated-path: results/regime-state-daily.csv

Produced by `scripts/build_regime_state.py`:

generated-path: results/regime-state-summary.json

Produced by `scripts/hyperliquid_capability_test.py`:

generated-path: results/hyperliquid-capability.json

Produced by `scripts/build_hyperliquid_contract_terms.py`:

generated-path: results/hyperliquid-contract-terms.json

Produced by `scripts/build_hyperliquid_fixture.py`:

generated-path: results/hyperliquid-fixture/

Produced by `scripts/detect_forced_flow.py`:

generated-path: results/hyperliquid-forced-flow-candidates.jsonl

Produced by `scripts/evaluate_ws_capture_conjunction.py`:

generated-path: results/hyperliquid-ws-conjunction.json

Produced by `scripts/build_filing_specialist_panel.py`:

generated-path: results/filing-specialist-events.csv

Produced by `scripts/run_filing_specialist.py`:

generated-path: results/filing-specialist-scores.json

Produced by `scripts/fetch_filing_texts.py`:

generated-path: results/filing-text-manifest.json

Produced by `hpc/probabilistic-council/filing_scorer.py`:

generated-path: results/filing-text-scores.json

Produced by `hpc/probabilistic-council/filing_scorer.py --encoder hf`:

generated-path: results/filing-text-scores-frozen.json

Produced by `hpc/probabilistic-council/run_filing_text_ab.py`:

generated-path: results/filing-text-ab.json

Produced by `scripts/run_filing_council.py`:

generated-path: results/filing-council-ab.json

Produced by `scripts/run_decision_layer.py`:

generated-path: results/decision-layer.json

Produced by `scripts/run_rpo_market_council.py`:

generated-path: results/rpo-market-council.json

Produced by `scripts/run_surprise_alpha.py`:

generated-path: results/surprise-alpha.json

Produced by `scripts/build_complex_panels_pit.py` (corrected disclosure clocks):

generated-path: results/complex-capex-quarterly-pit.csv
generated-path: results/complex-revenue-quarterly-pit.csv

Produced by `scripts/build_driver_vintages.py` (corrected clocks):

generated-path: results/capex-vintages-pit.csv
generated-path: results/revenue-vintages-pit.csv

Produced by `scripts/run_intensity_pit_clock_test.py`:

generated-path: results/intensity-clock-test.json

Produced by `scripts/run_driver_surprise.py`:

generated-path: results/revenue-surprise.json
generated-path: results/capex-surprise.json

Produced by `scripts/run_intensity_gate_test.py`:

generated-path: results/intensity-gate-test.json

Produced by `scripts/run_sleeve_portfolio.py`:

generated-path: results/sleeve-portfolio.json

The ignored bar cache is repaired by `scripts/repair_unadjusted_bars.py` and `scripts/sanitize_bar_cache.py`; neither writes a tracked artifact.

Produced by `scripts/run_three_sleeve_portfolio.py`:

generated-path: results/three-sleeve-portfolio.json

Produced by `scripts/run_walk_forward.py` (rolling origins, annual refits):

generated-path: results/walk-forward.json

Produced by `scripts/run_capacity_curve.py`:

generated-path: results/capacity-curve.json

Produced by `scripts/run_forward_snapshot.py` (append-only, tracked on purpose so the frozen predictions are tamper-evident):

generated-path: results/forward/snapshots/*.json

Scored once, at the end, by `scripts/evaluate_forward_window.py`:

generated-path: results/forward/evaluation.json

Produced by `scripts/build_rpo_universe_panel.py` (broad cached frames, acceptance clocks):

generated-path: results/rpo-universe-vintages.csv

Produced by `scripts/run_universe_surprise.py`:

generated-path: results/rpo-universe-scores.json

Produced by `scripts/build_universe_driver_panels.py` (broad companyconcept, earliest-filed):

generated-path: results/universe-revenue-quarterly.csv
generated-path: results/universe-capex-quarterly.csv

Produced by `scripts/build_driver_vintages.py` on the broad panels:

generated-path: results/universe-revenue-vintages.csv
generated-path: results/universe-capex-vintages.csv

Produced by `scripts/run_driver_surprise.py` on the broad panels:

generated-path: results/universe-revenue-scores.json
generated-path: results/universe-capex-scores.json

Produced by `scripts/build_rpo_vintages.py`:

generated-path: results/rpo-vintages.csv

Produced by `scripts/build_rpo_vintages.py --panel results/obligation-panel.csv`:

generated-path: results/obligation-vintages.csv

Produced by `scripts/build_filing_obligation_panel.py`:

generated-path: results/filing-obligation-decisions.csv

Produced by `scripts/run_filing_obligation_panel.py`:

generated-path: results/filing-obligation-scores.json

Produced by `hpc/probabilistic-council/run_filing_obligation_text.py`:

generated-path: results/filing-obligation-text.json

Produced by `scripts/run_rpo_specialist.py`:

generated-path: results/rpo-specialist-scores.json

Produced by `scripts/build_filings_register.py --out results/filings-register-rpo.csv`:

generated-path: results/filings-register-rpo.csv

Produced by `scripts/run_rpo_filing_panel.py`:

generated-path: results/rpo-filing-panel-scores.json
