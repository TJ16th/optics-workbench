# Engine v2.3 / UI i18n U1-U5 Implementation Status

作成日: 2026-07-09

## Summary

エンジン v2.3 指示のうち、今回の対象である **`/v1/meta` の列挙情報追加** と **構造化エラー形式 (`code` / `params` / `message_en`)** は実装済みです。

UI については、`doc/codex_ui_i18n_work_order.md` の **U1-U5** に沿って、日英 i18n、擬似ロケール、用語集ヘルプ、エラーカタログ、カバレッジCI、チャート/SVGエクスポートの言語追従を実装済みです。

P2-0更新として、以下も完了済みです。

- The workspace is Git-managed and has been maintained with task-sized commits.
- Toggletip のキーボード操作は Playwright E2E で、Surface Table列ヘッダと結果metric名の代表例を検証済み。
- SVGエクスポート成果物は ja/en、layout/spot のテキストreadback検証をCIへ追加済み。

P2-1更新として、以下も完了済みです。

- field編集（角度グリッド、追加・削除、Field ID管理）、wavelength編集（F/d/C/eプリセット、任意波長、重み）、ray_sampling編集（samples_per_field、pupil_distribution、ray aiming mode）を実装。
- 解析条件変更時に `analysis_dirty` を表示し、Preview再実行成功でcleanへ戻すdirty遷移を実装。
- trace metadataに `evaluated_fields` / `wavelengths_nm` / `pupil_distribution` を追加し、UIで実評価field一覧を表示。

P2-2更新として、以下も完了済みです。

- P003アクロマートプリセットを追加し、Analysisタブに ray fan、distortion、field curvature、relative illumination、MTF のチャート群を実装。
- ray fanはY/Z断面ペア、MTFはM/S系列と `Diffraction included: false` 注記を表示。
- 波長色規約（F=青、d/e=黄緑/緑、C=赤）を `chartTheme` に分離し、ユニットテストをCIへ追加。

P2-3更新として、以下も完了済みです。

- `image_plane_policy` 編集UIを追加し、`fixed_sensor` / `paraxial_image` / `best_focus_rms` / `best_focus_mtf` / `custom_offset` / `sweep` と `apply_to`、MTF周波数、探索範囲、sweep stepsを設定可能にした。
- `/v1/solve/best-focus` を呼ぶ薄いAPIクライアントを追加し、評価像面metadata（policy mode、評価面X、センサーからのoffset、solve status、solve metric、warnings）をAnalysisタブに表示。
- focus curveチャートとbest focus markerを表示し、Layout Viewではセンサー面とは別に評価像面/solve位置を描画。
- best focus結果をセンサー位置へ書き戻す明示ボタンと確認ダイアログを追加し、書き戻し後は `system_dirty`、未登録状態へ戻す。
- P006 afocal telescopeプリセットを追加し、afocal系では像面ポリシーUIを無効化。

P2-4更新として、以下も完了済みです。

- snapshot作成時に現在のsystem、解析条件、trace/chart/focus結果を言語非依存の生キーで保存。
- 応答内の `artifact://...` URIを検出し、`GET /v1/artifacts/{category}/{id}` で取得してsnapshotへ埋め込み。
- artifact取得失敗時は保存を中断せず、`partial: true` と欠損artifact一覧を記録。
- Compareタブに2条件比較ビューを追加し、system_hash、field、wavelength、評価像面の条件差分と、spot/MTF/RI/focus curveのsummary比較を表示。
- field、wavelength、評価像面が一致しない場合の比較可能性ガードと、partial snapshot時の「データなし」フォールバック表示を実装。
- 小容量snapshotの単一JSON exportを追加。
- P003でja/en表示が追従することを実APIブラウザ確認済み。

P2-5更新として、以下も完了済みです。

