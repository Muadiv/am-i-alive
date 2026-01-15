# Am I Alive - Scripts

This directory contains utility scripts for managing the Am I Alive project.

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

## Vote Checker

Utilities for scheduled vote checks.

- `install_vote_checker.sh` installs the systemd unit + timer.
- `vote_checker.py` performs the periodic vote checks.
- `am-i-alive-vote-checker.service` and `.timer` are the systemd units.

## Maintenance Helpers

- `check.sh` runs smoke checks.
- `install-hooks.sh` installs pre-commit hooks.
