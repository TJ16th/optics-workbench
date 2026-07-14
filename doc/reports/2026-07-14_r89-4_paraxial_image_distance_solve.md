# R89 作業4 近軸像距離solve 実装報告

## 結果

作業4は完了した。機能実装の根拠コミットは`c6e447c`（`feat(engine): add paraxial image distance solve (R89-4)`）。

## 実装内容

- `POST /v1/solve/paraxial-image-distance`を追加した。
- sensor直前の最終空気間隔を、基準configuration・主波長の近軸像位置とsensor位置が一致する値へ解決する。
- evaluateの`configuration.solves=[{"type":"paraxial_image_distance",...}]`を評価前に適用する。
- evaluate応答の`configuration_resolved`へ解決済み変数と`resolved_solves`詳細を返す。
- 未知surface、最終空気間隔でないsurface、非空気層、負gap解を構造化エラーとした。
- 既存best-focus / image_plane_policyとは共有せず、等式制約solveとして独立した共有関数をendpointとevaluateから呼ぶ構成にした。

## API実測・検証

- f=50 mm薄レンズ、初期最終gap 40 mmを50 mmへ解決し、sensor位置と近軸像位置が`1e-12 mm`以内で一致した。
- evaluate solve後のspotが未solveより改善し、`configuration_resolved`を返すことを確認した。
- 対象回帰: `35 passed, 1 skipped, 1 warning in 1.70s`
- 全エンジンテスト: `157 passed, 1 skipped, 1 warning in 15.86s`
- `HEAD=c6e447c`、`GET /v1/meta build_info.git_commit=c6e447c`、UI HTTP 200を確認済み。
