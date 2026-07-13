# R76 完了報告: 曲線密度向上とMTF軸範囲固定

## 状態

- R76: **Done**
- 作業1（像面湾曲・周辺光量・歪曲のプロット点密度向上）: **Done**
- 作業2（MTFチャートの軸範囲固定）: **Done**
- 作業1実装コミット: `1468c7686b213e8f340d6b5205e4caab3c81587c`
- 作業2実装コミット: `7d063951512d1d13eb4721eed98a7edb599320aa`
- 直接テスト: `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`

## 作業1: 曲線解析のfield密度向上

次の4エンドポイント専用に、0から最大field角までの高密度fieldリストを生成するよう変更した。

- `/v1/analysis/distortion`
- `/v1/analysis/field-curvature`
- `/v1/analysis/ms-image-surface`
- `/v1/analysis/relative-illumination`

P002/P003では0～14 degの1 deg刻み15点に既存の`mid-y: 9.900092 deg`を加え、16 fieldを評価する。既存の`center`、`mid-y`、`edge-y`はID・角度・計算値を維持した。Ray Fan、MTF、Spot系には高密度fieldを適用していない。

| DOM表示 | 修正前 | 修正後 |
| --- | ---: | ---: |
| Field Curvature（標準パネル） | 6点 | 32点 |
| Distortion（標準パネル） | 2点 | 15点 |
| Field Curvature（個別パネル） | 6点 | 32点 |
| Distortion（個別パネル） | 2点 | 15点 |
| Relative Illumination | 3点 | 16点 |
| Ray Fan Y/Z | 各81点 | 各81点 |
| MTF | 30点 | 30点 |

代表3 fieldのField Curvature、Distortion、Relative Illumination値は修正前後で完全一致した。詳細値は`doc/reports/2026-07-13_r76_task1_curve_density_progress.md`に記録済み。

## 作業2: MTF軸範囲固定

- 共通`ChartSvg`に任意のX/Y domainを指定できるオプションを追加した。
- MTFチャートだけX軸を`0`から実データの最大空間周波数まで、Y軸を`0..1`に固定した。
- 現在のP002実データでは、X軸は`0..80 lp/mm`、Y軸は`0..1`となる。
- monochromatic MTFとwhite MTFの両方へ同一domainを適用した。
- 他のチャートは従来の自動スケールを維持した。

| モード | 修正前DOM目盛り | 修正後DOM目盛り | 修正後domain |
| --- | --- | --- | --- |
| monochromatic | `-4.00, 84.00, 0.05, 1.10` | `0.00, 80.00, 0.00, 1.00` | X=`0..80`, Y=`0..1` |
| white | `-4.00, 84.00, 0.05, 1.10` | `0.00, 80.00, 0.00, 1.00` | X=`0..80`, Y=`0..1` |

実API確認では両モードとも3リクエストを維持し、各リクエストの周波数は`[0, 10, 20, 40, 80]`、応答は各5点だった。変更は表示domainに限定され、API入力、近軸値、実光線追跡値、MTF応答値を変更していない。

## スクリーンショット

### 作業1

- 修正前: [screenshots/2026-07-13_r76_task1_curve_density_before_1.png](screenshots/2026-07-13_r76_task1_curve_density_before_1.png)
- 修正後: [screenshots/2026-07-13_r76_task1_curve_density_after_1.png](screenshots/2026-07-13_r76_task1_curve_density_after_1.png)

### 作業2

- 修正前（monochromatic）: [screenshots/2026-07-13_r76_task2_mtf_axes_before_1.png](screenshots/2026-07-13_r76_task2_mtf_axes_before_1.png)
- 修正後（monochromatic）: [screenshots/2026-07-13_r76_task2_mtf_axes_after_1.png](screenshots/2026-07-13_r76_task2_mtf_axes_after_1.png)
- 修正後（white）: [screenshots/2026-07-13_r76_task2_mtf_axes_after_2.png](screenshots/2026-07-13_r76_task2_mtf_axes_after_2.png)

## テスト結果

- 作業2対象E2E: `1 passed`
- `npm run ci`: `39 passed`
- `python -m pytest -q`: `113 passed, 1 skipped, 1 warning`

E2Eでは以下を直接固定した。

- 曲線系4エンドポイントの16 field payload
- Ray Fanが3 field、MTFが3回×1 fieldのままであること
- monochromatic/white MTF両方のX/Y domain属性
- monochromatic/white MTF両方の表示目盛り`0.00, 80.00, 0.00, 1.00`

## 実行プロセス確認

作業2実装コミット後にEngine APIとUI開発サーバーを再起動した。

- 機能・コードの最新コミット: `7d063951512d1d13eb4721eed98a7edb599320aa`
- `GET /v1/meta`の`build_info.git_commit`: `7d06395`
- UI `http://127.0.0.1:5173/`: HTTP `200`
- `build_info.git_dirty`: `true`（本報告、afterスクリーンショット、人間配置の未追跡active指示書等による）

本報告作成直前時点で、機能・コードに実質変更があった最新コミットと実行中プロセスの`build_info.git_commit`は一致している。