- `doc/ui_phase2_acceptance_report.md` を追加し、P2-0からP2-5までの受け入れ状況、CI証跡、supplementレビュー一覧、UI応答性メモ、残制約を集約。
- supplement glossary の ja/en エントリ数とキー一致を確認し、レビュー用一覧として記録。
- Phase 2範囲の既知制約を zip export、PNG画像比較、full snapshot compare、Raw YAML/JSON advanced editor、WebGL系チャートに整理。

ただし、以下は未完または制約があります。

- PNGエクスポート成果物の画像比較テストは未追加。
- UI v0.3 全体仕様のうち、今回の主対象は 19.2 / 27章 / 28.5 の i18n・ヘルプ範囲。Phase 2以降の MTF、PSF、Compare、本格snapshot compare、advanced raw editor などは未完。

## Source Specifications

| 対象 | 仕様書 | 主な参照箇所 |
|---|---|---|
| Engine v2.3 | `doc/optical_engine_spec_v2_3.md` | 26.9, 26.10 |
| UI v0.3 | `doc/optics_workbench_ui_spec_v0_3.md` | 19.2, 27章, 28.5 |
| UI作業指示 | `doc/codex_ui_i18n_work_order.md` | U1-U5 |

## Engine v2.3

### 指示内容

| 指示 | 期待 |
|---|---|
| `/v1/meta` に `enumerations` を追加 | metrics / error_codes / warning_codes / ray_status_codes / variable_key_patterns を返す |
| エラー・警告形式をコードベースに統一 | `severity`, `code`, `params`, `message_en` を返す |
| エンジンは多言語化しない | UIが用語集・エラーカタログから表示文を組み立てる |
| 全codeは `/v1/meta.enumerations` に列挙 | UI側CIでカバレッジ検証できる |

### 修正内容

| ファイル | 内容 |
|---|---|
| `optics_engine/metadata.py` | `API_SCHEMA_VERSION = "2.3.0"` / `RESULT_SCHEMA_VERSION = "2.3.0"`、列挙定数、`meta_payload().enumerations` を追加 |
| `optics_engine/models.py` | `ValidationIssue` を v2.3 形状へ対応。legacy `type` / `message` 入力は受けつつ、JSON出力は `code` / `message_en` に統一 |
| `optics_engine/api/main.py` | HTTPエラー応答を `severity` / `code` / `params` / `message_en` 形式へ統一 |
| `tests/test_engine_v2_3.py` | 構造化エラー、validate結果、HTTPエラー、meta列挙の回帰テストを追加 |
| `tests/test_engine_v2_1.py` | v2.3 meta列挙を含む形へ既存metaテストを更新 |

### 結果

| 検証 | 結果 |
|---|---|
| `/v1/meta` | `api_schema_version: 2.3.0`、`result_schema_version: 2.3.0`、`enumerations` を返す |
| validation issue | `type` / `message` ではなく `code` / `message_en` としてシリアライズ |
| API error | `system_not_found` などが構造化エラーで返る |
| テスト | Pythonテストは最終確認時点で `51 passed` を確認済み |

### 仕様との差分・未完

| 項目 | 状態 | メモ |
|---|---|---|
| v2.3小改訂の主対象 | 完了 | 26.9 / 26.10 の範囲は対応済み |
| エンジン本体の多言語化 | 対象外 | 仕様通り、翻訳はUI責務 |
| `engine_version` | 制約あり | `ENGINE_VERSION` は `0.1.0` のまま。API/Result schema version は `2.3.0` |
| v2.2以前からの大規模将来機能 | 未完 | 最適化API、Numba最適化、PSF/MTF詳細、afocal本格評価などは別フェーズ |

## UI U1-U5

### U1: i18n基盤導入

| 項目 | 内容 |
|---|---|
| 指示 | `react-i18next` 導入、ja/enリソース、言語自動判定、手動切替、永続化、擬似ロケール、`i18n:check` |
| 修正 | `i18next`, `react-i18next`, `i18next-parser` を追加。`src/i18n/` に初期化、リソース集約、擬似ロケール生成、数値/日時フォーマットを追加 |
| 結果 | `npm.cmd run i18n:check`、`npm.cmd run ui:build:pseudo` 通過。言語設定は `localStorage` に保存 |

