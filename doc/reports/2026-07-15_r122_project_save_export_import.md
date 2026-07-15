# R122 Project保存・Import / Export 実装報告

- 着手前見積もり: 中規模（UI状態スキーマ、3種round-trip、互換確認、E2Eを含め4〜6時間）
- 状態: **Done with noted limitation**
- 機能コミット: `ffb4293` (`feat(ui): add project file round trips (R122)`)
- 対象仕様: `doc/ui_spec.md` 22章・23章
- エンジン/API変更: なし

## 実装結果

### 対応した入出力

| 対象 | Export | Import | 復元・検証 |
|---|---|---|---|
| OpticalSystemDraft | JSON / YAML | JSON / YAML | `validate`→`register`を実行し、エンジンissueを構造化表示 |
| Project | JSON | JSON | system、configuration、analysis、results、snapshots、compare選択を復元 |
| Snapshot | JSON | JSON | R121の`configuration`とR122の`versions`を保持。旧形式も読込可能 |

Project JSONには仕様22.1の`optical_systems`、`configurations`、`analysis_conditions`、`results`、`snapshots`、`compare_sets`、`versions`をすべて含める。現行UIが単一光学系を扱うため、前5項目は単一要素または現在保持中のSnapshot配列として保存する。

`versions`には`engine_version`、`api_schema_version`、`ui_version`、`preset_version`、`material_catalog_version`、`result_schema_version`、`design_system_version`、`project_schema_version`を記録した。Project／Snapshot import時は`GET /v1/meta`由来の現在値と比較し、差分を`project_version_mismatch` warningとして表示する。差分があっても読込は拒否しない。

## 仕様22・23章の精査

| 仕様項目 | R122完了時点 | 根拠・制限 |
|---|---|---|
| 22.1 Project構造 | 実装済み | 仕様の7配列／objectをJSONへ保存。複数光学系の同時編集は未対応 |
| 22.2 Optical system JSON/YAML | 実装済み | `js-yaml`でYAML read/write。import後にvalidate/register |
| 22.2 Project JSON | 実装済み | 現在のWorkbench状態をround-trip |
| 22.2 Result table CSV/JSON | 未実装 | Analysis上の表表示はあるが専用ファイルexportなし |
| 22.2 Figure PNG/SVG | 部分実装 | Layout SVG/PNG、Spot SVGは既存実装。全22.3対象・Spot PNGは未完 |
| 22.2 Raw request/response JSON | 部分実装 | Debug表示は既存。ファイルdownloadは未実装 |
| 22.2 Snapshot JSON | 実装済み | configuration、versions、partial情報を保持 |
| 22.3 図表export | 部分実装 | Optical Layout／Spotの一部のみ。MTF等の全図種は未実装 |
| 22.4 summary／JSON artifact埋込 | 実装済み | Snapshot保存時にartifact URIを取得し`artifacts`へ格納 |
| 22.4 図PNG／大容量添付 | 未実装 | SnapshotへPNG、npy、parquetを添付する処理なし |
| 22.4 partial snapshot | 実装済み | `partial`、`missing_artifacts`、summary fallbackを保持 |
| 22.4 Snapshot／Project zip | 未実装 | 既存backlog Issue #1へProject zipとpartial manifest案を追記 |
| 23.1 version記録 | 実装済み | 仕様記載の8項目をProject/Snapshotへ格納 |
| 23.2 Snapshot version | 実装済み | 新規Snapshotと単体exportに`versions`を付与 |
| 23.3 読込時差分表示 | 実装済み | Project/Snapshotでwarningとsaved/currentを表示 |
| 23.3 起動時major確認 | 既存実装 | `api_schema_version` major不一致で解析を禁止 |
| 23.3 起動時minor警告 | 未実装 | R122のファイル互換確認対象外として変更なし |
| 23.3 capabilities disable | 部分実装 | 既存の機能別制御のみ。全capabilityの一律UI制御ではない |

## 構造化エラー

- JSON/YAML構文不正、必須Project配列欠損、OpticalSystem必須項目欠損は`optics_value_error`と`params.input`／`params.expected`を表示する。
- System importのvalidateが`error`を返した場合は、エンジンの`issues`を変換せず表示し、register／状態置換を行わない。
- version差分は`project_version_mismatch`として`version_key`、`saved`、`current`をparamsへ含める。

## テスト結果

- 対象E2E: `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - `R122 round-trips optical system, project, and versioned snapshot files`
  - `R122 reports structured issues for invalid project files`
- 対象E2E単独: `2 passed (5.5s)`（最終拡張前の再実行では`2 passed (5.5s)`相当、YAML／Snapshot追加後も全CIで通過）
- `npm run ci`: `61 passed (1.7m)`、`i18n:check ok (319 keys)`、build／coverage／unit／SVG／chart test成功
- `npm run ui:build:pseudo`: 成功
- 実ブラウザ: System JSON export、System import→validate/register、Project import時のversion warningを確認

## 稼働確認

機能コミット`ffb4293`の直後にAPI／UIを再起動し、以下を確認した。

- `GET /v1/meta`: `build_info.git_commit = ffb4293`
- `git rev-parse --short HEAD`: `ffb4293`
- UI `http://127.0.0.1:5173/`: HTTP 200
- listener: API `127.0.0.1:8000`、UI `127.0.0.1:5173`各1プロセス
- `build_info.git_dirty = true`は本報告書、スクリーンショット、active指示書等の未コミット文書による

## スクリーンショット

1. [System JSON export操作](screenshots/2026-07-15_r122_project_save_export_import_1.png)
2. [System import後のvalidate/register済み復元](screenshots/2026-07-15_r122_project_save_export_import_2.png)
3. [Project import時のversion不一致warning](screenshots/2026-07-15_r122_project_save_export_import_3.png)

## 未対応範囲

- Snapshot／Project zipとバイナリartifact添付
- 複数光学系の同時保持・切替
- Result table CSV/JSON専用export
- Raw request／responseのファイルdownload
- 22.3に列挙された全チャートのPNG/SVG export
- 起動時の`api_schema_version` minor差分warningの網羅

zipは単一JSON MVPへ混在させると、ブラウザ上の大容量メモリ管理、manifest、import readbackまで一度に広がるため分離した。`doc/reports/issues_backlog.md`の「Snapshot zip exportを実装する [issue: #1]」へ、Project zip、`partial: true`、`missing_artifacts`、失敗URIを保持する設計条件を追記済みである。
