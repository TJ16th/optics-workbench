# i18n:check groups dynamic keys 修正

日付: 2026-07-10

## 対象

`doc/work_orders/active/codex_fix_i18n_check_groups.md` に基づき、`npm run i18n:check` が `surfaceTable.groups.*` の6キーを unused として失敗していた問題を修正した。

## 原因

実装漏れではなく、動的キー参照の検出漏れだった。

対象キーは `apps/workbench-ui/src/ui/App.tsx` の group validation UI で使われている。

- `surfaceTable.groups.duplicate_id`
- `surfaceTable.groups.unknown_surface`
- `surfaceTable.groups.invalid_range`
- `surfaceTable.groups.overlap`
- `surfaceTable.groups.issue_error`
- `surfaceTable.groups.issue_warning`

ただし、警告本文は `messageKey` として保持して `t(issue.messageKey, issue.values)` で描画しており、titleも条件式で `t(issue.type === 'error' ? ... : ...)` としている。そのため `apps/workbench-ui/scripts/i18n-check.mjs` の単純な `t('literal.key')` 検出では参照済みと判定できなかった。

## 修正内容

`apps/workbench-ui/scripts/i18n-check.mjs` に完全一致の `allowedDynamicKeys` を追加し、上記6キーだけを意図的な動的参照として許可した。

プレフィックス許可ではなく完全一致にしたため、`surfaceTable.groups` 配下の別の未使用キーが将来増えた場合は引き続き検出される。

## UI表示確認

P3-1のgroup validation表示自体は既存E2Eで確認済み。

- `group edits mark the optical system dirty and show range warnings`
  - `Groups FOCUS_G and OIS_G overlap.`
  - `Group G3 starts after its end surface.`

今回の原因は実装漏れではないため、UI側の表示ロジック変更は行っていない。

## テスト結果

- `npm.cmd run i18n:check`
  - passed
  - `i18n:check ok (161 keys)`
- `npm.cmd run ci`
  - passed
  - `ui:build`
  - `i18n:check`
  - `i18n:coverage`
  - `i18n:test`
  - `svg:export:test`
  - `chart:test`
  - `ui:e2e`: 15 passed

## 状態

完了。`npm run i18n:check` と `npm run ci` はグリーンになった。
