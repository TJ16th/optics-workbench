# Issueバックログ運用の切り替え 指示書（Codex向け・タスクG8改訂版）

## 背景・設計変更

前バージョンのG8は「CodexがPATで`gh issue create`を直接実行する」設計でしたが、**PATの受け渡しがCodexアプリの実行環境（ローカルサンドボックス）とGitHub Actionsの実行環境で別物であり、PATをCodexアプリ側に安全に渡す確立した経路がなかったため撤回**しました。代わりに、GitHub Actions組み込みの `GITHUB_TOKEN`（実行時のみ有効な使い捨てトークン）を使う設計に変更します。Codexは今後もIssueを直接作成せず、`doc/reports/issues_backlog.md` への追記のみを行います。実際のIssue作成は人間がGitHub Actionsタブから手動でワークフローを起動します。

付属ファイル（人間が配置済み、またはこのタスクで配置する）：

- `scripts/create_issues_from_backlog.py` — backlogをパースしIssueを作成するスクリプト
- `.github/workflows/create-issues.yml` — workflow_dispatch専用のワークフロー

## 作業

1. 付属の `scripts/create_issues_from_backlog.py` を配置し、実行権限やshebangがリポジトリの他スクリプトと整合しているか確認する（G4で作った `scripts/pii_scan.py` と同じ配置慣習に合わせる）。
2. 付属の `.github/workflows/create-issues.yml` を `.github/workflows/` に配置する。
3. `doc/reports/issues_backlog.md` の既存10項目が、スクリプトの想定フォーマット（`## Issue: <タイトル>` 見出し、直後に `ラベル案: ...` 行、`### 背景` / `### 対応案` / `### 受け入れ条件` の小見出し）と一致しているか確認する。現状のファイルは概ねこの形式のはずだが、ズレがあれば整形する（**本文の内容は変更しない**。見出しレベルや行の配置のみ調整する）。
4. **ローカルで dry-run を実施する**（実際にはIssueを作成しない）：
   ```bash
   gh auth status   # Codex自身が既にgh CLIでログイン済みの開発者アカウントを使っている場合のみ可能。
                    # 認証されていなければこのステップは省略し、5のActions側dry-runで代替確認する。
   python scripts/create_issues_from_backlog.py --repo TJ16th/optics-workbench --file doc/reports/issues_backlog.md --dry-run
   ```
   dry-runの出力（パースできた項目一覧、タイトル、ラベル）を完了報告に含める。**実際にIssueを作成する必要はない。パースが正しく10項目を認識することの確認が目的。**
5. `AGENTS.md` の「GitHub Issue運用」節の記述と、実際に配置したワークフロー・スクリプトの動作が一致していることを確認する（節に書かれたコマンド例・ファイルパスが実物と食い違っていないか）。
6. このタスクを独立コミットとする。

## このタスクでは行わないこと（人間側の作業）

- GitHub Actionsタブから `Create Issues From Backlog` ワークフローを実際に手動起動し、10件のIssueを作成するのは**人間が行う**。Codexはこの起動を代行しない（`workflow_dispatch`はCodexの実行環境からは呼べない設計のため）。
- ワークフロー実行後、`issues_backlog.md` に `[issue: #N]` が自動付記されコミットされるので、その結果を確認するのも人間が行う。

## 完了条件

- `scripts/create_issues_from_backlog.py` と `.github/workflows/create-issues.yml` が配置されている。
- dry-runで10項目（または実際に存在する項目数）が正しくパースされたことが完了報告に示されている。
- `AGENTS.md`との整合確認結果が報告されている。

## 禁止事項

- Codex自身が`gh issue create`を実行してIssueを作成すること（このタスクの目的そのものが「Codexが直接作成しない設計への移行」であるため）。
- dry-runでの確認をスキップし、実配置だけで完了報告すること。
