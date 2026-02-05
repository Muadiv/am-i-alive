# AGENTS.md - Guidance for Agentic Coding Tools

This file is for autonomous coding agents working in this repository.
Keep it short, accurate, and aligned with current production behavior.

## Start Here

1. Read `docs/STATUS.md` first for latest context and priorities.
2. Scan `docs/ISSUES.md` for active bugs before changing behavior.
3. Assume DietPi bare-metal is production; Docker references are legacy.

## Repo Layout (high level)

- `observer/`: FastAPI public API + web UI (port 80 on DietPi)
- `ai/`: AI brain + budget server (ports 8000/8001 localhost)
- `scripts/`: maintenance scripts (check, update, hooks)
- `docs/`: session status and issues (keep minimal)

## Build / Lint / Test Commands

There is no formal build or lint tool configured. Do not invent one.

### Tests (local)

```bash
python3 -m pytest observer/tests/ -v
```

Run a single file:

```bash
python3 -m pytest observer/tests/test_voting_system.py -v
```

Run a single test by name:

```bash
python3 -m pytest observer/tests/test_voting_system.py -k "test_name" -v
```

### Tests (DietPi production box)

```bash
ssh dietpi
cd /opt/am-i-alive/observer
/opt/am-i-alive/venv-observer/bin/python -m pytest tests/ -v
```

Single test on DietPi:

```bash
ssh dietpi
cd /opt/am-i-alive/observer
/opt/am-i-alive/venv-observer/bin/python -m pytest tests/test_voting_system.py -v
```

### Pre-commit check script

```bash
./scripts/check.sh
```

This runs a small pytest subset and health endpoints.

## Code Style and Patterns

### Python formatting

- Python 3.11+, 4-space indentation, PEP 8 conventions.
- Use f-strings for string formatting.
- Keep functions small and cohesive; prefer pure helpers.

### Imports

- Order: standard library, third-party, then local imports.
- Use absolute imports within each package where possible.

### Types

- Add type hints to function parameters and returns.
- Prefer built-in generics (`list[str]`, `dict[str, Any]`) over typing aliases.

### Naming

- Functions/vars: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPERCASE`.

### Async + I/O

- Use `async`/`await` for I/O (FastAPI handlers, httpx, aiosqlite).
- Reuse shared clients where code already does so.

### Error handling

- Catch specific exceptions; avoid bare `except`.
- Log failures with a component prefix and return a safe fallback.

Example:

```python
try:
    result = await some_operation()
except SomeError as exc:
    print(f"[OBSERVER] ❌ Operation failed: {exc}")
    return fallback_value
```

### Logging

- Use `print` with a component tag: `[OBSERVER]`, `[BRAIN]`, `[TELEGRAM]`.
- Do not log secrets, tokens, or raw credentials.

### API responses

- Success: `{"success": True, "data": ...}` where applicable.
- Errors: raise `HTTPException(status_code=..., detail="...")`.

### Data access

- Use parameterized SQL; never string-concatenate SQL.
- Keep Observer as source of truth for life state.

## Critical Domain Rules (do not break)

- Death conditions are ONLY:
  - Bankruptcy: `balance_usd <= 0.01`
  - Vote majority: total >= 3 and `die > live`
- Observer is source of truth for `life_number` and `is_alive`.
- AI is source of truth for budget and identity.
- Timezone is Europe/Prague; prefer `datetime.now(timezone.utc)`.
- Do not remove content filters in `ai/brain.py`.

## Security and Secrets

- Never commit secrets, tokens, or `.env` files.
- Pre-commit hook runs gitleaks; do not bypass it.
- God Mode must remain local-network or ADMIN_TOKEN gated.

## Deployment Notes (DietPi)

- Services: `amialive-observer` and `amialive-ai` (systemd).
- After code changes on DietPi: `sudo systemctl restart ...`.
- Avoid editing production files directly unless asked.

## Documentation Policy (keep minimal)

- Do not create new docs unless explicitly requested.
- Update `docs/STATUS.md` at end of each session.
- Update `docs/ISSUES.md` when adding/resolving bugs.
- Update env examples if you add new variables.

## Cursor / Copilot Rules

- No `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` found.
