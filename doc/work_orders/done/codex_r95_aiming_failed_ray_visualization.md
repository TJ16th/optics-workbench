# R95：Layout ViewでのaimingF_failed光線の視覚的明示 指示書（Codex向け）

## 背景

R94の調査で、P011のPreview Layout Viewで途中終端して見える光線は、既存backlog項目（P011の周辺fieldでfull aiming収束失敗、R67/R80/R81既知）と同一原因のbaseline ray（`aiming_failed`）であることが確定した。あわせて、表示側の別課題も判明した：`blocked`光線はgray短破線＋終端×マーカーで明示される（R60）一方、`aiming_failed`光線には専用の視覚表現が無く、通常の波長色・marginal破線と見分けがつかず「誤解を招く」表示になっている。この課題はissues_backlog.mdへ「Layout Viewでaiming_failed baseline光線を明示する」として登録済み（規模小〜中）。

本タスクはこの表示課題を修正する。**エンジン側のaiming収束失敗そのもの（なぜ収束しないか）の根本原因調査・修正は本タスクの対象外**（別途扱う）。

## 作業

1. Preview Layout Viewで、`aiming_failed`のbaseline rayに専用の視覚表現を追加する。`blocked`（R60：gray短破線＋終端×マーカー）とは意味が異なる（blockedは物理的な遮光、aiming_failedは収束計算の失敗）ため、区別できる別の表現（色・マーカー形状等）にすること。既存の凡例（光線種別）にも追加する。
2. R73作業4でAnalysisタブのRay Fan/Longitudinal Aberrationパネルに追加したaiming_failed件数のCarbon warning表示と同様の警告表示を、Previewタブにも追加する（R94で「Previewには表示されない」と確認済みの欠落を埋める）。
3. P011を使ったE2Eテストを追加し、①aiming_failedの光線が専用の視覚表現で描画されること②Previewタブに警告が表示されること、を固定する。
4. 既存のblocked光線の表示・凡例には影響を与えないことを確認する。

## 完了条件

- P011のPreview Layout Viewで、aiming_failedのbaseline rayが、健全な光線ともblocked光線とも視覚的に区別できることが、スクリーンショットとDOM実測で示されている。
- 凡例に新しい表現が追加されている。
- Previewタブにaiming_failed件数の警告が表示されることが確認されている。
- 新規動作を固定するE2Eテストが追加され、既存テストとあわせて全てグリーンである。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを断定形で記載する（未来形で締めない）。
- **完了報告の実装根拠には、コミットメッセージだけでなく実際のコミットハッシュ値を必ず併記する。**

## 注意

- P011のaiming_failedそのものの根本原因調査・修正は本タスクの対象外。表示上の明示化のみを行う。
- 「区別できる」という主張は、目視ではなく必ずDOM実測（class名・color値等）で裏付けること。
