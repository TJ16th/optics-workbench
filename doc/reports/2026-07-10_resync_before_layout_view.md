# Layout View着手前のプロセス再同期

日付: 2026-07-10

## 対象

`doc/work_orders/active/codex_resync_before_layout_view.md` に基づき、Layout View描画品質改善へ入る前に、ローカルのエンジンAPIとUI開発サーバーをHEADへ同期する。

## 事前確認

作業開始時点では以下が起動していた。

| 用途 | URL | PID |
| --- | --- | ---: |
| Engine API | `http://127.0.0.1:8000` | 24108 |
| UI | `http://127.0.0.1:5173` | 31080 |

`GET /v1/meta` の確認結果:

- `build_info.git_commit`: `9adf0b2`
- `HEAD`: `9adf0b2`
- `build_info.git_dirty`: `False`

この時点で、Layout View描画品質改善へ入る前の同期目的は達成済みだった。

その後に発生した本タスクの指示書・完了報告・AGENTS.md追記のみのコミットは、機能・UIコードの実質変更ではない。したがって、AGENTS.mdの除外規定に基づき、このドキュメントのみの整理コミット自体を理由に追加再起動は要求しない。

## 運用メモ

Layout View描画品質改善のような複数コミットにまたがる見込みのタスクでは、完了報告前に再度API/UIプロセスを再起動し、`/v1/meta` の `build_info.git_commit` と最新HEADが一致していることを確認する。

この運用を明確にするため、`AGENTS.md` に「機能・UI変更を伴うタスクの完了報告前に、ローカルAPI/UIを再起動して `build_info.git_commit` とHEAD一致を確認する」旨を追記した。

あわせて、確認対象は機能・コードに実質変更があった最後のコミットであり、後続の指示書・完了報告・AGENTS.md追記のみのコミットは再確認対象に含めないことも明記した。

## 状態

完了。タスク着手時点で `build_info.git_commit=9adf0b2` と `HEAD=9adf0b2` は一致しており、`build_info.git_dirty=False` だったため、Layout View着手前のプロセス同期は確認済みである。
