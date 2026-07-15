# R122：Project保存・Import/Export（ui_spec 22章準拠） 指示書（Codex向け・キュー7件目）

## 背景

人間とのレビューで「編集した光学系・解析条件をどう保存するか」の出口が実質Snapshotのみ（しかもProject保存・ファイルexport/importは未実装）である点が次の柱として承認された。R120で諸元編集が可能になると「編集したのに保存できない」が顕在化するため、その直後に実施する。本指示書は連続作業キュー（R116〜R119＋R120/R121）の**末尾（7件目）への追加**。キュー運用ルールをそのまま適用。**R121（Snapshotへのconfiguration保存）完了後に着手すること**（本タスクのexport対象がR121の成果に依存するため）。

## 作業

### 1. 実装状況精査（先行、報告書の節として記載）

ui_spec 22章（Project構造・MVP保存方式・Export対象・Snapshot/artifact永続化）と23章（version記録・読込時の互換確認）の各項目について、実装済み／部分実装／未実装の一覧表を作る。既存のExportパネル（PNG/SVG export等）とResult table export の現状も含める。

### 2. MVP実装（ui_spec 22.2の「ブラウザからのファイルdownload/upload」方式）

精査結果を踏まえ、以下を実装する：

1. **光学系のexport/import**（YAML/JSON）：現在のOpticalSystemDraft（R120の編集結果を含む）をファイルとしてdownload。importは読み込み→既存のvalidate/registerフローへ接続し、検証エラーは構造化表示（黙殺禁止）。
2. **Projectのexport/import**（JSON）：22.1構造（optical_systems・configurations・analysis_conditions・results・snapshots・compare_sets・versions）に従う。現状のUI状態モデルで存在しない要素（例：複数光学系の同時保持）は空配列＋単一要素として保存し、schema上は仕様準拠を保つこと。
3. **Snapshotの単体export**（JSON）：R121で追加されたconfiguration込み。
4. **version記録と読込時互換確認**（23章）：export時に`versions`（engine/api/ui/preset/project_schema_version）を記録し、import時に`/v1/meta`現在値と比較、不一致は警告表示（読込は拒否しない）。
5. **22.4のartifact埋め込み・zip export**：実装規模を精査し、（a）今回実装できるなら実装、（b）大きい場合はpartial snapshot規約（`partial: true`）を含む設計案の報告に留めて既存backlog「Snapshot zip export」を更新する。判断理由を報告書へ。

### 3. テスト・検証

- export→import往復で内容が一致すること（system・project・snapshotの3種それぞれ。round-trip test）。
- importした系がvalidate/register→preview実行まで通ること。
- 不正ファイル・version不一致・schema欠損時の構造化エラー／警告表示。
- 旧形式（R121以前の）snapshotが読み込めること（後方互換）。
- `npm run ci`全通過、`npm run ui:build:pseudo`成功、i18n ja/en。

## 完了条件

- 実装状況精査の一覧表が報告書に含まれる。
- MVP実装1〜4が完了し、round-trip・互換テストが固定されている。5は実装または設計案報告のいずれかで決着している。
- **完了主張には対象範囲の列挙を必須とする**（export/import可能になった状態要素の一覧、できない要素の一覧）。
- スクリーンショット（export操作・import後の復元・version警告の3点以上）。
- **UI側のみ。エンジン・API変更不可**（必要と判明した項目は提案として報告）。
- build_info一致確認。報告書冒頭に着手前見積もり。
- 報告書：`doc/reports/2026-07-15_r122_project_save_export_import.md`（日付は完了日）

## 注意

- ファイル形式・スキーマはui_spec 22章を正とし、独自スキーマを発明しないこと。仕様に曖昧さ・矛盾を見つけた場合は、実装を仕様の字義どおりに寄せた上で、問題点を報告書の「仕様フィードバック」節へ列挙する（仕様書自体の変更はしない）。
