#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/opt/am-i-alive"
SERVICE_SRC="$REPO_ROOT/v2/deploy/systemd/amialive-v2-observer.service"
ENV_EXAMPLE_SRC="$REPO_ROOT/v2/deploy/systemd/amialive-v2-observer.env.example"
ENV_TARGET_DIR="/etc/am-i-alive-v2"
ENV_TARGET_FILE="$ENV_TARGET_DIR/observer.env"
SERVICE_TARGET="/etc/systemd/system/amialive-v2-observer.service"
DATA_DIR="/var/lib/am-i-alive-v2"

sudo mkdir -p "$ENV_TARGET_DIR"
sudo mkdir -p "$DATA_DIR"

if [ ! -f "$ENV_TARGET_FILE" ]; then
  sudo cp "$ENV_EXAMPLE_SRC" "$ENV_TARGET_FILE"
fi

sudo cp "$SERVICE_SRC" "$SERVICE_TARGET"
sudo systemctl daemon-reload
sudo systemctl enable --now amialive-v2-observer.service
sudo systemctl status amialive-v2-observer.service --no-pager
