# R22 rename audit trail check

Date: 2026-07-10

## Scope

- Work order: `doc/work_orders/active/codex_r22_rename_audit_trail_check.md`
- Related reports:
  - `doc/reports/2026-07-10_r8_work_orders_active_done_check.md`
  - `doc/reports/2026-07-10_r21_rename_files_with_task_numbers.md`

## Audit Result

`git log --oneline --all -- doc/work_orders doc/reports` shows the relevant sequence:

| Commit | Time | Meaning |
|---|---|---|
| `a25d2e0 docs: clean active work order queue` | 2026-07-10 08:38:16 +0900 | R8 cleanup: moved completed work orders from `active/` to `done/` without task-number filename changes. |
| `4794c06 docs: add task numbers to work order filenames` | 2026-07-10 08:45:50 +0900 | R21 rename pass: renamed Q1-Q6/R1/R2/R8 work orders and reports to task-numbered filenames. |
| `238de8e docs: require same-commit work order completion moves` | 2026-07-10 08:52:05 +0900 | R8c process rule: made future completion report and active-to-done moves same-commit requirements. |

The Q1-Q6/R1/R2/R8 filename changes were performed in `4794c06`, not during the R8 cleanup commit. This is now explicit rather than implied.

## Key Evidence

`git show --name-status --oneline 4794c06 -- doc/work_orders doc/reports` shows the task-numbered renames, including:

- `codex_layout_view_rendering_quality.md` -> `codex_q1_layout_view_rendering_quality.md`
- `codex_lod_ray_symmetry.md` -> `codex_q1b_lod_ray_symmetry.md`
- `codex_layout_symbol_scale_check.md` -> `codex_q2_layout_symbol_scale_check.md`
- `codex_right_panel_layout.md` -> `codex_q3_right_panel_layout.md`
- `codex_ray_count_behavior_check.md` -> `codex_q4_ray_count_behavior_check.md`
- `codex_preset_fast_negative_pair.md` -> `codex_q5_preset_fast_negative_pair.md`
- `codex_aberration_chart_standard.md` -> `codex_q6_aberration_chart_standard.md`
- `codex_wavelength_color_check.md` -> `codex_r1_wavelength_color_check.md`
- `codex_p003_ois_g_validity.md` -> `codex_r2_p003_ois_g_validity.md`
- `codex_work_orders_active_done_check.md` -> `codex_r8_work_orders_active_done_check.md`

## Performance Work Order Rename

The active performance work order was renamed as directed:

- Old: `doc/work_orders/active/codex_performance_work_order.md`
- New: `doc/work_orders/active/codex_p0-7_performance_work_order.md`

Markdown references to the old path were updated to the new path.

## AGENTS.md Decision

No further AGENTS.md rule was added in R22. R8c already added the stricter same-commit completion rule. That rule is sufficient for preventing future "report added but work order left in active" drift. The R21 ambiguity was a one-off audit-trail issue and is now documented here.

## Verification

- Confirmed `doc/work_orders/active/codex_p0-7_performance_work_order.md` exists.
- Confirmed the old `codex_performance_work_order.md` path no longer exists.
- Confirmed the audit identified `4794c06` as the rename commit.
- This is documentation/process-only work; no engine, API, or UI runtime code changed.
