# Layout View着手前のプロセス再同期

## 背景

`2026-07-10_restart_processes.md`の「追加再確認」で、プロセス再起動後も後続コミット（`bc0b509`→`13d5dec`）によりプロセスが再びHEADより古い状態になっていることが判明した。Layout View描画品質改善（複数コミットにまたがる見込み）に着手する前に、一度プロセスをHEADへ同期させておく。

## 作業

1. 現在のエンジンAPI・UI開発サーバープロセスを停止し、現在のHEADコードで再起動する（`codex_restart_processes.md`と同じ手順）。
2. `GET /v1/meta`の`build_info.git_commit`が現在のHEADと一致することを確認する。
3. 今回の結果を`doc/reports/`に短く記録する（前回同様の形式でよい。詳細な調査は不要、PID・コミット一致確認のみで十分）。
4. Layout View描画品質改善タスク（`codex_q1_layout_view_rendering_quality.md`）の完了後、再度この同期作業が必要になる見込みであることを一言メモしておく（人間側が都度依頼せずとも、大きめのタスク完了後は再起動を促す運用にするかどうかは今後検討）。

## 完了条件

- `build_info.git_commit`が現在のHEADと一致している。
- 短い確認報告が`doc/reports/`に存在する。
