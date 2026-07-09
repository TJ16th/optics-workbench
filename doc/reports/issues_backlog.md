# Issues Backlog

G5で正式整理するIssue草案の先行メモです。現在のactive指示書で直接カバーされていない項目を列挙します。

## UI: 高密度spot/散布表示のPlotly scattergl対応

ラベル案: `ui`, `performance`

P2-2では、点数の多いspot/散布表示にPlotly `scattergl` を使う規約でした。一方、現状のPhase 2実装は軽量なSVGチャートで構成されています。

現状SVGで実装されている理由:

- 現在のMVPデータ量ではSVGで操作性・表示品質ともに足りている。
- i18nラベル表示とSVG text readbackテストを単純に維持できる。
- Plotly/WebGL化は依存追加、描画LOD、エクスポート、画像・言語検証を伴うため、G3の公開準備中に混ぜるにはスコープが大きい。

提案:

- 今すぐ差し替えず、G5の公開前バックログに正式Issueとして残す。
- 高点数spot/散布だけをPlotly `scattergl` に切り替えるLOD閾値を設計する。
- Optical Layout、光線図、小規模で決定論的なチャートはSVGを維持する。
- WebGL/canvas系のexport制約をREADMEまたはUI内で明示する。

受け入れ条件案:

- 高密度spot cloudがUIをブロックせず描画できる。
- 小規模データは既存SVG表示と同等に安定している。
- ja/enラベルがi18nテストで担保される。
- export可否または代替形式が仕様・README・UIのいずれかで明示される。
