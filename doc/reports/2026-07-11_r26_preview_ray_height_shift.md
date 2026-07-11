# R26 preview ray height shift 確認報告

## 対象

- 指示書: `doc/work_orders/done/codex_r26_preview_ray_height_shift.md`
- 対象UI: `apps/workbench-ui/src/ui/App.tsx` の `layoutRayItems`
- 対象preset: `P002 N-BK7 Biconvex Singlet 50mm Demo`

## 確認内容

P002で `samples_per_field` を `5 / 9 / 15 / 25` に変えたとき、Layout Viewで表示される代表光線（`lower` / `center` / `upper`）のSTOP面到達Y座標を確認した。

確認条件:

- fields: `center`, `edge-y`, `edge-z`
- wavelengths: `486.13`, `587.56`, `656.27`
- `pupil_distribution: grid`
- `ray_aiming.mode: paraxial`
- `store_path: true`
- Layout Viewと同じ選択ロジック:
  - field×wavelengthごとにalive pathを集める
  - STOP面の実到達Y座標でsort
  - 最小を`lower`
  - `abs(stopY)`最小を`center`
  - 最大を`upper`

## 計測結果

代表としてd線（`587.56nm`）を記載する。STOP面ではこの条件の各wavelengthで同じY座標になった。

| samples_per_field | total rays | displayed rays | lower stopY mm | center stopY mm | upper stopY mm |
| ---: | ---: | ---: | ---: | ---: | ---: |
| `5` | `45` | `27` | `-2.66666666667` | `2.66666666667` | `8.0` |
| `9` | `81` | `27` | `-4.0` | `0.0` | `4.0` |
| `15` | `135` | `27` | `-4.8` | `-1.6` | `4.8` |
| `25` | `225` | `27` | `-5.33333333333` | `0.0` | `5.33333333333` |

field別に見ると、`center` / `edge-y` / `edge-z` の3 fieldで同じ代表Y座標になった。

## 切り分け結果

結論: **LOD代表選択ロジックのバグではなく、瞳サンプリング方式の性質**。

理由:

- 現在の `layoutRayItems` はsample indexではなく、実際のSTOP面到達Y座標（`local_point_mm[1]`）を使って `lower` / `center` / `upper` を選んでいる。
- したがってQ1-symmetryで修正された「sample indexベースの代表選択」には戻っていない。
- 一方、`grid`サンプリングは`samples_per_field`ごとに候補点集合を作り直すため、最小・最大・中心に最も近いサンプルの実Y座標が変わる。
- `samples_per_field=5`や`15`では、候補集合にY=0の中心サンプルが含まれず、`center`代表が0mmからずれる。

追加確認:

| distribution | 傾向 |
| --- | --- |
| `grid` | `samples_per_field`により最小/最大/中心候補Yが変わる |
| `hexapolar` | 現行実装ではgrid相当の経路になり、同じ傾向 |
| `fan_y` | 常にY=-1/0/+1を含み、代表高さが比較的安定する |
| `fan_z` | Yは常に0で、Y方向のlower/upper比較には向かない |

## 対応

- コード修正は行わなかった。現在の代表選択は実到達座標ベースであり、R26で疑われたLOD選択バグではないため。
- 人間に分かりやすい説明をUI/ヘルプへ追加する将来課題として、`doc/reports/issues_backlog.md` に以下を追記した。
  - `Issue: Layout Viewの代表光線がsampling方式に依存して見えることを説明する`

## 検証コマンド

```bash
python - <<'PY'
# P002 systemをload_systemし、trace_forward(..., store_path=True)でSTOP面Y座標を集計
PY
```

結果:

- R26計測表の通り。
- コード挙動変更なしのため、追加テスト・buildは実行していない。

## 残件

- backlogに新規項目を追加した。Issue化には `Create Issues From Backlog` ワークフローの手動起動が必要。
- UIに説明文を入れる場合は、i18n ja/enを追加し、`npm run i18n:coverage`で確認する。
