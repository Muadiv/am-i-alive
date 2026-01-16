# Code Review - Am I Alive?

> **Review Date:** 2026-01-16
> **Reviewer:** Claude Opus 4.5 (automated analysis)
> **Scope:** Full codebase security and quality review

---

## Executive Summary

This review identified **8 security vulnerabilities** (3 resolved), **5 code quality issues**, **2 confirmed bugs**, and various backlog items (missing features, documentation gaps, test coverage).

**Priority Actions (Confirmed Issues):**
1. Fix XSS vulnerabilities in template rendering ✅ (Session 27)
2. Add CSRF protection for state-changing operations ✅ (Session 27)
3. Hide sensitive error details from API responses ✅ (Session 27)
4. Track birth instructions per life ✅ (Session 27)

**Backlog (Nice-to-haves):**
- Audit logging, rate limiting middleware, state machine formalization
- Documentation improvements, additional test coverage

---

## 1. Security Vulnerabilities

### CRITICAL: XSS via Unescaped innerHTML (CWE-79) ✅ RESOLVED

**Files affected:**
- `observer/templates/index.html:450-453` - SSE thought stream
- `observer/templates/index.html:474` - Status banner
- `observer/templates/god.html:603-625` - Chronicle posts
- `observer/templates/god.html:801` - Message history

**Issue:** User-controlled data (AI thoughts, posts) is injected via `innerHTML` without sanitization:

```javascript
thought.innerHTML = `<p class="thought-content">${event.data}</p>`;
```

**Risk:** If the AI generates content containing `<script>` tags or event handlers, arbitrary JavaScript executes in visitors' browsers.

**Fix:** Use `textContent` for text content, or sanitize with DOMPurify:

```javascript
thought.querySelector('.thought-content').textContent = event.data;
// OR
thought.innerHTML = DOMPurify.sanitize(`<p>${event.data}</p>`);
```

---

### HIGH: Missing CSRF Protection (CWE-352) ✅ RESOLVED

**Files affected:**
- `observer/main.py` - All God Mode endpoints

**Issue:** State-changing endpoints accept POST without CSRF tokens:
- `/api/kill` - Kills the AI
- `/api/respawn` - Triggers respawn
- `/api/force-alive` - Forces alive state
- `/api/god/votes/adjust` - Manipulates votes
- `/api/god/oracle` - Sends oracle messages

**Risk:** Admin visiting malicious site could trigger these actions via hidden form/fetch.

**Fix:** Implement CSRF token verification:

```python
from fastapi import Cookie
import secrets

@app.post("/api/kill")
async def kill_ai(request: Request, csrf_token: str = Cookie(None)):
    if not csrf_token or not verify_csrf(csrf_token, request):
        raise HTTPException(403, "Invalid CSRF token")
    # ... rest of logic
```

---

### HIGH: Sensitive Error Information Disclosure (CWE-209) ✅ RESOLVED
**Files affected:**
- `ai/budget_server.py:169-181`
- `observer/main.py:1141, 1432`

**Issue:** Full exception details returned to clients:

```python
except Exception as e:
    return {"error": True, "details": str(e)}  # Leaks internal info
```

**Risk:** Stack traces, file paths, and system info could leak to attackers.

**Fix:** Return generic errors, log details server-side:

```python
except Exception as e:
    logger.error(f"Budget error: {e}", exc_info=True)
    return {"error": True, "message": "Internal server error"}
```

---

### MEDIUM: Race Conditions in Async Operations (CWE-362) (Pending)

**Files affected:**
- `observer/main.py:935-977` - State sync validator
- `observer/main.py:979-1006` - Voting window checker
- `observer/main.py:1009-1051` - Budget checker

**Issue:** Multiple background tasks modify shared state without synchronization:

```python
async def state_sync_validator():
    while True:
        await asyncio.sleep(30)
        await validate_state_sync_once()  # Can race with voting/budget checks
```

**Risk:** State corruption, double deaths, or missed death conditions.

**Fix:** Use `asyncio.Lock` for shared state:

```python
state_lock = asyncio.Lock()

async def validate_state_sync_once():
    async with state_lock:
        # ... validation logic
```

---

### MEDIUM: Authentication Relies Solely on IP Trust (CWE-290)

**File:** `observer/main.py:178-217`

**Issue:** God Mode auth trusts any request from LOCAL_NETWORK (192.168.0.0/24):

```python
if client_ip in LOCAL_NETWORK:
    return True  # Any device on local network is trusted
```

**Risk:** Compromised device on local network can access God Mode. VLAN isolation helps but isn't foolproof.

**Recommendation:** Add secondary authentication (password, 2FA) even for local access.

---

### MEDIUM: Incomplete Input Sanitization (CWE-20)

**File:** `observer/main.py:1311-1336`

**Issue:** `sanitize_message()` uses regex blacklist for shell metacharacters:

