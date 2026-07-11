# P0-7 タスク5 着手指示

## 対象

`doc/work_orders/active/codex_p0-7_performance_work_order.md`のタスク5（profiling metadata）に着手する。

## 前提

- タスク0〜4は完了済み。タスク2〜4の一連の改善で、full aimingの体感速度は大きく改善した（166倍→タスク4完了時点で各ケース5〜6倍の追加改善済み）。
- タスク4完了報告で、`ray_aiming_strategy`・`aiming_iterations_mean`・`aiming_cache_hits`・`aiming_cache_misses`・`affine_refined_count`・`affine_seed_count`が既に`TraceResult.metadata`に追加されている。本タスクはこれをAPI応答レベルのprofiling機能として体系化する位置づけ。

## 実施内容

指示書のタスク5に定義された内容をそのまま実施する：

- リクエストオプション`profiling: true`で、応答metadataに以下を含める：validation / compile（またはcache hit）/ aiming / trace / analysis後処理、それぞれのms、cache hit/miss、総光線数、aiming反復回数統計、aiming_failed件数。タスク4で追加済みのaiming関連フィールドをこの体系に統合する。
- spec_like_benchmarkをHTTP API経由でも実行できるモードを追加し、ライブラリ直呼びとのend-to-end差分（シリアライズ・validationコスト）を1ケースで計測して報告する。

## 作業規律の確認

- **タスク5完了後、完了報告を出してこのセッションで停止する。タスク6以降には進まない。**
- 既存の`TraceResult.metadata`のフィールド名を変更する場合、後方互換（既存フィールド名を残すか、変更理由を明記する）に注意すること。

## 完了条件

- 全テストグリーン。profilingフィールドのスキーマテストを追加。
- HTTP経由 vs 直呼びの差分レポート（1ケースでよい）。
