# 動的キー許可リストとCI構成の軽量確認

日付: 2026-07-10

## 対象

`doc/work_orders/active/codex_check_dynamic_keys_and_ci_scope.md` に基づき、group validation の動的i18nキー許可リストの網羅性と、`npm run ci` 構成の変遷を確認した。

## 確認1: 動的キー許可リスト

`apps/workbench-ui/src/ui/App.tsx` の `groupIssues()` が生成しうる本文 `messageKey` は以下4件。

- `surfaceTable.groups.duplicate_id`
- `surfaceTable.groups.unknown_surface`
- `surfaceTable.groups.invalid_range`
- `surfaceTable.groups.overlap`

`GroupPanel` の通知タイトルで条件分岐により使われるキーは以下2件。

- `surfaceTable.groups.issue_error`
- `surfaceTable.groups.issue_warning`

`apps/workbench-ui/scripts/i18n-check.mjs` の `allowedDynamicKeys` は、上記6件と一致している。余分な許可キーはなく、group validation が現時点で生成しうるキーは網羅されている。

将来 group validation の種類を増やす場合に `allowedDynamicKeys` への追加漏れが起きないよう、`groupIssues()` 近辺に同期コメントを追加した。

## 確認2: npm run ci 構成

確認コマンド:

- `git log --oneline -- package.json`
- `git log -p -- package.json`

確認結果:

- `package.json` の履歴は `436babb Initial public release` と `40df916 G4 add GitHub Actions CI` の2件。
- `436babb` の初期公開時点で `ci` はすでに以下7項目を含んでいた。
  - `ui:build`
  - `i18n:check`
  - `i18n:coverage`
  - `i18n:test`
  - `svg:export:test`
  - `chart:test`
  - `ui:e2e`
- `40df916` では `ci` の内容を増減したのではなく、Windows固有の `npm.cmd run ...` を `npm run ...` に変更し、CI向けにOS非依存化していた。

結論として、現在の7項目CI構成は意図された構成であり、今回確認した履歴上では後から意図せず混入した追加ではない。

## テスト結果

- `npm.cmd run i18n:check`
  - passed
  - `i18n:check ok (161 keys)`

## 状態

確認完了。動的キー許可リストは現行group validationの全パターンと一致し、CI構成も意図された7項目構成であることを確認した。
