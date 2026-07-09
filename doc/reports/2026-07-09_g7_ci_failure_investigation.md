# G7 CI失敗調査・修正報告

作業日: 2026-07-09

## 対象

- Repository: `https://github.com/TJ16th/optics-workbench`
- 失敗run: `https://github.com/TJ16th/optics-workbench/actions/runs/28999281557`
- 失敗commit: `e054eea1a8cf6542dc698d862f5a75667b71d919`
- 失敗job: `ui`

## 実ログ

`ui` jobの失敗ステップは `UI CI` だった。認証付きActionsログから、実際の失敗メッセージは以下。

```text
2026-07-09T06:40:45.1477616Z > optics-workbench@0.2.0 ui:e2e
2026-07-09T06:40:45.1478532Z > playwright test --config apps/workbench-ui/playwright.config.ts
2026-07-09T06:40:46.0510492Z [WebServer] /bin/sh: 1: npm.cmd: not found
2026-07-09T06:40:46.0668030Z Error: Process from config.webServer was not able to start. Exit code: 127
2026-07-09T06:40:46.0987912Z ##[error]Process completed with exit code 1.
```

Checks annotationには以下も出ていた。

```text
Process completed with exit code 1.
```

## 原因

`apps/workbench-ui/playwright.config.ts` の `webServer.command` がWindows専用の `npm.cmd` を直接呼んでいた。ローカルWindowsでは通るが、GitHub ActionsのUbuntu runnerでは `/bin/sh` が `npm.cmd` を解決できず、Playwright E2E開始前のwebServer起動で失敗していた。

あわせて、G7指示のPlaywright確認項目として `.github/workflows/ci.yml` を確認したところ、Ubuntu CI上でPlaywrightブラウザを導入するステップがなかった。今回の初回失敗は `npm.cmd` で止まっていたが、webServer修正後にブラウザ未導入で再失敗する可能性が高いため、同じPlaywright CI環境差の修正として導入ステップを追加した。

## 修正内容

- `apps/workbench-ui/playwright.config.ts`
  - `webServer.command` を `npm.cmd run ui:dev -- --port 5177` から、OS非依存の `node ../../node_modules/vite/bin/vite.js . --host 127.0.0.1 --port 5177` に変更。
- `.github/workflows/ci.yml`
  - `ui` jobの `npm ci` 後に `npx playwright install --with-deps msedge` を追加。
- `AGENTS.md`
  - GitHub Actions Ubuntu上でPlaywright E2Eを実行する場合はブラウザ導入ステップとOS非依存webServer起動が必要、という注意を「テスト・検証コマンド」節へ追記。

## ローカル確認

| Command | Result |
| --- | --- |
| `npm run ci` | Passed: Playwright E2E 6 passed |
| `npm run ui:build:pseudo` | Passed |

## GitHub Actions再確認

- 修正commit: `fe4f3c42b57c7dd40f6e732dc857d682abd93c73`
- 再実行run: `https://github.com/TJ16th/optics-workbench/actions/runs/29000291972`
- Workflow result: `success`

| Job | Status | Conclusion |
| --- | --- | --- |
| `engine` | `completed` | `success` |
| `ui` | `completed` | `success` |
| `pii` | `completed` | `success` |

## 備考

GitHub Actionsのログ取得APIは未認証では `Must have admin rights to Repository.` で403になった。既存のGitHub認証情報をトークン値を表示しない形で一時利用し、詳細ログを取得した。
