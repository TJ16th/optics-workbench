# P3進行確認フォローアップ2：非球面表示確認とaperture runtime化

曲率描画修正（follow-up curvature）を確認した。球面の凸/凹描画・符号は正しく実装され、E2Eでも確認済み。次に以下2点を進める。

## 作業1：非球面sag描画の視覚確認

現在、非球面（`aspherical_even`）のsag描画コードは追加済みだが、確認用プリセットが無いため視覚検証ができていない。

1. 最小の非球面確認手段を用意する。以下のどちらかを選び、理由とともに報告する：
   - (a) 既存プリセットのいずれか（例：P001やP004候補）に、非球面を1面追加した確認用バリアントを一時的に用意する（本採用プリセットを変更するのではなく、開発・視覚確認用の小さなfixtureとして）。
   - (b) `doc/reports/issues_backlog.md` にP004プリセット追加のIssueが既に登録されているので、そちらの実装を前倒しし、P004（簡易ダブルガウス。非球面を含む可能性がある場合）を使う。
2. 非球面のsag形状が、球面（conic=0近似）と視覚的に異なる曲線として描画されることを確認し、スクリーンショットを `doc/images/` に追加する。
3. conic定数を変えた場合（例：放物面 k=-1）に形状が変化することも確認できると良い（必須ではない）。
4. 確認用に一時的なプリセット変更をした場合、本タスク完了後に元に戻すか、正式なプリセットとして残すかを明記する。

## 作業2：Aperture操作のruntime configuration化（followup_checkの確認2）

`codex_ui_phase3_followup_check.md` の確認2に対応する。

1. 対象プリセット（P003等）の絞り面定義を確認し、`semi_diameter_mm` が `{ variable: iris_radius_mm, default: ... }` 形式になっているか確認する。なっていなければそのように変更する。
2. P3-3の実装（system再登録方式）を、`configuration.variables.iris_radius_mm` を送るランタイム方式に変更する。P3-2のgroup shiftと同じ「既存登録済みsystemを使う」経路に揃える。
3. 変更後、P3-5と同条件（fields=3, wavelengths=3, repeats=20等）でaperture操作のレイテンシを再計測し、変更前（drag: 30.025ms, commit: 31.474ms、HTTP median）との比較を報告する。
4. 関連E2E（`-g "aperture slider"`）を再実行し、system再登録が発生しなくなったことを確認する（例：`system_dirty`や新規`system_id`発行が起きないことをテストで固定する）。

## 完了条件

- 非球面sagカーブの視覚確認結果（スクリーンショット）が報告されている。
- apertureのruntime化が完了し、レイテンシ改善が数値で示されている。

## この後

両方完了したら、P3-6（Phase 3受け入れ確認）に進んでよい。
