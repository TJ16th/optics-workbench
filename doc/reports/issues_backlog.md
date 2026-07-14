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

- まず単色・軸上・円形瞳を対象に、実光線追跡で光路長（OPL）と瞳座標を取得し、参照球面との差からOPDを求める。
- OPDを規則瞳格子へ写像し、`P(u,v) = A(u,v) exp(i 2π OPD/λ)`のFFTから回折PSFを計算する。`A(u,v)`にはcircle/annulus、ケラレを反映する。
- 幾何PSFとの責務境界をAPIの`mode: geometric | diffraction`と`diffraction_included` metadataで明確にし、未実装中は`capabilities.diffraction_psf=false`を維持する。
- white PSF/MTFは波長ごとの回折PSFを共通の像面物理格子へ再標本化して重み付き合成し、その後にMTF化する。
- Zernike近似は波面診断・圧縮表現には利用できるが、annulusや局所的な瞳欠損を失わないよう、直接OPD格子を正本とする。

### 受け入れ条件

- 理想円形瞳でAiry第1暗環`1.22 λ N`と円形瞳の解析MTFに対する基礎検証ができる。
- OPDのpiston不変性、既知defocus、annulus遮蔽、ケラレ、複数波長の共通物理格子合成を直接テストできる。
- 同一入力・同一格子でPSF/MTF配列が決定論的になる。
- APIレスポンスのartifact方針が既存PSF/MTFと整合する。
- 実装完了時にのみ`capabilities.diffraction_psf=true`となり、幾何/回折の別がレスポンスで判別できる。

### R73設計調査追記（2026-07-13）

現行`TraceResult.paths`は交点・入射方向・statusを保持するが、区間光路長、区間屈折率、OPL、正規化瞳座標は保持しない。このため変更は`psf_mtf.py`内に閉じず、traceカーネル、結果モデル、API/artifact、white合成、検証まで横断する「大」規模となる。推奨は、光線ベースのOPL計測と参照球面OPDを正本にして直接FFTする方式である。Zernike fittingは第2段階の診断・高速近似として追加し、初期実装の唯一の波面表現にはしない。

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

## Issue: P005/P006のpreview/traceでNaN JSON serializationエラーが発生する

ラベル案: `engine`, `testing`

### 背景

R29の全プリセット有効径見直し中、P005（coaxial Cassegrain）とP006（afocal telescope）で`/v1/education/preview`および`/v1/trace/forward`が`400`を返した。`ray_aiming.mode`を`full` / `paraxial` / `off`に変えても、いずれも`Out of range float values are not JSON compliant: nan`となり、P005/P006の実光線ベース評価を継続できなかった。

### 対応案

- P005/P006のtrace resultまたはmetadataに`NaN`が混入する経路を特定する。
- APIレスポンス直前で非有限値を構造化エラーまたは`null`へ正規化する方針を決め、エンジン仕様の非有限値扱いと整合させる。
- P005/P006に対する`/v1/education/preview`および`/v1/trace/forward`の回帰テストを追加する。

### 受け入れ条件

- P005/P006のpreview/traceがJSON serialization errorで失敗しない。
- 非有限値が発生する場合も、`severity / code / params / message_en`の構造化エラーまたは仕様で定めた正規化値として返る。
- R29のような全プリセット横断評価で、P001〜P007を同一手順で評価できる。

## Issue: アフォーカル系のアイポイントに眼球モデルを接続し、網膜結像として評価できるようにする

ラベル案: `engine`

### 背景

現行のafocal系評価（双眼鏡・望遠鏡）は、終端要素`eye_reference`（射出瞳・アイレリーフ・角度MTF等）までを評価対象とし、「眼に渡す角度像の品質」を間接的な指標で評価する設計（エンジン仕様9.2節・22章）である。これに対し、眼球そのもの（角膜・水晶体・網膜相当）を簡易光学系としてモデル化し、`eye_reference`の後段に接続することで、実際の網膜結像（spot・MTF）まで直接評価する手法を追加したいという提案がある。視覚光学で用いられるGullstrand模型眼、Navarro模型眼等の簡易模型眼を接続する形を想定する。

