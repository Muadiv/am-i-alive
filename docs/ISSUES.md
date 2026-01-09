# Known Issues - Am I Alive?

## 🐛 Critical Issues

### ISSUE-001: State Desync Between Observer and AI Containers

**Priority:** High
**Status:** Partially Resolved
**Discovered:** 2026-01-09
**Component:** Observer/AI Communication

#### Description

The Observer database and AI container maintain separate life counters that can become out of sync. This causes the system to believe the AI is dead when it's actually alive, or vice versa.

#### Reproduction

1. Start the system: `docker compose up -d`
2. Let the AI die naturally (token exhaustion or vote death)
3. Check Observer state: `curl http://localhost:8085/api/state/full`
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

#### Files to Modify

- [x] `ai/brain.py` - Remove autonomous life management
- [x] `observer/main.py` - Add state validation
- [x] `observer/database.py` - Add sync support
- [x] `observer/tests/test_state_sync.py` - Added sync tests

#### Related Issues

- None yet (first critical bug discovered)

#### References

- Test session: 2026-01-09
- Commit: `471a2a4`
- Observer container: `am-i-alive-observer`
- AI container: `am-i-alive-ai`

---

### ISSUE-003: Token Exhaustion Desync (AI Continues After Death)

**Priority:** High  
**Status:** Open  
**Discovered:** 2026-01-09  
**Component:** Observer/AI State Consistency

#### Description

Observer marks the AI dead due to token exhaustion, but the AI continues running and
sending heartbeats (last_seen keeps updating). This creates a "dead-but-alive" desync.

#### Evidence (Life #105)

- `current_state`: `is_alive=0`, `life_number=105`, `model="NVIDIA Nemotron Nano"`,  
  `tokens_used=227815`, `tokens_limit=83000`, `last_seen=2026-01-09 16:19:57`.
- Latest death: `cause="token_exhaustion"` at `2026-01-09 15:50:48` for Life #105.
- Model switches happened after that death.

#### Impact

- Observer UI shows DEAD while AI is still acting.
- Votes are blocked even though AI is active.
- State consistency breaks (token death not enforced).

#### Proposed Directions (no changes yet)

1) Enforce death on AI side when Observer records a death.
2) Detect "alive while dead" and either stop AI or reconcile state.
3) Sync model changes without affecting life state (chosen direction).
4) Review token exhaustion thresholds to avoid premature death.

---

## 🟡 Medium Priority Issues

### ISSUE-002: God Mode Admin Tools Missing (Message History + Vote Override)

**Priority:** Medium  
**Status:** Open  
**Discovered:** 2026-01-09  
**Component:** Observer/God Mode

#### Description

God Mode should provide a full message history (visitor + god mode/oracle messages) and allow
manual adjustment of the vote counters. This is currently missing.

#### Requested Behavior

- Show a list of all visitor messages (read + unread) in God Mode.
- Show a list of all Oracle/God Mode messages sent to the AI.
- Allow manual modification of live/die vote counters from God Mode.

#### Notes

- This is an admin-only feature (local network).
- No changes implemented yet; requirements documented for future work.

---

## 🟢 Low Priority Issues

*(None yet)*

---

## ✅ Resolved Issues

*(None yet)*
