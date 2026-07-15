# R128 プロジェクト基本設定タブ＋像高ベースfield定義 設計提案

> 本書は設計提案である。製品コード、テスト、`doc/ui_spec.md`、`doc/engine_spec.md`は変更していない。

## 着手前見積もり

- 見積もり: 2〜3時間
- 難易度: 中
- 対象: 現行UI/API/persistenceの実測、情報設計、field schema案、段階導入案
- 対象外: 実装、正本仕様変更、既存データ変換

## 結論

次の構成を推奨する。

1. 左navigationへ第6画面`Project Settings`を追加する。
2. 波長セット、波長weight、fieldの基準定義、image plane policy既定をProject Settingsへ移す。
3. Preview/Analysis右contextは`Evaluation Controls`へ改名し、sampling、aiming、一時field overrideなど実行頻度の高い項目だけを置く。
4. 基本値と一時overrideは別stateとして保持し、UIに`Inherited` / `Overridden`と`Reset to project default`を明示する。
5. グローバル`MTF mode`は廃止し、R117の`mtf_monochromatic` / `mtf_white`パネル選択から必要modeを決める。
6. field typeは現行値`angular`を維持し、`image_height_paraxial`と将来の`image_height_real`をdiscriminated unionとして追加する。指示書にある`angle`への改名は行わない。
7. `image_height_paraxial`はエンジン共通resolverでpositionごとにangular fieldへ解決する。UIだけで角度へ変換して送る方式は移行用に限定する。
8. `image_height_real`は2変数の反復field solveを必要とするため、近軸modeの契約確定後に別フェーズで実装する。

## 1. 現状確認

### 1.1 実測条件

- コード基準: `123dc50`までの製品実装（R127）
- 実画面: `http://127.0.0.1:5173/`
- viewport: 1920x1080
- preset: P001（3 fields、1 wavelength）
- API build: `8b12945`

| 画面 | right clientHeight | right scrollHeight | Analysis Conditions高さ | Image Plane Policy高さ |
|---|---:|---:|---:|---:|
| Preview | 1032 px | 1497 px | 1230.98 px | 0 px |
| Analysis | 1032 px | 2127 px | 1230.98 px | 672.55 px |

Previewでも条件panel単体が右ペイン高を約199 px超える。AnalysisではImage Plane Policyを加えて約1095 pxのscroll超過となる。

### 1.2 現行右パネル項目と影響

`AnalysisConditionPanel`はPreviewとAnalysisに同じ内容で表示される。`ImagePlanePolicyPanel`はAnalysisだけに表示される。ただしrequestは共通`makeAnalysisRequest()`を使うため、Analysisで変更したpolicyも次回Previewへ送られる。

| 項目 | 現在の表示 | request / state | Previewへの影響 | Analysisへの影響 |
|---|---|---|---|---|
| Field ID | Preview / Analysis | `fields[].id` | trace metadata、layout/spot系列 | chart系列、比較、artifact key |
| Theta Y / Z | Preview / Analysis | `fields[].theta_y_deg/z_deg` | 光線方向、layout、spot | 全field依存解析、M/S方向、歪曲、像面湾曲 |
| MTF mode | Preview / Analysis | UI `mtfMode` | なし | `runChartAnalyses`のmonochromatic/white選択 |
| Wavelength preset/custom | Preview / Analysis | `wavelengths_nm[]` | trace、ray色、spot | 全波長依存解析 |
| Wavelength weight | Preview / Analysis | `wavelength_weights`、policyのweights | endpointに送るが単色Previewでは実質影響が限定的 | white MTF/PSF、best focus重み |
| Rays / field | Preview / Analysis | `ray_sampling.samples_per_field` | ray数、spot密度、時間 | fan/MTF/PSF/illuminationの精度と時間 |
| Pupil distribution | Preview / Analysis | `ray_sampling.pupil_distribution` | 光線配置 | 積分・fan・MTF等のsampling |
| Ray aiming | Preview / Analysis | `ray_sampling.ray_aiming.mode` | path、blocked/aiming_failed | 全実光線解析の有効ray |
| Evaluated fields | Preview / Analysis | trace response表示のみ | 解決済みfieldの確認 | 直前Preview結果の確認 |
| Policy mode | Analysis | `image_plane_policy.mode` | 次回Previewにも送られる | 評価面solve・spot/MTF等 |
| Apply to | Analysis | `image_plane_policy.apply_to` | 次回Previewにも送られる | evaluation plane / focus group / report only |
| Custom offset | Analysis | policy option | custom offset評価 | 同左 |
| MTF frequency | Analysis | policy option | best MTF policy時 | best MTF solve基準 |
| Search range / steps | Analysis | policy option | solve/sweep時 | solve/sweep時 |
| Solve image plane | Analysis | `/v1/solve/best-focus`相当 | 直接影響なし | evaluation plane結果更新 |
| Align authority | Analysis | UI transient state | 直接影響なし | Preserve fields / Fit fields to sensor |
| Align / Apply | Analysis | paraxial solve＋register | Apply後は次回Previewがstale | sensor gapと任意fieldを更新 |

