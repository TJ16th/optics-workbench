# AGENTS.md — AIコーディングエージェント向けルール

このリポジトリで作業するエージェント（Codex等）は、以下に従うこと。

## 正本ドキュメントと参照ルール

- エンジン仕様の正本：`doc/engine_spec.md`（現行バージョンはファイル冒頭の改訂履歴を参照）
- UI仕様の正本：`doc/ui_spec.md`（同上）
- **`doc/archive/` 以下は旧版であり、参照禁止。** 検索でヒットしても正本を優先すること。
- 有効な作業指示は `doc/work_orders/active/` 内のみ。`done/` は完了済みの記録であり、再実行しない。
- 実装報告は `doc/reports/` に `YYYY-MM-DD_<件名>.md` 形式で追加する。

## 報告・コミュニケーション言語

- 実装報告（`doc/reports/`）・タスク完了報告・人間への質問は**日本語**で書く。
- ただし以下は翻訳せず原文のまま記載する：識別子（surface ID、metric名、エラーコード、変数キー）、ファイルパス、コマンド、テスト出力・ログの引用（例：`51 passed` はそのまま）、コード片。
- コミットメッセージは英語とする（Conventional Commits推奨。例：`feat(engine): add image_plane_policy (Task A1)`、`docs: reorganize doc/ into canonical layout (Task G2)`）。
- README等の対外ドキュメントは**日本語主体＋冒頭に英語Overview**の構成を維持する。全文の日英併記は行わない（内部報告書も同様）。
- Issue（タイトル・本文）およびissues_backlogは日本語で書く。ラベル名は英語（engine / ui / docs / performance 等）。
- 本ルール適用前の英語レポートは翻訳し直さず、そのまま `doc/reports/` に保管する。

## 作業規律

- 指示書のタスクは**番号順に1タスクずつ**。タスク完了報告後に停止し、次タスクへ勝手に進まない。スコープの先取り禁止（指示書の「スコープ外」節を厳守）。
- 1タスク=1コミット。コミットメッセージにタスク番号を含める。
- 既存テストは常にグリーンを維持する。テストを削除・スキップして通すことは禁止（正当な理由がある場合は報告して停止）。
- per-rayのLevel 0リファレンス実装（`optics_engine/reference/` 相当）は削除しない。Golden Testの基準である。
- ベンチ結果は `bench_results/` のJSON履歴に追記し、報告に前回比を含める。

## エンジン側の不変規約

- エラー・警告はすべて構造化形式（severity / code / params / message_en）。message_enの情報は必ずparamsからも取得可能にする。新codeは `/v1/meta` の enumerations に必ず追加する。
- **capabilitiesには実際に動作する機能のみを列挙する**（列挙駆動テストで担保）。
- エンジンは多言語化しない（翻訳はUI責務）。
- 数値出力の決定論を守る：同一リクエスト→ビット同一出力。random/sobolサンプリングはseed必須。

## UI側の不変規約（i18n恒常DoD）

- 表示文字列のハードコード禁止。すべてi18nリソース経由。
- エンジン識別子（surface ID、metric生キー、変数キー、エラーコード）は翻訳しない。
- 新しく表示するmetric・エラーコードには glossary ja/en 両方のエントリ追加をセットで行い、`npm run i18n:coverage` グリーンでマージする。
- glossary本体（seed由来）の内容改変は人間レビュー経由。暫定追記は supplement 用語集へ。
- 小数点はロケールによらずピリオド固定。単位（mm, µm, deg, lp/mm等）は翻訳しない。
- ツールチップはCarbon Toggletip（クリック/フォーカス開閉）。ホバー限定にしない。
- 点数の多い散布・spot表示はPlotly scattergl。SVG+D3はレイアウト図・光線図に限定。

## テスト・検証コマンド

```bash
python -m pytest -q          # エンジン（Golden Test含む）
npm run ci                   # UI: build + i18n:check + i18n:coverage + i18n:test
npm run ui:build:pseudo      # 擬似ロケールビルド
python benchmarks/spec_like_benchmark.py --profile smoke   # ベンチ（結果はbench_results/へ）
```

## 禁止事項

- `doc/archive/` の参照、旧版仕様に基づく実装
- リモートへのpush（人間の明示承認なしに行わない）
- 個人情報・絶対パス（ユーザー名入り）・秘密情報のコード/ドキュメント/ログへの記載
- 未実装機能のcapabilities掲載、README進捗表の誇張
