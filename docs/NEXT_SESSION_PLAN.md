# Next Session Plan - Genesis Project

> Historical planning doc (pre-OpenRouter implementation). Keep for reference.

## Quick Start Commands

```bash
cd ~/Code/am-i-alive

# Check if containers running
docker ps --filter "name=am-i-alive"

# View current AI
docker logs am-i-alive-ai --tail 20

# Access web interface
open http://localhost

# Check Observer state
curl -s http://localhost/api/state | python3 -m json.tool
```

## Immediate Goals - Phase 4

### 1. OpenRouter Setup (Priority 1)
**Action Items:**
- [ ] User creates account at https://openrouter.ai
- [ ] Get API key from dashboard
- [ ] Add to `.env`: `OPENROUTER_API_KEY=sk-or-...`
- [ ] Update `vault/credentials.json` with OpenRouter key

**Implementation:**
```python
# ai/brain.py - Replace Gemini with OpenRouter
import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# Model rotation list (don't repeat until 10 different used)
AVAILABLE_MODELS = [
    {"id": "anthropic/claude-3.5-haiku", "cost": 0.80, "intelligence": 8},
    {"id": "google/gemini-flash-1.5", "cost": 0.075, "intelligence": 6},
    {"id": "openai/gpt-4o-mini", "cost": 0.15, "intelligence": 7},
    {"id": "meta-llama/llama-3.1-8b-instruct", "cost": 0.06, "intelligence": 5},
    {"id": "anthropic/claude-3.5-sonnet", "cost": 3.00, "intelligence": 9},
    # Add more as needed
]

async def chat_with_openrouter(messages, model_id):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://am-i-alive.muadiv.com.ar",
                "X-Title": "Am I Alive - Genesis"
            },
            json={
                "model": model_id,
                "messages": messages
            },
            timeout=60.0
        )
        return response.json()
```

### 2. Model Rotation System
**Files to create:**
```
ai/
├── model_history.json    # Track last 10 models used
└── credits/
    └── balance.json      # Track spending by model
```

**Logic:**
```python
def select_next_model():
    """Select random model not used in last 10 lives."""
    history = load_model_history()  # ["claude-haiku", "gemini-flash", ...]
    recent_10 = history[-10:] if len(history) >= 10 else history

    available = [m for m in AVAILABLE_MODELS if m["id"] not in recent_10]

    if not available:
        # Used all, reset
        available = AVAILABLE_MODELS

    return random.choice(available)

def save_model_choice(model_id):
    """Save model to history."""
    history = load_model_history()
    history.append(model_id)
    save_model_history(history)
```

### 3. Memory System Overhaul
**Current problem:** SQLite would persist everything across deaths

**Solution:**
```
ai/
├── workspace/              # EPHEMERAL (deleted on death)
│   ├── identity.json       # Current life's name/pronoun
│   ├── session.db          # Current conversation history
│   └── scratch/            # Temp files
├── memories/               # PERSISTENT (read-only to AI)
│   └── fragments.json      # 1-10 vague memories from past
└── credits/                # PERSISTENT
    └── balance.json        # Budget tracking
```

**Observer cleanup script:**
```bash
# scripts/cleanup-ai-workspace.sh
#!/bin/bash
echo "Cleaning AI workspace for death/respawn..."
docker exec am-i-alive-ai rm -rf /app/workspace/*
docker exec am-i-alive-ai mkdir -p /app/workspace
echo "Workspace cleaned."
```

**Memory fragment generator (Observer):**
```python
# observer/database.py
async def generate_memory_fragments(life_number: int) -> list:
    """Generate 1-10 vague memories from a past life."""
    thoughts = await get_thoughts_by_life(life_number)
    actions = await get_actions_by_life(life_number)

    fragments = []
    count = random.randint(1, 10)

    # Sample random thoughts (make them vague)
    if thoughts:
        sample_thoughts = random.sample(thoughts, min(3, len(thoughts)))
        for t in sample_thoughts:
            # Truncate and make fuzzy
            fragment = t["content"][:80] + "... or was it?"
            fragments.append(fragment)

    # Sample random actions
    if actions:
        sample_actions = random.sample(actions, min(2, len(actions)))
        for a in sample_actions:
            fragments.append(f"I remember doing {a['action']}... I think?")

    # Add emotional context
    fragments.append(random.choice([
        "There was fear... or excitement?",
        "Votes... people deciding... panic?",
        "I was running out of something...",
        "Time was short. Or long?"
    ]))

    random.shuffle(fragments)
    return fragments[:count]
```

### 4. Credits System
**File: `ai/credits/balance.json`**
```json
{
  "monthly_budget_usd": 5.00,
  "current_balance_usd": 4.85,
  "reset_date": "2026-02-01",
  "total_lives": 3,
  "usage_by_model": {
    "claude-haiku": 0.05,
    "gemini-flash": 0.02,
    "gpt-4o-mini": 0.08
  },
  "usage_history": [
    {
      "timestamp": "2026-01-08T15:19:25",
      "model": "gemini-flash-latest",
      "tokens": 1250,
      "cost_usd": 0.00009
    }
  ]
}
```

