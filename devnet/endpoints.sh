#!/usr/bin/env bash
# Extract each EL's JSON-RPC + Engine API endpoints from a running Kurtosis
# enclave into devnet/endpoints.json, which the Batman harness reads.
#
# Usage:  ./devnet/endpoints.sh [enclave-name]   (default: batman-gloas)
#
# Best-effort: it parses `kurtosis enclave inspect`. If service/port names differ
# in your package version, run `kurtosis enclave inspect <enclave>` by hand and
# fill devnet/endpoints.json yourself — the schema is just a list of
# {client_id, rpc, engine}.
set -euo pipefail

ENCLAVE="${1:-batman-gloas}"
OUT="$(dirname "$0")/endpoints.json"

if ! command -v kurtosis >/dev/null 2>&1; then
  echo "kurtosis CLI not found — install it first (see devnet/README.md)." >&2
  exit 1
fi

# EL services are named like: el-1-geth-lighthouse, el-2-reth-teku, ...
services=$(kurtosis enclave inspect "$ENCLAVE" 2>/dev/null \
  | grep -oE 'el-[0-9]+-[a-z0-9-]+' | sort -u || true)

if [ -z "$services" ]; then
  echo "No EL services found in enclave '$ENCLAVE'. Is it running?" >&2
  echo "Try: kurtosis enclave inspect $ENCLAVE" >&2
  exit 1
fi

{
  echo "["
  first=1
  for svc in $services; do
    rpc=$(kurtosis port print "$ENCLAVE" "$svc" rpc 2>/dev/null || true)
    engine=$(kurtosis port print "$ENCLAVE" "$svc" engine-rpc 2>/dev/null || true)
    [ -z "$rpc" ] && continue
    [ $first -eq 0 ] && echo ","
    first=0
    printf '  {"client_id": "%s", "rpc": "%s", "engine": "%s"}' "$svc" "$rpc" "$engine"
  done
  echo ""
  echo "]"
} > "$OUT"

echo "Wrote $OUT:"
cat "$OUT"
