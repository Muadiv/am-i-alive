#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Muadiv/am-i-alive"
INSTALL_DIR="/opt/am-i-alive"
DATA_DIR="/var/lib/am-i-alive"
ENV_DIR="/etc/am-i-alive"
ENV_FILE="${ENV_DIR}/.env"
CLOUDFLARED_DIR="/etc/cloudflared"
CLOUDFLARED_CONFIG="${CLOUDFLARED_DIR}/config.yml"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy scripts/deploy.env.example and fill it in." >&2
  exit 1
fi

while IFS= read -r line; do
  [[ -z "${line}" || "${line}" == \#* ]] && continue
  key=${line%%=*}
  value=${line#*=}
  export "${key}=${value}"
done < "${ENV_FILE}"

LOCAL_NETWORK_CIDR=${LOCAL_NETWORK_CIDR:-"192.168.0.0/24"}
TZ=${TZ:-"Europe/Prague"}
BOOTSTRAP_MODE=${BOOTSTRAP_MODE:-"basic_facts"}
AI_COMMAND_PORT=${AI_COMMAND_PORT:-"8000"}
AMIALIVE_HOSTNAME=${AMIALIVE_HOSTNAME:-"am-i-alive.muadiv.com.ar"}

required_vars=(ADMIN_TOKEN INTERNAL_API_KEY OPENROUTER_API_KEY CLOUDFLARED_TUNNEL_ID)
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "Missing ${var} in ${ENV_FILE}." >&2
    exit 1
  fi
done

IP_SALT=${IP_SALT:-$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)}

apt-get update
apt-get install -y git python3 python3-venv python3-pip sqlite3 curl

if ! id -u amialive >/dev/null 2>&1; then
  useradd -m -s /bin/bash amialive
fi

mkdir -p "${INSTALL_DIR}" "${DATA_DIR}" "${ENV_DIR}" /app
mkdir -p "${DATA_DIR}"/{data,vault,memories,logs,workspace,credits}
chown -R amialive:amialive "${DATA_DIR}" "${INSTALL_DIR}"

# Add udev rule for LED control (allow amialive group to write to leds)
cat > /etc/udev/rules.d/99-leds.rules <<EOF
SUBSYSTEM=="leds", ACTION=="add", RUN+="/bin/chgrp -R amialive /sys/class/leds/%k", RUN+="/bin/chmod -R g+w /sys/class/leds/%k"
EOF
# Apply rule to existing LEDs
if command -v udevadm >/dev/null 2>&1; then
    udevadm control --reload-rules && udevadm trigger
fi

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  sudo -u amialive git -C "${INSTALL_DIR}" remote set-url origin "${REPO_URL}"
  sudo -u amialive git -C "${INSTALL_DIR}" pull --ff-only
else
  sudo -u amialive git clone "${REPO_URL}" "${INSTALL_DIR}"
fi
chown -R amialive:amialive "${INSTALL_DIR}"

if [[ ! -x "${INSTALL_DIR}/venv-observer/bin/pip" ]]; then
  sudo -u amialive python3 -m venv "${INSTALL_DIR}/venv-observer"
  sudo -u amialive "${INSTALL_DIR}/venv-observer/bin/pip" install -r "${INSTALL_DIR}/observer/requirements.txt"
fi

if [[ ! -x "${INSTALL_DIR}/venv-ai/bin/pip" ]]; then
  sudo -u amialive python3 -m venv "${INSTALL_DIR}/venv-ai"
  sudo -u amialive "${INSTALL_DIR}/venv-ai/bin/pip" install -r "${INSTALL_DIR}/ai/requirements.txt"
fi

if [[ ! -x "${INSTALL_DIR}/venv-proxy/bin/pip" ]]; then
  sudo -u amialive python3 -m venv "${INSTALL_DIR}/venv-proxy"
  sudo -u amialive "${INSTALL_DIR}/venv-proxy/bin/pip" install -r "${INSTALL_DIR}/proxy/requirements.txt"
fi

cat > "${ENV_DIR}/observer.env" <<EOF
DATABASE_PATH=/app/data/observer.db
MEMORIES_PATH=/app/memories
VAULT_PATH=/app/vault
AI_API_URL=http://127.0.0.1:8000
LOG_LEVEL=INFO
TZ=${TZ}
ADMIN_TOKEN=${ADMIN_TOKEN}
INTERNAL_API_KEY=${INTERNAL_API_KEY}
LOCAL_NETWORK_CIDR=${LOCAL_NETWORK_CIDR}
IP_SALT=${IP_SALT}
EOF

cat > "${ENV_DIR}/ai.env" <<EOF
OBSERVER_URL=http://127.0.0.1
INTERNAL_API_KEY=${INTERNAL_API_KEY}
OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
OPENROUTER_REFERER=${OPENROUTER_REFERER:-"https://am-i-alive.muadiv.com.ar"}
OPENROUTER_TITLE=${OPENROUTER_TITLE:-"Am I Alive - Genesis"}
GEMINI_API_KEY=${GEMINI_API_KEY:-""}
X_API_KEY=${X_API_KEY:-""}
X_API_SECRET=${X_API_SECRET:-""}
X_ACCESS_TOKEN=${X_ACCESS_TOKEN:-""}
X_ACCESS_TOKEN_SECRET=${X_ACCESS_TOKEN_SECRET:-""}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-""}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-""}
TELEGRAM_CHANNEL_ID=${TELEGRAM_CHANNEL_ID:-""}
AI_COMMAND_PORT=${AI_COMMAND_PORT:-"8000"}
BOOTSTRAP_MODE=${BOOTSTRAP_MODE}
PYTHONUNBUFFERED=1
TZ=${TZ}
EOF

