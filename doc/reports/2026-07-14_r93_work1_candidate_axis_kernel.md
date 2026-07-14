# R93 作業1 candidate軸trace kernel 中間実施記録

## 状態

- R93全体: **Partial**
- 作業1: 完了
- 作業2（J3統合・ベンチマーク）: 未着手
- 作業3（J5運用固め・仕様更新）: 未着手
- R94: 未着手

本書はR93全体の完了報告ではない。`codex_r93_jacobian_candidate_axis_kernel.md` の指示に従い、作業1の完了時点で区切った中間実施記録である。このため作業指示書は `doc/work_orders/active/` に保持する。

## 実装内容

- `_trace_raw_candidates()` を追加し、`origin` / `direction` を `[candidate, ray, 3]`、`wavelength` / `status` を `[candidate, ray]`、runtime surface centerを `[candidate, surface, 3]` として保持するcandidate軸カーネルを実装した。
- alive状態はcandidate×rayのdense maskで管理し、candidateごとの元ray index順を維持した。
- `candidate_chunk_size` による固定candidate順のchunk分割を追加した。
- surface topology、surface ID順、material ID順、surfaceのmaterial参照順が一致しない場合は、既存 `_trace_raw()` の独立評価へ自動fallbackする。
- 現行 `_trace_raw()` および `optics_engine/reference/` のLevel 0実装は変更していない。
- `CandidateTraceResult.candidate()` により各candidateを既存 `TraceResult` と同じ形で比較可能にした。

## 根拠

- 機能コミット: `5fd9f815c40f44e9cc6551252aa0aad445d5a34a`
- Goldenテスト: `tests/golden/test_r93_candidate_trace_kernel.py`
- 既存Goldenテスト: `tests/golden/test_trace_kernel_equivalence.py`

検証結果:

```text
python -m pytest -q tests/golden/test_r93_candidate_trace_kernel.py tests/golden/test_trace_kernel_equivalence.py
6 passed in 1.00s

python -m pytest -q
188 passed, 1 skipped, 1 warning in 15.35s
```

Goldenテストでは、同一candidate群についてcandidate軸カーネル、独立 `_trace_raw()`、Level 0のstatus・方向・sensor座標・pathが一致することを確認した。またchunk size 1と3の結果がbit-identicalであること、およびmaterial ID順不一致時にfallbackすることを確認した。

## 実行環境

機能コミット後にAPI・UI開発サーバーを再起動した。

- `HEAD`: `5fd9f815c40f44e9cc6551252aa0aad445d5a34a`
- `GET /v1/meta` の `build_info.git_commit`: `5fd9f81`
- `build_info.git_dirty`: `true`（未追跡のactive指示書と本中間記録を含むため）
- UI `http://127.0.0.1:5173/`: HTTP 200

## 次の区切り

次回はR93作業2としてJ3からcandidate軸カーネルを利用する経路を実装し、R83/R91条件の複数回ベンチマークを行う。作業2の完了報告前に作業3またはR94へ進まない。
