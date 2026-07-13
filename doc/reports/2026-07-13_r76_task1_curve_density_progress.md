# R76 中間報告: 作業1 曲線解析のfield密度向上

## 状態

- R76全体: **Partial**
- 作業1（像面湾曲・周辺光量・歪曲のプロット点密度向上）: **実装・検証済み**
- 作業2（MTF軸範囲固定）: **未着手**
- 実装コミット: `1468c7686b213e8f340d6b5205e4caab3c81587c`
- R76全体は未完了のため、指示書 `doc/work_orders/active/codex_r76_curve_density_and_mtf_axis_fix.md` はactiveに残した。

## 修正内容

- 曲線としてfield全域を評価する次の4エンドポイント専用に、高密度fieldリストを生成するよう変更した。
  - `/v1/analysis/distortion`
  - `/v1/analysis/field-curvature`
  - `/v1/analysis/ms-image-surface`
  - `/v1/analysis/relative-illumination`
- 最大field方向に0から最大角まで15点を等間隔生成し、既存の代表fieldを同一座標で上書き・追加する。
- P002/P003では、0～14 degの1 deg刻み15点に既存の`mid-y: 9.900092 deg`を加え、合計16 fieldとなる。
- 既存の`center`、`mid-y`、`edge-y`のIDと角度は維持した。
- Ray Fan、MTF、Spot系には高密度fieldを適用していない。
- 曲線系チャートにE2E検証用の安定した`data-testid`を追加した。

## 実データ比較

P002を実APIへ接続し、修正前後のNetworkレスポンスとDOMを比較した。

| 対象 | 修正前 | 修正後 |
| --- | ---: | ---: |
| Field Curvature（標準パネル） | 6点 | 32点（M/S各16点） |
| Distortion（標準パネル） | 2点 | 15点（centerは`null`のため非表示） |
| Distortion（個別パネル） | 2点 | 15点 |
| Field Curvature（個別パネル） | 6点 | 32点 |
| Relative Illumination | 3点 | 16点 |
| Ray Fan Y/Z | 各81点 | 各81点 |
| MTF | 30点 | 30点 |

4つの曲線系リクエストはいずれも16 fieldを送信した。角度列は`0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9.900092, 10, 11, 12, 13, 14 deg`である。Ray Fanは2リクエストとも3 field、MTFは3リクエストとも1 fieldで、従来の評価単位を維持した。

### 代表fieldの値

| 解析 | field | 修正前 | 修正後 | 判定 |
| --- | --- | ---: | ---: | --- |
| Field Curvature `best_focus_shift_mm` | center | `1.0362167832824127` | `1.0362167832824127` | 一致 |
| Field Curvature `best_focus_shift_mm` | mid-y | `-0.5227939135810935` | `-0.5227939135810935` | 一致 |
| Field Curvature `best_focus_shift_mm` | edge-y | `-2.0233185280272856` | `-2.0233185280272856` | 一致 |
| Distortion `distortion_percent` | center | `null` | `null` | 一致 |
| Distortion `distortion_percent` | mid-y | `-2.4182001434449067` | `-2.4182001434449067` | 一致 |
| Distortion `distortion_percent` | edge-y | `-2.8151529466834067` | `-2.8151529466834067` | 一致 |
| Relative Illumination | center | `1` | `1` | 一致 |
| Relative Illumination | mid-y | `0.9417534841504308` | `0.9417534841504308` | 一致 |
| Relative Illumination | edge-y | `0.8863729093633073` | `0.8863729093633073` | 一致 |

代表3 fieldは同じ角度・同じ計算式で評価され、値はすべて完全一致した。

## 視覚確認

- 修正前: [screenshots/2026-07-13_r76_task1_curve_density_before_1.png](screenshots/2026-07-13_r76_task1_curve_density_before_1.png)
- 修正後: [screenshots/2026-07-13_r76_task1_curve_density_after_1.png](screenshots/2026-07-13_r76_task1_curve_density_after_1.png)

修正後はField CurvatureとDistortionの曲線形状をfield全域で連続的に確認できる。スクリーンショットは1600×1200、P002、英語表示、実API接続で取得した。

## テスト結果

- 対象E2E: `2 passed`
- `npm run ci`: `39 passed`
- `python -m pytest -q`: `113 passed, 1 skipped, 1 warning`
- 直接テスト: `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - P002/P003の曲線系DOM点数を固定した。
  - 曲線系4エンドポイントの16 field payloadを固定した。
  - Ray Fanが3 field、MTFが3回×1 fieldのままであることを固定した。

## 実行プロセス確認

実装コミット後にEngine APIとUI開発サーバーを再起動した。

- `HEAD`: `1468c7686b213e8f340d6b5205e4caab3c81587c`
- `GET /v1/meta`の`build_info.git_commit`: `1468c76`
- UI `http://127.0.0.1:5173/`: HTTP `200`
- `build_info.git_dirty`: `true`（afterスクリーンショット、R76を含む人間配置のactive指示書等が未追跡であるため）

本報告作成直前時点で、機能・コードに実質変更があった最新コミットと実行中プロセスの`build_info.git_commit`は一致している。
