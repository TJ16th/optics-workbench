# 軽量確認：動的キー許可リストの網羅性とci構成の変遷

## 確認1：messageKey生成パターンの網羅性

`i18n-check.mjs`の`allowedDynamicKeys`に登録した6キー（`surfaceTable.groups.duplicate_id`等）が、group validationロジックが生成しうる`messageKey`の**全パターン**であることを確認する。

1. `App.tsx`のgroup validationで`messageKey`を決定しているコード箇所を確認し、生成されうるキーの列挙（switch文、条件分岐等）と、`allowedDynamicKeys`の6件を突き合わせる。
2. 一致していることを報告する。今後group validationの種類が増えた場合、`allowedDynamicKeys`への追加も同時に必要になる旨を、該当コード近辺にコメントとして残す（i18n:checkは動的キーの追加漏れを検出できないため、レビュー時に気づけるようにするため）。

## 確認2：npm run ci構成の変遷確認

現在の`npm run ci`は`ui:build / i18n:check / i18n:coverage / i18n:test / svg:export:test / chart:test / ui:e2e`で構成されている（今回の報告で確認）。当初のG4時点では`ui:build / i18n:check / i18n:coverage / i18n:test`の4項目だったと記録されている。

1. `svg:export:test`・`chart:test`・`ui:e2e`が`ci`スクリプトに追加された経緯（どのタスクで追加されたか）を`git log -p -- package.json`等で簡単に確認する。
2. 意図通りの拡充であることを確認し、一言報告する（詳細調査は不要。矛盾や意図しない追加が無いことの確認のみ）。

## 完了条件

- 確認1・2それぞれの結果が報告されている。特に問題が無ければ短い報告でよい。
