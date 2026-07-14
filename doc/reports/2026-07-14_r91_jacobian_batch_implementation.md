# R91 Jacobian batch J2/J3 実装報告

## 結論

仕様25.7節のJ2 correctness-first Jacobian APIと、J3 request-local warm refinementを実装した。機能・精度・決定論の完了条件は満たした。性能はJ2比で改善する条件が多い一方、一部プリセットで回帰と大きな測定ばらつきがあり、状態は **Done with noted performance limitation** とする。J4 candidate軸batch kernelは指示どおり実装していない。

## 実装内容

- `POST /v1/optics/evaluate`で`jacobian.mode / variables / steps`を構造化検証する。
- `forward_diff`と`central_diff`、`forward_fallback`、`backward_fallback`、両側infeasible時の`failed`列を実装した。
- `VariableBinding` registryからbase値とstepを解決し、曲率、radius、thickness、conic、偶数次非球面係数、group shift、irisを摂動できる。
- responseへ`mode / variables / residuals / matrix_shape / matrix / steps_used / columns`を追加した。
- 1000要素以下はinline JSON、1000要素超の数値matrixは決定論的SHA-256 IDのNPY artifactとした。
- `ArtifactStore.put()`をlockと`os.replace()`によるatomic writeへ変更し、同一IDへの並行putを直接テストした。
- 基準点は`strategy=exact`、摂動点は同一requestの基準originだけをNewton初期値にして既定toleranceまで再収束する。
- 固定damping列`1, 1/2, 1/4, 1/8, 1/16`を使い、residual不能・特異・過大step・非収束はray単位でcold exactへfallbackする。
- warm originはrequest-local workspaceだけに保持し、R82の`_AIMING_AFFINE_CACHE`へ書き込まない。
- `/v1/meta.capabilities.jacobian_modes`へ実動作する`forward_diff`、`central_diff`を追加した。

## 非球面step floor

P009/P010の実値域は、P009 `A4=-2.4992e-6`、P010 `A4=-1e-4 / A6=5e-7 / A8=-5e-10`である。既存registryの次数floorを`A4=1e-12 / A6=1e-16 / A8=1e-20`とし、相対stepは非球面係数だけ`abs(A) x 1e-3`とした。実際のstepはそれぞれ`2.4992e-9 / 1e-7 / 5e-10 / 5e-13`となり、全て`base + h != base`を満たす。machine spacingを下回る指定は`np.nextafter()`差まで引き上げ、metadataへ記録する。

## 検証

- 機能コミット: `f8d47b3` (`feat(engine): add Jacobian warm refinement API (R91)`)
- 直接テスト: `tests/test_r91_jacobian.py`、`19 passed`
- エンジン全回帰: `182 passed, 1 skipped, 1 warning in 22.09s`
- UI CI: `npm run ci`成功、Playwright `39 passed (1.1m)`
- warm/exact oracle:
  - status、aiming success、pupil targetは一致
  - origin・sensor座標は`atol=2e-6 mm`以内
  - residualは`atol=1e-6 / rtol=1e-8`以内
  - Jacobianは`atol=1e-6 / rtol=1e-3`以内
- cache clear、9/25/81 samples、別iris/field履歴後も同一Jacobian responseがビット同一
- ケラレ境界とTIR境界でstatus変化をsoftな`ray_loss_ratio`列として評価
- forwardは概ね一次、centralは概ね二次の収束を直接テスト
- process再起動後の`GET /v1/meta`: `build_info.git_commit = f8d47b3`
- 実HTTP確認: `status=ok`、`jacobian.status=ok`、`central_diff`、`matrix_shape=2x1`、`scheme_used=central`
- UI応答: HTTP `200`

## ベンチマーク

正式履歴:

- `bench_results/20260714_225810_r91_jacobian.json`
- `bench_results/20260714_230137_r91_jacobian.json`

R83と同じ2 operands、1 field、1 wavelength、9 rays、full exact aimingで、P002/P007/P012/P011を各10回測定した。J3/J2 speedupは次の範囲だった。

| preset | variables | run 1 | run 2 |
|---|---:|---:|---:|
| P002 | 1 | `1.192x` | `1.160x` |
| P007 | 1 | `1.226x` | `0.471x` |
| P012 | 1 | `0.500x` | `0.661x` |
| P011 | 1 | `1.187x` | `3.390x` |
| P011 | 5 | `2.949x` | `2.691x` |
| P011 | 10 | `1.787x` | `1.302x` |
| P011 | 20 | `1.562x` | `1.549x` |

P011 5変数のrun 2だけが`J3 <= 1.25 x cold`を満たし、他は未達だった。J3はcandidate軸traceを共有しないため、変数数に応じたtraceコスト自体は残る。P007/P012ではwarm line-searchまたはfallback負荷が勝つ測定があり、P011では実行順による大きな時間変動も見られた。J4投資判断は本タスクでは行わず、profilingとwarm適用判定を`issues_backlog.md`へ登録した。

## 制限

- J4 `_trace_raw_candidates()`は未実装。
- 両側hard infeasibleのfailed列は、NaNや偽のゼロを返さずinline JSONの`null`と明示的なcolumn diagnosticsで表す。成功数値matrixの1000要素超だけをNPY artifact化する。
- J3の性能改善はプリセット・変数・実行負荷に依存し、現時点で`1.25 x cold`を一般保証しない。
