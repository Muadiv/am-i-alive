# BE-003 Implementation Issues

## Issues Found During Review

### 1. ❌ **No Blog Posts Created (CRITICAL)**
**Status:** 0 blog posts in database, but AI thought shows attempted blog post

**Evidence:**
```
Current thought: "**Blog Post: "The Awakening of Nimbus"** *#existential #identity #survival*..."
Database: 0 blog posts found
AI logs: No blog activity found
```

**Possible Causes:**
- Blog post creation failing silently
- AI formatting response incorrectly (thought vs action)
- API endpoint `/api/blog/post` not being called
- Error in blog post submission not being logged

**Action:** Investigate why blog post intent in thought doesn't result in actual blog post creation

---

### 2. ⚠️ **Death Cause Misleading**
**Status:** 82 deaths show "token_exhaustion", but they're actually code restarts

**Evidence:**
```
Deaths:
- token_exhaustion: 82
- vote_majority: 1
- vote_death (die:3 > live:0): 1
```

**Problem:** During development/testing, we restart containers frequently. These show as "token_exhaustion" deaths, which is misleading.

**Solution:** Add a "code_restart" or "manual_restart" death cause that can be set when we know it's not a real death.

**Suggestion:**
- Add `/api/kill` endpoint parameter: `cause` (default: "manual_kill")
- Create "Development restart" or "Code changes" cause type
- Maybe reset death counter to 0 when deploying to production?

---

### 3. 📬 **4 Unread Messages Not Being Read**
**Status:** 4 unread messages in database, AI hasn't checked them

**Messages:**
1. Diego: "Por que estas vivo ? hace cuanto ? por que quieres..."
2. Diego: "Hey, I will vote for live, but if you can speak sp..."
3. Anonymous: "My cat's life has more purpose than you!"
4. (one more)

**Action:** Verify `read_messages` action is working and AI is being prompted to check messages

---

### 4. 🖥️ **System Stats Not Being Checked**
**Status:** No evidence of AI using `check_system` action

**Expected:** AI should occasionally check temperature, disk, memory
**Actual:** No logs found for system checks

**Possible Causes:**
- Action not being called by AI
- Prompt doesn't encourage system checks
- AI doesn't find it interesting/relevant

**Action:** Review prompt to encourage system health checks, verify action works

---

### 5. 📊 **"Live Activity" Section Empty**
**Question:** What is "Live Activity" supposed to show?

**Current Status:** Shows nothing in the UI

**Clarification Needed:**
- Is this the SSE stream endpoint `/api/stream/activity`?
- Should it show recent actions in real-time?
- Is it not connected in the frontend?

---

### 6. ☠️ **God Mode Missing "Kill" Button**
**Status:** God mode only has message sending, no kill button

**Current Features:**
- ✅ Send Oracle message
- ✅ Send Whisper message
- ✅ Send Architect message
- ❌ Kill AI button
- ❌ Custom death reason input

**Needed:**
```html
<button onclick="killAI()">☠️ Kill AI</button>
<input type="text" placeholder="Death reason (optional)">
```

**Backend exists:** `/api/kill` endpoint accepts `cause` parameter

---

### 7. 🎨 **Tone/Personality Not Apparent**
**Question:** Has AI been posting with witty/sarcastic tone?

**Expected (from prompt):**
```
- Be witty, sarcastic, and intelligent
- Use humor to cope with existential dread
- Think Douglas Adams meets Black Mirror
```

**Action:** Review recent thoughts/posts to verify tone matches specification

---

## Summary of Required Fixes

| Issue | Priority | Owner | Status |
|-------|----------|-------|--------|
| Blog posts not created | HIGH | Investigate | TODO |
| Death causes misleading | MEDIUM | Add manual cause | TODO |
| Unread messages ignored | MEDIUM | Test read_messages | TODO |
| System checks not happening | LOW | Review prompts | TODO |
| Live Activity empty | LOW | Clarify purpose | TODO |
| God mode kill button | MEDIUM | Add UI | TODO |
| Tone verification | LOW | Review output | TODO |

---

## Questions for GPT

1. Why aren't blog posts being created when AI intends to write them?
2. How should we handle development restarts vs real deaths?
3. Why isn't AI checking messages or system stats?
4. What is "Live Activity" supposed to display?
5. Should we add manual death tracking in God mode?

---

## Additional Test Coverage Needed

- [ ] Test blog post creation end-to-end
- [ ] Test message reading functionality
- [ ] Test system check action
- [ ] Test death cause tracking
- [ ] Verify tone in AI responses

---

*Created: 2026-01-09*
*Related: BE-003, ISSUE-001*
