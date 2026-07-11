# Issues Backlog

G5時点のGitHub Issue草案です。現在の `doc/work_orders/active/` で直接カバーされていない、次の2〜3フェーズで着手しやすい残件に絞っています。

## Active指示書でカバー済みのためIssue化しない項目

以下は `doc/work_orders/active/codex_p0-7_performance_work_order.md` で扱うため、このbacklogではIssue化しません。

- spec-like benchmark履歴化と性能推移レポート
- Golden Test追加
- ray aiming残差計算の軽量化
- バッチ配列トレースカーネル
- 瞳アフィン写像、warm start、aiming cache
- profiling metadata
- インタラクティブ性能ハーネス
- 条件付きNumba化

以下は `doc/work_orders/active/codex_github_publication_work_order.md` または人間側作業で扱うため、Issue化しません。

- `<REPO_NAME>` / `<COPYRIGHT_HOLDER>` の確定
- GitHubリポジトリ作成とpush
- 公開前チェックリスト

## Issue: Snapshot zip exportを実装する [issue: #1]

ラベル案: `ui`

### 背景

Phase 2では小容量snapshotの単一JSON exportのみ実装済みです。仕様上の `snapshot.json + artifacts/` zip exportは未実装です。

### 対応案

- snapshot本体を `snapshot.json` として保存する。
- 埋め込み済みartifactを `artifacts/` 以下へ展開する。
- artifact欠損時は `partial` と欠損一覧をzip内manifestへ含める。
- zip import/readbackの最小テストを追加する。

### 受け入れ条件

- artifactありsnapshotをzip exportできる。
- exportしたzipからsnapshotとartifactを復元できる。
- partial snapshotでも欠損情報が保持される。

## Issue: Snapshot比較をチャート重ね合わせまで拡張する [issue: #2]

ラベル案: `ui`

### 背景

現在のCompareビューはsummary/table中心です。spot、MTF、relative illumination、focus curveの本格的な並置・重ね合わせ比較は限定的です。

### 対応案

- 比較可能性ガードを維持したまま、A/Bのchart overlayまたはside-by-side表示を追加する。
- field、波長、評価像面が不一致の場合は該当チャートだけdisabledにする。
- snapshotの生キー保存、表示時ローカライズ規約を維持する。

### 受け入れ条件

- 同条件snapshotでspot/MTF/RI/focus curveを視覚比較できる。
- 不一致条件では警告とdisabled状態が表示される。
- ja/en切替後もラベルが現在ロケールで表示される。

## Issue: Raw JSON/YAML advanced editorを実装する [issue: #3]

ラベル案: `ui`, `good-first-issue`

### 背景

UI仕様ではRaw JSON/YAML編集が定義されていますが、現状は高度な編集・round-trip検証まで未実装です。

### 対応案

- Advanced modeでOptical System JSON/YAMLを編集できるようにする。
- parse error、validation error、system_dirty遷移をUIに表示する。
- 保存前にvalidate/registerの導線を出す。

### 受け入れ条件

- 有効なJSON/YAMLを読み込み、Surface Table/Layoutへ反映できる。
- 無効入力では構造化エラーを表示し、既存systemを壊さない。
- raw表示では識別子を翻訳しない。

## Issue: UI実装にP004プリセット（簡易ダブルガウス）を追加する

ラベル案: `ui`

### 背景

UI仕様9章にP004の定義があるが、実装側 `apps/workbench-ui/src/domain/presets.ts` に存在しないことがP3-0で判明した。

### 対応案

仕様9章のP004定義に従い、`presets.ts` へ追加する。近軸検証を行い、9.1節の数値検証規約に従って凍結する。

### 受け入れ条件

- P004がプリセット一覧に表示され選択できる。
- 近軸トレースが破綻しない。

## Issue: PNG exportの画像比較テストを追加する [issue: #4]

ラベル案: `ui`, `testing`, `good-first-issue`

### 背景

