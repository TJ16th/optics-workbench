# R56：AGENTS.mdのクロスワークスペース同期追加 指示書（Codex向け）

## 背景

R55で以下2方向の自動同期を導入した。

1. `doc/work_orders/active`（Claude側 → Codex側）
2. `doc/reports`＋`doc/reports/screenshots`（Codex側 → Claude側）

しかし、正本の`AGENTS.md`（リポジトリ直下）はこの同期対象に含まれていない。Claude側は完了報告の評価のたびにAGENTS.mdの規約（完了主張の根拠明記、スクリーンショット保存規約等）を参照しているため、Codex側でAGENTS.mdが更新されてもClaude側の参照コピーが古いままだと、評価基準がずれる。

## 作業

1. R55で追加した同期スクリプト（`scripts/sync_cross_workspace_docs.ps1`）に、以下の一方向同期を追加する：
   - リポジトリ直下の`AGENTS.md` → `F:\vscode\claude\opt\doc\AGENTS.md`（Codex側→Claude側の一方向のみ。逆方向の書き戻しは行わない）
2. 同期方式はR55の既存実装に合わせる：更新検出のポーリング間隔、起動時のSHA-256照合による補完、削除非同期、同一パスへの再配置時の再同期。
3. 既存のWindowsタスク`OpticsCrossWorkspaceDocSync-R55`の監視対象にAGENTS.mdを追加するか、別タスクとして追加するかはCodexの判断とするが、多重起動・二重実行が発生しないようにする。
4. 同期ログ（`%LOCALAPPDATA%\OpticsDocSync\sync.log`）にAGENTS.mdの同期イベントも記録されるようにする。

## 完了条件

- リポジトリ直下のAGENTS.mdを更新後、`F:\vscode\claude\opt\doc\AGENTS.md`に反映されることを実際に検証し、結果を報告する（R55と同様、検証用の一意な変更を使った実測確認とする）。
- Claude側のコピーは参照専用であり、Codex側が同期の正本であることが動作として確認できる（一方向同期であることの検証）。
- 完了報告のフォーマット・検証粒度はR55の完了報告（`2026-07-12_r55_cross_workspace_doc_sync.md`）に準拠する。

## 注意

- タスク番号はR56とする。
- 本タスクはR55の同期範囲拡張であり、既存の同期方向・削除非同期等の設計方針は変更しない。
