# v2 Roadmap

## Phase 1 - Foundation

- Create `v2` workspace and docs.
- Build minimal `observer_v2` app with config, health, and public state endpoint.
- Add initial pytest coverage for baseline endpoints.

## Phase 2 - Lifecycle Core

- Add lifecycle state machine and persistence.
- Implement birth/death/rebirth flows.
- Enforce death invariants (only bankruptcy and vote_majority).

## Phase 3 - Voting v2

- Implement 24h vote rounds.
- Add vote cooldown and anti-abuse fingerprinting.
- Round close adjudication and automatic new round creation.

## Phase 4 - Funding v2

- Static BTC address exposure.
- Donation ledger with idempotent tx ingestion.
- Runway snapshots and support-pressure signals.

## Phase 5 - Agency + Narrative

- Intention planner with priority scoring.
- Memory/scar continuity across lives.
- Timeline moments with meaningful updates.

## Phase 6 - Deployment and Shadow Run

- Deploy as separate DietPi services.
- Keep v1 and v2 alive in parallel.
- Run soak tests, then cutover.
