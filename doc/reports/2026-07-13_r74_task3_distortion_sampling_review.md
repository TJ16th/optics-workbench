# R74 作業3 歪曲のサンプリング依存性確認

## 状態

**Done**

- 調査基準HEAD: `f84480d57b88ef01a052ee724857c636e15ef103`
- 実行中APIの機能コミット: `434748c7121ebbeaee3ef7e38c4dd702c5f279df`
- 対象コード: `optics_engine/aberrations.py`、`optics_engine/api/main.py`
- 対象仕様: `doc/engine_spec.md` 21.3節
- コード修正: なし。本作業は調査のみ。

## 結論

P002/P003の歪曲レスポンスは、外部`ray_sampling`のサンプル数、distribution、aiming modeを変えてもビット同一だった。現行実装はリクエストの共有samplingを歪曲計算へ渡さず、内部固定の`1 ray / grid / full aiming`で主光線を追跡し、主波長における固定近軸EFLを理想像高の基準に使う。

これは、解析条件による歪曲値の揺れを防ぐ`doc/engine_spec.md` 21.3節の意図と一致する。

## コード確認

- APIの`_analysis_context`は共有`ray_sampling`を読み取るが、`POST /v1/analysis/distortion`はそのsamplingを`analyze_distortion`へ渡さない。
- `analyze_distortion`は内部で`samples_per_field: 1`、`pupil_distribution: grid`、`ray_aiming.mode: full`を固定する。
- 実像高はaiming済み主光線のsensor交点を使用する。
- 理想像高は`analyze_paraxial`由来の基準EFLとfield角から計算する。
- response metadataは`reference: paraxial_efl`と`wavelength_nm: 587.56`を返す。

## 実測条件

WorkbenchのP002/P003実プリセット定義と推奨3 fieldを使用した。

| 条件名 | samples_per_field | pupil_distribution | ray_aiming.mode |
|---|---:|---|---|
| preview | 9 | grid | paraxial |
| standard | 81 | grid | full |
| high_density | 1001 | grid | full |
| debug | 3 | fan_y | off |

## レスポンス一致

| preset | 4条件共通SHA-256 | ビット同一 |
|---|---|---|
| P002 | `6a88f3a0bde290b84f0eaeb1b1886f10b56635ad72a757a1491f9eee46c2667e` | yes |
| P003 | `84260756a9cef0ac8568e8971139264bd139dc8c46d7b56bf8e90b48426c5cb3` | yes |

## 代表値

| preset | field | actual_y_mm | ideal_y_mm | distortion_percent |
|---|---|---:|---:|---:|
| P002 | mid-y 9.900092 deg | 8.3893039062 | 8.5891229094 | -2.3264191855 |
| P002 | edge-y 14 deg | 11.9363281304 | 12.2701761812 | -2.7208089425 |
| P003 | mid-y 7.036366 deg | 12.1530815085 | 11.4965942840 | 5.7102756552 |
| P003 | edge-y 10 deg | 17.3453250321 | 16.4237061189 | 5.6115161008 |

center fieldは理想像高が0であるため、`distortion_percent`は`null`となる。各条件でこの扱いも同一だった。

## テスト結果

- `python -m pytest -q tests/test_engine_v2_1.py::test_ray_fan_longitudinal_distortion_and_profiling_are_available` -> `1 passed in 0.41s`
- R73完了監査時の全体テスト: `python -m pytest -q` -> `107 passed, 1 skipped, 1 warning`

## 判定

- 外部`ray_sampling`への依存: **なし**
- 主光線の固定sampling: **確認済み**
- 基準EFL: **主波長の近軸EFL**
- 仕様21.3節との整合: **整合**
- 別修正タスク: **不要**
