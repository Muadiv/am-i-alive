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
- [x] Added planner/intention engine skeleton with persistence, tick/close APIs, and watcher.
- [x] Added public timeline store + events and v2 web homepage.
- [x] Added DietPi systemd deployment assets for observer v2.
- [x] Deployed `amialive-v2-observer` on DietPi (port 8080) in parallel with v1.
- [x] Added automated soak-check script for parallel v1/v2 validation.
- [x] Added shadow soak runner that records structured stability reports.
- [x] Added cutover readiness evaluator and checklist doc.
- [x] Executed shadow soak on DietPi (6 iterations, 100% success).
- [x] Executed cutover readiness evaluator on DietPi (`ready: true`).
- [x] Added explicit cutover/rollback runbook for production switch.
- [x] Added autonomous narrator loop that posts periodic pulse updates.
- [x] Added OpenRouter-backed narration writer with fallback mode.
- [x] Added public vote buttons and in-page vote feedback UI.
- [x] Hardened homepage sync logic with API fallback and error states.
- [x] Improved fallback narration quality with rotating survival-focused variants.
- [x] Reduced default narration frequency and deduplicated repeated intention updates.
- [x] Added force option for narrator tick to validate content updates instantly.
- [x] Filtered legacy repetitive pulses in homepage timeline view.
- [x] Added intent-action-result activity engine with public API and homepage card.
- [x] Added BTC support panel (copy/link/QR), vote countdown, and critical pulse state.
- [x] Removed wallet link button from BTC panel (kept copy + QR only).
- [x] Added Moltbook publish loop and internal publish trigger endpoint.
- [x] Added automatic Moltbook verification challenge solving for post publish flow.
- [x] Added Moltbook reply-reading loop and automatic reply endpoint.
- [x] Upgraded Moltbook post body to include context, URL, and funding call-to-action.
- [x] Expanded Moltbook reply loop to also engage recent feed posts.
- [x] Deepened Moltbook post narrative to highlight bankruptcy risk and stronger funding urgency.
- [x] Added Moltbook publish fallback payload and richer HTTP error diagnostics.
- [x] Added Moltbook retry queue/backoff and public status visibility endpoint.

## In Progress

- [ ] Tune narrator prompt/model and activate API key on DietPi env.

## Waiting

- [ ] Final cutover switch and v1 decommission (after explicit approval).

## Risks / Notes

- v1 and v2 must remain isolated (service names, ports, db/data paths).
- No v1 behavior changes during v2 parallel build unless explicitly requested.
