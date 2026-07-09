# Optics Workbench UI Phase 2 作業指示書（Codex向け・タスクP2-0〜P2-5）

## 背景と前提

UI Phase 1＋i18n/ヘルプ（U1〜U5）は実装済み。本指示書はUI仕様v0.3 29章の**Phase 2（写真レンズ解析）**を実装する。

**着手前提**：エンジンAPI追補（タスクA0〜A3）が完了していること。特にP2-3はA1（image_plane_policy）、P2-4はA2（GET /v1/artifacts）に依存する。A1/A2未完の状態でP2-3/P2-4に着手しない（モックで代替しない）。

仕様の根拠：UI仕様v0.3の13章（解析条件編集）、14章（評価像面）、17章（可視化規約）、20章（LOD）、22.4節（snapshot永続化）、27章（i18n/ヘルプ）、28章（受け入れ条件）。エンジン仕様v2.3の21.5節・26.8節。

## 進め方

タスクは番号順に1タスクずつ。完了報告後に停止する。各タスクはGitの独立コミットとする（A0でリポジトリ化済み）。

## 恒常DoD（全タスクに適用。U1〜U4で整えた規律の維持）

1. **新規の表示文字列はすべてi18nリソース経由**。ハードコード禁止。
2. **新しく表示するmetric・エラーコード・チャート種別には、glossary ja/en両方のエントリ追加をセットで行う**。i18n:check / i18n:coverage / i18n:test グリーンを維持してマージする。
3. supplement用語集（glossary.supplement.*.json）への追記は暫定として可。ただしタスク完了報告に追記エントリ一覧を含め、人間レビュー後に本体へ統合する前提とする。
4. エンジン識別子（metric生キー、surface ID、エラーコード）は非翻訳。小数点ピリオド固定（18章・27.3節）。
5. 新規パネル・チャートの用語にはToggletip（①階層）を付与する。チャートの読み方解説（②階層）はray fan・MTFで必須。
6. チャート実装はLOD規約（20章）に従う。点数の多いspot/散布はPlotly scattergl（WebGL）を使い、SVG+D3をチャートに使わない。

---

## タスクP2-0：U1〜U5残件の仕上げ

実装報告のRemaining Work 1〜2を先に閉じる。

### 作業

1. Playwrightを導入し、ToggletipのキーボードE2E（Tab→Enterで開く→Escで閉じる、Surface Table列ヘッダ＋metric名の代表各1箇所）を追加する。CIに組み込む（起動はエンジンモックまたは実エンジンのどちらでもよい。選択を報告）。
2. SVGエクスポートの読み戻し検証を追加する：ja/en各言語でエクスポートしたSVGをパースし、軸ラベル文字列が選択言語の用語集ラベルと一致することをアサートする（画像比較ではなくテキスト検証でよい）。

### 完了条件

- Playwright E2EとSVG読み戻しテストがCIでグリーン。28.5節のToggletip・エクスポート言語の2項目を「部分完了」から「完了」に更新した受け入れ表を報告する。

---

## タスクP2-1：解析条件編集UI（仕様13章）

### 作業

1. field編集（角度グリッド、追加・削除、field ID管理）、wavelength編集（プリセットF/d/C/e＋任意波長＋重み）、ray_sampling編集（samples_per_field、pupil_distribution、aiming mode）を実装する。
2. 編集は analysis_dirty に正しく連動させる（11章のdirty規約）。
3. decenter/tilt が構成に存在する場合の±field自動評価（エンジン側挙動）に備え、**応答metadataの実評価field一覧を表示**する（送信したfield setと実評価が異なり得るため）。

### 完了条件

- 各編集操作のdirty遷移テスト。
- 条件を変えてspot再実行し、結果が更新されるE2E 1本。

---

## タスクP2-2：解析ビュー群

### 作業

1. 以下のチャートを実装する：ray fan（Y/Z断面ペア表示）、distortion（像高 vs 歪曲率）、field curvature（M/S像面カーブ）、relative illumination、MTF（S/M別、周波数軸lp/mm）。spot diagramは既存実装をscattergl・LOD規約準拠に改修する。
2. 各チャートの軸ラベル・凡例は用語集参照（U5規約）。波長の色分け規約を実装する：F線=青系、d/e線=緑黄系、C線=赤系で固定し、fieldはパネル分割（色と重複させない）。この規約をリソース化して全チャートで共有する。
3. ray fanとMTFにはヘルプドロワー（②階層、glossaryのlong）への導線を付ける。
4. MTF応答の "diffraction_included": false をUI上に明示する（幾何MTFの楽観性の注記。用語集mtfエントリのshortにも整合）。

