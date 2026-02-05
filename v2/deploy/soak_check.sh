#!/usr/bin/env bash
set -euo pipefail

V1_URL="${V1_URL:-http://127.0.0.1}"
V2_URL="${V2_URL:-http://127.0.0.1:8080}"

echo "[SOAK] Checking v1 health: $V1_URL/health"
curl -sS "$V1_URL/health"
echo

echo "[SOAK] Checking v2 health: $V2_URL/health"
curl -sS "$V2_URL/health"
echo

echo "[SOAK] Checking v1 state: $V1_URL/api/public/state"
curl -sS "$V1_URL/api/public/state"
echo

echo "[SOAK] Checking v2 state: $V2_URL/api/public/state"
curl -sS "$V2_URL/api/public/state"
echo

echo "[SOAK] Checking v2 vote round: $V2_URL/api/public/vote-round"
curl -sS "$V2_URL/api/public/vote-round"
echo

echo "[SOAK] Checking v2 funding: $V2_URL/api/public/funding"
curl -sS "$V2_URL/api/public/funding"
echo
