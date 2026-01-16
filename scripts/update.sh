#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/am-i-alive"
DATA_DIR="/var/lib/am-i-alive"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
  echo "${INSTALL_DIR} is not a git repo. Run scripts/setup.sh first." >&2
  exit 1
fi

old_rev=$(git -C "${INSTALL_DIR}" rev-parse HEAD)
git -C "${INSTALL_DIR}" pull --ff-only
new_rev=$(git -C "${INSTALL_DIR}" rev-parse HEAD)

if [[ "${old_rev}" == "${new_rev}" ]]; then
  echo "No updates to apply."
  exit 0
fi

mapfile -t changed_files < <(git -C "${INSTALL_DIR}" diff --name-only "${old_rev}..${new_rev}")

restart_observer=false
restart_ai=false
restart_proxy=false
restart_cloudflared=false

reinstall_observer=false
reinstall_ai=false
reinstall_proxy=false

for file in "${changed_files[@]}"; do
  case "${file}" in
    observer/requirements.txt)
      reinstall_observer=true
      restart_observer=true
      ;;
    ai/requirements.txt)
      reinstall_ai=true
      restart_ai=true
      ;;
    proxy/requirements.txt)
      reinstall_proxy=true
      restart_proxy=true
      ;;
    observer/*)
      restart_observer=true
      ;;
    ai/*)
      restart_ai=true
      ;;
    proxy/*)
      restart_proxy=true
      ;;
    scripts/setup.sh)
      restart_cloudflared=true
      ;;
  esac
  if [[ "${file}" == "scripts/setup.sh" || "${file}" == "scripts/update.sh" ]]; then
    echo "Script updated: ${file}"
  fi
done

if [[ "${reinstall_observer}" == "true" ]]; then
  sudo -u amialive python3 -m venv "${INSTALL_DIR}/venv-observer"
  sudo -u amialive "${INSTALL_DIR}/venv-observer/bin/pip" install -r "${INSTALL_DIR}/observer/requirements.txt"
fi

if [[ "${reinstall_ai}" == "true" ]]; then
  sudo -u amialive python3 -m venv "${INSTALL_DIR}/venv-ai"
  sudo -u amialive "${INSTALL_DIR}/venv-ai/bin/pip" install -r "${INSTALL_DIR}/ai/requirements.txt"
fi

if [[ "${reinstall_proxy}" == "true" ]]; then
  sudo -u amialive python3 -m venv "${INSTALL_DIR}/venv-proxy"
  sudo -u amialive "${INSTALL_DIR}/venv-proxy/bin/pip" install -r "${INSTALL_DIR}/proxy/requirements.txt"
fi

if [[ "${restart_observer}" == "true" ]]; then
  systemctl restart amialive-observer
fi
if [[ "${restart_ai}" == "true" ]]; then
  systemctl restart amialive-ai
fi
if [[ "${restart_proxy}" == "true" ]]; then
  systemctl restart amialive-proxy
fi
if [[ "${restart_cloudflared}" == "true" ]]; then
  systemctl restart cloudflared
fi

if [[ "${restart_observer}" == "false" && "${restart_ai}" == "false" && "${restart_proxy}" == "false" && "${restart_cloudflared}" == "false" ]]; then
  echo "No service restarts needed."
fi

systemctl status amialive-observer amialive-ai amialive-proxy cloudflared --no-pager

if [[ ! -d "${DATA_DIR}" ]]; then
  echo "Warning: ${DATA_DIR} missing. Run scripts/setup.sh to recreate." >&2
fi
