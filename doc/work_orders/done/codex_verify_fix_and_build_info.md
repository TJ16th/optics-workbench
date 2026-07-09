# 修正内容の整合確認とbuild_info導入 指示書（Codex向け）

## 背景

`2026-07-10_education_preview_paths_fix.md`の報告に矛盾がある。「確認結果」では、前回の`/v1/trace/forward`修正により`education/preview`にも自動的に`paths`が返る構造になっていた（＝今回コード変更は不要だった）と書かれている。一方、人間が実際にブラウザのNetwork タブで確認した時点では`paths`は存在せず、`Ctrl+F`検索でもヒットしなかった。

この食い違いの原因を先に特定する。加えて、今後同種の「報告と実物の食い違い」を即座に切り分けられるよう、`/v1/meta`にビルド識別情報を追加する（`doc/work_orders/active/codex_engine_build_info_meta.md`として指示済みの内容。まだ未着手であれば本タスクに統合して行う）。

## 作業

### 1. 食い落着の原因確認

1. `git log --oneline -- optics_engine/api/main.py`で、`/v1/trace/forward`にpathsを追加したコミットと、今回のコミットの差分を確認する。今回のコミットで`main.py`に実質的な変更が入っているか（`education/preview`ハンドラのコード自体が変わったか）を確認し、正確に報告する。
2. もし今回`main.py`に変更が無かった（テスト追加のみだった）場合：人間が確認した時点（修正前）と現在（確認後）で、**人間側のエンジンプロセスが再起動されていなかった可能性**が高い。この場合、「ローカルでプロセスを起動したまま長時間コード変更を重ねると、変更が反映されない」という開発運用上の注意点をAGENTS.mdまたはREADMEの開発環境セットアップ節に一言追記する。
3. もし今回`main.py`に実質的な変更が入っていた場合、報告の「確認結果」の記述（「共有レスポンスになっていた」）が不正確だったことになるので、正しい経緯（実際は何が欠けていて、今回何を直したか）に書き改めて再報告する。

### 2. build_info導入（`codex_engine_build_info_meta.md`の内容を実施）

1. `/v1/meta`のレスポンスに`build_info`を追加する：
   ```json
   "build_info": {
     "git_commit": "<現在の作業ツリーのgit commitハッシュ（短縮形）>",
     "git_dirty": true または false,
     "started_at": "<プロセス起動時刻のISO8601>"
   }
   ```
2. `git_commit`はプロセス起動時に`git rev-parse --short HEAD`相当で取得する。git未検出時は`"unknown"`とし、エラーにしない。
3. `git_dirty`は`git status --porcelain`相当が空でない場合`true`。
4. UI側のDebugタブ（存在すれば）に、接続先エンジンの`build_info`を表示する。
5. `AGENTS.md`の「完了主張の根拠明記」節に、以下を追記する：
   - 「ブラウザ等の実環境で修正が反映されているか確認する際は、まず`/v1/meta`の`build_info.git_commit`が報告コミットと一致しているかを確認する。一致しない場合はプロセス再起動が必要である」

## 完了条件

- 食い違いの原因（プロセス未再起動か、報告の誤記載か）が特定され、正確に報告されている。
- `/v1/meta`が`build_info.git_commit`を返し、現在のHEADと一致することが確認されている。
- AGENTS.mdへの追記が完了している。

## 人間側での最終確認

このタスク完了後、人間が以下を行う：
1. エンジンプロセスを再起動する。
2. `GET /v1/meta`をブラウザまたはcurlで叩き、`build_info.git_commit`を確認する。
3. ブラウザをハードリロードし、Network タブで`education/preview`レスポンスに`paths`が含まれることを確認する。
4. Layout Viewで実際に光線が屈折して見えることを確認する。
