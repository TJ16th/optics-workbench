# R125 issues_backlogクリーンアップ 完了報告

## 結果

R118全件監査とR121/R122完了後の再判定に基づき、`doc/reports/issues_backlog.md`を42件から34件へ整理した。状態は **Done** とする。

- 変更前の正本: `df4a19c:doc/reports/issues_backlog.md`
- 根拠監査: `doc/reports/2026-07-15_r118_issues_backlog_audit.md`
- 変更対象: backlog文書のみ。エンジン/UIコードは変更していない。

## 削除

| 項目 | 完了根拠 |
|---|---|
| P004プリセット | `5e5160b`、現行preset API/UI E2E |
| `edge_thickness` metric | `19867e2`、`tests/test_r89_work3_edge_constraints.py` |
| P005/P006 NaN serialization | `ae4b1e9`、全preset HTTP smoke |
| afocal＋模型眼・網膜評価 | `d9b6b27`、`dd0a684`、`e2cde35`、`af5395b` |
| 固定annulus定義・UI | `1b6bed7`、`aa1aea7`、`eadbceb` |
| 周辺光量専用sampling/metadata | `66f2ef3`、R75精度回帰 |
| named Position Manager＋snapshot runtime configuration | `6d5fcab`、`doc/reports/2026-07-15_r121_position_manager.md` |

`[issue: #N]`付きの削除対象は0件だったため、GitHub Issueのclose・編集は行っていない。既存の`[issue: #1]`から`[issue: #10]`は未完項目としてbacklogに維持した。

## 統合・書換

- 「ズーム/フォーカス時の撮影シミュレーション」を「撮影結果シミュレータ」のzoom/focus milestoneと受け入れ条件へ統合した。
- Layout代表光線の旧説明を、R27以降のsampling非依存baselineと任意density layerの責務差へ書き換えた。
- Coddington項目を、R75で未対応のミラー・even asphereだけへ限定した。
- P011項目へR116のLayout baseline完了を追記し、通常225-ray bundleの物理的vignetting分類だけを残件とした。
- 周辺光量の適応sampling項目から、R75で完了した固定1000-ray専用samplingへの古い依存記述を除いた。
- Snapshot zipはR122で単一JSON/Project JSONまで実装済みだがzip自体は未実装のため、`[issue: #1]`を維持した。

## 確認

- `rg -n "^## Issue:" doc/reports/issues_backlog.md`: 34件。
- `git diff --check`: 問題なし。
- 削除した全項目はGit履歴の`df4a19c:doc/reports/issues_backlog.md`から復元可能。
- 本タスクは文書のみのため、API/UI再起動とテスト再実行は対象外。直前のR124検証はエンジン`198 passed, 1 skipped`、UI`64 passed`だった。