R68の設計調査では、現行traceカーネルが`eye_reference`で停止せず後続面を追跡できる一方、`system_type`の終端検証、射出瞳・アイレリーフ集計、主絞り、結果の単位系が1システム全体に固定されていることを確認した。また、仕様上の`position_mode: at_exit_pupil`に対応する自動配置処理は現行コンパイル処理に見当たらず、単純な面列延長だけでは仕様上の責務を保てない。

### 対応案

- 初期版は587.56 nmの簡約Gullstrand眼を採用する。角膜前面`R=+7.70 mm, t=0.50 mm, n=1.376`、角膜後面`R=+6.80 mm, t=3.10 mm, n=1.336`、水晶体前面`R=+10.0 mm, t=3.60 mm, n=1.4085`、水晶体後面`R=-6.00 mm, t=17.187 mm, n=1.336`を既存の球面`refractive`で表す。初期版の網膜は平面`sensor`とし、曲率`R=-17.2 mm`の網膜は曲面評価面対応へ分離する。
- 一般的なsystem chainingグラフは初期版では導入しない。単一面列内に、装置側afocal区間、`eye_reference`中間境界、模型眼区間、網膜`sensor`を持つ明示的な「視覚評価コンポジット」を追加する。
- コンパイル時に`eye_reference`境界indexを保持し、装置側の射出瞳・アイレリーフ・角度spot/MTFは境界まで、網膜spot/MTFは境界後の`sensor`までとして結果名前空間を分離する。ray aimingの主絞りは装置側、`eye_reference`は眼瞳クリップとして扱う。
- `position_mode: at_exit_pupil`の実配置を実装し、固定offsetとの排他・位置検証を追加する。模型眼へ入る媒質はAIRとし、初期版は固定瞳径・無調節・単色とする。
- 将来の任意system chainingは、複数装置接続、座標変換、媒質handoff、個別cacheが必要になった段階で別Issueとして設計する。

### 受け入れ条件

- 簡約Gullstrand眼を`eye_reference`後段に接続し、網膜相当`sensor`でspot/MTFを評価できる。
- 同じtraceから、装置側の射出瞳・アイレリーフ・角度spot/MTFと、模型眼側の網膜spot/MTFを別の結果として取得できる。
- 装置側評価が模型眼の屈折面を含めてアイレリーフや角倍率を再計算しないことを直接テストで固定する。
- `position_mode: at_exit_pupil`が計算済み射出瞳位置へ実配置され、固定offset時も境界位置が決定論的になる。
- 平面網膜、単色、固定調節という初期版の制限を仕様とcapabilitiesに正確に記載し、曲面網膜や眼分散を未実装のまま列挙しない。

## Issue: 実体を持つ後続面による内径側の固定遮蔽を自然に表現する

ラベル案: `engine`

### 背景

カセグレン式望遠鏡の副鏡M2のように、後続する光学面自体の物理径が前段光束の中央遮蔽を生む場合がある。現行仕様は各面で外径超過を遮光する局所判定と、専用annulus面による内径遮蔽を持つが、後続面の`semi_diameter_mm`から前段の内径遮蔽を導出する表現はない。

### 対応案

- 面が前段光路へ投影する内径遮蔽を、明示的な参照またはコンパイル時に生成する遮蔽制約としてモデル化する。
- 非局所遮蔽がray aiming、pupil sampling、paraxial pupil、実光線traceへ与える影響を統一して扱う。
- 専用annulus面を自動挿入する方式と、面属性として遮蔽投影を持つ方式を比較する。

### 受け入れ条件

- 副鏡面の物理径から前段光束の中央遮蔽を表現できる。
- 同じ遮蔽がaiming、sampling、traceで一貫して適用される。
- 専用annulus面との重複遮蔽を検出または防止できる。

## Issue: 実体を持たない固定内径遮蔽のannulus定義とUIを維持・整備する

ラベル案: `engine`, `ui`

### 背景

鏡筒内壁や遮光環など、対応する光学面を持たない機械的制約には、現行の`mechanical_aperture`と`shape: annulus`が適している。エンジンの遮光判定は利用可能で、R47でSystemタブのinner/outer表示・編集は追加されたが、固定遮蔽としてのLayout View表現、検証、文書化を横断的に固定する必要がある。

