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

ただし、作業ツリーには本タスクの指示書とAGENTS追記が未コミットで存在していたため、コミット後にHEADが進む。そのため、最終的な一致確認は本報告とAGENTS追記をコミットした後、プロセスを再起動して行う。

## 運用メモ

Layout View描画品質改善のような複数コミットにまたがる見込みのタスクでは、完了報告前に再度API/UIプロセスを再起動し、`/v1/meta` の `build_info.git_commit` と最新HEADが一致していることを確認する。

この運用を明確にするため、`AGENTS.md` に「機能・UI変更を伴うタスクの完了報告前に、ローカルAPI/UIを再起動して `build_info.git_commit` とHEAD一致を確認する」旨を追記した。

## 状態

この報告を含むコミット作成後に、API/UIプロセスを再起動し、最終的な `build_info.git_commit` とHEAD一致を確認する。
