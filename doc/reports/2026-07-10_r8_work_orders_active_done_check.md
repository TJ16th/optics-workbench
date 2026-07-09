# work_orders active/done 棚卸し報告

日付: 2026-07-10

## 対象

- 指示書: `doc/work_orders/done/codex_r8_work_orders_active_done_check.md`
- 対象ディレクトリ:
  - `doc/work_orders/active/`
  - `doc/work_orders/done/`
  - `doc/reports/`
  - `AGENTS.md`

## 判定方針

- 対応する `doc/reports/` の完了報告が存在するものは `done/` へ移動した。
- 大きい統合指示書は、配下タスクの完了報告と対応コミットが揃っている場合のみ `done/` へ移動した。
- `codex_performance_work_order.md` は、性能改善タスク0-7の本体が未完であり、既存レポートでも今後作業として参照されているため `active/` に残した。

## done へ移動した指示書

| 指示書 | 根拠 |
|---|---|
| `codex_check_dynamic_keys_and_ci_scope.md` | `2026-07-10_check_dynamic_keys_and_ci_scope.md` |
| `codex_close_resync_task.md` | `e0eb254 docs: close layout resync task` と AGENTS.md 反映済み |
| `codex_education_preview_paths_fix.md` | `2026-07-10_education_preview_paths_fix.md` |
| `codex_fix_i18n_check_groups.md` | `2026-07-10_fix_i18n_check_groups.md` |
| `codex_github_publication_work_order.md` | G1-G5 reports: `2026-07-09_g1...` through `2026-07-09_g5...` |
| `codex_q1_layout_view_rendering_quality.md` | `2026-07-10_q1_layout_view_rendering_quality.md` |
| `codex_q1b_lod_ray_symmetry.md` | `2026-07-10_q1b_lod_ray_symmetry.md` |
| `codex_r2_p003_ois_g_validity.md` | `2026-07-10_r2_p003_ois_g_validity.md` |
| `codex_restart_processes.md` | `2026-07-10_restart_processes.md` |
| `codex_restart_report_and_dirty_flag.md` | `2026-07-10_restart_processes.md` と AGENTS.md の dirty/reporting rule |
| `codex_resync_before_layout_view.md` | `2026-07-10_resync_before_layout_view.md` |
| `codex_ui_phase3_followup_check.md` | `2026-07-09_ui_phase3_followup_curvature.md` |
| `codex_ui_phase3_followup2.md` | `2026-07-09_ui_phase3_followup2_asphere.md`, `2026-07-09_ui_phase3_followup2_aperture_runtime.md` |
| `codex_ui_phase3_followup3.md` | `2026-07-09_ui_phase3_followup3_stability_and_variables.md` |
| `codex_ui_phase3_p3_2_precheck.md` | `2026-07-09_ui_phase3_p3_2_precheck.md` |
| `codex_ui_phase3_work_order.md` | P3-0 through P3-5 reports and follow-up reports exist |
| `codex_ui_ray_path_verification.md` | `2026-07-09_ui_ray_path_verification.md` |
| `codex_verify_fix_and_build_info.md` | `2026-07-10_verify_fix_and_build_info.md` |
| `codex_r8_work_orders_active_done_check.md` | 本レポート |

## active に残した指示書

| 指示書 | 理由 |
|---|---|
| `codex_performance_work_order.md` | 性能改善タスク0-7の本体が未完。`issues_backlog.md` や過去レポートでも今後作業として参照されている。 |

## AGENTS.md 確認

AGENTS.md には既に以下の趣旨のルールが存在したため、追加変更は不要と判断した。

- 有効な作業指示は `doc/work_orders/active/` のみ。
- 完了済み指示書は `done/` に置く。
- 実装報告は `doc/reports/YYYY-MM-DD_<件名>.md` に残す。
- 完了主張には根拠コミット、テストファイル名、テスト結果を明記する。
- コード変更を伴わない指示書・報告書・AGENTS.mdのみのコミットは、プロセス再起動確認の対象に含めない。

## 最終状態

- `active/` には未完了の `codex_performance_work_order.md` のみが残る想定。
- `done/` には完了済み指示書を集約済み。
- 本作業はドキュメント整理のみであり、エンジン/API/UIの実行コード変更はない。
