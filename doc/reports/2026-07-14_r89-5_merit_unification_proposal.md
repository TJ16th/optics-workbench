# R89 作業5 Merit Function統一 調査・提案

## 結論

現行Workbench UIは`POST /v1/optics/evaluate`を呼び出しておらず、evaluate応答の`merit.score`、`merit.metrics`、`merit.weights`にコード上依存していない。したがってUI内の表示移行は不要だが、Python利用者・外部API利用者との互換性を考慮し、即時の意味変更ではなく移行期間を設ける案を推奨する。本作業ではproduction codeを変更していない。

## UI参照調査

- `apps/workbench-ui/src/api/engine.ts:67-280`の全endpoint呼び出しを確認した。health、meta、validate、register、preview、各analysis、best-focus、visual-compositeはあるが、`/v1/optics/evaluate`と`/v1/optics/evaluate-batch`はない。
- `apps/workbench-ui/src`およびUI testsに、evaluate responseやMerit型の定義はない。
- `apps/workbench-ui/src/ui/App.tsx:3290`の`termId="merit"`は、trace profilingの`trace_ms`にhelp用語を付けているだけであり、evaluateのmerit値を参照していない。
- `glossary.supplement.ja/en.json`には`relative_illumination_loss`、`constraint_penalty`、`score`の用語があるが、表示コードからのevaluate依存はない。

## エンジン現状

- operand指定時は`optics_engine/optimization.py::_evaluate_operands`が正規化残差の二乗和を返す。
- metrics/preset指定時は`_compute_merit`が旧線形scoreを返す。
- R89作業1・3の`ray_loss_penalty`と`continuous_constraint_penalty`は、どちらの経路にも加算される。
- したがって同じ`merit.score`というフィールドに、入力形式によって異なる意味が残っている。

## 移行案

### 案A: 即時統一

`merit.score`を常に`sum(residual^2) + penalties`へ変更し、`metrics`と`weights`を診断情報へ整理する。

- メリット: 25.4節へ最短で一致し、意味が一つになる。
- デメリット: 外部利用者のscore比較・閾値・ランキングを予告なく壊す。presetのtarget/tolerance定義が先に必要。

### 案B: 1リリースだけdual response（推奨）

`merit.score`を新残差二乗和へ統一し、旧値を`legacy_merit`へ移す。`legacy_merit`には廃止予定versionをmetadataで明示し、次のschema major/minor境界で削除する。

- メリット: 仕様準拠の標準入口を確立しつつ、外部クライアントが旧ランキングを比較・移行できる。
- デメリット: 移行期間中は応答が二重になり、ドキュメントとテストも二系統必要。

### 案C: 新フィールドを先行追加

既存`merit`を旧形式のまま残し、`residual_merit`を追加する。後のversionで名称を反転する。

- メリット: 最も後方互換性が高い。
- デメリット: 正式フィールド`merit`が仕様不一致のまま残り、利用者が新旧を選び間違えやすい。

## 推奨手順

1. 各presetをoperand template（target、tolerance、weight、one_sided）として定義し直す。
2. 案Bを採用し、`merit.score = sum(residual^2) + ray_loss_penalty + continuous_constraint_penalty + hard penalty`へ固定する。
3. 旧`_compute_merit`出力を`legacy_merit`へ隔離し、API schema versionとREADME互換性注記を更新する。
4. evaluate/evaluate-batch、全preset、infeasible、ray loss、constraintを同じ導出関数で列挙駆動テストする。
5. Workbench UIが将来evaluateを利用するときは、新`merit.score`だけを型定義し、`legacy_merit`へ依存しない。

## 根拠

- UI検索: `rg`による`merit.score`、`merit.metrics`、`merit.weights`、`/v1/optics/evaluate`の参照確認
- エンジン検索: `MeritResult`、`_compute_merit`、`_evaluate_operands`、penalty加算箇所
- production code変更: なし
