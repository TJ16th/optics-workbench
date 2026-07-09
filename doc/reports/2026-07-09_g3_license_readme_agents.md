# G3 LICENSE / README / AGENTS 実施報告

作成日: 2026-07-09

## 実施内容

- `LICENSE` にApache License 2.0正式全文を追加。
- `NOTICE` を最小構成で追加。
- ユーザー差し替え済みの `README.md` / `AGENTS.md` を正として、実コマンドと現状に合わせて最小修正。
- README参照用のクリーンなスクリーンショット3枚を `doc/images/` に配置。
- `pyproject.toml` にsetuptools package discovery設定を追加し、monorepo直下の `apps/` / `node_modules/` をPython package候補にしないよう修正。
- `pyproject.toml` のtest extraを `pytest` / `httpx` に修正。
- P2-2のPlotly `scattergl` 未対応は、G5用の `doc/reports/issues_backlog.md` にIssue草案として登録。

## READMEの実態反映

- エンジン起動は `python -m uvicorn optics_engine.api.main:app --host 127.0.0.1 --port 8000` に更新。
- 開発インストールは `python -m pip install -e ".[api,test]"` に更新。
- UI起動は実スクリプト名 `npm run ui:dev` に更新。
- snapshot exportは「単一JSONのみ実装、zip exportは未実装」と明記。
- UI Phase 2は「実装済み。ただしsnapshot zip export等に制約あり」として誇張しない記述に更新。

## スクリーンショット

`doc/images/` に以下を配置済み。

- `doc/images/workbench-ja.png`
- `doc/images/workbench-en.png`
- `doc/images/help-drawer.png`

3枚ともアプリ画面のみで、ブラウザのアドレスバーやローカル絶対パスは写っていない。

## 残置プレースホルダ

- `README.md`: `<REPO_NAME>`
- `NOTICE`: `<REPO_NAME>`
- `NOTICE`: `<COPYRIGHT_HOLDER>`

いずれも指示書どおり、人間側で公開時に確定する。

## 検証結果

```text
python -m pip install -e ".[api,test]": passed
python -m pytest -q: 57 passed, 1 warning
npm.cmd run ci: passed
npm.cmd run ui:build:pseudo: passed
```

補足:

- `npm.cmd run ci` は一度、image-plane policyのselect直後Solveで古いpolicy値を送るE2E不安定性を検出した。
- `apps/workbench-ui/src/ui/App.tsx` でSolve時にフォーム現在値を読み戻すよう修正し、再実行で `6 passed` を確認した。
- Viteは依存パッケージ由来の `"use client" directive ignored` 警告を出すが、ビルドは成功している。
- Python側はFastAPI TestClient由来のStarletteDeprecationWarningが1件あるが、テストは成功している。

## Git履歴確認

現在の公開履歴:

```text
3981279 G2 canonicalize documentation
436babb Initial public release
```

G2は独立コミット済み。G3は本報告・関連修正を含めて独立コミットとして記録する。
