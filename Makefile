.PHONY: market sync save bootstrap doctor current claims overlaps worktree owners chain graph hooks hooks-global remember share absorb test engine-test secrets check strategy-check manifest pdf-check gate-status status agency-deals tranche-table credit-deals deal-structure deal-diligence deal-ratings gate-scorecard credit-gauntlet credit-gauntlet-long ownership-layer index-mandate cascade-tape

# Pull the team's work and load their shared memory. Run this first, every session.
sync:
	git pull --rebase --autostash
	@bash scripts/memory-absorb.sh

# Commit and push one logical change. Usage: make save M="what changed"
save:
	@test -n "$(M)" || (echo 'usage: make save M="what changed"' && exit 1)
	git add -A
	git commit -m "$(M)"
	git push

# First time on a new device.
bootstrap:
	bash scripts/bootstrap.sh

# Regenerate docs/CURRENT.md from the thesis ledger. Run after appending a record.
current:
	@python3 scripts/render_current.py

# Health check for the memory system. Read only, safe to run any time.
doctor:
	@bash scripts/doctor.sh

# Chain logs: scope caps, load bearing edges, evidence, and the freeze.
chain:
	@python3 scripts/check_chain.py
	@python3 scripts/link_algoterminal.py

# Resolve our nodes, representations and sources against the algoterminal stack.
graph:
	@python3 scripts/link_algoterminal.py

# Ownership: one roster, one claim table, every claimed path real.
owners:
	@python3 scripts/check_owners.py
	@python3 scripts/check_chain.py
	@python3 scripts/link_algoterminal.py

# Who is working on what, and where will that collide. Fetches first.
claims:
	@python3 scripts/claims.py

# Only the collisions, which is the part that costs hours.
overlaps:
	@python3 scripts/claims.py --overlaps

# Give a workstream its own checkout on its own branch. Usage: make worktree NAME=<name>
worktree:
	@test -n "$(NAME)" || (echo 'usage: make worktree NAME=<short-name>' && exit 1)
	@bash scripts/new-worktree.sh "$(NAME)"

# Wire the memory wrapper for the harnesses that only touch committed files. Safe.
hooks:
	@bash scripts/install-hooks.sh repo

# Also wire the harnesses that edit your home directory. Affects every project here.
hooks-global:
	@bash scripts/install-hooks.sh --global

# Write a memory that the team will see. Usage: make remember M="what you learned"
remember:
	@test -n "$(M)" || (echo 'usage: make remember M="what you learned"' && exit 1)
	hippo remember "$(M)" --tag gqh

# Share this device's memory with the team, filtered for the public repo.
share:
	@bash scripts/memory-share.sh

# Load the team's shared memory into this device's local store.
absorb:
	@bash scripts/memory-absorb.sh

test:
	@python3 tests/test_snowflake_research_sidecar.py
	@python3 tests/test_regime_risk_control.py
	@python3 tests/test_market_map.py
	@python3 tests/test_memory_filter.py
	@python3 tests/test_memory_absorb.py
	@python3 tests/test_thesis_index.py
	@python3 tests/test_structure.py
	@python3 tests/test_claims.py
	@python3 tests/test_paths.py
	@python3 tests/test_owners.py
	@python3 tests/test_chain.py
	@python3 tests/test_truths.py
	@python3 tests/test_link_algoterminal.py
	@python3 tests/test_edgar.py
	@python3 tests/test_xbrl.py
	@python3 tests/test_eia.py
	@python3 tests/test_event.py
	@python3 tests/test_strategy_contracts.py
	@python3 tests/test_market_runner.py
	@python3 tests/test_market_control_panel.py
	@python3 tests/test_tradeability_panel.py
	@python3 tests/test_crosswalk_review.py
	@python3 tests/test_pdf_renderer.py
	@python3 tests/test_strategy_builders.py
	@python3 tests/test_strategy_sources.py
	@python3 tests/test_strategy_e2e.py
	@python3 tests/test_run_manifest.py
	@python3 tests/test_controls_metrics.py
	@python3 tests/test_strategy_identification.py
	@python3 tests/test_universe.py
	@python3 tests/test_scan.py
	@python3 tests/test_quantgraph_manifest.py
	@python3 tests/test_scan_stats.py
	@python3 tests/test_scan_report.py
	@python3 tests/test_scan_fdr.py
	@python3 tests/test_ideas.py
	@python3 tests/test_live.py
	@python3 tests/test_variant_ledger.py
	@python3 tests/test_imagery.py
	@python3 tests/test_hazard.py
	@python3 tests/test_factors.py
	@python3 tests/test_scan_compute.py
	@python3 tests/test_scan_windows.py
	@python3 tests/test_cascade_evaluation.py
	@python3 tests/test_index_mandate.py
	@python3 tests/test_ownership_layer.py
	@python3 tests/test_intensity_accounting.py
	@python3 tests/test_filing_specialist.py
	@python3 tests/test_filing_text.py
	@python3 tests/test_filing_options.py
	@python3 tests/test_rpo_vintages.py
	@python3 tests/test_rpo_specialist.py
	@python3 tests/test_rpo_filing_panel.py
	@python3 tests/test_text_ab.py
	@python3 tests/test_live_risk_plan.py
	@python3 tests/test_decision_layer.py
	@python3 tests/test_market_state.py
	@python3 tests/test_council_diagnostics.py
	@python3 tests/test_specialist_registry.py
	@python3 tests/test_coupling.py
	@python3 tests/test_event_returns.py
	@python3 tests/test_driver_vintages.py
	@python3 tests/test_intensity_gate.py
	@python3 tests/test_rpo_universe_panel.py
	@python3 tests/test_bars_sanity.py
	@python3 tests/test_portfolio_stats.py
	@python3 tests/test_three_sleeve.py
	@python3 tests/test_build_hyperliquid_fixture.py
	@python3 tests/test_split_hyperliquid_engine_fixture.py
	@python3 tests/test_compute_lead_dependence_audit.py
	@python3 tests/test_warehouse_revision_event_study.py
	@python3 -m unittest discover -s orderbook-engine/collector/tiger -p 'test_*.py'

