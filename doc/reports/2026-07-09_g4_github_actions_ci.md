# G4 GitHub Actions CI 実施報告

作成日: 2026-07-09

## 実施内容

- `.github/workflows/ci.yml` を配置。
- `.github/workflows/bench.yml` を配置。
- ルートに残っていたworkflow雛形 `github_workflows_ci.yml` / `github_workflows_bench.yml` は削除。
- `package.json` の `ci` script をGitHub ActionsのUbuntu環境でも動く `npm run ...` 形式へ更新。
- `package.json` に `pii:scan` を追加。
- `scripts/pii_scan.py` を追加し、G1系の個人パス・代表的なsecret形式をCIで検出できるようにした。

## CI構成

### engine job

- Python 3.12
- `python -m pip install -e ".[api,test]"`
- `python -m pytest -q`

### ui job

- Node 20
- `npm ci`
- `npm run ci`
- `npm run ui:build:pseudo`

### pii job

- Python 3.12
- `python scripts/pii_scan.py`

## Benchmark Workflow

`.github/workflows/bench.yml` は `workflow_dispatch` 専用。

実行内容:

```text
python -m pip install -e ".[api,test]"
python benchmarks/spec_like_benchmark.py --profile smoke --json > bench_results/spec_like_smoke_${{ github.sha }}.json
```

生成JSONはActions artifactとしてアップロードし、CIからリポジトリへコミットしない。

## i18n:coverage方式

CIではエンジンをバックグラウンド起動しない。

理由:

- `apps/workbench-ui/scripts/i18n-coverage.mjs` は `/v1/meta` 取得に失敗した場合、`optics_engine/metadata.py` の列挙定義を静的に読み取るフォールバックを持つ。
- G4時点のcoverage目的は、UI用語集とエンジン列挙定義のズレ検出であり、HTTP起動自体の検証はengine pytestで別途担保する。
- CIの並列job間でエンジン起動を共有しないため、UI jobが単独で安定する。

## ローカル検証結果

```text
python scripts/pii_scan.py: passed
python -m pytest -q: 57 passed, 1 warning
npm.cmd run ci: passed
npm.cmd run ui:build:pseudo: passed
python benchmarks/spec_like_benchmark.py --profile smoke --json: passed
```

補足:

- `npm.cmd run ci` 内のPlaywright E2Eは `6 passed`。
- Viteは依存パッケージ由来の `"use client" directive ignored` 警告を出すが、ビルドは成功している。
- Python pytestはFastAPI TestClient由来のStarletteDeprecationWarningが1件あるが、テストは成功している。
- smoke benchmarkは14面、非球面2面、3波長、full ray aimingを含むspec-like構成でJSON出力を確認した。
