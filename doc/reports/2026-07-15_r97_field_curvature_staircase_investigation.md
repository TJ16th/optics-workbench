# R97 像面湾曲チャートの階段状異常調査

## 結論

提示されたノコギリ状・階段状の像面湾曲は、**UIの座標変換や点順序ではなく、旧実装または明示`method=rms_search`で返る離散的なエンジン値が原因**である。

RMS経路の`_best_focus_for_field()`は`search_range_mm=5`を既定11点で探索するため、候補は`-5, -4, ... 5 mm`の1 mm刻みに限定される。P002の16 fieldではMが5種類、Sが3種類の値しか持たず、標準パネルでは同じX座標を結ぶ垂直線、個別パネルでは同じY座標を結ぶ水平線として現れる。

現行P002既定はR75で実装された`_coddington_focus()`を使用し、API値・両チャートDOMとも滑らかである。現行コードでは提示現象を再現せず、製品コードの修正は行っていない。

## 再現条件

- preset: `P002 N-BK7 Biconvex Singlet`
- fields: 0〜14 degの1 deg刻み15点と`mid-y=9.900092 deg`、計16点
- primary wavelength: `587.56 nm`
- API:
  - `POST /v1/analysis/field-curvature`
  - `POST /v1/analysis/ms-image-surface`
- 現行既定: `method=coddington`
- 異常再現: `method=rms_search`, `search_range_mm=5.0`

UIの個別チャートX軸上限が`14.70 deg`となるのは、最大field `14 deg`へ`ChartSvg`が5% paddingを加えるためである。指摘された約`14.65 deg`という範囲とも整合し、対象はP002と判定した。

## API実測

稼働中APIは`GET /v1/meta build_info.git_commit=0bac84b`で、R75実装`84c592f`を含む現行機能コミットだった。

### 現行Coddington

両endpointはHTTP 200、`metadata.method=coddington`、16 rowsを返した。代表値は次のとおり。

| field deg | M mm | S mm |
|---:|---:|---:|
| 0 | 1.036217 | 1.036217 |
| 4 | 0.688702 | 0.866626 |
| 8 | -0.338440 | 0.361491 |
| 9.900092 | -1.052445 | 0.006857 |
| 12 | -1.999965 | -0.468324 |
| 14 | -3.046984 | -0.999653 |

全16点でM/Sは滑らかかつ単調で、丸めや離散分岐はなかった。

### RMS探索による異常再現

同じrequestへ`method=rms_search`を指定すると、値は次のように量子化された。

| field deg | M mm | S mm |
|---:|---:|---:|
| 0〜5 | 0 | 0 |
| 6〜7 | -1 | 0 |
| 8 | -1 | -1 |
| 9 | -2 | -1 |
| 9.900092〜10 | -2 | -1 |
| 11〜12 | -3 | -1 |
| 13〜14 | -4 | -2 |

metadataは`method=rms_search`, `search_steps=11`だった。探索範囲端には達していないためwarningはなく、異常は非収束ではなく粗い候補点から最小値を選ぶ方式そのものによる。

## 原因箇所

### エンジン

`optics_engine/field_curvature.py`の`_best_focus_for_field()`が次を行う。

- `np.linspace(-search_mm, search_mm, steps)`
- 既定`search_mm=5.0`, `steps=11`
- 最小RMSの候補点をそのままfocus shiftとして返し、候補間の補間・局所再探索をしない

初回公開コミット`436babb`では、同軸P002もこのRMS探索を使いながら`method=coddington_rms_consistent`と表示していた。R75機能コミット`84c592fdd967ca4f96c70a8a3b938992e1ebb01e`が実Coddington漸化式を追加し、P002/P003の既定経路を`_coddington_focus()`へ置き換えた。

提示スクリーンショット相当の値は、R75以前のAPIプロセス、または現行APIへ`method=rms_search`を明示した場合に再現する。Workbenchの`runChartAnalyses()`は`method`を送信しないため、現行P002で後者は通常発生しない。提示時点では古いAPIプロセスが稼働していた可能性が高いと推定する。

### UI

`apps/workbench-ui/src/ui/App.tsx`の次の関数を確認した。

- `seriesFromFieldCurvature()`: field角をX、M/S shiftをYへ写像
- `seriesFromFieldCurvatureStandard()`: M/S shiftをX、field角をYへ写像
- `ChartSvg()`: seriesの点をpolylineで接続

現行Coddington応答を実UIへ通したDOMでは、両seriesとも16点が連続座標になった。RMS応答を同じUIへ通すと次のDOMになった。

- 標準版: 16点に対し、Mのdistinct Xは5、Sは3
- 個別版: 16点に対し、Mのdistinct Yは5、Sは3

したがって2パネルは別々の不具合ではなく、同じ量子化値を軸交換して表示した結果である。UIのソート・scale・重複生成は根本原因ではない。

## スクリーンショット

- 現行Coddingtonの滑らかな表示: [screenshots/2026-07-15_r97_field_curvature_staircase_investigation_1.png](screenshots/2026-07-15_r97_field_curvature_staircase_investigation_1.png)
- `rms_search`を明示した提示現象の再現: [screenshots/2026-07-15_r97_field_curvature_staircase_investigation_2.png](screenshots/2026-07-15_r97_field_curvature_staircase_investigation_2.png)

2枚目では、標準版の垂直ジャンプと個別版の水平階段が同時に確認できる。

## 修正判断

P002の現行既定経路には修正不要である。再発時は、ブラウザ確認前に`GET /v1/meta`の`build_info.git_commit`がR75機能コミット`84c592f`以降を含む実行プロセスか確認し、古ければAPIを再起動する。

ミラー・even asphere・偏芯/チルト系で使用するRMS fallback自体の離散性を改善する場合は、粗い探索後の局所連続最適化または多段階refinementが必要で、規模は中と見積もる。ただしCoddington適用範囲拡張とRMS探索改善は既に`doc/reports/issues_backlog.md`の「同軸系の像面湾曲・M/S像面にCoddington方式を実装しmethodを正す」等で管理されているため、新規の重複Issue草案は追加しない。

## 検証

- 現行API直接測定: 2 endpoints、各16 rows、`method=coddington`
- RMS再現測定: 2 endpoints、各16 rows、`method=rms_search`, `search_steps=11`
- 実UI DOM: 現行とRMS強制の両方をP002で取得
- 回帰テスト: `python -m pytest -q tests/test_engine_v2_1.py -k "coddington"`
- 結果: `5 passed, 22 deselected, 1 warning in 1.31s`
- 製品コード変更: なし
