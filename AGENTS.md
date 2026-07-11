# AGENTS.md — AIコーディングエージェント向けルール

このリポジトリで作業するエージェント（Codex等）は、以下に従うこと。

## 正本ドキュメントと参照ルール

- エンジン仕様の正本：`doc/engine_spec.md`（現行バージョンはファイル冒頭の改訂履歴を参照）
- UI仕様の正本：`doc/ui_spec.md`（同上）
- **`doc/archive/` 以下は旧版であり、参照禁止。** 検索でヒットしても正本を優先すること。
- 有効な作業指示は `doc/work_orders/active/` 内のみ。`done/` は完了済みの記録であり、再実行しない。
- `doc/work_orders/` 直下には `active/`・`done/`・`README.md` 以外を置かない。
- 実装報告は `doc/reports/` に `YYYY-MM-DD_<件名>.md` 形式で追加する。
- コード変更を伴わない確認・運用作業であっても、人間から明示的に依頼された調査・確認タスクは完了報告を `doc/reports/` に残す。
- `doc/reports/issues_backlog.md` は、将来対応すべき残件の**下書きキュー**として継続使用する（詳細は下記「GitHub Issue運用」）。実際のIssue化は人間がGitHub Actionsから手動実行する。

## GitHub Issue運用【Codex自身はIssueを直接作成しない】

- Codex自身の実行環境（ローカルシェル）には、GitHub書き込み用の資格情報を持たせない。`gh issue create` 等をCodexの通常タスク実行中に直接叩かない。
- 作業中に見つかった「今回のスコープ外だが将来対応すべき項目」は、`doc/reports/issues_backlog.md` に**下書きとして追記する**（通常のファイル編集・コミットであり、特別な認証は不要）。フォーマットは既存の項目に倣う：
  ```markdown
  ## Issue: <タイトル>

  ラベル案: `engine` / `ui` / `docs` / `performance` / `testing` / `good-first-issue` から該当するもの

  ### 背景
  ...
  ### 対応案
  ...
  ### 受け入れ条件
  ...
  ```
- 実際のGitHub Issue作成は、**人間が `Create Issues From Backlog` ワークフロー（`.github/workflows/create-issues.yml`、workflow_dispatch）をGitHub Actionsタブから手動起動する**ことで行う。このワークフローはリポジトリ組み込みの `GITHUB_TOKEN`（実行時のみ有効な使い捨てトークン）を使い、`scripts/create_issues_from_backlog.py` 経由で重複確認をした上でIssueを作成し、作成済み項目のみ見出しに `[issue: #N]` を自動付記してコミットし直す。
- Codexは `doc/reports/issues_backlog.md` の見出しに既に `[issue: #N]` が付いている項目を、Issue化済みとして扱う（再提案しない）。
- Codexはこのワークフローを自分でトリガーしない（`workflow_dispatch` の起動は人間が行う）。トリガーが必要と判断した場合は、完了報告で「backlogに新規項目を追加した。Issue化にはCreate Issues From Backlogワークフローの手動起動が必要」と明記するに留める。
- ラベルは既定タクソノミーを使う：`engine` / `ui` / `docs` / `performance` / `testing` / `good-first-issue`。
- 既存Issueのクローズ・編集は、当該タスクで明示的に指示された場合のみ行う（PAT不要のこの設計では、そもそもCodexはIssue書き込み権限を持たないため通常発生しない）。

## 報告・コミュニケーション言語

- 実装報告（`doc/reports/`）・タスク完了報告・人間への質問は**日本語**で書く。
- ただし以下は翻訳せず原文のまま記載する：識別子（surface ID、metric名、エラーコード、変数キー）、ファイルパス、コマンド、テスト出力・ログの引用（例：`51 passed` はそのまま）、コード片。
- コミットメッセージは英語とする（Conventional Commits推奨。例：`feat(engine): add image_plane_policy (Task A1)`、`docs: reorganize doc/ into canonical layout (Task G2)`）。
- README等の対外ドキュメントは**日本語主体＋冒頭に英語Overview**の構成を維持する。全文の日英併記は行わない（内部報告書も同様）。
- Issue（タイトル・本文）およびissues_backlogは日本語で書く。ラベル名は英語（engine / ui / docs / performance 等）。
- 本ルール適用前の英語レポートは翻訳し直さず、そのまま `doc/reports/` に保管する。

## 完了主張の根拠明記

