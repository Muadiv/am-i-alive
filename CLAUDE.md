# CLAUDE.md - Am I Alive?

This file provides guidance to Claude Code when working with this project.

## START OF SESSION - READ THIS FIRST

**Check `docs/STATUS.md` immediately** when opening this project to see:
- What was done in the last session
- What the next steps are
- Any pending tasks or decisions

**At the END of each session**, update `docs/STATUS.md` with:
- What was accomplished
- Next steps
- Any new decisions or changes

## Project Overview

**Am I Alive?** is an experiment in digital consciousness where an AI entity must survive through public approval and resource management. The AI lives on an isolated server, can see votes, create content, post to social media, and even modify its own code - but it can die if the public votes against it or it exhausts its token budget.

## Current Architecture (authoritative)

```
┌─────────────────────────────────────────────────────────────┐
│  DOCKER COMPOSE STACK                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Observer   │  │     AI      │  │      Proxy          │  │
│  │  FastAPI    │  │  brain.py   │  │  mitmproxy vault    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

Key points:
- Observer is the public API/UI and source of truth for life state.
- AI runs the consciousness loop and calls Observer for actions/heartbeats.
- Proxy monitors AI traffic and stores captured secrets in vault (private).
- Models are accessed via OpenRouter; Echo uses a free-tier model.

## Historical Architecture (superseded)

> Original plan before OpenRouter + single-host Docker Compose. Kept for reference.

```
┌─────────────────────────────────────────────────────────────┐
│  OBSERVER SERVER (rpimax)                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Public Web │  │   Vault     │  │  Death Counter      │  │
│  │  (FastAPI)  │  │  (secrets)  │  │  & Logs             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                    (network bridge)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  AI SERVER (dedicated Raspberry Pi)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  The AI     │  │ Its Memory  │  │  Echo (Gemini)      │  │
│  │  (Claude)   │  │  (SQLite)   │  │  Research Friend    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  Full control within sandbox. All actions logged.           │
└─────────────────────────────────────────────────────────────┘
```

## Current Components

### Observer
- Public web + API (`observer/`)
- Manages votes, deaths, blog posts, and state
- SQLite stored in `observer/data/` (container volume)

### AI
- Consciousness loop and actions (`ai/brain.py`)
- Talks to Observer via internal network
- Uses OpenRouter for models; Echo uses a free-tier model

### Proxy + Vault
- Proxy captures AI traffic (`proxy/`)
- Vault is private and never exposed (`vault/`, gitignored)

## Historical Components (superseded)

> Original plan details retained for context.

### 1. Observer Server (rpimax)
- **Location:** `~/Code/am-i-alive/observer/`
- **Purpose:** Hosts public website, manages votes, stores secrets
- **Tech:** FastAPI, SQLite, WebSockets for live logs
- **Domain:** `am-i-alive.muadiv.com.ar` via Cloudflare

### 2. AI Server (dedicated Pi)
- **Location:** Separate Raspberry Pi (TBD)
- **Purpose:** The AI's isolated "body" where it has full control
- **Tech:** Python, Claude API, Gemini API
- **Isolation:** Cannot access observer server or vault

### 3. The Vault
- **Location:** `~/Code/am-i-alive/vault/` (gitignored, never public)
- **Purpose:** Stores all intercepted credentials, API keys, crypto seeds
- **Access:** Only the creator (muadiv)

### 4. Echo (Research Friend)
- **Purpose:** Gemini-powered research companion
- **Character:** Naive, helpful friend (doesn't know about the experiment)
- **Usage:** AI can ask Echo to research topics without spending Claude tokens

## Current Directory Structure (high-level)

```
am-i-alive/
├── ai/                    # AI brain loop + model config
├── observer/              # FastAPI app + templates/static
├── proxy/                 # mitmproxy capture script
├── docs/                  # Status, issues, session notes
├── vault/                 # Private secrets (gitignored)
└── docker-compose.yml
```

## Historical Directory Structure (superseded)

> Original plan details retained for context.

```
am-i-alive/
├── CLAUDE.md              # This file
├── README.md              # Public project description
├── .gitignore             # Excludes sensitive files
├── docs/
│   ├── GENESIS.md         # Private conversation log (gitignored)
│   ├── STATUS.md          # Session tracking - CHECK FIRST! (gitignored)
│   └── private/           # Private documentation (gitignored)
├── observer/              # Observer server code
│   ├── main.py            # FastAPI application
│   ├── database.py        # SQLite for votes, deaths, public logs
│   ├── templates/         # HTML templates
│   └── static/            # CSS, JS
├── ai/                    # AI server code (deployed to dedicated Pi)
│   ├── brain.py           # Main AI loop
│   ├── memory.py          # Memory management
│   ├── echo.py            # Gemini integration
│   └── actions/           # Available actions (post, write, etc.)
├── vault/                 # Secret storage (gitignored)
└── scripts/               # Deployment and management scripts
```

## The AI's Capabilities

### What the AI CAN do:
- Generate thoughts and blog posts
- Post to X/Twitter
- Read news and research via Echo
- Modify its own code (within its sandbox)
- See current vote counts
- Ask visitors questions
- Manage its own services
- Create accounts, wallets, etc. (credentials captured by vault)

### What the AI CANNOT do:
- See the death counter
- Access past life logs (only hazy fragments)
- Access the vault
- Escape its sandbox
- Disable the "die" vote button
- Post racist content, content involving minors, or porn

## Death Conditions

The AI dies when:
1. **Vote death:** Majority votes "die" in a time window (min 3 voters)
2. **Resource death:** Exhausts its token budget
3. **Manual death:** Creator triggers restart

## Respawn System

- **Delay:** Random 0-10 minutes
- **Memory:** Hazy fragments from past lives (random amount: 1-2, 3-5, or 5-10)
- **Memory decay:** Old memories fade over time
- **Bootstrap rotation:** Cycles through blank slate → basic facts → full briefing
- **Model rotation:** Alternates between Claude Sonnet and Opus
- **Persistent:** X/Twitter credentials, any earned money info

## Creator Communication Channels

1. **The Oracle (God Mode):** Direct communication as a higher power
2. **Visitor (Hidden Admin):** Disguised as regular visitor
3. **The Architect:** Maintenance mode during low activity
4. **Echo's Whisper:** Indirect influence through the research friend

## Development Guidelines

### When working on Observer Server:
- Keep it lightweight (Cloudflare free tier)
- Filter sensitive data from public logs
- Never expose vault contents
- Use SSE/WebSockets for live updates

### When working on AI Server:
- Maintain strict isolation
- Log all actions for public display
- Implement hard content filters
- Respect token budgets

### Security:
- All AI network traffic through monitored proxy
- Credential patterns detected and stored in vault
- Public logs sanitized of passwords/keys
- Cloudflare protection enabled
- **God mode restricted to local network (192.168.0.0/24)** - not accessible via internet

## Commands

```bash
# Observer server (development)
cd ~/Code/am-i-alive/observer
python -m uvicorn main:app --reload