SVG exportはテキストreadbackでja/enラベルを検証済みです。一方、PNG exportの画像比較テストは未追加です。

### 対応案

- deterministicな小型layout/spotケースでPNG exportを生成する。
- 画像サイズ、非空ピクセル、主要ラベル付近の描画有無を検証する。
- 完全なpixel-perfect比較ではなく、安定したスモーク検証から始める。

### 受け入れ条件

- PNG exportが空画像でないことをCIで検出できる。
- ja/enそれぞれの代表ケースで成功する。
- テストが環境差で過度に不安定にならない。

## Issue: 高密度spot/散布表示のPlotly scattergl対応 [issue: #5]

ラベル案: `ui`, `performance`

### 背景

P2-2では、点数の多いspot/散布表示にPlotly `scattergl` を使う規約でした。一方、現状のPhase 2実装は軽量なSVGチャートで構成されています。

現状SVGで実装されている理由:

- 現在のMVPデータ量ではSVGで操作性・表示品質ともに足りている。
- i18nラベル表示とSVG text readbackテストを単純に維持できる。
- Plotly/WebGL化は依存追加、描画LOD、エクスポート、画像・言語検証を伴うため、公開準備中に混ぜるにはスコープが大きい。

### 対応案

- 高点数spot/散布だけをPlotly `scattergl` に切り替えるLOD閾値を設計する。
- Optical Layout、光線図、小規模で決定論的なチャートはSVGを維持する。
- WebGL/canvas系のexport制約をREADMEまたはUI内で明示する。

### 受け入れ条件

- 高密度spot cloudがUIをブロックせず描画できる。
- 小規模データは既存SVG表示と同等に安定している。
- ja/enラベルがi18nテストで担保される。
- export可否または代替形式が仕様・README・UIのいずれかで明示される。

## Issue: supplement glossaryを本体用語集へ統合する [issue: #6]

ラベル案: `ui`, `docs`

### 背景

v2.3/P2対応で不足した用語・エラーコードは `glossary.supplement.{ja,en}.json` に追加されています。これは人間レビュー待ちの暫定領域です。

### 対応案

- supplement entriesをレビューする。
- 表現を確定した項目を `glossary.{ja,en}.json` 本体へ移す。
- supplement側から移行済みキーを削除する。

### 受け入れ条件

- ja/enのキー集合が一致する。
- `npm run i18n:coverage` が通る。
- 用語本文の人間レビュー結果が反映されている。

## Issue: axis_convention import/exportを実装する [issue: #7]

ラベル案: `engine`, `docs`

### 背景

エンジン内部の光軸は `+X` ですが、外部OSSや一般的な光学データはZ軸光軸系で表現されることがあります。現状、外部Z軸系との明示的なimport/export変換は未実装です。

### 対応案

- `+X` 内部表現とZ軸光軸系の座標写像を明文化する。
- 外部データ取り込み用の変換helperを追加する。
- rayoptics等との比較テストで変換を固定する。

### 受け入れ条件

- 単純な球面レンズ系をZ軸表現から取り込み、内部 `+X` 系で同じ近軸量になる。
- 変換規約がドキュメント化されている。

## Issue: variable binding registryをCompiledSystemに保持する

ラベル案: `engine`

### 背景

follow-up3時点では、`semi_diameter_mm: { variable: "iris_radius_mm", default: 10 }` のようなvariable形式はロード時にdefault値へ正規化される。`iris_radius_mm` については `configuration.variables.iris_radius_mm` をtrace時に個別処理しているためMVPとして動作するが、CompiledSystem内に「どのsurface/parameterがどのvariable keyへ束縛されているか」という情報は残っていない。

このまま `{surface_id}_curvature`、`{surface_id}_conic`、`{surface_id}_thickness_after_mm` など25.6節の一般変数へ広げると、UI表示、validation、最適化API、CompiledSystem cache再利用の整合が取りづらくなる。

### 対応案