`fields`、wavelength、sampling、aiming、policyはPreview、Charts、Through-focus MTF、Visual Composite、Best Focusの共通requestへ入る。一方`MTF mode`はChartsだけに効くのにPreviewにも表示されている。これが現行ラベルと実際の共有範囲を分かりにくくしている。

### 1.3 現行field・sensor・position

- UI型`AnalysisField`は`type: 'angular'`だけを許可する。
- エンジン仕様15.1と実装も`angular`を使用する。指示書の`angle`は現行識別子ではない。
- R37の70% fieldは`preset_label: image_height_70pct`という表示用metadataを持つが、保存値は計算済み角度である。
- R123の`Fit fields to sensor`は`atan((width/2)/EFL)`と`atan((height/2)/EFL)`をY/Z別に計算し、既存field比率を保ってangular値へ書き戻す。
- sensor規約は`width_mm = Y`、`height_mm = Z`である。
- `zoom_position`変更はruntime configurationであり、positionごとにEFLが変わる。
- 現在のsensor寸法はOpticalSystemのsensor surface所有であり、Project固有値ではない。編集時は`system_dirty`となるべきである。

## 2. 情報アーキテクチャ案

### 案A: 現行右パネルをAccordionで整理

- fields / wavelengths / sampling / policyを同じ右contextに残し、初期開閉だけ調整する。
- 規模: 小。
- 長所: state移動が少なく、既存E2Eへの影響が小さい。
- 短所: 低頻度の基礎設定と毎回の操作が混在したままで、Projectとしての保存単位が見えない。
- 評価: 応急対応としては可能だが非推奨。

### 案B: Project Settingsへ全条件を移す

- 左navigationにSettingsを追加し、fields、wavelength、sampling、policyをすべて移す。
- 規模: UI中。
- 長所: 右ペインが大幅に短くなり、設定の一覧性が高い。
- 短所: 結果を見ながらsamplingやfieldを調整する往復が増え、R99の「操作と結果を同一画面」の方針を損なう。
- 評価: 非推奨。

### 案C: Project defaults＋明示overrideの2層モデル

- Project Settingsに基準値を置き、Preview/Analysis右contextには高頻度項目と明示overrideだけを置く。
- overrideがない項目はProject値を継承する。
- override中はTagと差分を表示し、1操作で基準値へ戻せる。
- 規模: UI中〜大、Project schema中。
- 長所: 基準値の所有者が明確で、結果を見ながらの調整も維持できる。Snapshot再現性も保ちやすい。
- 短所: effective conditionの合成規約とdirty判定が必要。
- 評価: **推奨**。

### 2.1 推奨Project Settings画面

左navigationを次の6画面にする。

```text
System
Project Settings
Preview
Analysis
Compare
Debug
```

`System`は光学系処方、`Project Settings`は評価基盤と明確に分ける。現在Systemのiconに使う`Settings`はProject Settingsへ移し、Systemには光学系・表を示す別のCarbon iconを割り当てる。

Project Settings中央workspace:

| セクション | 項目 | 所有・dirty |
|---|---|---|
| Spectral definition | wavelength set、primary、weight、名称 | Project defaults / `analysis_dirty` |
| Detector reference | sensor width/height、Y/Z規約、active sensor | OpticalSystem参照。編集は`system_dirty` |
| Field definition | mode、center/70%/edge、方向、custom field | Project defaults / `analysis_dirty` |
| Focus defaults | image plane policy既定、apply_to、search preset | Project defaults / `analysis_dirty` |
| Evaluation profile | preview/standard/high densityの既定profile | Project defaults / `analysis_dirty` |
| Reference context | reference position、reference wavelength | Project defaults / re-resolve |

