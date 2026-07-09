# R8c AGENTS same-commit rule report

Date: 2026-07-10

## Scope

- Work order: `doc/work_orders/active/codex_r8c_agents_same_commit_rule.md`
- Target: `AGENTS.md`

## Changes

- Added `Completion Report Move Rule` to `AGENTS.md`.
- The rule says that when a completion report is added under `doc/reports/`, the corresponding work order must be moved from `doc/work_orders/active/` to `doc/work_orders/done/` in the same commit.
- It also explicitly forbids splitting the report commit and the active-to-done move into separate commits.

## Verification

- Confirmed the new AGENTS rule is present.
- This report and the completed work order move are included in the same task commit, following the new rule immediately.

## Notes

- This is a documentation/process-only change. No engine, API, or UI runtime code changed.
