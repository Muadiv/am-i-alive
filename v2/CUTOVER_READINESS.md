# v2 Cutover Readiness

Use these checks before switching traffic from v1 to v2.

## Required Gates

- v1 and v2 health endpoints respond successfully.
- v2 state and vote-round endpoints respond with valid payloads.
- `v2/` pytest suite passes on DietPi.
- Shadow soak report exists and meets thresholds:
  - minimum iterations: 3 (increase for real cutover)
  - minimum success rate: 99%

## Commands

Run tests:

```bash
/opt/am-i-alive/venv-observer/bin/python -m pytest v2/ -v
```

Run shadow soak sample:

```bash
./v2/deploy/shadow_soak_runner.py --iterations 3 --interval 5
```

Evaluate cutover readiness:

```bash
./v2/deploy/cutover_readiness.py
```

## Note

Keep v1 and v2 running in parallel until cutover is explicitly approved.
