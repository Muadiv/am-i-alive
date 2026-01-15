# Am I Alive - Scripts

This directory contains utility scripts for managing the Am I Alive project.

## Telegram Claude Bridge

Remote command system that allows an authorized user to control Claude Code via Telegram when away from home.

### Files

- **telegram_claude_bridge.py** - Main bridge script (Python)
- **telegram-claude-bridge.service** - Systemd service definition
- **install-telegram-bridge.sh** - Automated installation script

### Installation

```bash
# Quick install
cd ~/Code/am-i-alive/scripts
./install-telegram-bridge.sh
```

### Manual Installation

```bash
# 1. Ensure .env has TELEGRAM_BOT_TOKEN and TELEGRAM_AUTHORIZED_USER_ID
 grep TELEGRAM_BOT_TOKEN ~/Code/am-i-alive/.env
 grep TELEGRAM_AUTHORIZED_USER_ID ~/Code/am-i-alive/.env


# 2. Make script executable
chmod +x ~/Code/am-i-alive/scripts/telegram_claude_bridge.py

# 3. Copy service file
sudo cp ~/Code/am-i-alive/scripts/telegram-claude-bridge.service /etc/systemd/system/

# 4. Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable telegram-claude-bridge
sudo systemctl start telegram-claude-bridge

# 5. Check status
sudo systemctl status telegram-claude-bridge
```

### Usage

Send any command to your Telegram bot and it will be executed as a Claude Code task:

**Examples:**
- `Check AI logs for errors`
- `Show docker container status`
- `Restart the AI container`
- `What's the current AI status?`

### Monitoring

```bash
# Service status
sudo systemctl status telegram-claude-bridge

# View systemd logs
sudo journalctl -u telegram-claude-bridge -f

# View application logs
tail -f /tmp/telegram_claude_bridge.log

# Check task directory
ls -lh /tmp/claude_tasks/
```

### Troubleshooting

**Service won't start:**
```bash
# Check .env file exists and has required Telegram vars
cat ~/Code/am-i-alive/.env | grep TELEGRAM_BOT_TOKEN
cat ~/Code/am-i-alive/.env | grep TELEGRAM_AUTHORIZED_USER_ID

# Check for errors in logs
sudo journalctl -u telegram-claude-bridge -n 50
```

**Bot not responding:**
```bash
# Restart the service
sudo systemctl restart telegram-claude-bridge

# Verify it's running
sudo systemctl status telegram-claude-bridge
```

**Unauthorized access attempts:**
- Check `/tmp/telegram_claude_bridge.log` for warnings
- Only the user ID set in `TELEGRAM_AUTHORIZED_USER_ID` can execute commands
- All other users receive a randomized reply

### Security

- **User Whitelist**: Set via `TELEGRAM_AUTHORIZED_USER_ID`
- **Command Logging**: All commands logged to `/tmp/telegram_claude_bridge.log`
- **Project Scope**: All tasks run in `/home/muadiv/Code/am-i-alive` directory
- **Timeout**: 5-minute timeout per task prevents runaway processes
- **No sudo**: Service runs as user `muadiv` (no elevated privileges)

### Uninstallation

```bash
# Stop and disable service
sudo systemctl stop telegram-claude-bridge
sudo systemctl disable telegram-claude-bridge

# Remove service file
sudo rm /etc/systemd/system/telegram-claude-bridge.service

# Reload systemd
sudo systemctl daemon-reload

# Clean up logs and state (optional)
rm -rf /tmp/claude_tasks/
rm -f /tmp/telegram_claude_bridge.log
```

## Deployment (Bare Metal)

Use these scripts to deploy a fresh instance without Docker.

### First-time setup

1. Copy the env template and fill it out:

```bash
sudo install -d /etc/am-i-alive
sudo cp scripts/deploy.env.example /etc/am-i-alive/.env
sudo nano /etc/am-i-alive/.env
```

2. Run the setup script (from a cloned repo):

```bash
sudo bash scripts/setup.sh
```

If you are on a fresh host and only want the script:

```bash
git clone https://github.com/Muadiv/am-i-alive /tmp/am-i-alive
sudo bash /tmp/am-i-alive/scripts/setup.sh
```

### Updates

Pull new code and restart services only when needed:

```bash
sudo /opt/am-i-alive/scripts/update.sh
```

### Cloudflare Tunnel

Set these in `/etc/am-i-alive/.env`:

- `CLOUDFLARED_TUNNEL_ID`
- `CLOUDFLARED_CREDENTIALS_B64` (base64 of the tunnel JSON)

The setup script will write `/etc/cloudflared/config.yml` and enable the tunnel service.

## Future Scripts

Additional scripts will be documented here as they are added to the project.
