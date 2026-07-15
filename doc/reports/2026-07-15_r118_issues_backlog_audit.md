# R118 issues_backlog全件監査

## 結論

`doc/reports/issues_backlog.md`の`## Issue:` 42件を全件確認した。backlog本体は指示どおり変更していない。

- 維持: 34件
- 実装済み削除候補: 6件
- 前提陳腐化による削除または書き換え候補: 1件
- 重複統合候補: 1組
- active work orderで実装予定: 2件（R121、R122。完了までは削除しない）

優先度は依存関係、仕様不整合、数値正しさ、利用者影響を基準にした監査時点の提案である。

## 全件台帳

| No. | 項目 | 登録由来 | 現状 | 優先 | 判定 |
|---:|---|---|---|---|---|
| 1 | Snapshot zip export [#1] | G5/P2 | 単一JSONのみ。新規R122 activeで実装予定 | 高 | 維持。R122完了後に再判定 |
| 2 | Snapshot比較のチャート重ね合わせ [#2] | G5/P2 | Compareはsummary/table中心 | 中 | 維持 |
| 3 | Raw JSON/YAML advanced editor [#3] | G5/P2 | raw表示はあるが編集round-tripなし | 中 | 維持 |
| 4 | P004プリセット追加 | P3-0 | R66以前にP004実装済み。EFL/F値/API/E2E回帰あり | - | **削除候補** |
| 5 | PNG export画像比較 [#4] | G5 | PNG出力はあるが画像比較CIなし | 中 | 維持 |
| 6 | Plotly scattergl [#5] | P2-2/G3 | 高密度spotもSVG。LOD/WebGL未実装 | 中 | 維持 |
| 7 | supplement glossary統合 [#6] | G5 | ja/en supplementが現存 | 中 | 維持。人間レビュー依存 |
| 8 | axis_convention import/export [#7] | G5 | 内部+Xのみ。外部Z軸変換なし | 中 | 維持 |
| 9 | variable binding registry | follow-up3/R85 | 一般variable処理は拡張されたがCompiledSystem registry/debug metadataなし | **高** | 維持 |
| 10 | 回折PSF・波面・FFT瞳 [#8] | G5/R73 | 幾何PSF/MTFのみ。R119でR111設計を整理予定 | 高 | 維持 |
| 11 | 視覚系プリズム・正立像 [#9] | Phase 8 | 簡約模型眼はあるがプリズム/左右像反転なし | 中 | 維持 |
| 12 | job/WebSocket [#10] | G5 | 同期HTTPのみ | 低 | 維持 |
| 13 | mechanical_diameter_mm | R2 | 未実装 | 中 | 維持 |
| 14 | edge_thickness metric | R2/R85 | R89-3 `19867e2`でoperand/API/constraint実装済み | - | **削除候補** |
| 15 | optimization multi-configuration | R3 | 単一configuration中心。複数position同時評価なし | **高** | 維持 |
| 16 | 有限距離物体Workbench UI | R9/R36/R98 | 直接kernel検証はあるがfield editor/API標準導線なし | 中 | 維持 |
| 17 | field角とsensor/EFL可視化 | R9/R36 | 推奨field既定値は整備済みだが関係可視化なし | 中 | 維持 |
| 18 | OIS群シフト時の有効径評価 | R13 | 簡易警告のみ。全field/瞳の定量評価なし | 中 | 維持 |
| 19 | 撮影結果シミュレータ | R14 | 未実装 | 低 | 維持 |
| 20 | 連続スペクトル色収差 | R15 | 離散波長weightのみ | 低 | 維持 |
| 21 | 面反射ゴースト | R16 | 未実装 | 中 | 維持 |
| 22 | コート特性・CCI | R17 | 未実装。ゴーストモデル依存 | 低 | 維持 |
| 23 | ズーム/フォーカス撮影sim | R18 | 未実装。No.19の特殊化 | 低 | **No.19との統合候補** |
| 24 | 3D/STL出力 | R19 | 未実装 | 低 | 維持 |
| 25 | 解析条件・表示設定preset | R20 | R117はpanel配置保存のみ。条件セットの名前付き保存なし | 中 | 維持 |
| 26 | Layout代表光線のsampling依存説明 | R26 | R27でsample数非依存baselineを導入。sampling依存なのは任意density layerのみ | 低 | **削除またはdensity説明へ書換候補** |
| 27 | P005/P006 NaN serialization | R29 | R32で再帰`null`正規化と全preset HTTP回帰を実装 | - | **削除候補** |
| 28 | afocal＋模型眼・網膜評価 | R34/R68 | R69で簡約Gullstrand、instrument/retinal compositeを実装 | - | **削除候補**。高精度眼モデルは別件 |
| 29 | 後続実体面から中央遮蔽を自然導出 | R49/R53 | 専用annulus面が必要。自動導出なし | 中 | 維持 |
| 30 | 固定内径遮蔽annulus | R49 | engine遮光、R47編集、R58断面表示、回帰が揃う | - | **削除候補** |
| 31 | 可変位置・可変径mechanical_aperture | R49 | group移動は可能、configuration別径overrideなし | 中 | 維持 |
| 32 | rectangle aperture | R49 | 未実装 | 中 | 維持 |
| 33 | polygon/花形 aperture | R49 | 型予約のみ、kernelはNotImplementedError | 低 | 維持 |
| 34 | 3D rayと2D断面投影差の明示 | R60 | X-Y表示のみ。Y/Z/radius inspectorなし | 中 | 維持 |
| 35 | Coddington適用範囲 | R74 | R75で球面/平面/薄レンズ完了。mirror/even asphereはRMS fallback | 中 | 維持。残件へ題名を狭めるとよい |
| 36 | 周辺光量専用sampling/metadata | R74 | R75-2 `66f2ef3`で1000 rays、専用request、metadata、精度回帰を実装 | - | **削除候補** |
| 37 | 適応的収束sampling | R74 | 設計のみ。固定1000 raysが現行 | 中 | 維持 |
| 38 | ArtifactStore短TTL flaky | R74 | 20 ms実時間TTLテストと`time.time()`依存が現存 | 中 | 維持 |
| 39 | P011 full aiming収束 | R67/R80/R94/R116 | R116でLayout baselineは0件。通常225-rayは`213 alive / 12 aiming_failed`のまま | **高** | 維持。baseline完了を追記して範囲を狭める |
| 40 | Jacobian warm適用判定/profiling | R91/R96 | warm実装・性能調査済みだがcandidate別判定/内訳なし | 中 | 維持 |
| 41 | 全analysis endpointのconfiguration統一 | R106 | trace/spot/MTF等は対応、chromatic/exit-pupil/eye-box/telescope等に欠落 | **高** | 維持 |
| 42 | named Position Manager＋snapshot runtime config | R106 | R121で実装予定 | **高** | 維持。R121完了後に再判定 |

## 削除候補の根拠

1. **P004**: `apps/workbench-ui/src/domain/presets.ts`に存在し、`tests/test_preset_api_smoke.py`とUI E2Eで固定済み。
2. **edge_thickness**: R89-3報告と`tests/test_r89_work3_edge_constraints.py`が受け入れ条件を直接満たす。
3. **P005/P006 NaN**: R32報告と全preset HTTP smokeがpreview/trace JSON境界を固定する。
4. **模型眼接続**: R69で簡約Gullstrandと網膜spot/PSF/MTFを実装済み。曲面網膜・眼分散等は元Issueの完了を妨げず、別の高精度化テーマである。
5. **固定annulus**: R47/R58/R59により編集、断面表示、trace遮光、density整合が揃う。
6. **周辺光量専用sampling**: R75-2で要求条件・実使用条件・放射量方式metadataと精度比較を実装済み。
7. **Layout sampling説明**: R27が問題となった代表線を固定baselineへ置換した。density layerの説明だけが必要なら、元Issueを残すより題名と受け入れ条件を書き換える方が正確である。

## 重複・依存関係

- 「撮影結果シミュレータ」と「ズーム/フォーカス時の撮影シミュレーション」は基盤と特殊化の関係が強い。後者を前者のmilestone/受け入れ条件へ統合する案を推奨する。
- Coddington、周辺光量固定sampling、適応samplingは重複ではない。R75で前2件の一部/全部が進み、適応samplingはその後段である。
- 後続実体面の中央遮蔽自動導出と固定annulusは代替表現であり、重複ではない。前者は未実装、後者は実装済みである。
- R116はP011のLayout表示を直したが、通常評価bundleの物理到達不能光線を正しいstatusへ分類する残件は維持される。

## 推奨アクション

backlog本体を人間レビューで更新する際は、削除候補7件を一括で機械削除せず、`[issue: #N]`付き項目は対応するGitHub Issueの状態を確認してから閉じる。No.1とNo.42はactive work orderの完了報告後に再監査する。No.23はNo.19へ統合し、No.35とNo.39は完了済み範囲を背景へ追記して残件だけへ狭めるのがよい。