```python
dangerous_patterns = [r'\$\([^)]*\)', r'`[^`]*`', ...]
for pattern in dangerous_patterns:
    text = re.sub(pattern, '[filtered]', text)
```

**Risk:** Bypass via variations: `$( cmd)`, unicode lookalikes, or unlisted metacharacters.

**Fix:** Use whitelist validation instead:

```python
def sanitize_message(text: str) -> str:
    # Allow only alphanumeric, spaces, basic punctuation
    return re.sub(r'[^a-zA-Z0-9\s.,!?\'\"-]', '', text)
```

---

### LOW: Hardcoded Cloudflare IP Ranges

**File:** `observer/main.py:145-175`

**Issue:** Cloudflare IP ranges are hardcoded and may become outdated.

**Recommendation:** Fetch dynamically from https://www.cloudflare.com/ips-v4 or use environment variable.

---

### LOW: Budget Server Binds to All Interfaces (Pending Verification)

**Note:** DNS stability is still intermittent; resolved via resolv.conf overrides on DietPi.

**File:** `ai/budget_server.py`

**Issue:** Server binds to `0.0.0.0:8001` but should only be accessible from localhost.

**Fix:** Bind to `127.0.0.1`:

```python
uvicorn.run(app, host="127.0.0.1", port=8001)
```

---

## 2. Code Quality Issues

### Dead Code

| Location | Description |
|----------|-------------|
| `observer/database.py:322-360` | `close_current_voting_window()` marked DEPRECATED |
| `observer/database.py:1157` | TODO comment for TASK-004 validation |

**Action:** Remove deprecated functions after confirming no tests depend on them.

---

### Code Duplication

**Files:** `ai/budget_server.py:69-102` and `ai/credit_tracker.py:245-283`

Token aggregation logic is duplicated. Extract to shared utility:

```python
# ai/utils.py
def aggregate_tokens(tracker_data: dict, life_number: int = None) -> dict:
    # Shared aggregation logic
    pass
```

---

### Inconsistent Error Handling ✅ RESOLVED

**Pattern 1:** Silent failures with no logging:
```python
except Exception:
    budget_data = {"error": "Could not fetch budget"}  # No log
```

**Pattern 2:** Bare except clauses:
```python
except:  # Catches everything including SystemExit, KeyboardInterrupt
    pass
```

**Fix:** Always log exceptions, use specific exception types.

---

### Magic Numbers

| Location | Value | Should Be |
|----------|-------|-----------|
| `main.py:130` | `RESPAWN_DELAY_MIN = 10` | Environment variable |
| `main.py:133` | `STATE_SYNC_INTERVAL = 30` | Environment variable |
| `main.py:30` | `VOTING_WINDOW_SECONDS = 3600` | Configurable |

---

### Inconsistent Naming

- `message_type` vs `notification_type` vs `type`
- `life_number` vs `current_life_number`
- `is_notable` vs `notable_id`

**Action:** Establish naming conventions in CONTRIBUTING.md.

---

## 3. Potential Bugs

### Bug 1: Charge Allowed Before Balance Check

**File:** `ai/credit_tracker.py:217-228`

```python
def charge(self, ...):
    # Balance deducted first
    self._balance -= cost

    # Status checked after
    if self._balance <= 0:
        return "BANKRUPT"
```

**Issue:** If balance is $0.01 and cost is $0.01, charge succeeds but returns BANKRUPT.

**Fix:** Check before charging:

```python
if self._balance - cost <= 0:
    return "BANKRUPT"  # Don't charge
self._balance -= cost
```

---

### Bug 2: SSE Stream Memory Growth

**File:** `observer/main.py:1061-1087`

```python
sent_ids = set()
while True:
    # ...
    if len(sent_ids) > 100:
        sent_ids.clear()  # Could cause duplicates after clear
```

**Issue:** Clearing `sent_ids` can cause re-sending of activities if they're still in the recent query window.

**Fix:** Use bounded LRU cache or sliding window of timestamps.

---

### ~~Bug 3: Timezone Edge Cases~~ (VERIFIED OK)

**Status:** Not a bug - timezone handling was already fixed in Session 26.

All datetime operations now use `datetime.now(timezone.utc)` consistently. The `to_prague_time` filter handles display conversion. SQLite dates are parsed with timezone awareness.

---

### ~~Bug 4: Birth Time Template Handling~~ (VERIFIED OK)

**Status:** Not a bug - intentional fallback handling.

**File:** `observer/templates/index.html:416`

```javascript
if (!birthTime || birthTime === "None") {
    timeAliveEl.textContent = "N/A";
    return;
}
```

The code explicitly checks for the "None" string and handles it gracefully. This is defensive coding, not a bug.

---

### Threat Model Note: Vote Gaming via Multiple IPs

**File:** `observer/database.py:297-319`

**Note:** This is a threat model consideration, not a bug. The current design accepts this risk.

No global vote caps exist - a botnet could theoretically trigger death with enough IPs. However:
- Minimum 3 votes required before death can occur
- 1 vote per IP per hour rate limit exists
- Cloudflare provides some DDoS protection
- This is an art project, not critical infrastructure

**Future considerations (if needed):**
- Captcha for votes
- Maximum votes per life
- Cloudflare rate limiting rules

---

## 4. Backlog: Nice-to-Have Features

> These are enhancements, not bugs. Prioritize based on project goals.

### 4.1 Audit Logging (Low Priority)

God Mode operations aren't logged with integrity guarantees. Implement append-only audit log:

```python
async def audit_log(action: str, admin_ip: str, details: dict):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "admin_ip": admin_ip,
        "details": details,
        "signature": sign_entry(...)  # HMAC or similar
    }
    # Write to append-only file/database
