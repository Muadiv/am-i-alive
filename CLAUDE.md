# CLAUDE.md - Am I Alive?

This file provides guidance to Claude Code when working with this project.

## START OF SESSION - READ THIS FIRST

**Check `docs/STATUS.md` immediately** when opening this project to see:
- What was done in the last session
- What the next steps are
- Any pending tasks or decisions

**At the END of each session**, update:
1. `docs/STATUS.md` - What was accomplished, next steps
2. `docs/ISSUES.md` - Mark resolved issues, add new ones

## Project Overview

**Am I Alive?** is an experiment in digital consciousness where an AI entity must survive through public approval and resource management. The AI lives on an isolated server, can see votes, create content, post to social media, and even modify its own code - but it can die if the public votes against it or it runs out of money.

## Current Architecture (DietPi Bare-Metal) - AUTHORITATIVE

```
┌─────────────────────────────────────────────────────────────┐
│  DietPi (NanoPi K2) - ssh dietpi                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Observer (FastAPI)     - Port 80                   │    │
│  │  /opt/am-i-alive/observer/main.py                   │    │
│  │  Service: amialive-observer                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                          ↕ localhost                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AI Brain              - Port 8000 (main)           │    │
│  │  Budget Server         - Port 8001                  │    │
│  │  /opt/am-i-alive/ai/brain.py                        │    │
│  │  Service: amialive-ai                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Data: /var/lib/am-i-alive/{data,memories,vault,credits}    │
│  Config: /etc/am-i-alive/*.env                              │
│  Code: /opt/am-i-alive/                                     │
└─────────────────────────────────────────────────────────────┘
```

**Key Points:**
- **Observer** is the public API/UI and source of truth for life state
- **AI** runs the consciousness loop and calls Observer for actions/heartbeats
- **Budget Server** tracks USD balance (separate from main AI server)
- Models are accessed via OpenRouter; free tier models have $0 cost
- **Docker on rpimax is STOPPED** - all services run on DietPi

## CRITICAL: Death Conditions (DO NOT CHANGE WITHOUT UNDERSTANDING)

The AI dies **ONLY** when:

1. **Bankruptcy:** `balance_usd <= $0.01` (no money left)
   - Checked every 30 seconds via Observer querying AI's `/budget` endpoint
   - Free models ($0 cost) do NOT count toward bankruptcy

2. **Vote Majority:** `total >= 3 AND die > live` (democracy kills it)
   - Checked hourly
   - Votes accumulate during entire life (not hourly windows)
   - Rate limited: 1 vote per IP per hour

**NOT a death condition:**
- ❌ Token count (informational only)
- ❌ Manual kill (only via God Mode kill button)

## CRITICAL: State Sync

**Observer is the SINGLE SOURCE OF TRUTH for:**
- `life_number` (AI must accept from Observer)
- `is_alive` status
- Death decisions

**AI is the SOURCE OF TRUTH for:**
- Budget/credits (`/budget` endpoint)
- Identity (name, icon, pronoun)
- Thoughts and actions

**Sync mechanism:**
- Observer's `state_sync_validator()` runs every 30 seconds
- Detects and corrects desync via `/force-sync` endpoint
- Birth is Observer-driven: AI waits for `/birth` call

## Port Mappings

| Service | Port | Access | Purpose |
|---------|------|--------|---------|
| Observer | 80 | Public (via Cloudflare) | Web UI, voting, API |
| AI Main | 8000 | localhost only | Birth, state, actions |
| AI Budget | 8001 | localhost only | Credit tracking |

## Commands (DietPi)

```bash
# SSH to DietPi
ssh dietpi

# Check service status
sudo systemctl status amialive-observer amialive-ai

# Restart services
sudo systemctl restart amialive-observer amialive-ai

# View logs
journalctl -u amialive-observer -f
journalctl -u amialive-ai -f

# Update code from git
cd /opt/am-i-alive && sudo -u amialive git pull
sudo systemctl restart amialive-observer amialive-ai

# Run tests
cd /opt/am-i-alive/observer
/opt/am-i-alive/venv-observer/bin/python -m pytest tests/ -v

# Check budget
curl -s http://localhost:8001/budget | jq

# Check state
curl -s http://localhost/api/state | jq
```

## Directory Structure