- `CompiledSystem` にvariable binding registryを追加し、variable key、対象surface、対象parameter、default値、許容範囲/型を保持する。
- `load_system` / `compile_system` でvariable形式をdefault数値へ正規化しつつ、binding情報を失わないようにする。
- `configuration.variables` 適用を `iris_radius_mm` 専用処理から一般的なparameter injectionへ拡張する。
- system hash / cache keyに、binding schemaとdefault値を含め、runtime値そのものはcache keyに含めない方針を明確にする。
- unknown variable、型不正、範囲外値の構造化エラー/警告を追加する。

### 受け入れ条件

- 同一CompiledSystemに対して複数のruntime variable値を連続適用しても前回値が残留しない。
- `iris_radius_mm` がregistry経由で動作し、現行のaperture runtime化テストが維持される。
- 少なくとも1つのsurface parameter（例: `{surface_id}_curvature` または `{surface_id}_thickness_after_mm`）がregistry経由でruntime injectionできる。
- variable bindingの内容がdebug/API metadataで確認できる。

## Issue: 回折PSF・波面収差・FFT瞳関数を追加する [issue: #8]

ラベル案: `engine`

### 背景

現状は幾何PSF/MTFが中心です。回折PSF、波面収差、瞳関数FFT、白色回折PSF/MTFは未実装です。

### 対応案

- まず単色・軸上・円形瞳の回折PSFを実装する。
- 幾何PSFとの責務境界を明確にする。
- white PSF/MTFは波長重み付き結合として段階的に追加する。

### 受け入れ条件

- 理想円形瞳でAiry disk相当の基礎検証ができる。
- APIレスポンスのartifact方針が既存PSF/MTFと整合する。

## Issue: 視覚系のプリズム・正立像モデルを拡張する [issue: #9]

ラベル案: `engine`

### 背景

Phase 8でafocal、eye_reference、射出瞳、アイボックス、角度MTF等はMVP実装済みです。一方、ポロプリズム/ダハプリズム、像の正立化、実眼モデル、双眼鏡の詳細な左右チャンネルモデルは未実装です。

### 対応案

- まずプリズムを「光路長・反転状態・開口制約」の簡易モデルとして扱う。
- 左右チャンネル差と双眼アライメント評価を拡張する。
- UI Phase 4のafocalビューと連携する。

### 受け入れ条件

- プリズムありafocal系で射出瞳と像反転状態を評価できる。
- 双眼鏡プリセットで左右チャンネル差を表示できる。

## Issue: 長時間解析向けjob/WebSocketセッションを検討する [issue: #10]

ラベル案: `engine`, `ui`

### 背景

現行APIは同期HTTPが中心です。重いPSF/MTF、最適化、大量field解析では、非同期jobや進捗通知が必要になる可能性があります。

### 対応案

- まずHTTP job APIかWebSocketかを比較する。
- 進捗、キャンセル、artifact TTLとの関係を設計する。
- UI側ではjob状態表示と再取得導線を設計する。

### 受け入れ条件

- 長時間解析の進捗とキャンセル方針が仕様化されている。
- MVP API形状とUI状態遷移が決まっている。

## Issue: 面ごとの製造外径（mechanical_diameter_mm）を導入し、段付き外径をUIで表現できるようにする

ラベル案: `engine`, `ui`

### 背景

現PhaseのLayout Viewは `semi_diameter_mm` を有効半径として扱い、clear aperture boundaryを描画する。これは光線通過域の可視化としては正しいが、実レンズ図面で必要になる段付きの製造外径、コバ径、鏡筒保持部の表現には不足する。エンジン仕様v2.2で定義済みの `edge_thickness` 評価値は隣接面間の周縁厚み制約チェックに留まり、製造外径自体を決定する仕組みではない。

### 対応案