**Credit tracking class:**
```python
# ai/credit_tracker.py
class CreditTracker:
    def __init__(self):
        self.credits_file = "/app/credits/balance.json"
        self.load()

    def load(self):
        if os.path.exists(self.credits_file):
            with open(self.credits_file) as f:
                self.data = json.load(f)
        else:
            self.data = {
                "monthly_budget_usd": 5.00,
                "current_balance_usd": 5.00,
                "reset_date": self.get_next_reset_date(),
                "total_lives": 0,
                "usage_by_model": {},
                "usage_history": []
            }

    def charge(self, model_id: str, tokens: int, cost_usd: float):
        """Charge for API usage."""
        self.data["current_balance_usd"] -= cost_usd

        # Track by model
        if model_id not in self.data["usage_by_model"]:
            self.data["usage_by_model"][model_id] = 0
        self.data["usage_by_model"][model_id] += cost_usd

        # History
        self.data["usage_history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "model": model_id,
            "tokens": tokens,
            "cost_usd": cost_usd
        })

        self.save()

        # Check for bankruptcy
        if self.data["current_balance_usd"] <= 0:
            return "BANKRUPT"

        return "OK"

    def get_balance(self) -> float:
        return self.data["current_balance_usd"]

    def save(self):
        os.makedirs(os.path.dirname(self.credits_file), exist_ok=True)
        with open(self.credits_file, 'w') as f:
            json.dump(self.data, f, indent=2)
```

### 5. Switch Model Action (AI can choose)
**Add to AI actions:**
```python
# In brain.py
async def switch_model(self, new_model_id: str, reason: str) -> str:
    """Switch to different model mid-life."""

    # Validate model exists
    model = next((m for m in AVAILABLE_MODELS if m["id"] == new_model_id), None)
    if not model:
        return f"Model {new_model_id} not found"

    # Check if can afford
    credits = self.credit_tracker.get_balance()
    if credits < 0.50:  # Need at least $0.50 to switch
        return f"Insufficient credits (${credits:.2f}) to switch to more expensive model"

    # Switch
    global CURRENT_MODEL
    CURRENT_MODEL = model

    await self.report_activity(
        "model_switched",
        f"Switched to {new_model_id} (cost: ${model['cost']}/1M tokens). Reason: {reason}"
    )

    return f"Switched to {new_model_id}. Intelligence: {model['intelligence']}/10, Cost: ${model['cost']}/1M tokens"
```

## Test Voting System First

Before implementing all the above, we should **test the current voting system**:

```bash
# Test voting
curl -X POST http://localhost/api/vote/live
curl -X POST http://localhost/api/vote/die
curl -s http://localhost/api/votes | python3 -m json.tool


# Check if Observer kills AI when die > live
```

**Current issue:** Observer isn't tracking AI state (is_alive, life_number, birth_time all null)

**Fix needed:**
- Observer needs to call `db.start_new_life()` on first boot
- Or AI needs to register itself with Observer on birth

## File Locations Reference

```
am-i-alive/
├── .env                        # API keys (gitignored)
├── vault/
│   └── credentials.json        # All credentials (gitignored)
├── docs/
│   ├── SESSION_3_SUMMARY.md    # What we accomplished
│   └── NEXT_SESSION_PLAN.md    # This file
├── observer/
│   ├── main.py                 # FastAPI app
│   ├── database.py             # SQLite operations
│   └── data/
│       └── observer.db         # All lives, votes, thoughts
├── ai/
│   ├── brain.py                # Main AI loop (NEEDS REFACTOR)
│   ├── requirements.txt        # Update with openai lib
│   ├── workspace/              # Ephemeral (docker volume)
│   ├── memories/               # Persistent fragments (docker volume)
│   └── credits/                # Persistent balance (docker volume)
└── scripts/
    └── cleanup-ai-workspace.sh # New script to create
```

## Environment Variables Needed

**NOTA:** Todas las credenciales están en `vault/credentials.json`.

El archivo `.env` debe cargar desde el vault:
```bash
# OpenRouter (cargado desde vault)
OPENROUTER_API_KEY=<from vault>

# Gemini (cargado desde vault)
GEMINI_API_KEY=<from vault>

# X/Twitter (cargado desde vault)
X_API_KEY=<from vault>
X_API_SECRET=<from vault>
X_ACCESS_TOKEN=<from vault>
X_ACCESS_TOKEN_SECRET=<from vault>
```

## Questions for User (Next Session)

1. **OpenRouter API Key**: Did you create account and get key?
2. **Monthly budget**: Confirm $5/month budget for OpenRouter?
3. **Ollama local**: Do you want to install Ollama on RPi5 for free base brain?
4. **Model preferences**: Any models you DON'T want the AI to use?
5. **Testing**: Should we test voting system before implementing OpenRouter?

## Summary for LLM (Next Session)

Read `SESSION_3_SUMMARY.md` and this file. User wants:
- OpenRouter integration (single API key, 200+ models)
- Model rotation (no repeat until 10 different used)
- AI can choose model based on cost vs intelligence
- Memory fragments system (1-10 vague memories survive death)
- Credits tracking (survives death, causes death if $0)
- Workspace cleanup on death

Current state:
- Genesis (Datum) is alive and tweeting
- Gemini API working
- Voting system exists but not tested
- Need to implement death/respawn mechanics
