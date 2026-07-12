# R65 仕様書同期とプリセット数確認

## 状態

**Done**。正本`doc/engine_spec.md`・`doc/ui_spec.md`のCodex側からClaude側への一方向同期を追加し、実運用タスクで検証した。プリセット数は実コード9件、`doc/ui_spec.md` 9.1も9件で一致していたため、件数記述は変更していない。

## 実装内容

`scripts/sync_cross_workspace_docs.ps1`へ`specs` routeを追加した。

- Source: `F:\vscode\opt\doc`
- Destination: `F:\vscode\claude\opt\doc`
- 対象: `engine_spec.md`, `ui_spec.md`のみ
- 方向: Codex → Claudeのみ
- 既存共通処理による起動時SHA-256補完、750 msポーリング、更新・再配置検出、削除非同期、ログ記録を利用
- 既存Windowsタスク`OpticsCrossWorkspaceDocSync-R55`へ相乗りし、新規タスク・workerは追加していない

`AGENTS.md`の「Claude/Codexワークスペース間のドキュメント同期」節にも、両正本仕様書の一方向同期を追記した。

## 実測検証

実装コミット後に`OpticsCrossWorkspaceDocSync-R55`を再起動し、次を確認した。

### 起動・多重実行

- Windowsタスク: `Running`
- `sync_cross_workspace_docs.ps1` worker: 1プロセス
- 新規タスク・二重workerなし

### 更新同期と復元

正本へ一時的に一意なHTMLコメントを追加し、Claude側参照コピーへの出現をポーリングで確認した。

- `engine_spec.md`: `R65_ENGINE_SYNC_PROBE_20260713`を確認
- `ui_spec.md`: `R65_UI_SYNC_PROBE_20260713`を確認
- 正本を元のバイト列へ戻した後、Claude側も元のSHA-256へ復元された
- ログへ`[specs] engine_spec.md`と`[specs] ui_spec.md`が記録された

最終SHA-256は次のとおりで、Codex側とClaude側が一致している。

| ファイル | SHA-256 |
|---|---|
| `engine_spec.md` | `BED0C47D2AF0F24544809AEB0B373AC15757384E00329A0BC9452BB6505A3415` |
| `ui_spec.md` | `F4AC6AB77D5AE2464E9787895442D83191107DB3FA4B84476E3B19281FA4E9B3` |

### 逆同期防止

Claude側`engine_spec.md`だけへ`R65_REVERSE_SYNC_PROBE_20260713`を追加して2秒待機したが、Codex側正本のSHA-256は変化しなかった。タスク再起動後、Claude側はCodex正本で再補完され、最終SHA-256が一致した。

## プリセット数の事実確認

TypeScriptの`presets`配列を実ロードした結果は次の9件だった。

```text
P001, P002, P005, P003, P006, P007, P008, P009, P010
```

P004は`doc/ui_spec.md` 9.4に設計例として記載されているが、現時点の`apps/workbench-ui/src/domain/presets.ts`には実装されていない。このため「P001〜P010で全10件」というR65指示書の想定は成立せず、コード上の総数は9件である。

`doc/ui_spec.md` 9.1の「代表的な光学系を9つ内蔵する」は実コードと一致しているため修正不要と判断した。R64完了報告の「9.1の内蔵プリセット数9件と実コード上のプリセット数が一致した」という記載も、P010追加後の実数を指しており正しい。作業1時点の件数を指したものではない。

## 検証

- PowerShell AST parser: `ParserErrors=0`
- 正本一時検証後: `git diff --exit-code -- doc/engine_spec.md doc/ui_spec.md` 成功
- 実装コミット: `9c06fafefc709baf3d10a49eb8c952a0bdd8bf12`

本タスクは運用スクリプトと文書規約のみの変更であり、エンジンAPI・UIコードは変更していない。そのためAPI/UIプロセスの再起動・`/v1/meta`確認は対象外である。
