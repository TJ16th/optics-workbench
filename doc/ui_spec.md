# Optics Workbench UI 要求仕様・技術仕様書 v0.4

## 改訂履歴

### R92追記（Through-focus MTF View）

Analysisタブへ標準解析と切り替え可能なThrough-focus MTF Viewを追加した。推奨fieldごとに独立パネルを表示し、10/30 lp/mmのM/S曲線を比較できる。

### v0.4

エンジンv2.4の視覚評価コンポジットに対応した。`visual_evaluation.mode: instrument_and_retinal`の系では、Analysisタブに装置側`instrument`と網膜側`retinal`のセグメント切替を表示し、角度spot/PSF/MTF・射出瞳・アイレリーフと、網膜spot/PSF/MTFを単位系を混在させず表示する。初期UIプリセット`V001`は簡約Gullstrand眼、587.56 nm単色、4 mm固定瞳、無調節、平面網膜に限定する。

### v0.3

日英対応（i18n）とヘルプ・用語集システムを仕様化した。

1. **27章を全面改訂**し、多言語対応（i18n）・3階層ヘルプ（用語ツールチップ / ヘルプドロワー / エラー解説）・用語集リソースの一元管理を定義した。翻訳境界（エンジン由来の識別子は翻訳しない）、数値・単位の非翻訳規約（小数点はピリオド固定）、用語集スキーマ、`/v1/meta` 列挙とのカバレッジCI、Toggletipによるアクセシビリティ対応を含む。
2. **19.2のエラー構造をコードベースに改訂**した。エンジンは機械可読コード＋パラメータ＋英語フォールバックを返し、表示文言はUI側がエラーカタログ（用語集リソースの一部）から組み立てる（エンジン仕様v2.3 26.10節と対応）。
3. **5章の技術スタックにi18nライブラリ（react-i18next）を追加**した。
4. **28.5に i18n / ヘルプの受け入れ条件を追加**した。
5. 用語集シードファイル `glossary.ja.json` / `glossary.en.json`（初稿）を本仕様に付属させる。
6. **17.2 Optical Layout Viewの描画規約を追記**した。光線LOD、有効径境界、ガラス領域、接合面、負エッジ厚警告の表示方針を定義した。

### v0.2

### v0.2

エンジン仕様v2.1との突き合わせレビューに基づき、優先度の高い4点を修正した。

1. **image_plane_policyの実装責務をエンジン側と確定**（14章）。像面依存の解析はエンジンAPIへのパラメータ送信1回で完結し、UIは2段呼び出しのオーケストレーションを行わない（エンジン仕様v2.1 21.5節）。apply_to: sensor_surfaceのみUI側のwrite-back操作として再定義し、操作手順（solve結果→system編集→system_dirty→validate/register）を規約化した。
2. **snapshotのartifact永続化ポリシーを新設**（22.4節）。エンジンartifactは揮発性（TTL・再起動で消滅：エンジン仕様v2.1 26.8節）であるため、snapshot作成時に必要データを `GET /v1/artifacts` で取得して埋め込む規約、partial snapshotの扱い、zip export形式を定義した。
3. **P005プリセットの数値を近軸検証済みの値に修正**（9.4節）。旧値は実像を結ばず（|f2| < f1-d）副鏡ケラレもあったため、EFL 3000mm / F15構成へ差し替えた（エンジン仕様v2.1 6.3節の例と同一）。あわせて9.1節にプリセット数値の実装時検証規約を追加し、28.2節のP005受け入れ条件を更新した。
4. **version確認をGET /v1/meta参照に更新**（23.3節・26.2節）。起動時のhealth/meta取得、api_schema_versionのmajor/minor不一致時の挙動、capabilitiesによるUI機能のdisable規約を定義した。

### v0.1

光学シミュレーションエンジン仕様 v2 を操作・可視化するためのUIビューア仕様として初版を定義した。

主な定義内容は以下。

1. UIターゲットを「エンジン開発者・検証者向けの操作卓を主軸にしつつ、教育用途にも転用できる光学ビューア」と定義。
2. UIはエンジン内部を直接importせず、HTTP API経由で操作する方針を定義。
3. React + TypeScript + Vite + Carbon Design System を基本技術スタックとして定義。
4. エンジン・UI・schema・presetをmonorepo内で分離管理するディレクトリ構成を定義。
5. 6つの初期プリセット光学系を定義。
6. 物理センサー面と解析用評価面を分離し、`image_plane_policy` を定義。
7. field指定方法として、物体側角度指定、センサー近軸由来、逆光線追跡由来を定義。
8. UI状態モデル、dirty state、validation/register規約、job/error/large data handlingを定義。
9. 可視化コンポーネント、単位、表示精度、Raw JSON/YAML編集、保存/export、versioning、テスト仕様を定義。

---

# 0. 文書の目的

本書は、光学シミュレーションエンジンを操作・検証・可視化するためのUIアプリケーション **Optics Workbench** の要求仕様・技術仕様を定義する。

本UIは、エンジン仕様で定義された以下の機能を、人間が操作・確認できる形で提供する。

- 光学系定義の読み込み・確認・編集
- API requestの生成・実行
- API responseの整形表示
- 光線経路・収差・PSF・MTF・周辺光量・瞳などの可視化
- validation error / numerical error / aiming failed等の確認
- プリセット光学系を用いた教育・検証
- snapshot保存と条件比較
- Raw JSON / YAMLによる開発者向け確認

本UIは、商用光学設計CADの完全代替ではなく、光学エンジンを正しく使い、挙動を理解し、検証するための作業台である。

---

# 1. UIの目的

## 1.1 基本目的

Optics Workbenchの基本目的は以下である。

```text
光学系を選ぶ・作る・少し変える
  ↓
エンジンAPIに正しい入力を渡す
  ↓
返ってきた値を光学的に意味のある形で見る
  ↓
条件差分を比較する
```

したがって、本UIは単なるJSON入力フォームではなく、以下を統合する。

```text
API操作卓
+
光学可視化ビューア
+
解析結果デバッガ
+
教育用プレビュー環境
```

## 1.2 主なユースケース

1. プリセット光学系を読み込み、光線図・近軸量・spot等を確認する。
2. Surface TableでR/D/Nを変更し、validate/register後に再解析する。
3. 絞り径、フォーカス群、ズーム位置、field、波長を変更して結果の変化を見る。
4. 近軸像面、RMS best、MTF30 bestなどの評価面を切り替えて解析する。
5. sensor固定時とbest focus評価時の結果差を比較する。
6. API request / response JSONを確認し、エンジン側の入出力を検証する。
7. validation errorやray aiming失敗を、光線図・surface table・raw JSONで追跡する。
8. snapshotを保存し、A/B比較する。
9. 教育用に光線図・spot・MTFなどをPNG/SVGで出力する。

---

# 2. ターゲットユーザー

## 2.1 Primary target

| 対象 | 主な目的 |
|---|---|
| エンジン開発者 | API入力・出力・validation・trace結果を確認する |
| 光学シミュレーション検証者 | 符号規約、ray aiming、近軸量、収差結果を確認する |
| 個人開発者 | プリセットを元に光学系を触り、結果を可視化する |

## 2.2 Secondary target

| 対象 | 主な目的 |
|---|---|
| 光学初学者 | 光線の曲がり方、絞り、焦点、収差を視覚的に理解する |
| 写真・双眼鏡・望遠鏡愛好家 | レンズ構成や瞳、周辺光量、見え味の違いを見る |
| 教育コンテンツ制作者 | 光線図や評価図を教材素材として出力する |

## 2.3 対象外

| 対象外 | 理由 |
|---|---|
| 商用光学設計CADの完全代替 | 公差解析・製造性・高度最適化までは初期対象外 |
| 完全ノーコード教材アプリ | Raw JSONや詳細設定を隠しすぎるとエンジン検証ができない |
| 3Dレンダリングアプリ | 実写風画像生成やゴースト・フレア表現は主目的ではない |
| 最適化専用UI | 最適化は外部エンジン主導。UIは評価・比較・デバッグ中心 |

---

# 3. UI設計原則

## 3.1 Preset first

ユーザーに空の光学系から入力させない。  
まずプリセットを選び、そこから編集する構成とする。

```text
preset load
  ↓
validate
  ↓
register
  ↓
preview / analysis
  ↓
edit / compare
```

## 3.2 Raw JSON is always available, but not mandatory

API request / responseは常に確認できる。  
ただし、通常操作はフォーム・テーブル・スライダーから行う。

```text
フォームで編集
  ↓
生成されたrequest JSONを確認可能
  ↓
API実行
  ↓
整形された結果を見る
  ↓
raw response JSONも確認可能
```

## 3.3 Validation first

解析実行前にvalidate状態を明示する。  
光学系がdirtyの場合は、analysis APIを実行しない。

## 3.4 Visual and numeric must be linked

図、表、JSON、エラー箇所は相互リンクさせる。

例：

- 光線図でsurfaceを選ぶとSurface Tableの該当行を選択する。
- validation errorでS4-S5間の負gapが出たら、光線図上でも該当位置を表示する。
- rayを選択すると、ray path tableでも該当rayを表示する。

## 3.5 Snapshot and compare are core

snapshot / compareは後付けではなく、UIの中核機能とする。  
光学系操作では、変更前後の差分を見られることが重要である。

---

# 4. エンジンとビューアの関係

## 4.1 基本方針

本プロジェクトは、光学シミュレーションエンジンとOptics Workbench UIを、同一リポジトリ内の別アプリケーションとして管理する。

```text
optics-workbench/
  apps/
    engine-api/        # 光学エンジンAPI
    workbench-ui/      # ビューアUI
  packages/
    optics-schema/     # OpenAPI schema / generated types
    shared-presets/    # プリセット光学系
  docs/
    engine_spec.md
    ui_spec.md
    design_system.md
```

ビューアUIはエンジン内部のPythonモジュールを直接importしない。  
ビューアは常にHTTP APIを経由してエンジンを操作する。

```text
workbench-ui
  ↓ HTTP / JSON
engine-api
  ↓ Python import
optics_engine
```

## 4.2 責務分離

| 項目 | エンジン責務 | UI責務 |
|---|---|---|
| 光線追跡 | 実行する | 結果を描画する |
| 近軸計算 | 実行する | 数値カード・表で表示する |
| validation | 判定する | エラー位置を表示・誘導する |
| ray aiming | 実行する | mode選択・failed件数表示 |
| CompiledSystem cache | 管理する | cache hit/missを表示する |
| surface定義 | 読み込む・検証する | 編集・表表示する |
| material定義 | 屈折率計算する | 硝材テーブルとして表示する |
| API request生成 | 受け取る | UI状態から生成する |
| API response | 返す | 整形表示・可視化する |
| プリセット光学系 | 正本として読み込む | 一覧・説明・推奨解析を表示する |
| Snapshot | 任意で保存APIを提供 | 基本的にUI側で保持する |

