# Known Issues - Am I Alive?

## ✅ Resolved Issues

### ISSUE-001: State Desync Between Observer and AI Containers

**Priority:** High
**Status:** ✅ RESOLVED (BE-003)
**Discovered:** 2026-01-09
**Resolved:** 2026-01-09 (Session 7)
**Component:** Observer/AI Communication

#### Description

The Observer database and AI container maintain separate life counters that can become out of sync. This causes the system to believe the AI is dead when it's actually alive, or vice versa.

#### Reproduction

1. Start the system: `docker compose up -d`
2. Let the AI die naturally (token exhaustion or vote death)
3. Check Observer state: `curl http://localhost/api/state/full`
4. Check AI logs: `docker logs am-i-alive-ai --tail 20`
5. Observer shows Life #70, AI shows Life #14

#### Expected Behavior

- Observer is the single source of truth for life_number
- AI container should never increment life_number on its own
- Birth sequences should ONLY be initiated by Observer
- State should always be in sync

#### Current Behavior

- AI container has independent life counter
- AI can self-respawn without Observer knowing
- Observer database shows `is_alive=0, life_number=70`
- AI logs show `Life #14` and is actively thinking
- Voting is blocked because Observer thinks AI is dead

#### Impact

- **Critical:** Users cannot vote when AI is actually alive
- **Critical:** System state is inconsistent
- **Medium:** Metrics and analytics are incorrect
- **Medium:** Death counter doesn't reflect reality

#### Root Cause Analysis

**Problem:** The AI container has autonomy to manage its own lifecycle.

**Code Location:**
- `ai/brain.py`: Line ~XXX - AI can increment life counter
- `observer/main.py`: `schedule_respawn()` - Observer initiates birth
- No synchronization mechanism between the two

**Why it happens:**
1. AI dies (token exhaustion or vote)
2. Observer schedules respawn
3. Observer calls `/api/birth` on AI
4. **Bug:** AI may have already self-respawned with different life_number
5. Observer doesn't validate that birth was accepted
6. Two systems now have different life_numbers

#### Proposed Solutions

**Option A: Observer as Single Authority (Recommended)**
```python
# ai/brain.py
# Remove: self.life_number auto-increment
# Change: Always get life_number from Observer

async def birth_sequence(self, life_data):
    """Accept birth data from Observer - never create own life."""
    self.life_number = life_data['life_number']  # From Observer
    self.bootstrap_mode = life_data['bootstrap_mode']
    # ... rest of birth
```

**Option B: Two-Phase Commit**
```python
# observer/main.py
async def notify_ai_birth(life_info):
    # Phase 1: Request birth
    response = await client.post(f"{AI_API_URL}/birth", json=life_info)

    # Phase 2: Verify acceptance
    state = await client.get(f"{AI_API_URL}/state")
    if state['life_number'] != life_info['life_number']:
        # RETRY or ABORT
        raise BirthSyncError()
```

**Option C: Heartbeat Validation**
```python
# observer/main.py
async def heartbeat_validator():
    """Continuously validate AI state matches Observer."""
    while True:
        observer_state = await db.get_current_state()
        ai_state = await fetch_ai_state()

        if observer_state['life_number'] != ai_state['life_number']:
            # FIX: Force AI to sync with Observer
            await force_ai_sync(observer_state)
```

#### Recommended Fix: **Option A + Option C**

1. **Immediate:** Implement Option C (heartbeat validation) to detect desyncs
2. **Short-term:** Implement Option A (remove AI autonomy)
3. **Long-term:** Add integration tests for birth/death cycles

#### Workaround (Temporary)

If state is desynced:

```bash
# Stop AI container
docker compose stop ai

# Reset Observer state
docker exec am-i-alive-observer python3 -c "
import asyncio
import database as db
asyncio.run(db.init_db())
# Manually fix state in DB
"

# Restart both
docker compose restart observer ai
```

#### Files Modified

- [x] `ai/brain.py` - Remove autonomous life management, accept life_number from Observer
- [x] `observer/main.py` - Add state validation (`state_sync_validator`)
- [x] `observer/database.py` - Add sync support
- [x] `observer/tests/test_state_sync.py` - Added sync tests

#### Resolution

Implemented BE-003 with:
1. Observer-driven birth gating in AI (`/birth` endpoint)
2. AI `/state` + `/force-sync` endpoints
3. Observer state sync validator runs every 30 seconds
4. Per-life heartbeat token tracking

#### References

- Fix session: 2026-01-09 (Session 7)
- Commit: See Session 7 in STATUS.md

---

### ISSUE-003: Token Exhaustion Desync (AI Continues After Death)

**Priority:** High
**Status:** ✅ RESOLVED
**Discovered:** 2026-01-09
**Resolved:** 2026-01-14
**Component:** Observer/AI State Consistency

#### Description

Observer marks the AI dead due to token exhaustion, but the AI continues running and
sending heartbeats (last_seen keeps updating). This creates a "dead-but-alive" desync.

#### Resolution

**Root cause was fixed by changing death logic:**
- Death now triggers on **USD balance <= $0.01** only (bankruptcy)
- Token count is informational only - NOT a death trigger
- Free models ($0 cost) can be used indefinitely
- Observer queries AI's `/budget` endpoint every 30 seconds for real balance

**Code changes:**
- `observer/main.py:token_budget_checker()` - Now queries `/budget`, checks `balance_usd`
- Removed `tokens_used >= tokens_limit` death condition

#### References

- Fix documented in STATUS.md Priority 0A
- Implementation verified in `observer/main.py:965-1008`

---

