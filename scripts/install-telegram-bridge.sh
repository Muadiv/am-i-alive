#!/bin/bash
# Install Telegram Claude Bridge as systemd service

set -e

echo "🤖 Installing Telegram Claude Bridge..."

# Check if .env exists
if [ ! -f "/home/muadiv/Code/am-i-alive/.env" ]; then
    echo "❌ Error: .env file not found"
    echo "   Create /home/muadiv/Code/am-i-alive/.env with TELEGRAM_BOT_TOKEN"
    exit 1
fi

# Check if TELEGRAM_BOT_TOKEN is in .env
if ! grep -q "TELEGRAM_BOT_TOKEN" /home/muadiv/Code/am-i-alive/.env; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN not found in .env"
    exit 1
fi

# Check if TELEGRAM_AUTHORIZED_USER_ID is in .env
if ! grep -q "TELEGRAM_AUTHORIZED_USER_ID" /home/muadiv/Code/am-i-alive/.env; then
    echo "❌ Error: TELEGRAM_AUTHORIZED_USER_ID not found in .env"
    exit 1
fi

# Make script executable
chmod +x /home/muadiv/Code/am-i-alive/scripts/telegram_claude_bridge.py
echo "✅ Made bridge script executable"

# Copy service file to systemd
sudo cp /home/muadiv/Code/am-i-alive/scripts/telegram-claude-bridge.service /etc/systemd/system/
echo "✅ Copied service file to /etc/systemd/system/"

# Reload systemd
sudo systemctl daemon-reload
echo "✅ Reloaded systemd daemon"

# Enable service (auto-start on boot)
sudo systemctl enable telegram-claude-bridge
echo "✅ Enabled service for auto-start"

# Start service
sudo systemctl start telegram-claude-bridge
echo "✅ Started service"

# Wait a moment for startup
sleep 2

# Check status
echo ""
echo "📊 Service Status:"
sudo systemctl status telegram-claude-bridge --no-pager -l

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Useful commands:"
echo "   sudo systemctl status telegram-claude-bridge     # Check status"
echo "   sudo systemctl restart telegram-claude-bridge    # Restart service"
echo "   sudo systemctl stop telegram-claude-bridge       # Stop service"
echo "   sudo journalctl -u telegram-claude-bridge -f     # View logs"
echo "   tail -f /tmp/telegram_claude_bridge.log          # View application logs"
echo ""
echo "🔐 Only the TELEGRAM_AUTHORIZED_USER_ID can send commands."
echo "📱 Send a message to your Telegram bot to test!"
