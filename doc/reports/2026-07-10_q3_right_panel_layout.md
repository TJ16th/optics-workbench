# Right Panel Layout Report

Date: 2026-07-10

## Scope

`doc/work_orders/done/codex_q3_right_panel_layout.md` に基づき、Workbench UI右ペインの縦伸び、スクロール時の中央ペイン巻き込み、低頻度セクションの常時展開を確認し、レイアウトを整理した。

## Findings

修正前:

- `.workbench-grid` がviewport固定ではなく、右ペインの内容量に応じてページ全体が縦に伸びていた。
- 右ペインを下まで見る操作が、中央のLayout View / chart領域の表示位置にも影響しやすかった。
- API、Analysis Conditions、Image Plane Policy、Group Motion、Aperture Motion、Decenter / Tilt、Validation、Exportがすべて常時展開されていた。

## Changes

- 3ペインレイアウトをviewport固定に変更した。
  - `.app-shell`: `height: 100vh; overflow: hidden`
  - `.workbench-grid`: `height: 100vh; min-height: 0`
  - `.left-pane` / `.center-pane` / `.right-pane`: `overflow-y: auto`
- 右ペインの低頻度セクションをCarbon Accordionへ移した。
  - API: collapsed by default
  - Validation: collapsed by default
  - Chart Export: collapsed by default
- 操作頻度の高いセクションは既存どおり直接表示に維持した。
  - Analysis Conditions
  - Image Plane Policy
  - Group Motion
  - Aperture Motion
  - Decenter / Tilt
- 1120px以下の1カラム表示では、従来どおりページ全体スクロールへ戻すようにした。

## Verification

追加E2E:

- `right pane scrolls independently and keeps center pane stable`
  - 右ペインの `scrollHeight > clientHeight` を確認。
  - 右ペインを最下部までスクロールしても、中央ペインのbounding box `y` が変化しないことを確認。
  - API accordionが初期状態で閉じており、クリックでBase URL入力が表示されることを確認。

実行済み:

```text
npm.cmd run ui:build
npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts -g "right pane scrolls"
```

結果:

- UI build: passed
- Targeted E2E: passed, 1 test

## Notes

右ペイン内のDebug系追加予定パネルは、今回導入したAccordion構造に自然に追加できる。常時操作するパネルは開いたまま、参照系・設定系のパネルは折りたたむ方針とした。