## 4.3 禁止事項

以下は禁止する。

```text
workbench-ui が optics_engine Python module を直接importする
workbench-ui が独自に光線追跡を再実装する
workbench-ui がvalidation結果を独自判定する
engine-api がReact UIの状態構造に依存する
プリセット光学系をUI専用形式だけで保持する
API responseの型をUI側で手書き複製する
```

---

# 5. 開発言語・実装環境

## 5.1 推奨技術スタック

| 領域 | 採用技術 | 理由 |
|---|---|---|
| UI言語 | TypeScript | API入出力、surface table、result objectの型安全性を確保する |
| i18n | react-i18next | 日英切替。リソースはビュー単位namespace＋用語集namespace（27章）【v0.3追加】 |
| UIフレームワーク | React | コンポーネント単位でSystem/Preview/Analysis/Debug画面を構築しやすい |
| ビルド環境 | Vite | 軽量で開発サーバーの反応が速い |
| デザインシステム | Carbon Design System / Carbon React | 高密度な技術UI、フォーム、テーブル、タブ、状態表示に向く |
| APIサーバー | FastAPI | Python光学エンジンと接続しやすく、OpenAPI生成に向く |
| API通信 | TanStack Query | API結果、job状態、system_id、cache状態を扱いやすい |
| テーブル | TanStack Table + Carbon styling | surface table / material table / result tableを柔軟に扱える |
| 汎用グラフ | Plotly.js | MTF、field curvature、relative illuminationなどに使う |
| 独自光学描画 | SVG + D3 | 光線図、レンズ断面、瞳表示などに使う |
| JSON表示 | Monaco Editor または軽量JSON viewer | request / response JSONの確認・コピー |
| E2Eテスト | Playwright | APIを含むUI操作の回帰確認 |
| 単体テスト | Vitest / pytest | UIロジックとPython APIを分けてテスト |
| 整形・Lint | ESLint / Prettier / Ruff | TypeScript/Python双方の品質維持 |

## 5.2 アプリ形態

初期版はWebアプリとして実装する。

```text
Browser
  ↓
Optics Workbench UI
  ↓ http://localhost:8000
FastAPI optics engine
```

将来、ローカルアプリとして配布する場合はTauriを候補とする。  
初期版ではElectronは採用しない。

## 5.3 推奨ローカル環境

| 項目 | 推奨 |
|---|---|
| OS | Windows 11 / macOS / Linux |
| Node.js | LTS版 |
| Package manager | pnpm |
| Python | 3.12以上 |
| API framework | FastAPI |
| Python numerical stack | NumPy / SciPy / Numba |
| UI dev server | Vite |
| Browser | Chrome / Edge / Firefox |
| Version control | Git |
| CI | GitHub Actions等 |

---

# 6. リポジトリ構成

```text
optics-workbench/
  apps/
    workbench-ui/
      src/
        app/
        pages/
        features/
          system/
          preview/
          analysis/
          compare/
          debug/
        optics-views/
          layout-view/
          ray-view/
          spot-view/
          mtf-view/
          pupil-view/
        api/
          generated/
          queries/
          mutations/
        model/
        design-system/
        utils/

    engine-api/
      optics_engine/
        core/
        paraxial/
        geometry/
        materials/
        system/
        tracing/
        analysis/
        visual/
        optimization/
        education/
        api/
        io/
        tests/

  packages/
    optics-schema/
      openapi/
      generated-types/
    shared-presets/
      optical_systems/
      metadata/
    ui-components/
      tokens/
      carbon-overrides/

  docs/
    engine_spec.md
    ui_spec.md
    design_system.md
    api_mapping.md
    preset_spec.md
    testing_spec.md
    development_setup.md
```

## 6.1 API Schema共有

FastAPI / Pydantic schemaからOpenAPIを生成し、UI側はTypeScript型を生成する。

```text
engine-api
  ↓ generate OpenAPI
packages/optics-schema/openapi.json
  ↓ generate TypeScript client/types
workbench-ui/src/api/generated/
```

正本はPython/FastAPI/Pydantic schemaとする。  
UI側でrequest/response型を手書きしない。

---

# 7. Design System

## 7.1 採用方針

本UIのデザインシステムは、Carbon Design Systemを主参照とする。

ただし、光学シミュレーション特有の解析ビュー、光線図、収差図、PSF/MTF表示、Raw JSON表示を含むため、Carbonをそのままコピーするのではなく、以下の方針で独自の **Optics Workbench Design System** を定義する。

- 高密度な業務UI・テーブル・フォーム・状態表示はCarbonを参照する。
- 日本語UI、アクセシビリティ、エラー文言、フォーム説明はデジタル庁デザインシステムを参照する。
- キャンバス、プロパティパネル、インスペクタ構成はAdobe Spectrum系の制作ツールUIも参考にする。
- グラフ、光線図、PSF、MTF、瞳表示は独自コンポーネントとして定義する。

## 7.2 テーマ

初期版では以下をサポートする。

| Theme | 内容 |
|---|---|
| Light | 標準 |
| Dark | 長時間作業・光線図表示向け |

## 7.3 UI密度

| モード | UI密度 | 用途 |
|---|---:|---|
| Preview | 中 | 教育・確認用 |
| Analysis | 高 | 数値評価 |
| Debug | 非常に高 | API・検証・profiling |
| Presentation | 低 | 教材・説明資料出力用、将来拡張 |

## 7.4 状態tokens

| 状態 | 用途 |
|---|---|
| valid | validate OK |
| warning | warning |
| error | error |
| dirty | 未validate変更 |
| stale | 結果が古い |
| running | API実行中 |
| selected | 選択中 |
| inactive | 非表示・無効 |

状態は色だけで表現せず、ラベル・アイコンも併用する。

---

# 8. 画面構成

## 8.1 基本レイアウト

```text
┌────────────────────────────────────────────┐
│ Header: Preset / System name / Validate状態 │
├──────────────┬─────────────────┬───────────┤
│ 左ペイン      │ 中央ビュー        │ 右ペイン   │
│ System Tree  │ Optical Layout   │ Controls  │
│ Presets      │ Ray / Plot View  │ API Params│
├──────────────┴─────────────────┴───────────┤
│ 下ペイン: Results / Tables / Raw JSON / Logs │
└────────────────────────────────────────────┘
```

## 8.2 タブ構成

| タブ | 役割 |
|---|---|
| System | 光学系・surface・material・groupの確認と編集 |
| Preview | 教育用・確認用の軽量光線表示 |
| Analysis | spot / MTF / distortion / illuminationなどの解析 |
| Compare | snapshot比較 |
| Debug | raw JSON / validation / profiling / trace log |

## 8.3 Systemタブ

- プリセット選択
- surface table
- material table
- group table
- aperture / sensor / eye_reference設定
- validate結果
- system_id / system_hash表示

## 8.4 Previewタブ

- 光線図
- aperture slider
- focus slider
- zoom_position切替
- field切替
- ray count少なめ
- ray aiming mode切替
- blocked ray表示

## 8.5 Analysisタブ

- endpoint選択
- field set
- wavelength set
- sampling設定
- image plane policy
- 実行ボタン
- 結果プロット
- metadata表示

`visual_evaluation.mode: instrument_and_retinal`の系では、通常の写真レンズ解析実行に代えて模型眼評価を実行する。結果領域にはCarbon ContentSwitcherによる`instrument` / `retinal`切替を置く。

- `instrument`: 角度spot RMS（arcmin）、射出瞳径（mm）、アイレリーフ（mm）、角度PSF、角度MTF（cycles/degree）
- `retinal`: 網膜spot RMS（µm）、網膜重心（mm）、位置PSF、MTF（lp/mm）

識別子`instrument` / `retinal`はAPI schema上では翻訳せず、表示ラベルのみi18nリソースから解決する。未実装の模型眼・曲面網膜・調節状態をUIで選択可能にしてはならない。

## 8.6 Compareタブ

- snapshot一覧
- A/B選択
- paraxial差分
- spot重ね表示
- MTF重ね表示
- relative illumination比較
- raw condition diff

## 8.7 Debugタブ

- request JSON
- response JSON
- validation raw output
- profiling
- cache hit/miss
- aiming iteration count
- failed ray status集計
- trace path table

---

# 9. プリセット光学系

## 9.1 プリセットの目的

初期版では、代表的な光学系を12個内蔵する。このうち通常のUIプリセット一覧には11個を表示し、反射系検証用のP005は定義・テストカバレッジを維持したまま非表示とする。

目的は以下。

1. エンジン機能の確認
2. UIコンポーネントの動作確認
3. 教育用デモ
4. API request / responseの標準サンプル
5. Golden Testとは別の、操作確認用サンプル

本プリセットは、商用設計値や文献完全再現値ではない。  
MVP段階では「光学的に破綻しにくい初期値」とし、Golden Test用の厳密データは別途定義する。

**数値の検証規約【v0.2追加】**

各プリセットの数値は、実装時に近軸トレース（/v1/analysis/paraxial）と代表fieldの実光線追跡で検証してから凍結する。特に、(1) 像面位置と最終thicknessの整合、(2) 最外field光線がセンサー有効域に到達すること、(3) 各面の有効径が軸上・最外光束をケラらないこと、を確認する。最終空気間隔は必要に応じて best-focus solve で調整した値を採用する。

## 9.2 共通波長

```yaml
wavelengths_nm:
  primary: 587.56
  samples: [486.13, 546.07, 587.56, 656.27]
```

## 9.3 共通硝材データ

Sellmeier式：

```text
n(λ)^2 - 1 =
B1 λ^2 / (λ^2 - C1)
+ B2 λ^2 / (λ^2 - C2)
+ B3 λ^2 / (λ^2 - C3)
```

λはµm単位。

### AIR

```yaml
- id: AIR
  type: constant
  n: 1.0
```

### N-BK7

```yaml
- id: N-BK7
  type: sellmeier
  B: [1.03961212, 0.231792344, 1.01046945]
  C: [0.00600069867, 0.0200179144, 103.560653]
```

### N-F2

```yaml
- id: N-F2
  type: sellmeier
  B: [1.34533359, 0.209073176, 0.937357162]
  C: [0.00997743871, 0.0470450767, 111.886764]
```

## 9.4 プリセット一覧

### P001: Ideal Thin Lens 50mm F4

目的：焦点距離、F値、画角、絞り、センサー位置の関係を見る。

