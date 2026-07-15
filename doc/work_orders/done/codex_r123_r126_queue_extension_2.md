# R123〜R126：連続作業キュー拡張2 指示書（Codex向け）

## 背景

R118/R119の人間レビューが完了し、以下が承認された。本指示書は連続作業キューの**末尾への追加**（R122の後に記載順で直列実行）。キュー運用ルール（直列・タスク別コミット・amend禁止・push禁止・バッチ実行モード・判断要時は提案待ちスキップ・完了主張への対象範囲列挙）をすべて適用する。

---

## R126：解析実行中の進捗表示・非ブロッキング化（UI側MVP）

人間の新規指摘：「解析中、画面がフリーズする。『解析中。何パーセント』とか出ると親切」。

**スコープ判断（承認済み）**：単一解析内の真のパーセント表示はエンジン側の非同期job/進捗API（backlog「長時間job/WebSocket」）が必要なため本タスク対象外。**UI側で可能な範囲のMVP**を実装する：

1. **実行中もUIを操作可能に保つ**：Run Charts等の実行中にUIスレッドがブロックされる箇所を特定し、解消する（リクエストは既に非同期のはずなので、ブロックの実態＝大量データの同期描画・re-render等を計測して特定すること。原因の計測結果を報告書に記載）。
2. **パネル単位のloading表示**：R117のchart workspace各パネルへ、実行中スケルトン/スピナー＋当該チャートの経過秒数を表示。
3. **粗い進捗表示**：Run Charts全体で「N個中M個完了」のカウンタを表示（workspaceの解析エンドポイント呼び出し数を分母とする）。全体経過時間も表示。
4. **実行中のキャンセル**：既存のAbortController等でリクエスト中断ができるなら「キャンセル」ボタンを追加。仕組み上困難なら理由を報告し未実装でよい。
5. E2E：実行中にパネルloading表示が出ること、完了カウンタが進むこと、実行中に他タブ（System等）へ遷移できること。
6. **将来の真のパーセント表示**について：エンジン側job/進捗APIの要件（どのendpointが長時間か、進捗の粒度候補）を報告書の提案節へ記載し、backlog「長時間job/WebSocket」項目へ追記する。
- 報告書：`doc/reports/2026-07-15_r126_analysis_progress_ui.md`

## R123：R108案B実装（整合プレビュー付き適用、Y/Z個別対応）

R119提案の**案Bを承認済み**。`Fit fields to sensor`は**Y/Z個別対応まで含める**（承認済み）。R119報告の設計に忠実に実装する：

1. Analysisの`Image plane policy`パネルへ`Align`コマンドを追加。実行時は変更せず、プレビュー（現在値・solve値・差分・solve status、focus/field fit/real imageの3項目分離表示、R119の閾値案と使用基準の明示）を表示。
2. `Preserve field angles`（既定）＝最終gapのみ更新／`Fit fields to sensor`＝sensor寸法維持でY/Z各方向の最大angular fieldを近軸逆算、中間fieldは最大fieldに対する既存比率を維持。
3. 適用→system dirty→再validate/register、旧結果はstale表示。プレビュー自体は永続化しない。
4. 新endpoint不要：既存`/v1/solve/paraxial-image-distance`＋`/v1/analysis/paraxial`を順に呼ぶ。afocal系・solve失敗・負gap・非空気最終区間・sensor不在は適用不可とし、エンジンの構造化issueをそのまま表示。
5. E2E：プレビュー表示、Preserve適用でgapのみ変化、Fit適用でY/Z field変化＋比率維持、afocal系での適用不可表示。
- 報告書：`doc/reports/2026-07-15_r123_align_command_implementation.md`

## R124：R111案A・A1実装（幾何PSFの製品契約固定）

R119提案の**案A・A1着手を承認済み**。A2以降（trace契約変更を伴うOPL・回折）は本タスク対象外（別発注）。

1. 既存`analyze_geometric_psf`を土台に、geometric modeの表示・API契約を固定：正規化・重心・pixel/grid範囲・ray loss・単位・artifact metadata（R119のA1定義）。
2. UIのAnalysis workspace（R117）のchart picker候補へ`PSF (Geometric)`を追加。**`Geometric`表記とdiffraction_included: falseの明示を必須とする**（既存MTFの脚注と同じ流儀）。
3. R119検証ゲート1を実装：同一traceからのビット同一、energy正規化、平行移動時の重心不変形状、ray loss metadataをテスト固定。
4. capabilitiesの`diffraction_psf=false`は変更しない。
5. エンジン側の変更は「既存幾何PSFの契約明確化・metadata追加」の範囲に限る（trace kernel・数値結果の変更は不可。既存PSF数値が変わる場合は理由と差分を定量報告）。
- 報告書：`doc/reports/2026-07-15_r124_geometric_psf_a1.md`

## R125：issues_backlogクリーンアップ（R118監査の実行）

**R121・R122の完了後に実施**（両タスクでbacklog2件が削除候補化するため、その再判定込み）。R118報告の推奨アクションに従う：

1. 削除候補6件（P004・edge_thickness・NaN・模型眼・固定annulus・周辺光量sampling）＋R121/R122完了分を処理。**`[issue: #N]`付き項目は、対応するGitHub Issueの状態を確認してから閉じる**（`gh` CLI等で確認できない環境なら「要人間確認」として残し、その旨を報告）。
2. No.23（ズーム撮影sim）をNo.19（撮影シミュレータ）のmilestone/受け入れ条件へ統合。
3. No.26をdensity layer説明の項目へ書換。No.35（Coddington）・No.39（P011通常束の分類）は完了済み範囲を背景へ追記し残件だけへ狭める。
4. 変更前のbacklog全文をgit履歴で参照可能に保つ（通常コミットで良い）。変更一覧（削除・統合・書換の対応表）を報告書に記載。
- 報告書：`doc/reports/2026-07-15_r125_backlog_cleanup.md`

---

## 共通の完了条件

- 各タスク：`npm run ci`／エンジンテスト（該当時）全通過、スクリーンショット（UI変更時）、build_info一致確認、報告書冒頭に着手前見積もり、完了主張への対象範囲列挙。
- R123/R126はUI側のみ（エンジン変更不可）。R124のみエンジン側の契約明確化を許可（上記制限内）。
