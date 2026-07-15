# R117 UI Phase4 Analysis workspace

## 状態

**Done**。実装根拠はコミット`9ba435b`（`feat(ui): add configurable analysis workspace (R117)`）である。R116の実API表示回帰更新は先行コミット`6e528e5`に分離した。

## 実装内容

- Analysisの全チャート縦積みと`Standard / Through-focus MTF`別画面切替を廃止し、共通の2〜4面chart workspaceへ統合した。
- 初回はLongitudinal Aberration、Field Curvature、Distortion、Ray Fanの4面を表示する。
- 各面のchart pickerから、上記に加えてRelative Illumination、Monochromatic MTF、White-light MTF、Through-focus MTFへ差し替えられる。
- panelは2面を下限、4面を上限として追加・削除できる。
- Through-focus MTFは同じworkspace slot内に推奨field別chartを表示し、従来の別Viewを廃止した。
- MTF mode toggleは解析条件として維持した。単色/白色の実行結果をUI session中に別々に保持し、2つのpanelで同時比較できる。
- chart selection、panel数・順序、左navigation開閉、右context panel開閉をlocalStorageへ保存し、reload後に復元する。
- 既存のengine/API、解析request payload、snapshot schema、数値系列は変更していない。

## テスト

`apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`で次を直接固定した。

- 初回4面と軸ラベル寸法
- 2面までの削除、再追加、chart selectionのreload復元
- 左右panel開閉状態のreload復元
- Through-focus MTFの同一workspace統合と3 field × 4 series
- Monochromatic / White-light MTF各198点の並列表示
- drawer遷移後のLayout/Chart寸法安定

実行結果:

- `npm run ci`: build、`i18n:check`、`i18n:coverage`、`i18n:test`、SVG export、chart theme、E2Eを通過。E2Eは`56 passed (1.7m)`。
- `npm run ui:build:pseudo`: 成功。
- 実API性能E2E: P007/P009とも30秒budget内。
- `git diff --check`: 問題なし。

## 実画面確認

Edge/Playwright、1920×1080で確認した。初期4面は各630px幅で相互重なりなし、各panelの`scrollWidth=clientWidth=628`だった。単色/白色MTFはそれぞれ198点を同時表示した。

- [初期4面](screenshots/2026-07-15_r117_analysis_workspace_1.png)
- [単色/白色MTF並列](screenshots/2026-07-15_r117_analysis_workspace_2.png)

機能コミット後にAPI/UIを再起動した。`GET /v1/meta`の`build_info.git_commit=9ba435b`と確認対象HEAD`9ba435b`は一致し、UI `http://127.0.0.1:5173/`はHTTP `200`だった。`build_info.git_dirty=true`は未追跡の作業指示書、スクリーンショット、本報告書によるものである。

## 制限

chart配置はlocalStorageでworkspaceとして永続化するが、既存snapshot JSON schemaには追加していない。これは「engine/API/payload/snapshot構造を変更しない」というR117スコープに従ったものである。