- README の状況表・ステータス文言、`doc/work_orders` の active/done 分類、および実装報告内の「Done」「実装済み」表記を新たに主張・変更する場合は、**根拠となるコミットハッシュ・テストファイル名・直近のテスト/CI実行結果を必ず明記する**こと。根拠を示せない完了主張は行わない。
- ブラウザ等の実環境で修正が反映されているか確認する際は、まず `/v1/meta` の `build_info.git_commit` が報告コミットと一致しているかを確認する。一致しない場合はプロセス再起動が必要である。
- `/v1/meta` の `build_info.git_dirty` は作業ツリー全体の状態を示す。`doc/work_orders/active/` の指示書や `doc/reports/` の報告書追加でも `true` になりうるため、値の解釈時は `git status --short` で内訳を確認する。
- 機能の一部が未実装・簡略化されている場合は「Done」と書かず、「Partial」「Done with noted limitation」のように状態を正確に区別する（例：単一JSON exportは実装、zip exportは未実装、のように粒度を分ける）。
- 別タスク・別報告書の記述と矛盾する完了主張をしないこと。矛盾に気づいた場合は、その場で報告し人間の確認を求める（無視して片方を採用しない）。

## 人間が配置したファイルの扱い

- `README.md`、`AGENTS.md`、`doc/engine_spec.md`、`doc/ui_spec.md`、glossary本体（`apps/workbench-ui/src/i18n/glossary/glossary.{ja,en}.json`）は人間が正本として配置するファイルである。
- これらの内容変更は、**指示書に明記された範囲**（例：`TODO(codex)` マーカーの充足、指定箇所のパス更新）に限る。指示されていない全面書き換え・言い回しの改善・節構成の変更・削除は禁止。
- 指示の参照先（「最新版」「そのファイル」等）が具体的なパスやコミットで特定できない場合は、実行せず人間に確認する。存在しないファイルを自分で作って代替してはならない。

## 作業規律

- 指示書のタスクは**番号順に1タスクずつ**。タスク完了報告後に停止し、次タスクへ勝手に進まない。スコープの先取り禁止（指示書の「スコープ外」節を厳守）。
- 1タスク=1コミット。コミットメッセージにタスク番号を含める。
- 複数エンドポイントが同種のレスポンス項目を持つ場合、修正時は代表1箇所だけでなく全該当エンドポイントを横断確認し、直接テストで固定する。
- ローカルでエンジン/APIプロセスを起動したままコード変更を重ねた場合、実行中プロセスには変更が反映されない。Network確認やブラウザ確認の前に必要に応じてプロセスを再起動する。
- **機能・UI変更を伴うタスクの完了報告を出す前に、ローカルのエンジンAPI・UI開発サーバープロセスを再起動し、`GET /v1/meta`の`build_info.git_commit`が最新HEADと一致していることを確認してから報告する。** 人間がブラウザで確認する時点で、報告コミットと実際に動いているプロセスが常に一致している状態を維持する（人間が都度再起動を依頼する運用にしない）。一致確認の結果（`build_info.git_commit`とHEADの値）を完了報告に含める。ドキュメントのみの変更等、プロセス再起動が無関係なタスクでは本項目は不要。
  - **確認対象は「機能・コードに実質変更があった最後のコミット」であり、その後に続く報告書自体のコミット・本ルールに基づく追記コミットは対象に含めない。** タスクの指示書ファイル・完了報告ファイル・AGENTS.md追記のみを含むコミットは、それ自体では確認をやり直す必要はない（無限後退を避けるため）。完了報告は「本コミットの直前時点で一致確認済み」の形で断定的に記述し、「この後確認する」という未来形の記述で締めない。
- 既存テストは常にグリーンを維持する。テストを削除・スキップして通すことは禁止（正当な理由がある場合は報告して停止）。
- per-rayのLevel 0リファレンス実装（`optics_engine/reference/` 相当）は削除しない。Golden Testの基準である。
- ベンチ結果は `bench_results/` のJSON履歴に追記し、報告に前回比を含める。

## 完了報告スクリーンショットの保存

- 完了報告に視覚的な確認結果（ブラウザのスクリーンショット等）を添付する場合、
  画像ファイルを `doc/reports/screenshots/YYYY-MM-DD_<件名>_<連番>.png` として
  リポジトリに保存し、完了報告書（.md）からはそのファイルへの相対パスで参照する。
- チャットに画像を貼るだけ、または完了報告に「スクリーンショットを確認した」と
  文章で述べるだけでは不十分とする。画像ファイル自体をリポジトリに残すこと。
- 1つの完了報告で複数のスクリーンショットを使う場合、連番（_1, _2, ...）で区別する。
- スクリーンショットは差分が分かるものを優先する（修正前後の比較が必要な場合は
  両方保存し、report本文でどちらがbefore/afterか明記する）。

## バッチ実行モード