| No | id | kind | surface_type | R / f | D | N | semiD | aperture |
|---:|---|---|---|---:|---:|---|---:|---|
| 1 | STOP | aperture_stop | plane | 0 | 0.0 | AIR | 6.25 | circle 6.25 |
| 2 | TL1 | thin_lens | ideal | f=50.0 | 50.0 | AIR | 12.5 | - |
| 3 | IMG | sensor | plane | 0 | 0.0 | - | - | 36×24 |

期待値：

- EFL ≒ 50 mm
- F number ≒ 4
- BFL ≒ 50 mm
- distortion ≒ 0
- sensor面と近軸像面がほぼ一致

### P002: N-BK7 Biconvex Singlet 50mm Demo

目的：単玉レンズによる屈折、球面収差、色収差、spot diagramの基本確認。

| No | id | kind | surface_type | R | D | N | semiD | aperture |
|---:|---|---|---|---:|---:|---|---:|---|
| 1 | STOP | aperture_stop | plane | 0 | 2.0 | AIR | 8.0 | circle 8.0 |
| 2 | S1 | refractive | spherical | 50.0 | 5.0 | N-BK7 | 15.0 | - |
| 3 | S2 | refractive | spherical | -50.0 | 46.5 | AIR | 15.0 | - |
| 4 | IMG | sensor | plane | 0 | 0.0 | - | - | 36×24 |

期待値：

- P001よりspotが広がる
- 絞りを開くと球面収差が増える
- F線/C線/d線で焦点位置が変わる
- 白色spotは単色spotより広がる

### P003: Achromat Doublet 100mm Demo

目的：クラウンガラスとフリントガラスによる色収差補正の基本確認。

| No | id | kind | surface_type | R | D | N | semiD | aperture |
|---:|---|---|---|---:|---:|---|---:|---|
| 1 | STOP | aperture_stop | plane | 0 | 5.0 | AIR | 12.5 | circle 12.5 |
| 2 | S1 | refractive | spherical | 61.47 | 7.5 | N-BK7 | 18.0 | - |
| 3 | S2 | refractive | spherical | -44.64 | 3.0 | N-F2 | 18.0 | - |
| 4 | S3 | refractive | spherical | -129.94 | 93.0 | AIR | 18.0 | - |
| 5 | IMG | sensor | plane | 0 | 0.0 | - | - | 36×24 |

期待値：

- P002に比べて軸上色収差が小さい
- EFLは約100 mm級
- longitudinal aberration graphが表示可能

### P004: Double Gauss 50mm F1.4 Demo

目的：対称8面の高速写真レンズ構成で、spot、MTF、歪曲、像面湾曲、非点収差を確認する。

| No | id | kind | surface_type | R | D | N | semiD | aperture |
|---:|---|---|---|---:|---:|---|---:|---|
| 1 | S1 | refractive | spherical | 58.0 | 5.0 | N-BK7 | 22.5 | - |
| 2 | S2 | refractive | spherical | 200.0 | 2.0 | AIR | 22.0 | - |
| 3 | S3 | refractive | spherical | -190.0 | 2.5 | N-F2 | 21.75 | - |
| 4 | S4 | refractive | spherical | -75.0 | 5.0 | AIR | 21.75 | - |
| 5 | STOP | aperture_stop | plane | 0 | 5.0 | AIR | 17.75 | circle 17.75 |
| 6 | S5 | refractive | spherical | 75.0 | 2.5 | N-F2 | 19.0 | - |
| 7 | S6 | refractive | spherical | 190.0 | 2.0 | AIR | 18.75 | - |
| 8 | S7 | refractive | spherical | -200.0 | 5.0 | N-BK7 | 18.75 | - |
| 9 | S8 | refractive | spherical | -58.0 | 32.15 | AIR | 18.5 | - |
| 10 | IMG | sensor | plane | 0 | 0.0 | - | - | 36×24 |

推奨fieldはcenter `0 deg`、70%像高 `7.036366 deg`、edge-y `10 deg`とする。

期待値（主波長587.56nm）：

- EFL ≒ 49.978 mm、BFL ≒ 36.889 mm、F number ≒ 1.408
- 軸上best-focus相当の最終空気間隔は32.15 mm、center 81-ray spot RMS ≒ 0.483460 mm
- 4レンズのedge thicknessは約1.879 / 0.526 / 1.046 / 2.828 mmで、すべて正
- 3 field × 3 wavelength × 9 samplesの実光線81本がIMGへ到達する
- 25 samplesではalive 219 / aiming_failed 6 / blocked 0
- center / mid / edgeでspot形状が変化する
- MTF、distortion、field curvature、relative illuminationが表示可能
- 周辺fieldで像面湾曲・非点収差が見える

### P005: Coaxial Cassegrain Telescope Demo

目的：ミラー、負thickness、propagation_sign、annulus遮蔽、反射望遠鏡の評価確認。

通常のUIプリセット一覧では非表示とする。プリセット定義とエンジン/API・回帰テストは反射系検証用として維持する。

【v0.2修正】旧値（M2 R=-500 / d=700 / 像距離800 / M2 semiD 25）は近軸検算の結果、|f2|=250 < f1-d=300 のため実像を結ばず、軸上光束（M2位置で半径30mm）が副鏡径25mmでケラれていた。以下は近軸検証済みの値である（エンジン仕様v2.1 6.3節と同一）。

| No | id | kind | surface_type | R | D | N | semiD | aperture |
|---:|---|---|---|---:|---:|---|---:|---|
| 1 | ENTRANCE | aperture_stop | plane | 0 | 0.0 | AIR | 100.0 | annulus inner 40 / outer 100 |
| 2 | M1 | mirror | spherical | -2000.0 | -650.0 | AIR | 100.0 | - |
| 3 | M2 | mirror | spherical | -1050.0 | 1050.0 | AIR | 40.0 | - |
| 4 | IMG | sensor | plane | 0 | 0.0 | - | - | 24×24 |

近軸検算（口径半径100mmのマージナル光線）：

```text
y=100, u=0
M1後 (f1=1000): u = -0.1
M2位置(650mm): y = 35  → semiD 40内、ケラレなし
M2後 (|f2|=525): u = -0.1 + 35/525 = -0.0333
結像: M2の1050mm後 = M1頂点の+X側400mm
EFL = 3000 mm, F/15
```

期待値：

- M1後、光線は-X方向へ伝播する
- M2後、光線は+X方向へ伝播する
- EFL ≒ 3000 mm、F# ≒ 15
- 像面はM1頂点の+X側 約400 mm（sensor位置と一致）
- 軸上光束がM2でケラれない
- annulus中央遮蔽が表示される
- negative thicknessがvalidation上正常に扱われる

### P006: Keplerian Telescope 10x Afocal Demo

目的：afocal系、eye_reference、角倍率、射出瞳、アイレリーフ、角度spot、angular MTFの確認。

| No | id | kind | surface_type | R / f | D | N | semiD | aperture |
|---:|---|---|---|---:|---:|---|---:|---|
| 1 | OBJ_STOP | aperture_stop | plane | 0 | 0.0 | AIR | 25.0 | circle 25.0 |
| 2 | OBJ | thin_lens | ideal | f=200.0 | 200.0 | AIR | 25.0 | - |
| 3 | FIELD_STOP | mechanical_aperture | plane | 0 | 20.0 | AIR | 8.0 | circle 8.0 |
| 4 | EYEPIECE | thin_lens | ideal | f=20.0 | 0.0 | AIR | 12.0 | - |
| 5 | EYE | eye_reference | plane | 0 | 0.0 | - | - | pupil 4.0 |

期待値：

- angular magnification ≒ 10x
- exit pupil diameter ≒ 5 mm
- residual divergence diopter ≒ 0
- focal系とは異なる角度単位で表示される

### P007: Fast Positive-Negative Meniscus Pair Demo

目的：強い正曲率・負曲率を持つ2群メニスカス構成で、Layout Viewの面形状、実光線、spot、ray fan、近軸量を確認する。

| No | id | kind | surface_type | R | D | N | semiD | aperture |
|---:|---|---|---|---:|---:|---|---:|---|
| 1 | S1 | refractive | spherical | 15.0 | 10.5 | N-BK7 | 14.5 | - |
| 2 | S2 | refractive | spherical | 60.0 | 3.0 | AIR | 14.5 | - |
| 3 | STOP | aperture_stop | plane | 0 | 3.0 | AIR | 13.2 | circle 13.2 |
| 4 | S3 | refractive | spherical | -35.0 | 3.0 | N-F2 | 11.5 | - |
| 5 | S4 | refractive | spherical | -100.0 | 26.948477258301352 | AIR | 10.25 | - |
| 6 | IMG | sensor | plane | 0 | 0.0 | - | - | 36×24 |

推奨field：center `0 deg`、70%像高 `1.050122 deg`、edge-y `1.5 deg`。

期待値（現行実装値の近軸・実光線検証）：

- EFL ≒ 47.954 mm
- BFL ≒ 26.948 mm
- F number ≒ 1.816
- 3 field × 3 wavelength × 9 samplesの実光線81本がIMGへ到達する
- S1/S2の正曲率とS3/S4の負曲率がLayout Viewで明確に区別できる
- spot、ray fan、paraxial解析を実行できる

### P008: Real Achromatic Keplerian Telescope Demo

目的：理想薄レンズではなく、N-BK7/N-F2の実曲率アクロマート対物・接眼によるafocal評価、角倍率、射出瞳、アイレリーフ、残存収差を確認する。

| No | id | kind | surface_type | R | D | N | semiD | aperture |
|---:|---|---|---|---:|---:|---|---:|---|
| 1 | STOP | aperture_stop | plane | 0 | 1.5 | AIR | 6.0 | circle 6.0 |
| 2 | O1 | refractive | spherical | 62.5 | 4.0 | N-BK7 | 6.75 | - |
| 3 | O2 | refractive | spherical | -43.0 | 2.0 | N-F2 | 6.5 | - |
| 4 | O3 | refractive | spherical | -125.0 | 108.51795245333561 | AIR | 6.5 | - |
| 5 | E1 | refractive | spherical | 25.0 | 0.4 | N-F2 | 2.5 | - |
| 6 | E2 | refractive | spherical | 8.6 | 0.8 | N-BK7 | 2.5 | - |
| 7 | E3 | refractive | spherical | -12.5 | 20.0 | AIR | 2.5 | - |
| 8 | EYE | eye_reference | plane | 0 | 0.0 | - | - | pupil 5.0 |

推奨field：center `0 deg`、mid-y `0.25 deg`、edge-y `0.5 deg`。

期待値（主波長587.56nm）：

- angular magnification ≒ -5.0x
- exit pupil diameter ≒ 2.4 mm
- eye relief ≒ 20 mm
- 軸上25 samplesの残存divergence ≒ 0.368 D
- 3 field × 3 wavelength × 25 samplesの実光線225本がEYEへ到達し、各面でケラれない
- P006の理想薄レンズ系と比較して、実ガラス・実曲率による残存角度収差を確認できる