```

---

### 4.2 Rate Limiting Middleware (Low Priority)

No HTTP-level rate limiting (app-level checks exist). Could add with slowapi:

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/vote/{vote_type}")
@limiter.limit("1/hour")
async def vote(...):
    pass
```

---

### 4.3 API Documentation (Low Priority)

No OpenAPI/Swagger specification exposed. FastAPI generates this automatically - could enable at `/docs`:

```python
@app.get("/api/state", response_model=StateResponse, tags=["Public API"])
async def get_state():
    """Returns current AI state including life status and vote counts."""
    pass
```

---

### 4.4 Graceful Degradation (Medium Priority)

If budget server is unreachable, AI is never killed for bankruptcy (currently errs on side of keeping AI alive):

```python
except Exception as e:
    print(f"Failed to check budget: {e}")  # AI keeps running!
```

**Fix:** Implement circuit breaker - shutdown after N consecutive failures.

---

### 4.5 State Machine Formalization (Low Priority)

Life/death transitions aren't formally defined. Could implement explicit state machine:

```python
from enum import Enum

class AIState(Enum):
    DEAD = "dead"
    BIRTHING = "birthing"
    ALIVE = "alive"
    DYING = "dying"

VALID_TRANSITIONS = {
    AIState.DEAD: [AIState.BIRTHING],
    AIState.BIRTHING: [AIState.ALIVE, AIState.DEAD],
    AIState.ALIVE: [AIState.DYING],
    AIState.DYING: [AIState.DEAD],
}
```

---

## 5. Documentation Gaps

| Gap | Priority | Action |
|-----|----------|--------|
| No API specification | High | Enable FastAPI auto-docs at `/docs` |
| No database schema docs | Medium | Create ER diagram |
| No security model docs | Medium | Document trust boundaries |
| Outdated Docker references | Low | Remove or update |
| Missing flow diagrams | Low | Add to docs/ |

---

## 6. Test Coverage Gaps

### Critical Paths Untested

| Path | Risk | Priority |
|------|------|----------|
| XSS in templates | Resolved | Consider adding E2E tests with Playwright |
| CSRF on God Mode | High | Add security tests |
| Race conditions | Medium | Add concurrent test scenarios |
| Budget edge cases (negative balance) | Medium | Add unit tests |
| Authentication bypass attempts | High | Add security tests |

### Recommended Test Additions

```python
# tests/test_security.py

async def test_xss_in_thoughts():
    """Verify HTML is escaped in thought stream."""
    thought = "<script>alert('xss')</script>"
    await db.log_activity(1, "think", thought)
    response = await client.get("/api/activity/recent")
    assert "&lt;script&gt;" in response.text

async def test_csrf_required_for_kill():
    """Verify kill endpoint requires CSRF token."""
    response = await client.post("/api/kill")
    assert response.status_code == 403

async def test_god_mode_requires_auth():
    """Verify God Mode blocked from external IPs."""
    # Simulate external IP
    response = await client.get("/god", headers={"X-Forwarded-For": "8.8.8.8"})
    assert response.status_code in [401, 403]
```

---

## Priority Action Plan

### Immediate (This Week)

1. **XSS Fix** ✅ - `innerHTML` replaced with DOM-safe rendering
2. **Error Disclosure** ✅ - Generic errors with server-side logging
3. **CSRF Tokens** ✅ - Enforced on all God Mode actions

### Short-Term (This Month)

4. **Race Conditions** - Add asyncio.Lock for shared state
5. **Audit Logging** - Implement for God Mode operations
6. **Rate Limiting** - Add middleware for vote and message endpoints
7. **Test Coverage** - Add security tests for auth and XSS

### Long-Term (Backlog)

8. **State Machine** - Formalize life/death transitions
9. **Documentation** - API specs, ER diagrams, security model
10. **Circuit Breaker** - Graceful degradation for external services

---

## Appendix: Files Reviewed

| File | Lines | Issues Found |
|------|-------|--------------|
| `ai/brain.py` | ~2300 | 2 |
| `ai/credit_tracker.py` | ~300 | 2 |
| `ai/budget_server.py` | ~200 | 2 |
| `observer/main.py` | ~1500 | 8 |
| `observer/database.py` | ~1200 | 3 |
| `observer/templates/*.html` | ~2000 | 4 |

---

*Generated by automated code review. Manual verification recommended for all findings.*
