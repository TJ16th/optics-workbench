# R83 full aiming持続スループット計測

## 結論

R83は調査・計測のみで完了した。製品コードは変更していない。計測対象コミットは`10584e126064866f9d2de4740b028b845f56ebb1`（R82機能コミット）で、正式な生データは`bench_results/20260714_134920_r83_optimization_throughput.json`に保存した。

- `POST /v1/optics/evaluate`の25.7節`jacobian`モードは**未実装**。リクエストへ`jacobian`を付けてもHTTP 200で無視され、応答に`jacobian`はない。
- `POST /v1/optics/evaluate-batch`は候補ごとに独立して`evaluate_system()`を呼ぶ。基準点のaiming解を摂動点へ渡す処理や候補次元の一括traceはない。
- R73の簡易merit条件をfull aiming化したHTTP coldは`5.667–29.937 ms/evaluate`（`33.403–176.447 evaluate/s`）。仕様27.3節の`100–500 ms/候補`を全条件で下回った。
- 100 cold候補の線形外挿は`0.567–2.994 s`で、仕様の`10–60 s`上限を十分下回る。
- 現行の外部有限差分でも、20変数・30反復の外挿はP002で`3.570 s`、最大のP011で`18.860 s`。今回の簡易merit条件では実用域にある。
- ただし25.7節を中央仮定`1.25 × cold evaluate`で実装できれば、5/10/20変数でそれぞれ約`4.8x / 8.8x / 16.8x`短縮できる。GPU化判断より先に投資効果が明確なCPU側の候補である。

## 1. 実装状況

### `/v1/optics/evaluate`

`optics_engine/api/main.py::optics_evaluate()`は`evaluation`、`configuration`、`variables`、`ray_sampling`だけを`evaluate_system()`へ渡しており、`jacobian`を参照しない。`EvaluateResult`にもjacobian応答フィールドはない。

APIへ`jacobian.mode=forward_diff`、変数`S1_radius_mm`を付けて直接POSTした結果は次のとおりだった。

```text
HTTP 200
response keys: merit, metadata, metrics, operands, status, violations
has_jacobian: false
```

したがって現状の最適化的ワークフローは、変数n個につき基準点を含む`n+1`回の独立evaluateである。

### `/v1/optics/evaluate-batch`

`optics_engine/optimization.py::evaluate_batch()`は各candidateについて`evaluate_system(base_system, ..., variables=...)`を呼ぶ。各評価は`apply_variables()`後に`compile_system()`し、候補間でaiming origin、瞳サンプル、近軸量を引き渡さない。`parallel_workers > 1`時も同じ関数をThreadPoolで並列実行するだけである。

2 candidateをAPIへ直接POSTした結果、応答metadataは`candidate_count=2`、`parallel_workers=1`だけで、候補は異なる`system_hash`を持った。warm start共有を示す項目や処理はなかった。

## 2. 計測条件

R73作業5の回帰テストを根拠に、以下を「簡易merit」とした。

| 項目 | 条件 |
|---|---:|
| operands | `ray_fan_error`, `longitudinal_aberration` |
| field | center 1点 |
| wavelength | 587.56 nm 1本 |
| pupil samples | 9 |
| aiming | `full` |
| 内部trace | fan_y + fan_z + fan_y = 3回 |
| 公称ray数 | 27/evaluate |

`ray_fan_error`はfan_y/fan_z、`longitudinal_aberration`はfan_yを実行する。R73テストの`paraxial`だけをR83の目的に合わせて`full`へ変更した。

P002/P007/P012/P011で`S1_radius_mm`を基準値から相対`1e-7`刻みで変えた。全値は正のedge thickness等を変化させない微小域であり、各初回traceのmetadataが`aiming_cache_hits=0`, `aiming_cache_misses=1`、同一系の再実行が`hits=1`, `misses=0`であることを4系すべてで直接確認した。

反復数はlocal cold 50、local hit 100、HTTP cold 30、HTTP hit 50。HTTPはlocalhostへのpersistent connectionを使用した。

## 3. 持続スループット

### HTTP実測

| preset | 屈折面 / 全entry | cold mean ms | cold eval/s | hit mean ms | hit eval/s |
|---|---:|---:|---:|---:|---:|
| P002 | 2 / 4 | 5.667 | 176.447 | 6.190 | 161.555 |
| P007 | 4 / 6 | 19.988 | 50.029 | 6.505 | 153.738 |
| P012 | 7 / 9 | 27.074 | 36.936 | 8.743 | 114.371 |
| P011 | 10 / 12 | 29.937 | 33.403 | 10.778 | 92.784 |

