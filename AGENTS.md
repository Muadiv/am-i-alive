# Repository Guidelines

## Project Structure & Module Organization
- `ai/` runs the AI loop (`brain.py`) and integrates Gemini/X; containerized via `ai/Dockerfile`.
- `observer/` is the public FastAPI app (`main.py`) with SQLite helpers (`database.py`), templates in `observer/templates/`, and assets in `observer/static/`.
- `proxy/` hosts a mitmproxy script (`intercept.py`) for traffic monitoring and vault capture.
- `docs/` contains project notes; treat `docs/STATUS.md` as the session handoff log.
- `vault/` stores secrets and credentials; keep it private and out of commits.
- `docker-compose.yml` wires the services, networks, and shared volumes.

## Build, Test, and Development Commands
- `docker compose up --build` — build and run all services together.
- `docker compose up observer` — run only the public web server.
- `python -m uvicorn main:app --reload` (from `observer/`) — local dev server without Docker.
- `pip install -r observer/requirements.txt` / `pip install -r ai/requirements.txt` — install per-service deps for local runs.

## Coding Style & Naming Conventions
- Python 3.11, 4-space indentation, PEP 8 formatting, and snake_case for functions/variables.
- Use UPPERCASE for module constants (e.g., `VOTING_WINDOW_SECONDS`).
- Keep templates simple and logic-light; push behavior into Python instead of Jinja.
- Sanitize anything that might surface in public logs or templates.

## Testing Guidelines
- No automated tests are present yet.
- If adding tests, prefer `pytest`, name files `test_*.py`, and focus on API handlers and database behavior.

## Commit & Pull Request Guidelines
- Git history only includes “Initial/First commit,” so no formal convention exists.
- Use short, imperative commit summaries (e.g., “Add vote history page”).
- PRs should describe behavior changes, note config/env updates, and include screenshots for UI changes.

## Security & Configuration Tips
- Use `.env` or compose env vars for `GEMINI_API_KEY`, X/Twitter keys, and `OBSERVER_URL`.
- Never commit `vault/` contents, `.env` files, or private logs.

## Agent-Specific Instructions
- At the start of a session, read `docs/STATUS.md` for current tasks.
- At the end of a session, update `docs/STATUS.md` with progress and next steps.