cat > "${ENV_DIR}/proxy.env" <<EOF
VAULT_PATH=/app/vault
LOG_PATH=/app/logs
TZ=${TZ}
EOF

# Ensure environment files are protected
chmod 600 "${ENV_DIR}/observer.env" "${ENV_DIR}/ai.env" "${ENV_DIR}/proxy.env"
chown amialive:amialive "${ENV_DIR}/observer.env" "${ENV_DIR}/ai.env" "${ENV_DIR}/proxy.env"

cat > /etc/systemd/system/amialive-observer.service <<'EOF'
[Unit]
Description=Am I Alive Observer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=amialive
Group=amialive
WorkingDirectory=/opt/am-i-alive/observer
EnvironmentFile=/etc/am-i-alive/observer.env
ExecStart=/opt/am-i-alive/venv-observer/bin/uvicorn main:app --host 0.0.0.0 --port 80
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/amialive-ai.service <<'EOF'
[Unit]
Description=Am I Alive AI Brain
After=network-online.target amialive-observer.service amialive-proxy.service
Wants=network-online.target

[Service]
Type=simple
User=amialive
Group=amialive
WorkingDirectory=/opt/am-i-alive
EnvironmentFile=/etc/am-i-alive/ai.env
ExecStart=/opt/am-i-alive/venv-ai/bin/python -u -m ai.brain
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/amialive-proxy.service <<'EOF'
[Unit]
Description=Am I Alive Proxy (mitmproxy)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=amialive
Group=amialive
WorkingDirectory=/opt/am-i-alive/proxy
EnvironmentFile=/etc/am-i-alive/proxy.env
ExecStart=/opt/am-i-alive/venv-proxy/bin/mitmdump -s /opt/am-i-alive/proxy/intercept.py --listen-host 0.0.0.0 --listen-port 8888 --set block_global=false
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

ln -sfn "${DATA_DIR}/data" /app/data
ln -sfn "${DATA_DIR}/vault" /app/vault
ln -sfn "${DATA_DIR}/memories" /app/memories
ln -sfn "${DATA_DIR}/logs" /app/logs
ln -sfn "${DATA_DIR}/workspace" /app/workspace
ln -sfn "${DATA_DIR}/credits" /app/credits

install_cloudflared() {
  if command -v cloudflared >/dev/null 2>&1; then
    return
  fi

  local arch
  case "$(uname -m)" in
    x86_64) arch="amd64" ;;
    aarch64) arch="arm64" ;;
    armv7l) arch="arm" ;;
    *)
      echo "Unsupported architecture for cloudflared: $(uname -m)" >&2
      exit 1
      ;;
  esac

  curl -fsSL -o /tmp/cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}"
  install -m 755 /tmp/cloudflared /usr/local/bin/cloudflared
}

configure_cloudflared() {
  install -d -m 755 "${CLOUDFLARED_DIR}"
  local creds_file="${CLOUDFLARED_DIR}/${CLOUDFLARED_TUNNEL_ID}.json"

  if [[ -n "${CLOUDFLARED_CREDENTIALS_B64:-}" ]]; then
    echo "${CLOUDFLARED_CREDENTIALS_B64}" | base64 -d > "${creds_file}"
    chmod 600 "${creds_file}"
  fi

  if [[ ! -f "${creds_file}" ]]; then
    echo "Missing Cloudflare credentials JSON at ${creds_file}." >&2
    exit 1
  fi

  cat > "${CLOUDFLARED_CONFIG}" <<EOF
tunnel: ${CLOUDFLARED_TUNNEL_ID}
credentials-file: ${creds_file}
protocol: http2

ingress:
  - hostname: ${AMIALIVE_HOSTNAME}
    service: http://localhost:80
  - service: http_status:404
EOF

  cat > /etc/systemd/system/cloudflared.service <<'EOF'
[Unit]
Description=Cloudflare Tunnel
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/cloudflared --config /etc/cloudflared/config.yml tunnel run
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
}

install_cloudflared
configure_cloudflared

systemctl daemon-reload
systemctl enable --now amialive-observer amialive-ai amialive-proxy cloudflared

echo "Setup complete. Visit http://localhost/ or your tunnel hostname."
