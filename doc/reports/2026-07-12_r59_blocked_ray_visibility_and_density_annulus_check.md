# R59 blocked ray可視化／density annulus整合性 調査報告

## 結論

- Part 1: 「`blocked`を理由によらず一律非表示」という指示書の前提は現行実装には該当しない。baselineは`alive`、`aiming_failed`、`blocked`のいずれもpathが2点以上なら描画する。P005のM1で遮光された2本も実DOMに存在した。
- Part 2: density rayはannulus制約を正しく尊重しており、不整合はなかった。コード修正は不要である。

## Part 1: blocked ray

### コード確認

`apps/workbench-ui/src/ui/App.tsx`の`layoutBaselineRayItems()`は次を描画対象とする。

```text
(alive | aiming_failed | blocked) and path.length >= 2
```

この条件はR33で追加済みだった。一方、通常のdensity layerを生成する`layoutRayItems()`は`alive`かつ2点以上のみを描画する。

### P005 baseline実測

recommended field、`587.56 nm`、`ray_aiming.mode=full`で9本を確認した。

| field | role | status | path長 | 終端 | UI DOM |
|---|---|---|---:|---|---|
| center | chief | blocked | 1 | STOP | 非表示 |
| center | marginal_lower | alive | 4 | IMG | 表示 |
| center | marginal_upper | alive | 4 | IMG | 表示 |
| mid-y | chief | blocked | 1 | STOP | 非表示 |
| mid-y | marginal_lower | alive | 4 | IMG | 表示 |
| mid-y | marginal_upper | blocked | 2 | M1 | 表示 |
| edge-y | chief | blocked | 1 | STOP | 非表示 |
| edge-y | marginal_lower | alive | 4 | IMG | 表示 |
| edge-y | marginal_upper | blocked | 2 | M1 | 表示 |

集計は次の通り。

- STOPで即遮蔽、1点path: 3本
- M1で遮蔽、2点path: 2本
- IMG到達、4点path: 4本
- 実DOM baseline: 6本（alive 4本、blocked 2本）

DOM上のblocked 2本はいずれも`marginal_upper`で、field index 1/2、SVG pathは2セグメントを持っていた。したがって意味のある部分軌跡は既に可視化されている。

### 可視化方針案

1. 現状維持: 部分pathは表示できている。要素追加がなく最も静かな表示だが、aliveとblockedを線だけでは判別できない。
2. 専用線種: `blocked` baselineを短い破線または低彩度にし、終端に小さな`x`を付ける。遮光位置が明確になるため推奨案とする。
3. 操作時のみ強調: 通常は現状表示、光線選択・フォーカス時にstatusと終端面をToggletipで示す。情報量は抑えられるが、常時の判別性は上がらない。

本タスクのスコープに従いUI変更は行っていない。実装する場合は、density rayのblocked表示とは分けて判断する必要がある。多数のdensity blockedを常時表示するとLayout Viewが過密になるためである。

## Part 2: density ray

P005のrecommended field 3点に対し、`hexapolar`、full aimingで`9 samples/field`と`25 samples/field`を検証した。

Annulusの通過判定は`abs(Y)`ではなく半径`r=sqrt(Y^2+Z^2)`で行う必要がある。例えば`Y=0, Z=60.827625 mm`は`abs(Y)<40 mm`でも、半径`60.827625 mm`なので有効な開口帯内である。

| samples/field | field | alive | blocked | STOP半径min (mm) | STOP半径max (mm) | 範囲外alive |
|---:|---|---:|---:|---:|---:|---:|
| 9 | center | 9 | 0 | 40.000000 | 76.157731 | 0 |
| 9 | mid-y | 9 | 0 | 40.000000 | 76.157731 | 0 |
| 9 | edge-y | 9 | 0 | 40.000000 | 76.157731 | 0 |
| 25 | center | 25 | 0 | 40.000000 | 95.219046 | 0 |
| 25 | mid-y | 25 | 0 | 40.000000 | 95.219046 | 0 |
| 25 | edge-y | 25 | 0 | 40.000000 | 95.219046 | 0 |

全102本のalive density rayが`inner=40 mm`から`outer=100 mm`の範囲内だった。範囲外を通過してaliveとなる光線は0本であり、density samplingと実traceのannulus制約は整合している。

## 検証根拠

- 調査対象コード基準: `aa1aea7244ac50c8ea91cb9b2e7288a583ac131c`（短縮形: `aa1aea7`、`fix(ui): unify stop aperture segments (R58)`）
- ライブラリ実trace: P005、recommended field、9/25 samples、full aiming、path保存
- 実UI DOM: `http://127.0.0.1:5173/`、P005 Preview、baseline 6本、うち`blocked` 2本
- 稼働APIの`build_info.git_commit`: `aa1aea7`（調査対象コードと一致）

本タスクは調査・報告のみでコード変更がなく、pytest、UI CI、プロセス再起動、スクリーンショット保存は完了条件の対象外である。
