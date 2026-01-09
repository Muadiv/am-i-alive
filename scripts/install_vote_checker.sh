#!/bin/bash
# Install Am I Alive Vote Checker systemd timer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🗳️  Installing Am I Alive Vote Checker..."

# Copy systemd files
echo "📋 Copying systemd service and timer files..."
sudo cp "$SCRIPT_DIR/am-i-alive-vote-checker.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/am-i-alive-vote-checker.timer" /etc/systemd/system/

# Reload systemd
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable timer
echo "⏱️  Enabling vote checker timer..."
sudo systemctl enable am-i-alive-vote-checker.timer

# Start timer
echo "▶️  Starting vote checker timer..."
sudo systemctl start am-i-alive-vote-checker.timer

# Show status
echo ""
echo "✅ Vote checker installed successfully!"
echo ""
echo "Timer status:"
sudo systemctl status am-i-alive-vote-checker.timer --no-pager
echo ""
echo "📅 Next run time:"
systemctl list-timers am-i-alive-vote-checker.timer --no-pager
echo ""
echo "💡 Useful commands:"
echo "  - Check timer status: sudo systemctl status am-i-alive-vote-checker.timer"
echo "  - View logs: sudo journalctl -u am-i-alive-vote-checker.service -f"
echo "  - Run manually: sudo systemctl start am-i-alive-vote-checker.service"
echo "  - Stop timer: sudo systemctl stop am-i-alive-vote-checker.timer"