API base、language、themeはProjectに含めず、引き続きアプリ設定またはDebug utilityとする。

### 2.2 右contextに残す項目

| 画面 | 残す項目 |
|---|---|
| Preview | Rays / field、pupil distribution、aiming、field subset、一時field override、density表示 |
| Analysis | panel picker、解析ごとのsampling preset、field subset、一時override、image plane effective policy、Align |
| Project Settings | validation summary、effective condition preview。編集本体は中央 |

波長セット全編集と基準field全編集は右から除く。一時overrideを許可する場合も、展開操作の中に限定する。

### 2.3 ラベルと状態表現

- `Analysis Conditions`は`Evaluation Controls`へ改名する。
- Project値をそのまま使う場合: `Inherited from Project` Tag。
- 一時変更中: `Overridden` Tag＋変更項目数＋`Reset to project default`。
- 結果が古い場合: 既存`Stale results`を維持する。
- effective値は常にrequest previewまたはsummaryで確認できるようにする。
- overrideは画面ローカルではなくAnalysisConditionに属し、PreviewからAnalysisへ移動しても保持する。

### 2.4 MTF mode

次の3案がある。

| 案 | 内容 | 規模 | 評価 |
|---|---|---:|---|
| 維持 | Project Settingsへ移す | 小 | R117 panel選択と二重管理になるため非推奨 |
| Analysisだけに残す | 右contextへ移す | 小 | Preview混入は解消するがpanelとの矛盾が残る |
| panel選択へ一本化 | `mtf_monochromatic` / `mtf_white`から必要modeを導出 | 中 | **推奨** |

両MTF panelが選択された場合は両modeを実行・cacheし、片方だけならそのmodeだけを実行する。Project/Snapshotでは旧`mtf_mode`を読める状態を残し、新形式は`analysis_panels`または`mtf_modes[]`を正本とする。

### 2.5 R101 navigation shellへの影響

- `ActiveTab`へ`project_settings`を追加し、5画面到達E2Eを6画面へ更新する。
- expanded/collapsed閾値、1366px context drawer、中央chart寸法は変更しない。
- navigation persistence、keyboard/tooltip、ja/en/pseudo、各viewport到達性を直接テストする。
- Project Settingsでは右drawerを既定閉にする案が妥当だが、既定動作変更はE2Eで固定する。
- 画面追加自体は小〜中、state ownership変更を含む全体は中〜大。

## 3. field定義のエンジン仕様案

### 3.1 型名

現行互換のため、次を推奨する。

```text
angular
image_height_paraxial
image_height_real
```

`angular`を`angle`へrenameしない。必要なら入力aliasとして`angle`を受けても、正規化・出力は`angular`とする。

### 3.2 推奨schema

```yaml
fields:
  - id: center
    type: image_height_paraxial
    target:
      mode: sensor_fraction
      y: 0.0
      z: 0.0

  - id: field_70
    type: image_height_paraxial
    target:
      mode: sensor_fraction
      y: 0.7
      z: 0.7

  - id: edge
    type: image_height_paraxial
    target:
      mode: sensor_fraction
      y: 1.0
      z: 1.0
```

absolute像高も必要なため、targetはunionとする。

```yaml
target:
  mode: absolute_mm
  y_mm: 12.6
  z_mm: 8.4
```

`sensor_fraction`は`y * width_mm/2`、`z * height_mm/2`へ変換する。これによりwidth=Y / height=Z規約、非正方sensor、R123のY/Z個別fitと一致する。UIの`Center / 70% / Edge`は既定方向を`diagonal`とし、Y edge、Z edge、diagonal、custom directionを選べるようにする。

半対角のscalarだけを正本にする案は、Y/Z非対称field、decenter/tilt、縦横比を表現しにくいため採用しない。表示上の像高scalarは`hypot(y_mm, z_mm)`として併記できる。

### 3.3 `image_height_paraxial` resolver

`doc/engine_spec.md`の追記候補:

- 4.3節: angularへの正規化規約とresolved direction。
- 14章: 基準configuration、主波長、EFLの定義。
- 15章: field discriminated unionとresolution lifecycle。
- 21章/API共通request: original fieldとresolved field metadata。
- 27.4節: field direction cache keyとposition invalidation。

