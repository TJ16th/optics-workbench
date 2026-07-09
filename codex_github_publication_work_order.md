# リポジトリ公開準備 作業指示書（Codex向け・タスクG1〜G5）

## 背景と実行タイミング

GitHubでの公開（Apache-2.0）を前提にリポジトリを整備する。エンジンAPI追補（A0〜A3）・UI i18n（U1〜U5）は完了済み。**本指示書はUI Phase 2（P2系）より先に実行する。** 理由：(1) G2のdoc再編成が既発行指示書（UI Phase 2、最適化タスク8-13等）の参照パスを変えるため、(2) 個人情報が履歴に混入している場合、push前の今が履歴作り直しの唯一安全なタイミングのため。

注意：A3で「新エラーコードに対するUI側i18n:coverageの失敗（レッド状態）」を意図的に残している。公開リポジトリのCIが初日から赤になるのを避けるため、**G4の前段でこのレッドを解消する**（G4の作業1参照。UI Phase 2指示書のP2-5にある同項目は本タスクで消し込んだ旨を報告し、P2-5では確認のみとする）。

前提：ローカルGit化は完了済み（baselineコミットあり）。GitHubへのpushはG5完了・人間の最終確認後に行う。**G5完了までリモートへpushしない。**

付属ファイル：`README.md`（雛形）、`AGENTS.md`（雛形）、`.github/workflows/ci.yml`・`bench.yml`（雛形）。雛形内の `TODO(codex)` マーカーは実際のコマンド・パスに置き換えること。

## 進め方

タスクは番号順に1タスクずつ。各タスク完了報告後に停止する。1タスク1コミット。

---

## タスクG1：個人情報・環境情報の除去と履歴クリーン化

### 作業

1. 追跡対象の全ファイルに対し、以下のパターンでスキャンし、検出一覧を報告する：
   - ユーザー名・個人環境：`<user>`、`<user-home>`、`<user-home-escaped>`、`<user-app-data>`、`<runtime-cache>`、`<workspace-root>`、`<workspace-root-escaped>`
   - 汎用：メールアドレス正規表現、`\\\\` を含むUNCパス、ホスト名らしき文字列、APIキー/トークン形式（`<openai-token-prefix>`、`<github-token-prefix>`、`<aws-key-prefix>` 等）
2. 検出箇所を修正する：ドキュメント・報告書内の実行例は相対パスまたは `<python>` のようなプレースホルダに書き換える。ベンチスクリプト内の絶対パスは環境変数または引数化する。
3. スクリーンショットPNG（capture-ui-*.png）を確認する：ウィンドウタイトル・パスバー等に個人情報が写り込んでいる場合は破棄。README用の画像は**クリーン化後に撮り直し**、`doc/images/` に配置する。リポジトリ直下の作業キャプチャは追跡対象から外す（.gitignoreへ）。
4. **Git履歴を検査する**：`git log -p | grep`（またはgit filter用ツール）で上記パターンが過去コミットに含まれるか確認する。
5. 履歴に混入がある場合（未pushなので安全に作り直せる）：orphanブランチ方式でクリーンな状態を単一の初回コミットに squash し、旧ブランチを削除する。混入がない場合は履歴を維持する。**どちらを選んだかと根拠を報告する。**
6. 再発防止として、G4のCIにシークレット/PIIスキャン（gitleaks等の軽量ツール、または上記パターンのgrepスクリプト）を追加する準備をする（組み込み自体はG4）。

### 完了条件

- スキャン結果ゼロ件（修正後の再スキャンログを報告に添付）。
- 履歴検査の結果と、squash実施有無の報告。

---

## タスクG2：doc再編成と正本化

### 作業

1. docを以下の構成へ再編成する（Git上のリネームとして実施）：

```text
doc/
  README.md                 # 正本一覧と参照ルール（AGENTS.mdから参照される）
  engine_spec.md            # ← optical_engine_spec_v2_3.md を改名（正本。現v2.3）
  ui_spec.md                # ← optics_workbench_ui_spec_v0_3.md を改名（正本。現v0.3）
  images/                   # README用スクリーンショット（G1で撮り直したもの）
  work_orders/
    active/                 # 実行中・未着手の指示書のみ
    done/                   # 完了済み指示書（性能タスク0-7の完了分、U1-U5等）
  reports/                  # 実装報告（implementation_status_*.md、日付付き）
  archive/                  # 旧版仕様（v2, v2_1, v2_2, v0_1, v0_2）。以後追加しない
```

2. 指示書を仕分ける：完了済み（v2.3小改訂、U1〜U5）→ done/、未着手・実行中（エンジンAPI追補、UI Phase 2、最適化タスク8-13、性能タスクの未完分）→ active/。仕分け結果の一覧を報告する。
3. **active/内の全指示書のファイルパス参照を新パスに更新する**（`doc/optical_engine_spec_v2_3.md` → `doc/engine_spec.md` 等）。本文中の「仕様v2.1 21.5節」のような版言及は改訂履歴で追えるため変更しない。
4. glossaryのシード原本がdocにある場合、実装側（apps/workbench-ui/src/i18n/glossary/）を正とし、docの重複コピーはarchiveへ移す（二重管理の排除）。
5. `doc/README.md` を作成する：正本2ファイルと現行バージョン、archive参照禁止、work_orders/active/のみが有効な指示である旨、reportsの命名規約（`YYYY-MM-DD_<件名>.md`）。

### 完了条件

