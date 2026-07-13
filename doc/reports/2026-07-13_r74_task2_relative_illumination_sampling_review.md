# R74 作業2 周辺光量のサンプリング依存性調査

## 状態

**Done with confirmed accuracy and specification gaps**

- 調査基準HEAD: `86a87bd430dc254c983219b71cf026750ef9e345`
- 実行中APIの機能コミット: `434748c7121ebbeaee3ef7e38c4dd702c5f279df`
- 対象コード: `optics_engine/psf_mtf.py`、`optics_engine/api/main.py`、`apps/workbench-ui/src/api/engine.ts`、`apps/workbench-ui/src/ui/App.tsx`
- 対象仕様: `doc/engine_spec.md` 16.5、20.2、21.4節
- コード修正: なし。本作業は調査のみ。

## 結論

WorkbenchのRun Chartsは、UI共有`ray_sampling`を周辺光量endpointへそのまま送る。UI既定は`9 rays / grid / paraxial`であり、周辺光量専用の1000〜100000 rays設定はない。

ケラレのないP002推奨edge 14 degではthroughputが常に`1.0`で、9 raysでもcos⁴値と一致した。一方、partial vignettingが生じる同じP002の40 deg fieldでは、9 raysがthroughputを`1.0`と誤判定し、100000 rays基準よりrelative illuminationを`11.68%`過大評価した。したがって、**UI既定9 raysは一般的な周辺光量評価には不十分**である。

## UIから実際に渡るサンプル数

- `App.tsx`の`samplesPerField`初期値は`9`。
- `pupilDistribution`初期値は`grid`。
- `aimingMode`初期値は`paraxial`。
- `makeAnalysisRequest`はこれらを共有`ray_sampling`へ設定する。
- `runChartAnalyses`は共有requestを変更せず`POST /v1/analysis/relative-illumination`へ渡す。
- APIも`payload.ray_sampling`をそのまま`analyze_relative_illumination`へ渡す。

ブラウザNetworkの直接取得も試みたが、in-app browser制御ランタイムの一時`kernel.js`欠落で接続できなかった。このため、実測は上記のUI request生成コードと同じpayloadをローカルAPIへ送る方法で行った。

## エンジン実装

`analyze_relative_illumination`はfieldごとに共有samplingで`trace_forward`を行い、次を計算する。

```text
throughput = arrived_count / traced_count
relative_illumination = throughput(field) * cos(theta)^4
                        / (throughput(center) * cos(theta_center)^4)
```

samplingが空の場合だけ`128 rays / grid / paraxial`へfallbackする。UIは空ではなく9 raysを送るため、このfallbackは使われない。

metadataは`method: ray_throughput_times_cos4`と`radiometric_basis: object_space_solid_angle`だけを返す。実際には瞳gridを使いcos⁴を別乗算しており、サンプル数、distribution、aiming、重み付けはmetadataから取得できない。これは仕様16.5・21.4節の放射量定義とmetadata要件に一致しない。

## 実測条件

- optical system: Workbench P002 N-BK7 Biconvex Singlet
- wavelength: 587.56 nm
- normalization field: center 0 deg
- evaluation field: theta_y 40 deg、theta_z 0 deg
- pupil distribution: grid
- ray aiming: paraxial
- API: `POST /v1/analysis/relative-illumination`

P002推奨edge 14 degも9〜10000 raysで確認し、全条件でthroughput `1.0`、relative illumination `0.8863729093633073`だった。40 degでは1000 rays時のthroughputが`0.900`となり、partial vignettingを確認したため収束評価に採用した。

## 9〜10000 rays

| rays/field | throughput | relative illumination | 10000 rays比 | API時間 ms |
|---:|---:|---:|---:|---:|
| 9 | 1.000000 | 0.3443625112 | +11.6819% | 4.1 |
| 21 | 1.000000 | 0.3443625112 | +11.6819% | 23.4 |
| 81 | 0.925926 | 0.3188541771 | +3.4092% | 16.8 |
| 257 | 0.910506 | 0.3135440764 | +1.6870% | 17.8 |
| 1000 | 0.900000 | 0.3099262601 | +0.5137% | 38.7 |
| 4096 | 0.899658 | 0.3098085581 | +0.4756% | 76.3 |
| 10000 | 0.895400 | 0.3083421926 | 基準 | 118.5 |

## 10000〜100000 rays

| rays/field | throughput | relative illumination | 100000 rays比 | API時間 ms |
|---:|---:|---:|---:|---:|
| 10000 | 0.895400 | 0.3083421926 | -0.0011% | 119.6 |
| 20000 | 0.896800 | 0.3088243001 | +0.1552% | 389.2 |
| 50000 | 0.896500 | 0.3087209913 | +0.1217% | 938.0 |
| 100000 | 0.895410 | 0.3083456362 | 基準 | 1311.9 |

grid候補集合はサンプル数ごとに再構成されるため、誤差は単調減少しない。同一入力の結果は決定論的であり、同じサンプル数でのrun-to-run乱数ノイズではなく、サンプル集合の離散化誤差である。

## 判定

- UI共有samplingとの関係: **直接使用**
- 周辺光量専用sampling: **なし**
- UI既定9 raysの十分性: **ケラレなしでは値が安定するが、partial vignettingには不十分**
- 1000 rays: 本例で高密度参照との差約`0.51%`
- 10000 rays: 本例で100000 raysとの差約`0.0011%`だが、20000/50000点が非単調なため単一点比較だけで一般収束を保証できない
- sampling metadata: **不足**
- 放射量方式の仕様整合: **不一致**

## テスト結果

- `python -m pytest -q tests/test_phase6_psf_mtf_illumination.py` -> `4 passed in 0.33s`
- R73完了監査時の全体テスト: `python -m pytest -q` -> `107 passed, 1 skipped, 1 warning`

修正はR74のスコープ外とし、`doc/reports/issues_backlog.md`へ別Issue下書きを追加した。
