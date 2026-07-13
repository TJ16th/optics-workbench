# R74 作業1 像面湾曲・M/S像面の実装確認

## 状態

**Done with confirmed specification gap**

- 調査基準HEAD: `e3b88c634e3d18edee1766435d5154e72f0b1747`
- 実行中APIの機能コミット: `434748c7121ebbeaee3ef7e38c4dd702c5f279df`
- 対象コード: `optics_engine/field_curvature.py`、`optics_engine/api/main.py`
- 対象仕様: `doc/engine_spec.md` 21.2節
- 対象テスト: `tests/test_phase5_tilt_asymmetric_ms.py`
- コード修正: なし。本作業は調査のみ。

## 結論

`ray_sampling`を変えてもP002/P003のField CurvatureとM/S像面の値は変化せず、4条件でJSONがビット同一だった。ただし、これは仕様21.2節が定めるCoddington方式を使用しているためではない。APIが外部`ray_sampling`を解析関数へ渡さず、内部固定`21 rays / grid / paraxial`のRMS探索を常に使用するためである。

同軸系のM/Sレスポンスは`method: coddington_rms_consistent`を返すが、実際にはCoddington方程式を実行していない。したがって、**サンプル数非依存は確認できたが、計算方式とmethod metadataは仕様不一致**である。

## コード確認

### API境界

- `POST /v1/analysis/field-curvature`は`fields`と`configuration`だけを`analyze_field_curvature`へ渡す。
- `POST /v1/analysis/ms-image-surface`も`fields`と`configuration`だけを`analyze_ms_image_surface`へ渡す。
- リクエストの`ray_sampling`は両解析へ渡らない。
- `field-curvature`レスポンスには計算方式のmethod metadataがない。

### 解析本体

`_best_focus_for_field`は、外部条件に関係なく次を固定している。

```text
samples_per_field = 21
pupil_distribution = grid
ray_aiming.mode = paraxial
sensor scan = -5.0 ... +5.0 mm / 11 points
```

Field CurvatureはY/Zの2次元RMS、M/S像面はY幅・Z幅を個別に最小化する。どちらもCoddington方程式ではなくRMS最小探索である。同軸かつdecenter/tiltなしの場合だけ、計算経路を変えずにmethod文字列を`coddington_rms_consistent`へ変更している。

`tests/test_phase5_tilt_asymmetric_ms.py`はM/S値が非nullであることと`method == "coddington_rms_consistent"`だけを固定し、Coddington計算の実在やRMS結果との独立比較は行っていない。

## API実測条件

Workbenchの`apps/workbench-ui/src/domain/presets.ts`にあるP002/P003の光学系、有効径、推奨3 fieldを使用し、次の条件を両endpointへ送った。

| 条件名 | samples_per_field | pupil_distribution | ray_aiming.mode |
|---|---:|---|---|
| preview | 9 | grid | paraxial |
| standard | 81 | grid | full |
| high_density | 1001 | grid | full |
| debug | 3 | fan_y | off |

## 実測結果

各行のSHA-256は、レスポンスJSONをkey順でcanonical化した値である。4条件はendpointごとに同じhashとなった。

| preset | endpoint | 4条件共通SHA-256 | ビット同一 |
|---|---|---|---|
| P002 | `field-curvature` | `274581f78d1db9cc2a29a0cb22bf53658f0ffcad44c8629028d6f1a6edfab58b` | yes |
| P002 | `ms-image-surface` | `b13560160211e66b7db416332a50f616f96c0e79dd7463ab64fcf153526007ca` | yes |
| P003 | `field-curvature` | `7334e67da24cba3bd81aa3c3a23af49681c4e69f55f6cd0c8fb0473aa8daf9ce` | yes |
| P003 | `ms-image-surface` | `56fc4b2acf2c74ba43a567e70bcd20ab75b79bda7d74a584646704aa7e8a3c01` | yes |

### P002

| field | Field Curvature shift mm | RMS mm | M shift mm | S shift mm |
|---|---:|---:|---:|---:|
| center | 0.0 | 0.029375990162286033 | 0.0 | 0.0 |
| mid-y 9.900092 deg | -2.0 | 0.104348734165455 | -1.0 | -2.0 |
| edge-y 14 deg | -3.0 | 0.15001087963359613 | -2.0 | -4.0 |

### P003

| field | Field Curvature shift mm | RMS mm | M shift mm | S shift mm |
|---|---:|---:|---:|---:|
| center | -5.0 | 0.05389498763919815 | -5.0 | -5.0 |
| mid-y 7.036366 deg | -5.0 | 0.178216306758017 | -5.0 | -5.0 |
| edge-y 10 deg | -5.0 | 0.31029434188017285 | -5.0 | -5.0 |

P003は全値が既定探索範囲の下端`-5.0 mm`に張り付く。現行レスポンスは範囲不足または非収束を通知しないため、この値を収束済みの最良像面と断定できない。

## テスト結果

- `python -m pytest -q tests/test_phase5_tilt_asymmetric_ms.py` -> `4 passed in 0.36s`
- R73完了監査時の全体テスト: `python -m pytest -q` -> `107 passed, 1 skipped, 1 warning`
- API実測時の`GET /v1/meta build_info.git_commit`: `434748c`。対象機能コミットと一致。

## 判定

- 外部`ray_sampling`への依存: **なし（実測でビット同一）**
- Coddington方式の使用: **なし**
- 仕様21.2節との整合: **不一致**
- `method`の正確性: **不正確**
- P003探索の収束性: **範囲端のため未証明**

修正はR74のスコープ外とし、`doc/reports/issues_backlog.md`へ別Issue下書きを追加した。