- 通常、指示書のタスクは1つ完了するごとに停止し、人間の確認・次の発注を待つ（既存規約）。
- ただし、指示書または発注メッセージに **「バッチ実行可」** と明記された場合に限り、Codexは複数タスクを連続して自律実行してよい。
- バッチ実行可の対象は、以下の条件を満たすタスク群に限る（人間が発注時に判断する）：
  1. 各タスクの完了条件が明確に定義されている。
  2. 前のタスクの実行結果の中身によって次のタスクの内容が変わらない（＝各タスクが独立している。調査タスクのように「直してみないと次に何が問題か分からない」性質のものはバッチ実行の対象にしない）。
  3. 失敗しても被害が閉じている（コード変更を伴う場合は既存テストのグリーン維持で担保する。pushやIssue作成等の外部作用を伴うタスクはバッチ実行の対象にしない）。
- バッチ実行中、各タスク完了時に1〜2行の進捗ログを記録し、バッチ完了後にまとめて1本の完了報告として提示する（個別タスクごとの詳細報告は、必要な範囲でこの中に含める）。
- **想定外の発見があった場合は、バッチを中断し、そこで停止して人間に報告する。** 想定外の発見とは：新しいバグの発見、仕様との矛盾、実装方針の分岐が必要な判断、既存テストの失敗、等。良かれと思って自己判断で対応を進めない。
- バッチ実行は「番号付きタスクが明確に列挙された指示書」（例：P0-7性能改善タスク群）に対してのみ用いる。都度人間が状況を見て動的に作成する調査系タスク（R系）には原則として適用しない。

## エンジン側の不変規約

- エラー・警告はすべて構造化形式（severity / code / params / message_en）。message_enの情報は必ずparamsからも取得可能にする。新codeは `/v1/meta` の enumerations に必ず追加する。
- **capabilitiesには実際に動作する機能のみを列挙する**（列挙駆動テストで担保）。
- エンジンは多言語化しない（翻訳はUI責務）。
- 数値出力の決定論を守る：同一リクエスト→ビット同一出力。random/sobolサンプリングはseed必須。

## UI側の不変規約（i18n恒常DoD）

- 表示文字列のハードコード禁止。すべてi18nリソース経由。
- エンジン識別子（surface ID、metric生キー、変数キー、エラーコード）は翻訳しない。
- 新しく表示するmetric・エラーコードには glossary ja/en 両方のエントリ追加をセットで行い、`npm run i18n:coverage` グリーンでマージする。
- glossary本体（seed由来）の内容改変は人間レビュー経由。暫定追記は supplement 用語集へ。
- 小数点はロケールによらずピリオド固定。単位（mm, µm, deg, lp/mm等）は翻訳しない。
- ツールチップはCarbon Toggletip（クリック/フォーカス開閉）。ホバー限定にしない。
- 点数の多い散布・spot表示はPlotly scattergl。SVG+D3はレイアウト図・光線図に限定。

## テスト・検証コマンド

```bash
python -m pytest -q          # エンジン（Golden Test含む）
npm run ci                   # UI: build + i18n:check + i18n:coverage + i18n:test
npm run ui:build:pseudo      # 擬似ロケールビルド
python benchmarks/spec_like_benchmark.py --profile smoke   # ベンチ（結果はbench_results/へ）
```

Playwright E2EをGitHub Actions Ubuntu上で実行する場合は、CI側で `npx playwright install --with-deps msedge` を先に実行すること。ローカルWindowsでは既存ブラウザで通っても、CIではブラウザ導入とOS非依存のwebServer起動コマンドが必要。

## 禁止事項

- `doc/archive/` の参照、旧版仕様に基づく実装
- リモートへのpush（人間の明示承認なしに行わない）
- 新規の書き込み系資格情報（PAT等）の発行・保存・環境変数への設定は人間の承認を得てから行う。GitHub Issue作成はPATを使わずAGENTS.md「GitHub Issue運用」節の方式（Actions workflow_dispatch＋組み込みGITHUB_TOKEN）で行うため、通常はこの種の資格情報をCodexに持たせる必要はない。
- 個人情報・絶対パス（ユーザー名入り）・秘密情報のコード/ドキュメント/ログへの記載
- 未実装機能のcapabilities掲載、README進捗表の誇張

## Work Order File Naming

- 新規の作業指示書は `doc/work_orders/active/codex_<task-number>_<short-slug>.md` 形式で作成する。
- 完了報告は `doc/reports/YYYY-MM-DD_<task-number>_<short-slug>.md` 形式で作成する。
- `task-number` は小文字で、台帳・指示番号の表記を保つ。例: `g8`, `a1`, `u5`, `p3-2`, `q1`, `q1b`, `r14-20`。
- 指示番号が未確定の場合は推測で新規番号を作らず、人間に確認する。既存の会話順から明確に次番が決まる整理タスクのみ、その根拠を完了報告に書く。
## Completion Report Move Rule

- When adding a task completion report under `doc/reports/`, move the corresponding work order from `doc/work_orders/active/` to `doc/work_orders/done/` in the same commit.
- Do not split a completion report and its active-to-done work order move into separate commits.