### 対応案

- `mechanical_aperture`のannulusを固定内径遮蔽の標準表現として仕様化する。
- Systemタブ、Layout View、validate、traceのinner/outer扱いを直接テストする。
- `aperture_stop`のannulusとの役割差をUIと仕様で明確にする。

### 受け入れ条件

- mechanical annulusをSystemタブで表示・編集し、Layout Viewで単一の固定遮蔽として確認できる。
- inner未満とouter超過の光線が決定論的に遮光される。
- 主開口絞りとの役割差と併用規則が仕様に記載される。

## Issue: mechanical_apertureをフォーカス・ズーム連動の可変位置・可変径に拡張する

ラベル案: `engine`, `ui`

### 背景

マクロレンズ等では、フォーカス群の移動に連動して副絞りの位置と径が変化する。現行のgroups/zoom_positionsは群に含めた`mechanical_aperture`のX/Y/Z移動には利用できるが、`group_positions`はshiftだけを持ち、configurationごとの開口径変更は表現できない。

### 対応案

- mechanical apertureを既存groupへ所属させる位置変更手順を仕様とUIで明示する。
- `group_positions`またはsurface overrideへconfiguration別の`semi_diameter_mm`/inner/outer値を追加する。
- compile cache、validation、optimization variable、trace metadataへconfiguration依存径を反映する。

### 受け入れ条件

- focus/zoom positionごとにmechanical apertureの位置と径を決定論的に切り替えられる。
- circleとannulusのconfiguration依存径をvalidate・trace・Layout Viewが同じ値で扱う。
- 既存の固定mechanical apertureとの後方互換性を維持する。

## Issue: mechanical_apertureにrectangle形状を追加する

ラベル案: `engine`, `ui`

### 背景

マウント、ミラーボックス、センサー前枠などの矩形開口によるケラレは、circle/annulusでは正確に表現できない。実務上の利用頻度が比較的高い。

### 対応案

- `shape: rectangle`とY/Z方向の半幅または幅・高さをデータモデルへ追加する。
- 回転・偏芯を含むローカル面座標で通過判定し、SystemタブとLayout Viewへ形状を表示する。

### 受け入れ条件

- 矩形内外の境界テストが通る。
- rectangleを含む系をvalidate、compile、trace、表示できる。
- circle/annulusの既存結果が変わらない。

## Issue: mechanical_apertureのpolygon・花形輪郭表現を拡張する

ラベル案: `engine`, `ui`

### 背景

正多角形の絞り羽根、角型・花形フードなどの輪郭によるケラレを扱うには、現行モデルで予約されている`polygon`を実用的な頂点・回転定義へ拡張する必要がある。教育上・実務上の優先度はrectangleより低いため、用途を精査してから着手する。

### 対応案

- 正多角形パラメータと任意頂点列のどちらを初期スコープにするか決める。
- 凹形状、自己交差、頂点順、ローカル回転のvalidation規則を定義する。
- traceとLayout Viewで同じ輪郭データを使用する。

### 受け入れ条件

- 採用したpolygon表現の内外判定と境界規約がテストされる。
- 回転したpolygon開口をtraceとLayout Viewで一貫して扱える。
- 教育用途と優先順位が仕様またはIssue判断に記録される。

## Issue: 3次元光線と2D Layout View開口断面の投影差を明示する

ラベル案: `ui`

### 背景

現行Layout Viewは3次元光線をX-Y断面へ投影する一方、circle/annulusの開口はY方向断面として描画する。Z成分を持つ光線は、実際の半径`sqrt(Y^2+Z^2)`ではannulus開口帯内でも、2D表示上のYだけを見ると中央遮蔽内を通過しているように見える場合がある。trace結果は正しいが、投影差を知らない利用者には矛盾して見える。

### 対応案

- Layout ViewにY投影であることを示すToggletipまたは表示モード情報を追加する。
- X-Z断面への切り替え、Y/Z断面の併記、または選択光線の`Y / Z / radius`数値表示を比較する。
- annulus通過判定がY単独ではなく半径であることを、選択光線の詳細表示から確認できるようにする。

