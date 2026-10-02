#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/home/ubuntu/collector/data}"
OCI_NAMESPACE="${OCI_NAMESPACE:?OCI_NAMESPACE is required}"
OCI_BUCKET="${OCI_BUCKET:?OCI_BUCKET is required}"
OCI_PREFIX="${OCI_PREFIX:-market-simulator/binance/}"
[[ "$OCI_PREFIX" == */ ]] || OCI_PREFIX="$OCI_PREFIX/"
OCI_CLI="${OCI_CLI:-oci}"
OCI_AUTH="${OCI_AUTH:-instance_principal}"

[[ -d "$DATA_DIR" ]] || { echo "missing data directory: $DATA_DIR" >&2; exit 1; }
command -v "$OCI_CLI" >/dev/null || { echo "missing OCI CLI: $OCI_CLI" >&2; exit 1; }

"$OCI_CLI" os object sync \
  --src-dir "$DATA_DIR" \
  --bucket-name "$OCI_BUCKET" \
  --namespace "$OCI_NAMESPACE" \
  --auth "$OCI_AUTH" \
  --prefix "$OCI_PREFIX"
