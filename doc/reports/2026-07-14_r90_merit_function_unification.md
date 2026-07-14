# R90 Merit Function統一 完了報告

## 結論

エンジン仕様25.4節に従い、`merit.score`を全経路で`sum(residual^2) + ray_loss_penalty + continuous_constraint_penalty + hard_penalty`から導出する形へ統一した。旧線形weighted scoreは`legacy_merit`へ隔離し、API schema `2.5.0`の1リリース互換フィールドとして廃止予定metadataを返す。

## 実装内容

- `fast_design_score`と`spot_only`をtarget / tolerance / weight / one_sidedを持つoperand templateへ変更した。
- preset、明示operands、従来のmetrics指定を、共通のoperand評価と`_derive_merit()`へ集約した。
- `one_sided: lower | upper`の残差を実装した。
- ray loss、連続constraint、hard infeasibleを同じMerit導出へ接続した。
- 旧`_compute_merit()`相当の線形値を`legacy_merit`へ移し、`metadata.deprecations`にreplacementと削除予定schemaを含めた。
- evaluateとevaluate-batchの両方を列挙駆動テストで検証した。
- API/result schemaを`2.5.0`へ更新し、READMEへ互換性注記を追加した。
- `apps/workbench-ui/src`を横断検索し、`/v1/optics/evaluate`および`/v1/optics/evaluate-batch`呼び出しが存在しないことを再確認した。

## 根拠

- 機能コミット: `b0644b9` (`feat(engine): unify merit function output (R90)`)
- 直接テスト: `tests/test_r90_merit_unification.py`
- エンジン全回帰: `163 passed, 1 skipped, 1 warning in 16.11s`
- UI CI: `npm run ci`成功、Playwright `39 passed (55.7s)`
- 再起動後の`GET /v1/meta`: `build_info.git_commit = b0644b9`
- 同時点のUI応答: HTTP `200`

## 互換性

`legacy_merit`は`definition = legacy_linear_weighted_score`を返す。`metadata.deprecations`は`merit`への移行と`2.6.0`での削除予定を明示する。Workbench UIはevaluate系endpointに依存していないため、本変更による現行UIの呼び出し契約への影響はない。
