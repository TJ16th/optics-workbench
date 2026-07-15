# R123 Alignコマンド実装 完了報告

## 結果

R119で承認された設計に基づき、Analysisの`Image Plane Policy`へセンサー整合のプレビューと適用を追加した。状態は **Done with noted limitation** とする。

- 機能コミット: `77d211d` (`feat(ui): add sensor alignment preview (R123)`)
- 根拠テスト: `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
- 実装着手時の見積り: UI/APIクライアント、i18n、E2E、実画面確認を含め約2時間

## 実装内容

- `Align`は適用前に`/v1/solve/paraxial-image-distance`と`/v1/analysis/paraxial`を順に呼び、現在値、solve値、差分、solve statusを表示する。
- プレビューをFocus、Field fit、Real imageの3区分で表示し、焦点差`0.001 mm`、field fit差がセンサー寸法の`0.5%`という判定基準を明示した。
- `Preserve field angles`はセンサー直前gapのみを更新する。
- `Fit fields to sensor`はY/Z方向を別々に逆算し、中間fieldの最大fieldに対する既存比率を維持して更新する。
- Apply後はvalidate/registerを実行し、既存解析結果を消さず`Stale results`として保持する。
- `afocal`、sensorなし、負gap、非収束は適用不可とし、エンジンの構造化issueを表示する。
- 表示文言をja/enのi18nリソースへ追加した。

## 検証

- `npm run ci`: `63 passed (1.7m)`、`i18n:check ok (337 keys)`、build/coverage/unit/SVG/chartすべて成功。
- `npm run ui:build:pseudo`: 成功。
- R123 E2Eで、プレビュー非破壊、Preserveでgapのみ更新、FitでY/Z field更新と比率維持、`afocal`で無効化を直接確認した。
- 最初のフルCIでは既存preset ComboBoxテストが1回だけ30秒でタイムアウトしたが、単体再実行とフルCI再実行では再現せず、最終結果は全件グリーンだった。

機能コミット直後にAPI/UIを再起動し、`GET /v1/meta`の`build_info.git_commit = 77d211d`と`git rev-parse HEAD = 77d211d5a2a7d9ed0421b7a64328af9f5fe4e3de`の一致を確認した。`git_dirty = true`は未追跡のactive指示書と本報告書・スクリーンショットによる。

## 画面確認

- [Analysis全体とAlignプレビュー](screenshots/2026-07-15_r123_align_command_implementation_1.png)
- [Fit fields to sensor選択時のAlignパネル](screenshots/2026-07-15_r123_align_command_implementation_2.png)

## 制限

- 本タスクは既存の近軸solve/paraxial endpointを利用するUI実装であり、新しいエンジンendpointは追加していない。
- field fitは近軸像高に基づく整合であり、実光線像高の最適化ではない。
- Apply後の解析は自動再実行せず、既存結果をstaleとして保持する。
