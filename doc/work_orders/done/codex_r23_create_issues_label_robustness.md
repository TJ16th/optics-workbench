# Create Issues From Backlogワークフロー：ラベル欠落による失敗の恒久対応

## 背景

`Create Issues From Backlog`ワークフローを実行したところ、`gh issue create`が`--label ui`で失敗した。原因は、GitHubリポジトリにデフォルトラベル9個（bug, documentation, duplicate, enhancement, good first issue, help wanted, invalid, question, wontfix）のみが存在し、プロジェクトのラベルタクソノミー（AGENTS.mdの「GitHub Issue運用」節：`engine` / `ui` / `docs` / `performance` / `testing` / `good-first-issue`）が1つもリポジトリに作成されていなかったため。

人間側で上記6ラベルを手動作成し、直近の実行は解消見込みだが、以下2点の恒久対応が必要：

1. 未知のラベルで全体が失敗する脆さの解消。
2. `doc/reports/issues_backlog.md`内の「variable binding registry」Issueに使われている`architecture`ラベルが、既定タクソノミー6件に含まれていない（タクソノミードリフト）。

## 作業

### 1. スクリプトのラベル自動作成対応

`scripts/create_issues_from_backlog.py`を修正し、`gh issue create`を呼ぶ前に、使用予定の各ラベルが存在するか確認し、存在しなければ`gh label create <name>`で作成してから続行するようにする（`gh label create`は既に存在する場合エラーになるため、事前に一覧取得して存在確認するか、エラーを握りつぶして続行する形にする）。

- 新規作成するラベルの色は固定の適当な色（例：`ededed`）で構わない。
- 1件のIssue作成が失敗しても、後続のIssue作成が止まらないようにする（現状は`subprocess.run(..., check=True)`で最初の失敗時に即座に停止しているため、1件失敗すると残り全件が実行されない設計になっている。個別に例外を捕捉し、失敗した項目は失敗一覧として最後にまとめて報告し、成功した項目は`[issue: #N]`を付記する形に変更する）。

### 2. `architecture`ラベルのタクソノミードリフト解消

`doc/reports/issues_backlog.md`内で`architecture`ラベルが使われている箇所（「variable binding registry」Issue）を確認し、以下のいずれかで対応する（判断して報告する）：

- (a) 既定タクソノミーの`engine`ラベルに統一する（`architecture`ラベルを使わない）。
- (b) `architecture`を正式にタクソノミーへ追加する（AGENTS.mdの「GitHub Issue運用」節のラベル一覧に追記する）。

どちらでも構わないが、以後同じような未知ラベルの追加が起きないよう、AGENTS.mdに「新しいラベルを使う場合はタクソノミーへの追記とセットで行う」旨を一言追記する。

### 3. 動作確認

ローカルで`--dry-run`を実行し、10件（または現在のbacklog件数）全件が正しくパースされ、ラベルが既定タクソノミーの範囲に収まっていることを確認する。実際のGitHub Issue作成（workflow_dispatch起動）は人間が行う。

## 完了条件

- ラベル自動作成ロジックが追加されている。
- 1件の失敗が全体を止めない設計に変更されている。
- `architecture`ラベルのタクソノミードリフトが解消されている。
- dry-runで全件のラベルが検証済みタクソノミーに収まっていることが確認されている。