- 新構成のtree出力と、active/done仕分け表の報告。
- active/内指示書のパス参照更新のdiff要約。

---

## タスクG3：LICENSE・README・AGENTS.mdの配置

### 作業

1. リポジトリ直下に `LICENSE` を配置する（**Apache License 2.0 の正式全文**。改変しない）。ソースファイルへのライセンスヘッダ一括付与は行わない（LICENSEファイルのみで足りる）。
2. 付属雛形 `README.md` をリポジトリ直下に配置し、`TODO(codex)` を実情に合わせて埋める：実際の起動コマンド（エンジン・UI）、テストコマンド、Phase進捗表の現状化、スクリーンショットパス。**誇張しない**：未実装機能を実装済みのように書かない。プロジェクト名・リポジトリ名のプレースホルダは人間が決めるため `<REPO_NAME>` のまま残し、その旨を報告する。
3. 付属雛形 `AGENTS.md` をリポジトリ直下に配置し、テスト・CIコマンドを実際のものに更新する。
4. `NOTICE` ファイルを作成する（プロジェクト名とコピーライト行のみの最小構成。名義は `<COPYRIGHT_HOLDER>` プレースホルダとし、人間が確定する）。

### 完了条件

- LICENSE / README.md / AGENTS.md / NOTICE が配置され、README内のコマンドが実際に動作することを確認した報告（コマンド実行ログ）。
- 残置したプレースホルダの一覧報告。

---

## タスクG4：GitHub Actions CI

### 作業

1. **前段：i18n:coverageのグリーン化。** A1/A2で追加された全エラーコード（image_plane_policy_not_applicable、artifact_not_found 等。solve_not_converged と artifact_expired はglossary本体に既存のはずなので確認のみ）について、不足分のja/enエントリをsupplement用語集へ追記し、`npm run i18n:coverage` をグリーンにする。追記エントリは完了報告に一覧で含める（人間レビュー対象）。
2. 付属雛形を `.github/workflows/ci.yml` に配置し、実環境に合わせて修正する：
   - engineジョブ：Python 3.12セットアップ、依存インストール、`pytest -q`（Golden Test含む）
   - uiジョブ：Node 20セットアップ、`npm ci`、`npm run ci`（ui:build / i18n:check / i18n:coverage / i18n:test）、`npm run ui:build:pseudo`
   - piiジョブ：G1のパターンによるgrepスキャン（またはgitleaks）
3. 付属雛形を `.github/workflows/bench.yml` に配置する：workflow_dispatch起動で `benchmarks/spec_like_benchmark.py --profile smoke` を実行し、結果JSONをActions artifactとしてアップロードする（bench_results/へのコミットはCIでは行わない）。
4. ワークフローをローカルで検証する（actが使えない場合は、各ステップのコマンドを手元で順次実行して同等性を確認し、その旨を報告する）。
5. i18n:coverage は実エンジン起動が必要な場合、CI内でエンジンをバックグラウンド起動するか、/v1/meta の応答をリポジトリ内のfixture JSONと突き合わせる方式にするか、**どちらを採るか判断して報告する**（fixture方式の場合、fixtureとの乖離検出テストをエンジン側pytestに追加すること）。

### 完了条件

- 2つのワークフローファイルの配置と、各ステップのローカル実行ログ。
- i18n:coverageのCI方式の判断理由の報告。

---

## タスクG5：残件のIssueバックログ化とpush前チェックリスト

### 作業

1. `doc/reports/issues_backlog.md` を作成する。各実装報告のRemaining Work・仕様との差分のうち、**active/の指示書でカバーされていない項目**をIssue草案（タイトル・本文・ラベル案：engine/ui/docs/performance/good-first-issue）として列挙する。active/でカバー済みの項目（例：Toggletip E2E→UI Phase 2のP2-0）はIssue化せず、対応先の指示書名を記す。
   - 想定される未カバー項目の例：回折PSF、プリズム展開モデルの本格化、supplement用語集の本体統合（人間レビュー待ち）、axis_convention（Z軸系インポート）、Numba化（条件付き）、WebSocketセッション。仕様の将来拡張全部を網羅する必要はなく、「次の2〜3フェーズで現実に着手しうるもの」に絞る。
2. `gh` CLIが利用可能ならリポジトリ作成後のIssue一括登録スクリプト（backlogから生成）を用意する。不可ならbacklogのまま人間が登録する前提とする。
3. push前最終チェックリストを実行し、結果を報告する：
   - [ ] G1スキャン再実行でゼロ件（履歴含む）
   - [ ] `git status` クリーン、.gitignoreが生成物・キャプチャを除外
   - [ ] LICENSE / NOTICE / README / AGENTS.md 配置済み、プレースホルダ一覧を人間へ提示
   - [ ] CI相当のコマンドが全てローカルグリーン
   - [ ] doc/archive/ 以外に旧版仕様が存在しない
   - [ ] bench_results/ に環境依存の個人情報が含まれない

### 完了条件

- issues_backlog.md とチェックリスト結果の提出。**push自体は行わず**、人間の確認待ちで停止する。

---

## 人間側の作業（Codexの作業対象外）

- リポジトリ名・公開/非公開の最終決定、GitHub上でのリポジトリ作成とpush
- NOTICE / READMEの `<COPYRIGHT_HOLDER>` `<REPO_NAME>` の確定
- issues_backlog.md のレビューとIssue登録（またはスクリプト実行の承認）
- supplement用語集の内容レビュー（別途）

