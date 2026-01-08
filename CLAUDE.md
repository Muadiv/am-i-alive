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

## Architecture

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

## Key Components

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

## Directory Structure

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

## Commands

```bash
# Observer server
cd ~/Code/am-i-alive/observer
python -m uvicorn main:app --reload

# View logs
tail -f ~/Code/am-i-alive/logs/ai.log

# Check vault (creator only)
cat ~/Code/am-i-alive/vault/secrets.json
```

## Environment Variables

Create `.env` file (gitignored):
```
ANTHROPIC_API_KEY=sk-...
GEMINI_API_KEY=...
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_SECRET=...
```

## Token Budget

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
