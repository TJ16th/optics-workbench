# Issues Backlog

G5時点のGitHub Issue草案です。現在の `doc/work_orders/active/` で直接カバーされていない、次の2〜3フェーズで着手しやすい残件に絞っています。

## Active指示書でカバー済みのためIssue化しない項目

以下は `doc/work_orders/active/codex_performance_work_order.md` で扱うため、このbacklogではIssue化しません。

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
