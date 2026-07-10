# P0-7 タスク2 着手指示

## 対象

`doc/work_orders/active/codex_p0-7_performance_work_order.md`のタスク2（aiming残差計算の軽量化）に着手する。

## 前提

- タスク0（計測基盤）・タスク1（Golden Test）は完了済み。
- タスク1で追加した`tests/golden/test_golden_optical_systems.py`・`golden_values.json`が、本タスクの回帰確認に使える。
- タスク0の実測で、`full` ray aimingが約10ms/ray（`paraxial`/`off`の約166倍）と判明している。指示書の記載通り、現在の`full` aimingは瞳サンプルごとにNewton反復と`paths`を使った途中トレースを行っており、これが重さの主因と推定されている。

## 実施内容

指示書のタスク2に定義された内容をそのまま実施する：

- stop面到達点だけを返す専用関数（`paths`全体を構築しない軽量トレース）を実装する。
- aimingの残差計算をこの専用関数に置き換える。
- タスク0のベンチ（full aiming 3条件比較）を再実行し、before/afterを報告する。

## 作業規律の確認

- **タスク2完了後、完了報告を出してこのセッションで停止する。タスク3以降には進まない。** 次のタスクは人間が明示的に発注する。
- 完了報告前に、Golden Test（`tests/golden/`）と既存テスト全体を再実行し、数値が凍結値と一致することを確認する（trace結果が変わっていないことの確認。今回は経路構築を省略するだけで、屈折計算自体は変えないはずなので、Golden Testの値は変化しないことが期待値）。

## 完了条件

指示書のタスク2に定義された完了条件（全テスト＋Goldenグリーン、full aimingベンチが改善、目安：2倍以上）を満たすこと。改善幅とper-ray costの内訳変化を報告に含める。