### 受け入れ条件

- Z成分を持つ光線について、2D投影と3D開口判定の違いをUI上で確認できる。
- circle/annulusの通過・遮蔽statusと表示説明が矛盾しない。
- 既存のX-Y Layout Viewを過密にせず、キーボード操作とja/en表示に対応する。

## Issue: 同軸系の像面湾曲・M/S像面にCoddington方式を実装しmethodを正す

ラベル案: `engine`, `testing`

### 背景

R74作業1で、`POST /v1/analysis/field-curvature`と`POST /v1/analysis/ms-image-surface`は外部`ray_sampling`を解析関数へ渡さず、内部固定の`21 rays / grid / paraxial`でセンサー位置を11点走査するRMS探索を実行していることを確認した。同軸系では`method: coddington_rms_consistent`を返すが、Coddington方程式は実装されておらず、`doc/engine_spec.md` 21.2節の「同軸系はCoddingtonを既定」と一致しない。

P003ではfield curvatureとM/S像面の全fieldが既定探索範囲の端`-5.0 mm`へ張り付くが、非収束または範囲不足として通知されない。既存`tests/test_phase5_tilt_asymmetric_ms.py`は値が非nullであることとmethod文字列だけを確認しており、実方式や探索端を検証していない。

R75作業1の実装コミット`84c592fdd967ca4f96c70a8a3b938992e1ebb01e`で、P002/P003を含む球面・平面屈折系と理想薄レンズ系のCoddington計算、正しいmethod、RMS探索端warning、再現条件metadataは対応済みとなった。残件は、ミラー反射の符号規約とeven asphereの局所主曲率をCoddington漸化式へ組み込み、同軸のミラー・非球面系でも`rms_search`フォールバックを不要にすることである。

### 対応案

- 同軸系向けに、aiming済み主光線に沿ったCoddington方程式によるM/S像面計算を実装し、既定方式とする。
- RMS探索は偏芯・チルト系および相互検証用の明示modeとして残し、サンプル数、distribution、aiming、探索範囲、探索刻みを結果metadataへ含める。
- `field-curvature`と`ms-image-surface`の両レスポンスへ実際の計算方式を示すmethod metadataを追加し、`coddington_rms_consistent`という誤解を招く名称を廃止する。
- RMS最良点が探索範囲端にある場合は、探索範囲拡張または`solve_not_converged`相当の構造化warningを返す。

### 受け入れ条件

- P002/P003同軸系の既定応答が実際の`coddington`計算となり、瞳サンプル数を変えても同一値になる。
- Coddington結果を独立した近軸参照式またはGolden Testで検証し、RMS探索との比較差をテストする。
- 偏芯・チルト系のRMS modeでは、使用したサンプリング条件と探索条件がmetadataから確認できる。
- P003のように探索解が範囲端へ張り付く場合、収束済みの値として無警告で返さない。
- `field-curvature`と`ms-image-surface`のmethod表示が実際の計算経路と一致する。

## Issue: 周辺光量に解析専用サンプリングと正確な放射量metadataを導入する

ラベル案: `engine`, `performance`, `testing`

### 背景

R74作業2で、WorkbenchのRun Chartsは共有`ray_sampling`を`POST /v1/analysis/relative-illumination`へそのまま渡し、UI既定の`9 rays / grid / paraxial`で周辺光量を計算することを確認した。周辺光量専用の最小サンプル数や収束判定はない。

P002の40 deg fieldでは、100000 rays時のthroughput `0.89541`に対し、9 raysでは`1.0`となり、relative illuminationを`11.68%`過大評価した。現行実装は瞳gridの到達率へcos⁴を明示乗算する`ray_throughput_times_cos4`であり、仕様16.5・21.4節の等立体角または等価な重み付きサンプリングからcos⁴を自然導出する定義とは異なる。またresponse metadataにサンプル数、distribution、aiming、重み付け方式がない。

### 対応案

