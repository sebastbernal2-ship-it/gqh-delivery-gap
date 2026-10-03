#!/usr/bin/env bash
# Wire the memory wrapper for this machine's agent harnesses.
#
# Two groups, and the difference matters:
#
#   repo-file targets   pi, codex, cursor, openclaw
#                       These only write instruction text into committed files
#                       (AGENTS.md, .cursorrules). Safe, and they travel with the clone.
#
#   machine-wide targets claude-code, opencode
#                       These edit configuration in your home directory, which affects
#                       every project on this machine, not just this repo. Opt in with
#                       `make hooks-global`.
set -uo pipefail

cd "$(git rev-parse --show-toplevel)"
MODE="${1:-repo}"

if ! command -v hippo >/dev/null 2>&1; then
  cat <<'NOTE'
hippo is not installed on this machine, so memory is read-only here:
your agent reads memory/SHARED.md and docs/, and nothing is captured locally.
Install hippo, then run `make hooks` again.
NOTE
  exit 0
fi

run() {
  printf '%-12s ' "$1"
  hippo hook install "$1" 2>&1 | tail -1
}

echo "repo-file targets (committed instruction files):"
for target in pi codex cursor openclaw; do run "$target"; done

if [ "$MODE" = "--global" ]; then
  echo
  echo "machine-wide targets (edits your home directory, affects every project here):"
  for target in claude-code opencode; do run "$target"; done
else
  cat <<'NOTE'

machine-wide targets skipped: claude-code and opencode edit your home directory and
affect every project on this machine, not just this repo. If you want capture wired
for those harnesses, run: make hooks-global

You do not need them for this repo to work. The committed instruction files
(AGENTS.md, CLAUDE.md, .cursorrules) already carry the protocol, and capture still
happens through .githooks/pre-commit on every commit.
NOTE
fi