P007/P012/P011ではhitがcoldの約`3.1–3.7x`高速だった。P002はSTOPが先頭でaiming solve自体が軽く、HTTP/JSONコストが支配するためhitの優位が見えなかった。

### HTTP・シリアライズ影響

| preset | local cold ms | HTTP cold ms | 差分 ms | HTTP内比率 | local hit ms | HTTP hit ms | 差分 ms | HTTP内比率 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P002 | 4.264 | 5.667 | 1.403 | 24.8% | 3.441 | 6.190 | 2.749 | 44.4% |
| P007 | 19.219 | 19.988 | 0.769 | 3.8% | 4.516 | 6.505 | 1.989 | 30.6% |
| P012 | 26.253 | 27.074 | 0.821 | 3.0% | 6.343 | 8.743 | 2.400 | 27.5% |
| P011 | 29.710 | 29.937 | 0.227 | 0.8% | 8.046 | 10.778 | 2.732 | 25.3% |

空に近い`GET /v1/health`のpersistent HTTP中央値は`0.892 ms`だった。coldの複雑系ではHTTP差分は`0.8–3.8%`で無視できる。一方、P002 coldと全hit系列では`24.8–44.4%`を占めるため、高頻度最適化ではエンジン内batch化がHTTP呼び出し削減の面でも有効である。差分は別プロセス間の平均値比較であり、厳密なendpoint内profiling値ではない。

## 4. 最適化ワークフロー外挿

HTTP cold平均を使い、`Jacobian = (n+1) × cold`、全体時間=`Jacobian × 反復数`で線形外挿した。

| 変数n | 1 Jacobianの範囲 | 10反復 | 30反復 |
|---:|---:|---:|---:|
| 5 | 34.002–179.622 ms | 0.340–1.796 s | 1.020–5.389 s |
| 10 | 62.337–329.307 ms | 0.623–3.293 s | 1.870–9.879 s |
| 20 | 119.007–628.677 ms | 1.190–6.287 s | 3.570–18.860 s |

範囲の下端はP002、上端はP011。20変数ではP012/P011の1 Jacobianが`500 ms`を超えるが、これは21候補分の合計であり、1候補はそれぞれ`27.074 / 29.937 ms`で27.3節の候補目標内である。

100候補の線形外挿はP002/P007/P012/P011の順に`0.567 / 1.999 / 2.707 / 2.994 s`。仕様の`10–60 s`は上限側の性能目標として全条件で達成している。ただし、より多いfield・wavelength・rayや高価なoperandへ一般化した値ではない。

## 5. Jacobian batchの理論効果

25.7節の「ほぼ1回強」を定量化するため、実装後コストを保守的な中央仮定`1.25 × cold evaluate`、感度幅を`1.1–1.5 ×`と置いた。中央仮定の短縮率は次のとおり。

| 変数n | 現状回数 | batch仮定 | 短縮率 | P011 1 Jacobian | P011 30反復 |
|---:|---:|---:|---:|---:|---:|
| 5 | 6回 | 1.25回相当 | 4.8x | 37.421 ms | 1.123 s |
| 10 | 11回 | 1.25回相当 | 8.8x | 37.421 ms | 1.123 s |
| 20 | 21回 | 1.25回相当 | 16.8x | 37.421 ms | 1.123 s |

感度幅では短縮率はn=5で`4.0–5.5x`、n=10で`7.3–10.0x`、n=20で`14.0–19.1x`となる。これは未実装機能の理論試算であり、達成値の主張ではない。

## 6. 判定

- 現行CPU実装は、R73由来の簡易meritでは27.3節の候補・100候補目標を達成。
- 5–10変数・10–30反復は現行の独立HTTP evaluateでも秒単位。20変数・P011・30反復でも約18.9秒。
- HTTPはcold複雑系では主要ボトルネックではないが、cache hitや軽量系では無視できない。
- 25.7節は未実装で、変数数に比例する重複計算が残る。実装時の期待効果は4.8–16.8倍程度で、GPU化とは独立に検討価値が高い。
- 本タスクではGPU化、Numba化、Jacobian batch実装の判断・コード変更は行っていない。

## 検証根拠

- 対象機能コミット: `10584e126064866f9d2de4740b028b845f56ebb1`
- benchmark JSON: `bench_results/20260714_134920_r83_optimization_throughput.json`
- API直接確認: `POST /v1/optics/evaluate`, `POST /v1/optics/evaluate-batch`, `GET /v1/health`
- cache直接確認: P002/P007/P012/P011でcold `miss=1`、warm `hit=1`
- テスト結果: `python -m pytest -q` -> `118 passed, 1 skipped, 1 warning in 13.38s`
