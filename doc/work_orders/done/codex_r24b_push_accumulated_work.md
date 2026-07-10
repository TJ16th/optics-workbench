# R24（差し替え）：大量の未push分の確認とpush

## 背景

`codex_r24_stale_commit_investigation.md`で調査を依頼する前に、人間がGitHubリポジトリのトップページを確認したところ、リポジトリ全体のコミット数が9個のみで、`.github/workflows`を含むほとんどのファイルがG8-push（コミット`4d6ec49`）時点のまま更新されていないことが判明した。

これにより、Create Issues From Backlogワークフローが古いbacklog（10件版）しか処理できなかった原因が判明した：**Q1〜Q6・R1〜R22の一連のタスクが、G8-push以降一度もGitHubへpushされていなかった**ため。AGENTS.mdの「pushは人間の明示承認なしに行わない」規約が忠実に守られた結果であり、バグではない。`codex_r24_stale_commit_investigation.md`が想定していた「ワークフロー内でのref固定」等の調査は不要になった。本タスクはその内容を置き換える。

## 作業

### 1. 未push差分の確認（pushはまだ実行しない）

1. `git fetch origin`を実行する。
2. `git log origin/master..HEAD --oneline`で、ローカルにあってリモートに無い全コミットを一覧化する（Q1〜Q6、R1〜R22相当の全タスクが含まれるはず）。
3. `git diff origin/master..HEAD --stat`で変更ファイル一覧を出す。
4. 現在のHEADの`build_info.git_commit`相当（ローカルの最新コミットハッシュ）を確認する。
5. 上記を完了報告としてまとめ、**ここで一旦停止する。pushはまだ実行しない。**

### 2. 人間の確認後にpush（別途明示的な承認後に実行）

1. 人間から明示的にpush許可が出たら、`git push origin master`を実行する。
2. push後、GitHub上のリポジトリでコミット数・最終更新日時が更新されていることを確認する。
3. `doc/reports/issues_backlog.md`のGitHub上の内容が25件（またはR23の対応が先に完了していればそれ以降の件数）になっていることを確認する。

## 完了条件

- 手順1の報告が提示され、人間の承認を得てから手順2に進んでいる（承認前にpushしていない）。
- push後、GitHub上のリポジトリ・issues_backlog.mdの内容が最新化されていることが確認されている。

## この後

pushが完了し、GitHub上のbacklogが最新化されたら、`codex_r23_create_issues_label_robustness.md`（ラベル自動作成・部分継続対応）を実行し、その後で人間が再度`Create Issues From Backlog`ワークフローをworkflow_dispatchで実行し、残り15件（またはそれ以上）を登録する。

## 禁止事項

- 人間の明示的な承認を得る前に`git push`を実行すること。
