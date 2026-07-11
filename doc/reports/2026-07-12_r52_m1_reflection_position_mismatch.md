# R52 M1反射位置と描画位置の不一致 修正報告

## 結論

原因は分類(a)のLayout View描画バグだった。光線追跡が返すM1/M2交点は各球面の物理sagと一致していたが、Layout Viewだけがmirrorの曲率を見やすくする目的でsagを`8倍`に拡大していた。このため、実座標で描く光線の折れ点と、拡大sagで描くmirror pathが一致していなかった。

光線追跡カーネル、交点計算、propagation sign、P005面配置には問題がなかった。

## 実光線座標

P005、center field、587.56 nm、full ray aimingの`layout_baseline_rays`から取得したchief rayは次の通りだった。

| 面 | X (mm) | Y (mm) | Z (mm) |
|---|---:|---:|---:|
| STOP | 0.000000000 | 40.000000000 | 0 |
| M1 | 79.599959992 | 40.000000000 | 0 |
| M2 | -570.093293020 | 13.996665278 | 0 |
| IMG | 480.000000000 | -0.014051542 | 0 |

system定義からコンパイルした面頂点は`STOP=0`、`M1=80`、`M2=-570`、`IMG=480 mm`である。球面では反射点Xは頂点Xそのものではなく、光線高さに対応するsag分だけ移動する。

- M1: vertex `80` + sag(`R=-2000`, `r=40`) = `79.599959992 mm`
- M2: vertex `-570` + sag(`R=-1050`, `r=13.996665278`) = `-570.093293020 mm`

したがって、traceの交点座標は物理球面上にある。

参考としてmarginal rayのM1反射点は`X=77.498435544 mm, Y=±100 mm`、M2反射点は`X=-570.581755145 mm, Y≈±34.947780552 mm`で、いずれも各球面sagと一致した。

## データソースの確認

### Mirror path

`LayoutView`は`systemPositions(system)`で面頂点Xを求め、`surface.radius_mm`と`surfaceSagMm()`からprofileを生成する。修正前はmirrorだけ次の表示倍率を適用していた。

```ts
surfaceSagMm(surface, rayHeightMm) * 8
```

### Ray path

光線はAPIの`path[].point_mm`を`rayPathD()`へ渡し、同じ`xScale()`と物理Y倍率でSVG pathへ変換する。sagの表示拡大は適用していない。

この異なるsag倍率が不一致の直接原因だった。

## 修正内容

- mirror profileのsag表示倍率を廃止し、全surfaceを物理sagの`1倍`で描画するようにした。
- P005 E2Eを物理sag時のM1/M2 profile幅へ更新し、再び誇張倍率が入ると失敗するようにした。
- Python回帰テストへ、M1/M2のhit Xが`vertex X + spherical sag`と`1e-9 mm`以内で一致する直接検証を追加した。
- 既存の反射ベクトル則検証も維持した。

## 実ブラウザ確認

実APIと`http://127.0.0.1:5173/?lng=en`を使い、chief ray折れ点からSVG mirror pathまでの最短距離を計測した。

- M1: `0.000007772 px`
- M2: `0.003955034 px`

サンプリング誤差を含めても視覚上・数値上ともmirror path上で反射している。

![P005 mirror reflection points aligned with physical profiles](screenshots/2026-07-12_r52_m1_reflection_position_mismatch_1.png)

## 検証

- 対象Pythonテスト: `2 passed in 1.04s`
- 対象UI E2E: `1 passed (3.3s)`
- `python -m pytest -q`: `87 passed, 1 skipped, 1 warning in 7.44s`
- `npm run ci`: 成功
- `npm run ui:e2e`: `28 passed (38.7s)`
- 実装根拠: 本報告と同一のR52コミット（`fix(ui): align mirror profiles with ray intersections (R52)`）

## Golden Testへの影響

エンジン計算は変更していない。Golden Testを含む全pytestはグリーンで、M1→M2 `-650 mm`、M2→IMG `+1050 mm`の頂点間隔も不変である。今回追加した検証により、頂点間隔だけでなく実際の球面hit座標も固定した。

## プロセス整合

機能コミット後にAPI・UIを再起動し、`GET /v1/meta`の`build_info.git_commit`と当該コミットのHEADが一致することを確認して完了した。
