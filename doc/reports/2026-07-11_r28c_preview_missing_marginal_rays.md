# R28c preview missing marginal rays 完了報告

## 実施内容

- P007で`Run Preview`後、Layout Viewにchief rayだけが見え、R27で追加したmarginal ray 2本が表示されない問題を調査した。
- 実ブラウザで`/v1/education/preview`レスポンスを確認し、`metadata.layout_baseline_rays`は27本返っていることを確認した。
  - role: `chief`, `marginal_lower`, `marginal_upper`
  - P007ではmarginal rayが`status: aiming_failed`として返るが、path自体は表示可能な部分経路を持っていた。
- UI側の`layoutBaselineRayItems()`が`status === "alive"`のみを描画対象にしていたため、`aiming_failed`のmarginal rayがSVG DOMから除外されていたことを原因として特定した。
- baseline layerは通常のdensity rayではなく、Layout View用の補助基準線なので、`alive`または`aiming_failed`で2点以上のpathを持つものを描画対象に変更した。
- SVGに`data-baseline-status`を追加し、E2Eで`aiming_failed`のmarginal rayがDOMに存在することを明示的に確認できるようにした。

## 検証結果

- `npm.cmd run ui:build`
  - 成功
- `npm.cmd run ui:e2e -- --grep "layout baseline chief|P007 fast meniscus|layout scale stable after preview"`
  - `3 passed`
- `npm.cmd run ci`
  - `ui:build` ok
  - `i18n:check` ok (`176 keys`)
  - `i18n:coverage` ok
  - `i18n:test` ok
  - `svg:export:test` ok
  - `chart:test` ok
  - `ui:e2e` ok (`24 passed`)

## ブラウザ確認

- P007で`Run Preview`後のLayout Viewを確認した。
  - `data-baseline-rays = 27`
  - `data-density-rays = 27`
  - `data-displayed-rays = 54`
  - `data-total-rays = 81`
  - baseline role: `chief`, `marginal_lower`, `marginal_upper`
  - baseline status: `alive`, `aiming_failed`
  - marginal ray count: `18`
- スクリーンショット: `doc/images/r28c-p007-preview-baseline-rays.png`

## 仕様・指示書との差分

- `/v1/education/preview`のリクエストオプション不足ではなかった。UIは`include_layout_baseline_rays: true`を送っており、APIもbaseline dataを返していた。
- API/engine側の変更は不要だったため、今回の修正対象外とした。
- density layerの表示条件は変更せず、baseline layerだけを対象に修正した。
