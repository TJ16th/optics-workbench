# R14-20 backlog batch registration 2 完了報告

## 対象

- `doc/work_orders/active/codex_r14-20_backlog_batch_registration_2.md`

## 実施内容

`doc/reports/issues_backlog.md` に以下7件のIssue下書きを追加した。指示どおり実装は行っていない。

1. `撮影結果シミュレータを追加する`
2. `太陽光5000K等の連続スペクトルで色収差をシミュレーションする`
3. `面反射ゴーストシミュレーションを追加する`
4. `コート特性・CCI（教育目的）項目を追加する`
5. `ズーム/フォーカス時の撮影シミュレーションを追加する`
6. `光学系の3Dデータ出力（3Dプリンタ用カットモデル）を追加する`
7. `解析条件・表示設定のプリセット機能を追加する`

## 検証

- Markdown追記のみのため、ビルド・E2Eは対象外。
- R9-13直前の検証結果:
  - `python -m pytest tests/test_core_acceptance.py -q`: `11 passed`
  - `npm.cmd run ui:build`: 成功
  - `npm.cmd run i18n:check`: `i18n:check ok (175 keys)`
  - `npm.cmd run i18n:coverage`: `i18n:coverage ok`
  - `npx.cmd playwright test --config apps/workbench-ui/playwright.config.ts apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`: `19 passed`

## 未対応・仕様との差分

- 本タスクはバックログ登録のみであり、7件の実装は未着手。
- GitHub Issue化はAGENTS.mdの運用どおり、人間が `Create Issues From Backlog` workflowを手動実行する前提。
