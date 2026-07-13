# R74 作業4 自動収束サンプリング設計調査

## 状態

**Done（設計調査のみ。適応サンプリングは未実装）**

- 調査基準HEAD: `c7e9c3ba4866061a359a4f7266e4b55cf796d957`
- 対象: 周辺光量、および偏芯・チルト系で使用するRMS M/S像面探索
- 関連実測: `doc/reports/2026-07-13_r74_task2_relative_illumination_sampling_review.md`
- 関連仕様: `doc/engine_spec.md` 16.5、20.2、21.2、21.4、27章
- コード修正: なし。本作業は設計調査のみ。

## 結論

適応サンプリングは実現可能であり、特にpartial vignettingを含む周辺光量へ有効である。ただし、現行gridを単純にN倍して差分を見る方式では誤差が非単調になるため、**追加batchを再利用できるnested・seed付きサンプラ**が前提となる。

推奨は、周辺光量で統計的信頼区間と逐次差分を併用し、`tolerance_met / max_samples / time_budget`の停止理由を必ず返す方式である。RMS像面探索は、先に同軸系Coddington実装と連続的なfocus solveを整備し、偏芯・チルト系だけへ段階導入する。

## 現状からの制約

- 現行`grid`はNごとに候補集合を作り直し、N=10000の点集合がN=20000の部分集合にならない。
- P002 40 degのrelative illuminationは10000、20000、50000、100000 raysで`0.3083422`、`0.3088243`、`0.3087210`、`0.3083456`となり、単調収束しない。
- 現行`random`も関数呼び出しごとにseed 0からradius列とangle列をcount個ずつ生成するため、Nを変えたときに先頭N点が同じになる保証がない。
- 周辺光量responseはサンプル数や推定誤差を返さない。
- 現行M/S像面は同軸系でも固定21 rays・1 mm刻みRMS探索であり、仕様上のCoddington方式が未実装である。

## 収束判定案

### 案A: 標準誤差・信頼区間

seed付き独立サンプルをbatch追加し、各fieldの重み付きfluxについて平均、分散、有効サンプル数を逐次更新する。中心fieldとの比はdelta methodまたはbatch間分散で誤差伝播し、95%信頼区間の半幅が次を満たしたら停止する。

```text
CI_half_width <= max(absolute_tolerance,
                     relative_tolerance * abs(relative_illumination))
```

長所:

- 精度目標を統計量として説明できる。
- fieldごとに必要Nが異なる場合、未収束fieldだけ追加できる。
- weighted samplingへ拡張できる。

短所:

- 独立または適切にscrambleされたサンプルという前提が必要。
- pが0/1付近では通常近似が過度に楽観的になるため、Wilson区間等が必要。
- low-discrepancy列では素朴な標準誤差をそのまま使えない。

P002 40 degのthroughput約`0.895`に対し、独立Bernoulli近似で95%相対半幅`0.5%`を満たす目安は約18000 raysである。最悪付近のp=0.5では約154000 raysとなり、100000上限でも未収束になり得る。

### 案B: nested sampleの逐次差分

Nを1024→2048→4096のように倍増し、前段sampleを含むnested列で推定値を更新する。次を2段階連続で満たしたら停止する。

```text
abs(value_2N - value_N)
  <= max(absolute_tolerance, relative_tolerance * abs(value_2N))
```

長所:

- 分布仮定を置かず、deterministic/quasi-Monte Carloにも利用できる。
- 実装とUI説明が比較的単純。

短所:

- 偶然近い2段階で偽収束する可能性がある。
- 信頼水準を直接与えられない。
- nestedでない現行gridには適用できない。

### 推奨: 併用

案Aを主判定、案Bを安定性gateとして併用する。少なくとも2段階連続で逐次差分を満たし、同時に信頼区間条件を満たした場合だけ`converged=true`とする。統計的CIを提供できないdeterministic modeでは、`criterion: successive_difference`を明記し、confidenceを返さない。

## 推奨API

```yaml
relative_illumination_sampling:
  mode: adaptive
  initial_samples: 1024
  max_samples: 65536
  growth_factor: 2
  relative_tolerance: 0.01
  absolute_tolerance: 0.002
  confidence: 0.95
  consecutive_levels: 2
  seed: 0
  time_budget_ms: 5000
```

response metadata:

```json
{
  "sampling": {
    "mode": "adaptive",
    "samples_used": 8192,
    "levels": [1024, 2048, 4096, 8192],
    "estimated_error": 0.0031,
    "confidence_interval": [0.704, 0.710],
    "converged": true,
    "stop_reason": "tolerance_met",
    "seed": 0,
    "elapsed_ms": 840.2
  }
}
```