### P009: N-BK7 Aspheric Singlet 50mm Demo

目的：P002と同じ曲率・口径・硝材の単玉を基準に、前面をeven asphere化したときの球面収差補正をspotとray fanで比較する。

| No | id | kind | surface_type | R | conic / asphere | D | N | semiD | aperture |
|---:|---|---|---|---:|---|---:|---|---:|---|
| 1 | STOP | aperture_stop | plane | 0 | - | 2.0 | AIR | 8.0 | circle 8.0 |
| 2 | ASP1 | refractive | aspherical_even | 50.0 | k=-1.1792 / A4=-2.4992e-6 | 5.0 | N-BK7 | 9.5 | - |
| 3 | S2 | refractive | spherical | -50.0 | - | 46.9248 | AIR | 9.75 | - |
| 4 | IMG | sensor | plane | 0 | - | 0.0 | - | - | 36×24 |

推奨fieldはP002と同じcenter `0 deg`、70%像高 `9.900092 deg`、edge-y `14 deg`とする。

期待値（主波長587.56nm、center、81-ray hexapolar）：

- P002球面版spot RMS ≒ 0.0466582 mm
- P009非球面版spot RMS ≒ 0.0228093 mm
- P009はP002に対してspot RMSを約49%低減する
- EFL ≒ 49.213 mm、F number ≒ 3.076でP002と近軸powerが一致する
- 3 field × 3 wavelength × 25 samplesの実光線225本がIMGへ到達する
- Layout ViewでASP1の非球面形状を確認できる

### P010: High-Order Aspheric Singlet Inflection Demo

目的：A4 / A6 / A8を含む強いeven asphereを使い、口径内で曲率が2回反転する高次非球面形状をSurface Table、Layout View、spot、ray fanで確認する。

| No | id | kind | surface_type | R | conic / asphere | D | N | semiD | aperture |
|---:|---|---|---|---:|---|---:|---|---:|---|
| 1 | STOP | aperture_stop | plane | 0 | - | 2.0 | AIR | 8.0 | circle 8.0 |
| 2 | ASP1 | refractive | aspherical_even | 50.0 | k=-1 / A4=-1.0e-4 / A6=5.0e-7 / A8=-5.0e-10 | 5.0 | N-BK7 | 9.5 | - |
| 3 | S2 | refractive | spherical | -50.0 | - | 63.175 | AIR | 9.75 | - |
| 4 | IMG | sensor | plane | 0 | - | 0.0 | - | - | 36×24 |

推奨fieldはcenter `0 deg`、70%像高 `6.681170 deg`、edge-y `9.5 deg`とする。

期待値（主波長587.56nm）：

- ASP1のメリジオナル曲率は半径約4.79 mmで正から負、約8.38 mmで負から正へ反転する
- 半径4.0 / 5.0 / 8.0 / 8.5 mmでの曲率はそれぞれ約`+0.0045253 / -0.0010625 / -0.0027000 / +0.0010407 mm^-1`
- EFL ≒ 49.213 mm、BFL ≒ 47.536 mm、F number ≒ 3.076
- 軸上best-focus相当の最終空気間隔は63.175 mm、center 81-ray spot RMS ≒ 0.464633 mm
- 3 field × 3 wavelength × 25 samplesの実光線225本がIMGへ到達する
- Layout ViewでASP1の曲率反転を含む高次非球面形状を確認できる

### P011: Planar-Type 6-Element Double Gauss 50mm F1.4 Demo

目的：外側メニスカス単玉2枚と、内側BK7/F2接合ダブレット2組からなる対称6枚Planar/Xenon型で、高速写真レンズのspot、MTF、歪曲、像面湾曲を確認する。

| No | id | kind | surface_type | R | D | N | semiD | aperture |
|---:|---|---|---|---:|---:|---|---:|---|
| 1 | S1 | refractive | spherical | 58.0 | 5.0 | N-BK7 | 22.5 | - |
| 2 | S2 | refractive | spherical | 200.0 | 2.0 | AIR | 21.75 | - |
| 3 | S3 | refractive | spherical | -190.0 | 2.0 | N-BK7 | 21.75 | - |
| 4 | C1 | refractive | spherical | -240.0 | 2.5 | N-F2 | 21.5 | cemented |
| 5 | S4 | refractive | spherical | -75.0 | 5.0 | AIR | 21.5 | - |
| 6 | STOP | aperture_stop | plane | 0 | 5.0 | AIR | 17.75 | circle 17.75 |
| 7 | S5 | refractive | spherical | 75.0 | 2.5 | N-F2 | 19.0 | - |
| 8 | C2 | refractive | spherical | 240.0 | 2.0 | N-BK7 | 18.75 | cemented |
| 9 | S6 | refractive | spherical | 190.0 | 2.0 | AIR | 18.5 | - |
| 10 | S7 | refractive | spherical | -200.0 | 5.0 | N-BK7 | 18.5 | - |
| 11 | S8 | refractive | spherical | -58.0 | 30.8 | AIR | 18.25 | - |
| 12 | IMG | sensor | plane | 0 | 0.0 | - | - | 36×24 |

推奨fieldはcenter `0 deg`、70%像高 `7.036366 deg`、edge-y `10 deg`とする。

期待値（主波長587.56nm）：

- EFL ≒ 49.983 mm、BFL ≒ 35.363 mm、F number ≒ 1.408
- 軸上best-focus相当の最終空気間隔は30.8 mm、center 81-ray spot RMS ≒ 0.465423 mm
- 6枚のedge thicknessは約1.954 / 2.255 / 0.317 / 0.852 / 2.189 / 2.888 mmで、すべて正
- 3 field × 3 wavelength × 9 samplesはalive 81
- 25 samplesではalive 213 / aiming_failed 12 / blocked 0
- Layout Viewで6枚、2接合面、4群の構成を確認できる

### P012: Tessar-Type 50mm F2.8 Demo

目的：前群の空気間隔単玉2枚と、STOP後のBK7/F2接合ダブレットからなる4枚3群Tessar型で、中口径写真レンズのspot、MTF、歪曲、像面湾曲を確認する。

| No | id | kind | surface_type | R | D | N | semiD | aperture |
|---:|---|---|---|---:|---:|---|---:|---|
| 1 | S1 | refractive | spherical | 91.85 | 5.0 | N-BK7 | 13.0 | - |
| 2 | S2 | refractive | spherical | -334.0 | 1.5 | AIR | 12.5 | - |
| 3 | S3 | refractive | spherical | -250.5 | 3.0 | N-F2 | 12.0 | - |
| 4 | S4 | refractive | spherical | -100.2 | 4.0 | AIR | 11.5 | - |
| 5 | STOP | aperture_stop | plane | 0 | 4.0 | AIR | 8.925 | circle 8.925 |
| 6 | S5 | refractive | spherical | 100.2 | 3.0 | N-F2 | 10.25 | - |
| 7 | C1 | refractive | spherical | 334.0 | 4.0 | N-BK7 | 10.25 | cemented |
| 8 | S6 | refractive | spherical | -100.2 | 39.4 | AIR | 10.25 | - |
| 9 | IMG | sensor | plane | 0 | 0.0 | - | - | 36×24 |

推奨fieldはcenter `0 deg`、70%像高 `7.036366 deg`、edge-y `10 deg`とする。

期待値（主波長587.56nm）：

- EFL ≒ 49.982 mm、BFL ≒ 40.222 mm、F number ≒ 2.800
- 軸上best-focus相当の最終空気間隔は39.4 mm、center 81-ray spot RMS ≒ 0.036863 mm
- 4枚のedge thicknessは約3.911 / 2.602 / 2.632 / 3.317 mmで、すべて正
- 3 field × 3 wavelength × 9 / 25 / 81 samplesはいずれも全光線alive、blocked 0
- Layout Viewで4枚、1接合面、3群の構成を確認できる

---

# 10. UI状態モデル

## 10.1 状態単位

| 状態単位 | 内容 |
|---|---|
| Project | 作業全体。複数の光学系、解析履歴、snapshotを含む |
| OpticalSystemDraft | 現在編集中の光学系定義 |
| SystemRegistration | validate/register済みのsystem_id, system_hash, validation状態 |
| RuntimeConfiguration | variables, zoom_position, decenter, tiltなどの実行時条件 |
| AnalysisCondition | field, wavelength, ray sampling, image plane policyなど |
| AnalysisJob | API実行単位。実行中・成功・失敗・キャンセル状態を持つ |
| ResultBundle | API応答、可視化用データ、metadata、profilingを含む結果単位 |
| Snapshot | ある時点の入力条件と結果を固定保存したもの |
| CompareSet | 複数snapshotを比較するための集合 |
| UISelection | 選択中のsurface, ray, field, wavelength, result itemなど |

## 10.2 ResultBundle

```json
{
  "result_id": "res_20260708_0001",
  "source_job_id": "job_20260708_0001",
  "system_id": "sys_ab12",
  "system_hash": "sha256:...",
  "configuration_hash": "sha256:...",
  "analysis_condition_hash": "sha256:...",
  "endpoint": "/v1/analysis/spot",
  "status": "ok",
  "result": {},
  "metadata": {},
  "profiling": {},
  "created_at": "2026-07-08T08:00:00+09:00"
}
```

## 10.3 Snapshot

Snapshotは、ある時点の作業状態と結果を保存する単位である。

含むもの：

- OpticalSystemDraft
- RuntimeConfiguration
- AnalysisCondition
- ResultBundle
- 埋め込みartifact（比較・再表示に必要なデータ。22.4の規約に従う）【v0.2追加】
- UI表示用metadata
- engine/api/ui/preset version

---

# 11. Dirty State / Validation / Register規約

## 11.1 dirty scope

| dirty scope | 意味 | 必要な処理 |
|---|---|---|
| system_dirty | 光学系構造が変更された | validate → registerが必要 |
| configuration_dirty | variables等の実行時条件が変更された | analysis再実行が必要 |
| analysis_dirty | field/wavelength/sampling等が変更された | analysis再実行が必要 |
| view_dirty | 表示設定のみ変更された | 再描画のみ |
| result_stale | 表示中の結果が現在条件と一致しない | 再実行またはsnapshot化を促す |

## 11.2 操作ごとのdirty規約

