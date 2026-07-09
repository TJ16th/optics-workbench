# UI Phase 3 follow-up2: aperture runtime configuration

## 対象

`doc/work_orders/active/codex_ui_phase3_followup2.md` の作業2に対応した。

## 修正内容

- P003の `STOP` を `semi_diameter_mm: { variable: "iris_radius_mm", default: 10 }` 形式に変更した。
- UIの `RuntimeConfiguration` に `variables` を追加し、絞りスライダーはsystemを変更せず `configuration.variables.iris_radius_mm` を送るようにした。
- Layout Viewのaperture_stop表示もruntime iris値を参照するようにした。
- エンジンはvariable形式の数値をロード時にdefaultへ正規化し、trace時は `configuration.variables.iris_radius_mm` を瞳サンプリングと開口判定へ適用するようにした。
- E2Eは、P003 system登録が1回だけで、その後のdrag/commitではregisterが増えないことを確認する形に更新した。

## ベンチマーク

結果JSON:

- `bench_results/2026-07-09_ui_phase3_followup2_aperture_runtime.json`

条件:

- local FastAPI: `http://127.0.0.1:8000`
- P003 Achromat Doublet 100mm
- fields: 3
- wavelengths: 3
- repeats: 20
- drag: `samples_per_field=5`, `ray_aiming.mode=paraxial`
- commit: `samples_per_field=9`, `ray_aiming.mode=paraxial`
- system登録は最初の1回のみ。以後は `configuration.variables.iris_radius_mm=5`

| case | before median HTTP | after median HTTP | delta | improvement |
|---|---:|---:|---:|---:|
| drag | 30.025 ms | 4.321 ms | -25.704 ms | 85.6% faster |
| commit | 31.474 ms | 4.759 ms | -26.715 ms | 84.9% faster |

Effective UI median（70ms debounce込み）:

| case | before | after |
|---|---:|---:|
| drag | 100.025 ms | 74.321 ms |
| commit | 101.474 ms | 74.759 ms |

## 検証

- `python -m pytest tests/test_engine_v2_1.py`
  - 成功。16 passed。
- `python -m pytest`
  - 初回は速度比テストが一度だけノイズで失敗。該当テスト単体の再実行後、全体再実行で成功。最終結果は58 passed / 1 warning。
- `npm.cmd run ui:build`
  - 成功。Viteの既存警告のみ。
- `npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts -g "aperture slider"`
  - 成功。1 passed。
- `npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - 成功。11 passed。

## 未対応・注意

- エンジンのロード時にはvariable形式の数値をdefaultへ正規化している。現時点では、変数メタデータの永続的なschema保持ではなく、UIから送る `configuration.variables.iris_radius_mm` をruntime評価へ適用するMVP対応。
- `source_commit` はベンチ実行時点の作業ツリーを示す `worktree-after-ebe116e` とした。
