.PHONY: sync save bootstrap doctor current hooks hooks-global remember share absorb test secrets check status

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

# Credential scan over every file. This repo is public.
secrets:
	@python3 scripts/scan_secrets.py

# Public repo gate: no credentials, and the ledger is valid.
check: secrets
	@python3 scripts/check_theses.py

status:
	@git status -sb
