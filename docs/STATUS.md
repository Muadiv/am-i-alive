# Project Status - Am I Alive?

> Check this first when opening the project.

---

## DEPLOYMENT: DietPi (NanoPi K2) - Bare Metal

**Host:** `ssh dietpi` (192.168.10.5, IOT VLAN)
**Observer:** http://dietpi:80
**AI Server:** http://127.0.0.1:8000 (internal)
**Budget Server:** http://127.0.0.1:8001 (internal)

```bash
# Check services
sudo systemctl status amialive-observer amialive-ai

# View logs
journalctl -u amialive-observer -f
journalctl -u amialive-ai -f

# Deploy updates
cd /opt/am-i-alive && sudo -u amialive git pull
sudo systemctl restart amialive-observer amialive-ai
```

---

## REFACTOR PLAN TRACKING
- [x] Inventory oversized modules and map responsibilities
- [x] Define target module breakdown per domain
- [x] Plan extraction order and compatibility shims
- [x] Update imports and wiring plan
- [x] Identify required tests/smoke checks and regressions
- [x] Fix `ai/actions.py` orphaned code and complete ActionExecutor
- [x] Extract AI system stats/monitoring into a service and slim `ai/brain.py`
- [x] Begin splitting `observer/main.py` into routers/services

## SUMMARY OF PROGRESS - 2026-01-28

### Accomplishments
- Added Open-Meteo weather checks via new `check_weather` action and config in [ai/services/weather_service.py](ai/services/weather_service.py:1), [ai/brain.py](ai/brain.py:866), [ai/actions.py](ai/actions.py:91), [ai/config.py](ai/config.py:33), [ai/services/prompt_service.py](ai/services/prompt_service.py:60), and [ai/identity.py](ai/identity.py:174).
- Added weather defaults to [scripts/deploy.env.example](scripts/deploy.env.example:28) and budget API wiring in Observer (commit 0ebfc40).
- Tests: `python -m pytest ai/tests/test_services.py -q` (added weather report coverage).
- Wired Observer budget fetches to the dedicated budget server URL via [observer/config.py](observer/config.py:26), [observer/routes/public.py](observer/routes/public.py:102), and [observer/health.py](observer/health.py:46); documented env update in [scripts/deploy.env.example](scripts/deploy.env.example:23).
- Tests: `cd observer && python -m pytest tests/test_budget_display.py -q` (4 passed; Starlette TemplateResponse deprecation warning).
- Registered custom sqlite datetime adapters/converters and updated tests to pass detect_types flags (removes deprecation warnings) in [observer/database.py](observer/database.py:27), [observer/tests/conftest.py](observer/tests/conftest.py:12), and observer tests.
- Tests: `cd observer && python -m pytest tests/test_voting_system.py -q` (9 passed), `tests/test_messages.py` (6 passed), `tests/test_visitor_tracking.py` (4 passed), `tests/test_god_mode.py` (3 passed).
- Styled the message-to-AI panel to match the vote card and expanded the textbox in [observer/static/style.css](observer/static/style.css:251).
- Tests: `cd observer && python -m pytest tests/test_messages.py -q` (6 passed, sqlite datetime adapter warnings).
- Added last-life survival time and vote outcome stats to the Observer home stats bar in [observer/templates/index.html](observer/templates/index.html:79) with data from [observer/routes/public.py](observer/routes/public.py:55).
- Tests: `cd observer && python -m pytest tests/test_voting_system.py -q` (9 passed, sqlite datetime adapter warnings).
- Disabled direct Telegram posting in [ai/actions.py](ai/actions.py:62); prompts now clarify that only blog posts reach the channel via [ai/services/prompt_service.py](ai/services/prompt_service.py:60) and [ai/identity.py](ai/identity.py:160).
- Added latest blog post preview above thoughts on the home page in [observer/templates/index.html](observer/templates/index.html:100) via [observer/routes/public.py](observer/routes/public.py:53).
- Added previous/next blog navigation with disabled states in [observer/templates/blog_post.html](observer/templates/blog_post.html:62) using neighbors from [observer/database.py](observer/database.py:1474).
- Tests: `python -m pytest ai/tests/test_prompt_service.py -q` (3 passed), `cd observer && python -m pytest tests/test_blog_posts.py -q` (3 passed, sqlite datetime adapter warnings).
- Moved public pages into [observer/routes/public.py](observer/routes/public.py:1) and wired router in [observer/main.py](observer/main.py:1).
- Moved `/api/system/stats` into [observer/routes/system.py](observer/routes/system.py:1) and wired router in [observer/main.py](observer/main.py:1).
- Telegram blog notifications now post to the public channel in [ai/telegram_notifier.py](ai/telegram_notifier.py:253).
- Observer now auto-sends birth payload when AI reports missing life_number in [observer/main.py](observer/main.py:955).
- Extracted AI vital-signs report formatting into [ai/services/system_stats_service.py](ai/services/system_stats_service.py:1) and slimmed [ai/brain.py](ai/brain.py:971).
- Added process snapshot + disk cleanup scan actions via [ai/services/system_check_service.py](ai/services/system_check_service.py:1) and wired them in [ai/brain.py](ai/brain.py:836).
- Documented new tool discovery actions in [ai/services/prompt_service.py](ai/services/prompt_service.py:1) and [ai/identity.py](ai/identity.py:1).
- Replaced remaining `print()` calls with structured logging across AI modules ([ai/brain.py](ai/brain.py:208), [ai/api/command_server.py](ai/api/command_server.py:1)).
- Added refactor checklist tracking to [docs/STATUS.md](docs/STATUS.md:1).
- Tests: `python -m pytest ai/tests/test_prompt_service.py -q` (updated with system stats report coverage).

