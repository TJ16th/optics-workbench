# リポジトリ公開 最終確定・push指示（Codex向け）

## 決定事項

- GitHubリポジトリ：`https://github.com/TJ16th/optics-workbench`
- 著作権者名義：`TJ16th`

## 作業

1. プレースホルダを確定値で置換する（3箇所、すべて完了報告に置換前後を明記すること）：
   - `README.md` の `<REPO_NAME>` → `optics-workbench`（タイトル行、および言及箇所すべて）
   - `NOTICE` の `<REPO_NAME>` → `optics-workbench`
   - `NOTICE` の `<COPYRIGHT_HOLDER>` → `TJ16th`（NOTICEの著作権表示は年を含む形式とする。年は今回のG系作業日付を基準に `Copyright 2026 TJ16th` とする）
2. 置換後、以下を再実行してグリーンを確認する（新規ではなく既存検証コマンドの再確認）：
   - `python -m pytest -q`
   - `npm run ci` を**連続3回**実行し、Playwright E2Eがフレーキーでないことを確認する（G3・G5で image-plane policy 関連のE2E不安定性が2回報告されているため、pushの最終ゲートとして安定性を再確認する。3回中1回でも失敗したら、その内容を報告して停止し、pushしない）
   - `npm run ui:build:pseudo`
3. `git status` がクリーンであることを確認する。
4. このタスクを独立コミットとする（コミットメッセージ例：`G6 finalize repository placeholders for public release`）。
5. **リモートリポジトリの追加とpushを実行する**：
   - リモートが未設定の場合、`git remote add origin https://github.com/TJ16th/optics-workbench.git` を実行する
   - 認証情報の設定・入力はこのタスクの範囲外とする。認証エラーが出た場合はその旨を報告して停止し、資格情報の設定を人間に委ねる
   - push対象ブランチ・pushコマンドを実行前に報告し、実行後に結果（成功/失敗、リモートのコミットハッシュ）を報告する
6. push成功後、`doc/reports/` に最終報告ファイル（`YYYY-MM-DD_g6_public_release.md`）を作成し、以下を記録する：
   - 置換したプレースホルダの一覧
   - E2E 3回連続実行の結果
   - pushしたコミットハッシュとリモートURL
   - 今後の運用（Issue登録はbacklogから人間が転記する旨、CIはpush後にGitHub Actionsで自動実行される旨）

## 完了条件

- リモート `https://github.com/TJ16th/optics-workbench` に公開ブランチがpushされている。
- GitHub Actions（`ci.yml`）がpush後に自動起動し、結果を報告する（起動確認まではこのタスクに含める。CI結果の詳細な待機・修正は別タスクとする）。
- 最終報告ファイルが `doc/reports/` に存在する。

## 禁止事項

- 上記以外のファイルの内容変更（README/NOTICE本文の言い回し変更等）は行わない。
- E2E再実行で不安定性が再発した場合、原因調査・修正を勝手に行わず、まず報告して停止する（今回はpushのゲートとしての確認が目的であり、新たなバグ修正タスクをここに含めない）。