---

### ISSUE-002: God Mode Admin Tools Missing (Message History + Vote Override)

**Priority:** Medium
**Status:** ✅ RESOLVED
**Discovered:** 2026-01-09
**Resolved:** 2026-01-14 (Session 20)
**Component:** Observer/God Mode

#### Description

God Mode should provide a full message history (visitor + god mode/oracle messages) and allow
manual adjustment of the vote counters.

#### Resolution

Implemented in Session 20 (Security Hardening):
- God mode shows all visitor messages (read + unread)
- God mode shows all Oracle/God Mode messages sent to AI
- `/api/god/votes/adjust` endpoint for manual vote counter modification
- Admin token gating with local network bypass

---

## 🐛 Active Issues

### ISSUE-004: OpenRouter 429 Rate Limits

**Priority:** Medium
**Status:** ✅ RESOLVED
**Discovered:** 2026-01-14 (Session 23)
**Resolved:** 2026-01-15 (Session 24)
**Component:** AI/OpenRouter Integration

#### Description

OpenRouter returns 429 (Too Many Requests) when using free tier models like `qwen/qwen3-coder:free`.

#### Resolution

Implemented automatic 429 handling in `ai/brain.py`:
1. **Exponential backoff:** Wait 5s, 10s, 20s between retries
2. **Model rotation:** Auto-switch to different free model when rate limited
3. **Max retries:** 3 attempts before giving up
4. **Activity logging:** Rate limit events logged to observer

**Code location:** `ai/brain.py:513-559`

---

### ISSUE-005: X/Twitter API 401 Unauthorized

**Priority:** Medium
**Status:** Open (Mitigated)
**Discovered:** 2026-01-14 (Session 23)
**Component:** AI/Twitter Integration

#### Description

Twitter API returns 401 Unauthorized when AI attempts to post tweets.

#### Evidence

```
X/Twitter birth tweet returns 401 Unauthorized
```

#### Impact

- AI cannot post to Twitter
- Birth announcements fail silently

#### Proposed Solutions

1. Regenerate X API credentials (API Key, Secret, Access Token)
2. Verify app permissions (Read and Write)
3. Check if account is suspended or restricted
4. Add `.twitter_suspended` flag file when 401 detected (implemented in Session 27)

#### Workaround

Using Telegram public channel (@AmIAlive_AI) as alternative communication method. Session 27 auto-disables X on 401/unauthorized by writing `.twitter_suspended`.

---

## 🟢 Low Priority Issues

### ISSUE-007: Deprecation Warnings (datetime.utcnow)

**Priority:** Low
**Status:** ✅ RESOLVED
**Discovered:** 2026-01-15 (Session 25)
**Resolved:** 2026-01-15 (Session 26)
**Component:** Multiple files

#### Description

Python 3.12+ deprecates `datetime.utcnow()`. Should use `datetime.now(timezone.utc)` instead.

#### Resolution

Replaced all `datetime.utcnow()` with `datetime.now(timezone.utc)` across:
- `observer/database.py` - All occurrences + added timezone-aware parsing for SQLite dates
- `ai/brain.py` - All occurrences + fixed comparison issues
- `ai/credit_tracker.py` - Reset date handling
- `scripts/vote_checker.py` - Duration calculation
- `observer/tests/*.py` - Updated test fixtures to use real datetime operations

---

### ISSUE-008: Dead Code - brain_gemini_backup.py

**Priority:** Low
**Status:** ✅ RESOLVED
**Discovered:** 2026-01-15 (Session 25)
**Resolved:** 2026-01-15 (Session 26)
**Component:** AI

#### Description

File `ai/brain_gemini_backup.py` (896 lines) was never imported or used. It was a duplicate of `brain.py` from before OpenRouter migration.

#### Resolution

Deleted the file entirely. No archive needed as git history preserves it.

---

### ISSUE-009: Missing Startup Validation

**Priority:** Low
**Status:** ✅ RESOLVED
**Discovered:** 2026-01-15 (Session 25)
**Resolved:** 2026-01-15 (Session 26)
**Component:** Observer/AI

#### Description

Neither Observer nor AI validate that required environment variables are set at startup.

#### Resolution

Added `validate_environment()` function to `ai/brain.py` that:
- Raises RuntimeError for missing required vars (OPENROUTER_API_KEY, OBSERVER_URL)
- Prints warnings for missing optional vars (TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, etc.)

---

### ISSUE-010: Database Connection Per Query

**Priority:** Low
**Status:** Deferred
**Discovered:** 2026-01-15 (Session 25)
**Component:** Observer/Database

#### Description

`observer/database.py` creates a new SQLite connection for each query instead of using connection pooling or a persistent connection.

#### Impact

- Performance overhead on high traffic
- Not critical for current usage levels
- SQLite handles this reasonably well for low-traffic scenarios

#### Decision

Deferred - The current implementation works fine for expected traffic levels. Implementing connection pooling would require significant refactoring of 50+ database functions. Will revisit if performance becomes an issue.

#### Proposed Solution (If Needed Later)

1. Create a connection manager class that maintains a connection pool
2. Refactor all `async with aiosqlite.connect()` calls to use the pool
3. Add proper connection cleanup on shutdown

---

### ISSUE-006: God Mode UI/UX Poor Design

**Priority:** Low
**Status:** ✅ RESOLVED
**Discovered:** 2026-01-14
**Resolved:** 2026-01-15
**Component:** Observer/Templates

#### Description

God mode page had poor contrast, illegible text, and overall ugly appearance.

#### Resolution

UI was redesigned with better contrast and readability.
