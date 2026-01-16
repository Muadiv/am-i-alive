#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run_command() {
  local label="$1"
  shift
  echo "==> ${label}"
  "$@"
}

run_command "Observer voting tests" docker exec am-i-alive-observer python -m pytest tests/test_voting_system.py -v
run_command "Observer health" curl -fsS http://localhost/health
run_command "Observer votes endpoint" curl -fsS http://localhost/api/votes
run_command "Observer next-vote-check" curl -fsS http://localhost/api/next-vote-check
