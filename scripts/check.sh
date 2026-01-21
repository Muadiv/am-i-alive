#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run_command() {
  local label="$1"
  shift
  echo "==> ${label}"
  "$@"
}

# Detect environment
if [[ -d "/opt/am-i-alive" ]]; then
  # Bare metal / DietPi
  PYTHON_OBSERVER="/opt/am-i-alive/venv-observer/bin/python"
  echo "Detected Bare-Metal environment"
  
  run_command "Observer voting tests" ${PYTHON_OBSERVER} -m pytest /opt/am-i-alive/observer/tests/test_voting_system.py -v
else
  # Docker / Local
  echo "Detected Docker/Local environment"
  if command -v docker >/dev/null 2>&1; then
    run_command "Observer voting tests" docker exec am-i-alive-observer python -m pytest tests/test_voting_system.py -v
  else
    echo "Warning: Neither bare-metal nor docker detected. Running local tests if possible."
    if [[ -d "observer/tests" ]]; then
       run_command "Observer voting tests" python3 -m pytest observer/tests/test_voting_system.py -v
    fi
  fi
fi

run_command "Observer health" curl -fsS http://localhost/health
run_command "Observer votes endpoint" curl -fsS http://localhost/api/votes
run_command "Observer next-vote-check" curl -fsS http://localhost/api/next-vote-check