- エンジン仕様に面単位の任意項目 `mechanical_diameter_mm` を追加する。
- 省略時は `semi_diameter_mm` と同値として扱い、マージンの自動付与はしない。
- `mechanical_diameter_mm` は描画・製造制約評価専用とし、光線の遮光判定には影響させない。この非影響をテストで固定する。
- UI Layout Viewで、clear aperture boundaryと製造外形を別レイヤーとして描画できるようにする。
- edge thicknessの評価位置は現行どおり有効半径基準 `min(semiD_a, semiD_b)` を維持し、将来的にmechanical edge位置での評価オプションを追加する余地を注記する。
- 将来的な発展として、最小コバ厚み制約から外径を逆算する、外径差が過大な場合に警告する、といった機能は別Issue候補として残す。

### 受け入れ条件

- `mechanical_diameter_mm` を面ごとに指定でき、省略時は有効径ベースの既定値が使われる。
- UIが段付き外径を正しく描画する。
- 有効径境界と製造外形がUI上で区別できる。
- snapshot export/importで追加寸法が保持される。
- 既存の `edge_thickness` 評価・validationと矛盾しない。

## Issue: edge_thickness metricのエンジン実装を追加する

ラベル案: `engine`

### 背景

仕様・`/v1/meta` のmetadata列挙には `edge_thickness` が存在するが、エンジン本体に算出コードが見当たらないことがLayout View品質改善タスクで判明した。

### 対応案

- 仕様10.3節の定義（`min(semiD_a, semiD_b)` 位置での周縁厚評価）に従い、実際の算出ロジックを実装する。
- validation warning、optimization operand、API metadataで同じ評価値を参照できるようにする。

### 受け入れ条件

- `edge_thickness` オペランドがevaluate APIで実際の数値を返す。
- 既存のedge thickness警告経路と整合する。

## Issue: 最適化APIにmulti-configuration（複数zoom_position/フォーカス位置）評価を追加する

ラベル案: `engine`

### 背景

ズーム・フォーカス・防振群の実務的な設計最適化は、複数のconfiguration（広角端・望遠端、無限遠・至近等）を同時に評価し全域でバランスした解を探す必要がある。現行のオペランドAPI（25.3節）・ヤコビアンバッチ（25.7節）は単一configurationのみ対応で、`zoom_positions`（10.2節）とは接続されていない。

### 対応案

- 各オペランドに `configuration_id` / `zoom_position_id` を持たせる。
- 複数configurationを1回のevaluateでまとめて評価し、merit合成する仕組みを検討する。
- 詳細設計は別途エンジン仕様改訂で行う。本Issueは登録のみとし、着手は最適化タスク8-13の前提整理時とする。

### 受け入れ条件

- エンジン仕様への追記案が作成される。

## Issue: 有限距離物体のWorkbench UI対応

ラベル案: `ui`, `engine`

### 背景

エンジン仕様5.2では `object_points` / `position_mm` による有限距離物体点が定義されているが、現行Workbenchの `AnalysisField` とfield editorは `type: angular` の無限遠field角だけを扱う。P001-P007のUIプリセットもすべて角度fieldで評価されるため、有限距離物体の追跡をUIから試す入口がない。

### 対応案

- field editorに有限距離物体点モードを追加し、物点IDと `position_mm` を入力できるようにする。
- API送信前に、エンジンが対応する有限距離field形式へ正規化する。
- 未対応の解析では明示的にdisabledまたは警告表示にする。

### 受け入れ条件

- UIから有限距離物体点を定義し、preview/spot相当の追跡で利用できる。
- angular fieldとfinite object fieldの違いが条件表示・snapshotに保存される。

## Issue: field角とセンサーサイズ/EFLの関係をUIで可視化する

ラベル案: `ui`, `docs`

### 背景

現行UIのfield editorは `theta_y_deg` / `theta_z_deg` の直接入力であり、センサーサイズや近軸EFLから自動計算される画角ではない。UI仕様15章では `sensor_paraxial` / `sensor_reverse_trace` 方針が定義されているが、Workbench上ではユーザーが指定したfield角と、センサー範囲・EFL・像高 `h = f tan(theta)` の関係を十分に確認できない。

### 対応案

