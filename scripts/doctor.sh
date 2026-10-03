#!/usr/bin/env bash
# Health check for the shared memory system. Read only.
#
# Answers three questions:
#   1. Is this project's memory isolated to this repo, or is it bleeding into a shared store?
#   2. Does every harness that opens this repo get the protocol?
#   3. Is capture wired and is the shared memory current?
set -uo pipefail

cd "$(git rev-parse --show-toplevel)"
ROOT="$PWD"
problems=0
note() { printf '  %s\n' "$*"; }
bad() { printf '  PROBLEM: %s\n' "$*"; problems=$((problems + 1)); }

echo "repo: $ROOT"
echo

echo "1. memory isolation"
resolve_store() {
  local d="$1"
  while [ "$d" != "/" ] && [ -n "$d" ]; do
    [ -f "$d/.hippo/hippo.db" ] && { printf '%s' "$d"; return 0; }
    d="$(dirname "$d")"
  done
}
STORE="$(resolve_store "$ROOT")"
note "resolved store: ${STORE:-none}"
case "$STORE" in
  "$ROOT") note "scope: this repo only (good)" ;;
  "") bad "no store found. Run: make bootstrap" ;;
  *) bad "store is OUTSIDE the repo at $STORE. Project memories here can appear in other projects' sessions. Fix: run make bootstrap so this repo gets its own store." ;;
esac

if command -v hippo >/dev/null 2>&1; then
  export HIPPO_OUT="$(mktemp)"
  hippo export "$HIPPO_OUT" >/dev/null 2>&1
  python3 - "$HIPPO_OUT" "$ROOT" <<'PY'
import json, sys
from pathlib import Path
try:
    entries = json.loads(Path(sys.argv[1]).read_text())
except Exception:
    entries = []
root = sys.argv[2]
foreign = []
for m in entries:
    tags = m.get("tags", []) or []
    paths = [t for t in tags if t.startswith("path:")]
    if not any(t in ("quanthacks", "gqh", "gator-quant-hacks") for t in tags):
        if not paths:
            foreign.append((m.get("id"), "no project tag", (m.get("content") or "")[:50]))
            continue
        if not any("quanthacks" in t or "gqh" in t for t in paths):
            foreign.append((m.get("id"), "tagged to another path", (m.get("content") or "")[:50]))
print(f"  entries in store: {len(entries)}")
if foreign:
    print(f"  PROBLEM: {len(foreign)} entr(ies) not recognisably this project:")
    for i, why, text in foreign[:5]:
        print(f"    - {i}: {why}: {text}")
    sys.exit(3)
print("  every entry is this project's (good)")
PY
  case $? in 3) problems=$((problems + 1)) ;; esac
  rm -f "$HIPPO_OUT"
else
  note "hippo not installed here: memory is read-only (memory/SHARED.md + docs/)"
fi
echo

echo "2. harness coverage"
for f in AGENTS.md CLAUDE.md .cursorrules; do
  if [ -f "$f" ]; then
    if grep -q "hippo:start" "$f"; then
      note "$(printf '%-13s' "$f") present, protocol and memory block (good)"
    else
      note "$(printf '%-13s' "$f") present, no memory block (run: make hooks)"
    fi
  else
    bad "$f missing. A harness that reads it gets no protocol"
  fi
done
echo

echo "3. capture and shared memory"
if git config user.email >/dev/null 2>&1; then
  note "git identity: $(git config user.email)"
else
  bad "git has no user.email here, so commits will fail. Set it: git config --global user.email you@example.com"
fi
if [ "$(git config core.hooksPath)" = ".githooks" ]; then
  note "commit hook enabled (good)"
else
  bad "commit hook not enabled. Run: make bootstrap"
fi
if [ -s memory/shared.json ]; then
  note "shared memory: $(python3 -c 'import json;print(len(json.load(open("memory/shared.json"))))') entries"
else
  bad "memory/shared.json is empty or missing"
fi
if git diff --quiet -- memory/shared.json 2>/dev/null; then
  note "shared memory matches the last commit"
else
  note "shared memory has uncommitted changes (make save)"
fi
echo

echo "4. the live position"
if [ -f docs/theses/index.jsonl ]; then
  active="$(python3 - <<'PYEOF'
import json
from pathlib import Path
rows = []
for line in Path("docs/theses/index.jsonl").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    try:
        rows.append(json.loads(line))
    except json.JSONDecodeError:
        pass
print(len([r for r in rows if r.get("status") == "active"]))
PYEOF
)"
  note "active theses in the ledger: $active"
  if [ "$active" -eq 0 ]; then
    note "no active thesis recorded. The team is between positions (allowed, but say so out loud)."
  fi
  if [ docs/CURRENT.md -ot docs/theses/index.jsonl ]; then
    bad "docs/CURRENT.md is older than the ledger. Run: make current"
  else
    note "docs/CURRENT.md is current with the ledger"
  fi
else
  bad "docs/theses/index.jsonl is missing: there is no ledger to record the position in"
fi
echo

if [ "$problems" -gt 0 ]; then
  echo "first run on a new machine: make bootstrap fixes all of the above"
  echo
fi
if [ "$problems" -eq 0 ]; then
  echo "result: healthy"
else
  echo "result: $problems problem(s) above"
fi
exit 0