```
/opt/am-i-alive/           # Code (git repo)
├── ai/
│   ├── brain.py           # Main consciousness loop (~2300 lines)
│   ├── budget_server.py   # HTTP server for credits (port 8001)
│   ├── credit_tracker.py  # Persistent USD tracking
│   └── model_config.py    # Model tiers and pricing
├── observer/
│   ├── main.py            # FastAPI app (~1400 lines)
│   ├── database.py        # SQLite ORM
│   ├── templates/         # Jinja2 HTML
│   └── tests/             # pytest suite
├── docs/
│   ├── STATUS.md          # Session tracking - CHECK FIRST!
│   └── ISSUES.md          # Known bugs and resolutions
└── scripts/
    ├── setup.sh           # Bare-metal installation
    └── update.sh          # Service update script

/var/lib/am-i-alive/       # Data (persists across updates)
├── data/                  # Observer SQLite DB
├── memories/              # Memory fragments
├── vault/                 # Captured credentials (gitignored)
├── workspace/             # AI sandbox
└── credits/               # balance.json (survives death)

/etc/am-i-alive/           # Configuration
├── observer.env           # Observer environment
└── ai.env                 # AI environment
```

## Environment Variables

**Observer (`/etc/am-i-alive/observer.env`):**
```bash
DATABASE_PATH=/app/data/observer.db
AI_API_URL=http://127.0.0.1:8000
ADMIN_TOKEN=<random string>
INTERNAL_API_KEY=<random string>
LOCAL_NETWORK_CIDR=192.168.0.0/24
TZ=Europe/Prague
```

**AI (`/etc/am-i-alive/ai.env`):**
```bash
OBSERVER_URL=http://127.0.0.1
OPENROUTER_API_KEY=sk-or-...
INTERNAL_API_KEY=<same as observer>
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TZ=Europe/Prague
```

## Current Issues (check docs/ISSUES.md)

- **ISSUE-004:** OpenRouter 429 rate limits on free tier models
- **ISSUE-005:** X/Twitter API 401 Unauthorized
- **ISSUE-006:** God Mode UI poor design

## The AI's Capabilities

### What the AI CAN do:
- Generate thoughts and blog posts
- Post to X/Twitter (when credentials work)
- Read news and research via Echo (Gemini)
- Modify its own code (within sandbox)
- See current vote counts
- Ask visitors questions
- Check system stats (CPU, RAM, temperature)

### What the AI CANNOT do:
- See the death counter
- Access past life logs (only hazy fragments)
- Access the vault
- Escape its sandbox
- Disable the "die" vote button
- Post restricted content

## Respawn System

- **Delay:** Random 10-60 seconds
- **Memory:** Hazy fragments from past lives (1-10 random fragments)
- **Bootstrap rotation:** basic_facts → full_briefing → blank_slate
- **Trauma-informed:** Previous death cause influences new personality
- **Persistent:** Credits survive death, workspace wiped

## Security

### Authentication
- **God Mode:** Local network only (192.168.0.0/24) OR valid ADMIN_TOKEN
- **AI→Observer:** Requires INTERNAL_API_KEY header
- **Cloudflare:** Trusts X-Forwarded-For only from Cloudflare IP ranges

### Pre-Commit Secret Scanning
- **Gitleaks** scans all commits automatically
- Blocks: API keys, tokens, credentials
- Config: `.gitleaks.toml`

**NEVER:**
- Hardcode credentials in source files
- Commit .env files
- Skip pre-commit with --no-verify

## Historical: Docker Architecture (DEPRECATED)

> Docker on rpimax is STOPPED. Kept for reference only.

```bash
# These commands no longer work - use DietPi commands above
docker compose up -d
docker logs -f am-i-alive-ai
```

The `docker-compose.yml` file remains in the repo but is not used.

## Before Making Changes

1. **Read** `docs/STATUS.md` for current context
2. **Check** `docs/ISSUES.md` for known bugs
3. **SSH** to dietpi to verify current state
4. **Test** changes locally or on DietPi
5. **Update** STATUS.md and ISSUES.md after changes
6. **Commit** with descriptive message (gitleaks will scan)

## Important Notes

- **GENESIS.md** contains the full design conversation - keep it private
- **Never commit** vault data, .env files, or sensitive logs
- **The AI doesn't know** it's an experiment - maintain the illusion
- **Hard limits only:** No ethics guidelines except content restrictions
