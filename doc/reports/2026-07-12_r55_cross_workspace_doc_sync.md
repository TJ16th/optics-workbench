# R55 Claude/Codexワークスペース間ドキュメント同期 完了報告

## 実装内容

`scripts/sync_cross_workspace_docs.ps1`を追加し、750 ms間隔の更新検出で次の2方向を継続同期するようにした。

1. `F:\vscode\claude\opt\doc\work_orders\active` → `F:\vscode\opt\doc\work_orders\active`
2. `F:\vscode\opt\doc\reports` → `F:\vscode\claude\opt\doc\reports`

report同期の対象は、`doc/reports`直下のMarkdownと`doc/reports/screenshots`以下のファイルである。相対パスを維持し、作成・更新・renameを検出する。削除は同期しない。

監視プロセスの起動時にも同期元と同期先をSHA-256で照合し、コピー先に存在しないファイルや内容が異なるファイルを補完する。これにより、プロセス停止中や再起動直前に追加されたファイルも取りこぼさない。また、同期元からファイルが消えた場合はコピー先を削除せず、監視メモリからだけ除外する。同じパスへ再配置されたファイルは、内容・更新時刻が以前と同じでも新規ファイルとして再同期する。

Git管理および完了報告の正本は`F:\vscode\opt`側とし、Claude側は参照用コピーとして扱う。

## 自動起動

Windowsタスク`OpticsCrossWorkspaceDocSync-R55`を登録した。

- Trigger: 現在のユーザーのログオン時
- Action: Windows PowerShell 5.1から`scripts/sync_cross_workspace_docs.ps1`を非表示実行
- Multiple instances: `IgnoreNew`
- Execution time limit: なし
- 現在の状態: `Running`
- ログ: `%LOCALAPPDATA%\OpticsDocSync\sync.log`

初版の`FileSystemWatcher`方式はWindowsタスク配下でevent actionが処理されなかったため採用せず、PowerShell 5.1互換のポーリング方式へ変更した。また、PowerShell 5.1に存在しない`[System.IO.Path]::GetRelativePath()`を使用せず、検証付きのルート接頭辞除去で相対パスを求める。

## AGENTS.md

正本`AGENTS.md`へ以下を追記した。

- 2方向の同期元・同期先
- report Markdownとscreenshotsの対象範囲
- 削除を同期しないこと
- `F:\vscode\opt`をGit正本とすること
- Windowsタスク名とログ確認先

## 実動検証

一意な検証ファイル`r55_sync_probe_20260712`を使い、作成後のコピーと、内容を`v1`から`v2`へ変更した後の再コピーを確認した。

| 経路 | 作成 | 更新後内容 |
|---|:---:|---|
| Claude active → Codex active | 成功 | `incoming-v2` |
| Codex reports Markdown → Claude reports | 成功 | `report-v2` |
| Codex screenshots → Claude screenshots | 成功 | `screenshot-v2` |

検証用ファイルは同期元・同期先の双方から削除した。削除非同期の仕様により、片側だけの削除ではなく検証処理が各パスを明示的に除去した。

追加検証:

- PowerShell parser: `PowerShell parse: ok`
- Windowsタスク: `OpticsCrossWorkspaceDocSync-R55 Running`
- 同期ログ: `work_orders`、`reports`、`screenshots`の作成・更新を記録
- 本完了報告`2026-07-12_r55_cross_workspace_doc_sync.md`自体もClaude側へ自動コピーされたことを確認
- Claude側へ追加された`codex_r54_annulus_marker_cross_section.md`が、起動時補完によってCodex側へコピーされ、SHA-256が一致することを確認
- 同一パスのファイルを同期元から削除して再配置した場合、コピー先は削除されず、再配置後のファイルが再同期されることを確認

## 根拠

- スクリプト: `scripts/sync_cross_workspace_docs.ps1`
- 運用規約: `AGENTS.md`
- 実装根拠: 本報告と同一のR55コミット（`feat(ops): add cross-workspace document sync (R55)`）

本タスクは同期運用と文書の変更であり、エンジンAPI・UI機能を変更していないため、pytest、UI CI、API/UI再起動は対象外である。