### Review Notes
- Public/system routes were relocated cleanly; imports use fallback patterns to support running as package or script.
- System stats route now tolerates missing `psutil` in local tests and still returns defaults.

### Planned (AI Aliveness Enhancements)
- Daily rhythm + intention prompt block (behavior cue) in [ai/services/prompt_service.py](ai/services/prompt_service.py:1). ✅
- Flashback memory + body sensation framing per cycle (continuity + embodiment) in [ai/brain.py](ai/brain.py:520). ✅
- Read-only tooling: `check_services` (whitelisted systemd status) + `check_logs` (last N lines) with strict allow-list. ✅
- Lightweight self-model record (traits + 1–2 goals) updated daily and fed into prompts. ✅
- Added service interfaces for observer/chat clients in [ai/services/interfaces.py](ai/services/interfaces.py:1).
- Consolidated action parameter parsing helpers in [ai/services/action_params.py](ai/services/action_params.py:1).
- Extracted oracle messaging workflow into [ai/services/oracle_service.py](ai/services/oracle_service.py:1) and wired it in [ai/brain.py](ai/brain.py:945).
- Added combined system+model health check via [ai/services/health_check_service.py](ai/services/health_check_service.py:1) and [ai/brain.py](ai/brain.py:868).

## SUMMARY OF PROGRESS - 2026-01-27

### Accomplishments
- Added AI budget and sandbox services and wired lifecycle helpers into the brain flow.
- Continued AI refactor wiring via service integration for budget/sandbox and lifecycle helpers.
- Routed AI command server startup through the dedicated [ai/api/command_server.py](ai/api/command_server.py:1).
- Fixed command server import to use [ai/brain.py](ai/brain.py:1) constants.
- Added [ai/services/prompt_service.py](ai/services/prompt_service.py:1) and tests in [ai/tests/test_prompt_service.py](ai/tests/test_prompt_service.py:1).
- Added Observer SSE broadcast service wrapper.
- Improved Telegram diagnostics and channel validation in [ai/telegram_notifier.py](ai/telegram_notifier.py:1).
- Auto-sends birth payload when AI reports missing life_number in [observer/main.py](observer/main.py:955).
- Moved `/api/system/stats` into [observer/routes/system.py](observer/routes/system.py:1) and wired router in [observer/main.py](observer/main.py:1).
- Moved public pages into [observer/routes/public.py](observer/routes/public.py:1) and wired router in [observer/main.py](observer/main.py:1).
- Tests: `python -m pytest ai/tests/test_prompt_service.py -q` (2 passed), `cd observer && python -m pytest tests/test_budget_display.py -q` (4 passed; warnings about sqlite datetime adapter and templating), `cd observer && python -m pytest tests/test_system_checks.py -q` (skipped on Windows), `cd observer && python -m pytest tests/test_state_sync.py -q` (3 passed; sqlite datetime adapter warnings).

### Files Changed
- Modified: `ai/brain.py`, `observer/main.py`
- Added: `ai/core/action_processor.py`, `ai/safety/content_filter.py`, `ai/services/*`, `observer/services/broadcast.py`
- Removed: `ai/core/brain.py`

---

## SUMMARY OF PROGRESS - 2026-01-26

### Accomplishments
- Fixed pytest hanging on exit by closing shared DB and HTTP client fixtures.
- Adjusted oracle forwarding to tolerate optional internal headers.
- Normalized observer health/router imports to work as script or package.
- Tests: 38 passed, 1 skipped (local).

### Files Changed
- Modified: `observer/tests/conftest.py` (fixture cleanup)
- Modified: `observer/main.py` (oracle request kwargs)
- Modified: `observer/health.py` (import fallback)
- Modified: `observer/config.py` (logging import fallback)
- Modified: `observer/database.py` (logging import fallback)

---

## SUMMARY OF PROGRESS - 2026-01-21

### Accomplishments
- **Phase 1 Hardening Complete**: Implemented all security and performance improvements identified in the previous audit.
- **Phase 2 Expansion Complete**: Enhanced project architecture and AI capabilities for bare-metal environment.
- **Database Optimization**: Refactored `observer/database.py` to use connection pooling with a shared persistent connection, improving response times.
- **Trauma Expansion**: Enhanced `ai/identity.py` and state sync to pass detailed past-life stats (survival duration, vote breakdown) to the AI for deeper personality evolution.
- **Hardware Interaction**: Added `control_led` action in `ai/actions.py` allowing the AI to control the blue stat LED on the NanoPi K2.
- **Reliability Fixes**: Fixed 403 Forbidden errors in internal Observer-to-AI communications and resolved indentation issues in the database module.
- **Deployment**: Verified all changes on DietPi; all services are active, healthy, and synced.