基本式:

```text
target_y_mm = fraction_y * sensor.width_mm / 2
target_z_mm = fraction_z * sensor.height_mm / 2
theta_y_deg = atan(target_y_mm / EFL(position, wavelength_ref))
theta_z_deg = atan(target_z_mm / EFL(position, wavelength_ref))
```

全endpointが個別実装せず、API入口の共通resolverを通す。応答metadataには少なくとも次を残す。

```json
{
  "field_id": "field_70",
  "source_type": "image_height_paraxial",
  "target_y_mm": 12.6,
  "target_z_mm": 8.4,
  "theta_y_deg": 14.14,
  "theta_z_deg": 9.54,
  "reference_position": "wide",
  "reference_wavelength_nm": 587.56,
  "resolution_method": "paraxial_efl"
}
```

afocal、sensorなし、EFLが0または非有限、target不正は構造化errorにする。新codeは`/v1/meta` enumerationsへ追加する。

### 3.4 `image_height_real`機構

目的は、指定sensor点へ主光線が到達する物体側角度`theta_y/theta_z`を求めること。未知数2、残差2の非線形solveとなる。

```text
F(theta_y, theta_z) =
  [chief_sensor_y - target_y,
   chief_sensor_z - target_z]
```

各反復で必要な処理:

1. paraxial resolverを初期値にする。
2. R116と同じfull ray aimingでstop中心を通るchief rayを求める。
3. sensor交点のY/Z残差を計算する。
4. 有限差分または既存candidate-axis/Jacobian基盤で2x2 Jacobianを作る。
5. damping付きNewton/Broydenで更新する。
6. 角度差と像高残差の両方を収束判定する。

R116の知見は「有効瞳中心を狙うchief ray」を安定に作る点で再利用できる。ただしfield solveはその外側の反復であり、aiming失敗、vignetting、歪曲の非単調性、複数解を別途扱う必要がある。

推奨規模: 大。初期対象はfocal、同軸、単一position、circle pupil、sensor内targetへ限定し、失敗時は`field_solve_failed`、`field_target_unreachable`等の構造化issueを返す。

### 3.5 導入案比較

| 案 | 内容 | UI | Engine | 評価 |
|---|---|---:|---:|---|
| UI換算のみ | UIが像高からangularへ変換して現APIへ送る | 中 | なし | 試作向け。clientごとに意味がずれるため恒久採用しない |
| 近軸resolver | engineが`image_height_paraxial`を共通解決 | 中 | 中 | **初回製品実装に推奨** |
| 実光線まで一括 | paraxial/realを同時追加 | 大 | 特大 | 検証境界が広すぎるため非推奨 |

## 4. zoom / multi-configuration

同じ像高targetでもpositionごとにEFLが変わるため、resolved angleはpositionの派生値とする。

- source field definitionはProject/AnalysisConditionに保持する。
- `zoom_position`またはgroup position変更時にfield resolverを再実行する。
- resolved angleをsourceへ書き戻さない。
- result、Snapshot、Compareにはsource targetとresolved angleの両方を保存・表示する。
- cache keyはsystem hash、runtime configurationのposition部分、field definition、reference wavelengthを含める。
- R121 Position Managerの切替時は`analysis_dirty` / `result_stale`とし、次回Preview/Analysis requestで解決する。
- 将来のR5 multi-configurationでは各configurationを独立resolveし、同じfield IDでもconfiguration別resolved metadataを持つ。

「全positionで同一物体角を保つ」用途も必要なため、`angular`は今後も第一級fieldとして残す。

## 5. 永続化と互換

### 5.1 保存先の案

| 案 | 保存先 | 評価 |
|---|---|---|
| OpticalSystem | wavelength/field/policyをsystemへ格納 | 光学処方と評価設定が混ざるため非推奨 |
| AnalysisConditionのみ | 現在と同じ | 実効条件は保存できるがProject既定とoverrideを区別できない |
| Project defaults＋AnalysisCondition effective/override | Projectに基準、AnalysisConditionに差分と実効値 | **推奨** |

推奨概念schema:

```json
{
  "project_settings": {
    "spectral_definition": {},
    "field_definitions": [],
    "image_plane_policy_default": {},
    "evaluation_profiles": {}
  },
  "analysis_conditions": [{
    "overrides": {},
    "effective": {}
  }]
}
```

