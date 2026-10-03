#!/usr/bin/env bash
# Wire the memory wrapper for whichever agent harnesses this machine has.
#
# The repo's instruction files (AGENTS.md, CLAUDE.md, .cursorrules) are committed and travel
# with the clone. The wrappers below are per-machine, so each teammate runs this once.
set -uo pipefail

cd "$(git rev-parse --show-toplevel)"

if ! command -v hippo >/dev/null 2>&1; then
  cat <<'NOTE'
hippo is not installed on this machine, so memory runs in read-only mode:
your agent reads memory/SHARED.md and docs/, and nothing is captured locally.
Install hippo, then run `make hooks` again.
NOTE
  exit 0
fi

for target in claude-code codex cursor opencode openclaw pi; do
  printf '%-12s ' "$target"
  hippo hook install "$target" 2>&1 | tail -1
done

echo
echo "committed instruction files: AGENTS.md (codex, pi, opencode, openclaw), CLAUDE.md, .cursorrules"
echo "re-run after pulling if a harness file is missing"