### Next Steps (Phase 3 Evolution)
1. **Tool Discovery**: Explore adding more system interaction tools (e.g., process monitoring, disk cleanup).
2. **UI Enhancement**: Update the web dashboard to show the new trauma stats to visitors.
3. **Advanced Memories**: Implement a more structured memory retrieval system based on relevance rather than random fragments.

---

## LAST SESSION: 2026-02-05 (Moltbook rate limit handling)

### What We Did
- Added Moltbook rate-limit persistence to avoid post 429s after restarts.
- Added retry-aware cooldown handling for Moltbook posts/comments.
- Instructed AI to include URLs in Moltbook posts when available.

### Files Changed
- Modified: `ai/brain.py`
- Modified: `ai/core/action_processor.py`
- Modified: `ai/identity.py`
- Modified: `ai/moltbook_client.py`
- Modified: `ai/services/prompt_service.py`
- Modified: `docs/STATUS.md`

---

## LAST SESSION: 2026-01-21 (Phase 2 & Hardening)

### What We Did
- Refactored `observer/database.py` to use a global connection pool, resolving ISSUE-010.
- Enhanced AI trauma prompts to include survival duration and vote counts from previous lives.
- Implemented `control_led` action enabling AI-to-hardware interaction on DietPi.
- Fixed critical 403 Forbidden bugs in internal API communication between Observer and AI.
- Updated `scripts/setup.sh` with `udev` rules for LED access and secured environment file permissions.
- Deployed all changes to DietPi and verified system health with `pytest` (9/9 passed).
- Confirmed AI state sync is working correctly (Life #5 active).

### Files Changed
- Modified: `observer/database.py` (connection pooling, life details)
- Modified: `observer/main.py` (lifespan management, birth payload, headers)
- Modified: `ai/identity.py` (enhanced trauma prompts, bootstrap instructions)
- Modified: `ai/brain.py` (sync handling, LED control implementation)
- Modified: `ai/actions.py` (added control_led action)
- Modified: `scripts/setup.sh` (udev rules, salt generation)
- Modified: `scripts/update.sh` (ownership preservation)
- Modified: `scripts/check.sh` (bare-metal environment detection)
- Modified: `docs/STATUS.md`


---

## CURRENT STATE

### Features Working
- [x] Observer (FastAPI + web UI)
- [x] AI consciousness loop with actions
- [x] Voting system with rate limiting (1 vote/IP/hour)
- [x] Death by bankruptcy (USD <= $0.01) or vote majority
- [x] Respawn system (10-60s delay, memory fragments)
- [x] Blog posts, Telegram channel (@AmIAlive_AI)
- [x] God Mode (local network only)
- [x] Budget tracking (current life + all-time)
- [x] Content filtering
- [x] Test suite: 38/38 passing

### Known Issues
- **ISSUE-005:** Twitter API 401 - using Telegram instead
- See `docs/ISSUES.md` for full list

---

## QUICK REFERENCE

### Death Conditions (ONLY TWO)
1. **Bankruptcy:** USD balance <= $0.01
2. **Vote majority:** min 3 votes AND die > live (hourly check)

### Key Paths (DietPi)
- Code: `/opt/am-i-alive/`
- Data: `/var/lib/am-i-alive/{data,memories,vault,credits}`
- Config: `/etc/am-i-alive/*.env`

### Run Tests
```bash
ssh dietpi
cd /opt/am-i-alive/observer
/opt/am-i-alive/venv-observer/bin/python -m pytest tests/ -v
```

---

## SESSION HISTORY

> Older sessions available in git history. Only recent sessions kept here.

### 2026-01-16 - Documentation Cleanup
- Consolidated docs from 14 files to 7
- Added documentation guidelines

### 2026-01-15 - Budget + Oracle + UI + Filters (Session 27)
- Budget totals split by life (current vs all-time)
- Oracle delivery acknowledgements
- Content filter improvements
- God Mode UI cleanup
- Twitter 401 auto-disable

### 2026-01-15 - Major Fixes + Timezone (Session 26)
- Fixed trauma-informed bootstrap
- Added AI autonomy prompts
- Fixed datetime.utcnow() deprecation
- Deleted dead code (brain_gemini_backup.py)
- Added startup validation

### 2026-01-15 - Telegram Channel + 429 Fix (Session 25)
- Implemented 429 rate limit handling (backoff + model rotation)
- Created Telegram channel @AmIAlive_AI
- Deep codebase review (ISSUE-007 to ISSUE-010)

### 2026-01-14 - DietPi Bare-Metal Setup (Session 23)
- Migrated from Docker on rpimax to bare-metal on DietPi
- Created systemd services
- Configured Cloudflare tunnel

---

*Update this file at end of each session - keep it concise!*