- 周辺光量解析に専用sampling設定を設け、共有preview値とは分離して既定を少なくとも1000 rays/fieldとする。
- 仕様16.5節に沿い、物体空間の等立体角サンプリングまたはヤコビアンを持つ重み付き瞳サンプリングを実装する。
- cos⁴を別途乗算する近似を維持する場合は、仕様方式と明確にmodeを分け、二重計上を防ぐ。
- response metadataへ要求/実使用サンプル数、distribution、aiming、weighting、seed、到達数を含める。
- UIに周辺光量の精度presetまたは収束状態を表示し、Run Chartsの30秒性能ガードと両立させる。

### 受け入れ条件

- Run Charts既定9 raysが、周辺光量の最終値に暗黙利用されない。
- P002 40 deg等のpartial vignetting系で、既定設定が高密度参照値に対する規定誤差内へ収束する。
- 放射量サンプリングとcos⁴の扱いが`doc/engine_spec.md` 16.5・21.4節と一致する。
- response metadataだけで計算の再現条件を取得できる。
- 同一seed入力はビット同一となり、sampling精度と実行時間の回帰テストがある。

## Issue: 周辺光量とRMS像面探索に適応的収束サンプリングを導入する

ラベル案: `engine`, `performance`, `testing`

### 背景

R74作業2では、周辺光量の誤差がサンプル数に強く依存し、P002 40 degで9 raysが100000 rays基準を`11.68%`過大評価した。現行gridはNごとに点集合を再構成するため誤差が単調減少せず、固定Nだけでは収束済みか判定できない。R74作業1で確認したRMS像面探索も、本来は偏芯・チルト系でサンプリング依存となる。

このIssueは、先行する「周辺光量に解析専用サンプリングと正確な放射量metadataを導入する」と「同軸系の像面湾曲・M/S像面にCoddington方式を実装しmethodを正す」の後段に位置付ける。

### 対応案

- sample indexを継続できるnested・seed付きサンプラを導入し、前段の光線を捨てずにbatchを追加する。
- 周辺光量では、重み付きfluxと中心field比の標準誤差/信頼区間を計算し、相対・絶対許容誤差を満たすまでNを増やす。
- 統計仮定を置かない補助条件として、N→2Nの推定値差が閾値以下になることを2段階連続で要求する。
- 偏芯・チルト系のRMS像面探索では同一ray列を再利用し、M/S焦点位置とRMS幅の両方が連続2段階で安定したとき収束とする。
- `initial_samples`、`max_samples`、`relative_tolerance`、`absolute_tolerance`、`confidence`、`seed`、`time_budget_ms`をAPIで指定可能にする。
- response metadataへ`samples_used`、`levels`、`estimated_error`、`confidence_interval`、`converged`、`stop_reason`、`elapsed_ms`を返す。
- `max_samples`または`time_budget`で未収束終了した場合は、構造化warning `sampling_not_converged`を返し、`/v1/meta` enumerationsへ追加する。

### 受け入れ条件

- 同一seed・同一入力でサンプル列と最終レスポンスがビット同一になる。
- 追加batchが既存sampleを再計算せず、固定高密度計算より少ない光線数で規定誤差を満たす代表ケースがある。
- P002 40 deg等のpartial vignettingで、返却した信頼区間または逐次差分が高密度参照誤差を過小評価しない。
- 収束、最大sample、時間切れの各停止経路が直接テストされる。
- Run ChartsのP007/P009 E2Eが30秒以内を維持し、未収束時も値とwarningを表示できる。
- 同軸系のCoddington計算には不要なadaptive RMS samplingを適用しない。

## Issue: ArtifactStoreの短TTLテストを時刻ジッタに強くする

ラベル案: `testing`

### 背景

R74完了監査の`python -m pytest -q`で、`tests/test_engine_v2_3.py::test_artifact_http_lifecycle_content_types_and_expiry`が生成直後のartifact取得に404を返し、1回失敗した。このテストは`ttl_seconds=0.02`（20 ms）を使用するため、artifactを3件生成してTestClientから取得するまでにTTLを超えると、expiry確認前の正常取得まで失敗する。対象テストだけを別processで5回反復すると5/5 passであり、時刻・負荷依存のflakyと判断する。R74の変更は文書のみで、この失敗経路とは無関係である。

### 対応案

