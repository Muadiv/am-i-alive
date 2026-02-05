# v2 Cutover Runbook

This runbook switches production traffic from v1 to v2 with a rollback window.

## Preconditions

- `./v2/deploy/cutover_readiness.py` returns `"ready": true`.
- `amialive-observer` (v1) and `amialive-v2-observer` (v2) are both active.
- Team explicitly approves cutover window.

## Cutover Steps

1. Keep both services running.
2. Update proxy/DNS to route observer traffic to `127.0.0.1:8080`.
3. Verify:
   - `/health`
   - `/api/public/state`
   - `/api/public/vote-round`
   - `/api/public/funding`
4. Keep v1 running in standby for rollback window (recommended 48h).

## Rollback Steps

1. Revert proxy/DNS route back to v1.
2. Confirm v1 endpoints respond normally.
3. Leave v2 running for diagnostics.

## Decommission v1 (after rollback window)

1. Confirm no rollback required.
2. Disable and stop v1 service.
3. Archive v1 logs and snapshots.
