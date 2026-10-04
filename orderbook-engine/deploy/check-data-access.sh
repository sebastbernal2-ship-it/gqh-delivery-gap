#!/usr/bin/env bash
# Prove this machine can reach every configured data source.
#
#   bash deploy/check-data-access.sh
#
# Reads credentials from the secret store, which lives outside the repository.
# Prints status per source and prints no credential value. A source without a
# configured credential is reported as skipped, not as a failure.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ENV_FILE="${ENV_FILE:-$HOME/.config/quanthacks/env}"
VENV="${DATA_VENV:-$HOME/.venv/quanthacks-data}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
else
  echo "no secret store at $ENV_FILE, nothing to check"
  exit 0
fi

status=0
say() { printf '%-10s %s\n' "$1" "$2"; }

# Python deps for the database checks, installed once.
if [ ! -x "$VENV/bin/python" ]; then
  echo "preparing $VENV (first run only)"
  python3 -m venv "$VENV" >/dev/null
  "$VENV/bin/pip" install --quiet "psycopg[binary]" snowflake-connector-python >/dev/null
fi

if [ -n "${MASSIVE_API_KEY:-}" ]; then
  code=$(curl -s -o /dev/null -m 25 -w '%{http_code}' \
    "https://api.massive.com/v1/marketstatus/now" -H "Authorization: Bearer $MASSIVE_API_KEY" || true)
  if [ "$code" = "200" ]; then say massive "ok, http 200"; else say massive "FAILED, http $code"; status=1; fi
else
  say massive "skipped, no key configured"
fi

if [ -n "${TIGERDATA_URL:-}" ]; then
  out=$("$VENV/bin/python" - <<'PY' 2>&1 | tail -1
import os, psycopg
# The URL carries the user and host; the password arrives separately.
with psycopg.connect(os.environ["TIGERDATA_URL"],
                     password=os.environ.get("TIGERDATA_PASSWORD"),
                     autocommit=True) as conn:
    cur = conn.cursor()
    cur.execute("select count(*) from depth_events")
    depth = cur.fetchone()[0]
    cur.execute("select count(*) from trade_events")
    trades = cur.fetchone()[0]
print(f"ok, depth_events={depth} trade_events={trades}")
PY
) || true
  case "$out" in
    ok,*) say tiger "$out";;
    *) say tiger "FAILED, $out"; status=1;;
  esac
else
  say tiger "skipped, no url configured"
fi

if [ -n "${SNOWFLAKE_ACCOUNT:-}" ] && [ -n "${SNOWFLAKE_PRIVATE_KEY_PATH:-}" ]; then
  out=$("$VENV/bin/python" - <<'PY' 2>&1 | tail -1
import os
import snowflake.connector as sc
from cryptography.hazmat.primitives import serialization
key = open(os.path.expanduser(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]), "rb").read()
pkb = serialization.load_pem_private_key(key, password=None).private_bytes(
    encoding=serialization.Encoding.DER, format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption())
with sc.connect(account=os.environ["SNOWFLAKE_ACCOUNT"], user=os.environ["SNOWFLAKE_USER"],
                private_key=pkb, role=os.environ.get("SNOWFLAKE_ROLE"),
                warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE")) as conn:
    cur = conn.cursor()
    cur.execute("select current_role()")
    role = cur.fetchone()[0]
    cur.execute("select count(*) from VECTOR_RESEARCH.RAW.SOURCE_RECORDS")
    rows = cur.fetchone()[0]
print(f"ok, role={role} source_records={rows}")
PY
) || true
  case "$out" in
    ok,*) say snowflake "$out";;
    *) say snowflake "FAILED, $out"; status=1;;
  esac
else
  say snowflake "skipped, no account or key path configured"
fi

exit "$status"
