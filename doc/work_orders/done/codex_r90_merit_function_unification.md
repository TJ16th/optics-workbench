# R90：Merit Function統一の実装（25.4節） 指示書（Codex向け）

## 背景

R89作業5の調査で、現行Workbench UIが`/v1/optics/evaluate`・`/v1/optics/evaluate-batch`を一切呼んでおらず、旧`merit.score`（線形weighted score）形式へのUI依存がゼロであることが確認された。これによりmerit統一のUI破壊リスクは無いと判断できる。一方、外部API利用者への配慮から、R89作業5は「Plan B：1リリースだけ新旧を併記してから旧形式を削除する」移行案を推奨している。本タスクはこの推奨案を実装する。

## 作業

1. 各presetの評価条件を、operand template（target・tolerance・weight・one_sided）として定義し直す。
2. `merit.score`を`sum(residual^2) + ray_loss_penalty + continuous_constraint_penalty + hard penalty`（25.4節の定義、R89作業1・3で追加したpenaltyを含む）へ統一する。
3. 旧`_compute_merit()`が返していた線形weighted scoreの出力を、`legacy_merit`フィールドへ隔離する。廃止予定であることをAPI応答のmetadata（例：deprecation notice、対象schema version）で明示する。
4. `evaluate`・`evaluate-batch`の両方、全プリセット、infeasible系、ray loss系、constraint系を、同一のderivation関数を通した列挙駆動テストで検証する。
5. API schema versionとREADME等の互換性注記を更新する（該当箇所があれば）。
6. 現行Workbench UIがevaluate系を呼んでいないことを再確認し、本タスクによる変更がUIに影響しないことを確認する。

## 完了条件

- `merit.score`が25.4節の定義（残差二乗和＋penalty）で統一され、複数プリセット・複数条件でAPI実測により確認されている。
- 旧形式が`legacy_merit`として引き続き取得可能であり、廃止予定である旨がAPI応答から分かるようになっている。
- 列挙駆動テストで、evaluate・evaluate-batch・全プリセット・infeasible・ray loss・constraintの組み合わせがカバーされている。
- R82決定論、R87〜R89で追加した機能・回帰テストに影響がないことを確認している。
- 既存テストが全てグリーンである。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを断定形で記載する（未来形で締めない）。
- **完了報告の実装根拠には、コミットメッセージだけでなく実際のコミットハッシュ値を必ず併記する。**

## 注意

- 本タスクはR89作業5の提案（Plan B）をそのまま実装することを基本方針とするが、実装中に不都合が判明した場合は、根拠とともに別案へ変更してよい。
- 「UIに影響しない」という主張は、目視ではなく必ずコード参照（evaluate系endpointを呼んでいないことの再確認）で裏付けること。
