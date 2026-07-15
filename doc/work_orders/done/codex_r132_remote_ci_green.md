# R132：リモートCI green化 指示書（Codex向け）

## 背景

R131のpush後、GitHub Actions run 29427984708が`engine`と`pii`の2ジョブで失敗した。原因はR131で特定済み。本タスクで修正しgreenへ戻す。

**push許可**：本タスクの修正コミット（CI設定・スキャナ方針のみ）のpushは、CI green化が目的のため**本指示書で事前承認済み**とする。ただしforce禁止、対象は本タスクのコミットのみ。

## 作業

### 1. engineジョブのNode依存導入

- preset smokeの`_shipped_presets()`がNode+TypeScriptを必要とするため、CIの`engine`ジョブへ`actions/setup-node`＋`npm ci`を追加する（`ui`ジョブと同じNodeバージョン・cache設定に合わせる）。
- 代替案（テスト側でNode不在時skip）は採用しない：ローカルとCIの検証範囲が乖離するため。ただし実装上の強い理由があれば提案として報告し判断を仰ぐこと。

### 2. PIIスキャナのベースライン許可リスト

R130で人間が「例外付きOK」と承認した39件（workspace_absolute_path / codex_runtime_cache、12ファイル）を恒久的にどう扱うかの実装：

- `scripts/pii_scan.py`に**ベースライン許可リスト**（ファイル＋検出内容の組を列挙した設定ファイル）を導入する。承認済み39件のみを列挙し、**新規検出は引き続きexit 1で失敗**させる（スキャナの検出能力自体は弱めない）。
- 許可リストファイルには「R130で人間承認済み（2026-07-16）」の由来コメントを付ける。
- AGENTS.mdへ運用ルールを追記：許可リストへの追加は人間の明示承認を必要とする。

### 3. 検証

- ローカルで`python scripts/pii_scan.py`がexit 0（39件が許可リスト経由でpass、故意に新規パターンを一時追加してexit 1になることも確認して戻す）。
- エンジンpytest・UI CIのローカル全通過。
- push→GitHub Actions再実行で**3ジョブ全green**を確認。green にならない場合は追加修正（本タスクスコープ内のCI/スキャナ設定に限る）を行い、それでも解決しない場合は原因報告で停止。

## 完了条件

- GitHub Actions最新runが全ジョブgreen。run URLとジョブ別結果を報告書へ記載。
- 許可リストの全39件一覧と由来が報告書に含まれる。
- 報告書：`doc/reports/2026-07-16_r132_remote_ci_green.md`、冒頭に着手前見積もり。

## 注意

- force push・履歴書き換え禁止。製品コード（エンジン・UI本体）は変更しない。
