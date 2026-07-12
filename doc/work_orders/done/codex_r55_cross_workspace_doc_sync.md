# R55 cross-workspace document sync

## 目的

- `F:\vscode\claude\opt\doc\work_orders\active`の新規・更新ファイルを`F:\vscode\opt\doc\work_orders\active`へコピーする。
- `F:\vscode\opt\doc\reports`へ追加・更新した報告Markdownと`screenshots`配下の画像を、同じ相対パスで`F:\vscode\claude\opt\doc\reports`へコピーする。
- 同期規約を`AGENTS.md`へ記載する。

## 条件

- 削除は同期しない。
- ログオン後も継続監視できるようWindowsタスクとして登録する。
- `F:\vscode\opt`側を実装・報告のGit正本とする。
- R55として1コミットにまとめ、完了報告を残す。
