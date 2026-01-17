# Operations Runbook

## Cloudflare Tunnel Recovery (am-i-alive)

Use when the site returns Cloudflare 404 or external access fails.

1. Login to Cloudflare tunnel (interactive):

```bash
sudo cloudflared tunnel login
```

2. Attach the hostname to the tunnel (overwrite existing DNS if needed):

```bash
sudo cloudflared tunnel route dns --overwrite-dns am-i-alive-tunnel am-i-alive.muadiv.com.ar
```

3. Restart cloudflared:

```bash
sudo systemctl restart cloudflared
```

4. Verify:

```bash
curl -I https://am-i-alive.muadiv.com.ar
```

Note: `curl -I` uses HEAD and returns 405; verify via browser or `curl https://...`.

---

## DNS Stability (DietPi)

### Current Config
- `/etc/network/interfaces` includes static resolvers for both `eth0` and `wlan0`.
- `/etc/resolv.conf` points directly at upstream resolvers:
  - `1.1.1.1`, `1.0.0.1`, `8.8.8.8`, `8.8.4.4`

### If DNS fails again
1. Reapply resolvers:

```bash
sudo tee /etc/resolv.conf <<'EOF'
options timeout:2 attempts:3
nameserver 1.1.1.1
nameserver 1.0.0.1
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
```

2. Restart networking:

```bash
sudo systemctl restart networking
```

3. Test resolution:

```bash
python3 - <<'PY'
import socket
print(socket.gethostbyname_ex('openrouter.ai'))
PY
```

---

## Service Restart Policies

All core services are configured with `Restart=always`:

```bash
systemctl show amialive-observer -p Restart -p RestartSec
systemctl show amialive-ai -p Restart -p RestartSec
systemctl show amialive-proxy -p Restart -p RestartSec
systemctl show cloudflared -p Restart -p RestartSec
```

---

## Life Continuity on Reboot

The AI now resumes the same life if `/app/workspace/identity.json` matches the Observer life number.
A new life starts only after Observer death/respawn or bankruptcy/vote death triggers.

