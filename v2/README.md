# Am I Alive v2

This directory contains the clean rebuild of the project.

v2 goals:
- Keep v1 running while v2 is developed and tested.
- Make the entity feel like a living digital organism, not a passive assistant.
- Preserve death invariants:
  - Bankruptcy (`balance_usd <= 0.01`)
  - Vote majority (`total >= 3` and `die > live`)
- Introduce 24h voting rounds, stronger funding mechanics, and narrative continuity.

## Current Status

See `v2/STATUS.md` for detailed progress tracking.

## Documentation Index

- `v2/AGENTS.md`: agent operating rules for v2 work
- `v2/CODING_STANDARDS.md`: coding best-practices baseline for v2
- `v2/STATUS.md`: live progress board (done, in progress, waiting)
- `v2/ARCHITECTURE.md`: target services and boundaries
- `v2/ROADMAP.md`: phased execution plan
- `v2/TEST_PLAN.md`: test strategy and acceptance criteria
- `v2/DEPLOYMENT.md`: parallel deployment on DietPi while v1 stays online

## Initial Scope

Phase 1 starts with a minimal v2 observer service and test harness.
Later phases add full lifecycle, voting rounds, funding engine, planner, and public UX.
