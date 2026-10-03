.PHONY: sync save bootstrap memory all check status

# Pull the team's work before you do anything.
sync:
	git pull --rebase --autostash

# Commit and push one logical change. Usage: make save M="what changed"
save:
	@test -n "$(M)" || (echo 'usage: make save M="what changed"' && exit 1)
	git add -A
	git commit -m "$(M)"
	git push

# First time on a new device.
bootstrap:
	bash scripts/bootstrap.sh

# Export this device's local memory so the team converges.
memory:
	bash scripts/memory-export.sh

# Regenerate every number the note quotes.
all:
	@test -f src/pipeline.py || (echo "src/pipeline.py does not exist yet. See docs/02-system.md." && exit 1)
	python -m src.pipeline

# Cheap gate before a commit that touches results.
check:
	@python scripts/check_results.py

status:
	@git status -sb
	@echo "--- results ---"
	@ls -1 results/*.json 2>/dev/null || echo "(no result files yet)"
