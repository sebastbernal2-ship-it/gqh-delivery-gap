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

# A commit needs an identity. Without one, the first commit fails with a message
# nobody enjoys reading at 2am.
if ! git config user.email >/dev/null 2>&1; then
  echo "NOTE: git has no user.email on this machine. Commits will fail until you set it:"
  echo "  git config --global user.name \"Your Name\""
  echo "  git config --global user.email \"you@example.com\""
fi

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

cat <<'PROTOCOL'

Check the gates:    make check
Run the tests:      make test
Reproduce the work: make reproduce

Every number in the note comes from a file under results/.
The out-of-sample window is opened once, by its owner, and reported as it lands.

PROTOCOL