### 完了条件

- P003（アクロマート）で全チャートが表示され、ja/en切替が追従するスクリーンショット報告。
- 波長色規約のユニットテスト。
- 28.2節のP003受け入れ条件（色収差カーブ表示等）を満たすこと。

---

## タスクP2-3：評価像面UI（仕様14章。前提：エンジンA1完了）

### 作業

1. image_plane_policy編集UIを実装する：mode選択（fixed_sensor / paraxial_image / best_focus_rms / best_focus_mtf / custom_offset / sweep）、criteria編集（対象field/波長重み、MTF周波数）、apply_to選択（evaluation_plane / focus_group / report_only）。
2. 応答metadataの evaluation_plane ブロックを結果パネルに常時表示する（policy_mode、評価面位置、sensorとのoffset、solve_status）。solve_not_converged警告はエラーカタログ経由で表示する。
3. focus curve表示（sweep結果のX位置 vs metricチャート、best focus位置のマーカー）を実装する。
4. sensor write-back操作を実装する（14.3節の規約：solve結果→OpticalSystemDraft更新→system_dirty→validate/register。明示ボタン＋確認ダイアログ）。
5. Layout Viewの sensor / paraxial image / active evaluation plane の区別表示（Phase 1実装済み）を、policyの結果と連動させる。
6. afocal系プリセット（P006）選択時はpolicy編集UIをdisableする（27章・エンジン仕様21.5節）。

### 完了条件

- P002（単玉）でbest_focus_rmsを実行し、評価面がsensorからずれて表示され、write-backでsensor位置が更新されsystem_dirtyになるE2E。
- focus curveチャートの表示とja/en追従。
- P006でpolicy UIがdisableされるテスト。

---

## タスクP2-4：Snapshot保存と2条件比較（仕様22.4節。前提：エンジンA2完了）

### 作業

1. snapshot作成時のartifact埋め込みを実装する：必須データ（spot点群、MTF/focus curve等の曲線JSON、図PNG）をGET /v1/artifactsで取得しsnapshotへ埋め込む。大容量（PSF array等）は既定offのユーザートグル。
2. 取得失敗時のpartial snapshot（partial: true＋欠損一覧）と、Compare時の「データなし」フォールバック表示を実装する。
3. export形式：小容量は単一JSON、添付ありはzip（snapshot.json + artifacts/）。
4. 2条件比較ビューを実装する：2つのsnapshotを選び、条件差分（system_hash / configuration / analysis条件）の表示と、spot・MTF・RIの並置比較。**比較可能性ガード**を入れる：field・波長・評価面が一致しない比較項目には不一致警告を表示する。
5. snapshotは言語非依存（生キー保存、表示時ローカライズ。U5で実装済みの規約を維持）。

### 完了条件

- snapshot作成→エンジン再起動（またはartifact失効）→snapshotからの再表示が成立するE2E（揮発性への耐性の実証）。
- partial snapshotのフォールバック表示テスト。
- P003の絞り径2条件の比較スクリーンショット報告。

---

## タスクP2-5：Phase 2受け入れとカバレッジ確認

### 作業

1. UI仕様28章のPhase 2該当受け入れ条件を1つずつ検証し、結果表を作る。
2. i18n:coverage を実行し、エンジンA3で追加された全コード・本Phaseで追加した全metricに用語集エントリが揃っていることを確認する（A3で意図的に残したレッド状態をここで解消する）。
3. supplement用語集の全追記エントリ一覧を、人間レビュー用に別ファイルとして出力する。
4. bench観点：spot 2048点表示・チャート5種同時表示時のUI応答性（操作から描画までの体感遅延）を簡易計測して報告する。

### 完了条件

- 受け入れ結果表、カバレッジCIグリーン、supplementレビュー用一覧の提出。

---

## スコープ外（先取り禁止）

- Phase 3（group編集・slider操作・decenter/tilt操作UI）、Phase 4（afocal系ビュー）
- 最適化API関連のUI
- Raw YAML/JSON advanced editor
- 教育Explanation Panel（レッスン連動解説）
