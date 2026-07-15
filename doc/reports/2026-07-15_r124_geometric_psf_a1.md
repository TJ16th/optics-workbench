# R124 Geometric PSF A1 完了報告

## 結果

R119の案A・A1に基づき、既存幾何PSFを製品契約として固定し、Analysis workspaceへ`PSF (Geometric)`を追加した。状態は **Done with noted limitation** とする。

- 機能コミット: `bd8c86c` (`feat(psf): formalize geometric analysis contract (R124)`)
- 根拠テスト: `tests/test_phase6_psf_mtf_illumination.py`、`apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
- 着手時の見積り: エンジン契約、API artifact、UI heatmap、全回帰確認を含め約3時間

## 実装内容

- `GeometricPSFResult`へ`mode: geometric`、`diffraction_included: false`、metadataを追加した。
- metadataでsum-to-one正規化、sensor Y/Z座標、`mm`、`relative_energy`、grid/pixel寸法を固定した。
- `traced_ray_count`、`arrived_count`、`lost_ray_count`、`ray_loss_fraction`、`status_counts`を返す。
- `psf_array` artifactへcontent type、shape、normalization、値・座標単位のmanifestを付与した。
- 重心相対座標を決定論的に格子化し、同一traceのbit同一と平行移動時のPSF形状不変を固定した。
- UI chart pickerへ`PSF (Geometric)`を追加し、32 x 32 heatmap、mode、回折非包含、grid、pixel寸法、正規化、重心、ray lossを表示した。
- `Run Charts`は軸上fieldの幾何PSFを追加取得し、R126の進捗総数にも反映する。

既存trace kernelと光線到達点は変更していない。`total_energy`も既存の到達光線数という意味を維持した。

## 検証

- `python -m pytest -q`: `198 passed, 1 skipped, 1 warning in 21.74s`
- `npm run ci`: `64 passed (2.1m)`、`i18n:check ok (345 keys)`、build/coverage/unit/SVG/chartすべて成功
- `npm run ui:build:pseudo`: 成功
- PSFテストで同一traceの完全一致、grid energy合計1、平行移動時のgrid不変と重心移動、ray loss metadata、artifact manifestを直接確認した。
- 初回全pytestでweighted retinal PSFの`total_energy`互換性回帰を検出したため、既存契約へ戻して全件グリーンを再確認した。

機能コミット直後にAPI/UIを再起動し、`GET /v1/meta`の`build_info.git_commit = bd8c86c`と`git rev-parse HEAD = bd8c86c295b613b724ed4cdc3fb5295a02fa6d05`の一致を確認した。`git_dirty = true`は未追跡のactive指示書と本報告書・スクリーンショットによる。

## 画面確認

- [P002 PSF (Geometric) heatmap](screenshots/2026-07-15_r124_geometric_psf_a1_1.png)

## 制限

- 回折PSF、OPL/OPD、瞳位相、FFTはA2以降であり未実装。`capabilities.diffraction_psf=false`を維持している。
- UIはRun Charts条件の軸上fieldを表示する。field別PSF切替とlinear/log切替、encircled energy曲線は本A1の対象外。
- artifact本体は現行互換のJSON配列であり、仕様例の`.npy`とPNG生成は未実装。
