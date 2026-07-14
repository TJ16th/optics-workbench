# R86 主要UI向けAPI 未対応入力黙殺スポットチェック

## 位置づけ

本書は主要UI向けAPIに代表的な不正・未対応入力を送った**監査報告**である。修正・設計提案・production code変更は行っていない。確認対象のproduction codeは`10584e126064866f9d2de4740b028b845f56ebb1`で、APIの`build_info.git_commit`は`10584e1`だった。

分類は指示書に従う。

- **① 構造化エラー**: 4xxと`severity/code/params/message_en`を返す
- **② 黙って既定動作**: HTTP 200で入力が無視・既定化される
- **③ 異常値を受理**: HTTP 200で物理的に不正・上限外の値を採用する

## 結論

狭いスポットチェックでも、R85と同種の黙殺・異常受理パターンが複数見つかった。

- ①構造化エラー: invalid surface type、unknown group/decenter/tilt、invalid image-plane policy、10000 nm
- ②黙殺・既定化: unknown aiming mode、unknown analysis metric/view、negative iris、preview `controls.iris_radius_mm`
- ③異常値受理: unknown material registration、negative semi-diameter、negative wavelength、巨大iris

最も危険なのは、未知材質を含むsystemが登録成功し、後続traceで構造化されていないHTTP 500になる経路である。また`ray_aiming.mode="teleport"`がparaxialと同じ結果を返しながらmetadataには`teleport`と記録されるため、利用者が指定modeで計算されたと誤認できる。

## 一覧

| カテゴリ | Endpoint / 入力 | HTTP | 分類 | 実結果 |
|---|---|---:|---|---|
| system | register: `material_after=UNOBTANIUM` | 200 | **③** | system hashを発行。後続traceはHTTP 500 `Internal Server Error` |
| system | register: `surface_type=hyperbanana` | 400 | **①** | `optics_value_error`。Pydantic literal error |
| system | register: `semi_diameter_mm=-2` | 200 | **③** | 負の有効半径を含むsystem hashを発行 |
| configuration | unknown `group_positions.NO_SUCH_GROUP` | 400 | **①** | `optics_value_error`、unknown group |
| configuration | decenterのunknown group | 400 | **①** | `optics_value_error`、unknown group |
| configuration | tiltのunknown surface ID | 400 | **①** | `optics_value_error`、unknown tilt target |
| trace | `ray_aiming.mode=teleport` | 200 | **②** | status/sensorがparaxialと完全一致。metadataだけ`teleport` |
| trace | wavelength `-587.56 nm` | 200 | **③** | 9/9 alive、有限sensor値 |
| trace | wavelength `10000 nm` | 400 | **①** | `optics_value_error`だがmessageはcomplex値の内部TypeError |
| analysis | `image_plane_policy.mode=warp_drive` | 400 | **①** | `optics_value_error`、unknown mode |
| analysis/spot | `metric=banana_metric`, `view=impossible_view` | 200 | **②** | baselineと同じRMS/重心/件数。extra fieldsを無視 |
| preview | `configuration.variables.iris_radius_mm=-3` | 200 | **②** | defaultとstatus/sensorが完全一致 |
| preview | `configuration.variables.iris_radius_mm=1000` | 200 | **③** | default 9 aliveから1 alive/8 missedへ変化。上限検証なし |
| preview | `controls.iris_radius_mm=-3` | 200 | **②** | defaultと完全一致。preview routeは`controls`を参照しない |

## 1. System登録・configuration

### 未知材質

P002のS1を`material_after: UNOBTANIUM`へ変えて`POST /v1/systems/register`した。

```json
{
  "system_id": "sha256:a4e332573a654edfe36e86a7ef422d5fb09040f062f836239463a8176515ee2d",
  "system_hash": "sha256:a4e332573a654edfe36e86a7ef422d5fb09040f062f836239463a8176515ee2d"
}
```

登録はHTTP 200だった。登録IDでtraceするとHTTP 500、bodyは`Internal Server Error`だった。`validate_system()`が`surface.material_after`とmaterials表の参照整合性を検査しないためである。登録時は③、後続は構造化されていないサーバーエラーである。

### 不正surface type

`surface_type: hyperbanana`はHTTP 400、`code=optics_value_error`となった。構造化wrapperはあるが、`params={}`でfield/path情報はmessage文字列内だけだった。分類①。