sensor寸法そのものはOpticalSystemに残す。Project Settings画面はその値を参照・編集する入口であり、所有権を移さない。

### 5.2 R122 Project / Snapshot

- `project_schema_version`をminor更新し、`project_settings`をoptional追加する。
- 旧Project読込時は`analysis_conditions[0]`からProject defaultsを合成する。
- 新Project exportはProject defaultsとoverrideを保存する。
- Snapshotは再現性優先でsource definition、effective angular fields、resolved metadata、runtime configurationを固定保存する。
- Snapshot restoreでは保存済みeffective値を表示した上で、再実行時にresolverで再計算し、差があればcompatibility warningを出す。
- 単一JSONの現行R122契約を維持し、zip対応とは分離する。

### 5.3 既存プリセット

- P001〜P013の既存`angular` fieldsはそのまま有効とし、自動変換しない。
- `preset_label: image_height_70pct`は表示互換metadataとして読める状態を残す。
- 新規または明示移行済みpresetから`image_height_paraxial`を使用する。
- 移行ツールは現在角度と参照EFLからtarget像高を提示し、人間が確認して変換する。暗黙変換はしない。
- afocal presetはangularを維持する。像高modeはfocal＋sensorを前提とする。

## 6. 規模と依存関係

| 作業 | UI | Engine/API | Schema/spec | 規模 | 依存 |
|---|---|---|---|---:|---|
| Project Settings第6画面 | 必要 | 不要 | UI spec | 中 | R101 E2E更新 |
| wavelength/field基準値の移設 | 必要 | 不要 | Project state | 中 | 第6画面 |
| Evaluation Controls改名・override表示 | 必要 | 不要 | AnalysisCondition | 中 | Project defaults |
| MTF panel駆動化 | 必要 | endpoint追加不要 | Snapshot互換 | 中 | R117 panel model |
| `image_height_paraxial`型 | 必要 | 必要 | engine 4.3/14/15/21/27 | 中〜大 | field resolver設計 |
| position別再解決 | 表示必要 | 必要 | configuration metadata | 中 | R121/R5 |
| Project/Snapshot schema更新 | 必要 | 不要 | UI 10/22/23 | 中 | defaults/override確定 |
| `image_height_real` | 必要 | 必要 | engine 15/16/API | 大〜特大 | paraxial型、R116 aiming |

## 7. 推奨段階導入

1. **仕様確定**: Project defaults / override、`angular`名称維持、target Y/Z規約、MTF panel駆動を正本へ反映する。
2. **Engine paraxial field**: 共通field resolver、metadata、構造化error、全endpoint横断testを追加する。
3. **Persistence**: `project_settings`、AnalysisCondition override、旧Project/Snapshot migrationを実装する。
4. **UI shell**: Project Settings第6画面、基準設定移設、Evaluation Controls、R101 viewport E2Eを実装する。
5. **MTF整理**: グローバルmodeをpanel駆動へ置換し、旧snapshotを読み替える。
6. **Preset opt-in**: 代表focal preset 1件でimage-height modeを検証後、対象presetを段階移行する。
7. **Real field solve**: 別フェーズで限定scopeから開始する。

Engine resolverをUIより先に入れることで、UIが一時的な独自角度変換の正本になることを防ぐ。

## 8. 人間が判断すべき事項

1. 左navigationの名称を`Project Settings` / `プロジェクト基本設定`で確定するか。
2. Project defaults＋明示overrideの2層モデルを採用するか。
3. `Analysis Conditions`の後継名を`Evaluation Controls` / `評価コントロール`とするか。
4. グローバルMTF modeを廃止し、R117 panel選択へ一本化するか。
5. field識別子は現行`angular`を維持し、`angle`へrenameしない方針でよいか。
6. 0/70/100%の既定方向をsensor diagonalとし、保存はY/Z別fractionにするか。
7. absolute mm targetも初回schemaに含めるか。
8. `image_height_paraxial`をエンジン共通resolverとして先行実装するか。
9. 既存presetはangularのまま保持し、代表presetからopt-in移行するか。
10. `image_height_real`を別フェーズの大規模タスクとして分離するか。

## 9. 今回変更していないもの

- 製品コード
- テスト
- `doc/ui_spec.md`
- `doc/engine_spec.md`
- Project/Snapshot schema
- preset field値
- active API/UIプロセス
