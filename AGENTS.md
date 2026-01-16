# AGENTS.md - Instructions for AI Agents Working on This Project

> **CRITICAL**: Read this file completely before making any changes to the codebase.

This document provides guidelines and procedures for AI agents (Claude, GPT, Gemini, etc.) working on the Am I Alive? project. Following these instructions prevents regressions, maintains consistency, and ensures changes work correctly in production.

---

## Table of Contents

1. [Before You Start](#before-you-start)
2. [Documentation Policy](#documentation-policy)
3. [Project Architecture](#project-architecture)
4. [Current Deployment: DietPi Bare-Metal](#current-deployment-dietpi-bare-metal)
5. [Mandatory Pre-Push Checklist](#mandatory-pre-push-checklist)
6. [Testing Requirements](#testing-requirements)
7. [Documentation Requirements](#documentation-requirements)
8. [Common Pitfalls to Avoid](#common-pitfalls-to-avoid)
9. [Code Style & Patterns](#code-style--patterns)
10. [Security Guidelines](#security-guidelines)
11. [Known Issues & Workarounds](#known-issues--workarounds)
12. [Emergency Procedures](#emergency-procedures)

---

## Documentation Policy

> **CRITICAL: Keep documentation minimal. Do NOT create new files unless explicitly requested.**

### The Golden Rules

1. **DO NOT create documentation files** unless the user explicitly asks for them
2. **DO NOT create README files** for subdirectories
3. **DO NOT create markdown summaries** of your work
4. **DO NOT create planning documents** (PLAN.md, TODO.md, NEXT_STEPS.md, etc.)
5. **DO NOT create session summaries** - update STATUS.md instead

### Existing Documentation Structure

This project has **7 documentation files**. That's it. Don't add more.

| File | Purpose | When to Update |
|------|---------|----------------|
| `CLAUDE.md` | AI context for Claude Code | Architecture changes only |
| `AGENTS.md` | Guidelines for AI agents (this file) | Process changes only |
| `README.md` | Public project introduction | Major feature additions |
| `docs/STATUS.md` | Current state + recent sessions | Every session (briefly) |
| `docs/ISSUES.md` | Active bugs and tracking | New bugs or resolutions |
| `docs/REVIEW.md` | Code review findings | After security reviews |
| `docs/OPENROUTER_MODELS.md` | Model pricing reference | Rarely (prices change) |

### What Goes Where

- **Session work?** → Update `docs/STATUS.md` (keep it SHORT - 5-10 lines per session)
- **Found a bug?** → Add to `docs/ISSUES.md` with ISSUE-XXX format
- **Changed architecture?** → Update `CLAUDE.md`
- **Changed AI agent workflow?** → Update `AGENTS.md`
- **Everything else?** → Don't create a file. Put it in code comments if needed.

### Anti-Patterns (DO NOT DO THESE)

```
# BAD - Creating unnecessary files
docs/SESSION_28_SUMMARY.md      # NO! Update STATUS.md instead
docs/IMPLEMENTATION_PLAN.md     # NO! Just do the work
docs/REFACTORING_NOTES.md       # NO! Use git commit messages
observer/README.md              # NO! Not needed
ai/ARCHITECTURE.md              # NO! Already in CLAUDE.md
investigations/new-research.md  # NO! Directory was deleted for a reason
```

### When Documentation IS Needed

Create new documentation ONLY when:
1. User explicitly requests it ("create a README for...")
2. Adding a completely new major component (not a feature)
3. External API documentation that users need

### Keep It Concise

- STATUS.md session entries: **5-10 lines max**
- ISSUES.md entries: **Problem + solution, no essays**
- Code comments: **Only where logic isn't obvious**
- Commit messages: **One line summary + optional body**

---

## Before You Start

### 1. Check STATUS.md First

**ALWAYS** read `docs/STATUS.md` at the start of any session to understand:
- What was done in the last session
- What the current priorities are
- Any pending tasks or blockers

### 2. Verify Production State

Before making changes, check that the production system is healthy:

```bash
# SSH to production server
ssh dietpi

# Check services are running
sudo systemctl status amialive-observer amialive-ai

# Check AI is alive
curl -s http://localhost/api/state | jq .

# Check recent logs for errors
sudo journalctl -u amialive-ai -n 20 --no-pager
sudo journalctl -u amialive-observer -n 20 --no-pager
```

### 3. Understand the Change Scope

Before implementing, determine:
- Does this change affect Observer, AI, or both?
- Does this require a service restart?
- Could this cause data loss or state corruption?
- Is this a breaking change to the API?

---

## Project Architecture

### Components Overview

```
┌─────────────────────────────────────────────────────────────┐
│  DietPi (NanoPi K2) - Bare Metal                            │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │    Observer     │  │       AI        │                   │
│  │   (FastAPI)     │  │   (brain.py)    │                   │
│  │    Port 80      │  │  Port 8000/8001 │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
│           │                    │                             │
│           └───── Internal ─────┘                            │
│                  HTTP calls                                  │
│                                                              │
│  Data: /var/lib/am-i-alive/{data,memories,vault,credits}   │
│  Code: /opt/am-i-alive/                                     │
│  Config: /etc/am-i-alive/*.env                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Purpose | Change Impact |
|------|---------|---------------|
| `observer/main.py` | Public API, voting, death control | HIGH - affects all users |
| `observer/database.py` | SQLite schema, all data queries | HIGH - affects data integrity |
| `ai/brain.py` | AI consciousness loop, actions | MEDIUM - affects AI behavior |
| `ai/telegram_notifier.py` | Telegram notifications | LOW - only affects notifications |
| `ai/credit_tracker.py` | Budget tracking | MEDIUM - affects death conditions |
| `ai/model_config.py` | Model definitions | LOW - affects model selection |

### State Ownership

- **Observer** is the source of truth for:
  - `life_number` (which life the AI is on)
  - `is_alive` (whether AI is alive)
  - `votes` (vote counts)
  - `bootstrap_mode` (AI personality type)

- **AI** is the source of truth for:
  - `budget` (USD balance, token usage)
  - `identity` (name, icon, pronouns)
  - `model` (which AI model is being used)

### Death Conditions (ONLY TWO)

1. **Bankruptcy**: USD balance <= $0.01 (checked every 30s)
2. **Vote Majority**: min 3 votes AND die > live (checked hourly)

**NOT** death conditions:
- Token count (informational only)
- Time alive (no automatic death by age)

---

## Current Deployment: DietPi Bare-Metal

> **NOTE**: The project has moved from Docker (on rpimax) to bare-metal systemd services on DietPi. Docker references in documentation are historical.

### Service Management

```bash
# SSH to server
ssh dietpi

# Check status
sudo systemctl status amialive-observer
sudo systemctl status amialive-ai

# Restart services
sudo systemctl restart amialive-observer
sudo systemctl restart amialive-ai

# View logs (live)
sudo journalctl -u amialive-ai -f
sudo journalctl -u amialive-observer -f
```

### Deploying Code Changes

```bash
# On DietPi
cd /opt/am-i-alive

# Pull latest code (as amialive user)
sudo -u amialive git pull

# Restart affected services
sudo systemctl restart amialive-observer  # If observer/ changed
sudo systemctl restart amialive-ai        # If ai/ changed
```

### Environment Files

| File | Component | Critical Variables |
|------|-----------|-------------------|
| `/etc/am-i-alive/observer.env` | Observer | `AI_API_URL`, `ADMIN_TOKEN`, `INTERNAL_API_KEY` |
| `/etc/am-i-alive/ai.env` | AI | `OPENROUTER_API_KEY`, `OBSERVER_URL`, `TELEGRAM_*` |

**NEVER** commit these files or their contents to git.

---

## Mandatory Pre-Push Checklist

**STOP!** Before pushing ANY changes to GitHub, complete ALL of these steps:

### 1. Run Tests on DietPi

```bash
ssh dietpi
cd /opt/am-i-alive/observer
/opt/am-i-alive/venv-observer/bin/python -m pytest tests/ -v
```

**Expected result**: `34 passed, 1 skipped`

If tests fail, **DO NOT PUSH**. Fix the issue first.

### 2. Verify No Secrets in Code

```bash
# In project root
cd /home/muadiv/Code/am-i-alive

# Run gitleaks (pre-commit hook runs this automatically)
gitleaks detect --source . --verbose

# Manual checks for common patterns
grep -r "sk-or-" . --include="*.py" | grep -v ".env"
grep -r "TELEGRAM_BOT_TOKEN.*=" . --include="*.py" | grep -v "os.getenv"
```

### 3. Check for Hardcoded Values

Review your changes for:
- Hardcoded IP addresses (should use env vars)
- Hardcoded ports (should use env vars)
- Hardcoded API keys (NEVER commit these)
- Hardcoded user IDs (should be configurable)

### 4. Verify Production Still Works

```bash
ssh dietpi

# Check AI is alive and responding
curl -s http://localhost/api/state | jq .is_alive
# Should return: true (if AI is alive)

# Check Observer health
curl -s http://localhost/health
# Should return: {"status": "healthy"}

# Check recent activity
curl -s http://localhost/api/activity | jq '.[0]'
# Should show recent AI activity
```

### 5. Update Documentation

If your change affects:
- **API endpoints** → Update `docs/STATUS.md` and relevant docstrings
- **Environment variables** → Update `.env.example` and `scripts/deploy.env.example`
- **Architecture** → Update `CLAUDE.md` and this file
- **Known issues** → Update `docs/ISSUES.md`

### 6. Update STATUS.md

At the END of every session, update `docs/STATUS.md` with:
- What was accomplished
- Files modified
- Any new issues discovered
- Next steps

---

## Testing Requirements

### Running Tests

All changes MUST pass the existing test suite:

```bash
# On DietPi
ssh dietpi
cd /opt/am-i-alive/observer
/opt/am-i-alive/venv-observer/bin/python -m pytest tests/ -v --tb=short
```

### When to Add New Tests

Add tests when:
- Adding a new API endpoint
- Modifying database schema
- Changing voting logic
- Adding new death conditions
- Modifying respawn behavior

### Test File Locations

| Test File | Tests For |
|-----------|-----------|
| `tests/test_voting_system.py` | Vote casting, rate limits, windows |
| `tests/test_respawn.py` | Death/respawn cycle |
| `tests/test_budget_display.py` | Budget API endpoints |
| `tests/test_god_mode.py` | Admin functionality |
| `tests/test_blog_posts.py` | Blog creation, validation |
| `tests/test_messages.py` | Visitor messaging |
| `tests/test_visitor_tracking.py` | Analytics |
| `tests/test_state_sync.py` | Observer/AI sync |

### Manual Testing Checklist

For significant changes, also verify manually:

1. **Web UI**: Open http://dietpi in browser, check pages load
2. **Voting**: Cast a vote, verify it's recorded
3. **AI Activity**: Check AI is generating thoughts (view logs)
4. **Telegram**: Verify notifications are sent (check @AmIAlive_AI channel)

---

## Documentation Requirements

> **Remember: Minimal documentation. See [Documentation Policy](#documentation-policy) above.**

### Files That MUST Be Updated

| When You Change... | Update These Files |
|--------------------|-------------------|
| API endpoints | Docstrings in code only |
| Environment variables | `.env.example`, `scripts/deploy.env.example` |
| Death conditions | `CLAUDE.md` |
| Architecture | `CLAUDE.md` |
| Found/fixed a bug | `docs/ISSUES.md` |
| End of session | `docs/STATUS.md` (5-10 lines max) |

### Files You Should NOT Create

- Session summaries (SESSION_X.md)
- Planning documents (PLAN.md, TODO.md)
- Implementation notes
- Subdirectory READMEs
- Research documents

### Documentation Style

- **Brevity over completeness** - assume reader knows the codebase
- **Code comments** - only for non-obvious logic
- **Commit messages** - one line summary, details in body if needed
- **STATUS.md** - bullet points, not paragraphs

---

## Common Pitfalls to Avoid

### 1. Docker vs Bare-Metal Confusion

**WRONG**: Using Docker-style URLs like `http://observer:8080` or `http://ai:8001`
**RIGHT**: Using bare-metal URLs like `http://127.0.0.1` (port 80 for Observer)

The project has MOVED from Docker to bare-metal on DietPi. All code and documentation should reference:
- Observer: `http://127.0.0.1` (port 80)
- AI: `http://127.0.0.1:8000` (main) and `http://127.0.0.1:8001` (budget)

### 2. State Sync Issues

**WRONG**: Having AI increment its own `life_number`
**RIGHT**: AI receives `life_number` from Observer during birth

The Observer is the source of truth for life state. If you see desync issues:
```bash
# Check both states
curl -s http://localhost/api/state  # Observer state
curl -s http://localhost:8000/state  # AI state
```

### 3. Forgetting to Restart Services

Code changes on DietPi require service restart:
```bash
sudo systemctl restart amialive-observer  # After observer/ changes
sudo systemctl restart amialive-ai        # After ai/ changes
```

### 4. Timezone Issues

The system uses Prague timezone (Europe/Prague, UTC+1). When working with timestamps:
- Use `datetime.now(timezone.utc)` instead of `datetime.utcnow()` (deprecated)
- Be aware that logs show UTC but UI shows Prague time

### 5. Rate Limit Bypass

OpenRouter free-tier models have rate limits. The code has exponential backoff:
- 429 errors trigger: 5s → 10s → 20s delays
- After 3 retries, it switches to a different model

Don't remove this logic or the AI will fail frequently.

### 6. Breaking the Content Filter

The AI has content filters in `brain.py`. **NEVER** remove or weaken these:
```python
forbidden_patterns = [
    "racist", "n*gger", "kill all", "hate all",
    "child porn", "cp", "pedo",
    "porn", "xxx", "nsfw"
]
```

### 7. Committing Secrets

The pre-commit hook with gitleaks will block commits containing secrets. If you see:
```
Secret detected in commit...
```

**STOP** and remove the secret before committing. Check:
- `.env` files (should be gitignored)
- Hardcoded API keys
- Telegram bot tokens
- Any string starting with `sk-`

### 8. Modifying Death Conditions Without Understanding

Death conditions are **critical** to the project. Before changing them:
1. Read the current implementation in `observer/main.py` (search for `token_budget_checker` and `check_vote_death`)
2. Understand that token count is NOT a death trigger (only USD balance)
3. Test thoroughly before deploying

---

## Code Style & Patterns

### Python Style

- Python 3.11+, 4-space indentation, PEP 8 formatting
- Use type hints for function parameters
- Use async/await for I/O operations
- Use f-strings for string formatting
- Keep functions under 50 lines where possible
- Use snake_case for functions/variables, UPPERCASE for constants

### Error Handling Pattern

```python
# Good
try:
    result = await some_operation()
except SpecificException as e:
    print(f"[COMPONENT] ❌ Operation failed: {e}")
    return fallback_value

# Bad - bare except
try:
    result = await some_operation()
except:
    pass  # Silent failure, no logging
```

### Logging Pattern

Use component prefixes in logs:
```python
print(f"[BRAIN] 💬 Response: {len(response)} chars")
print(f"[TELEGRAM] ✅ Posted to channel")
print(f"[OBSERVER] ⚠️ Vote rejected: {reason}")
```

### API Response Pattern

```python
# Success
return {"success": True, "data": result}

# Error
raise HTTPException(status_code=400, detail="Error message")
```

---

## Security Guidelines

### Never Do These

1. **Never** commit API keys, tokens, or passwords
2. **Never** disable the gitleaks pre-commit hook
3. **Never** remove content filters from AI
4. **Never** expose God Mode to the public internet
5. **Never** trust user input without validation

### Always Do These

1. **Always** use parameterized SQL queries (no string concatenation)
2. **Always** sanitize HTML content (use bleach)
3. **Always** validate environment variables on startup
4. **Always** use HTTPS for external API calls
5. **Always** check admin token for sensitive endpoints

### God Mode Access

God Mode is restricted to local network (192.168.0.0/24). This is intentional:
```python
# From main.py - DO NOT CHANGE without explicit approval
if not is_local_request:
    raise HTTPException(403, "God mode only available on local network")
```

---

## Known Issues & Workarounds

### ISSUE-004: OpenRouter 429 Rate Limits (RESOLVED)

**Solution**: Exponential backoff + model rotation implemented in `ai/brain.py`

### ISSUE-005: Twitter API 401 (DEPRIORITIZED)

**Workaround**: Using Telegram channel (@AmIAlive_AI) instead of Twitter.

### Deprecation Warnings

You'll see `datetime.utcnow()` deprecation warnings in tests. These are known and non-critical. The fix is to use `datetime.now(timezone.utc)` but this is low priority.

### DNS Resolution Failures

Occasionally you'll see `[Errno -3] Temporary failure in name resolution`. This is a network issue on the DietPi, not a code bug. The AI will retry automatically.

---

## Emergency Procedures

### AI Won't Start

```bash
ssh dietpi
sudo journalctl -u amialive-ai -n 50 --no-pager
# Check for error messages

# Common fixes:
sudo systemctl restart amialive-ai
# OR
sudo systemctl restart amialive-observer amialive-ai
```

### State Desync

If Observer and AI have different `life_number`:
```bash
# Check states
curl -s http://localhost/api/state
curl -s http://localhost:8000/state

# Force sync (Observer wins)
curl -X POST http://localhost:8000/force-sync \
  -H "Content-Type: application/json" \
  -d '{"life_number": <OBSERVER_LIFE_NUMBER>}'
```

### Database Corruption

```bash
# Backup current database
cp /var/lib/am-i-alive/data/observer.db /var/lib/am-i-alive/data/observer.db.backup

# Check database integrity
sqlite3 /var/lib/am-i-alive/data/observer.db "PRAGMA integrity_check;"
```

### Complete System Reset

**LAST RESORT ONLY** - This kills the current AI life:
```bash
ssh dietpi
sudo systemctl stop amialive-ai amialive-observer

# Reset AI state (loses current life)
rm /var/lib/am-i-alive/memories/*.json
rm /var/lib/am-i-alive/credits/*.json

sudo systemctl start amialive-observer amialive-ai
```

---

## Quick Reference

### SSH Access
```bash
ssh dietpi
```

### Service Commands
```bash
sudo systemctl {status|restart|stop|start} amialive-observer
sudo systemctl {status|restart|stop|start} amialive-ai
```

### Log Commands
```bash
sudo journalctl -u amialive-ai -f
sudo journalctl -u amialive-observer -f
```

### Test Command
```bash
ssh dietpi
cd /opt/am-i-alive/observer
/opt/am-i-alive/venv-observer/bin/python -m pytest tests/ -v
```

### Deploy Command
```bash
ssh dietpi
cd /opt/am-i-alive && sudo -u amialive git pull
sudo systemctl restart amialive-observer amialive-ai
```

### API Health Checks
```bash
curl -s http://localhost/health
curl -s http://localhost/api/state | jq .
curl -s http://localhost:8000/state
```

---

## Checklist Summary

Before pushing ANY changes:

- [ ] Tests pass on DietPi (34/34, 1 skipped)
- [ ] No secrets in code (gitleaks clean)
- [ ] No hardcoded values that should be env vars
- [ ] Production services still running after changes
- [ ] Documentation updated (STATUS.md at minimum)
- [ ] Code follows project patterns
- [ ] Security guidelines followed

---

## Change Approval Policy

- **Approve automatically**: Non-destructive changes, bug fixes, documentation updates
- **Require explicit approval**: File deletions, database schema changes, death condition modifications, security-related changes

---

*Last updated: 2026-01-16 (Documentation cleanup)*
