# P0タスク1 Golden Test 完了報告

## 概要

`doc/work_orders/active/codex_p0_task1_kickoff.md` に従い、P0-7性能改善指示書のタスク1（Golden Test）だけを実施した。
タスク2以降には進んでいない。

## 実装内容

- `tests/golden/` を新設した。
- `tests/golden/test_golden_optical_systems.py` を追加した。
  - BK7/F2 100mm級アクロマートダブレットの物理サニティテストを追加。
  - エンジン仕様v2.3 6.3節のカセグレン例の物理サニティテストを追加。
  - 両系の凍結回帰テストを追加。
- `tests/golden/golden_values.json` を追加し、現行エンジンの凍結値を保存した。

## Golden対象

### アクロマートダブレット

BK7/F2の100mm級アクロマートとして、以下を満たす設計を固定した。

- D線EFL: `99.97412328039455 mm`
- D線BFL: `93.33699484632511 mm`
- F線像位置: `108.8858577252041 mm`
- C線像位置: `108.88546515623807 mm`
- F/C像位置差: 約 `0.000392568966 mm`
- D線EFLに対するF/C像位置差: 約 `3.93e-6`

P0-7本体の記載にある「EFL 95-105mm」「F/C焦点差がD線EFLの0.1%未満」という物理サニティ条件を満たす。

### カセグレン

仕様v2.3 6.3節の検証済み値を使用した。

- M1: `R=-2000 mm`, `thickness_after=-650 mm`, `semiD=100 mm`
- M2: `R=-1050 mm`, `thickness_after=1050 mm`, `semiD=40 mm`
- EFL: `3000 mm`
- BFL: `1050 mm`
- 近軸像位置: `400 mm`
- M2位置でのマージナル光線高さ: `35 mm`（M2 semiD `40 mm` 内）

## 確認結果

- `python -m pytest tests/golden/test_golden_optical_systems.py -q`: `4 passed`
- `python -m pytest -q`: `67 passed, 1 skipped, 1 warning`

補足:

- 検証のため、このローカルランタイムに `pytest`、`fastapi`、`uvicorn`、`httpx` をインストールした。
- warningは既存APIテスト由来の `StarletteDeprecationWarning` であり、今回追加したGolden Testの失敗ではない。

## 作業範囲

本タスクはテスト・fixture・報告書のみの変更であり、エンジンAPI・UIプロセスの再起動確認は対象外。
`doc/work_orders/active/codex_p0-7_performance_work_order.md` はタスク2以降が残るため、activeに残している。