主なファイル:

- `apps/workbench-ui/src/i18n/index.ts`
- `apps/workbench-ui/src/i18n/resources.ts`
- `apps/workbench-ui/src/i18n/format.ts`
- `apps/workbench-ui/.env.pseudo`
- `apps/workbench-ui/i18next-parser.config.cjs`
- `package.json`

### U2: Phase 1 UIからの文字列抽出

| 項目 | 内容 |
|---|---|
| 指示 | 主要画面の表示文字列をja/enリソースへ移動。数値・単位・識別子は非翻訳 |
| 修正 | `App.tsx` を `useTranslation` ベースへ更新。プリセット表示、操作ボタン、パネル見出し、ステータス、Raw JSON周辺、解析表示をローカライズ |
| 結果 | ハードコード表示文字列の監査で主要な残存なし。生の surface ID / system_id / raw JSON / metric key は翻訳対象外として維持 |

主なファイル:

- `apps/workbench-ui/src/ui/App.tsx`
- `apps/workbench-ui/src/i18n/locales/ja/*.json`
- `apps/workbench-ui/src/i18n/locales/en/*.json`

### U3: 用語集統合と3階層ヘルプ

| 項目 | 内容 |
|---|---|
| 指示 | `glossary.ja.json` / `glossary.en.json` を配置し、Toggletip、Help Drawer、エラー解説を実装 |
| 修正 | 付属用語集を配置。v2.3 meta列挙で不足する識別子は supplement 用語集で補完。`termLabel` / `renderEngineIssue` を実装 |
| 結果 | Surface Table列ヘッダ、metric、チャートラベル、エラー表示が用語集を参照。Help Drawer と see_also 回遊を実装 |

主なファイル:

- `apps/workbench-ui/src/i18n/glossary.ts`
- `apps/workbench-ui/src/i18n/glossary/glossary.ja.json`
- `apps/workbench-ui/src/i18n/glossary/glossary.en.json`
- `apps/workbench-ui/src/i18n/glossary/glossary.supplement.ja.json`
- `apps/workbench-ui/src/i18n/glossary/glossary.supplement.en.json`

P2-0追記:

- Playwright E2Eで、Surface Tableの `radius_mm` ヘッダと解析metricの `ray_fan` について、キーボードフォーカス、Enterによる展開、Escによる閉鎖を検証済み。

### U4: カバレッジCI

| 項目 | 内容 |
|---|---|
| 指示 | ja/en用語集キー一致、`/v1/meta.enumerations` カバレッジ、i18n未定義/未使用キー検出、擬似ロケール検証 |
| 修正 | `i18n-check.mjs`、`i18n-coverage.mjs`、`i18n-unit-tests.mjs` を追加。`ci` に組み込み |
| 結果 | `npm.cmd run ci` 通過。意図的に1項目を削るレッドテストも失敗検出を確認済み |

主なファイル:

- `apps/workbench-ui/scripts/i18n-check.mjs`
- `apps/workbench-ui/scripts/i18n-coverage.mjs`
- `apps/workbench-ui/scripts/i18n-unit-tests.mjs`
- `apps/workbench-ui/README.md`

### U5: チャート・エクスポートの言語追従

| 項目 | 内容 |
|---|---|
| 指示 | チャート表示、SVG/PNGエクスポート、snapshot表示を現在言語または選択言語に追従 |
| 修正 | Layout / Spot のSVG内ラベル、エクスポート言語選択、snapshot表示ラベルの実行時ローカライズを実装 |
| 結果 | ja/en表示と擬似ロケール表示を確認。snapshotの言語非依存ユニットテスト通過。SVG readbackで ja/en の出力ラベル追従を検証 |

未完・制約:

- SVGエクスポート成果物のテキストreadbackは自動化済み。PNG成果物の画像比較テストは未追加。

## UI v0.3 28.5 Acceptance Status

