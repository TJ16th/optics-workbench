# R127：Surface Inspectorの右contextパネル移設 指示書（Codex向け・キュー追加）

## 背景

R120でSurface InspectorをSystem画面の下段に実装したが、人間のレビューで「右側に出したほうがよい」との指摘。R99の設計思想（右contextパネル＝画面別の操作系）とも一貫するため採用。本指示書は連続作業キューの**末尾への追加**（R125の後）。キュー運用ルールをすべて適用。

## 作業

1. Surface Inspector（R120実装）を下段からSystem画面の**右contextパネル内**へ移設する。Table/Splitどちらのビューでも右側に表示。
2. 編集機能・対応範囲（R120の編集可能列×面kindマトリクス）・validation・debounce挙動は**一切変更しない**。純粋な配置変更。
3. 右contextパネル内の既存要素（API/Validation等のAccordion）との配置関係を整理する。inspectorは面選択時に最上部へ表示し、未選択時は「面を選択してください」のplaceholderまたは非表示（自然な方を選び理由を報告）。
4. 1366px以下のdrawerモードでも編集フローが成立することを確認（drawer内でのinspector表示、編集→debounce preview反映）。
5. E2E：R120の既存inspector E2Eを新配置へ更新（削除・skip不可）。表の全高表示が下段時代より改善したこと（表の可視行数）を計測し報告。1366px drawerでの編集動作。
6. スクリーンショット：1920px Tableビュー＋右inspector、1366px drawer内inspector の2点以上。

## 完了条件

- 配置変更のみで機能同一（編集対応範囲の一覧を再掲し「変更なし」を明記）。
- `npm run ci`全通過、`ui:build:pseudo`成功、build_info一致確認。
- UI側のみ。エンジン・API・snapshot構造変更不可。
- 報告書：`doc/reports/2026-07-15_r127_surface_inspector_right_panel.md`（日付は完了日）、冒頭に着手前見積もり。
