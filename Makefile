.PHONY: sync save bootstrap remember share absorb autoshare schedule unschedule memory test secrets all check status

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

# Unattended: share, commit only the memory files, push. Safe on a timer.
autoshare:
	@bash scripts/autoshare.sh

# Opt in: run autoshare every 15 minutes on this machine.
schedule:
	@bash scripts/schedule.sh install

unschedule:
	@bash scripts/schedule.sh uninstall

# Private device-to-device export. Gitignored.
memory:
	bash scripts/memory-export.sh

test:
	@python3 tests/test_memory_filter.py
	@python3 tests/test_memory_absorb.py

# Public repo gate. Run before a push.
secrets:
	@python3 scripts/scan_secrets.py

# Regenerate every number the note quotes.
all:
	@test -f src/pipeline.py || (echo "src/pipeline.py does not exist yet. See docs/02-system.md." && exit 1)
	python -m src.pipeline

# Cheap gate before a commit that touches results.
check: secrets
	@python scripts/check_results.py

status:
	@git status -sb
	@echo "--- results ---"
	@ls -1 results/*.json 2>/dev/null || echo "(no result files yet)"
