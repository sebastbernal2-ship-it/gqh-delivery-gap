#!/usr/bin/env bash
# Publish the research site, then verify it is actually serving.
#
# The research site is the Vercel project `docs` (default domain docs-roan-seven.vercel.app). Other apps
# in this repo must deploy to their own project: the production alias is the link handed to judges, and a
# foreign deploy to this project replaces it with an app that 404s these paths.
#
# Copies docs/ to a scratch directory, links the scratch copy to the `docs` project, deploys it, then
# checks the published pages on both the shared alias and the private mirror.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH="${TMPDIR:-/tmp}/gqh-docs-publish"
rm -rf "$SCRATCH"
cp -r "$ROOT/docs" "$SCRATCH"
rm -rf "$SCRATCH/.vercel"
cd "$SCRATCH"

npx --yes vercel@latest link --yes --project docs >/dev/null 2>&1 || true
URL=$(npx --yes vercel@latest deploy --prod --yes 2>&1 | grep -Eo "https://[a-zA-Z0-9.-]+\.vercel\.app" | tail -1)
echo "deployed: $URL"

for path in / /note.html /scan/field.html /scan/graph-propagation.html /scan/connection-index.html /scan/decomposition.html; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "https://docs-roan-seven.vercel.app${path}")
  printf "  docs-roan-seven.vercel.app%s -> %s\n" "$path" "$code"
  code_new=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "https://gqh-site.vercel.app${path}")
  printf "  gqh-site.vercel.app%s -> %s\n" "$path" "$code_new"
done
