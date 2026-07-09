# doc/work_orders 整理 指示書（Codex向け・タスクG9）

## 背景

`doc/work_orders/` 直下に、規約（`active/` / `done/` のみ）に反する状態ができている：フォルダ直下に配置済みのはずのG6・G7指示書ファイルが直置きされ、`g8` という規約にないフォルダが作られている。原因は人間側の受け渡し時に配置先を明示していなかったことによる。本タスクで規約通りの状態に戻す。

`AGENTS.md` の「正本ドキュメントと参照ルール」に、直下には `active/`・`done/`・`README.md` 以外を置かない旨を明記済み（本タスク開始前に確認すること）。

## 作業

1. **インベントリを取る**：`doc/work_orders/` 以下を再帰的に列挙し、`active/`・`done/`・`README.md` 以外に存在するファイル・フォルダ（`g8/` フォルダの中身を含む）を完了報告に一覧化する。

2. **各ファイルを以下のルールで分類・移動する**：
   - `doc/reports/` に対応する完了報告が既に存在する指示書ファイル（例：`codex_g6_finalize_and_push.md` → `2026-07-09_g6_public_release.md` が対応、`codex_g7_ci_failure_investigation.md` → `2026-07-09_g7_ci_failure_investigation.md` が対応）は、`git mv` で `doc/work_orders/done/` へ移動する。
   - 対応する完了報告がまだ存在しない指示書ファイルは `doc/work_orders/active/` へ移動する。
   - `g8` フォルダの中身は、ファイルごとに以下の判定を行う：
     - **Markdownの指示書が複数バージョン存在する場合**（PAT方式の旧版とActions方式の新版）、**内容がActions方式（`gh issue create`をCodex自身が実行せず、`scripts/create_issues_from_backlog.py` と `.github/workflows/create-issues.yml` を配置しdry-runで確認する内容）になっている方を正とする**。もう一方（PAT発行・`gh auth status`でのCodex自身の認証確認を前提にしている版）は古い設計であり、`git rm` で削除する（Git履歴には残るため復元可能）。
     - 正とした指示書ファイルは `doc/work_orders/active/` へ移動する（未実行のため）。
     - `create_issues_from_backlog.py` のコピーが含まれていれば、内容を確認の上 `scripts/create_issues_from_backlog.py` として配置する（既に同じ内容が配置済みならこちらは削除する）。
     - ワークフローYAML（`create-issues.yml` 相当）のコピーが含まれていれば、同様に `.github/workflows/create-issues.yml` として配置する（既に配置済みなら削除する）。
     - `AGENTS.md` のコピーが含まれていれば、内容を比較する。リポジトリ直下の `AGENTS.md` より新しい・異なる内容であれば、その差分を完了報告に明記した上でリポジトリ直下の `AGENTS.md` を更新する。同一内容であれば単に削除する。
     - `github_pat_setup_memo.md`（PAT発行手順のメモ）は、設計変更によりPAT方式自体を採用しないため**削除する**（このファイルはそもそも「リポジトリにコミットしない」と明記されていた個人メモであり、リポジトリ管理下に置くこと自体が本来誤りだった）。
   - 上記のいずれにも当てはまらない不明なファイルがあれば、削除・移動せず一覧化して完了報告に記載し、判断を人間に委ねる。

3. **最終確認**：作業後、`doc/work_orders/` 直下が `active/`・`done/`・（存在すれば）`README.md` のみであることを確認する。

4. 移動前後の対応表（旧パス→新パス、または「削除（理由）」）を完了報告に含める。

5. このタスクを独立コミットとする（`git mv`・`git rm` を使い、削除でも履歴からの追跡可能性を保つ）。

## 完了条件

- `doc/work_orders/` 直下に `active/` / `done/` / `README.md` 以外が存在しない。
- 移動・削除の対応表が完了報告に記載されている。
- `AGENTS.md` を更新した場合、その差分が明記されている。
- `git log` でこのタスクが単一コミットとして記録されている。

## 禁止事項

- 内容を確認せずにファイルを削除すること（特にAGENTS.mdやスクリプトのように実行に影響するもの）。
- 判定に迷うファイルを、報告せず独断で削除すること。