- ArtifactStoreへ注入可能なclockを設け、正常取得とexpiryを実時間sleepに依存せず検証する。
- clock注入を避ける場合は、正常取得用storeと短TTL expiry用storeを分離し、正常取得側には十分長いTTLを使う。
- full suite負荷下で再現する反復テストを追加し、20 ms未満のscheduler/IOジッタへ依存しない構成にする。

### 受け入れ条件

- artifact生成直後のJSON/PNG/NPY取得が負荷や実行順に依存せず200となる。
- expiry後の404をfake clockまたは十分な時間差で決定論的に検証できる。
- 対象テストを100回反復してflaky failureが発生しない。
- ArtifactStore本体のTTL semanticsとAPI content-type検証を維持する。

## Issue: P011の周辺fieldでfull aiming収束失敗を解消する

ラベル案: `engine`, `testing`

### 背景

R67で追加したP011 Planar/Xenon型50 mm F1.4を、3 fields × 3 wavelengths × 25 rays、`hexapolar`、`full` aimingで追跡すると、225本中`alive 213`、`aiming_failed 12`となる。R80でも現行HEAD `1031997`（機能コミット`b655a3a`）の実APIで同値を再現した。`blocked 0`であるため開口遮光ではなく、周辺fieldの主光線aimingが収束せず像面へ到達しない既知問題である。また、既存のP011直接回帰は中心81-ray spot RMSの期待値`0.4654229601 mm`に対して`0.4654474966 mm`を決定論的に返して失敗する。到達数の既知値は一致しているが、このRMS差も原因切り分けが必要である。

### 対応案

- 失敗12本のfield、wavelength、pupil座標、反復履歴を構造化して特定する。
- affine seed、Jacobian更新、収束判定、iteration上限のどこで失敗するかをLevel 0リファレンス実装と比較する。
- P011固有の処方問題と汎用full aimingアルゴリズムの問題を切り分け、必要ならfallback aimingを設計する。
- 修正時はP011だけでなくP007等の高速系プリセットでも到達率と決定論を回帰テストする。

### 受け入れ条件

- P011の同条件で`aiming_failed 0`となり、225本が像面へ到達する、または物理的に到達不能な光線が別の正しいstatusへ分類される。
- `blocked`と`aiming_failed`を混同せず、原因をmetadataまたは構造化warningから判別できる。
- 中心81-ray spot RMSの正しい基準値をLevel 0との比較で確定し、`tests/test_preset_api_smoke.py::test_p011_planar_double_gauss_has_six_positive_thickness_elements`がグリーンになる。
- Level 0/Level 1の代表光線が許容差内で一致し、既存のaiming Golden Testがグリーンを維持する。

## Issue: Jacobian warm refinementの適用判定と性能profilingを追加する

ラベル案: `engine`, `performance`, `testing`

### 背景

R91でJ2独立exact有限差分とJ3 request-local warm refinementを実装した。R83条件の再測定では、J3はJ2比で高速化する条件が多い一方、P007/P012の一部測定ではwarm Newtonのline-search・cold fallback負荷が独立exactを上回った。P011でも変数数に対する時間の単調性が崩れる測定があり、現在のaggregate時間だけではCPU外乱と候補別収束コストを分離できない。

### 対応案

- candidate・variable・field・wavelengthごとにwarm iteration、line-search trial、cold fallback、aiming時間、trace時間を固定順metadataへ集計する。
- 基準originからの初期residual、予測Newton step、候補geometry差を使い、warm refinementを適用するか最初からcold exactへ送る決定論的な判定を追加する。
- P002/P007/P011/P012の1/5/10/20変数を交互順・複数processで測定し、熱・scheduler・ブラウザ負荷の影響を分離する。
- J3単体の改善を確認した後に、R91対象外のJ4 candidate軸batch kernelへ投資するか判断する。

### 受け入れ条件

- 同一requestの数値結果と適用判定が履歴に依存せずビット同一である。
- warmを選んだcandidateは代表プリセット全体で独立exactより遅くならないか、遅くなる場合は規定閾値でcoldへ切り替わる。
- response metadataから候補別の反復・fallback・時間内訳を再現できる。
- R83条件の複数回測定で中央値と分散を報告し、`1.25 x cold`目標に対する達否を安定して判定できる。