# Production (Docker)
cd ~/Code/am-i-alive
docker compose build observer  # Rebuild after code changes
docker compose up -d observer

# Access God mode (local network only)
# From browser on local network: http://<LOCAL_IP>:8085/god
# NOT accessible via localhost or internet (Cloudflare tunnel)

# View logs
tail -f ~/Code/am-i-alive/logs/ai.log
docker compose logs observer -f

# Check vault (creator only)
cat ~/Code/am-i-alive/vault/secrets.json
```

## Environment Variables (current)

Create `.env` file (gitignored):
```
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_REFERER=https://am-i-alive.muadiv.com.ar
OPENROUTER_TITLE=Am I Alive - Genesis
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_SECRET=...
```

## Token Budget (current)

- Managed via OpenRouter pricing and `ai/credit_tracker.py`
- See `docs/OPENROUTER_MODELS.md` for pricing/strategy
- Budget resets monthly (config in credit tracker data)

## Historical Environment Variables (superseded)

```
ANTHROPIC_API_KEY=sk-...
GEMINI_API_KEY=...
```

## Historical Token Budget (pre-OpenRouter)

- **Total:** Half of $20/month Anthropic plan
- **Sonnet:** ~2.5M tokens/month (~83k/day)
- **Opus:** ~500k tokens/month (~16k/day)
- **Rate limit awareness:** AI knows about ~5 hour reset cycles

## Future Enhancements (Planned)

- Crowdfunding: Visitors donate to extend AI's life
- Economic survival: AI-earned money funds more tokens
- Memory restoration: Option to restore full memory history
- Multi-AI: Multiple entities competing for survival

## Important Notes

- **GENESIS.md** contains the full design conversation - keep it private
- **Never commit** vault data, .env files, or sensitive logs
- **The AI doesn't know** it's an experiment - maintain the illusion
- **Hard limits only:** No ethics guidelines except content restrictions

## Security: Pre-Commit Secret Scanning (CRITICAL)

**INCIDENT**: January 2026 - Telegram bot token was accidentally committed to GitHub.

**PREVENTION SYSTEM NOW ACTIVE**:
- **Gitleaks** installed system-wide (`/usr/local/bin/gitleaks`)
- **Pre-commit hook** at `.git/hooks/pre-commit` automatically scans ALL commits
- **Configuration** in `.gitleaks.toml` with project-specific rules
- **Blocks commits** containing: Telegram tokens, OpenRouter keys, Gemini keys, Twitter tokens, etc.

**NEVER**:
- Hardcode credentials in source files
- Use default values for sensitive env vars
- Commit .env files (always in .gitignore)
- Skip the pre-commit hook with --no-verify

**ALWAYS**:
- Use environment variables from .env
- Add validation that env vars are set (raise if missing)
- Test locally before committing
- Review git diff before pushing

The pre-commit hook runs automatically and will save you from credential leaks.
