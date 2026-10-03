#!/usr/bin/env bash
# First run on a new device. Checks tooling, builds the environment, prints the protocol.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

command -v git >/dev/null || fail "git is not installed"
command -v python3 >/dev/null || fail "python3 is not installed"

PYVER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
case "$PYVER" in
  3.1[1-9]|3.[2-9][0-9]) : ;;
  *) fail "python 3.11 or newer is required, found $PYVER" ;;
esac

if ! command -v gh >/dev/null; then
  echo "note: gh is not installed. Cloning and pushing still work over https."
fi

if [ ! -d .venv ]; then
  echo "creating .venv"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -e .
echo "environment ready: $(python -V)"

# Mechanical capture: every commit refreshes and stages the shared memory.
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh 2>/dev/null || true

# Load the team's shared memory so recall works from the first session.
if [ -s memory/shared.json ]; then
  bash scripts/memory-absorb.sh
fi

cat <<'PROTOCOL'

Capture is automatic:  agent hook (AGENTS.md) + pre-commit hook
Before you start:      make sync
Work in your paths:    see OWNERS.md
Commit a unit of work: make save M="what changed"
Check results shape:   make check
Export local memory:   make memory
Stop for the night:    make sync
Optional unattended:   make schedule

Two rules that decide the score:
  1. If it is not in this repo, it is not shared.
  2. The out-of-sample window is opened once, by its owner, and reported as it lands.

PROTOCOL
