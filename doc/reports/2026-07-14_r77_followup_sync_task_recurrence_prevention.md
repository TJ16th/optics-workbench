# R77 同期タスク再発防止フォローアップ完了報告

## 状態

**Done with noted limitation**

Windowsタスク `OpticsCrossWorkspaceDocSync-R55` の失敗時再起動設定とTask Scheduler Operational履歴を有効化し、単一ワーカー稼働およびレポート同期の往復を確認した。ソースコード、エンジン仕様、UI仕様の変更はない。

根拠となる直前コミットは `c533a20`（`docs: record report sync outage investigation`）。本タスクの運用確認は、下記のTask Scheduler設定値、プロセス確認、SHA-256同期試験を直接実行して固定した。

## 実施内容

### 1. 失敗時再起動設定

`OpticsCrossWorkspaceDocSync-R55` に以下を設定した。

- `RestartCount: 3`
- `RestartInterval: PT1M`
- `MultipleInstances: IgnoreNew`（維持）
- `ExecutionTimeLimit: PT0S`（維持）

`Export-ScheduledTask` のXMLでも `<RestartOnFailure>` に `<Count>3</Count>` と `<Interval>PT1M</Interval>` が保存されていることを確認した。既存のログオントリガー、750 msポーリング、起動時SHA-256補完処理は変更していない。

### 2. Task Scheduler履歴

管理者権限で次を実行した。

```powershell
wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true
```

確認結果:

```text
enabled: true
```

これにより、今後の停止・再起動についてTask Scheduler Operationalログを追跡できる。

### 3. 単一ワーカー確認

最終確認時の状態は以下のとおり。

```text
State: Running
WorkerCount: 1
WorkerPids: 17628
```

タスクは1件、実ワーカーも1プロセスであり、重複起動はない。

### 4. 同期往復試験

`doc/reports/2026-07-13_report_sync_outage_investigation.md` に一時HTMLコメントを追加し、Claude側への反映後にコメントを除去した。

- 一時変更の反映: 500 msで確認
- 復元後source SHA-256: `9E3AB1C5E7319956F50C310693DD5ED529BA2A17B4AA837969BA898B77FA7C3D`
- 復元後destination SHA-256: `9E3AB1C5E7319956F50C310693DD5ED529BA2A17B4AA837969BA898B77FA7C3D`
- 復元後Git差分: なし

Codex側reportからClaude側reportへの更新・復元が正常に動作している。

## 意図的停止試験の結果と制約

設定適用後、手動起動中の同期ワーカーPID `30692`を `Stop-Process -Force` で終了し、95秒監視した。この経路ではタスクが `Ready` になり、自動再起動は観測されなかったため、同期タスクを手動起動してPID `17628`で復旧した。

この結果から、Task Schedulerの `RestartOnFailure` は設定済みであるものの、手動起動したインスタンスを外部から強制終了する試験経路は再起動対象の失敗として扱われない。今後、実障害が発生した場合は今回有効化したOperationalログで終了理由と再起動イベントを確認する。同期処理を停止したままにはしていない。

## テスト

本タスクはWindows運用設定のみであり、エンジン/API/UIコードを変更していないため、`python -m pytest -q`、`npm run ci`、ベンチマークは対象外とした。

実施した直接確認:

- `Get-ScheduledTask` / `Export-ScheduledTask` による設定確認
- `wevtutil gl Microsoft-Windows-TaskScheduler/Operational` による `enabled: true` 確認
- `Win32_Process` による実ワーカー1件確認
- 一時変更とSHA-256による双方向の更新・復元確認