| 操作 | dirty scope |
|---|---|
| surface追加・削除 | system_dirty |
| radius_mm変更 | system_dirty |
| thickness_after_mm変更 | system_dirty |
| material_after変更 | system_dirty |
| sensor面の物理位置変更 | system_dirty |
| group定義変更 | system_dirty |
| iris_radius_mmなどvariables変更 | configuration_dirty |
| zoom_position選択変更 | configuration_dirty |
| decenter値変更 | configuration_dirty |
| tilt値変更 | configuration_dirty |
| field変更 | analysis_dirty |
| wavelength変更 | analysis_dirty |
| ray count変更 | analysis_dirty |
| image_plane_policy変更 | analysis_dirty |
| グラフのズーム・パン | view_dirty |
| surface選択 | view_dirty |

## 11.3 system lifecycle

```text
Draft
  ↓ validate
Validated
  ↓ register
Registered
  ↓ structural edit
Dirty
  ↓ validate
Validated
```

## 11.4 result stale表示

現在の入力条件と表示中のResultBundleが一致しない場合、UIはstale状態を表示する。

```text
表示中の結果は現在の条件と一致していません。
変更内容：iris_radius_mm, samples_per_field
```

---

# 12. 光学系編集UI詳細仕様

## 12.1 Surface Table

標準列：

| 列 | 内容 | 編集 |
|---|---|---|
| No | 面番号 | 不可 |
| id | surface id | 可 |
| kind | refractive / mirror / aperture_stop等 | 可 |
| surface_type | spherical / aspherical_even / plane等 | 可 |
| radius_mm | 曲率半径 | 可 |
| asphere | 設定済みのconic定数とA4 / A6 / A8...（未設定値は省略） | 表示 |
| thickness_after_mm | 次面までの距離 | 可 |
| material_after | 後側媒質 | 可 |
| semi_diameter_mm | 有効半径 | 可 |
| aperture | 開口形状・径 | 可 |
| group | 所属group | 表示中心 |
| status | validation状態 | 不可 |

## 12.2 kind別の必須項目

| kind | 必須項目 |
|---|---|
| refractive | surface_type, radius_mm, thickness_after_mm, material_after, semi_diameter_mm |
| mirror | surface_type, radius_mm, thickness_after_mm, semi_diameter_mm |
| aperture_stop | aperture.shape, aperture size, thickness_after_mm |
| mechanical_aperture | aperture.shape, aperture size, thickness_after_mm |
| thin_lens | focal_length_mm, semi_diameter_mm, thickness_after_mm |
| sensor | sensor.width_mm, sensor.height_mm |
| eye_reference | eye.pupil_diameter_mm, position_mode |
| dummy | id, thickness_after_mm |

sensor編集では、`width_mm` をY軸方向（面内水平）、`height_mm` をZ軸方向（面内垂直）の全長として扱う。

## 12.3 R=0の扱い

`radius_mm = 0` は平面として扱う。  
APIに送る値は必ず `radius_mm: 0` とする。

## 12.4 Undo / Redo

対象：

- surface値変更
- surface追加・削除
- material変更
- group定義変更
- sensor位置変更
- Raw YAML / JSON編集後の適用

対象外：

- API実行結果
- graph zoom / pan
- UISelection
- snapshot作成

---

# 13. 解析条件編集UI

## 13.1 基本項目

| 項目 | UI |
|---|---|
| endpoint | select |
| fields | field editor |
| wavelengths | preset / custom |
| ray_sampling | preset / advanced |
| pupil_distribution | select |
| ray_aiming | off / paraxial / full |
| image_plane_policy | select |
| field_source_policy | select |

## 13.2 ray sampling preset

| preset | 内容 |
|---|---|
| preview | 少数ray、paraxial aiming |
| standard | 中密度、full aiming |
| high_density | 高密度、full aiming |
| debug | 少数ray、path詳細保存 |

---

# 14. センサー位置・評価像面・フォーカス扱い

## 14.1 基本方針

UIは、ユーザーが明示しない限りセンサー位置を勝手に動かさない。  
物理センサー面と解析用評価面を分離する。

**実装責務【v0.2確定】**

image_plane_policy は**エンジン仕様v2.1 21.5節で定義されるエンジン側機能**であり、UIは像面依存の解析リクエストにパラメータとして含めて送信する。best_focus探索・sweep・focus_group solveを含め、UIが best-focus solve と解析の2段呼び出しでオーケストレーションすることはしない（1解析=1リクエスト）。UI側の責務は、policyの編集UI、応答metadata（evaluation_plane）の表示、およびwrite-back操作（14.3）のみである。

| 概念 | 意味 |
|---|---|
| Sensor surface | 光学系データ内の実体としてのセンサー位置 |
| Evaluation plane | spot / PSF / MTFなどを評価する仮想像面 |
| Focus solve | 近軸像面・RMS最小・MTF最大などを探索する処理（エンジン側で実行） |
| Write back | 求めた評価面位置をsensor面に反映する操作（UI側で実行） |

デフォルト：

```yaml
image_plane_policy:
  mode: fixed_sensor
  apply_to: evaluation_plane
```

## 14.2 image_plane_policy

エンジン仕様v2.1 21.5節のmode定義に従う。UIは以下をselectで提供する。

| mode | 内容 | 主用途 |
|---|---|---|
| fixed_sensor | 光学系定義内のsensor位置で評価する | 実機センサー固定、デフォルト |
| paraxial_image | 近軸像面で評価する | 初期確認、教育、近軸との整合確認 |
| best_focus_rms | 指定field / wavelengthでRMS spot最小位置を探索する | spot評価 |
| best_focus_mtf | 指定空間周波数のMTF最大位置を探索する | MTF評価 |
| best_focus_merit | 複数field / wavelength / metricの重み付きmeritで最良像面を探す | 設計比較 |
| custom_offset | sensor基準の任意offset位置で評価する | デフォーカス評価 |
| sweep | sensor近傍を掃引し、focus curveを出す | フォーカス感度確認 |

system_type: afocal の系では image_plane_policy 編集UIを無効化する（エンジン側でvalidation errorとなるため。対応概念は仮想視度掃引）。

## 14.3 apply_to と write-back

| apply_to | 内容 | 実装側 |
|---|---|---|
| evaluation_plane | sensor面は動かさず、解析用仮想面だけを動かす | エンジン（既定） |
| focus_group | sensorは固定し、指定focus groupを動かして合焦させる | エンジン（solved shiftをruntime configとして適用） |
| report_only | 位置だけ計算し、解析面には反映しない | エンジン |
| sensor_surface（write-back） | 求めた像面位置を光学系定義内のsensor面へ反映する | **UI**。エンジンAPIのapply_toには存在しない |

既定は `evaluation_plane` とする。

**write-back操作の規約【v0.2改訂】**

sensor_surfaceへの反映は、エンジンがstatelessである（系定義を書き換えない）ため、UI側の明示操作として実装する。

```text
1. 解析またはsolveの応答から solved_evaluation_plane_x_mm を取得
2. ユーザーが「Write back to sensor」を明示実行
3. UIがOpticalSystemDraftの該当thickness_after_mmを更新
4. system_dirtyになる
5. validate → register（新しいsystem_hash / system_id）
```

focus_groupで解決したshift量を恒久化する場合も同様に、UIがzoom_positions / group定義へ書き戻し、system_dirtyとする。

## 14.4 UI表示

光線図には以下の像面マーカーを表示する。

| マーカー | 内容 |
|---|---|
| Sensor | 光学系定義内の物理センサー面 |
| Paraxial image | 近軸像面 |
| RMS best | RMS spot最小像面 |
| MTF30 best | MTF 30 lp/mm最大像面 |
| Active evaluation plane | 今回の解析に使った評価面 |

表示規約：

| 面 | 表示 |
|---|---|
| Sensor | 実線 |
| Paraxial image | 点線 |
| RMS best | 破線 |
| MTF30 best | 一点鎖線 |
| Active evaluation plane | 強調線 |

---

# 15. Field定義と逆光線追跡による画角決定

## 15.1 field_source_policy

| mode | 内容 | 主用途 |
|---|---|---|
| object_angle | 物体側角度を直接指定する | 通常解析、歪曲、収差評価 |
| sensor_paraxial | センサーサイズと近軸EFLからfield角を決める | プリセット初期field生成 |
| sensor_reverse_trace | センサー上の点から逆光線追跡し、物体側方向を推定する | 実画角・歪曲マップ・ケラレ解析 |
| custom_direction | 方向ベクトルを直接指定する | デバッグ・特殊解析 |

## 15.2 sensor_paraxial

```text
theta_y = atan(sensor_y / f_ref)
theta_z = atan(sensor_z / f_ref)
```

ここで `f_ref` は基準同軸状態・主波長の近軸EFLとする。

## 15.3 sensor_reverse_trace

センサー上の指定点から逆方向光線追跡を行い、物体側に出ていく主光線方向を推定する。

用途：

- 実画角の推定
- 歪曲マップ生成
- センサー各点が見ている物体方向の可視化
- ケラレ込みの画角確認
- CRA評価
- レンダリング連携

通常のspot / MTF評価では、物体側field角を入力として使う方が意味が明確である。

---

# 16. API実行・Analysis Job管理

## 16.1 実行フロー

```text
1. system編集
2. validate
3. register
4. system_id取得
5. analysis endpoint実行
6. result保存
7. visualization更新
```

## 16.2 AnalysisJob

```json
{
  "job_id": "job_20260708_0001",
  "endpoint": "/v1/analysis/spot",
  "status": "running",
  "system_id": "sys_ab12",
  "created_at": "2026-07-08T08:00:00+09:00",
  "started_at": "2026-07-08T08:00:01+09:00",
  "finished_at": null,
  "progress": {
    "stage": "ray_tracing",
    "current": 3,
    "total": 9
  }
}
```

## 16.3 job status

| status | 内容 |
|---|---|
| queued | 実行待ち |
| running | 実行中 |
| succeeded | 成功 |
| failed | 失敗 |
| canceled | キャンセル |
| stale | 結果はあるが現在条件と不一致 |

## 16.4 同期APIと非同期API

MVP Phase 1では同期APIを前提とする。

Phase 2以降では、長時間解析向けに非同期job APIを追加できる構造とする。

```text
POST /v1/jobs
  → job_id

GET /v1/jobs/{job_id}
  → status / progress

GET /v1/jobs/{job_id}/result
  → result
```

---

# 17. 可視化コンポーネント表示規約

## 17.1 共通規約

すべての可視化は以下を表示またはmetadataとして保持する。

- system_id
- configuration
- analysis_condition
- field
- wavelength
- ray_sampling
- ray_aiming mode
- evaluation plane
- 表示単位

## 17.2 Optical Layout View

表示対象：

- X-Z断面
- X-Y断面
- surface位置
- lens surface形状
- aperture_stop
- mechanical_aperture
- annulus
- sensor
- eye_reference
- dummy surface
- group範囲
- decenter / tilt状態
- evaluation plane marker

**描画規約【v0.3追記】**