| 検証 | 期待 | 状態 | メモ |
|---|---|---|---|
| 言語切替 | ja/en切替、主要画面全文言切替、再起動後保持 | 完了 | `localStorage` 永続化、ja/enスクリーンショット確認 |
| 識別子非翻訳 | surface ID、metric生キー、raw JSONは不変 | 完了 | raw JSON/API識別子は翻訳しない設計 |
| 小数点固定 | ja/en両方でピリオド固定 | 完了 | `formatFixed` と単体テストで確認 |
| Toggletip | Surface Table全列ヘッダと結果metric名でキーボード操作により開閉 | 完了 | Playwright E2Eで Surface Table代表ヘッダ `radius_mm` とmetric代表 `ray_fan` を検証 |
| エラーカタログ | `negative_air_gap` はja/enカタログ文言、未登録は `message_en` | 完了 | `i18n:test` で確認 |
| カバレッジCI | 27.6の4検証がCIジョブとして存在しグリーン | 完了 | `i18n:check`, `i18n:coverage`, `i18n:test`, `svg:export:test`, `ui:e2e` |
| エクスポート言語 | SVGエクスポートで出力言語選択、軸ラベル追従 | 完了 | SVG成果物readbackで ja/en、layout/spot のタイトル・軸ラベルを検証 |

## UI Phase 2 P2-1 Acceptance Status

| 検証 | 期待 | 状態 | メモ |
|---|---|---|---|
| field編集 | 角度fieldのID・Y/Z角を編集でき、追加・削除できる | 完了 | 右ペインの解析条件パネルに実装 |
| wavelength編集 | F/d/C/eプリセット、任意波長、重みを編集できる | 完了 | Previewには `wavelengths_nm` と `wavelength_weights` を送信 |
| ray_sampling編集 | samples_per_field、pupil_distribution、aiming modeを編集できる | 完了 | grid / hexapolar / random / fan_y / fan_z と paraxial / full / off |
| dirty遷移 | field/wavelength/sampling変更でanalysis_dirty、Preview再実行でclean | 完了 | Playwright E2Eで確認 |
| 実評価field表示 | 応答metadataの実評価field一覧を表示する | 完了 | `trace.metadata.evaluated_fields` を表示。metadataはエンジン側にも追加 |

## UI Phase 2 P2-2 Acceptance Status

| 検証 | 期待 | 状態 | メモ |
|---|---|---|---|
| P003プリセット | アクロマートでチャート群を確認できる | 完了 | `P003 Achromat Doublet 100mm Demo` を追加 |
| ray fan | Y/Z断面ペア表示、用語集ヘルプ導線 | 完了 | 波長色で系列表示。Help Drawer導線あり |
| distortion | 像高field角 vs 歪曲率 | 完了 | `/v1/analysis/distortion` を表示 |
| field curvature | M/S像面カーブ | 完了 | field curvature と ms-image-surface 応答を統合 |
| relative illumination | field角 vs 周辺光量 | 完了 | `/v1/analysis/relative-illumination` を表示 |
| MTF | M/S系列、周波数軸lp/mm、幾何MTF注記 | 完了 | `Diffraction included: false` を明示 |
| 波長色規約 | F/d/e/C線の固定色 | 完了 | `npm.cmd run chart:test` で検証 |

## UI Phase 2 P2-3 Acceptance Status

