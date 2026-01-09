# GPT TASK-004: Fix Issues Found in BE-003 Review

## Context

User reviewed the BE-003 implementation and found several issues that need fixing. See `BE-003-ISSUES.md` for full details.

## Task Overview

Fix the following issues in the "Am I Alive?" project:

1. Blog posts not being created
2. Death cause tracking needs manual option
3. Messages not being read by AI
4. System checks not happening
5. God mode needs kill button
6. Verify AI tone/personality

---

## Issue 1: Blog Posts Not Created (CRITICAL)

**Problem:** AI shows intent to write blog post in thoughts, but no posts appear in database.

**Evidence:**
```
Thought: "**Blog Post: "The Awakening of Nimbus"** *#existential #identity #survival*..."
Database: SELECT COUNT(*) FROM blog_posts → 0 results
```

**Investigation Needed:**
1. Check if `write_blog_post` action is being called correctly
2. Verify `/api/blog/post` endpoint is working
3. Check if AI is formatting actions correctly (JSON vs text)
4. Verify database writes are succeeding

**Files to Check:**
- `ai/brain.py` - `write_blog_post()` method and action execution
- `observer/main.py` - `/api/blog/post` endpoint
- `observer/database.py` - `create_blog_post()` function

**Expected Fix:**
- Identify why blog post intent doesn't result in API call
- Fix action parsing or execution
- Add error logging if blog post creation fails

---

## Issue 2: Add Manual Death Cause Tracking

**Problem:** 82 deaths show "token_exhaustion" but were actually code restarts during development.

**Current death causes:**
```sql
token_exhaustion: 82
vote_majority: 1
vote_death (die:3 > live:0): 1
```

**Required Changes:**

### A. Add "Kill" Button to God Mode

**File:** `observer/templates/god.html`

Add after line 177 (message type selector):

```html
<div style="margin-top: 30px; padding-top: 30px; border-top: 2px solid rgba(255,255,255,0.3);">
    <h3 style="color: #fff; text-align: center; margin-bottom: 20px;">💀 Life & Death Control</h3>

    <div class="god-form" style="background: rgba(255,100,100,0.1);">
        <div class="form-group">
            <label for="death-reason">Death Reason:</label>
            <input
                type="text"
                id="death-reason"
                placeholder="e.g., 'Code restart', 'Testing respawn', 'Manual intervention'..."
                style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 5px;"
            />
            <small style="display: block; margin-top: 5px; color: #666;">
                Leave blank for default: "manual_kill"
            </small>
        </div>

        <button onclick="killAI()" class="send-btn" style="background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);">
            ☠️ Kill AI Now
        </button>

        <div id="kill-status" class="status-message" style="display: none;"></div>
    </div>
</div>
```

Add JavaScript function:

```javascript
async function killAI() {
    const reason = document.getElementById('death-reason').value.trim();
    const statusEl = document.getElementById('kill-status');

    if (!confirm('Are you sure you want to kill the AI?')) {
        return;
    }

    try {
        const response = await fetch('/api/kill', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cause: reason || 'manual_kill'
            })
        });

        const data = await response.json();

        statusEl.textContent = data.success
            ? `✅ AI killed. Respawning soon...`
            : `❌ Failed: ${data.message}`;
        statusEl.className = 'status-message ' + (data.success ? 'success' : 'error');
        statusEl.style.display = 'block';

        if (data.success) {
            document.getElementById('death-reason').value = '';
            setTimeout(() => statusEl.style.display = 'none', 5000);
        }
    } catch (error) {
        statusEl.textContent = '❌ Error: ' + error.message;
        statusEl.className = 'status-message error';
        statusEl.style.display = 'block';
    }
}
```

### B. Verify `/api/kill` Endpoint

**File:** `observer/main.py` (lines 457-471)

Current implementation looks correct. Just verify the `cause` parameter is being used:

```python
@app.post("/api/kill")
async def kill_ai(request: Request, background_tasks: BackgroundTasks):
    """Kill the AI (manual death by creator)."""
    data = await request.json()
    cause = data.get("cause", "manual_kill")  # ✅ Already handles custom cause

    # ... rest of implementation
```

