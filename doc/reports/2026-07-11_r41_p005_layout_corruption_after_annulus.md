# R41 P005 annulus後のLayout View崩れ修正

## 原因

R40で追加したannulus STOPは、エンジンとUIの面X座標計算を破壊していなかった。実座標は `STOP=0 mm`、`M1=80 mm`、`M2=-570 mm`、`IMG=480 mm` であり、M1からM2は `-650 mm`、M2からIMGは `1050 mm` を維持している。

表示崩れの主因は `LayoutView` の光線Y倍率が固定の `4 px/mm` だったことにある。P005の半径100 mmの周辺光線はY方向に400 pxとして描かれ、SVGの高さ340 pxを大きく越えたため、画面上下へ飛び出して見えた。さらにR40のSTOPからM1まで10 mmはX表示で約6 pxとなり、両者が重なって見えた。

## 修正

- 光線Y倍率を最大有効半径に対して `min(4, 92 / largestSemiDiameter)` とし、面の表示高と同じ上限に収めた。P005では `0.92 px/mm` となる。
- P005の入口STOPをM1の80 mm手前に置いた。M1–M2、M2–IMGの鏡間隔は不変である。
- Layout Viewへ `data-vertex-x-mm` と `data-ray-y-scale` を追加し、面位置と表示倍率をE2Eで直接検証できるようにした。
- P005のコンパイル済み面座標と鏡間隔をPython回帰テストへ追加した。

## 実画面確認

ローカルAPI/UIに対するヘッドレス実ブラウザ確認で、P005の全9本の基準光線のSVG bounding boxが `0 <= y` かつ `y + height <= 340` を満たした。STOP、M1、M2、IMGは光軸上に描画され、光線は `STOP -> M1 -> M2 -> IMG` の順に画面内で折れ、annulus中央遮蔽も維持された。

## R40で検出できなかった理由と再発防止

R40のUI E2Eモックは、面位置を `surfaceIndex * 3`、光線高さを最大 `1.5 mm` の人工値で返していた。このため大口径P005の実座標・実光線高さでは起こる範囲外描画を再現できなかった。

今回、P005について以下を回帰テストへ固定した。

- UI E2E: STOP/M1/M2/IMGの頂点X座標、annulus中央遮蔽、`data-ray-y-scale=0.92`
- Python: P005のコンパイル済み面座標、およびM1–M2とM2–IMGの間隔

## 検証

- `python -m pytest -q`: `86 passed, 1 skipped`
- `npm run ci`: `27 passed`
- 実ブラウザP005確認: 全基準光線のSVG bounding boxが表示範囲内