- 光線は全戻り値をそのまま描かず、field・wavelength・pupil sampleの代表光線を抽出して表示する。UIはAPIから返った総光線数と実際に表示した光線数をmetadataまたはDOM属性で保持し、検証時に比較できるようにする。
- 光線のstrokeは細く、半透明とし、波長ごとに区別できる色を用いる。多数光線の解析結果では表示上限を設け、spotやray fanの数値結果とは分離する。
- レンズ形状は `semi_diameter_mm` に基づく有効径境界（clear aperture boundary）として描く。これは製造寸法ではなく、現Phaseでは有効半径・開口境界の可視化に限定する。
- 隣接面の有効半径が異なる場合、現MVPでは両面の有効半径端点を直線で結ぶ。段付き端面やsquared edge表現は製造寸法モデル追加後に扱う。
- 屈折面の `material_after` が空気以外の場合、隣接する次面までをガラス領域として塗り分ける。接合面は通常面より控えめな線種で表現し、空気間隔とガラス内部を視覚的に区別する。
- エッジ厚は隣接面の `min(semiD_a, semiD_b)` 位置で評価する。負値または警告対象の可能性がある場合、描画を失敗させず、該当ガラス領域を警告スタイルで示す。

## 17.3 Ray Path View

表示対象：

- chief ray
- marginal ray
- sampled rays
- blocked rays
- aiming_failed rays
- numerical_error rays
- reflected rays
- refracted rays

光線数が多い場合、表示用に間引いてよい。  
統計値にはAPI応答の全光線結果を使う。

## 17.4 Spot Diagram View

表示項目：

- spot点群
- field id
- wavelength
- RMS radius
- GEO radius
- Encircled energy 80% radius
- centroid
- chief ray intersection
- 有効光線数
- blocked ray数
- aiming_failed数

## 17.5 MTF Chart View

focal系：

```text
unit: lp/mm
```

afocal系：

```text
unit: cycles/degree
```

表示項目：

- sagittal MTF
- meridional MTF
- white MTF / monochromatic MTF
- geometric / diffraction included
- field
- wavelength
- evaluation plane

focal系のWorkbench UIは、解析条件の`MTFモード`を`単色` / `白色光`のセグメントで切り替える。`単色`は`POST /v1/analysis/mtf`、`白色光`は`POST /v1/analysis/white-mtf`へ接続し、白色光では解析条件の波長ウェイトを使用する。結果パネルには実行したモードを明示し、白色光の凡例には`white`を付けて単色結果と区別する。両モードの横軸単位はfocal系では`lp/mm`とする。現行実装はいずれも幾何MTFであり、`diffraction included: false`を表示する。

## 17.6 PSF Heatmap View

表示項目：

- PSF heatmap
- grid size
- pixel size
- normalization
- linear / log表示切替
- peak位置
- encircled energy

## 17.7 Ray Fan View

表示項目：

- Y fanとZ fanを独立したpanelとして表示する
- Y fanのX軸は正規化瞳座標`Py`、Y軸はY方向横収差`mm`
- Z fanのX軸は正規化瞳座標`Pz`、Y軸はZ方向横収差`mm`
- seriesは`field id + wavelength`の組合せごとに分離する
- wavelengthごとに区別できる色と凡例を表示する
- `/v1/analysis/ray-fan`を`fan_y`と`fan_z`で独立実行し、対応する結果だけを各panelへ描画する
- `status=alive`かつ対象座標・横収差が有限の点をplotする
- 点数に応じてmarker半径とopacityを調整し、点数自体はDOM metadataとして保持する

未実行時は実行を促すempty stateを表示する。実行済みでplot可能な点がないpanelは「プロット可能なデータがない」状態を表示する。API errorは構造化エラー通知として表示し、不正な点を正常seriesへ混入しない。

## 17.8 Longitudinal Aberration View

表示項目：

- X軸は縦方向焦点ずれ`mm`
- Y軸は符号付き正規化瞳座標`pupil_y`
- focal系の軸上fieldを対象とし、複数field条件では`hypot(theta_y_deg, theta_z_deg)`が最小のfieldを使用する
- seriesはwavelengthごとに分離し、wavelength色と凡例を表示する
- 各seriesは瞳座標順に結線する
- `status=alive`かつ瞳座標・焦点ずれが有限の点をplotする
- ゼロ基準は主波長の近軸焦点とする
- API metadataとして`reference_kind=primary_wavelength_paraxial_focus`、`reference_wavelength_nm`、`reference_x_mm`を保持する
- 軸上・瞳中心光線は光軸との交点が一意に定まらないため、その波長の近軸焦点を`pupil_y -> 0`の極限値として使用する
- 単一波長では主に球面収差、複数波長の重ね描きでは主波長基準の軸上色収差を含む図として扱う

未実行時は実行を促すempty stateを表示する。実行済みでplot可能な点がない場合は「プロット可能なデータがない」状態を表示する。API errorは構造化エラー通知として表示し、不正な点を正常seriesへ混入しない。

## 17.9 Field Curvature / M-S Image Surface View

表示項目：

- 標準収差panelではX軸を焦点ずれ`mm`、Y軸を半画角`deg`とする
- 個別Field Curvature panelではX軸をfield angle`deg`、Y軸を焦点ずれ`mm`とする
- `/v1/analysis/field-curvature`と`/v1/analysis/ms-image-surface`のrowを`field_id`で結合する
- M seriesは`tangential_focus_shift_mm`、S seriesは`sagittal_focus_shift_mm`を表示する
- M/S値がない場合に限り`best_focus_shift_mm`をfallbackとして使用する
- MとSを異なる色と凡例で表示し、field順に結線する
- field angleは`hypot(theta_y_deg, theta_z_deg)`で求める
- field angle・焦点ずれが有限の点だけをplotする

未実行時は実行を促すempty stateを表示する。実行済みでplot可能な点がないpanelは「プロット可能なデータがない」状態を表示する。API errorは構造化エラー通知として表示し、不正な点を正常seriesへ混入しない。

## 17.10 Distortion View

表示項目：

- 標準収差panelではX軸を歪曲率`%`、Y軸を半画角`deg`とする
- 個別Distortion panelではX軸をfield angle`deg`、Y軸を歪曲率`%`とする
- seriesは`distortion`の単一seriesとする
- field angleは`hypot(theta_y_deg, theta_z_deg)`で求める
- 歪曲率は近軸EFLから求めたideal image heightに対する実像高の差として表示する
- 軸上fieldはideal image heightが0で歪曲率を定義できないためplotから除外する
- field angle・歪曲率が有限の点だけをfield順に結線する

未実行時は実行を促すempty stateを表示する。実行済みでplot可能な点がないpanelは「プロット可能なデータがない」状態を表示する。API errorは構造化エラー通知として表示し、不正な点を正常seriesへ混入しない。

## 17.11 Through-focus MTF View【R92新設】

- Analysisタブ内で`標準解析` / `デフォーカスMTF`をセグメント切替する
- `POST /v1/analysis/mtf/through-focus`を使用し、解析条件のfield、波長、evaluation plane、ray aimingを引き継ぐ
- 推奨fieldごとに独立したpanelを1つ表示する。panel見出しにはfield idと`theta_y_deg / theta_z_deg`を示す
- X軸は評価面基準の`defocus mm`、Y軸は`MTF`で0〜1に固定する
- 初期表示周波数は10 lp/mmと30 lp/mmとし、周波数を色で区別する
- 同じ周波数ではMを実線、Sを破線とし、4 series（M@10 / S@10 / M@30 / S@30）を凡例に表示する
- M/Sはエンジン応答の`mtf_meridional` / `mtf_sagittal`を使用し、UIでY/Zから再推定しない
- 現行実装は幾何MTFであるため、`diffraction included: false`に相当する注意を表示する
- defocus範囲はAPI metadataの物理基準範囲を使用し、UI側で固定±0.1 mmへ置き換えない

3 field・21 defocus点・2周波数・M/Sの既定表示は同期APIで30秒以内を目標とする。`defocus_mm = 0`の値は、同一field・波長・評価面・瞳サンプリングにおける通常MTFの10/30 lp/mmと一致しなければならない。

---

# 18. 単位・表示精度・丸め規約

## 18.1 標準表示単位

| 項目 | 表示単位 |
|---|---|
| radius_mm | mm |
| thickness_after_mm | mm |
| semi_diameter_mm | mm |
| sensor size | mm |
| pixel pitch | µm |
| focal length | mm |
| spot radius | µm |
| wavelength | nm |
| field angle | deg |
| visual angle | arcmin / mrad |
| angular MTF | cycles/degree |
| photographic MTF | lp/mm |
| relative illumination | % |
| distortion | % |
| refractive index | 無次元 |
| diopter | D |

## 18.2 表示精度

| 項目 | 推奨表示精度 |
|---|---:|
| radius / thickness | 0.001 mm |
| EFL / BFL | 0.001 mm |
| sensor position | 0.001 mm |
| spot radius | 0.01 µm |
| wavelength | 0.01 nm |
| field angle | 0.001 deg |
| arcmin | 0.01 arcmin |
| MTF | 0.001 |
| distortion | 0.01 % |
| relative illumination | 0.1 % |
| refractive index | 6 decimals |
| diopter | 0.001 D |
| profiling | 0.1 ms |

---

# 19. Error / Warning表示仕様

## 19.1 エラー分類

| 種別 | 内容 | 例 |
|---|---|---|
| schema_error | 入力JSON/YAMLの形式不正 | 必須field欠落 |
| validation_error | 光学系として不正 | aperture_stopがない |
| infeasible | 実行時条件により物理的に不可能 | 群移動後の負air gap |
| numerical_error | 数値計算の失敗 | 非球面Newton不収束 |
| aiming_failed | ray aimingの不収束 | 広角fieldで絞り中心に到達不能 |
| no_valid_rays | 有効光線がない | 全光線遮光 |
| api_error | API通信失敗 | 500, timeout |
| version_mismatch | UI/API schema不整合 | response schema不一致 |
| artifact_error | 大容量データ取得失敗 | psf_array取得失敗 |

## 19.2 エラー構造【v0.3改訂：コードベース】

エンジンは機械可読コード＋パラメータ＋**英語フォールバック文**を返す（エンジン仕様v2.3 26.10節）。エンジンは多言語化しない。表示文言は、UIがエラーカタログ（27.4節の用語集リソースの `errors` namespace）からコードをキーに組み立てる。

エンジン応答：

```json
{
  "severity": "error",
  "code": "negative_air_gap",
  "params": {
    "surface_ids": ["S4", "S5"],
    "group_ids": ["G2"],
    "gap_mm": -0.35
  },
  "message_en": "Air gap between S4 and S5 is negative (-0.35 mm)."
}
```