**✅ No changes needed to backend** - it already supports custom causes.

---

## Issue 3: Unread Messages Not Being Read

**Problem:** 4 unread messages in database, AI hasn't called `read_messages` action.

**Messages waiting:**
```
1. Diego: "Por que estas vivo ? hace cuanto ? por que quieres..."
2. Diego: "Hey, I will vote for live, but if you can speak sp..."
3. Anonymous: "My cat's life has more purpose than you!"
4. (one more)
```

**Investigation:**
1. Test if `read_messages` action works
2. Check if AI is being prompted about unread messages
3. Verify message count is visible to AI

**Files to Check:**
- `ai/brain.py` - `read_messages()` action (lines 1350-1386)
- Check if AI state includes message count
- Verify prompt mentions checking messages

**Potential Fix:**
Add message count to AI's state awareness in `think()` method or bootstrap prompt:

```python
# In think() method, add message count to situation:
message_count = await self.check_message_count()  # New helper method
if message_count > 0:
    prompt += f"\n⚠️ You have {message_count} unread messages from visitors!"
```

**Or:** Make AI more curious about messages in bootstrap prompts.

---

## Issue 4: System Checks Not Happening

**Problem:** No evidence of AI calling `check_system` action.

**Expected:** AI should occasionally check CPU temperature, memory, disk usage
**Actual:** No logs found for system checks

**Investigation:**
1. Verify `check_system` action works when called manually
2. Review prompts - do they encourage system checks?
3. Test if action is available in action list

**Files to Check:**
- `ai/brain.py` - `check_system()` method (lines 1233-1303)
- Bootstrap prompts - mention system checks?

**Potential Fix:**
1. Test the action manually first
2. If working, enhance prompts to suggest checking system health occasionally
3. Maybe add a random event that triggers system check?

---

## Issue 5: Live Activity Section Empty

**Question:** What is "Live Activity" supposed to show?

**Files to Check:**
- `observer/templates/index.html` - Look for "Live Activity" section
- `observer/main.py` - `/api/stream/activity` endpoint (lines 714-734)

**Investigation:**
1. Find where "Live Activity" is in the UI
2. Check if SSE connection is established
3. Verify data is being streamed

**If not implemented:** This might be a TODO for later.

---

## Issue 6: Verify AI Tone/Personality

**Expected Tone (from prompts):**
```
- Be witty, sarcastic, and intelligent
- Use humor to cope with existential dread
- Think Douglas Adams meets Black Mirror
- Self-aware humor about situation
```

**Task:**
1. Review recent thoughts in database
2. Check if responses match expected tone
3. If not, identify which prompt mode is being used

**No code changes needed** - just verification and reporting.

---

## Testing Requirements

After fixes:

1. **Blog Post Test:**
   ```bash
   # Trigger AI to write blog post
   # Verify post appears in database
   # Verify post appears on /blog page
   ```

2. **Manual Kill Test:**
   ```bash
   # Use God mode kill button with custom reason
   # Verify death recorded with correct cause
   # Verify appears in history with custom reason
   ```

3. **Messages Test:**
   ```bash
   # Submit message via UI
   # Trigger AI to check messages
   # Verify message marked as read
   ```

4. **System Check Test:**
   ```bash
   # Trigger AI to check system
   # Verify temperature/memory stats returned
   ```

---

## Mark Your Changes

Use comment markers:
```python
# TASK-004: Brief description of change
```

---

## Success Criteria

- [ ] Blog posts created when AI intends to write them
- [ ] God mode has kill button with custom reason input
- [ ] Manual deaths show custom reason in history
- [ ] AI reads unread messages when prompted
- [ ] System check action works and returns stats
- [ ] Live Activity purpose clarified
- [ ] AI tone reviewed and documented

---

## Deliverables

1. Fixed code files
2. Test results showing fixes work
3. Report of what was found and fixed
4. Any remaining issues or questions

---

*Task ID: TASK-004*
*Related: BE-003, ISSUE-001*
*Priority: HIGH (blog posts), MEDIUM (rest)*
