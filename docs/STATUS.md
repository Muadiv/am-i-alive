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