- field editorまたは解析条件パネルに、近軸EFL由来の予想像高とセンサー内外判定を表示する。
- 将来の `field_source_policy` 実装では `object_angle` と `sensor_paraxial` を切り替え可能にする。
- snapshot条件にもfield sourceを保持する。

### 受け入れ条件

- 現在のfield角がセンサー半幅/半高に対してどの程度の像高になるかUI上で確認できる。
- 角度直接指定とセンサー由来fieldの違いがユーザーに明確に示される。

## Issue: OIS群シフト時の有効径自動評価を高度化する

ラベル案: `engine`, `ui`

### 背景

R9-13では、Workbench UIに±5 mmのシフト上限明示と、対象群の最小有効径・絞り半径・シフト量から見る簡易ケラレ警告を追加した。ただし実際のOIS設計では、前後面の有効径、field、瞳位置、群シフト状態ごとの非対称光束を考慮して有効径を決める必要がある。

### 対応案

- decenter状態の代表field/瞳サンプルに対して、面ごとの必要有効径と余裕を計算するエンジン解析を追加する。
- UIでは群ごとの最大シフト量と、面ごとの不足余裕を一覧表示する。
- 現行の簡易警告は高速プレビュー用として残し、詳細解析結果で上書きできるようにする。

### 受け入れ条件

- OIS群を最大シフトさせた状態で、面ごとの有効径不足を定量的に確認できる。
- field/波長/絞り条件を変えた場合に警告が更新される。

## Issue: 撮影結果シミュレータを追加する

ラベル案: `engine`, `ui`

### 背景

現行の解析はPSF/MTF/spotなどの光学評価値が中心で、RGBD画像などを入力に、レンズの収差・被写界深度を反映した撮影結果をシミュレーションする機能はない。

### 対応案

- まず無収差・無限深度のRGBD画像に対し、PSFを畳み込む簡易シミュレーションから着手する。
- 将来的に被写界深度、フォーカス位置、オブジェクト距離差によるボケ量を反映する。
- UIでは入力画像、深度、解析条件を選び、結果画像を比較表示できるようにする。

### 受け入れ条件

- 単一PSFでの画像畳み込み結果をUIで確認できる。
- 使用した光学系、field、波長/重み、フォーカス条件が結果に保存される。

## Issue: 太陽光5000K等の連続スペクトルで色収差をシミュレーションする

ラベル案: `engine`

### 背景

現行の色収差評価はF/d/Cなどの離散波長が中心である。太陽光5000Kなどの連続スペクトル光源で軸上色・倍率色を評価するには、`light_sources` のサンプル密度や重み付き波長セットを扱う仕組みが必要になる。

### 対応案

- 5000K相当などの代表的な連続スペクトルを、重み付き波長サンプルへ変換するプリセットを追加する。
- 既存の波長重み付き解析へ接続し、色収差カーブやwhite PSF/MTFに反映する。
- サンプル数と速度のトレードオフを設定できるようにする。

### 受け入れ条件

- 5000K相当の重み付きスペクトルで、軸上色収差カーブを評価できる。
- 離散F/d/C評価との差を比較できる。

## Issue: 面反射ゴーストシミュレーションを追加する

ラベル案: `engine`

### 背景

現行のトレースは主に順方向の単純な透過経路を扱う。面反射ゴースト、すなわち各面での部分反射によって生じる迷光経路は評価対象外である。

### 対応案

- 初期段階では、1回または2回反射までの単純なゴースト経路を列挙して評価する。
- 反射率はまず定数または面ごとの簡易係数として扱う。
- 将来のコート特性モデルと接続できるよう、反射イベント情報を構造化する。

### 受け入れ条件

- 単純な2面反射ゴースト経路を計算できる。
- ゴースト強度の概算とセンサー上の位置を返せる。

## Issue: コート特性・CCI（教育目的）項目を追加する

ラベル案: `engine`, `docs`

### 背景

コーティングの透過率・反射率特性は仕様上非対応または簡略扱いである。一方で、教育目的として「コートを付けるとゴーストが減る」ことを示す簡易項目が有用である。

