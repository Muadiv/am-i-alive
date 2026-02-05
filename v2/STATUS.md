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

## In Progress

- [ ] Persist lifecycle, vote rounds, and donation ledger in v2 database.

## Waiting

- [ ] Implement lifecycle state machine.
- [ ] Implement 24h vote rounds and adjudication.
- [ ] Implement funding engine (BTC static address + donation ledger).
- [ ] Implement planner/intention engine.
- [ ] Build v2 public timeline UI.
- [ ] Deploy v2 on DietPi in parallel with v1.
- [ ] Run shadow soak tests and cutover readiness checks.

## Risks / Notes

- v1 and v2 must remain isolated (service names, ports, db/data paths).
- No v1 behavior changes during v2 parallel build unless explicitly requested.
