# 未push差分の確認とpush 指示書（Codex向け・タスクG8-push）

## 背景

GitHub Actionsの画面で確認したところ、ワークフロー一覧に「CI」しか表示されておらず、**「Benchmark (smoke)」（`.github/workflows/bench.yml`）と「Create Issues From Backlog」（`.github/workflows/create-issues.yml`）のどちらも存在しない**。G8完了報告にはpush作業の記載がないため、G8時点の変更がローカルコミットのみでリモートに届いていない可能性が高い。また、G4で配置したはずのbench.ymlも同様にリモートに存在しない可能性がある。原因を特定した上で、確認→人間への提示→pushの順で進める。

## 作業

1. `git fetch origin` を実行し、リモート（`origin/master`）の最新状態を取得する。
2. `git log origin/master..HEAD --oneline` を実行し、**ローカルにあってリモートにまだ無いコミット**を一覧化する。完了報告にそのまま貼る。
3. `git diff origin/master..HEAD --stat` を実行し、変更されるファイルの一覧を完了報告に貼る。
4. `git show origin/master:.github/workflows` （相当のコマンド、例：`git ls-tree origin/master -- .github/workflows`）で、**リモート上に実際に存在するワークフローファイル一覧**を確認し、報告する。特に `bench.yml` がリモートに存在するか否かを明記する。
5. 存在しない場合、いつのコミットで追加されたはずが、なぜリモートに届いていないのか（単に該当コミットがまだpushされていないだけか、それとも一度も正しくコミットされていなかったか）をコミット履歴から特定し、報告する。
6. ここまでの内容（未pushコミット一覧、変更ファイル一覧、bench.ymlの状況）を報告し、**この時点で一旦停止する。pushはまだ実行しない。**

## 人間の確認後に行うこと（別メッセージで明示的な許可が出てから実行）

7. 人間から明示的にpush許可が出たら、`git push origin master` を実行する。
8. push後、GitHub Actionsの「All workflows」画面に「CI」に加えて「Benchmark (smoke)」「Create Issues From Backlog」が表示されることを確認する（`gh api` 等で確認できればそれでよいし、確認方法が無ければ人間に画面確認を依頼してよい）。
9. push後の状態を完了報告にまとめる（pushしたコミットハッシュ、リモートでのワークフロー一覧）。

## 完了条件

- 手順1〜6の報告が出て、人間の承認を得てから手順7〜9に進んでいる（承認前にpushしていない）。
- push後、3つのワークフロー（CI, Benchmark (smoke), Create Issues From Backlog）がGitHub Actions上に存在することが確認されている。

## 禁止事項

- 人間の明示的な承認を得る前に `git push` を実行すること。
- 差分内容を確認せずにpushすること。