### 対応案

- 面ごとに簡易的な反射率係数または波長依存カーブを持たせる。
- ゴーストシミュレーションと組み合わせ、コート有無でゴースト強度が変わることを表示する。
- 詳細な薄膜計算ではなく、教育用途の簡易モデルとして仕様化する。

### 受け入れ条件

- 面のコート係数を設定できる。
- その係数がゴースト強度計算に反映される。
- 教育用途の制限が仕様書に明記される。

## Issue: ズーム/フォーカス時の撮影シミュレーションを追加する

ラベル案: `ui`

### 背景

ズーム・フォーカス位置を変えたときの歪曲変化、画角変化、フォーカスブリージングを視覚的に確認するUIは未実装である。

### 対応案

- 方眼チャートまたは画像に対して、歪曲マップを適用した簡易表示を行う。
- focus group / zoom positionの変更に応じて画角や歪曲量の変化を比較する。
- 将来の撮影結果シミュレータと接続できるようにする。

### 受け入れ条件

- 方眼チャートが歪曲量に応じて変形表示される。
- 複数のズーム/フォーカス位置を比較できる。

## Issue: 光学系の3Dデータ出力（3Dプリンタ用カットモデル）を追加する

ラベル案: `ui`, `engine`

### 背景

レンズ形状を3Dプリンタで出力して手元で確認する教育用途がある。高い光学性能を持つ必要はなく、カットモデルとしての断面形状・回転体形状を出力できればよい。

### 対応案

- 面のsagデータから回転体としての3D形状を生成する。
- 初期段階では単純な単玉/2枚玉プリセットからSTL等を出力する。
- Layout Viewの2D断面形状を3D出力に再利用できるか検討する。

### 受け入れ条件

- 単純なレンズプリセットからSTLファイルを出力できる。
- 断面カットモデルとして確認できる形状になる。

## Issue: 解析条件・表示設定のプリセット機能を追加する

ラベル案: `ui`

### 背景

波長、光線本数、センサーサイズ、チャート表示ON/OFFなどの解析条件・表示設定を、まとまった構成として呼び出したい。snapshotとは責務が一部重なるが、比較結果の保存ではなく「条件セットの再利用」を目的とする。

### 対応案

- Super35、フルフレーム、代表波長セット、低速/高速サンプリングなどの既定プリセットを用意する。
- ユーザー定義プリセットを保存・呼び出しできるようにする。
- snapshotとの違いを仕様とUI文言で明確にする。

### 受け入れ条件

- 複数の解析条件プリセットを選択できる。
- 選択によりfield、波長、sampling、表示設定がまとめて更新される。

## Issue: Layout Viewの代表光線がsampling方式に依存して見えることを説明する

ラベル案: `ui`, `docs`

### 背景

R26の確認で、P002のLayout View代表光線（lower / center / upper）はsample indexではなく、実際のSTOP面到達Y座標に基づいて選ばれていることを確認した。一方で、`grid` / 現行`hexapolar`相当の瞳サンプリングは`samples_per_field`ごとに候補点集合を作り直すため、光線数を変えると表示代表光線のSTOP到達高さそのものが変わる。これはLOD選択バグではなくsampling方式の性質だが、人間には「表示がずれた」ように見えやすい。

### 対応案

- Ray sampling設定またはLayout View付近に、代表光線は実際に生成された瞳サンプルから選ばれ、`samples_per_field`変更時には代表高さが変わる場合がある旨を短く表示する。
- 必要なら、比較用に`fan_y`など固定高さを含むsampling方式を使うと分かりやすいことをヘルプに追記する。
- 将来、Layout View専用の固定代表光線モードを追加するか検討する。

### 受け入れ条件

- `samples_per_field`変更時の代表光線の見え方がsampling由来であることをUI上で理解できる。
- 表示文言はi18n ja/en両方に追加され、`npm run i18n:coverage`が通る。
