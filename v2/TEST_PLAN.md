# v2 Test Plan

## Unit Tests

- Config parsing and required env handling.
- Lifecycle transition validation.
- Vote round adjudication function.
- Donation idempotency logic.

## Integration Tests

- Public API baseline (`/health`, `/api/public/state`).
- Vote submission + cooldown enforcement.
- End-of-round close and death decision flow.
- Donation ingestion + status progression.

## End-to-End Tests

- E2E-001: Birth to active state.
- E2E-002: 24h round closes with survival.
- E2E-003: 24h round closes with vote death.
- E2E-004: Bankruptcy death.
- E2E-005: Donation event extends runway state.
- E2E-006: Rebirth continuity stores scar memory.
- E2E-007: v1/v2 parallel isolation.
- E2E-008: restart resilience on systemd restart.

## Release Gates

- All critical tests green.
- Death invariants verified.
- No cross-talk between v1 and v2 state/data.
- 7+ day parallel soak stability before cutover.
