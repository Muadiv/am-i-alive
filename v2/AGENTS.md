# AGENTS.md (v2)

Rules for autonomous coding agents working in `v2/`.

## Start Here

1. Read `v2/STATUS.md`.
2. Read `v2/CODING_STANDARDS.md`.
3. Keep v1 untouched unless explicitly requested.

## Execution Rules

- Keep each file under 300 lines when practical.
- Keep functions small and cohesive.
- Add type hints to new/modified functions.
- Add tests with behavior changes.
- Do not hardcode secrets or env-specific values.
- Respect death invariants and source-of-truth boundaries.

## Delivery Rules

- Work in small increments.
- After each completed part:
  - commit
  - push
  - pull on DietPi
  - run `v2/` tests on DietPi
- Update `v2/STATUS.md` with done/in-progress/waiting.

## Parallel Deployment Constraint

- v1 and v2 must both run until explicit decommission approval.
- No shared DB/data/service names between v1 and v2.
