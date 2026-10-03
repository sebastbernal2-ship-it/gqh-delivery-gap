#!/usr/bin/env bash
# Unattended share: refresh the team's memory, commit only the memory files, push.
#
# Safe to run on a timer. It never stages other people's work in progress: the commit
# contains memory/shared.json and memory/SHARED.md and nothing else.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0
[ -f scripts/memory-share.sh ] || exit 0
command -v hippo >/dev/null 2>&1 || exit 0

bash scripts/memory-share.sh >/dev/null 2>&1
git add -- memory/shared.json memory/SHARED.md 2>/dev/null

if git diff --cached --quiet -- memory/shared.json memory/SHARED.md; then
  exit 0
fi

git commit -q -m "memory: autoshare $(hostname -s) $(date -u +%Y-%m-%dT%H:%MZ)" \
  -- memory/shared.json memory/SHARED.md || exit 0

for attempt in 1 2 3; do
  if git push -q 2>/dev/null; then
    echo "autoshare: pushed"
    exit 0
  fi
  git pull -q --rebase --autostash 2>/dev/null || break
done
echo "autoshare: committed locally, push deferred"
