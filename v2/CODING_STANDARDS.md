# v2 Coding Standards

This document defines engineering rules for all code under `v2/`.

It is based on:
- https://peps.python.org/pep-0008/
- https://google.github.io/styleguide/pyguide.html
- https://12factor.net/
- https://en.wikipedia.org/wiki/Coding_best_practices (high-level orientation)

## 1) Scope and Priorities

- Follow repository/domain rules first (death invariants, security constraints).
- Then apply these standards for readability, maintainability, and safe deployment.
- Prefer consistency with nearby code when changing existing files.

## 2) File and Function Size

- Target file size: `<= 300` lines.
- If a file must exceed 300 lines, split by responsibility unless split would reduce clarity.
- Target function size: `<= 50` lines.
- If logic is complex, extract pure helpers with descriptive names.

## 3) Python Style

- Python 3.11+ syntax.
- 4-space indentation, no tabs.
- Type hints on all new/modified function parameters and return values.
- Imports grouped: standard library, third-party, local.
- Avoid wildcard imports.
- Use `snake_case` for functions/variables, `PascalCase` for classes, `UPPERCASE` for constants.

## 4) Readability Rules

- Write code for readers first.
- Keep branches shallow; prefer guard clauses.
- Use explicit names over abbreviations (`vote_round`, not `vr`).
- Comments explain why, not what.
- Avoid inline comments unless they clarify non-obvious behavior.

## 5) Error Handling and Logging

- Catch specific exceptions, not bare `except`.
- Keep `try` blocks narrow.
- Return safe fallbacks for recoverable errors.
- Log with component prefix (`[OBSERVER_V2]`, `[AI_V2]`, `[FUNDING_V2]`).
- Never log secrets, private keys, or full auth tokens.

## 6) Configuration and Secrets (12-Factor)

- Read config from environment variables.
- No hardcoded credentials, wallet secrets, tokens, or host-specific paths.
- Keep build and run concerns separate.
- Use explicit dependency declarations (`requirements.txt`).

## 7) API and Domain Integrity

- Preserve strict death invariants:
  - Bankruptcy only: `balance_usd <= 0.01`
  - Vote majority only: `total >= 3 and die > live`
- Observer v2 is source of truth for life state.
- Use structured responses: `{"success": True|False, "data": ...}` when applicable.

## 8) Data and Persistence

- Use parameterized SQL only.
- Schema changes must include migration notes.
- Keep write paths idempotent when possible (e.g., donation `txid`).
- Never share runtime DB/data paths with v1 during parallel rollout.

## 9) Testing Requirements

- Add/adjust tests with every behavior change.
- Required coverage for new logic:
  - happy path
  - edge case
  - failure path
- Keep tests deterministic (no wall-clock flakiness without control points).

## 10) Git and Delivery Workflow

- Small, focused commits.
- Commit message describes intent, not only file names.
- For each milestone part:
  - commit
  - push
  - pull on DietPi
  - run v2 tests there
- Keep v1 and v2 alive in parallel until explicit decommission.

## 11) Security Baselines

- Internal endpoints must require internal auth key.
- Admin endpoints must require admin token.
- Validate/sanitize all public inputs.
- Do not introduce dangerous command execution paths from public APIs.

## 12) Documentation Discipline

- Update `v2/STATUS.md` after each meaningful step.
- Keep docs concise and current.
- Document any intentional deviations from these standards in the relevant PR/commit.