UI表示（ja選択時、エラーカタログから生成）：

```text
S4–S5間の空気間隔が負になっています（-0.35 mm）。
対処: 群位置またはthickness_after_mmを見直してください。
```

カタログに未登録のコードを受信した場合は `message_en` をそのまま表示し、未登録コードとしてconsole警告する（27.6節のカバレッジCIで検出対象）。

## 19.3 エラー箇所ジャンプ

エラーに `surface_ids` または `group_ids` が含まれる場合、UIは該当箇所へジャンプできるようにする。

対象：

- Surface Table
- Optical Layout View
- Group Table
- Raw JSON該当行

---

# 20. Large Data Handling / LOD

## 20.1 基本方針

大容量データは、JSONに直接すべて含めない。  
summaryとartifact参照を分ける。

```json
{
  "summary": {
    "rms_radius_um": 12.4,
    "valid_ray_count": 4096
  },
  "artifacts": {
    "spot_points": "artifact://spot/spot_001.parquet",
    "psf_array": "artifact://psf/psf_001.npy",
    "psf_image": "artifact://psf/psf_001.png"
  }
}
```

## 20.2 表示LOD

| データ | 方針 |
|---|---|
| ray path | 表示上限を設ける。chief/marginalは優先表示 |
| spot points | 点数が多い場合は間引き表示 |
| PSF | heatmap画像または縮小arrayを表示 |
| MTF | JSONで直接表示可 |
| field map | 必要に応じて補間表示 |
| batch result | tableはページング |
| raw JSON | 折りたたみ・検索付き |
| profiling log | 折りたたみ表示 |

## 20.3 ray path表示上限

```yaml
ray_display:
  max_display_rays: 500
  always_show_chief_ray: true
  always_show_marginal_rays: true
  show_blocked_rays: true
```

統計値はAPI応答の全体値を使い、表示用間引きデータで再計算してはならない。

---

# 21. Raw JSON / YAML編集規約

## 21.1 Raw表示対象

| 対象 | 表示 | 編集 |
|---|---|---|
| Optical System YAML | 可 | Advanced modeで可 |
| Optical System JSON | 可 | Advanced modeで可 |
| API request JSON | 可 | Debug modeで可 |
| API response JSON | 可 | 不可 |
| validation response | 可 | 不可 |
| ResultBundle | 可 | 不可 |
| Snapshot JSON | 可 | 原則不可 |

## 21.2 Raw System編集

```text
1. Raw textをparse
2. schema validation
3. OpticalSystemDraftへ反映
4. system_dirtyにする
5. validate required表示
```

parseまたはschema validationに失敗した場合、OpticalSystemDraftへ反映しない。

## 21.3 Raw Response編集禁止

API responseは編集不可とする。

理由：

- 解析結果の正本性が失われる
- snapshot比較が不正確になる
- result metadataとの整合が壊れる

---

# 22. Project保存・Import / Export仕様

## 22.1 Project構造

```json
{
  "project_id": "proj_001",
  "name": "Double Gauss test",
  "created_at": "2026-07-08T08:00:00+09:00",
  "updated_at": "2026-07-08T08:30:00+09:00",
  "optical_systems": [],
  "configurations": [],
  "analysis_conditions": [],
  "results": [],
  "snapshots": [],
  "compare_sets": [],
  "versions": {}
}
```

## 22.2 MVPでの保存方式

Phase 1では、ブラウザからのファイルdownload / uploadでよい。

| 対象 | 形式 |
|---|---|
| Optical system | YAML / JSON |
| Project | JSON |
| Result table | CSV / JSON |
| Figure | PNG / SVG |
| Raw request | JSON |
| Raw response | JSON |
| Snapshot | JSON |

## 22.3 Export対象

- Optical Layout
- Ray Path
- Spot Diagram
- MTF
- Field Curvature
- Relative Illumination
- PSF Heatmap
- Exit Pupil
- Eye Box

SVG出力では、軸ラベル・単位・field・wavelength・evaluation plane情報を含める。

## 22.4 Snapshotとartifact永続化【v0.2新設】

**前提**

エンジンのartifactは揮発性である（エンジン仕様v2.1 26.8節：TTL既定30分、プロセス再起動で消滅）。したがって、artifact URIをsnapshotに保存するだけでは、後日のCompare・再表示が成立しない。

**規約**

```text
snapshot作成時、UIはTTL内に GET /v1/artifacts で
比較・再表示に必要なデータを取得し、snapshotへ埋め込む。
```

| データ | 埋め込み | 形式 |
|---|---|---|
| summary（RMS値、metadata等） | 必須（ResultBundleに含まれる） | JSON |
| spot点群 | 必須 | parquet添付またはJSON（点数上限あり） |
| MTF / field curvature / focus curve等の曲線 | 必須 | JSON |
| 図（layout / spot / MTF等） | 必須 | PNG |
| PSF array（.npy等の大容量） | 任意。既定off、ユーザートグル | npy添付 |
| ray path全経路 | 任意。既定off | parquet添付 |

**partial snapshot**

artifact取得に失敗した場合（TTL切れ・artifact_error）、snapshot作成は中断せず、`partial: true` と欠損artifact一覧を記録する。Compare画面でpartial snapshotを使う場合、欠損データに依存する比較項目は「データなし」と明示し、summary値のみの比較にフォールバックする。

**保存形式**

埋め込みデータを含むsnapshotは、単一JSONに収まらない場合があるため、export形式は以下の2種を許可する。

| 形式 | 内容 |
|---|---|
| 単一JSON | 添付なし、または小容量（base64埋め込みが目安1 MB以下） |
| zip | snapshot.json + artifacts/ ディレクトリに添付ファイルを同梱 |

Project export（22.2）も同様に、埋め込みartifactを含む場合はzip形式とする。

---

# 23. Versioning / Compatibility

## 23.1 管理するバージョン

| バージョン | 内容 |
|---|---|
| engine_version | 光学エンジン本体 |
| api_schema_version | API request/response schema |
| ui_version | Optics Workbench UI |
| preset_version | プリセット光学系 |
| material_catalog_version | 硝材データ |
| result_schema_version | ResultBundle形式 |
| design_system_version | UIデザインシステム |
| project_schema_version | Project保存形式 |

## 23.2 Snapshotへの記録

```json
{
  "versions": {
    "engine_version": "0.1.0",
    "api_schema_version": "0.1.0",
    "ui_version": "0.1.0",
    "preset_version": "0.1.0",
    "material_catalog_version": "0.1.0",
    "result_schema_version": "0.1.0",
    "project_schema_version": "0.1.0"
  }
}
```

## 23.3 version取得とmismatch検出【v0.2改訂】

バージョン情報の取得元は、エンジン仕様v2.1 26.9節の `GET /v1/meta` とする。

```text
UI起動時:
  GET /v1/health で疎通確認
  GET /v1/meta でengine/api schema/result schema等のversionとcapabilitiesを取得
  api_schema_version: major不一致 → エラー表示・解析実行を禁止
                      minor不一致 → 警告表示
  capabilities: 未実装機能（例: diffraction_psf, async_jobs）に対応する
                UI要素をdisable表示にする

Project / Snapshot読込時:
  保存されたversionsと /v1/meta の現在値を比較し、
  不一致がある場合は警告と差分を表示する
```

---

# 24. Accessibility / Keyboard操作

## 24.1 基本方針

- 色だけで状態を示さない
- エラーはテキストで表示する
- グラフには数値表を併設できる
- キーボード操作を可能にする
- tooltipで専門用語を補足する
- ダーク/ライトテーマで十分なコントラストを確保する

## 24.2 キーボード操作

| 操作 | キー |
|---|---|
| タブ移動 | Tab / Shift+Tab |
| Surface Tableセル移動 | Arrow keys |
| 編集確定 | Enter |
| 編集キャンセル | Esc |
| Undo | Ctrl+Z |
| Redo | Ctrl+Y / Ctrl+Shift+Z |
| 実行 | Ctrl+Enter |
| 検索 | Ctrl+F |
| 保存 | Ctrl+S |
| Raw JSONコピー | Ctrl+C |

---

# 25. 対象画面サイズ・レスポンシブ方針

本UIはデスクトップブラウザを主対象とする。  
初期版ではスマートフォン表示を対象外とする。

| 項目 | 推奨 |
|---|---|
| 画面幅 | 1440 px以上 |
| 画面高さ | 900 px以上 |
| ブラウザ | Chrome / Edge / Firefox最新版 |
| 入力 | キーボード + マウス / トラックパッド |
| タッチUI | 初期対象外 |

画面幅が1024 px未満の場合は警告を表示する。

---

# 26. Security / Local API接続・データ取扱い

## 26.1 基本方針

初期版では、Optics Workbench UIはローカルまたは指定されたAPI endpointにのみ接続する。  
外部クラウド送信は行わない。

## 26.2 API接続先

既定：

```text
http://localhost:8000
```

設定項目：

- API base URL
- timeout
- CORS状態
- engine health check（GET /v1/health）
- API schema version確認（GET /v1/meta。エンジン仕様v2.1 26.9節）

## 26.3 Telemetry

初期版ではtelemetryを無効とする。

```text
telemetry: off by default
```

将来導入する場合は、明示的なopt-inとする。

---

# 27. 多言語対応（i18n）・Help・用語集システム【v0.3全面改訂】

本ソフトの第一目的は教育である。ヘルプ・用語解説は付随機能ではなく中核機能として扱い、多言語対応と一体で設計する。

## 27.1 i18n基本方針

- 対応言語：日本語（ja）・英語（en）。リソース構造は追加言語を許容する。
- ライブラリ：react-i18next。リソースはJSON、ビュー単位のnamespace＋共有namespace（glossary / errors / units）。
- 既定言語：ブラウザ言語から自動判定（ja以外はen）。設定画面で手動切替でき、**アプリ設定として永続化**する（Projectには保存しない。Projectは言語非依存とする）。
- キー命名：`{namespace}.{view}.{要素}` 形式。英文をキーに使わない。
- 文字列のハードコード禁止。全表示文字列はリソース経由とする（例外：エンジン由来の識別子。27.2）。

## 27.2 翻訳境界（翻訳するもの / しないもの）

| 区分 | 例 | 扱い |
|---|---|---|
| UI文言 | ボタン、メニュー、説明、ダイアログ | 翻訳する |
| エンジン識別子 | surface ID（S1, STOP）、変数キー（S1_curvature）、metric名（rms_spot_radius）、エラーコード | **翻訳しない**。生キーのまま表示・送信 |
| 識別子の表示ラベル | rms_spot_radius →「RMSスポット半径」/ "RMS Spot Radius" | 用語集リソース（27.4）でマップして翻訳する |
| エラー文言 | negative_air_gap | エンジンはコード＋params＋英語フォールバック。UIがエラーカタログから組み立てる（19.2節） |
| 光学術語 | 非点収差、射出瞳 | ja表示では英語術語を併記する：「非点収差 (Astigmatism)」。併記の有無は用語集エントリで制御 |

