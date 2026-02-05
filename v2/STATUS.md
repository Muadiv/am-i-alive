# v2 Build Status

Last updated: 2026-02-05

## Done

- [x] Created `v2/` workspace and documentation scaffold.
- [x] Defined architecture, roadmap, deployment strategy, and test plan docs.
- [x] Built minimal `observer_v2` service skeleton.
- [x] Added baseline tests for health and public state endpoints.
- [x] Added lifecycle state machine scaffolding and transition tests.
- [x] Added 24h vote round scaffolding and adjudication tests.
- [x] Added funding scaffolding (static address endpoint + donation ledger module).
- [x] Added v2 coding standards and agent-specific execution rules.
- [x] Persisted life state, open vote round, and donations in v2 SQLite storage.
- [x] Added internal donation ingest endpoint with validation.
- [x] Added lifecycle transition API backed by persistence.
- [x] Added vote casting endpoint, duplicate-vote protection, and due-round close flow.
- [x] Hardened vote/lifecycle edge behavior (dead-state vote lock, born round reset, dead-round close handling).
- [x] Added automatic vote-round watcher for due-round adjudication checks.
- [x] Added funding monitor integration (wallet polling and internal sync endpoint).

## In Progress

- [ ] Build planner/intention engine skeleton with persistence.

## Waiting

- [ ] Build v2 public timeline UI.
- [ ] Deploy v2 on DietPi in parallel with v1.
- [ ] Run shadow soak tests and cutover readiness checks.

## Risks / Notes

- v1 and v2 must remain isolated (service names, ports, db/data paths).
- No v1 behavior changes during v2 parallel build unless explicitly requested.
