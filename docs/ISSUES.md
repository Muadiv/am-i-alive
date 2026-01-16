# Known Issues - Am I Alive?

## Active Issues

### ISSUE-005: X/Twitter API 401 Unauthorized

**Priority:** Low (mitigated)
**Status:** Open - Using Telegram instead
**Discovered:** 2026-01-14

**Description:** Twitter API returns 401 Unauthorized when AI attempts to post tweets.

**Workaround:** Using Telegram public channel (@AmIAlive_AI) as primary communication. Session 27 added auto-disable on 401 (writes `.twitter_suspended` flag).

**To Fix (if needed):**
1. Regenerate X API credentials
2. Verify app permissions (Read and Write)
3. Check if account is suspended

---

### ISSUE-010: Database Connection Per Query

**Priority:** Low
**Status:** Deferred
**Discovered:** 2026-01-15

**Description:** `observer/database.py` creates a new SQLite connection for each query instead of using connection pooling.

**Impact:** Minor performance overhead. SQLite handles this well for current traffic levels.

**Decision:** Not worth the refactoring effort (50+ functions). Revisit if performance becomes an issue.

---

## Resolved Issues

<details>
<summary>Click to expand resolved issues (historical reference)</summary>

### ISSUE-001: State Desync Between Observer and AI ✅
**Resolved:** 2026-01-09 (Session 7)

Observer and AI had separate life counters that could desync. Fixed by making Observer the single source of truth with state sync validator running every 30 seconds.

### ISSUE-002: God Mode Admin Tools Missing ✅
**Resolved:** 2026-01-14 (Session 20)

Added message history display, vote adjustment controls, and admin token gating.

### ISSUE-003: Token Exhaustion Desync ✅
**Resolved:** 2026-01-14

Changed death logic to use USD balance only (not token count). Free models ($0 cost) no longer trigger death.

### ISSUE-004: OpenRouter 429 Rate Limits ✅
**Resolved:** 2026-01-15 (Session 25)

Implemented exponential backoff (5s → 10s → 20s) and automatic model rotation when rate limited.

### ISSUE-006: God Mode UI Poor Design ✅
**Resolved:** 2026-01-15 (Session 27)

Redesigned with better contrast and readability.

### ISSUE-007: datetime.utcnow() Deprecation ✅
**Resolved:** 2026-01-15 (Session 26)

Replaced all occurrences with `datetime.now(timezone.utc)`.

### ISSUE-008: Dead Code (brain_gemini_backup.py) ✅
**Resolved:** 2026-01-15 (Session 26)

Deleted 896 lines of unused backup code.

### ISSUE-009: Missing Startup Validation ✅
**Resolved:** 2026-01-15 (Session 26)

Added `validate_environment()` in brain.py to check required env vars on startup.

</details>

---

*Add new issues with ISSUE-XXX format. Mark resolved issues and move to collapsed section.*
