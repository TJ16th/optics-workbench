# R131：公開push実行 指示書（Codex向け）

## 背景

R130のpush承認サマリーを人間がレビューし、**pushを明示承認した**（2026-07-16、PIIスキャンの例外付きOK判定を含めて承認）。本タスクはその実行。

## 作業

1. push前確認：HEADがR130報告時点の系譜（`170ef68`を含む）であること、`origin/master..HEAD`がR130報告と整合すること（本指示書等のドキュメントコミットが増えている分は許容、feat/fix等の新規実装コミットが増えていた場合は中止して報告）。
2. `git push origin master`を実行する（force禁止）。
3. push後確認：`git rev-list --left-right --count origin/master...HEAD`が`0 0`であること。GitHub上でCI（GitHub Actions）が起動した場合はその結果も確認し、失敗時は原因を調査・報告する（G7の前例あり）。
4. **Issue #25のclose**：P004実装済み（`5e5160b`）を根拠に、コメント付きでcloseする（`gh` CLI等で可能な場合。不可能な環境なら「人間がGitHub上でclose」と報告に明記して人間へ委ねる）。
5. 報告書：push実行結果、push後のorigin/master先端ハッシュ、Actions CI結果、Issue #25の処理結果。

## 完了条件

- push成功、`0 0`確認、リモートCI結果の確認（または起動なしの確認）。
- 報告書：`doc/reports/2026-07-16_r131_push_execution.md`。

## 注意

- force push・履歴書き換え・rebase禁止。
- push後にリモートCIが失敗した場合、修正コミットの作成は行わず原因報告まで（修正は別途発注）。
