# v2 Deployment (Parallel with v1)

## Objectives

- Keep v1 online while v2 is deployed and validated.
- Isolate v2 code, data, ports, and services.
- Allow safe rollback by preserving v1 unchanged.

## DietPi Paths

- Code: `/opt/am-i-alive-v2`
- Data: `/var/lib/am-i-alive-v2/`
- Env: `/etc/am-i-alive-v2/`

## Service Names

- `amialive-v2-observer`
- `amialive-v2-ai`

Systemd assets committed in:
- `v2/deploy/systemd/amialive-v2-observer.service`
- `v2/deploy/systemd/amialive-v2-observer.env.example`
- `v2/deploy/install_observer_service.sh`
- `v2/deploy/soak_check.sh`
- `v2/deploy/shadow_soak_runner.py`

## Suggested Ports

- `observer_v2`: 8080
- `ai_v2`: 8100 (localhost)
- `budget_v2`: 8101 (localhost)

## Rollout Steps

1. Copy v2 code to DietPi.
2. Configure v2 env files.
3. Install v2 systemd unit files.
4. Start v2 services and verify health endpoints.
5. Expose v2 behind separate subdomain.
6. Run parallel soak tests.
7. Cut over main domain after gates pass.

## Rollback

- If v2 degrades, route traffic back to v1.
- Keep v2 service logs for postmortem.
