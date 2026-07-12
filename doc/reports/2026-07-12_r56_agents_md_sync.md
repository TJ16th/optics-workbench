# R56 AGENTS.mdクロスワークスペース同期 完了報告

## 実装内容

R55で追加した既存スクリプト`scripts/sync_cross_workspace_docs.ps1`へ`agents` routeを追加した。

同期方向は次の一方向のみである。

```text
F:\vscode\opt\AGENTS.md
  -> F:\vscode\claude\opt\doc\AGENTS.md
```

既存のWindowsタスク`OpticsCrossWorkspaceDocSync-R55`と同じプロセスで監視し、新しいタスクやプロセスは追加していない。

- ポーリング間隔: `750 ms`
- 起動時: SHA-256照合により欠落・内容差分を補完
- 更新時: LastWriteTimeUtcとファイルサイズのsignature変化を検出してコピー
- 削除: 同期しない
- 逆方向: 同期しない
- ログmode: `[agents]`

正本`AGENTS.md`の同期規約節にも、Codex側が正本でClaude側が参照用コピーであることを追記した。

## 正方向の実測

R56の規約追記を含むCodex側`AGENTS.md`を同期し、次のSHA-256一致を確認した。

```text
Codex:  E47F9C314AF6F78F6BAC90F1E483077AC61E6F4D3FB09CEDCFCCF61E0BDC1B16
Claude: E47F9C314AF6F78F6BAC90F1E483077AC61E6F4D3FB09CEDCFCCF61E0BDC1B16
```

同期ログには次のeventが記録された。

```text
[agents] AGENTS.md
```

## 一方向性の実測

Claude側参照コピーへ一時マーカー`<!-- R56 reverse-sync probe -->`を追記した。

- 変更前Codex hash: `E47F9C314AF6F78F6BAC90F1E483077AC61E6F4D3FB09CEDCFCCF61E0BDC1B16`
- マーカー追記後Codex hash: `E47F9C314AF6F78F6BAC90F1E483077AC61E6F4D3FB09CEDCFCCF61E0BDC1B16`
- マーカー追記後Claude hash: `29C00DBB517A3C48B4EB9EC8AE422E80F9DEFE29C83294B158506C9F03F1F72E`

Codex正本は変化せず、ClaudeからCodexへの逆書き戻しが無いことを確認した。その後、既存タスクを再起動し、起動時SHA-256照合によってClaude側をCodex正本から復元した。復元後の両hashは再び`E47F9C314AF6F78F6BAC90F1E483077AC61E6F4D3FB09CEDCFCCF61E0BDC1B16`で一致した。

## 検証

- PowerShell parser: `ok`
- Windowsタスク: `OpticsCrossWorkspaceDocSync-R55 Running`
- 多重タスク追加: なし
- 正方向hash一致: `true`
- 逆方向書き戻し防止: `true`
- 起動時復元: `true`
- 同期ログ記録: `true`
- 実装根拠: R56実装コミット `250d9536da40a4a0d7f470bcae57c9b5b7abb386`（短縮形: `250d953`、`feat(ops): sync AGENTS.md to Claude workspace (R56)`）

本タスクは同期運用と文書だけの変更であり、エンジンAPI・UI機能を変更していないため、pytest、UI CI、API/UI再起動は対象外である。
