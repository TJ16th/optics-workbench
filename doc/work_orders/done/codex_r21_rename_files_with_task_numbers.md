# 持E��書・報告書ファイルの番号付きリネ�Eム 持E��書�E�Eodex向け�E�E
## 背景

これまでの持E��書�E�Edoc/work_orders/active/` および `done/`�E��E報告書�E�Edoc/reports/`�E��E、�E容に対応する管琁E��号�E�E1, Q2, R1, R8等）が人間�E台帳上にはあるが、ファイル名には反映されてぁE��ぁE��今後�E`codex_<番号>_<冁E��>.md`の命名規則に統一する、E
## 命名規則�E�今後�E新規ファイルにも適用�E�E
```text
codex_<番号>_<冁E��を表す短ぁE��語スラチE��>.md
```

- 番号は小文字（例：`q1`, `r8`, `p3-2`のようにハイフン含む番号はそ�Eまま小文字で�E�、E- 番号が無ぁE��去のタスク�E�E1〜G9、A0〜A3、U1〜U5、P2-0〜P2-5、P3-0〜P3-5等、既に英数字�E管琁E��号を持つも�E�E��E、その番号をそのまま使ぁE��例：`codex_g8_issue_workflow_switch.md`のように、既存ファイルは既にこ�E規則に近い形になってぁE��も�Eが多い�E�、E
## 対象と対応表

以下�E今回の会話で発注されたタスクのぁE��、番号付けされてぁE��が、ファイル名に番号が�EってぁE��ぁE��の一覧、E
| 番号 | 現在のファイル名！Eork_orders�E�E| 対応する報告書�E�Eeports、あれ�E�E�E| リネ�Eム征E|
|---|---|---|---|
| Q1 | `codex_q1_layout_view_rendering_quality.md` | `2026-07-10_q1_layout_view_rendering_quality.md` | `codex_q1_layout_view_rendering_quality.md` |
| Q1-symmetry | `codex_q1b_lod_ray_symmetry.md` | `2026-07-10_q1b_lod_ray_symmetry.md` | `codex_q1b_lod_ray_symmetry.md` |
| Q2 | `codex_q2_layout_symbol_scale_check.md` | `2026-07-10_q2_layout_symbol_scale_check.md` | `codex_q2_layout_symbol_scale_check.md` |
| Q3 | `codex_q3_right_panel_layout.md` | `2026-07-10_q3_right_panel_layout.md` | `codex_q3_right_panel_layout.md` |
| Q4 | `codex_q4_ray_count_behavior_check.md` | `2026-07-10_q4_ray_count_behavior_check.md` | `codex_q4_ray_count_behavior_check.md` |
| Q5 | `codex_q5_preset_fast_negative_pair.md` | `2026-07-10_q5_preset_fast_negative_pair.md` | `codex_q5_preset_fast_negative_pair.md` |
| Q6 | `codex_q6_aberration_chart_standard.md` | `2026-07-10_q6_aberration_chart_standard.md` | `codex_q6_aberration_chart_standard.md` |
| R1 | `codex_r1_wavelength_color_check.md` | `2026-07-10_r1_wavelength_color_check.md` | `codex_r1_wavelength_color_check.md` |
| R2 | `codex_r2_p003_ois_g_validity.md` | `2026-07-10_r2_p003_ois_g_validity.md` | `codex_r2_p003_ois_g_validity.md` |
| R8 | `codex_r8_work_orders_active_done_check.md` | �E�未完亁E��ら無し！E| `codex_r8_work_orders_active_done_check.md` |
| R9-13 | `codex_misc_light_fixes_batch1.md` | �E�未完亁E��ら無し！E| `codex_r9-13_misc_light_fixes_batch1.md` |
| R14-20 | `codex_backlog_batch_registration_2.md` | �E�未完亁E��ら無し！E| `codex_r14-20_backlog_batch_registration_2.md` |

上記以外にも、`doc/work_orders/done/`・`doc/reports/`に同種の対応漏れがなぁE��、人間�Eの台帳�E�別途�E有される`task_ledger.md`�E�と突き合わせて確認する。台帳にある番号�E�E1-G9, A0-A3, U1-U5, P0-7, O8-13, P2-0、E, P3-0、E, Q1〜Q6, R1〜R20等）を参�Eし、ファイル名に番号が含まれてぁE��ぁE��のがあれ�E同様にリネ�Eム対象とする、E
## 作業

1. `doc/work_orders/active/`・`doc/work_orders/done/`・`doc/reports/`それぞれで、上記対応表と台帳を突き合わせ、リネ�Eム対象を洗い出す、E2. `git mv`でリネ�Eムする�E�Eit履歴を保つため、`rm`+`create`ではなく`mv`を使ぁE��、E3. リネ�Eムによって、他�Eファイルからの相互参照�E�指示書冁E�E「、Emdを参照」等�E記述、AGENTS.mdめEoc/README.md冁E�Eパス言及）が壊れてぁE��ぁE��確認し、壊れてぁE��ば更新する、E4. リネ�Eム対応表�E�旧ファイル名�E新ファイル名）を`doc/reports/`に完亁E��告として記録する、E5. 今後�E新規ファイル作�E時にこ�E命名規則を使ぁE��とを、`AGENTS.md`の「正本ドキュメントと参�Eルール」節に一言追記する、E
## 完亁E��件

- 対応表の全ファイルがリネ�EムされてぁE��、E- 相互参照が壊れてぁE��ぁE��とを確認済み、E- AGENTS.mdに命名規則が�E記されてぁE��、E- 完亁E��告に、リネ�Eム対応表全件が記載されてぁE��、E
## 注愁E
- `doc/work_orders/active/`直下には`active/`・`done/`・`README.md`以外を置かなぁE��とぁE��AGENTS.mdの既存規紁E�E引き続き守ること�E�本タスクはファイル名変更のみで、E�E置構造は変えなぁE��、E- リネ�Eムのみのコミットとし、�E容変更は行わなぁE���E容修正が忁E��な場合�E別タスクとする�E�、E