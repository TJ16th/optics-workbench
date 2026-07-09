# GitHub Actions CI (ui job) 失敗調査・修正 指示書（Codex向け・タスクG7）

## 背景

`https://github.com/TJ16th/optics-workbench` へのpush後、GitHub Actions CIが起動した（run: https://github.com/TJ16th/optics-workbench/actions/runs/28999281557 、commit `e054eea1a8cf6542dc698d862f5a75667b71d919`）。

job結果：

| Job | Conclusion |
|---|---|
| engine | success |
| pii | success |
| ui | **failure** |

一方、ローカル環境（Windows、G4・G6実施環境）では `npm run ci` は `npm run ci` を**3回連続**実行してもPlaywright E2E含め全てpassedだった。つまり**ローカルではグリーン、GitHub Actions（Ubuntu）ではレッド**という環境差由来の不具合である可能性が高い。

## 作業

1. GitHub ActionsのUIジョブのログを取得する（`gh run view 28999281557 --log` が使えればそれを使う。`gh` CLI不在ならAPI経由 `curl` でログを取得するか、人間にログの貼り付けを依頼して報告する）。
2. ログから失敗しているステップを特定する（`ui:build` / `i18n:check` / `i18n:coverage` / `i18n:test` / Playwright E2E のどれか）。**推測で修正を始めず、まずログの実際の失敗メッセージを完了報告に引用すること**。
3. 失敗ステップに応じて典型原因を確認する：
   - **Playwright関連**：`.github/workflows/ci.yml` の ui job に `npx playwright install --with-deps` 相当のブラウザインストールステップが存在するか確認する。存在しない場合、Actions上のUbuntu環境にはPlaywrightブラウザバイナリが入らないため確実に失敗する。追加する。
   - **i18n:coverage関連**：G4で「`/v1/meta`取得失敗時は静的フォールバックを使う」設計にしたと報告されている。Actions環境でこのフォールバックが正しく機能しているか、フォールバック自体がエラーを投げていないか確認する。
   - **OS差異関連**：改行コード（CRLF/LF）、パス区切り（`\` vs `/`）に依存したコードやテストがないか、`ui:build`のログでエラーを確認する。
   - **Node/依存関係関連**：`ci.yml`のNodeバージョンとローカルのNodeバージョンが一致しているか確認する。`package-lock.json`がリポジトリに含まれ、`npm ci`が使われているか確認する。
4. 原因を1つに絞り込めたら修正する。**複数の仮説に同時に手を入れない**（原因切り分けができなくなるため）。
5. 修正後、GitHub Actions上で再度CIを走らせて確認する（pushして自動起動させるか、`workflow_dispatch`が設定されていれば手動起動する）。**ローカルでの確認だけで完了報告しない**（今回それでズレが生じたため）。

## 完了条件

- GitHub Actions上でCI（ui job含む全job）が `success` になっていることを、run URLとjob別ステータスで報告する。
- 失敗していた実際のログメッセージと、特定した原因、修正内容を報告する。
- ローカルとActions環境の差異が原因だった場合、その差異を `AGENTS.md` の「テスト・検証コマンド」節に一言記録し、今後同種の見落としを防ぐ（例：「Playwright使用時はCI環境にブラウザインストールステップが必要」）。

## 禁止事項

- ログを見ずに複数箇所を推測で同時修正すること。
- 「ローカルでpassedだから」を理由にActions上の確認を省略すること。
- CI設定をグリーンにするためだけにテストを削除・スキップすること。
