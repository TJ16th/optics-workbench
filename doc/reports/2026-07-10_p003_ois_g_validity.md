# P003 OIS_G Validity Report

Date: 2026-07-10

## 対象

- Work order: `doc/work_orders/active/codex_p003_ois_g_validity.md`
- 対象プリセット: P003 Achromat Doublet 100mm Demo

## 面構成の確認

P003の3つの屈折面は以下の材質境界を表す。

| Surface | 意味 | material_after |
|---|---|---|
| S1 | 空気 -> N-BK7 | N-BK7 |
| S2 | N-BK7 -> N-F2 の接合面 | N-F2 |
| S3 | N-F2 -> 空気 | AIR |

したがって、旧 `OIS_G: S2-S3` はF2側だけをdecenter/tilt対象にし、接合アクロマートを片側だけ動かす定義だった。

## 修正内容

- P003の `OIS_G` を `S2-S3` から `S1-S3` へ変更した。
- Python側のP003テストfixtureも同じ定義に揃えた。
- `tests/test_engine_v2_1.py` に、`FOCUS_G` / `OIS_G` がどちらも接合ブロック全体 `(S1..S3)` を対象にすることを固定する回帰テストを追加した。

`FOCUS_G` と `OIS_G` は同一の接合レンズブロック全体を参照する。これは同一物理ブロックに対して、focus用のX移動とOIS用のdecenter/tiltを適用する教育用MVPとして扱う。接合面をまたいで片割れだけを動かす旧定義は解消した。

## 横断確認

- P003:
  - `FOCUS_G`: S1-S3、接合ブロック全体。問題なし。
  - `OIS_G`: S1-S3、接合ブロック全体へ修正。問題なし。
- P006:
  - `EYE_G`: EYE単面。
  - `FOCUS`: EYEPIECE単面。
  - 接合面や複数材質ブロックを分割するgroupはない。
- Python test fixture内のP003定義も同様に修正済み。

## 近軸検証

`tests.test_engine_v2_1.p003_achromat_system()` を使い、更新後のgroup範囲で検証した。

Group ranges:

```text
FOCUS_G: (S1..S3) = (1, 3)
OIS_G:  (S1..S3) = (1, 3)
```

| Configuration | validation | EFL mm | BFL mm | F/# | paraxial image position mm |
|---|---|---:|---:|---:|---:|
| base | ok | 93.143466 | 90.431627 | 4.657173 | 97.931627 |
| close_focus | ok | 93.143466 | 90.431627 | 4.657173 | 99.931627 |
| OIS_G decenter Y +1mm | ok | 93.143466 | 90.431627 | 4.657173 | 97.931627 |
| OIS_G tilt Y +1deg | ok | 93.143344 | 90.431922 | 4.657167 | 97.931009 |

## Backlog

`doc/reports/issues_backlog.md` に以下2件を登録した。

- `edge_thickness metricのエンジン実装を追加する`
- `最適化APIにmulti-configuration（複数zoom_position/フォーカス位置）評価を追加する`

## 検証

- `python -B -m pytest tests/test_engine_v2_1.py -q`
  - 18 passed, 1 skipped
- `python -B -m pytest -q`
  - 60 passed, 1 skipped
- `npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts -g "group edits|decenter tilt|P003 slider"`
  - 3 passed
- `npm.cmd run ci`
  - 16 Playwright testsを含む全チェック passed