| 検証 | 期待 | 状態 | メモ |
|---|---|---|---|
| image_plane_policy編集 | mode、apply_to、criteria相当のfield/wavelength weights、MTF frequency、探索条件をUIで設定できる | 完了 | field/wavelength weightsは既存Analysis Conditionsと連動し、policy.criteriaへ送信 |
| 評価像面metadata表示 | policy_mode、評価面位置、センサーからのoffset、solve_statusを表示する | 完了 | AnalysisタブのEvaluation Planeパネルに表示 |
| solve_not_converged warnings | エラーカタログ経由で警告を表示する | 完了 | `evaluation_plane.warnings` を `renderEngineIssue` で表示 |
| focus curve | X position vs metricとbest focus markerを表示する | 完了 | `/v1/solve/best-focus` の `focus_curve` をChartSvgで表示 |
| sensor write-back | solve結果をOpticalSystem draftへ反映し、system_dirty化する | 完了 | 直前面の `thickness_after_mm` にoffsetを加算し、system_id/validationを破棄 |
| Layout View区別 | センサー面、評価像面、solve位置を区別する | 完了 | 評価像面を青破線、solve位置を赤破線で描画 |
| afocal無効化 | P006ではpolicy UIを無効化する | 完了 | P006 afocal telescopeプリセットを追加 |

## UI Phase 2 P2-4 Acceptance Status

| 検証 | 期待 | 状態 | メモ |
|---|---|---|---|
| artifact埋め込み | snapshot作成時にartifact URIをGETして埋め込む | 完了 | JSON artifactをsnapshot `artifacts` へ保存 |
| partial snapshot | artifact取得失敗時にpartial保存し、欠損一覧を記録する | 完了 | E2Eで `artifact_expired` をモック |
| 2条件比較 | 2つのsnapshotを選び、条件差分とspot/MTF/RI/focus summaryを比較できる | 完了 | CompareタブにA/B selectorと比較表を追加 |
| 比較可能性ガード | field・波長・評価像面不一致を警告する | 完了 | `Comparison guard` notificationを表示 |
| 言語非依存 | snapshotは生キー保存、表示時ローカライズ | 完了 | metric labelは `termLabel` で表示時解決 |
| export | 小容量snapshotは単一JSONでexportできる | 部分完了 | zip export（snapshot.json + artifacts/）は未実装 |

## Verification Results

最終確認で通過したコマンド:

```powershell
npm.cmd run ci
```

`npm.cmd run ci` の内訳:

```text
ui:build
i18n:check
i18n:coverage
i18n:test
svg:export:test
ui:e2e
```

P2-0で確認済み:

```text
i18n:coverage ok
svg-export-readback ok: ja/en layout/spot labels verified
Playwright E2E: 1 passed
npm.cmd run ci: passed
```

P2-1で確認済み:

```text
npm.cmd run ci: passed
Playwright E2E: 2 passed
Python pytest: 57 passed
```

P2-2で確認済み:

```text
npm.cmd run ci: passed
Playwright E2E: 3 passed
chart-theme:test ok
P003 ja/en browser screenshots: captured with real local API
```

P2-3で確認済み:

```text
npm.cmd run ci: passed
Playwright E2E: 4 passed
i18n:check ok (108 keys)
chart-theme:test ok
```

P2-4で確認済み:

```text
npm.cmd run ci: passed
Playwright E2E: 6 passed
i18n:check ok (120 keys)
partial snapshot fallback E2E: passed
```

P2-5で確認済み:

```text
npm.cmd run ci: passed
Playwright E2E: 6 passed (18.5 s)
supplement glossary: ja/en terms 7 each, errors 26 each
acceptance report: doc/ui_phase2_acceptance_report.md
```

Vite buildでは、依存パッケージ由来の `"use client"` directive ignored 警告が出るが、ビルド自体は成功している。

## Screenshots

| 種類 | ファイル |
|---|---|
| ja | `<workspace>/capture-ui-i18n-ja.png` |
| en | `<workspace>/capture-ui-i18n-en.png` |
| pseudo | `<workspace>/capture-ui-i18n-pseudo.png` |
| help drawer | `<workspace>/capture-ui-help-drawer.png` |

## Remaining Work

優先度順:

1. zip export（snapshot.json + artifacts/）とPNG成果物の画像比較テストを必要に応じて追加する。
2. UI v0.3の残範囲、特に full snapshot compare、Raw YAML/JSON advanced edit を次フェーズで実装する。
3. Engine v2.3小改訂外の将来機能、特に最適化API、afocal本格評価、PSF/MTF詳細、Numba高速化を別計画で進める。
