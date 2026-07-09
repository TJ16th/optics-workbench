# R21 ファイル番号付きリネーム報告

日付: 2026-07-10

## 対象

- 指示書: `doc/work_orders/active/codex_rename_files_with_task_numbers.md`
- 完了後の指示書: `doc/work_orders/done/codex_r21_rename_files_with_task_numbers.md`
- 対象領域:
  - `doc/work_orders/active/`
  - `doc/work_orders/done/`
  - `doc/reports/`
  - `AGENTS.md`
  - `doc/README.md`

## リネーム対応表

| 番号 | work order 旧名 | work order 新名 | report 旧名 | report 新名 |
|---|---|---|---|---|
| Q1 | `codex_q1_layout_view_rendering_quality.md` | `codex_q1_layout_view_rendering_quality.md` | `2026-07-10_q1_layout_view_rendering_quality.md` | `2026-07-10_q1_layout_view_rendering_quality.md` |
| Q1b | `codex_q1b_lod_ray_symmetry.md` | `codex_q1b_lod_ray_symmetry.md` | `2026-07-10_q1b_lod_ray_symmetry.md` | `2026-07-10_q1b_lod_ray_symmetry.md` |
| Q2 | `codex_q2_layout_symbol_scale_check.md` | `codex_q2_layout_symbol_scale_check.md` | `2026-07-10_q2_layout_symbol_scale_check.md` | `2026-07-10_q2_layout_symbol_scale_check.md` |
| Q3 | `codex_q3_right_panel_layout.md` | `codex_q3_right_panel_layout.md` | `2026-07-10_q3_right_panel_layout.md` | `2026-07-10_q3_right_panel_layout.md` |
| Q4 | `codex_q4_ray_count_behavior_check.md` | `codex_q4_ray_count_behavior_check.md` | `2026-07-10_q4_ray_count_behavior_check.md` | `2026-07-10_q4_ray_count_behavior_check.md` |
| Q5 | `codex_q5_preset_fast_negative_pair.md` | `codex_q5_preset_fast_negative_pair.md` | `2026-07-10_q5_preset_fast_negative_pair.md` | `2026-07-10_q5_preset_fast_negative_pair.md` |
| Q6 | `codex_q6_aberration_chart_standard.md` | `codex_q6_aberration_chart_standard.md` | `2026-07-10_q6_aberration_chart_standard.md` | `2026-07-10_q6_aberration_chart_standard.md` |
| R1 | `codex_r1_wavelength_color_check.md` | `codex_r1_wavelength_color_check.md` | `2026-07-10_r1_wavelength_color_check.md` | `2026-07-10_r1_wavelength_color_check.md` |
| R2 | `codex_r2_p003_ois_g_validity.md` | `codex_r2_p003_ois_g_validity.md` | `2026-07-10_r2_p003_ois_g_validity.md` | `2026-07-10_r2_p003_ois_g_validity.md` |
| R8 | `codex_r8_work_orders_active_done_check.md` | `codex_r8_work_orders_active_done_check.md` | `2026-07-10_r8_work_orders_active_done_check.md` | `2026-07-10_r8_work_orders_active_done_check.md` |
| R21 | `codex_rename_files_with_task_numbers.md` | `codex_r21_rename_files_with_task_numbers.md` | none | `2026-07-10_r21_rename_files_with_task_numbers.md` |

## 対象外

- `codex_misc_light_fixes_batch1.md` and `codex_backlog_batch_registration_2.md` were listed in the work order, but no matching files existed in `active/`, `done/`, or `reports/`.
- `codex_p0-7_performance_work_order.md` remains in `active/`. No task ledger file was present in this repository, and the current work order did not provide a concrete replacement name for this active performance task. It was therefore left unchanged rather than assigning an inferred number.

## 参照更新

- Markdown内の旧work order名と旧report名を新名へ機械的に置換した。
- `doc/README.md` のWork Orders表から完了済みになっていた古い publication work order active行を削除し、report命名例を `YYYY-MM-DD_<task-number>_<subject>.md` に更新した。
- `AGENTS.md` に今後の命名規約を追加した。

## 検証

- 旧Q/R対象名が残っていないことを `rg` で確認した。
- `active/` には未完了の `codex_p0-7_performance_work_order.md` のみが残る想定。
- 本作業はファイル名・参照・ドキュメント規約のみの変更であり、エンジン/API/UIのコード変更はない。
