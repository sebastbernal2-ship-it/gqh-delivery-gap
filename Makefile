.PHONY: sync save bootstrap doctor current claims overlaps worktree owners chain graph hooks hooks-global remember share absorb test secrets check status

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
	@python3 tests/test_memory_filter.py
	@python3 tests/test_memory_absorb.py
	@python3 tests/test_thesis_index.py
	@python3 tests/test_structure.py
	@python3 tests/test_claims.py
	@python3 tests/test_paths.py
	@python3 tests/test_owners.py
	@python3 tests/test_chain.py
	@python3 tests/test_link_algoterminal.py
	@python3 tests/test_edgar.py
	@python3 tests/test_xbrl.py
	@python3 tests/test_eia.py
	@python3 tests/test_massive_ingest.py
	@python3 tests/test_event.py
	@python3 tests/test_universe.py
	@python3 tests/test_scan.py
	@python3 tests/test_scan_stats.py
	@python3 tests/test_scan_report.py
	@python3 tests/test_scan_fdr.py
	@python3 tests/test_ideas.py
	@python3 tests/test_live.py
	@python3 tests/test_variant_ledger.py
	@python3 tests/test_scan_compute.py
	@python3 tests/test_scan_windows.py

# Count every variant tried, from the artifacts that recorded them.
variants:
	@python3 scripts/build_variant_ledger.py

# Regenerate the idea view from the graph.
ideas:
	@python3 scripts/render_ideas.py

# Credential scan over every file. This repo is public.
secrets:
	@python3 scripts/scan_secrets.py

# Public repo gate: no credentials, and the ledger is valid.
check: secrets
	@python3 scripts/check_theses.py
	@python3 scripts/check_structure.py
	@python3 scripts/check_paths.py
	@python3 scripts/check_owners.py
	@python3 scripts/check_chain.py
	@python3 scripts/link_algoterminal.py
	@python3 scripts/render_current.py --check
	@python3 scripts/check_scan.py
	@python3 scripts/check_ideas.py
	@python3 scripts/render_ideas.py --check

status:
	@git status -sb
