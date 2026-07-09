# エンジン・UIプロセス再起動報告

日付: 2026-07-10

## 対象

`doc/work_orders/active/codex_restart_processes.md` に基づき、古い可能性があったローカルのエンジンAPIとUI開発サーバーを停止し、当時のHEADコードで再起動した。

## 停止した旧プロセス

| 用途 | ポート | PID | 備考 |
| --- | ---: | ---: | --- |
| Engine API | 8000 | 29832 | 旧uvicornプロセス |
| UI dev server | 5173 | 16000 | 旧Viteプロセス |
| UI dev server | 5174 | 12988 | 5173衝突後に残っていたViteプロセス |

## 起動コマンド

Engine API:

```powershell
python -m uvicorn optics_engine.api.main:app --host 127.0.0.1 --port 8000
```

UI:

```powershell
npm.cmd run ui:dev -- --port 5173
```

## 再起動直後の待受

| 用途 | URL | 実待受PID | Command |
| --- | --- | ---: | --- |
| Engine API | `http://127.0.0.1:8000` | 17920 | `python -m uvicorn optics_engine.api.main:app --host 127.0.0.1 --port 8000` |
| UI | `http://127.0.0.1:5173` | 5784 | `vite apps/workbench-ui --host 127.0.0.1 --port 5173` |

## 再起動直後の確認結果

`GET /v1/meta`:

- `build_info.git_commit`: `bc0b509`
- `HEAD`: `bc0b509`
- `git_dirty`: `True`
- `started_at`: `2026-07-09T18:41:19.080499+00:00`

`git_dirty=True` は、当時 `doc/work_orders/active/codex_restart_processes.md` が未追跡だったため。

`POST /v1/education/preview`:

- `paths_present`: `True`
- `paths_count`: `5`
- first path: `STOP -> S1 -> S2 -> IMG`
- `trace_ms`: `0.8115 ms`

## 追加再確認

本報告作成時点で再度確認したところ、動作中プロセスは同じPIDで継続していたが、その後の作業コミットによりリポジトリのHEADは `13d5dec` まで進んでいた。

`GET /v1/meta`:

- `build_info.git_commit`: `bc0b509`
- `HEAD`: `13d5dec`
- `git_dirty`: `True`

`POST /v1/education/preview`:

- `paths_present`: `True`
- `paths_count`: `5`
- first path: `STOP -> S1 -> S2 -> IMG`
- `trace_ms`: `1.1829 ms`

つまり、再起動タスク実施時点では `build_info.git_commit` とHEADは一致していたが、後続コミット後の現在はプロセスが再びHEADより古い状態になっている。ブラウザで最新コミットの反映を確認する場合は、再度プロセス再起動が必要。

## git_dirty 方針

`git_dirty` は作業ツリー全体の状態を示す値として維持する。`doc/` 配下を除外してコード変更だけを見る方式にはしない。

理由:

- `build_info` は「このプロセスがどの作業ツリー状態から起動されたか」を素直に示すための情報であり、doc変更を除外すると意味が曖昧になる。
- 指示書・報告書追加でも `git_dirty=True` になりうる制約はあるが、`git status --short` と併用すれば内訳を確認できる。
- 本筋の機能・性能実装を止めてまで、dirty分類を細分化する優先度は高くない。

この方針は `AGENTS.md` に追記した。

## 報告運用

コード変更を伴わない確認・運用作業であっても、人間から明示的に依頼された調査・確認タスクは `doc/reports/` に完了報告を残す方針とした。この方針も `AGENTS.md` に追記した。

## 人間側の確認URL

- UI: `http://127.0.0.1:5173`
- Engine API: `http://127.0.0.1:8000`

最新コミット反映を確認する場合は、ブラウザのハードリロードだけでなく、まず `/v1/meta` の `build_info.git_commit` が確認したいコミットと一致しているかを見る。一致していない場合はエンジン/APIプロセスの再起動が必要。