### 負のsemi-diameter

`semi_diameter_mm: -2.0`はHTTP 200で登録された。正値制約validatorがない。分類③。

### Configuration参照

存在しないgroupを`group_positions`または`decenters`へ指定したケース、存在しない面をtilt範囲へ指定したケースは全てHTTP 400、`optics_value_error`だった。`validate_configuration()`のunknown参照検査が機能している。分類①。

## 2. Trace・Analysis

### 未知ray aiming mode

`ray_aiming.mode: teleport`はHTTP 200だった。P002、edge 5 deg、9 grid raysでparaxial baselineと比較すると、statusとsensor Y/Zが完全一致した。一方、metadataは次を返した。

```json
{"ray_aiming_mode": "teleport", "ray_aiming_strategy": "teleport"}
```

`trace_forward()`が`mode == "full"`以外を一律に非反復経路へ送るためである。計算はparaxial相当なのに未知mode名が結果へ残る。分類②。

### 波長範囲

- `-587.56 nm`: HTTP 200、9/9 alive、有限sensor値。Sellmeier式が波長二乗を使うため負号が実質消える。分類③。
- `10000 nm`: HTTP 400、`optics_value_error`。ただしmessageは`complex object`の内部TypeErrorで、意図的な波長範囲validationではない。分類①。

波長の有限性・正値・材料モデル有効域を入口で検査する共通契約は確認できなかった。

### Image-plane policy

`image_plane_policy.mode: warp_drive`はHTTP 400、`optics_value_error`、messageにunknown modeを含んだ。分類①。

### Analysis metric/view

`POST /v1/analysis/spot`へ`metric: banana_metric`、`view: impossible_view`を追加してもHTTP 200で、baselineと次が完全一致した。

```text
rms_radius_mm: 0.045055322307178035
centroid_y_mm: 4.256034343327323
centroid_z_mm: 0.0
arrived_count: 9
blocked_count: 0
```

Analysis endpointは汎用dict payloadから必要keyだけを読むため、未知keyを拒否しない。分類②。現行UIが送らないkeyでも、typoやversion mismatchを検出できない。

## 3. Education preview

### 負iris

`configuration.variables.iris_radius_mm=-3`はHTTP 200でdefaultと完全一致した。`_runtime_iris_radius()`が非正値を`None`にして既定口径へ戻すためである。分類②。

### 巨大iris

`iris_radius_mm=1000`はHTTP 200で適用された。結果はdefaultの9 aliveから1 alive/8 missedへ変わった。system側の有効径やUI上限との整合検査はない。分類③。

### `controls.iris_radius_mm`

仕様例にあるpreviewの`controls.iris_radius_mm=-3`もHTTP 200でdefaultと完全一致した。現行preview routeはpayloadをforwardへ渡すだけで`controls`をconfigurationへ変換しない。分類②。

## 危険パターン一覧

### ② 黙って既定動作

1. unknown aiming modeがparaxial相当へ落ち、invalid mode名をmetadataへ残す。
2. Analysisのunknown metric/viewが無視される。
3. negative irisがdefaultへ戻る。
4. preview `controls`が無視される。

### ③ 異常値を受理

1. unknown materialを含むsystemを登録し、後続traceでHTTP 500になる。
2. negative semi-diameterを含むsystemを登録する。
3. negative wavelengthで通常の有限trace結果を返す。
4. system上限を大幅に超えるirisを適用し、多数のmissed rayを返す。

## 監査範囲と判断事項

本スポットチェックは各endpoint 2〜3例に限定した。次は未実施である。

- 全endpoint・全payload keyのschema監査
- NaN/Infinity、空配列、極端なfield角、負samples等の境界値総当たり
- 材料ごとの有効波長域監査
- 不正入力修正や優先度決定

狭い確認で複数の同型問題が出たため、API payload schemaとunknown-key policyの横断監査を別タスクで行う価値はある。本タスクでは提案以上の深追い・修正をしていない。

## 完了根拠

- production実装基準: `10584e126064866f9d2de4740b028b845f56ebb1`
- R85監査: `0e526e2`
- API直接確認: `systems/register`, `trace/forward`, `analysis/spot`, `education/preview`, `GET /v1/meta`
- production code差分: なし
- `python -m pytest -q`: `118 passed, 1 skipped, 1 warning in 13.87s`
- `git diff --check`: pass
