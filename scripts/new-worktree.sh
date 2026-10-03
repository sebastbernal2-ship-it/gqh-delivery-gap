#!/usr/bin/env bash
# Give a workstream its own checkout on its own branch, so two agents never share a directory.
#
#   make worktree NAME=vishnu-fast
#
# Creates ../quanthacks-worktrees/<name> on a fresh branch off main.
set -euo pipefail

NAME="${1:-}"
[ -n "$NAME" ] || { echo "usage: make worktree NAME=<short-name>" >&2; exit 2; }

ROOT="$(git rev-parse --show-toplevel)"
BRANCH="feat/${NAME}"
DEST="$(dirname "$ROOT")/quanthacks-worktrees/${NAME}"

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "branch ${BRANCH} already exists; adding a worktree for it"
  git worktree add "$DEST" "$BRANCH"
else
  git fetch --quiet origin || true
  git worktree add -b "$BRANCH" "$DEST" origin/main
fi

cat <<NOTE

worktree ready: $DEST  (branch $BRANCH)
next:
  cd $DEST
  make sync
  make doctor
push the branch early so the team can see it in \`make claims\`.
NOTE
