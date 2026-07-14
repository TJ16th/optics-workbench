# R102：evaluate内の同一条件trace共有による性能回帰修正 指示書（Codex向け）

## 背景

R96調査で、spec-like smoke benchmarkの`fast_design_score`がclean R82基準（`10584e1`、19.633ms）比で現行`0bac84b`にて**+60.6%（31.538ms）の永続的な性能回帰**と確定した。原因は実測で以下の2点に特定済み。

1. **R89-1**（R88比+66.9%）：`_ray_loss_operands()`が仕様上必須の`ray_loss_ratio`を算出する際、既存のmetric traceと同一のfield・wavelength・sampling・configurationであっても`trace_forward()`を独立に再実行している。
2. **R90**（R89-4比+21.0%）：merit統一で`_evaluate_operands()`がoperandごとに`_metric_scalar_value()`を呼ぶ構造になり、R90以前はRMSとMTFで共有されていたtraceが失われた。relative illumination・ray lossを含め、現行presetは概ね4回traceする。

R96の判定は「`ray_loss_ratio`自体は正しさのための必要コスト、独立再traceとRMS/MTF別traceは最適化余地のある非効率、修正規模は中」。残件はissues_backlog.mdへ「evaluate内の同一条件traceをoperand間で再利用する」として登録済み。本タスクはその実装。

## 作業

1. **request-local評価コンテキストの導入**：1回のevaluate呼び出し内で、trace条件（sampling方式・ray数・field・wavelength・configuration/zoom_position・aimingモード・trace options等、結果に影響しうる全パラメータ）が**完全一致**するoperand間でtrace結果を共有するcacheを実装する。
   - cacheのスコープはrequest-local（1 evaluate呼び出し内）に限定し、呼び出しをまたいで持ち越さない。R82のaffine aiming cache決定論バグの教訓：cacheが決定論を壊す設計にしないこと。
   - cache keyの一致判定は保守的に。条件が完全一致すると確認できる場合のみ共有し、判定できない・部分一致の場合は共有せず従来通り再traceする。「黙って条件の違うtraceを流用する」ことは絶対に避ける（R85/R86で問題化した黙殺パターンの逆方向版になるため）。
2. **R89-1由来の重複解消**：`ray_loss_ratio`算出が、同一条件のmetric traceが既にある場合はそれを再利用するようにする。
3. **R90由来の重複解消**：RMS/MTF等、同一trace条件のoperand同士がtraceを共有するようにする。
4. **効果測定**：`benchmarks/spec_like_benchmark.py --profile smoke`をR96と同じ手法（正順・逆順・再正順の3系列、各warmup 1回・repeat 5回、medianの中央値）で修正前後に実行し、`fast_design_score`の改善幅を実測する。`preview full`・`high-count trace`に副作用（悪化）がないことも確認する。
5. **回帰確認**：既存の全テスト（pytest・Golden・i18n/UI CI）を通すこと。特に以下を確認：
   - 同一requestに対するevaluate結果（merit.score・各operand値・residuals）が修正前後で**ビット同一**であること（trace共有は数値結果を一切変えないはずの純最適化のため）。
   - R91/R93のヤコビアンバッチ経路（J2/J3/J4）が壊れないこと。変数を動かした摂動評価では系の状態が変わるため、cacheが誤って摂動前のtraceを返さないことを明示的にテストすること。
   - R71 Run Charts性能ガード（`run-charts-performance.spec.ts`）の通過。
6. **backlog更新**：実装完了に伴い、issues_backlog.mdの「evaluate内の同一条件traceをoperand間で再利用する」項目を削除または実装済みへ更新する（R95で下書き削除した前例に倣う）。

## 完了条件

- `fast_design_score`がclean R82基準（19.633ms）に近い水準へ改善している（目安：R82比+10%以内。ray_loss_ratio算出自体は正当な追加コストのため完全復元までは必須としないが、実測値と残差の内訳を報告書に明記すること）。
- `preview full`・`high-count trace`に修正起因の悪化がない。
- 同一requestのevaluate結果が修正前後でビット同一であることをテストで確認済み。
- ヤコビアン摂動評価でcacheが誤共有されないことをテストで確認済み。
- 既存全テスト・性能ガード通過。
- ベンチ結果JSON（`bench_results/`）とコミットハッシュが報告書に記載されている。

## 注意

- **本タスクはエンジン側のみ**。`apps/workbench-ui`配下は変更しないこと（R101のUI Phase2リファクタが並行進行中のため、コンフリクトを避ける）。UI側E2Eは実行・確認のみ可。
- trace kernelそのもの（交点計算・aiming）には手を入れない。共有するのは「同一条件のtrace呼び出しの結果」のみ。
- 報告書は`doc/reports/2026-07-15_r102_evaluate_trace_sharing.md`（日付は完了日）へ。着手前に本タスクの規模見積もり（人日換算）を報告書冒頭に記載すること（見積り較正データ収集のため）。
