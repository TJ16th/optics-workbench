# 光学エンジン API追補 作業指示書（Codex向け・タスクA0〜A3）

## 背景と目的

エンジンの実装状況は「仕様v2ベースのPhase 1-8＋v2.3小改訂（meta enumerations・構造化エラー）」である。**仕様v2.1で定義したAPIのうち、UI Phase 2が依存する2機能が未実装**のため、UI Phase 2着手前に本追補を完了させる。

- image_plane_policy（エンジン仕様v2.1→v2.3の21.5節）：UI Phase 2の best_focus_rms / best_focus_mtf / focus curve が依存
- GET /v1/artifacts（同26.8節）：UI Phase 2の snapshot保存・2条件比較が依存

仕様の根拠は `doc/optical_engine_spec_v2_3.md` の21.5節・26.8節・26.9節。v2.2のオペランドAPI・solves等は本追補の**対象外**（別途の最適化指示書タスク8〜13で扱う。先取りしない）。

## 進め方・共通制約

- タスクは番号順に1タスクずつ。完了報告後に停止する。
- 既存テスト（51 passed＋Golden）を常にグリーンに維持する。
- 新規のエラー・警告はすべてv2.3の構造化形式（severity / code / params / message_en）で返し、codeを /v1/meta の enumerations に追加する（26.10節の規約5）。
- ベンチ結果に影響する変更をした場合は bench_results/ へ追記する。

---

## タスクA0：リポジトリのGit化（1回限りの前提作業）

実装報告で対象ワークスペースがGitリポジトリでないことが判明した。以後の「タスク独立コミット」規約を成立させるため、最初に整備する。

### 作業

1. `git init` し、`.gitignore` を整備する（node_modules、dist、__pycache__、.venv、bench_results/の生成HTML、キャプチャPNG等の生成物を除外。bench_results/*.json は**追跡対象**とする）。
2. 現状全体を「baseline: engine v2.3 + UI U1-U5」として初回コミットする。
3. 以後のタスクはタスク単位のコミットとし、メッセージにタスク番号を含める（従来規約の再開）。

### 完了条件

- `git log` に初回コミットが存在し、`git status` がクリーンであること。

---

## タスクA1：image_plane_policy と best-focus拡張（仕様21.5節）

### 作業

1. 像面依存の解析エンドポイント（spot / ray-fan / psf / mtf / white-psf / white-mtf / relative-illumination / chromatic-aberration）に `image_plane_policy` リクエストパラメータを実装する。
2. modeを実装する：fixed_sensor（既定）/ paraxial_image / best_focus_rms / best_focus_mtf / best_focus_merit / custom_offset / sweep。
3. 探索仕様に従う：初期値=近軸像面、黄金分割または放物線補間、range_mm既定±5.0、tolerance_mm既定0.001。**探索の各評価点では光線追跡を再実行せず、トレース済み光線と評価面の交点計算のみ掃引する**（性能規約）。
4. apply_to を実装する：evaluation_plane（既定）/ focus_group（solved shiftをruntime configとして適用）/ report_only。sensor_surfaceは実装しない（クライアント責務）。
5. 応答metadataに evaluation_plane ブロック（policy_mode / evaluation_plane_x_mm / sensor_x_mm / offset_from_sensor_mm / solved_focus_group_shift_mm / solve_status）を必ず含める。
6. sweepはfocus curve（X位置の配列とmetric値の配列）を返す。
7. afocal系（system_type: afocal）でpolicyが指定された場合、構造化エラー（code: image_plane_policy_not_applicable 等）を返す。
8. /v1/solve/best-focus を同一実装の単独エンドポイントとして拡張する。
9. 探索不収束は solve_not_converged（v2.3形式のwarning）とし、range端の値を返す。

### 完了条件

- Goldenダブレットで、best_focus_rms の解が近軸像面位置の±0.5 mm以内にあり、fixed_sensorとbest_focusでspot RMSが整合的に変化するテスト。
- sweepが単調でないfocus curve（最小値を持つ曲線）を返し、その最小位置がbest_focus_rmsの解と一致（tolerance内）するテスト。
- custom_offset / paraxial_image / report_only / focus_group の各モードのテスト。
- afocal系でのvalidation errorテスト。
- **探索1回の解析が、fixed_sensor解析の3倍以内の時間で完了する**こと（光線追跡を評価点ごとに再実行していないことの間接確認）をベンチで報告。

---

## タスクA2：Artifact取得と生存期間（仕様26.8節）

### 作業

1. artifactストアを実装する：解析応答内の大容量データ（PSF配列、spot点群、focus curve、図）を `artifact://{category}/{id}` URIで参照し、実体は一時ディレクトリに置く。
2. `GET /v1/artifacts/{category}/{id}` を実装する。Content-Typeはartifact種別に応じる（.npy=application/octet-stream、parquet、image/png、application/json）。
3. TTLを実装する（既定30分、起動オプションで変更可）。応答metadataに expires_at を含める。期限切れのGC（アクセス時判定＋定期削除のどちらでもよい）を実装する。
4. 存在しない・期限切れは404＋構造化エラー（code: artifact_not_found / artifact_expired）で返す。
5. 既存の解析応答で「インライン返却していた大配列」があれば、閾値（目安：要素数10,000超）を超えるものをartifact参照へ移行する。閾値以下はインラインのまま維持してよい（応答にどちらかを明示）。

### 完了条件

- 解析実行→URI取得→GET成功→TTL経過（テストでは短TTL設定）→artifact_expired、の一連のライフサイクルテスト。
- PNG / npy / json 各Content-Typeの取得テスト。
- 期限切れエラーがv2.3構造化形式であるテスト。

---

## タスクA3：/v1/meta capabilities・enumerationsの誠実性更新

### 作業

1. capabilities に image_plane_policy_modes（A1で実際に動作するmodeのみ列挙）と artifacts（true / ttl_seconds）を追加する。
2. **capabilitiesは実装済み機能のみを列挙する**ことをテストで固定する：capabilities に列挙された全modeについて、実際にリクエストが成功する自動テスト（列挙駆動のパラメトリックテスト）。
3. A1・A2で追加した全コード（solve_not_converged / image_plane_policy_not_applicable / artifact_not_found / artifact_expired 等）を enumerations.error_codes / warning_codes に追加する。
4. UI側のカバレッジCI（i18n:coverage）を実行し、新コードに対する用語集エントリ不足が**検出されること**を確認して報告する（用語集への追記自体はUI Phase 2側のDoDで行う。ここでは検出の確認まで）。

### 完了条件

- 列挙駆動のcapabilitiesテストがグリーン。
- UI側 i18n:coverage が新コード不足で失敗することの確認報告（レッド確認。修正はUI側タスク）。

---

## 最終確認

- Pythonテスト全件グリーン（件数を報告）。
- /v1/meta の応答全文を報告に添付する（capabilities・enumerationsが実装と一致していることの人間レビュー用）。
- UI Phase 2への引き継ぎ事項（追加したエラーコード一覧、artifact URIを返すようになった応答フィールド一覧）を表で報告する。
