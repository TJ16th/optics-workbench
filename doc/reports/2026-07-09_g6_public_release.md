# G6 Public Release Final Report

Date: 2026-07-09

## Summary

G6の公開前確定作業として、リポジトリ名とNOTICE著作権表示のプレースホルダを確定値に置換し、公開前ゲート検証を再実行した。`master` を `https://github.com/TJ16th/optics-workbench.git` へpushし、push後にGitHub Actionsの起動を確認した。

## Placeholder Replacements

| File | Before | After |
| --- | --- | --- |
| `README.md` | `# <REPO_NAME> - Optics Workbench` | `# optics-workbench - Optics Workbench` |
| `README.md` | `` `<REPO_NAME>` `` | `` `optics-workbench` `` |
| `README.md` | `` `<COPYRIGHT_HOLDER>` `` | `` `TJ16th` `` |
| `NOTICE` | `<REPO_NAME>` | `optics-workbench` |
| `NOTICE` | `Copyright <COPYRIGHT_HOLDER>` | `Copyright 2026 TJ16th` |

Note: `README.md`のタイトル行は実ファイル上ではen dashを含む。上表ではASCII表記に寄せて記録した。

## Verification

| Command | Result |
| --- | --- |
| `python -m pytest -q` | Passed: 57 passed, 1 warning |
| `npm run ci` run 1 | Passed: Playwright E2E 6 passed |
| `npm run ci` run 2 | Passed: Playwright E2E 6 passed |
| `npm run ci` run 3 | Passed: Playwright E2E 6 passed |
| `npm run ui:build:pseudo` | Passed |

No image-plane policy E2E flake reproduced during the three consecutive `npm run ci` runs.

## Push Result

| Item | Value |
| --- | --- |
| Remote URL | `https://github.com/TJ16th/optics-workbench.git` |
| Branch | `master` |
| Pushed commit | `e054eea1a8cf6542dc698d862f5a75667b71d919` |
| Push result | Success |

Remote `master` was verified with `git ls-remote origin refs/heads/master` and matched `e054eea1a8cf6542dc698d862f5a75667b71d919`.

## GitHub Actions Check

GitHub Actions launched automatically after the push. A follow-up status check showed the CI workflow completed with failure. Per G6 scope, detailed log investigation and fixes are left to a separate task.

| Workflow | Status at check | Commit | URL |
| --- | --- | --- | --- |
| CI | `completed`, `failure` | `e054eea1a8cf6542dc698d862f5a75667b71d919` | https://github.com/TJ16th/optics-workbench/actions/runs/28999281557 |
| Graph Update: pip in /. #1453331891 | `completed`, `success` | `e054eea1a8cf6542dc698d862f5a75667b71d919` | https://github.com/TJ16th/optics-workbench/actions/runs/28999281343 |

CI job-level status:

| Job | Conclusion |
| --- | --- |
| engine | `success` |
| pii | `success` |
| ui | `failure` |

Detailed CI log investigation and any follow-up fixes are outside this G6 task.

## Operational Notes

- Issues should be transferred by a human from `doc/reports/issues_backlog.md` to GitHub Issues.
- GitHub Actions runs automatically on push via `.github/workflows/ci.yml`.
- Benchmark workflow also exists in `.github/workflows/bench.yml` and can be run manually as needed.
