# P0 task6 latency harness 完了報告

## 実施内容

- `benchmarks/latency_harness.html` を追加した。
- Workbench UI本体には触れず、単一HTMLの手動計測ツールとして実装した。
- HTML内に軽量な薄レンズ系を埋め込み、初回に `/v1/systems/register`、以後スライダー変更ごとに `/v1/education/preview` を送る。
- 操作対象は以下の2つ。
  - `iris_radius_mm`
  - `FOCUS_G.shift_x_mm`
- リクエスト条件は `ray_aiming: paraxial`、`samples_per_field: 5`、`3 fields`、`1 wavelength`、`profiling: true`。
- in-flight中のスライダー変更は最新値のみ保持し、応答後に次リクエストを送るキュー制御にした。
- 表示項目として、end-to-end latency、直近1秒のeffective fps、queued count、total rays、profiling breakdown、簡易bottleneck hintを追加した。

## 仕様書・指示書との差分

- 指示通り、`benchmarks/` 配下の独立HTMLのみを追加した。
- 外部JSライブラリ、npm追加、Workbench UI本体変更、描画機能追加は行っていない。
- CORSは既存APIが `http://127.0.0.1:5175` を許可済みだったため、エンジン側変更は不要だった。
- ブラウザで開く場合は、例として `python -m http.server 5175 -d benchmarks` で配信する。

## 検証結果

- 行数確認:
  - `benchmarks/latency_harness.html`: 250行
- ブラウザ相当確認:
  - `http://127.0.0.1:5175/latency_harness.html`
  - Playwright + msedgeで登録、単発preview、10秒連続sweepを確認。
- 単発preview実測:
  - `completed`: `1`
  - `latency`: `13.4 ms`
  - `rays`: `15`
  - `engine profiling total`: `1.672 ms`
- 10秒連続sweep実測:
  - `completed`: `558`
  - 直近 `latency`: `6.2 ms`
  - 直近 `fps`: `61.0`
  - `queued`: `73`
  - `rays`: `15`
  - `engine profiling total`: `0.950 ms`
  - bottleneck hint: `http_serialization_overhead_ms = 5.250 ms`

## 判定

- 10 fps以上を達成したため、タスク6の完了条件を満たした。
- 10 fps未満時の原因表示も、profiling totalとclient e2e latencyの差分から `http_serialization_overhead_ms` として表示できる。

## 根拠

- 変更ファイル: `benchmarks/latency_harness.html`
- 検証コマンド: Playwright + msedge によるブラウザ相当操作
- 対象コミット: 本報告を含むP0 task6コミット