# Exact-integer simulator regression suite; requires the orderbook-engine opam environment.
engine-test:
	cd orderbook-engine && opam exec -- dune runtest --force

# Fit the delivery model: what moves a promise, controls first then factors.
delivery-model:
	@python3 scripts/run_delivery_model.py

# Count every variant tried, from the artifacts that recorded them.
variants:
	@python3 scripts/build_variant_ledger.py

# Apply the pre-registered cascade rule to the recorded tape: docs/plan/cascade-protocol.md.
cascade-tape:
	@python3 scripts/evaluate_cascade_tape.py --json results/cascade-tape.json | tee results/cascade-tape.txt

# Regenerate the idea view from the graph.
ideas:
	@python3 scripts/render_ideas.py

# The credit and deal layer, the ownership crosswalk, and the index mandate study.
agency-deals:
	@python3 scripts/build_agency_only_deals.py --workers 10
	@python3 scripts/declare_deal_nodes.py

tranche-table:
	@python3 scripts/build_tranche_table.py --workers 6
	@python3 scripts/build_indenture_layer.py --workers 6

credit-deals:
	@python3 scripts/build_credit_deal_registry.py --pages 3

deal-structure:
	@python3 scripts/build_deal_structure.py

deal-diligence:
	@python3 scripts/build_deal_diligence.py --workers 4

deal-ratings:
	@python3 scripts/build_deal_ratings.py

gate-scorecard:
	@python3 scripts/build_gate_scorecard.py

credit-gauntlet:
	@python3 scripts/build_credit_panel.py
	@python3 scripts/run_credit_gauntlet.py --draws 500 --block 20

credit-gauntlet-long:
	@python3 scripts/build_credit_panel.py
	@python3 scripts/run_credit_gauntlet.py --set long --draws 500 --block 20
	@python3 scripts/check_credit_stability.py

ownership-layer:
	@python3 scripts/build_ownership_crosswalk.py

index-mandate:
	@python3 scripts/build_index_mandate_study.py

# Credential scan over every file. This repo is public.
secrets:
	@python3 scripts/scan_secrets.py

# Validate any supplied typed strategy package. Usage: make strategy-check EVENTS=...
strategy-check:
	@test -n "$(EVENTS)$(EXPOSURES)$(PHYSICAL)$(TRADES)$(CROSSWALK)" || (echo 'usage: make strategy-check EVENTS=... [EXPOSURES=...] [PHYSICAL=...] [TRADES=...]' && exit 1)
	@python3 scripts/check_strategy_ledger.py $(if $(EVENTS),--events $(EVENTS),) $(if $(EXPOSURES),--exposures $(EXPOSURES),) $(if $(PHYSICAL),--physical $(PHYSICAL),) $(if $(TRADES),--trades $(TRADES),) $(if $(CROSSWALK),--crosswalk $(CROSSWALK),)

# Hash current strategy inputs and record the code revision.
manifest:
	@python3 scripts/build_run_manifest.py

# Report the closed or open strategy promotion gate.
gate-status:
	@python3 scripts/report_promotion_gate.py

# Report the selected HTML-to-PDF renderer. Use RENDER=1 to render when installed.
pdf-check:
	@python3 scripts/check_pdf_renderer.py $(if $(RENDER),--render,)

# Public repo gate: no credentials, and the ledger is valid.
check: secrets
	@python3 scripts/check_market_map.py
	@python3 scripts/check_theses.py
	@python3 scripts/check_structure.py
	@python3 scripts/check_paths.py
	@python3 scripts/check_owners.py
	@python3 scripts/check_chain.py
	@python3 scripts/link_algoterminal.py
	@python3 scripts/render_current.py --check
	@python3 scripts/check_scan.py
	@python3 scripts/check_quantgraph_manifest.py
	@python3 scripts/check_ideas.py
	@python3 scripts/check_truths.py
	@python3 scripts/render_ideas.py --check

status:
	@git status -sb

# Regenerate the market map view and validate it: who is forced, by what, and into which instrument.
market:
	@python3 scripts/render_market_map.py
	@python3 scripts/check_market_map.py

# Optional local HPC regression suite. Requires PyTorch and g++ for native parity.
# Example: make test-hpc HPC_PYTHON=/path/to/venv/bin/python
.PHONY: test-hpc
HPC_PYTHON ?= python3
test-hpc:
	@$(HPC_PYTHON) -m unittest discover -s hpc/kdb-timeseries/tests -v
	@$(HPC_PYTHON) -m unittest discover -s hpc/probabilistic-council/tests -v
