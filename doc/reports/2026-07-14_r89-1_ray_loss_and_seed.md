# R89 作業1 ray_loss_ratioとsampling seed 実装報告

## 結果

作業1は完了した。機能実装の根拠コミットは`7bafc84`（`feat(engine): add ray loss operands and seeded sampling (R89-1)`）。

## 実装内容

- 各field×波長の`ray_loss_ratio`をevaluateの疑似operandへ自動追加した。
- `residual = ray_loss_ratio / ray_loss_tolerance`、既定toleranceは`0.1`とした。
- 既定対象は`total_internal_reflection`、`missed_surface`（内部status `missed`）、`aiming_failed`、`numerical_error`。既定では意図的な`blocked`を除外し、`ray_loss_statuses`で選択可能にした。
- `random`・`sobol`は`seed`必須とし、同じseedでbit-identical、異なるseedで異なる瞳座標となるようにした。
- ray lossの残差二乗を既存merit scoreへ連続penaltyとして加算した。

## 検証

- `tests/test_r89_work1_ray_loss_seed.py`とR82/R87回帰: `25 passed, 1 warning in 2.16s`
- 全エンジンテスト: `147 passed, 1 skipped, 1 warning in 14.68s`
- 初回全体実行で20 ms TTLのartifactテストが一度だけ期限切れになったが、単独再実行`1 passed`、全体再実行`147 passed`で非再現を確認した。production code変更は行っていない。
- `HEAD=7bafc84`、`GET /v1/meta build_info.git_commit=7bafc84`、UI HTTP 200を確認済み。

## 次作業との境界

本作業ではseed契約を先に固定した。`sobol`を含む各分布の専用配置と積分weightはR89作業2で実装する。