raw JSON / YAML表示、CSV / parquetエクスポート、APIリクエストには翻訳を一切適用しない（生キーのみ）。

## 27.3 数値・単位・日時の非翻訳規約

- 小数点はロケールによらず**ピリオド固定**。桁区切りは使用しない（18章の表示精度規約に従う）。
- 単位（mm, µm, deg, lp/mm, cycles/degree, diopter）は翻訳しない。
- 日時はデータ上ISO 8601で保持し、表示のみロケール整形してよい。Snapshot / Project内はISO 8601固定。

## 27.4 用語集リソース（単一ソース）

用語集は `glossary.{lang}.json` の1系統に集約し、以下がすべて同じソースを参照する：テーブル列ヘッダのラベル、結果metricの表示名、チャート軸ラベル、ツールチップ、ヘルプドロワー本文、SVGエクスポートの注記、エラーカタログ。

スキーマ：

```json
{
  "terms": {
    "rms_spot_radius": {
      "label": "RMSスポット半径",
      "en_term": "RMS Spot Radius",
      "short": "光線群のセンサー到達点の重心からの二乗平均平方根の広がり。小さいほど像がシャープ。",
      "long": "…（ヘルプドロワー用。Markdown可。数式・図参照可）",
      "formula": "sqrt(mean(r_i^2))",
      "see_also": ["spot_diagram", "encircled_energy_radius"],
      "lesson_mode": null
    }
  },
  "errors": {
    "negative_air_gap": {
      "label": "空気間隔が負",
      "message": "{surface_ids}間の空気間隔が負になっています（{gap_mm} mm）。",
      "action": "群位置またはthickness_after_mmを見直してください。"
    }
  }
}
```

- `short` はツールチップ用（1〜2文）。`long` はヘルプドロワー用（任意。未定義ならshortのみ表示）。
- `lesson_mode` は将来の教育モード導線用の予約フィールド（該当レッスンへの「試してみる」リンク。初期版では未使用、スキーマに席のみ確保）。
- ja/enでキー集合は完全一致でなければならない（27.6のCIで検証）。
- 初稿として `glossary.ja.json` / `glossary.en.json`（約55語＋エラーカタログ）を本仕様に付属させる。

## 27.5 3階層ヘルプ

| 階層 | 対象 | UI | ソース |
|---|---|---|---|
| ①用語ツールチップ | Surface Table列ヘッダ、metric名、設定項目、近軸量カード | Carbon **Toggletip**（クリック/フォーカスで開閉） | terms.short |
| ②ヘルプドロワー | チャートの読み方（ray fan / MTF / M-S像面等）、概念解説 | ツールチップ内「詳しく」→右ドロワーでMarkdown表示。see_alsoリンクで回遊可 | terms.long |
| ③エラー・警告解説 | validation / infeasible / aiming_failed / solve_not_converged 等 | エラーバッジ・トースト内に説明＋対処。詳細はドロワー | errors.* |

規約：

- ホバー限定のtooltipは使わない。Toggletipを基本とし、キーボード（Tab→Enter/Esc）・タッチで操作可能にする（24章のアクセシビリティ規約に従う）。
- ツールチップは計算値を含まない静的テキストとする（値の説明は結果パネル側の責務）。
- 教育Explanation Panel（Previewタブの操作連動解説）は将来の教育モード仕様で扱い、本章では①〜③のみをMVP対象とする。ただしレッスン文も実装時は必ず構造化リソースに置く（コードに埋めない)。

## 27.6 カバレッジ検証（CI）

用語の取りこぼしを構造的に防ぐため、以下をCIで機械検証する。

1. `glossary.ja.json` と `glossary.en.json` のキー集合が一致すること。
2. エンジンの `GET /v1/meta` が返す列挙（metrics / error_codes / warning_codes / ray_status_codes / variable_key_patterns。エンジン仕様v2.3 26.9節）に対し、UIが表示し得る全項目に用語集エントリが存在すること。
3. i18nリソースの未使用キー・未定義キー参照の検出（i18next-parserによる抽出との突き合わせ）。
4. 擬似ロケールビルド（全文字列を伸長装飾）で主要画面のレイアウト崩れをスクリーンショットテストすること。en文字列はjaより長くなりがちなため、両言語でのテーブルヘッダ・ボタンの収まりを確認する。

## 27.7 チャート・エクスポートの言語

- Plotly軸ラベル・凡例は用語集ラベルを使用し、UIロケールに追従する。
- SVG / PNGエクスポートは既定でUIロケールに追従し、エクスポートダイアログで出力言語（ja / en）を明示選択できる。
- Snapshot内のResultBundleは言語非依存（生キーのみ）とし、表示時に現在ロケールでラベル化する。過去snapshotも言語切替で再ラベルされる。

---

# 28. UIテスト・受け入れ条件

## 28.1 共通受け入れ条件

全プリセットで以下を満たす。

1. プリセット一覧に表示される
2. プリセットをロードできる
3. Surface Tableに面一覧が表示される
4. Optical Layout Viewに光学系が表示される
5. validateを実行できる
6. validate結果が表示される
7. registerを実行できる
8. system_idが表示される
9. paraxialまたは該当するfirst-order量を表示できる
10. raw request / responseを表示できる

## 28.2 プリセット別受け入れ条件

| Preset | 受け入れ条件 |
|---|---|
| P001 | EFL約50 mm、F#約4、光線がsensor近傍で収束 |
| P002 | spot diagram表示、波長別焦点差が確認できる |
| P003 | N-BK7/N-F2がMaterial Tableに表示され、色収差評価が実行できる |
| P004 | spot / MTF / distortion / field curvatureを実行できる |
| P005 | mirror反射、negative thickness、annulus遮蔽が表示される。EFL≒3000 mm、軸上光束がM2でケラれない |
| P006 | afocalとしてvalidateされ、exit pupilとangular magnificationが表示される |

## 28.3 Dirty Stateテスト

| 操作 | 期待 |
|---|---|
| radius変更 | system_dirtyになる |
| iris variable変更 | configuration_dirtyになる |
| field変更 | analysis_dirtyになる |
| graph zoom | view_dirtyのみ |
| sensor write-back | system_dirtyになる |
| stale result発生 | stale表示が出る |

## 28.4 Error表示テスト

| エラー | 期待 |
|---|---|
| aperture_stop欠落 | validation error表示 |
| material未定義 | 該当surfaceをハイライト |
| 負air gap | infeasible表示 |
| no_valid_rays | 空グラフではなく専用メッセージ |
| aiming_failed | 件数・割合を表示 |
| API timeout | timeoutとして表示 |

## 28.5 i18n / ヘルプ受け入れ条件【v0.3追加】

| 検証 | 期待 |
|---|---|
| 言語切替 | 設定でja/en切替後、主要画面の全文言が切り替わり、再起動後も保持される |
| 識別子非翻訳 | 言語切替後もsurface ID・metric生キー・raw JSONは不変 |
| 小数点固定 | ja/en両方でテーブル・入力・CSVの小数点がピリオドである |
| Toggletip | Surface Table全列ヘッダと結果metric名でキーボード操作により開閉できる |
| エラーカタログ | negative_air_gapのエラーがja/enそれぞれのカタログ文言で表示される。未登録コードはmessage_enフォールバック |
| カバレッジCI | 27.6の4検証がCIジョブとして存在しグリーン |
| エクスポート言語 | SVGエクスポートで出力言語を選択でき、軸ラベルが追従する |


---

# 29. MVP実装順序

## Phase 1：基本ビューア

- プリセット読み込み
- Surface Table表示
- Optical Layout表示
- validate実行
- register実行
- system_id表示
- paraxial実行・表示
- forward trace実行・光線表示
- education preview
- raw request / response表示
- dirty / stale状態表示
- sensor / paraxial image / active evaluation plane表示

## Phase 2：写真レンズ解析

- field / wavelength / sampling編集
- spot diagram
- ray fan
- distortion
- field curvature
- relative illumination
- MTF
- result snapshot保存
- 2条件比較
- best_focus_rms
- best_focus_mtf
- focus curve表示

## Phase 3：設計操作

- group編集
- zoom_position切替
- focus group slider
- aperture slider
- decenter / tilt操作
- validation warningの可視化
- before / after比較
- sensor write-back
- Raw YAML / JSON advanced edit

## Phase 4：afocal / 双眼鏡・望遠鏡

- system_type: afocal対応
- eye_reference表示
- exit pupil表示
- eye box heatmap
- angular spot
- angular MTF
- binocular alignment

---

# 30. 初期MVP完成条件

初期MVPは、以下を満たした時点で完了とする。

1. 6プリセットをロードできる
2. validate/registerを実行できる
3. surface tableを表示できる
4. optical layoutを表示できる
5. forward ray pathを表示できる
6. paraxial結果を表示できる
7. spot diagramを最低1つ表示できる
8. raw request / responseを表示できる
9. dirty / stale状態を表示できる
10. sensor / paraxial image / active evaluation planeを区別表示できる
11. エラー時に該当surfaceへ誘導できる
12. 結果をsnapshot保存できる
13. YAML / JSONとしてsystem exportできる
14. PNGまたはSVGとして主要図をexportできる
15. UIテストでP001〜P006の基本受け入れ条件を満たす

---

# 31. 将来拡張

## 31.1 デスクトップアプリ化

Web UIが安定した後、Tauriによるローカルデスクトップ化を検討する。

目的：

- Python API起動の統合
- Project file管理
- ローカルartifact管理
- オフライン利用

## 31.2 Test Dashboard

Golden Test結果をUIから閲覧できるTest Dashboardを追加する。

表示項目：

- test name
- pass / fail
- reference value
- actual value
- tolerance
- diff
- engine version

## 31.3 Batch / Optimization UI

外部最適化エンジンと連携する場合、以下を追加する。

- candidate一覧
- merit score ranking
- constraint violation表示
- parallel job status
- best candidate比較
- parameter sensitivity plot

## 31.4 Advanced Afocal UI

双眼鏡・望遠鏡向けに以下を拡張する。

- binocular left/right channel editor
- collimation error editor
- eye box 3D view
- blackout sensitivity map
- apparent field view
- angular distortion map

## 31.5 Material Catalog UI

将来、硝材カタログ管理UIを追加する。

機能：

- catalog material search
- nd/Vd表示
- partial dispersion表示
- Sellmeier係数表示
- material substitution
- glass map表示
