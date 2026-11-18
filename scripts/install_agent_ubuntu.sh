#!/usr/bin/env bash
# ==============================================================================
# SentinelOps Linux Monitoring Agent - Ubuntu Installer
# Installs the agent under /opt/sentinelops-agent as a least-privilege user.
# Usage:
#   sudo bash scripts/install_agent_ubuntu.sh \
#     --api-url https://monitor.example.com \
#     --server-id <SERVER_UUID> \
#     --api-token <sops_...>
# ==============================================================================
set -euo pipefail

API_URL=""
SERVER_ID=""
API_TOKEN=""
INTERVAL="5"
INSTALL_DIR="/opt/sentinelops-agent"
CONFIG_DIR="/etc/sentinelops"
SERVICE_USER="sentinelops"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-url) API_URL="$2"; shift 2 ;;
    --server-id) SERVER_ID="$2"; shift 2 ;;
    --api-token) API_TOKEN="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "Please run this installer with sudo/root privileges." >&2
  exit 1
fi

if [[ -z "$API_URL" || -z "$API_TOKEN" ]]; then
  echo "Usage: sudo $0 --api-url <URL> --server-id <UUID> --api-token <sops_TOKEN> [--interval 5]" >&2
  exit 1
fi

echo "[1/6] Installing Python runtime prerequisites..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip

echo "[2/6] Creating dedicated least-privilege user '${SERVICE_USER}'..."
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi
# Grant read-only log access via standard Ubuntu groups
usermod -aG adm,systemd-journal "$SERVICE_USER" || true

echo "[3/6] Copying monitoring agent to ${INSTALL_DIR}..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"
cp -r "$REPO_ROOT/monitoring-agent/"* "$INSTALL_DIR/"

echo "[4/6] Creating isolated Python virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"

echo "[5/6] Writing secured environment configuration (${CONFIG_DIR}/agent.env)..."
cat > "${CONFIG_DIR}/agent.env" <<EOF
SENTINELOPS_API_URL=${API_URL}
SENTINELOPS_SERVER_ID=${SERVER_ID}
SENTINELOPS_API_TOKEN=${API_TOKEN}
SENTINELOPS_INTERVAL_SECONDS=${INTERVAL}
SENTINELOPS_LOG_SOURCES=/var/log/syslog,/var/log/auth.log
SENTINELOPS_ENABLE_JOURNALCTL=true
SENTINELOPS_MAX_PROCESSES=30
EOF

chown -R "${SERVICE_USER}:${SERVICE_USER}" "$INSTALL_DIR" "$CONFIG_DIR"
chmod 0600 "${CONFIG_DIR}/agent.env"

echo "[6/6] Enabling and starting systemd service..."
cp "$INSTALL_DIR/config/sentinelops-agent.service" /etc/systemd/system/sentinelops-agent.service
systemctl daemon-reload
systemctl enable --now sentinelops-agent.service
systemctl status sentinelops-agent.service --no-pager

echo "SentinelOps Monitoring Agent installed and running!"

