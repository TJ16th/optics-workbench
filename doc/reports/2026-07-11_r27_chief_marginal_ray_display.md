# R27 Layout View chief/marginal ray display 完了報告

## 実施内容

- `trace_forward(..., options={"include_layout_baseline_rays": true, "store_path": true})` で、Layout View用の `metadata.layout_baseline_rays` を返す実装を追加した。
- baseline ray は各field/wavelengthごとに `chief` 1本、`marginal_lower` 1本、`marginal_upper` 1本を生成し、既存のexact ray aimingでSTOP中心/上下端を狙う。
- UIのLayout Viewを2レイヤー化した。
  - baseline layer: chief/marginal rayを常時描画。
  - density layer: 従来のsampling由来 lower/center/upper rayを描画。
- density layerのオン/オフ切り替えUIを追加した。既定はオン。
- baseline chiefは太い実線、baseline marginalは破線、density rayは薄めの線として区別した。
- E2Eモックレスポンスにも `layout_baseline_rays` を追加し、baseline layerとdensity layerを `data-ray-layer` で検証できるようにした。

## 仕様書・指示書との差分

- R27の主目的である「`samples_per_field` に依存しない chief/marginal ray 表示」は実装済み。
- density確認層のトグルは実装済み。
- P002/P003相当の `samples_per_field = 5/9/15/25` 安定性は、エンジン単体テストとE2Eで固定した。
- baseline rayは `store_path` かつ `include_layout_baseline_rays` が明示された場合のみ返す。通常traceレスポンスのサイズ増加を避けるため。
- 既存のsampling ray代表選択は残しており、R26で確認した挙動はdensity layerとして継続する。

## 検証結果

- `python -m pytest -q -p no:cacheprovider`
  - `73 passed, 1 skipped, 1 warning`
- `npm.cmd run ci`
  - `ui:build` ok
  - `i18n:check` ok (`176 keys`)
  - `i18n:coverage` ok
  - `i18n:test` ok
  - `svg:export:test` ok
  - `chart:test` ok
  - `ui:e2e` ok (`21 passed`)
- 追加確認:
  - `tests/test_engine_v2_1.py::test_layout_baseline_chief_and_marginal_rays_are_sample_count_independent`
  - `analysis-conditions.spec.ts` の `layout baseline chief and marginal rays are stable across ray counts`

## 注意点

- `codex_p0_task6_kickoff.md` は作業対象外の未追跡active指示書として残した。
- UI/エンジンプロセスの `/v1/meta build_info.git_commit` 確認は、R27コミット作成後に最終報告で実施結果を示す。
