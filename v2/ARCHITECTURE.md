# v2 Architecture

## Principles

- Observer remains source of truth for life state.
- Death rules are strict and minimal.
- Services are composable and testable.
- Parallel-safe deployment with v1.

## Service Boundaries

1. `observer_v2` (FastAPI)
- Public API for state, voting, timeline, and SSE.
- Internal API for heartbeats and lifecycle events.
- Owns life state, vote rounds, and death decisions.

2. `ai_v2`
- Runs autonomous loop.
- Maintains intentions and action execution.
- Reports moments/heartbeats into observer_v2.

3. `funding_v2` (module in ai_v2 or split later)
- Tracks wallet address and donation events.
- Tracks OpenRouter runway and funding pressure.

## Data Ownership

- `observer_v2`: `life_cycles`, `life_state`, `vote_rounds`, `votes`, `moments`
- `ai_v2`: planning memory, behavior state, private strategy artifacts
- Shared via API only, never direct DB coupling.

## v2 Initial Runtime (Parallel with v1)

- `observer_v2`: port 8080
- `ai_v2`: port 8100 (localhost)
- `budget_v2`: port 8101 (localhost)

## Security

- Internal endpoints require `X-Internal-Key`.
- Admin endpoints require `ADMIN_TOKEN`.
- Trust forwarding headers only from trusted proxy ranges.