`max_samples`または`time_budget_ms`で停止した場合も最良推定値を返し、構造化warning `sampling_not_converged`へ`requested_tolerance`、`estimated_error`、`samples_used`、`stop_reason`をparamsとして含める。

## RMS像面探索への適用

同軸系はCoddingtonが既定となるためadaptive samplingを適用しない。偏芯・チルト系のRMS方式では、同一sample列を使ってfocus solveを行い、M/S focus shiftとRMS幅の両方を確認する。

推奨初期値:

- N: 256→512→1024→2048→4096
- focus shift absolute tolerance: 0.01 mm
- RMS relative tolerance: 1%
- 2段階連続一致
- 共通rayによるcommon random numbers

現行1 mm刻みの11点探索では0.01 mm収束を評価できないため、連続的な1次元solveと探索端warningの実装が先行条件となる。

## 30秒性能ガード

P002 2 fields・1 wavelength・paraxial aimingの実測では、10000 raysが約120 ms、100000 raysが約1312 msだった。単純比例で9 fields・3 wavelengthsへ拡大すると約17.7秒相当であり、full aimingや他のRun Charts解析とのCPU競合を含めると30秒へ接近する。

Run Chartsは7 endpointを並列実行するため、adaptive samplingの可変時間は最遅endpointとCPU競合を増やす。次を推奨する。

- Run Charts既定: relative tolerance 1%、最大16384〜65536、endpoint予算5秒
- high accuracy明示: relative tolerance 0.5%、最大100000、endpoint予算15秒
- 全体30秒deadlineをUI/API双方で維持
- time budget到達時は値を破棄せず、未収束warning付きで返す
- E2Eでは高速収束、max_samples停止、time_budget停止を別fixtureで固定する

## 変更規模

| 範囲 | 規模 | 理由 |
|---|---|---|
| 周辺光量のみ | 中 | nested sampler、逐次統計、API metadata、warning、性能test |
| 偏芯系RMS像面探索 | 大 | Coddington分離、連続focus solve、2軸収束、ray再利用 |
| UI・Run Charts統合 | 中 | 精度preset、収束表示、deadline、i18n/E2E |
| 全体 | 大 | 複数解析のsampling契約と性能budgetを横断するため |

## 推奨実装順

1. R74作業2で登録した放射量sampling・metadataの仕様整合を先に行う。
2. nested・seed付きbatch samplerを追加する。
3. 周辺光量へ案A＋案Bの適応判定を導入する。
4. Run Chartsの5秒budgetと未収束表示を追加する。
5. Coddington実装後、偏芯・チルト系RMS探索へ同じcontrollerを拡張する。

## backlog

`doc/reports/issues_backlog.md`へ「周辺光量とRMS像面探索に適応的収束サンプリングを導入する」を登録した。先行する放射量sampling修正Issue、Coddington実装Issueとは別の後段Issueとして扱う。

## テスト・検証結果

- `python -m pytest -q` 初回: `1 failed, 106 passed, 1 skipped`。失敗は`tests/test_engine_v2_3.py::test_artifact_http_lifecycle_content_types_and_expiry`で、`ttl_seconds=0.02`のartifactが正常取得前に期限切れとなった。
- 上記テストの単独反復: `5/5 passed`。R74はドキュメント調査のみで当該コードを変更していないため、実時間20 msへ依存する既存テストのflaky事象と判断した。
- `python -m pytest -q` 再実行: `107 passed, 1 skipped, 1 warning in 12.56s`。
- `npm run ci`: 成功。build、i18n、SVG/chart検証、Playwrightを含み、Playwrightは`38 passed (51.7s)`。
- flaky事象は`doc/reports/issues_backlog.md`へ「ArtifactStoreの短TTLテストを時刻ジッタに強くする」として登録した。

## R74全体監査

| 作業 | 状態 | 根拠コミット | 報告書・検証 |
|---|---|---|---|
| 作業1 Field curvature / M-S sampling | Done（調査） | `86a87bd430dc254c983219b71cf026750ef9e345` | `2026-07-13_r74_task1_field_curvature_sampling_review.md`、focused `4 passed` |
| 作業2 Relative illumination sampling | Done（調査） | `f84480d` | `2026-07-13_r74_task2_relative_illumination_sampling_review.md`、focused `4 passed` |
| 作業3 Distortion sampling | Done（調査） | `c7e9c3ba4866061a359a4f7266e4b55cf796d957` | `2026-07-13_r74_task3_distortion_sampling_review.md`、focused `1 passed` |
| 作業4 Adaptive sampling | Done（設計調査） | 本報告コミット | 本報告、full pytest `107 passed, 1 skipped`、`npm run ci`成功 |

R74は調査・設計タスクであり、エンジン/API/UIコードの変更は行っていない。適応サンプリング、Coddington方式、周辺光量専用sampling・metadataはいずれも未実装であり、完了主張の対象外である。
