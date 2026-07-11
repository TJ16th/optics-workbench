# R28b後続：プレビュー実行後、marginal光線が表示されない問題 指示書（Codex向け）

## 背景

R28bでLayout Viewのスケール圧縮は解消されたが、人間が実際にP007で「プレビュー実行」した結果を見ると、赤い光線が1本（chief rayと思われる太い実線）しか表示されておらず、R27で実装したmarginal光線（上端・下端、破線2本）が見当たらない。薄いグレーの光線（density layer相当）は数本見えている。

R28bの完了報告・テストは、Layout Viewの「スケール」（surface位置・幅・高さ）の安定性は確認しているが、baseline layer（chief 1本＋marginal 2本）の**本数・表示有無**までは明示的に確認していない。スケール修正の過程で、baseline layerの描画条件（R27で実装した`layout_baseline_rays`メタデータの参照）が意図せず崩れた可能性がある。

## 作業

1. 実際にP007で「プレビュー実行」した際の`/v1/education/preview`レスポンスに、`metadata.layout_baseline_rays`が含まれているか確認する（R27の実装では`store_path`かつ`include_layout_baseline_rays`が明示された場合のみ返す設計だった。プレビュー実行時のリクエストがこのオプションを正しく指定しているか確認する）。
2. レスポンスに含まれていれば、UI側がそれを正しく読み取ってbaseline layer（chief実線・marginal破線2本）を描画しているか確認する。R28bのXスケール修正で、baseline layerの描画条件分岐に影響が及んでいないか確認する。
3. レスポンスに含まれていなければ、「プレビュー実行」のリクエストパスが`include_layout_baseline_rays`オプションを送っていない可能性がある。静的表示（Analysisタブ等）のリクエストと比較し、オプション指定の有無の差を確認する。
4. 原因を特定し修正する。
5. 修正後、P007で「プレビュー実行」時に、chief ray（太い実線1本）とmarginal ray（破線2本、上下）が常に表示されることを確認する（スクリーンショット添付）。
6. P001〜P006でも同様に、プレビュー実行時にbaseline layerが表示されることを横断確認する。
7. 今回の問題（baseline layerの表示有無がE2Eで明示的にカバーされていなかった）を踏まえ、density layerの本数確認だけでなくbaseline layer（chief/marginal）の存在確認も含めたE2Eを追加する。

## 完了条件

- プレビュー実行時に、chief ray・marginal ray（上下2本）が常に表示される。
- P001〜P007で横断確認済み。
- baseline layerの表示有無を明示的に確認するE2Eが追加されている。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを確認し、断定形で報告に記載する（未来形で締めない）。
